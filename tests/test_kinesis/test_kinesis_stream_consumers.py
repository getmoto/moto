import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_kinesis
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


def create_stream(client):
    stream_name = "my-stream"
    client.create_stream(StreamName=stream_name, ShardCount=4)
    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    return stream["StreamARN"]


@mock_kinesis
def test_list_stream_consumers():
    client = boto3.client("kinesis", region_name="eu-west-1")
    stream_arn = create_stream(client)

    resp = client.list_stream_consumers(StreamARN=stream_arn)

    assert resp["Consumers"] == []


@mock_kinesis
def test_register_stream_consumer():
    client = boto3.client("kinesis", region_name="eu-west-1")
    stream_arn = create_stream(client)

    resp = client.register_stream_consumer(
        StreamARN=stream_arn, ConsumerName="newconsumer"
    )
    assert "Consumer" in resp

    consumer = resp["Consumer"]

    assert consumer["ConsumerName"] == "newconsumer"
    assert (
        consumer["ConsumerARN"]
        == f"arn:aws:kinesis:eu-west-1:{ACCOUNT_ID}:stream/my-stream/consumer/newconsumer"
    )
    assert consumer["ConsumerStatus"] == "ACTIVE"
    assert "ConsumerCreationTimestamp" in consumer

    resp = client.list_stream_consumers(StreamARN=stream_arn)

    assert len(resp["Consumers"]) == 1
    consumer = resp["Consumers"][0]
    assert consumer["ConsumerName"] == "newconsumer"
    assert (
        consumer["ConsumerARN"]
        == f"arn:aws:kinesis:eu-west-1:{ACCOUNT_ID}:stream/my-stream/consumer/newconsumer"
    )
    assert consumer["ConsumerStatus"] == "ACTIVE"
    assert "ConsumerCreationTimestamp" in consumer


@mock_kinesis
def test_describe_stream_consumer_by_name():
    client = boto3.client("kinesis", region_name="us-east-2")
    stream_arn = create_stream(client)
    client.register_stream_consumer(StreamARN=stream_arn, ConsumerName="newconsumer")

    resp = client.describe_stream_consumer(
        StreamARN=stream_arn, ConsumerName="newconsumer"
    )
    assert "ConsumerDescription" in resp

    consumer = resp["ConsumerDescription"]
    assert consumer["ConsumerName"] == "newconsumer"
    assert "ConsumerARN" in consumer
    assert consumer["ConsumerStatus"] == "ACTIVE"
    assert "ConsumerCreationTimestamp" in consumer
    assert consumer["StreamARN"] == stream_arn


@mock_kinesis
def test_describe_stream_consumer_by_arn():
    client = boto3.client("kinesis", region_name="us-east-2")
    stream_arn = create_stream(client)
    resp = client.register_stream_consumer(
        StreamARN=stream_arn, ConsumerName="newconsumer"
    )
    consumer_arn = resp["Consumer"]["ConsumerARN"]

    resp = client.describe_stream_consumer(ConsumerARN=consumer_arn)
    assert "ConsumerDescription" in resp

    consumer = resp["ConsumerDescription"]
    assert consumer["ConsumerName"] == "newconsumer"
    assert "ConsumerARN" in consumer
    assert consumer["ConsumerStatus"] == "ACTIVE"
    assert "ConsumerCreationTimestamp" in consumer
    assert consumer["StreamARN"] == stream_arn


@mock_kinesis
def test_describe_stream_consumer_unknown():
    client = boto3.client("kinesis", region_name="us-east-2")
    create_stream(client)

    unknown_arn = f"arn:aws:kinesis:us-east-2:{ACCOUNT_ID}:stream/unknown"
    with pytest.raises(ClientError) as exc:
        client.describe_stream_consumer(ConsumerARN=unknown_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Consumer {unknown_arn}, account {ACCOUNT_ID} not found."


@mock_kinesis
def test_deregister_stream_consumer_by_name():
    client = boto3.client("kinesis", region_name="ap-southeast-1")
    stream_arn = create_stream(client)

    client.register_stream_consumer(StreamARN=stream_arn, ConsumerName="consumer1")
    client.register_stream_consumer(StreamARN=stream_arn, ConsumerName="consumer2")

    assert len(client.list_stream_consumers(StreamARN=stream_arn)["Consumers"]) == 2

    client.deregister_stream_consumer(StreamARN=stream_arn, ConsumerName="consumer1")

    assert len(client.list_stream_consumers(StreamARN=stream_arn)["Consumers"]) == 1


@mock_kinesis
def test_deregister_stream_consumer_by_arn():
    client = boto3.client("kinesis", region_name="ap-southeast-1")
    stream_arn = create_stream(client)

    resp = client.register_stream_consumer(
        StreamARN=stream_arn, ConsumerName="consumer1"
    )
    consumer1_arn = resp["Consumer"]["ConsumerARN"]
    client.register_stream_consumer(StreamARN=stream_arn, ConsumerName="consumer2")

    assert len(client.list_stream_consumers(StreamARN=stream_arn)["Consumers"]) == 2

    client.deregister_stream_consumer(ConsumerARN=consumer1_arn)

    assert len(client.list_stream_consumers(StreamARN=stream_arn)["Consumers"]) == 1
