import boto3

from moto import mock_kinesis


@mock_kinesis
def test_enable_encryption():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)

    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    desc.should.have.key("EncryptionType").should.equal("NONE")
    desc.shouldnt.have.key("KeyId")

    client.start_stream_encryption(
        StreamName="my-stream", EncryptionType="KMS", KeyId="n/a"
    )

    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    desc.should.have.key("EncryptionType").should.equal("KMS")
    desc.should.have.key("KeyId").equals("n/a")


@mock_kinesis
def test_disable_encryption():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)

    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    desc.should.have.key("EncryptionType").should.equal("NONE")

    client.start_stream_encryption(
        StreamName="my-stream", EncryptionType="KMS", KeyId="n/a"
    )

    client.stop_stream_encryption(
        StreamName="my-stream", EncryptionType="KMS", KeyId="n/a"
    )

    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    desc.should.have.key("EncryptionType").should.equal("NONE")
    desc.shouldnt.have.key("KeyId")
