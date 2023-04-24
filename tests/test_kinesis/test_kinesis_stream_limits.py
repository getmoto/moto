import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_kinesis


ONE_MB = 2**20


@mock_kinesis
def test_record_data_exceeds_1mb():
    client = boto3.client("kinesis", region_name="us-east-1")
    client.create_stream(StreamName="my_stream", ShardCount=1)
    with pytest.raises(ClientError) as exc:
        client.put_records(
            Records=[{"Data": b"a" * (ONE_MB + 1), "PartitionKey": "key"}],
            StreamName="my_stream",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "1 validation error detected: Value at 'records.1.member.data' failed to satisfy constraint: Member must have length less than or equal to 1048576"
    )


@mock_kinesis
def test_record_data_and_partition_key_exceeds_1mb():
    client = boto3.client("kinesis", region_name="us-east-1")
    client.create_stream(StreamName="my_stream", ShardCount=1)

    key = "key"
    key_size = len(key)
    data_size = ONE_MB - key_size + 1
    with pytest.raises(ClientError) as exc:
        client.put_records(
            Records=[{"Data": b"a" * data_size, "PartitionKey": key}],
            StreamName="my_stream",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "1 validation error detected: Value at 'records.1.member.data' failed to satisfy constraint: Member must have length less than or equal to 1048576"
    )


@mock_kinesis
def test_record_data_and_partition_key_exactly_1mb():
    client = boto3.client("kinesis", region_name="us-east-1")
    client.create_stream(StreamName="my_stream", ShardCount=1)

    key = "key"
    key_size = len(key)
    data_size = ONE_MB - key_size

    client.put_records(
        Records=[{"Data": b"a" * data_size, "PartitionKey": key}],
        StreamName="my_stream",
    )


@mock_kinesis
def test_record_data_and_partition_key_smaller_than_1mb():
    client = boto3.client("kinesis", region_name="us-east-1")
    client.create_stream(StreamName="my_stream", ShardCount=1)

    key = "key"
    key_size = len(key)
    data_size = ONE_MB - key_size - 1
    client.put_records(
        Records=[{"Data": b"a" * data_size, "PartitionKey": key}],
        StreamName="my_stream",
    )


@mock_kinesis
def test_total_record_data_exceeds_5mb():
    client = boto3.client("kinesis", region_name="us-east-1")
    client.create_stream(StreamName="my_stream", ShardCount=1)
    with pytest.raises(ClientError) as exc:
        client.put_records(
            Records=[{"Data": b"a" * 2**20, "PartitionKey": "key"}] * 5,
            StreamName="my_stream",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidArgumentException")
    err["Message"].should.equal("Records size exceeds 5 MB limit")


@mock_kinesis
def test_total_record_data_exact_5mb():
    client = boto3.client("kinesis", region_name="us-east-1")
    client.create_stream(StreamName="my_stream", ShardCount=1)
    key = "key"
    key_size = len(key)
    data_size = ONE_MB - key_size
    client.put_records(
        Records=[{"Data": b"a" * (data_size), "PartitionKey": key}] * 5,
        StreamName="my_stream",
    )


@mock_kinesis
def test_too_many_records():
    client = boto3.client("kinesis", region_name="us-east-1")
    client.create_stream(StreamName="my_stream", ShardCount=1)

    with pytest.raises(ClientError) as exc:
        client.put_records(
            Records=[{"Data": b"a", "PartitionKey": "key"}] * 501,
            StreamName="my_stream",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "1 validation error detected: Value at 'records' failed to satisfy constraint: Member must have length less than or equal to 500"
    )
