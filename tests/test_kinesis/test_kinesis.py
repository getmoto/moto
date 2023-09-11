import datetime
import time
import pytest

import boto3
from botocore.exceptions import ClientError

from dateutil.tz import tzlocal

from moto import mock_kinesis
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core.utils import utcnow


@mock_kinesis
def test_stream_creation_on_demand():
    client = boto3.client("kinesis", region_name="eu-west-1")
    client.create_stream(
        StreamName="my_stream", StreamModeDetails={"StreamMode": "ON_DEMAND"}
    )
    # At the same time, test whether we can pass the StreamARN instead of the name
    stream_arn = get_stream_arn(client, "my_stream")

    # AWS starts with 4 shards by default
    shard_list = client.list_shards(StreamARN=stream_arn)["Shards"]
    assert len(shard_list) == 4

    # Cannot update-shard-count when we're in on-demand mode
    with pytest.raises(ClientError) as exc:
        client.update_shard_count(
            StreamARN=stream_arn, TargetShardCount=3, ScalingType="UNIFORM_SCALING"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == f"Request is invalid. Stream my_stream under account {ACCOUNT_ID} is in On-Demand mode."
    )


@mock_kinesis
def test_update_stream_mode():
    client = boto3.client("kinesis", region_name="eu-west-1")
    client.create_stream(
        StreamName="my_stream", StreamModeDetails={"StreamMode": "ON_DEMAND"}
    )
    arn = client.describe_stream(StreamName="my_stream")["StreamDescription"][
        "StreamARN"
    ]

    client.update_stream_mode(
        StreamARN=arn, StreamModeDetails={"StreamMode": "PROVISIONED"}
    )

    resp = client.describe_stream_summary(StreamName="my_stream")
    stream = resp["StreamDescriptionSummary"]
    assert stream["StreamModeDetails"] == {"StreamMode": "PROVISIONED"}


@mock_kinesis
def test_describe_non_existent_stream():
    client = boto3.client("kinesis", region_name="us-west-2")
    with pytest.raises(ClientError) as exc:
        client.describe_stream_summary(StreamName="not-a-stream")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Stream not-a-stream under account 123456789012 not found."


@mock_kinesis
def test_list_and_delete_stream():
    client = boto3.client("kinesis", region_name="us-west-2")
    assert len(client.list_streams()["StreamNames"]) == 0

    client.create_stream(StreamName="stream1", ShardCount=1)
    client.create_stream(StreamName="stream2", ShardCount=1)
    assert len(client.list_streams()["StreamNames"]) == 2

    client.delete_stream(StreamName="stream1")
    assert len(client.list_streams()["StreamNames"]) == 1

    stream_arn = get_stream_arn(client, "stream2")
    client.delete_stream(StreamARN=stream_arn)
    assert len(client.list_streams()["StreamNames"]) == 0


@mock_kinesis
def test_delete_unknown_stream():
    client = boto3.client("kinesis", region_name="us-west-2")
    with pytest.raises(ClientError) as exc:
        client.delete_stream(StreamName="not-a-stream")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Stream not-a-stream under account 123456789012 not found."


@mock_kinesis
def test_list_many_streams():
    conn = boto3.client("kinesis", region_name="us-west-2")

    for i in range(11):
        conn.create_stream(StreamName=f"stream{i}", ShardCount=1)

    resp = conn.list_streams()
    stream_names = resp["StreamNames"]
    has_more_streams = resp["HasMoreStreams"]
    assert len(stream_names) == 10
    assert has_more_streams is True
    resp2 = conn.list_streams(ExclusiveStartStreamName=stream_names[-1])
    stream_names = resp2["StreamNames"]
    has_more_streams = resp2["HasMoreStreams"]
    assert len(stream_names) == 1
    assert has_more_streams is False


