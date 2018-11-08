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
                
    def test_get_records_empty(self):
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
        assert len(resp['Records']) == 0

    def test_get_records_seq(self):
        conn = boto3.client('dynamodb', region_name='us-east-1')

        conn.put_item(
            TableName='test-streams',
            Item={
                'id': {'S': 'entry1'},
                'first_col': {'S': 'foo'}
            }
        )
        conn.put_item(
            TableName='test-streams',
            Item={
                'id': {'S': 'entry1'},
                'first_col': {'S': 'bar'},
                'second_col': {'S': 'baz'}
            }
        )
        conn.delete_item(
            TableName='test-streams',
            Key={'id': {'S': 'entry1'}}
        )
        
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
        assert len(resp['Records']) == 3
        assert resp['Records'][0]['eventName'] == 'INSERT'
        assert resp['Records'][1]['eventName'] == 'MODIFY'
        assert resp['Records'][2]['eventName'] == 'DELETE'

        # now try fetching from the next shard iterator, it should be
        # empty
        resp = conn.get_records(ShardIterator=resp['NextShardIterator'])
        assert len(resp['Records']) == 0
