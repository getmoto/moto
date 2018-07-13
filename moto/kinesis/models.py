from __future__ import unicode_literals

import datetime
import time
import boto.kinesis
import re
import six
import itertools

from operator import attrgetter
from hashlib import md5

from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import unix_time
from .exceptions import StreamNotFoundError, ShardNotFoundError, ResourceInUseError, \
    ResourceNotFoundError, InvalidArgumentError
from .utils import compose_shard_iterator, compose_new_shard_iterator, decompose_shard_iterator


class Record(BaseModel):
    def __init__(self, partition_key, data, sequence_number, explicit_hash_key):
        self.partition_key = partition_key
        self.data = data
        self.sequence_number = sequence_number
        self.explicit_hash_key = explicit_hash_key
        self.created_at_datetime = datetime.datetime.utcnow()
        self.created_at = unix_time(self.created_at_datetime)

    def to_json(self):
        return {
            "Data": self.data,
            "PartitionKey": self.partition_key,
            "SequenceNumber": str(self.sequence_number),
            "ApproximateArrivalTimestamp": self.created_at_datetime.isoformat()
        }


class Shard(BaseModel):

    def __init__(self, shard_id, starting_hash, ending_hash):
        self._shard_id = shard_id
        self.starting_hash = starting_hash
        self.ending_hash = ending_hash
        self.records = OrderedDict()

    @property
    def shard_id(self):
        return "shardId-{0}".format(str(self._shard_id).zfill(12))

    def get_records(self, last_sequence_id, limit):
        last_sequence_id = int(last_sequence_id)
        results = []
        secs_behind_latest = 0

        for sequence_number, record in self.records.items():
            if sequence_number > last_sequence_id:
                results.append(record)
                last_sequence_id = sequence_number

                very_last_record = self.records[next(reversed(self.records))]
                secs_behind_latest = very_last_record.created_at - record.created_at

            if len(results) == limit:
                break

        millis_behind_latest = int(secs_behind_latest * 1000)
        return results, last_sequence_id, millis_behind_latest

    def put_record(self, partition_key, data, explicit_hash_key):
        # Note: this function is not safe for concurrency
        if self.records:
            last_sequence_number = self.get_max_sequence_number()
        else:
            last_sequence_number = 0
        sequence_number = last_sequence_number + 1
        self.records[sequence_number] = Record(
            partition_key, data, sequence_number, explicit_hash_key)
        return sequence_number

    def get_min_sequence_number(self):
        if self.records:
            return list(self.records.keys())[0]
        return 0

    def get_max_sequence_number(self):
        if self.records:
            return list(self.records.keys())[-1]
        return 0

    def get_sequence_number_at(self, at_timestamp):
        if not self.records or at_timestamp < list(self.records.values())[0].created_at:
            return 0
        else:
            # find the last item in the list that was created before
            # at_timestamp
            r = next((r for r in reversed(self.records.values()) if r.created_at < at_timestamp), None)
            return r.sequence_number

    def to_json(self):
        return {
            "HashKeyRange": {
                "EndingHashKey": str(self.ending_hash),
                "StartingHashKey": str(self.starting_hash)
            },
            "SequenceNumberRange": {
                "EndingSequenceNumber": self.get_max_sequence_number(),
                "StartingSequenceNumber": self.get_min_sequence_number(),
            },
            "ShardId": self.shard_id
        }