@mock_kinesis
def test_describe_stream_summary():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream_summary"
    shard_count = 5
    conn.create_stream(StreamName=stream_name, ShardCount=shard_count)

    resp = conn.describe_stream_summary(StreamName=stream_name)
    stream = resp["StreamDescriptionSummary"]

    assert stream["StreamName"] == stream_name
    assert stream["OpenShardCount"] == shard_count
    assert (
        stream["StreamARN"]
        == f"arn:aws:kinesis:us-west-2:{ACCOUNT_ID}:stream/{stream_name}"
    )
    assert stream["StreamStatus"] == "ACTIVE"

    stream_arn = get_stream_arn(conn, stream_name)
    resp = conn.describe_stream_summary(StreamARN=stream_arn)
    stream = resp["StreamDescriptionSummary"]

    assert stream["StreamName"] == stream_name


@mock_kinesis
def test_basic_shard_iterator():
    client = boto3.client("kinesis", region_name="us-west-1")

    stream_name = "mystream"
    client.create_stream(StreamName=stream_name, ShardCount=1)
    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shard_id = stream["Shards"][0]["ShardId"]

    resp = client.get_shard_iterator(
        StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
    )
    shard_iterator = resp["ShardIterator"]

    resp = client.get_records(ShardIterator=shard_iterator)
    assert len(resp["Records"]) == 0
    assert resp["MillisBehindLatest"] == 0


@mock_kinesis
def test_basic_shard_iterator_by_stream_arn():
    client = boto3.client("kinesis", region_name="us-west-1")

    stream_name = "mystream"
    client.create_stream(StreamName=stream_name, ShardCount=1)
    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shard_id = stream["Shards"][0]["ShardId"]

    resp = client.get_shard_iterator(
        StreamARN=stream["StreamARN"],
        ShardId=shard_id,
        ShardIteratorType="TRIM_HORIZON",
    )
    shard_iterator = resp["ShardIterator"]

    resp = client.get_records(
        StreamARN=stream["StreamARN"], ShardIterator=shard_iterator
    )
    assert len(resp["Records"]) == 0
    assert resp["MillisBehindLatest"] == 0


@mock_kinesis
def test_get_invalid_shard_iterator():
    client = boto3.client("kinesis", region_name="us-west-1")

    stream_name = "mystream"
    client.create_stream(StreamName=stream_name, ShardCount=1)

    with pytest.raises(ClientError) as exc:
        client.get_shard_iterator(
            StreamName=stream_name, ShardId="123", ShardIteratorType="TRIM_HORIZON"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    # There is some magic in AWS, that '123' is automatically converted into 'shardId-000000000123'
    # AWS itself returns this normalized ID in the error message, not the given id
    assert (
        err["Message"]
        == f"Shard 123 in stream {stream_name} under account {ACCOUNT_ID} does not exist"
    )


@mock_kinesis
def test_put_records():
    client = boto3.client("kinesis", region_name="eu-west-2")

    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=1)
    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    stream_arn = stream["StreamARN"]
    shard_id = stream["Shards"][0]["ShardId"]

    data = b"hello world"
    partition_key = "1234"

    client.put_records(
        Records=[{"Data": data, "PartitionKey": partition_key}] * 5,
        StreamARN=stream_arn,
    )

    resp = client.get_shard_iterator(
        StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
    )
    shard_iterator = resp["ShardIterator"]

    resp = client.get_records(ShardIterator=shard_iterator)
    assert len(resp["Records"]) == 5
    record = resp["Records"][0]

    assert record["Data"] == data
    assert record["PartitionKey"] == partition_key
    assert record["SequenceNumber"] == "1"


@mock_kinesis
def test_get_records_limit():
    client = boto3.client("kinesis", region_name="eu-west-2")

    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=1)
    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    stream_arn = stream["StreamARN"]
    shard_id = stream["Shards"][0]["ShardId"]

    data = b"hello world"

    for index in range(5):
        client.put_record(StreamARN=stream_arn, Data=data, PartitionKey=str(index))

    resp = client.get_shard_iterator(
        StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
    )
    shard_iterator = resp["ShardIterator"]

    # Retrieve only 3 records
    resp = client.get_records(ShardIterator=shard_iterator, Limit=3)
    assert len(resp["Records"]) == 3

    # Then get the rest of the results
    next_shard_iterator = resp["NextShardIterator"]
    response = client.get_records(ShardIterator=next_shard_iterator)
    assert len(response["Records"]) == 2


