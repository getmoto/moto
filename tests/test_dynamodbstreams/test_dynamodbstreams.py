from __future__ import unicode_literals, print_function

import boto3
from moto import mock_dynamodb2, mock_dynamodbstreams


class TestClass():
    stream_arn = None
    mocks = []
    
    def setup(self):
        self.mocks = [mock_dynamodb2(), mock_dynamodbstreams()]
        for m in self.mocks:
            m.start()
            
        # create a table with a stream
        conn = boto3.client('dynamodb', region_name='us-east-1')

        resp = conn.create_table(
            TableName='test-streams',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id',
                                   'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 1,
                                   'WriteCapacityUnits': 1},
            StreamSpecification={
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            }
        )
        self.stream_arn = resp['TableDescription']['LatestStreamArn']

    def teardown(self):
        conn = boto3.client('dynamodb', region_name='us-east-1')
        conn.delete_table(TableName='test-streams')
        self.stream_arn = None

        for m in self.mocks:
            m.stop()


    def test_verify_stream(self):
        conn = boto3.client('dynamodb', region_name='us-east-1')
        resp = conn.describe_table(TableName='test-streams')
        assert 'LatestStreamArn' in resp['Table']

    def test_describe_stream(self):
        conn = boto3.client('dynamodbstreams', region_name='us-east-1')

        resp = conn.describe_stream(StreamArn=self.stream_arn)
        assert 'StreamDescription' in resp
        desc = resp['StreamDescription']
        assert desc['StreamArn'] == self.stream_arn
        assert desc['TableName'] == 'test-streams'

    def test_list_streams(self):
        conn = boto3.client('dynamodbstreams', region_name='us-east-1')

        resp = conn.list_streams()
        assert resp['Streams'][0]['StreamArn'] == self.stream_arn

        resp = conn.list_streams(TableName='no-stream')
        assert not resp['Streams']

    def test_get_shard_iterator(self):
        conn = boto3.client('dynamodbstreams', region_name='us-east-1')

        resp = conn.describe_stream(StreamArn=self.stream_arn)
        shard_id = resp['StreamDescription']['Shards'][0]['ShardId']
        
        resp = conn.get_shard_iterator(
            StreamArn=self.stream_arn,
            ShardId=shard_id,
            ShardIteratorType='TRIM_HORIZON'
        )
        assert 'ShardIterator' in resp
                
    def test_get_records(self):
        conn = boto3.client('dynamodbstreams', region_name='us-east-1')

        resp = conn.describe_stream(StreamArn=self.stream_arn)
        shard_id = resp['StreamDescription']['Shards'][0]['ShardId']
        
        resp = conn.get_shard_iterator(
            StreamArn=self.stream_arn,
            ShardId=shard_id,
            ShardIteratorType='TRIM_HORIZON'
        )
        iterator_id = resp['ShardIterator']

        resp = conn.get_records(ShardIterator=iterator_id)
        assert 'Records' in resp

        # TODO: Add tests for inserting records into the stream, and
        # the various stream types
        