class Stream(BaseModel):

    def __init__(self, stream_name, shard_count, region):
        self.stream_name = stream_name
        self.shard_count = shard_count
        self.region = region
        self.account_number = "123456789012"
        self.shards = {}
        self.tags = {}

        if six.PY3:
            izip_longest = itertools.zip_longest
        else:
            izip_longest = itertools.izip_longest

        for index, start, end in izip_longest(range(shard_count),
                                              range(0, 2**128, 2 **
                                                    128 // shard_count),
                                              range(2**128 // shard_count, 2 **
                                                    128, 2**128 // shard_count),
                                              fillvalue=2**128):
            shard = Shard(index, start, end)
            self.shards[shard.shard_id] = shard

    @property
    def arn(self):
        return "arn:aws:kinesis:{region}:{account_number}:{stream_name}".format(
            region=self.region,
            account_number=self.account_number,
            stream_name=self.stream_name
        )

    def get_shard(self, shard_id):
        if shard_id in self.shards:
            return self.shards[shard_id]
        else:
            raise ShardNotFoundError(shard_id)

    def get_shard_for_key(self, partition_key, explicit_hash_key):
        if not isinstance(partition_key, six.string_types):
            raise InvalidArgumentError("partition_key")
        if len(partition_key) > 256:
            raise InvalidArgumentError("partition_key")

        if explicit_hash_key:
            if not isinstance(explicit_hash_key, six.string_types):
                raise InvalidArgumentError("explicit_hash_key")

            key = int(explicit_hash_key)

            if key >= 2**128:
                raise InvalidArgumentError("explicit_hash_key")

        else:
            key = int(md5(partition_key.encode('utf-8')).hexdigest(), 16)

        for shard in self.shards.values():
            if shard.starting_hash <= key < shard.ending_hash:
                return shard

    def put_record(self, partition_key, explicit_hash_key, sequence_number_for_ordering, data):
        shard = self.get_shard_for_key(partition_key, explicit_hash_key)

        sequence_number = shard.put_record(
            partition_key, data, explicit_hash_key)
        return sequence_number, shard.shard_id

    def to_json(self):
        return {
            "StreamDescription": {
                "StreamARN": self.arn,
                "StreamName": self.stream_name,
                "StreamStatus": "ACTIVE",
                "HasMoreShards": False,
                "Shards": [shard.to_json() for shard in self.shards.values()],
            }
        }

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        region = properties.get('Region', 'us-east-1')
        shard_count = properties.get('ShardCount', 1)
        return Stream(properties['Name'], shard_count, region)


class FirehoseRecord(BaseModel):

    def __init__(self, record_data):
        self.record_id = 12345678
        self.record_data = record_data


class DeliveryStream(BaseModel):

    def __init__(self, stream_name, **stream_kwargs):
        self.name = stream_name
        self.redshift_username = stream_kwargs.get('redshift_username')
        self.redshift_password = stream_kwargs.get('redshift_password')
        self.redshift_jdbc_url = stream_kwargs.get('redshift_jdbc_url')
        self.redshift_role_arn = stream_kwargs.get('redshift_role_arn')
        self.redshift_copy_command = stream_kwargs.get('redshift_copy_command')

        self.s3_role_arn = stream_kwargs.get('s3_role_arn')
        self.s3_bucket_arn = stream_kwargs.get('s3_bucket_arn')
        self.s3_prefix = stream_kwargs.get('s3_prefix')
        self.s3_compression_format = stream_kwargs.get(
            's3_compression_format', 'UNCOMPRESSED')
        self.s3_buffering_hings = stream_kwargs.get('s3_buffering_hings')

        self.redshift_s3_role_arn = stream_kwargs.get('redshift_s3_role_arn')
        self.redshift_s3_bucket_arn = stream_kwargs.get(
            'redshift_s3_bucket_arn')
        self.redshift_s3_prefix = stream_kwargs.get('redshift_s3_prefix')
        self.redshift_s3_compression_format = stream_kwargs.get(
            'redshift_s3_compression_format', 'UNCOMPRESSED')
        self.redshift_s3_buffering_hings = stream_kwargs.get(
            'redshift_s3_buffering_hings')

        self.records = []
        self.status = 'ACTIVE'
        self.created_at = datetime.datetime.utcnow()
        self.last_updated = datetime.datetime.utcnow()

    @property
    def arn(self):
        return 'arn:aws:firehose:us-east-1:123456789012:deliverystream/{0}'.format(self.name)

    def destinations_to_dict(self):
        if self.s3_role_arn:
            return [{
                'DestinationId': 'string',
                'S3DestinationDescription': {
                    'RoleARN': self.s3_role_arn,
                    'BucketARN': self.s3_bucket_arn,
                    'Prefix': self.s3_prefix,
                    'BufferingHints': self.s3_buffering_hings,
                    'CompressionFormat': self.s3_compression_format,
                }
            }]
        else:
            return [{
                    "DestinationId": "string",
                    "RedshiftDestinationDescription": {
                        "ClusterJDBCURL": self.redshift_jdbc_url,
                        "CopyCommand": self.redshift_copy_command,
                        "RoleARN": self.redshift_role_arn,
                        "S3DestinationDescription": {
                            "BucketARN": self.redshift_s3_bucket_arn,
                            "BufferingHints": self.redshift_s3_buffering_hings,
                            "CompressionFormat": self.redshift_s3_compression_format,
                            "Prefix": self.redshift_s3_prefix,
                            "RoleARN": self.redshift_s3_role_arn
                        },
                        "Username": self.redshift_username,
                    },
                    }
                    ]

    def to_dict(self):
        return {
            "DeliveryStreamDescription": {
                "CreateTimestamp": time.mktime(self.created_at.timetuple()),
                "DeliveryStreamARN": self.arn,
                "DeliveryStreamName": self.name,
                "DeliveryStreamStatus": self.status,
                "Destinations": self.destinations_to_dict(),
                "HasMoreDestinations": False,
                "LastUpdateTimestamp": time.mktime(self.last_updated.timetuple()),
                "VersionId": "string",
            }
        }

    def put_record(self, record_data):
        record = FirehoseRecord(record_data)
        self.records.append(record)
        return record


class KinesisBackend(BaseBackend):

    def __init__(self):
        self.streams = OrderedDict()
        self.delivery_streams = {}

    def create_stream(self, stream_name, shard_count, region):
        if stream_name in self.streams:
            raise ResourceInUseError(stream_name)
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

    def get_shard_iterator(self, stream_name, shard_id, shard_iterator_type, starting_sequence_number,
                           at_timestamp):
        # Validate params
        stream = self.describe_stream(stream_name)
        shard = stream.get_shard(shard_id)

        shard_iterator = compose_new_shard_iterator(
            stream_name, shard, shard_iterator_type, starting_sequence_number, at_timestamp
        )
        return shard_iterator

    def get_records(self, shard_iterator, limit):
        decomposed = decompose_shard_iterator(shard_iterator)
        stream_name, shard_id, last_sequence_id = decomposed

        stream = self.describe_stream(stream_name)
        shard = stream.get_shard(shard_id)

        records, last_sequence_id, millis_behind_latest = shard.get_records(last_sequence_id, limit)

        next_shard_iterator = compose_shard_iterator(
            stream_name, shard, last_sequence_id)

        return next_shard_iterator, records, millis_behind_latest

    def put_record(self, stream_name, partition_key, explicit_hash_key, sequence_number_for_ordering, data):
        stream = self.describe_stream(stream_name)

        sequence_number, shard_id = stream.put_record(
            partition_key, explicit_hash_key, sequence_number_for_ordering, data
        )

        return sequence_number, shard_id

    def put_records(self, stream_name, records):
        stream = self.describe_stream(stream_name)

        response = {
            "FailedRecordCount": 0,
            "Records": []
        }

        for record in records:
            partition_key = record.get("PartitionKey")
            explicit_hash_key = record.get("ExplicitHashKey")
            data = record.get("Data")

            sequence_number, shard_id = stream.put_record(
                partition_key, explicit_hash_key, None, data
            )
            response['Records'].append({
                "SequenceNumber": sequence_number,
                "ShardId": shard_id
            })

        return response

    def split_shard(self, stream_name, shard_to_split, new_starting_hash_key):
        stream = self.describe_stream(stream_name)

        if shard_to_split not in stream.shards:
            raise ResourceNotFoundError(shard_to_split)

        if not re.match(r'0|([1-9]\d{0,38})', new_starting_hash_key):
            raise InvalidArgumentError(new_starting_hash_key)
        new_starting_hash_key = int(new_starting_hash_key)

        shard = stream.shards[shard_to_split]

        last_id = sorted(stream.shards.values(),
                         key=attrgetter('_shard_id'))[-1]._shard_id

        if shard.starting_hash < new_starting_hash_key < shard.ending_hash:
            new_shard = Shard(
                last_id + 1, new_starting_hash_key, shard.ending_hash)
            shard.ending_hash = new_starting_hash_key
            stream.shards[new_shard.shard_id] = new_shard
        else:
            raise InvalidArgumentError(new_starting_hash_key)

        records = shard.records
        shard.records = OrderedDict()

        for index in records:
            record = records[index]
            stream.put_record(
                record.partition_key, record.explicit_hash_key, None, record.data
            )

    def merge_shards(self, stream_name, shard_to_merge, adjacent_shard_to_merge):
        stream = self.describe_stream(stream_name)

        if shard_to_merge not in stream.shards:
            raise ResourceNotFoundError(shard_to_merge)

        if adjacent_shard_to_merge not in stream.shards:
            raise ResourceNotFoundError(adjacent_shard_to_merge)

        shard1 = stream.shards[shard_to_merge]
        shard2 = stream.shards[adjacent_shard_to_merge]

        if shard1.ending_hash == shard2.starting_hash:
            shard1.ending_hash = shard2.ending_hash
        elif shard2.ending_hash == shard1.starting_hash:
            shard1.starting_hash = shard2.starting_hash
        else:
            raise InvalidArgumentError(adjacent_shard_to_merge)

        del stream.shards[shard2.shard_id]
        for index in shard2.records:
            record = shard2.records[index]
            shard1.put_record(record.partition_key,
                              record.data, record.explicit_hash_key)

    ''' Firehose '''

    def create_delivery_stream(self, stream_name, **stream_kwargs):
        stream = DeliveryStream(stream_name, **stream_kwargs)
        self.delivery_streams[stream_name] = stream
        return stream

    def get_delivery_stream(self, stream_name):
        if stream_name in self.delivery_streams:
            return self.delivery_streams[stream_name]
        else:
            raise StreamNotFoundError(stream_name)

    def list_delivery_streams(self):
        return self.delivery_streams.values()

    def delete_delivery_stream(self, stream_name):
        self.delivery_streams.pop(stream_name)

    def put_firehose_record(self, stream_name, record_data):
        stream = self.get_delivery_stream(stream_name)
        record = stream.put_record(record_data)
        return record

    def list_tags_for_stream(self, stream_name, exclusive_start_tag_key=None, limit=None):
        stream = self.describe_stream(stream_name)

        tags = []
        result = {
            'HasMoreTags': False,
            'Tags': tags
        }
        for key, val in sorted(stream.tags.items(), key=lambda x: x[0]):
            if limit and len(tags) >= limit:
                result['HasMoreTags'] = True
                break
            if exclusive_start_tag_key and key < exclusive_start_tag_key:
                continue

            tags.append({
                'Key': key,
                'Value': val
            })

        return result

    def add_tags_to_stream(self, stream_name, tags):
        stream = self.describe_stream(stream_name)
        stream.tags.update(tags)

    def remove_tags_from_stream(self, stream_name, tag_keys):
        stream = self.describe_stream(stream_name)
        for key in tag_keys:
            if key in stream.tags:
                del stream.tags[key]


kinesis_backends = {}
for region in boto.kinesis.regions():
    kinesis_backends[region.name] = KinesisBackend()