@mock_kinesis
def test_get_records_at_sequence_number():
    client = boto3.client("kinesis", region_name="eu-west-2")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=1)
    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shard_id = stream["Shards"][0]["ShardId"]

    for index in range(1, 5):
        client.put_record(
            StreamName=stream_name,
            Data=f"data_{index}".encode("utf-8"),
            PartitionKey=str(index),
        )

    resp = client.get_shard_iterator(
        StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
    )
    shard_iterator = resp["ShardIterator"]

    # Retrieve only 2 records
    resp = client.get_records(ShardIterator=shard_iterator, Limit=2)
    sequence_nr = resp["Records"][1]["SequenceNumber"]

    # Then get a new iterator starting at that id
    resp = client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="AT_SEQUENCE_NUMBER",
        StartingSequenceNumber=sequence_nr,
    )
    shard_iterator = resp["ShardIterator"]

    resp = client.get_records(ShardIterator=shard_iterator)
    # And the first result returned should be the second item
    assert resp["Records"][0]["SequenceNumber"] == sequence_nr
    assert resp["Records"][0]["Data"] == b"data_2"


@mock_kinesis
def test_get_records_after_sequence_number():
    client = boto3.client("kinesis", region_name="eu-west-2")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=1)
    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shard_id = stream["Shards"][0]["ShardId"]

    for index in range(1, 5):
        client.put_record(
            StreamName=stream_name,
            Data=f"data_{index}".encode("utf-8"),
            PartitionKey=str(index),
        )

    resp = client.get_shard_iterator(
        StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
    )
    shard_iterator = resp["ShardIterator"]

    # Retrieve only 2 records
    resp = client.get_records(ShardIterator=shard_iterator, Limit=2)
    sequence_nr = resp["Records"][1]["SequenceNumber"]

    # Then get a new iterator starting at that id
    resp = client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="AFTER_SEQUENCE_NUMBER",
        StartingSequenceNumber=sequence_nr,
    )
    shard_iterator = resp["ShardIterator"]

    resp = client.get_records(ShardIterator=shard_iterator)
    # And the first result returned should be the second item
    assert resp["Records"][0]["SequenceNumber"] == "3"
    assert resp["Records"][0]["Data"] == b"data_3"
    assert resp["MillisBehindLatest"] == 0


@mock_kinesis
def test_get_records_latest():
    client = boto3.client("kinesis", region_name="eu-west-2")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=1)
    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shard_id = stream["Shards"][0]["ShardId"]

    for index in range(1, 5):
        client.put_record(
            StreamName=stream_name,
            Data=f"data_{index}".encode("utf-8"),
            PartitionKey=str(index),
        )

    resp = client.get_shard_iterator(
        StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
    )
    shard_iterator = resp["ShardIterator"]

    # Retrieve only 2 records
    resp = client.get_records(ShardIterator=shard_iterator, Limit=2)
    sequence_nr = resp["Records"][1]["SequenceNumber"]

    # Then get a new iterator starting at that id
    resp = client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="LATEST",
        StartingSequenceNumber=sequence_nr,
    )
    shard_iterator = resp["ShardIterator"]

    client.put_record(
        StreamName=stream_name, Data=b"last_record", PartitionKey="last_record"
    )

    resp = client.get_records(ShardIterator=shard_iterator)
    # And the first result returned should be the second item
    assert len(resp["Records"]) == 1
    assert resp["Records"][0]["SequenceNumber"] == "5"
    assert resp["Records"][0]["PartitionKey"] == "last_record"
    assert resp["Records"][0]["Data"] == b"last_record"
    assert resp["MillisBehindLatest"] == 0


