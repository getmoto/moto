from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import kinesis_backends


class KinesisResponse(BaseResponse):

    @property
    def parameters(self):
        return json.loads(self.body.decode("utf-8"))

    @property
    def kinesis_backend(self):
        return kinesis_backends[self.region]

    def create_stream(self):
        stream_name = self.parameters.get('StreamName')
        shard_count = self.parameters.get('ShardCount')
        self.kinesis_backend.create_stream(stream_name, shard_count, self.region)
        return ""

    def describe_stream(self):
        stream_name = self.parameters.get('StreamName')
        stream = self.kinesis_backend.describe_stream(stream_name)
        return json.dumps(stream.to_json())

    def list_streams(self):
        streams = self.kinesis_backend.list_streams()

        return json.dumps({
            "HasMoreStreams": False,
            "StreamNames": [stream.stream_name for stream in streams],
        })

    def delete_stream(self):
        stream_name = self.parameters.get("StreamName")
        self.kinesis_backend.delete_stream(stream_name)

        return ""
