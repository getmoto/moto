from __future__ import unicode_literals

import datetime
import time

import boto.kinesis
import boto3
from boto.kinesis.exceptions import ResourceNotFoundException, InvalidArgumentException

from moto import mock_kinesis, mock_kinesis_deprecated
from moto.core import ACCOUNT_ID


@mock_kinesis_deprecated
def test_create_cluster():
    conn = boto.kinesis.connect_to_region("us-west-2")

    conn.create_stream("my_stream", 3)

    stream_response = conn.describe_stream("my_stream")

    stream = stream_response["StreamDescription"]
    stream["StreamName"].should.equal("my_stream")
    stream["HasMoreShards"].should.equal(False)
    stream["StreamARN"].should.equal(
        "arn:aws:kinesis:us-west-2:{}:my_stream".format(ACCOUNT_ID)
    )
    stream["StreamStatus"].should.equal("ACTIVE")

    shards = stream["Shards"]
    shards.should.have.length_of(3)


@mock_kinesis_deprecated
def test_describe_non_existent_stream():
    conn = boto.kinesis.connect_to_region("us-east-1")
    conn.describe_stream.when.called_with("not-a-stream").should.throw(
        ResourceNotFoundException
    )


@mock_kinesis_deprecated
def test_list_and_delete_stream():
    conn = boto.kinesis.connect_to_region("us-west-2")

    conn.create_stream("stream1", 1)
    conn.create_stream("stream2", 1)

    conn.list_streams()["StreamNames"].should.have.length_of(2)

    conn.delete_stream("stream2")

    conn.list_streams()["StreamNames"].should.have.length_of(1)

    # Delete invalid id
    conn.delete_stream.when.called_with("not-a-stream").should.throw(
        ResourceNotFoundException
    )


@mock_kinesis
def test_list_many_streams():
    conn = boto3.client("kinesis", region_name="us-west-2")

    for i in range(11):
        conn.create_stream(StreamName="stream%d" % i, ShardCount=1)

    resp = conn.list_streams()
    stream_names = resp["StreamNames"]
    has_more_streams = resp["HasMoreStreams"]
    stream_names.should.have.length_of(10)
    has_more_streams.should.be(True)
    resp2 = conn.list_streams(ExclusiveStartStreamName=stream_names[-1])
    stream_names = resp2["StreamNames"]
    has_more_streams = resp2["HasMoreStreams"]
    stream_names.should.have.length_of(1)
    has_more_streams.should.equal(False)


@mock_kinesis
def test_describe_stream_summary():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream_summary"
    shard_count = 5
    conn.create_stream(StreamName=stream_name, ShardCount=shard_count)

    resp = conn.describe_stream_summary(StreamName=stream_name)
    stream = resp["StreamDescriptionSummary"]

    stream["StreamName"].should.equal(stream_name)
    stream["OpenShardCount"].should.equal(shard_count)
    stream["StreamARN"].should.equal(
        "arn:aws:kinesis:us-west-2:{}:{}".format(ACCOUNT_ID, stream_name)
    )
    stream["StreamStatus"].should.equal("ACTIVE")


@mock_kinesis_deprecated
def test_basic_shard_iterator():
    conn = boto.kinesis.connect_to_region("us-west-2")

    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    response = conn.describe_stream(stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]

    response = conn.get_shard_iterator(stream_name, shard_id, "TRIM_HORIZON")
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(shard_iterator)
    shard_iterator = response["NextShardIterator"]
    response["Records"].should.equal([])
    response["MillisBehindLatest"].should.equal(0)


@mock_kinesis_deprecated
def test_get_invalid_shard_iterator():
    conn = boto.kinesis.connect_to_region("us-west-2")

    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    conn.get_shard_iterator.when.called_with(
        stream_name, "123", "TRIM_HORIZON"
    ).should.throw(ResourceNotFoundException)