@mock_kinesis
def test_get_records_at_timestamp():
    # AT_TIMESTAMP - Read the first record at or after the specified timestamp
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    # Create some data
    for index in range(1, 5):
        conn.put_record(
            StreamName=stream_name, Data=str(index), PartitionKey=str(index)
        )

    # When boto3 floors the timestamp that we pass to get_shard_iterator to
    # second precision even though AWS supports ms precision:
    # http://docs.aws.amazon.com/kinesis/latest/APIReference/API_GetShardIterator.html
    # To test around this limitation we wait until we well into the next second
    # before capturing the time and storing the records we expect to retrieve.
    time.sleep(1.0)
    timestamp = utcnow()

    keys = [str(i) for i in range(5, 10)]
    for k in keys:
        conn.put_record(StreamName=stream_name, Data=k, PartitionKey=k)

    # Get a shard iterator
    response = conn.describe_stream(StreamName=stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="AT_TIMESTAMP",
        Timestamp=timestamp,
    )
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(ShardIterator=shard_iterator)

    assert len(response["Records"]) == len(keys)
    partition_keys = [r["PartitionKey"] for r in response["Records"]]
    assert partition_keys == keys
    assert response["MillisBehindLatest"] == 0


@mock_kinesis
def test_get_records_at_very_old_timestamp():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    # Create some data
    keys = [str(i) for i in range(1, 5)]
    for k in keys:
        conn.put_record(StreamName=stream_name, Data=k, PartitionKey=k)

    # Get a shard iterator
    response = conn.describe_stream(StreamName=stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="AT_TIMESTAMP",
        Timestamp=1,
    )
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(ShardIterator=shard_iterator)
    assert len(response["Records"]) == len(keys)
    partition_keys = [r["PartitionKey"] for r in response["Records"]]
    assert partition_keys == keys
    assert response["MillisBehindLatest"] == 0


@mock_kinesis
def test_get_records_timestamp_filtering():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    conn.put_record(StreamName=stream_name, Data="0", PartitionKey="0")

    time.sleep(1.0)
    timestamp = datetime.datetime.now(tz=tzlocal())

    conn.put_record(StreamName=stream_name, Data="1", PartitionKey="1")

    response = conn.describe_stream(StreamName=stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="AT_TIMESTAMP",
        Timestamp=timestamp,
    )
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(ShardIterator=shard_iterator)
    assert len(response["Records"]) == 1
    assert response["Records"][0]["PartitionKey"] == "1"
    assert response["Records"][0]["ApproximateArrivalTimestamp"] > timestamp
    assert response["MillisBehindLatest"] == 0


