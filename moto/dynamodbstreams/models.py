from __future__ import unicode_literals

import os
import json
import boto3
import base64
import datetime

from moto.core import BaseBackend, BaseModel
from moto.dynamodb2.models import dynamodb_backends


class ShardIterator(BaseModel):
    def __init__(self, stream_shard, shard_iterator_type, sequence_number=None):
        self.id = base64.b64encode(os.urandom(472)).decode('utf-8')
        self.stream_shard = stream_shard
        self.shard_iterator_type = shard_iterator_type
        if shard_iterator_type == 'TRIM_HORIZON':
            self.sequence_number = stream_shard.starting_sequence_number
        elif shard_iterator_type == 'LATEST':
            self.sequence_number = stream_shard.starting_sequence_number + len(stream_shard.items)
        elif shard_iterator_type == 'AT_SEQUENCE_NUMBER':
            self.sequence_number = sequence_number
        elif shard_iterator_type == 'AFTER_SEQUENCE_NUMBER':
            self.sequence_number = sequence_number + 1

    def to_json(self):
        return {
            'ShardIterator': '{}/stream/{}|1|{}'.format(
                self.stream_shard.table.table_arn,
                self.stream_shard.table.latest_stream_label,
                self.id)
        }


class DynamoDBStreamsBackend(BaseBackend):
    def __init__(self, region):
        self.region = region

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)
        
    @property
    def dynamodb(self):
        return dynamodb_backends[self.region]

    def _get_table_from_arn(self, arn):
        table_name = arn.split(':', 6)[5].split('/')[1]
        return self.dynamodb.get_table(table_name)
    
    def describe_stream(self, arn):
        table = self._get_table_from_arn(arn)
        resp = {'StreamDescription': {
            'StreamArn': arn,
            'StreamLabel': table.latest_stream_label,
            'StreamStatus': ('ENABLED' if table.latest_stream_label
                             else 'DISABLED'),
            'StreamViewType': table.stream_specification['StreamViewType'],
            'CreationRequestDateTime': table.stream_shard.created_on.isoformat(),
            'TableName': table.name,
            'KeySchema': table.schema,
            'Shards': ([table.stream_shard.to_json()] if table.stream_shard
                       else [])
        }}
        
        return json.dumps(resp)

    def list_streams(self, table_name=None):
        streams = []
        for table in self.dynamodb.tables.values():
            if table_name is not None and table.name != table_name:
                continue
            if table.latest_stream_label:
                d = table.describe(base_key='Table')
                streams.append({
                    'StreamArn': d['Table']['LatestStreamArn'],
                    'TableName': d['Table']['TableName'],
                    'StreamLabel': d['Table']['LatestStreamLabel']
                })
                
        return json.dumps({'Streams': streams})

    def get_shard_iterator(self, arn, shard_id, shard_iterator_type, sequence_number=None):
        table = self._get_table_from_arn(arn)
        assert table.stream_shard.id == shard_id

        shard_iterator = ShardIterator(table.stream_shard, shard_iterator_type,
                                       sequence_number)
        
        return json.dumps(shard_iterator.to_json())

    

available_regions = boto3.session.Session().get_available_regions(
    'dynamodbstreams')
dynamodbstreams_backends = {region: DynamoDBStreamsBackend(region=region)
                            for region in available_regions}