@mock_kinesis_deprecated
def test_put_records():
    conn = boto.kinesis.connect_to_region("us-west-2")

    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    data = "hello world"
    partition_key = "1234"

    conn.put_record.when.called_with(stream_name, data, 1234).should.throw(
        InvalidArgumentException
    )

    conn.put_record(stream_name, data, partition_key)

    response = conn.describe_stream(stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]

    response = conn.get_shard_iterator(stream_name, shard_id, "TRIM_HORIZON")
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(shard_iterator)
    shard_iterator = response["NextShardIterator"]
    response["Records"].should.have.length_of(1)
    record = response["Records"][0]

    record["Data"].should.equal("hello world")
    record["PartitionKey"].should.equal("1234")
    record["SequenceNumber"].should.equal("1")


@mock_kinesis_deprecated
def test_get_records_limit():
    conn = boto.kinesis.connect_to_region("us-west-2")

    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    # Create some data
    data = "hello world"

    for index in range(5):
        conn.put_record(stream_name, data, str(index))

    # Get a shard iterator
    response = conn.describe_stream(stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(stream_name, shard_id, "TRIM_HORIZON")
    shard_iterator = response["ShardIterator"]

    # Retrieve only 3 records
    response = conn.get_records(shard_iterator, limit=3)
    response["Records"].should.have.length_of(3)

    # Then get the rest of the results
    next_shard_iterator = response["NextShardIterator"]
    response = conn.get_records(next_shard_iterator)
    response["Records"].should.have.length_of(2)


@mock_kinesis_deprecated
def test_get_records_at_sequence_number():
    # AT_SEQUENCE_NUMBER - Start reading exactly from the position denoted by
    # a specific sequence number.
    conn = boto.kinesis.connect_to_region("us-west-2")
    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    # Create some data
    for index in range(1, 5):
        conn.put_record(stream_name, str(index), str(index))

    # Get a shard iterator
    response = conn.describe_stream(stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(stream_name, shard_id, "TRIM_HORIZON")
    shard_iterator = response["ShardIterator"]

    # Get the second record
    response = conn.get_records(shard_iterator, limit=2)
    second_sequence_id = response["Records"][1]["SequenceNumber"]

    # Then get a new iterator starting at that id
    response = conn.get_shard_iterator(
        stream_name, shard_id, "AT_SEQUENCE_NUMBER", second_sequence_id
    )
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(shard_iterator)
    # And the first result returned should be the second item
    response["Records"][0]["SequenceNumber"].should.equal(second_sequence_id)
    response["Records"][0]["Data"].should.equal("2")


@mock_kinesis_deprecated
def test_get_records_after_sequence_number():
    # AFTER_SEQUENCE_NUMBER - Start reading right after the position denoted
    # by a specific sequence number.
    conn = boto.kinesis.connect_to_region("us-west-2")
    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    # Create some data
    for index in range(1, 5):
        conn.put_record(stream_name, str(index), str(index))

    # Get a shard iterator
    response = conn.describe_stream(stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(stream_name, shard_id, "TRIM_HORIZON")
    shard_iterator = response["ShardIterator"]

    # Get the second record
    response = conn.get_records(shard_iterator, limit=2)
    second_sequence_id = response["Records"][1]["SequenceNumber"]

    # Then get a new iterator starting after that id
    response = conn.get_shard_iterator(
        stream_name, shard_id, "AFTER_SEQUENCE_NUMBER", second_sequence_id
    )
    shard_iterator = response["ShardIterator"]

    response = conn.get_records(shard_iterator)
    # And the first result returned should be the third item
    response["Records"][0]["Data"].should.equal("3")
    response["MillisBehindLatest"].should.equal(0)


@mock_kinesis_deprecated
def test_get_records_latest():
    # LATEST - Start reading just after the most recent record in the shard,
    # so that you always read the most recent data in the shard.
    conn = boto.kinesis.connect_to_region("us-west-2")
    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    # Create some data
    for index in range(1, 5):
        conn.put_record(stream_name, str(index), str(index))

    # Get a shard iterator
    response = conn.describe_stream(stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator(stream_name, shard_id, "TRIM_HORIZON")
    shard_iterator = response["ShardIterator"]

    # Get the second record
    response = conn.get_records(shard_iterator, limit=2)
    second_sequence_id = response["Records"][1]["SequenceNumber"]

    # Then get a new iterator starting after that id
    response = conn.get_shard_iterator(
        stream_name, shard_id, "LATEST", second_sequence_id
    )
    shard_iterator = response["ShardIterator"]

    # Write some more data
    conn.put_record(stream_name, "last_record", "last_record")

    response = conn.get_records(shard_iterator)
    # And the only result returned should be the new item
    response["Records"].should.have.length_of(1)
    response["Records"][0]["PartitionKey"].should.equal("last_record")
    response["Records"][0]["Data"].should.equal("last_record")
    response["MillisBehindLatest"].should.equal(0)


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
    timestamp = datetime.datetime.utcnow()

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

    response["Records"].should.have.length_of(len(keys))
    partition_keys = [r["PartitionKey"] for r in response["Records"]]
    partition_keys.should.equal(keys)
    response["MillisBehindLatest"].should.equal(0)


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
    response["Records"].should.have.length_of(len(keys))
    partition_keys = [r["PartitionKey"] for r in response["Records"]]
    partition_keys.should.equal(keys)
    response["MillisBehindLatest"].should.equal(0)


@mock_kinesis
def test_get_records_timestamp_filtering():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    conn.put_record(StreamName=stream_name, Data="0", PartitionKey="0")

    time.sleep(1.0)
    timestamp = datetime.datetime.utcnow()

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
    response["Records"].should.have.length_of(1)
    response["Records"][0]["PartitionKey"].should.equal("1")
    response["Records"][0]["ApproximateArrivalTimestamp"].should.be.greater_than(
        timestamp
    )
    response["MillisBehindLatest"].should.equal(0)


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
    response["Records"].should.have.length_of(1)
    response["MillisBehindLatest"].should.be.greater_than(0)


@mock_kinesis
def test_get_records_at_very_new_timestamp():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    # Create some data
    keys = [str(i) for i in range(1, 5)]
    for k in keys:
        conn.put_record(StreamName=stream_name, Data=k, PartitionKey=k)

    timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)

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

    response["Records"].should.have.length_of(0)
    response["MillisBehindLatest"].should.equal(0)


@mock_kinesis
def test_get_records_from_empty_stream_at_timestamp():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    conn.create_stream(StreamName=stream_name, ShardCount=1)

    timestamp = datetime.datetime.utcnow()

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

    response["Records"].should.have.length_of(0)
    response["MillisBehindLatest"].should.equal(0)


@mock_kinesis_deprecated
def test_invalid_shard_iterator_type():
    conn = boto.kinesis.connect_to_region("us-west-2")
    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    response = conn.describe_stream(stream_name)
    shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
    response = conn.get_shard_iterator.when.called_with(
        stream_name, shard_id, "invalid-type"
    ).should.throw(InvalidArgumentException)


@mock_kinesis_deprecated
def test_add_tags():
    conn = boto.kinesis.connect_to_region("us-west-2")
    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    conn.describe_stream(stream_name)
    conn.add_tags_to_stream(stream_name, {"tag1": "val1"})
    conn.add_tags_to_stream(stream_name, {"tag2": "val2"})
    conn.add_tags_to_stream(stream_name, {"tag1": "val3"})
    conn.add_tags_to_stream(stream_name, {"tag2": "val4"})


@mock_kinesis_deprecated
def test_list_tags():
    conn = boto.kinesis.connect_to_region("us-west-2")
    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    conn.describe_stream(stream_name)
    conn.add_tags_to_stream(stream_name, {"tag1": "val1"})
    tags = dict(
        [
            (tag["Key"], tag["Value"])
            for tag in conn.list_tags_for_stream(stream_name)["Tags"]
        ]
    )
    tags.get("tag1").should.equal("val1")
    conn.add_tags_to_stream(stream_name, {"tag2": "val2"})
    tags = dict(
        [
            (tag["Key"], tag["Value"])
            for tag in conn.list_tags_for_stream(stream_name)["Tags"]
        ]
    )
    tags.get("tag2").should.equal("val2")
    conn.add_tags_to_stream(stream_name, {"tag1": "val3"})
    tags = dict(
        [
            (tag["Key"], tag["Value"])
            for tag in conn.list_tags_for_stream(stream_name)["Tags"]
        ]
    )
    tags.get("tag1").should.equal("val3")
    conn.add_tags_to_stream(stream_name, {"tag2": "val4"})
    tags = dict(
        [
            (tag["Key"], tag["Value"])
            for tag in conn.list_tags_for_stream(stream_name)["Tags"]
        ]
    )
    tags.get("tag2").should.equal("val4")


@mock_kinesis_deprecated
def test_remove_tags():
    conn = boto.kinesis.connect_to_region("us-west-2")
    stream_name = "my_stream"
    conn.create_stream(stream_name, 1)

    conn.describe_stream(stream_name)
    conn.add_tags_to_stream(stream_name, {"tag1": "val1"})
    tags = dict(
        [
            (tag["Key"], tag["Value"])
            for tag in conn.list_tags_for_stream(stream_name)["Tags"]
        ]
    )
    tags.get("tag1").should.equal("val1")
    conn.remove_tags_from_stream(stream_name, ["tag1"])
    tags = dict(
        [
            (tag["Key"], tag["Value"])
            for tag in conn.list_tags_for_stream(stream_name)["Tags"]
        ]
    )
    tags.get("tag1").should.equal(None)

    conn.add_tags_to_stream(stream_name, {"tag2": "val2"})
    tags = dict(
        [
            (tag["Key"], tag["Value"])
            for tag in conn.list_tags_for_stream(stream_name)["Tags"]
        ]
    )
    tags.get("tag2").should.equal("val2")
    conn.remove_tags_from_stream(stream_name, ["tag2"])
    tags = dict(
        [
            (tag["Key"], tag["Value"])
            for tag in conn.list_tags_for_stream(stream_name)["Tags"]
        ]
    )
    tags.get("tag2").should.equal(None)


@mock_kinesis_deprecated
def test_split_shard():
    conn = boto.kinesis.connect_to_region("us-west-2")
    stream_name = "my_stream"

    conn.create_stream(stream_name, 2)

    # Create some data
    for index in range(1, 100):
        conn.put_record(stream_name, str(index), str(index))

    stream_response = conn.describe_stream(stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(2)
    sum(
        [shard["SequenceNumberRange"]["EndingSequenceNumber"] for shard in shards]
    ).should.equal(99)

    shard_range = shards[0]["HashKeyRange"]
    new_starting_hash = (
        int(shard_range["EndingHashKey"]) + int(shard_range["StartingHashKey"])
    ) // 2
    conn.split_shard("my_stream", shards[0]["ShardId"], str(new_starting_hash))

    stream_response = conn.describe_stream(stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(3)
    sum(
        [shard["SequenceNumberRange"]["EndingSequenceNumber"] for shard in shards]
    ).should.equal(99)

    shard_range = shards[2]["HashKeyRange"]
    new_starting_hash = (
        int(shard_range["EndingHashKey"]) + int(shard_range["StartingHashKey"])
    ) // 2
    conn.split_shard("my_stream", shards[2]["ShardId"], str(new_starting_hash))

    stream_response = conn.describe_stream(stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(4)
    sum(
        [shard["SequenceNumberRange"]["EndingSequenceNumber"] for shard in shards]
    ).should.equal(99)


@mock_kinesis_deprecated
def test_merge_shards():
    conn = boto.kinesis.connect_to_region("us-west-2")
    stream_name = "my_stream"

    conn.create_stream(stream_name, 4)

    # Create some data
    for index in range(1, 100):
        conn.put_record(stream_name, str(index), str(index))

    stream_response = conn.describe_stream(stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(4)

    conn.merge_shards.when.called_with(
        stream_name, "shardId-000000000000", "shardId-000000000002"
    ).should.throw(InvalidArgumentException)

    stream_response = conn.describe_stream(stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(4)
    sum(
        [shard["SequenceNumberRange"]["EndingSequenceNumber"] for shard in shards]
    ).should.equal(99)

    conn.merge_shards(stream_name, "shardId-000000000000", "shardId-000000000001")

    stream_response = conn.describe_stream(stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(3)
    sum(
        [shard["SequenceNumberRange"]["EndingSequenceNumber"] for shard in shards]
    ).should.equal(99)
    conn.merge_shards(stream_name, "shardId-000000000002", "shardId-000000000000")

    stream_response = conn.describe_stream(stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(2)
    sum(
        [shard["SequenceNumberRange"]["EndingSequenceNumber"] for shard in shards]
    ).should.equal(99)
