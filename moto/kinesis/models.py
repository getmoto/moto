from __future__ import unicode_literals

import boto.kinesis
from moto.core import BaseBackend
from .exceptions import StreamNotFoundError


class Stream(object):
    def __init__(self, stream_name, shard_count, region):
        self.stream_name = stream_name
        self.shard_count = shard_count
        self.region = region
        self.account_number = "123456789012"

    @property
    def arn(self):
        return "arn:aws:kinesis:{region}:{account_number}:{stream_name}".format(
            region=self.region,
            account_number=self.account_number,
            stream_name=self.stream_name
        )

    def to_json(self):
        return {
            "StreamDescription": {
                "StreamARN": self.arn,
                "StreamName": self.stream_name,
                "StreamStatus": "ACTIVE",
                "HasMoreShards": False,
                "Shards": [{
                    "HashKeyRange": {
                        "EndingHashKey": "113427455640312821154458202477256070484",
                        "StartingHashKey": "0"
                    },
                    "SequenceNumberRange": {
                        "EndingSequenceNumber": "21269319989741826081360214168359141376",
                        "StartingSequenceNumber": "21267647932558653966460912964485513216"
                    },
                    "ShardId": "shardId-000000000000"
                }, {
                    "HashKeyRange": {
                        "EndingHashKey": "226854911280625642308916404954512140969",
                        "StartingHashKey": "113427455640312821154458202477256070485"
                    },
                    "SequenceNumberRange": {
                        "StartingSequenceNumber": "21267647932558653966460912964485513217"
                    },
                    "ShardId": "shardId-000000000001"
                }],
            }
        }


class KinesisBackend(BaseBackend):

    def __init__(self):
        self.streams = {}

    def create_stream(self, stream_name, shard_count, region):
        stream = Stream(stream_name, shard_count, region)
        self.streams[stream_name] = stream
        return stream

    def describe_stream(self, stream_name):
        if stream_name in self.streams:
            return self.streams[stream_name]
        else:
            raise StreamNotFoundError(stream_name)

    def list_streams(self):
        return self.streams.values()

    def delete_stream(self, stream_name):
        if stream_name in self.streams:
            return self.streams.pop(stream_name)
        raise StreamNotFoundError(stream_name)


kinesis_backends = {}
for region in boto.kinesis.regions():
    kinesis_backends[region.name] = KinesisBackend()
