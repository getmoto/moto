import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest
from moto import mock_kinesisvideo
from botocore.exceptions import ClientError


@mock_kinesisvideo
def test_create_stream():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    device_name = "random-device"

    # stream can be created
    res = client.create_stream(StreamName=stream_name, DeviceName=device_name)
    res.should.have.key("StreamARN").which.should.contain(stream_name)


@mock_kinesisvideo
def test_create_stream_with_same_name():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    device_name = "random-device"

    client.create_stream(StreamName=stream_name, DeviceName=device_name)

    # cannot create with same stream name
    with pytest.raises(ClientError):
        client.create_stream(StreamName=stream_name, DeviceName=device_name)


@mock_kinesisvideo
def test_describe_stream():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    device_name = "random-device"

    res = client.create_stream(StreamName=stream_name, DeviceName=device_name)
    res.should.have.key("StreamARN").which.should.contain(stream_name)
    stream_arn = res["StreamARN"]

    # cannot create with existing stream name
    with pytest.raises(ClientError):
        client.create_stream(StreamName=stream_name, DeviceName=device_name)

    # stream can be described with name
    res = client.describe_stream(StreamName=stream_name)
    res.should.have.key("StreamInfo")
    stream_info = res["StreamInfo"]
    stream_info.should.have.key("StreamARN").which.should.contain(stream_name)
    stream_info.should.have.key("StreamName").which.should.equal(stream_name)
    stream_info.should.have.key("DeviceName").which.should.equal(device_name)

    # stream can be described with arn
    res = client.describe_stream(StreamARN=stream_arn)
    res.should.have.key("StreamInfo")
    stream_info = res["StreamInfo"]
    stream_info.should.have.key("StreamARN").which.should.contain(stream_name)
    stream_info.should.have.key("StreamName").which.should.equal(stream_name)
    stream_info.should.have.key("DeviceName").which.should.equal(device_name)


@mock_kinesisvideo
def test_describe_stream_with_name_not_exist():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name_not_exist = "not-exist-stream"

    # cannot describe with not exist stream name
    with pytest.raises(ClientError):
        client.describe_stream(StreamName=stream_name_not_exist)


@mock_kinesisvideo
def test_list_streams():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    stream_name_2 = "my-stream-2"
    device_name = "random-device"

    client.create_stream(StreamName=stream_name, DeviceName=device_name)
    client.create_stream(StreamName=stream_name_2, DeviceName=device_name)

    # streams can be listed
    res = client.list_streams()
    res.should.have.key("StreamInfoList")
    streams = res["StreamInfoList"]
    streams.should.have.length_of(2)


@mock_kinesisvideo
def test_delete_stream():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    stream_name_2 = "my-stream-2"
    device_name = "random-device"

    client.create_stream(StreamName=stream_name, DeviceName=device_name)
    res = client.create_stream(StreamName=stream_name_2, DeviceName=device_name)
    stream_2_arn = res["StreamARN"]

    # stream can be deleted
    client.delete_stream(StreamARN=stream_2_arn)
    res = client.list_streams()
    streams = res["StreamInfoList"]
    streams.should.have.length_of(1)


@mock_kinesisvideo
def test_delete_stream_with_arn_not_exist():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    stream_name_2 = "my-stream-2"
    device_name = "random-device"

    client.create_stream(StreamName=stream_name, DeviceName=device_name)
    res = client.create_stream(StreamName=stream_name_2, DeviceName=device_name)
    stream_2_arn = res["StreamARN"]

    client.delete_stream(StreamARN=stream_2_arn)

    # cannot delete with not exist stream
    stream_arn_not_exist = stream_2_arn
    with pytest.raises(ClientError):
        client.delete_stream(StreamARN=stream_arn_not_exist)


@mock_kinesisvideo
def test_data_endpoint():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    device_name = "random-device"

    # data-endpoint can be created
    api_name = "GET_MEDIA"
    client.create_stream(StreamName=stream_name, DeviceName=device_name)
    res = client.get_data_endpoint(StreamName=stream_name, APIName=api_name)
    res.should.have.key("DataEndpoint")