@mock_kinesis
def test_get_records_millis_behind_latest():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    conn.put_record(StreamName=stream_name, Data="0", PartitionKey="0")
    time.sleep(1.0)
    conn.put_record(StreamName=stream_name, Data="1", PartitionKey="1")

    response = conn.describe_stream(StreamName=stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(
        StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
    )
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(ShardIterator=shard_iterator, Limit=1)
    assert len(response["Records"]) == 1
    assert response["MillisBehindLatest"] > 0


@mock_kinesis
def test_get_records_at_very_new_timestamp():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    # Create some data
    keys = [str(i) for i in range(1, 5)]
    for k in keys:
        conn.put_record(StreamName=stream_name, Data=k, PartitionKey=k)

    timestamp = utcnow() + datetime.timedelta(seconds=1)

    # Get a shard iterator
    response = conn.describe_stream(StreamName=stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="AT_TIMESTAMP",
        Timestamp=timestamp,
    )
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(ShardIterator=shard_iterator)

    assert len(response["Records"]) == 0
    assert response["MillisBehindLatest"] == 0


@mock_kinesis
def test_get_records_from_empty_stream_at_timestamp():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    timestamp = utcnow()

    # Get a shard iterator
    response = conn.describe_stream(StreamName=stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="AT_TIMESTAMP",
        Timestamp=timestamp,
    )
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(ShardIterator=shard_iterator)

    assert len(response["Records"]) == 0
    assert response["MillisBehindLatest"] == 0


@mock_kinesis
def test_valid_increase_stream_retention_period():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    conn.increase_stream_retention_period(
        StreamName=stream_name, RetentionPeriodHours=40
    )

    response = conn.describe_stream(StreamName=stream_name)
    assert response["StreamDescription"]["RetentionPeriodHours"] == 40


@mock_kinesis
def test_invalid_increase_stream_retention_period():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    conn.increase_stream_retention_period(
        StreamName=stream_name, RetentionPeriodHours=30
    )
    with pytest.raises(ClientError) as ex:
        conn.increase_stream_retention_period(
            StreamName=stream_name, RetentionPeriodHours=25
        )
    assert ex.value.response["Error"]["Code"] == "InvalidArgumentException"
    assert (
        ex.value.response["Error"]["Message"]
        == "Requested retention period (25 hours) for stream my_stream can not be shorter than existing retention period (30 hours). Use DecreaseRetentionPeriod API."
    )


@mock_kinesis
def test_invalid_increase_stream_retention_too_low():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    with pytest.raises(ClientError) as ex:
        conn.increase_stream_retention_period(
            StreamName=stream_name, RetentionPeriodHours=20
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        err["Message"]
        == "Minimum allowed retention period is 24 hours. Requested retention period (20 hours) is too short."
    )


@mock_kinesis
def test_invalid_increase_stream_retention_too_high():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    with pytest.raises(ClientError) as ex:
        conn.increase_stream_retention_period(
            StreamName=stream_name, RetentionPeriodHours=9999
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        err["Message"]
        == "Maximum allowed retention period is 8760 hours. Requested retention period (9999 hours) is too long."
    )


@mock_kinesis
def test_valid_decrease_stream_retention_period():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "decrease_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)
    stream_arn = get_stream_arn(conn, stream_name)

    conn.increase_stream_retention_period(
        StreamName=stream_name, RetentionPeriodHours=30
    )
    conn.decrease_stream_retention_period(
        StreamName=stream_name, RetentionPeriodHours=25
    )

    response = conn.describe_stream(StreamName=stream_name)
    assert response["StreamDescription"]["RetentionPeriodHours"] == 25

    conn.increase_stream_retention_period(StreamARN=stream_arn, RetentionPeriodHours=29)
    conn.decrease_stream_retention_period(StreamARN=stream_arn, RetentionPeriodHours=26)

    response = conn.describe_stream(StreamARN=stream_arn)
    assert response["StreamDescription"]["RetentionPeriodHours"] == 26


@mock_kinesis
def test_decrease_stream_retention_period_upwards():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "decrease_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    with pytest.raises(ClientError) as ex:
        conn.decrease_stream_retention_period(
            StreamName=stream_name, RetentionPeriodHours=40
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        err["Message"]
        == "Requested retention period (40 hours) for stream decrease_stream can not be longer than existing retention period (24 hours). Use IncreaseRetentionPeriod API."
    )


@mock_kinesis
def test_decrease_stream_retention_period_too_low():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "decrease_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    with pytest.raises(ClientError) as ex:
        conn.decrease_stream_retention_period(
            StreamName=stream_name, RetentionPeriodHours=4
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        err["Message"]
        == "Minimum allowed retention period is 24 hours. Requested retention period (4 hours) is too short."
    )


@mock_kinesis
def test_decrease_stream_retention_period_too_high():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "decrease_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    with pytest.raises(ClientError) as ex:
        conn.decrease_stream_retention_period(
            StreamName=stream_name, RetentionPeriodHours=9999
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        err["Message"]
        == "Maximum allowed retention period is 8760 hours. Requested retention period (9999 hours) is too long."
    )


@mock_kinesis
def test_invalid_shard_iterator_type():
    client = boto3.client("kinesis", region_name="eu-west-2")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=1)
    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shard_id = stream["Shards"][0]["ShardId"]

    with pytest.raises(ClientError) as exc:
        client.get_shard_iterator(
            StreamName=stream_name, ShardId=shard_id, ShardIteratorType="invalid-type"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert err["Message"] == "Invalid ShardIteratorType: invalid-type"


@mock_kinesis
def test_add_list_remove_tags():
    client = boto3.client("kinesis", region_name="eu-west-2")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=1)
    stream_arn = get_stream_arn(client, stream_name)
    client.add_tags_to_stream(
        StreamName=stream_name,
        Tags={"tag1": "val1", "tag2": "val2", "tag3": "val3", "tag4": "val4"},
    )

    tags = client.list_tags_for_stream(StreamName=stream_name)["Tags"]
    assert len(tags) == 4
    assert {"Key": "tag1", "Value": "val1"} in tags
    assert {"Key": "tag2", "Value": "val2"} in tags
    assert {"Key": "tag3", "Value": "val3"} in tags
    assert {"Key": "tag4", "Value": "val4"} in tags

    client.add_tags_to_stream(StreamARN=stream_arn, Tags={"tag5": "val5"})

    tags = client.list_tags_for_stream(StreamARN=stream_arn)["Tags"]
    assert len(tags) == 5
    assert {"Key": "tag5", "Value": "val5"} in tags

    client.remove_tags_from_stream(StreamName=stream_name, TagKeys=["tag2", "tag3"])

    tags = client.list_tags_for_stream(StreamName=stream_name)["Tags"]
    assert len(tags) == 3
    assert {"Key": "tag1", "Value": "val1"} in tags
    assert {"Key": "tag4", "Value": "val4"} in tags
    assert {"Key": "tag5", "Value": "val5"} in tags

    client.remove_tags_from_stream(StreamARN=stream_arn, TagKeys=["tag4"])

    tags = client.list_tags_for_stream(StreamName=stream_name)["Tags"]
    assert len(tags) == 2
    assert {"Key": "tag1", "Value": "val1"} in tags
    assert {"Key": "tag5", "Value": "val5"} in tags


