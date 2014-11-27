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

    def get_shard_iterator(self):
        stream_name = self.parameters.get("StreamName")
        shard_id = self.parameters.get("ShardId")
        shard_iterator_type = self.parameters.get("ShardIteratorType")
        starting_sequence_number = self.parameters.get("StartingSequenceNumber")

        shard_iterator = self.kinesis_backend.get_shard_iterator(
            stream_name, shard_id, shard_iterator_type, starting_sequence_number,
        )

        return json.dumps({
            "ShardIterator": shard_iterator
        })

    def get_records(self):
        shard_iterator = self.parameters.get("ShardIterator")
        limit = self.parameters.get("Limit")

        next_shard_iterator, records = self.kinesis_backend.get_records(shard_iterator, limit)

        return json.dumps({
            "NextShardIterator": next_shard_iterator,
            "Records": [record.to_json() for record in records]
        })

    def put_record(self):
        stream_name = self.parameters.get("StreamName")
        partition_key = self.parameters.get("PartitionKey")
        explicit_hash_key = self.parameters.get("ExplicitHashKey")
        sequence_number_for_ordering = self.parameters.get("SequenceNumberForOrdering")
        data = self.parameters.get("Data")

        sequence_number, shard_id = self.kinesis_backend.put_record(
            stream_name, partition_key, explicit_hash_key, sequence_number_for_ordering, data
        )

        return json.dumps({
            "SequenceNumber": sequence_number,
            "ShardId": shard_id,
        })
