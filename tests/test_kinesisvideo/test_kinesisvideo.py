import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_stream():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    device_name = "random-device"

    # stream can be created
    res = client.create_stream(StreamName=stream_name, DeviceName=device_name)
    assert stream_name in res["StreamARN"]


@mock_aws
def test_create_stream_with_same_name():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    device_name = "random-device"

    client.create_stream(StreamName=stream_name, DeviceName=device_name)

    # cannot create with same stream name
    with pytest.raises(ClientError):
        client.create_stream(StreamName=stream_name, DeviceName=device_name)


@mock_aws
def test_describe_stream():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    device_name = "random-device"

    res = client.create_stream(StreamName=stream_name, DeviceName=device_name)
    assert stream_name in res["StreamARN"]
    stream_arn = res["StreamARN"]

    # cannot create with existing stream name
    with pytest.raises(ClientError):
        client.create_stream(StreamName=stream_name, DeviceName=device_name)

    # stream can be described with name
    res = client.describe_stream(StreamName=stream_name)
    stream_info = res["StreamInfo"]
    assert stream_name in stream_info["StreamARN"]
    assert stream_info["StreamName"] == stream_name
    assert stream_info["DeviceName"] == device_name

    # stream can be described with arn
    res = client.describe_stream(StreamARN=stream_arn)
    stream_info = res["StreamInfo"]
    assert stream_name in stream_info["StreamARN"]
    assert stream_info["StreamName"] == stream_name
    assert stream_info["DeviceName"] == device_name


@mock_aws
def test_describe_stream_with_name_not_exist():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name_not_exist = "not-exist-stream"

    # cannot describe with not exist stream name
    with pytest.raises(ClientError):
        client.describe_stream(StreamName=stream_name_not_exist)


@mock_aws
def test_list_streams():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    stream_name_2 = "my-stream-2"
    device_name = "random-device"

    client.create_stream(StreamName=stream_name, DeviceName=device_name)
    client.create_stream(StreamName=stream_name_2, DeviceName=device_name)

    # streams can be listed
    res = client.list_streams()
    streams = res["StreamInfoList"]
    assert len(streams) == 2


@mock_aws
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
    assert len(streams) == 1


@mock_aws
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


@mock_aws
def test_data_endpoint():
    client = boto3.client("kinesisvideo", region_name="ap-northeast-1")
    stream_name = "my-stream"
    device_name = "random-device"

    # data-endpoint can be created
    api_name = "GET_MEDIA"
    client.create_stream(StreamName=stream_name, DeviceName=device_name)
    res = client.get_data_endpoint(StreamName=stream_name, APIName=api_name)
    assert "DataEndpoint" in res
