from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_kinesisvideo
import json


@mock_kinesisvideo
def test_list():
    client = boto3.client("kinesisvideo")
    stream_name = "my-stream"
    device_name = "random-device"

    # stream can be created
    res = client.create_stream(StreamName=stream_name, DeviceName=device_name)
    res.should.have.key("StreamARN").which.should.contain(stream_name)

    # stream can be described
    res = client.describe_stream(StreamName=stream_name)
    res.should.have.key("StreamInfo")
    stream_info = res["StreamInfo"]
    stream_info.should.have.key("StreamARN").which.should.contain(stream_name)
    stream_info.should.have.key("StreamName").which.should.equal(stream_name)
    stream_info.should.have.key("DeviceName").which.should.equal(device_name)

    stream_name_2 = "my-stream-2"
    res = client.create_stream(StreamName=stream_name_2, DeviceName=device_name)
    stream_2_arn = res["StreamARN"]

    # streams can be listed
    res = client.list_streams()
    res.should.have.key("StreamInfoList")
    streams = res["StreamInfoList"]
    streams.should.have.length_of(2)

    # stream can be deleted
    client.delete_stream(StreamARN=stream_2_arn)
    res = client.list_streams()
    streams = res["StreamInfoList"]
    streams.should.have.length_of(1)