@mock_kinesis
def test_merge_shards():
    client = boto3.client("kinesis", region_name="eu-west-2")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=4)
    stream_arn = get_stream_arn(client, stream_name)

    for index in range(1, 50):
        client.put_record(
            StreamName=stream_name,
            Data=f"data_{index}".encode("utf-8"),
            PartitionKey=str(index),
        )
    for index in range(51, 100):
        client.put_record(
            StreamARN=stream_arn,
            Data=f"data_{index}".encode("utf-8"),
            PartitionKey=str(index),
        )

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shards = stream["Shards"]
    assert len(shards) == 4

    client.merge_shards(
        StreamName=stream_name,
        ShardToMerge="shardId-000000000000",
        AdjacentShardToMerge="shardId-000000000001",
    )

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shards = stream["Shards"]

    # Old shards still exist, but are closed. A new shard is created out of the old one
    assert len(shards) == 5

    # Only three shards are active - the two merged shards are closed
    active_shards = [
        shard
        for shard in shards
        if "EndingSequenceNumber" not in shard["SequenceNumberRange"]
    ]
    assert len(active_shards) == 3

    client.merge_shards(
        StreamARN=stream_arn,
        ShardToMerge="shardId-000000000004",
        AdjacentShardToMerge="shardId-000000000002",
    )

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shards = stream["Shards"]

    active_shards = [
        shard
        for shard in shards
        if "EndingSequenceNumber" not in shard["SequenceNumberRange"]
    ]
    assert len(active_shards) == 2

    for shard in active_shards:
        del shard["HashKeyRange"]
        del shard["SequenceNumberRange"]

    # Original shard #3 is still active (0,1,2 have been merged and closed
    assert {"ShardId": "shardId-000000000003"} in active_shards
    # Shard #4 was the child of #0 and #1
    # Shard #5 is the child of #4 (parent) and #2 (adjacent-parent)
    assert {
        "ShardId": "shardId-000000000005",
        "ParentShardId": "shardId-000000000004",
        "AdjacentParentShardId": "shardId-000000000002",
    } in active_shards


@mock_kinesis
def test_merge_shards_invalid_arg():
    client = boto3.client("kinesis", region_name="eu-west-2")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=4)

    with pytest.raises(ClientError) as exc:
        client.merge_shards(
            StreamName=stream_name,
            ShardToMerge="shardId-000000000000",
            AdjacentShardToMerge="shardId-000000000002",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert err["Message"] == "shardId-000000000002"


def get_stream_arn(client, stream_name):
    return client.describe_stream(StreamName=stream_name)["StreamDescription"][
        "StreamARN"
    ]
