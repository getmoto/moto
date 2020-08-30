from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_kinesisvideo
import json


@mock_kinesisvideo
def test_list():
    client = boto3.client("kinesisvideo")
    stream_name = "my-stream"
    res = client.create_stream(StreamName=stream_name)
    res.should.have.key("StreamARN").which.should.contain(stream_name)
