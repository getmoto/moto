import boto

from freezegun import freeze_time

from moto import mock_dynamodb
from moto.dynamodb import dynamodb_backend

from boto.exception import DynamoDBResponseError


@mock_dynamodb
def test_list_tables():
    name = 'TestTable'
    dynamodb_backend.create_table(name)
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    assert conn.list_tables() == ['TestTable']


@mock_dynamodb
def test_describe_missing_table():
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    conn.describe_table.when.called_with('messages').should.throw(DynamoDBResponseError)


@freeze_time("2012-01-14")
@mock_dynamodb
def test_describe_table():
    dynamodb_backend.create_table(
        'messages',
        hash_key_attr='forum_name',
        hash_key_type='S',
        range_key_attr='subject',
        range_key_type='S',
        read_capacity=10,
        write_capacity=10,
    )
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    expected = {
        'Table': {
            'CreationDateTime': 1326499200.0,
            'ItemCount': 0,
            'KeySchema': {
                'HashKeyElement': {
                    'AttributeName': 'forum_name',
                    'AttributeType': 'S'
                },
                'RangeKeyElement': {
                    'AttributeName': 'subject',
                    'AttributeType': 'S'
                }
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            },
            'TableName': 'messages',
            'TableSizeBytes': 0,
            'TableStatus': 'ACTIVE'
        }
    }
    assert conn.describe_table('messages') == expected
