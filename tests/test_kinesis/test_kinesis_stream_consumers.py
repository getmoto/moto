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

    resp.should.have.key("Consumers").equals([])


@mock_kinesis
def test_register_stream_consumer():
    client = boto3.client("kinesis", region_name="eu-west-1")
    stream_arn = create_stream(client)

    resp = client.register_stream_consumer(
        StreamARN=stream_arn, ConsumerName="newconsumer"
    )
    resp.should.have.key("Consumer")

    consumer = resp["Consumer"]

    consumer.should.have.key("ConsumerName").equals("newconsumer")
    consumer.should.have.key("ConsumerARN").equals(
        f"arn:aws:kinesis:eu-west-1:{ACCOUNT_ID}:stream/my-stream/consumer/newconsumer"
    )
    consumer.should.have.key("ConsumerStatus").equals("ACTIVE")
    consumer.should.have.key("ConsumerCreationTimestamp")

    resp = client.list_stream_consumers(StreamARN=stream_arn)

    resp.should.have.key("Consumers").length_of(1)
    consumer = resp["Consumers"][0]
    consumer.should.have.key("ConsumerName").equals("newconsumer")
    consumer.should.have.key("ConsumerARN").equals(
        f"arn:aws:kinesis:eu-west-1:{ACCOUNT_ID}:stream/my-stream/consumer/newconsumer"
    )
    consumer.should.have.key("ConsumerStatus").equals("ACTIVE")
    consumer.should.have.key("ConsumerCreationTimestamp")


@mock_kinesis
def test_describe_stream_consumer_by_name():
    client = boto3.client("kinesis", region_name="us-east-2")
    stream_arn = create_stream(client)
    client.register_stream_consumer(StreamARN=stream_arn, ConsumerName="newconsumer")

    resp = client.describe_stream_consumer(
        StreamARN=stream_arn, ConsumerName="newconsumer"
    )
    resp.should.have.key("ConsumerDescription")

    consumer = resp["ConsumerDescription"]
    consumer.should.have.key("ConsumerName").equals("newconsumer")
    consumer.should.have.key("ConsumerARN")
    consumer.should.have.key("ConsumerStatus").equals("ACTIVE")
    consumer.should.have.key("ConsumerCreationTimestamp")
    consumer.should.have.key("StreamARN").equals(stream_arn)


@mock_kinesis
def test_describe_stream_consumer_by_arn():
    client = boto3.client("kinesis", region_name="us-east-2")
    stream_arn = create_stream(client)
    resp = client.register_stream_consumer(
        StreamARN=stream_arn, ConsumerName="newconsumer"
    )
    consumer_arn = resp["Consumer"]["ConsumerARN"]

    resp = client.describe_stream_consumer(ConsumerARN=consumer_arn)
    resp.should.have.key("ConsumerDescription")

    consumer = resp["ConsumerDescription"]
    consumer.should.have.key("ConsumerName").equals("newconsumer")
    consumer.should.have.key("ConsumerARN")
    consumer.should.have.key("ConsumerStatus").equals("ACTIVE")
    consumer.should.have.key("ConsumerCreationTimestamp")
    consumer.should.have.key("StreamARN").equals(stream_arn)


@mock_kinesis
def test_describe_stream_consumer_unknown():
    client = boto3.client("kinesis", region_name="us-east-2")
    create_stream(client)

    with pytest.raises(ClientError) as exc:
        client.describe_stream_consumer(ConsumerARN="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(f"Consumer unknown, account {ACCOUNT_ID} not found.")


@mock_kinesis
def test_deregister_stream_consumer_by_name():
    client = boto3.client("kinesis", region_name="ap-southeast-1")
    stream_arn = create_stream(client)

    client.register_stream_consumer(StreamARN=stream_arn, ConsumerName="consumer1")
    client.register_stream_consumer(StreamARN=stream_arn, ConsumerName="consumer2")

    client.list_stream_consumers(StreamARN=stream_arn)[
        "Consumers"
    ].should.have.length_of(2)

    client.deregister_stream_consumer(StreamARN=stream_arn, ConsumerName="consumer1")

    client.list_stream_consumers(StreamARN=stream_arn)[
        "Consumers"
    ].should.have.length_of(1)


@mock_kinesis
def test_deregister_stream_consumer_by_arn():
    client = boto3.client("kinesis", region_name="ap-southeast-1")
    stream_arn = create_stream(client)

    resp = client.register_stream_consumer(
        StreamARN=stream_arn, ConsumerName="consumer1"
    )
    consumer1_arn = resp["Consumer"]["ConsumerARN"]
    client.register_stream_consumer(StreamARN=stream_arn, ConsumerName="consumer2")

    client.list_stream_consumers(StreamARN=stream_arn)[
        "Consumers"
    ].should.have.length_of(2)

    client.deregister_stream_consumer(ConsumerARN=consumer1_arn)

    client.list_stream_consumers(StreamARN=stream_arn)[
        "Consumers"
    ].should.have.length_of(1)
