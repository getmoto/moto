import json

from moto.core.responses import BaseResponse
from .models import kinesis_backends, KinesisBackend


class KinesisResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="kinesis")

    @property
    def parameters(self):
        return json.loads(self.body)

    @property
    def kinesis_backend(self) -> KinesisBackend:
        return kinesis_backends[self.current_account][self.region]

    def create_stream(self):
        stream_name = self.parameters.get("StreamName")
        shard_count = self.parameters.get("ShardCount")
        stream_mode = self.parameters.get("StreamModeDetails")
        self.kinesis_backend.create_stream(
            stream_name, shard_count, stream_mode=stream_mode
        )
        return ""

    def describe_stream(self):
        stream_name = self.parameters.get("StreamName")
        stream_arn = self.parameters.get("StreamARN")
        limit = self.parameters.get("Limit")
        stream = self.kinesis_backend.describe_stream(stream_arn, stream_name)
        return json.dumps(stream.to_json(shard_limit=limit))

    def describe_stream_summary(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        stream = self.kinesis_backend.describe_stream_summary(stream_arn, stream_name)
        return json.dumps(stream.to_json_summary())

    def list_streams(self):
        streams = self.kinesis_backend.list_streams()
        stream_names = [stream.stream_name for stream in streams]
        max_streams = self._get_param("Limit", 10)
        try:
            token = self.parameters.get("ExclusiveStartStreamName")
        except ValueError:
            token = self._get_param("ExclusiveStartStreamName")
        if token:
            start = stream_names.index(token) + 1
        else:
            start = 0
        streams_resp = stream_names[start : start + max_streams]
        has_more_streams = False
        if start + max_streams < len(stream_names):
            has_more_streams = True

        return json.dumps(
            {"HasMoreStreams": has_more_streams, "StreamNames": streams_resp}
        )

    def delete_stream(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        self.kinesis_backend.delete_stream(stream_arn, stream_name)
        return ""

    def get_shard_iterator(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        shard_id = self.parameters.get("ShardId")
        shard_iterator_type = self.parameters.get("ShardIteratorType")
        starting_sequence_number = self.parameters.get("StartingSequenceNumber")
        at_timestamp = self.parameters.get("Timestamp")

        shard_iterator = self.kinesis_backend.get_shard_iterator(
            stream_arn,
            stream_name,
            shard_id,
            shard_iterator_type,
            starting_sequence_number,
            at_timestamp,
        )

        return json.dumps({"ShardIterator": shard_iterator})

    def get_records(self):
        stream_arn = self.parameters.get("StreamARN")
        shard_iterator = self.parameters.get("ShardIterator")
        limit = self.parameters.get("Limit")

        (
            next_shard_iterator,
            records,
            millis_behind_latest,
        ) = self.kinesis_backend.get_records(stream_arn, shard_iterator, limit)

        return json.dumps(
            {
                "NextShardIterator": next_shard_iterator,
                "Records": [record.to_json() for record in records],
                "MillisBehindLatest": millis_behind_latest,
            }
        )

    def put_record(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        partition_key = self.parameters.get("PartitionKey")
        explicit_hash_key = self.parameters.get("ExplicitHashKey")
        data = self.parameters.get("Data")

        sequence_number, shard_id = self.kinesis_backend.put_record(
            stream_arn,
            stream_name,
            partition_key,
            explicit_hash_key,
            data,
        )

        return json.dumps({"SequenceNumber": sequence_number, "ShardId": shard_id})

    def put_records(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        records = self.parameters.get("Records")

        response = self.kinesis_backend.put_records(stream_arn, stream_name, records)

        return json.dumps(response)

    def split_shard(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        shard_to_split = self.parameters.get("ShardToSplit")
        new_starting_hash_key = self.parameters.get("NewStartingHashKey")
        self.kinesis_backend.split_shard(
            stream_arn, stream_name, shard_to_split, new_starting_hash_key
        )
        return ""

    def merge_shards(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        shard_to_merge = self.parameters.get("ShardToMerge")
        adjacent_shard_to_merge = self.parameters.get("AdjacentShardToMerge")
        self.kinesis_backend.merge_shards(
            stream_arn, stream_name, shard_to_merge, adjacent_shard_to_merge
        )
        return ""

    def list_shards(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        next_token = self.parameters.get("NextToken")
        max_results = self.parameters.get("MaxResults", 10000)
        shards, token = self.kinesis_backend.list_shards(
            stream_arn=stream_arn,
            stream_name=stream_name,
            limit=max_results,
            next_token=next_token,
        )
        res = {"Shards": shards}
        if token:
            res["NextToken"] = token
        return json.dumps(res)

    def update_shard_count(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        target_shard_count = self.parameters.get("TargetShardCount")
        current_shard_count = self.kinesis_backend.update_shard_count(
            stream_arn=stream_arn,
            stream_name=stream_name,
            target_shard_count=target_shard_count,
        )
        return json.dumps(
            dict(
                StreamName=stream_name,
                CurrentShardCount=current_shard_count,
                TargetShardCount=target_shard_count,
            )
        )

    def increase_stream_retention_period(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        retention_period_hours = self.parameters.get("RetentionPeriodHours")
        self.kinesis_backend.increase_stream_retention_period(
            stream_arn, stream_name, retention_period_hours
        )
        return ""

    def decrease_stream_retention_period(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        retention_period_hours = self.parameters.get("RetentionPeriodHours")
        self.kinesis_backend.decrease_stream_retention_period(
            stream_arn, stream_name, retention_period_hours
        )
        return ""

    def add_tags_to_stream(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        tags = self.parameters.get("Tags")
        self.kinesis_backend.add_tags_to_stream(stream_arn, stream_name, tags)
        return json.dumps({})

    def list_tags_for_stream(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        exclusive_start_tag_key = self.parameters.get("ExclusiveStartTagKey")
        limit = self.parameters.get("Limit")
        response = self.kinesis_backend.list_tags_for_stream(
            stream_arn, stream_name, exclusive_start_tag_key, limit
        )
        return json.dumps(response)

    def remove_tags_from_stream(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        tag_keys = self.parameters.get("TagKeys")
        self.kinesis_backend.remove_tags_from_stream(stream_arn, stream_name, tag_keys)
        return json.dumps({})

    def enable_enhanced_monitoring(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        shard_level_metrics = self.parameters.get("ShardLevelMetrics")
        arn, name, current, desired = self.kinesis_backend.enable_enhanced_monitoring(
            stream_arn=stream_arn,
            stream_name=stream_name,
            shard_level_metrics=shard_level_metrics,
        )
        return json.dumps(
            dict(
                StreamName=name,
                CurrentShardLevelMetrics=current,
                DesiredShardLevelMetrics=desired,
                StreamARN=arn,
            )
        )

    def disable_enhanced_monitoring(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        shard_level_metrics = self.parameters.get("ShardLevelMetrics")
        arn, name, current, desired = self.kinesis_backend.disable_enhanced_monitoring(
            stream_arn=stream_arn,
            stream_name=stream_name,
            to_be_disabled=shard_level_metrics,
        )
        return json.dumps(
            dict(
                StreamName=name,
                CurrentShardLevelMetrics=current,
                DesiredShardLevelMetrics=desired,
                StreamARN=arn,
            )
        )

    def list_stream_consumers(self):
        stream_arn = self.parameters.get("StreamARN")
        consumers = self.kinesis_backend.list_stream_consumers(stream_arn=stream_arn)
        return json.dumps(dict(Consumers=[c.to_json() for c in consumers]))

    def register_stream_consumer(self):
        stream_arn = self.parameters.get("StreamARN")
        consumer_name = self.parameters.get("ConsumerName")
        consumer = self.kinesis_backend.register_stream_consumer(
            stream_arn=stream_arn, consumer_name=consumer_name
        )
        return json.dumps(dict(Consumer=consumer.to_json()))

    def describe_stream_consumer(self):
        stream_arn = self.parameters.get("StreamARN")
        consumer_name = self.parameters.get("ConsumerName")
        consumer_arn = self.parameters.get("ConsumerARN")
        consumer = self.kinesis_backend.describe_stream_consumer(
            stream_arn=stream_arn,
            consumer_name=consumer_name,
            consumer_arn=consumer_arn,
        )
        return json.dumps(
            dict(ConsumerDescription=consumer.to_json(include_stream_arn=True))
        )

    def deregister_stream_consumer(self):
        stream_arn = self.parameters.get("StreamARN")
        consumer_name = self.parameters.get("ConsumerName")
        consumer_arn = self.parameters.get("ConsumerARN")
        self.kinesis_backend.deregister_stream_consumer(
            stream_arn=stream_arn,
            consumer_name=consumer_name,
            consumer_arn=consumer_arn,
        )
        return json.dumps(dict())

    def start_stream_encryption(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        encryption_type = self.parameters.get("EncryptionType")
        key_id = self.parameters.get("KeyId")
        self.kinesis_backend.start_stream_encryption(
            stream_arn=stream_arn,
            stream_name=stream_name,
            encryption_type=encryption_type,
            key_id=key_id,
        )
        return json.dumps(dict())

    def stop_stream_encryption(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_name = self.parameters.get("StreamName")
        self.kinesis_backend.stop_stream_encryption(
            stream_arn=stream_arn, stream_name=stream_name
        )
        return json.dumps(dict())

    def update_stream_mode(self):
        stream_arn = self.parameters.get("StreamARN")
        stream_mode = self.parameters.get("StreamModeDetails")
        self.kinesis_backend.update_stream_mode(stream_arn, stream_mode)
        return "{}"
