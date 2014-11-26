from __future__ import unicode_literals

import boto.kinesis
from boto.kinesis.exceptions import ResourceNotFoundException
import sure  # noqa

from moto import mock_kinesis


@mock_kinesis
def test_create_cluster():
    conn = boto.kinesis.connect_to_region("us-west-2")

    conn.create_stream("my_stream", 2)

    stream_response = conn.describe_stream("my_stream")

    stream = stream_response["StreamDescription"]
    stream["StreamName"].should.equal("my_stream")
    stream["HasMoreShards"].should.equal(False)
    stream["StreamARN"].should.equal("arn:aws:kinesis:us-west-2:123456789012:my_stream")
    stream["StreamStatus"].should.equal("ACTIVE")

    shards = stream['Shards']
    shards.should.have.length_of(2)


@mock_kinesis
def test_describe_non_existant_stream():
    conn = boto.kinesis.connect_to_region("us-east-1")
    conn.describe_stream.when.called_with("not-a-stream").should.throw(ResourceNotFoundException)


@mock_kinesis
def test_list_and_delete_stream():
    conn = boto.kinesis.connect_to_region("us-west-2")

    conn.create_stream("stream1", 1)
    conn.create_stream("stream2", 1)

    conn.list_streams()['StreamNames'].should.have.length_of(2)

    conn.delete_stream("stream2")

    conn.list_streams()['StreamNames'].should.have.length_of(1)

    # Delete invalid id
    conn.delete_stream.when.called_with("not-a-stream").should.throw(ResourceNotFoundException)
