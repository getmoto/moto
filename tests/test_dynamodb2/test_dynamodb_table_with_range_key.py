from __future__ import unicode_literals

from decimal import Decimal

import boto
import boto3
from boto3.dynamodb.conditions import Key
import sure  # noqa
from freezegun import freeze_time
from moto import mock_dynamodb2
from boto.exception import JSONResponseError
from tests.helpers import requires_boto_gte
try:
    from boto.dynamodb2.fields import GlobalAllIndex, HashKey, RangeKey
    from boto.dynamodb2.table import Item, Table
    from boto.dynamodb2.exceptions import ValidationException
    from boto.dynamodb2.exceptions import ConditionalCheckFailedException
except ImportError:
    pass


def create_table():
    table = Table.create('messages', schema=[
        HashKey('forum_name'),
        RangeKey('subject'),
    ], throughput={
        'read': 10,
        'write': 10,
    })
    return table


def iterate_results(res):
    for i in res:
        pass


@requires_boto_gte("2.9")
@mock_dynamodb2
@freeze_time("2012-01-14")
def test_create_table():
    table = create_table()
    expected = {
        'Table': {
            'AttributeDefinitions': [
                {'AttributeName': 'forum_name', 'AttributeType': 'S'},
                {'AttributeName': 'subject', 'AttributeType': 'S'}
            ],
            'ProvisionedThroughput': {
                'NumberOfDecreasesToday': 0, 'WriteCapacityUnits': 10, 'ReadCapacityUnits': 10
            },
            'TableSizeBytes': 0,
            'TableName': 'messages',
            'TableStatus': 'ACTIVE',
            'KeySchema': [
                {'KeyType': 'HASH', 'AttributeName': 'forum_name'},
                {'KeyType': 'RANGE', 'AttributeName': 'subject'}
            ],
            'ItemCount': 0, 'CreationDateTime': 1326499200.0,
            'GlobalSecondaryIndexes': [],
        }
    }
    table.describe().should.equal(expected)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()
    table = create_table()
    conn.list_tables()["TableNames"].should.have.length_of(1)

    table.delete()
    conn.list_tables()["TableNames"].should.have.length_of(0)
    conn.delete_table.when.called_with('messages').should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_update_table_throughput():
    table = create_table()
    table.throughput["read"].should.equal(10)
    table.throughput["write"].should.equal(10)
    table.update(throughput={
        'read': 5,
        'write': 15,
    })

    table.throughput["read"].should.equal(5)
    table.throughput["write"].should.equal(15)

    table.update(throughput={
        'read': 5,
        'write': 6,
    })

    table.describe()

    table.throughput["read"].should.equal(5)
    table.throughput["write"].should.equal(6)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_item_add_and_describe_and_update():
    table = create_table()
    ok = table.put_item(data={
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    })
    ok.should.equal(True)

    table.get_item(forum_name="LOLCat Forum", subject='Check this out!').should_not.be.none

    returned_item = table.get_item(
        forum_name='LOLCat Forum',
        subject='Check this out!'
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    })

    returned_item['SentBy'] = 'User B'
    returned_item.save(overwrite=True)

    returned_item = table.get_item(
        forum_name='LOLCat Forum',
        subject='Check this out!'
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    })


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_item_put_without_table():
    table = Table('undeclared-table')
    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = Item(table, item_data)
    item.save.when.called_with().should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_missing_item():
    table = create_table()

    table.get_item.when.called_with(
        hash_key='tester',
        range_key='other',
    ).should.throw(ValidationException)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_item_with_undeclared_table():
    table = Table('undeclared-table')
    table.get_item.when.called_with(test_hash=3241526475).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_item_without_range_key():
    table = Table.create('messages', schema=[
        HashKey('test_hash'),
        RangeKey('test_range'),
    ], throughput={
        'read': 10,
        'write': 10,
    })

    hash_key = 3241526475
    range_key = 1234567890987
    table.put_item(data={'test_hash': hash_key, 'test_range': range_key})
    table.get_item.when.called_with(test_hash=hash_key).should.throw(ValidationException)


@requires_boto_gte("2.30.0")
@mock_dynamodb2
def test_delete_item():
    table = create_table()
    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = Item(table, item_data)
    item['subject'] = 'Check this out!'
    item.save()
    table.count().should.equal(1)

    response = item.delete()
    response.should.equal(True)

    table.count().should.equal(0)
    item.delete().should.equal(False)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_item_with_undeclared_table():
    table = Table("undeclared-table")
    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = Item(table, item_data)
    item.delete.when.called_with().should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query():
    table = create_table()

    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'subject': 'Check this out!'
    }
    item = Item(table, item_data)
    item.save(overwrite=True)

    item['forum_name'] = 'the-key'
    item['subject'] = '456'
    item.save(overwrite=True)

    item['forum_name'] = 'the-key'
    item['subject'] = '123'
    item.save(overwrite=True)

    item['forum_name'] = 'the-key'
    item['subject'] = '789'
    item.save(overwrite=True)

    table.count().should.equal(4)

    results = table.query_2(forum_name__eq='the-key', subject__gt='1', consistent=True)
    expected = ["123", "456", "789"]
    for index, item in enumerate(results):
        item["subject"].should.equal(expected[index])

    results = table.query_2(forum_name__eq="the-key", subject__gt='1', reverse=True)
    for index, item in enumerate(results):
        item["subject"].should.equal(expected[len(expected) - 1 - index])

    results = table.query_2(forum_name__eq='the-key', subject__gt='1', consistent=True)
    sum(1 for _ in results).should.equal(3)

    results = table.query_2(forum_name__eq='the-key', subject__gt='234', consistent=True)
    sum(1 for _ in results).should.equal(2)

    results = table.query_2(forum_name__eq='the-key', subject__gt='9999')
    sum(1 for _ in results).should.equal(0)

    results = table.query_2(forum_name__eq='the-key', subject__beginswith='12')
    sum(1 for _ in results).should.equal(1)

    results = table.query_2(forum_name__eq='the-key', subject__beginswith='7')
    sum(1 for _ in results).should.equal(1)

    results = table.query_2(forum_name__eq='the-key', subject__between=['567', '890'])
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query_with_undeclared_table():
    table = Table('undeclared')
    results = table.query(
        forum_name__eq='Amazon DynamoDB',
        subject__beginswith='DynamoDB',
        limit=1
    )
    iterate_results.when.called_with(results).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_scan():
    table = create_table()
    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item_data['forum_name'] = 'the-key'
    item_data['subject'] = '456'

    item = Item(table, item_data)
    item.save()

    item['forum_name'] = 'the-key'
    item['subject'] = '123'
    item.save()

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:09 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }

    item_data['forum_name'] = 'the-key'
    item_data['subject'] = '789'

    item = Item(table, item_data)
    item.save()

    results = table.scan()
    sum(1 for _ in results).should.equal(3)

    results = table.scan(SentBy__eq='User B')
    sum(1 for _ in results).should.equal(1)

    results = table.scan(Body__beginswith='http')
    sum(1 for _ in results).should.equal(3)

    results = table.scan(Ids__null=False)
    sum(1 for _ in results).should.equal(1)

    results = table.scan(Ids__null=True)
    sum(1 for _ in results).should.equal(2)

    results = table.scan(PK__between=[8, 9])
    sum(1 for _ in results).should.equal(0)

    results = table.scan(PK__between=[5, 8])
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_scan_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()
    conn.scan.when.called_with(
        table_name='undeclared-table',
        scan_filter={
            "SentBy": {
                "AttributeValueList": [{
                    "S": "User B"}
                ],
                "ComparisonOperator": "EQ"
            }
        },
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_write_batch():
    table = create_table()
    with table.batch_write() as batch:
        batch.put_item(data={
            'forum_name': 'the-key',
            'subject': '123',
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User A',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        })
        batch.put_item(data={
            'forum_name': 'the-key',
            'subject': '789',
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User B',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        })

    table.count().should.equal(2)
    with table.batch_write() as batch:
        batch.delete_item(
            forum_name='the-key',
            subject='789'
        )

    table.count().should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_batch_read():
    table = create_table()
    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }

    item_data['forum_name'] = 'the-key'
    item_data['subject'] = '456'

    item = Item(table, item_data)
    item.save()

    item = Item(table, item_data)
    item_data['forum_name'] = 'the-key'
    item_data['subject'] = '123'
    item.save()

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }
    item = Item(table, item_data)
    item_data['forum_name'] = 'another-key'
    item_data['subject'] = '789'
    item.save()
    results = table.batch_get(
        keys=[
            {'forum_name': 'the-key', 'subject': '123'},
            {'forum_name': 'another-key', 'subject': '789'},
        ]
    )

    # Iterate through so that batch_item gets called
    count = len([x for x in results])
    count.should.equal(2)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_key_fields():
    table = create_table()
    kf = table.get_key_fields()
    kf.should.equal(['forum_name', 'subject'])


@mock_dynamodb2
def test_create_with_global_indexes():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    Table.create('messages', schema=[
        HashKey('subject'),
        RangeKey('version'),
    ], global_indexes=[
        GlobalAllIndex('topic-created_at-index',
            parts=[
                HashKey('topic'),
                RangeKey('created_at', data_type='N')
            ],
            throughput={
                'read': 6,
                'write': 1
            }
        ),
    ])

    table_description = conn.describe_table("messages")
    table_description['Table']["GlobalSecondaryIndexes"].should.equal([
        {
            "IndexName": "topic-created_at-index",
            "KeySchema": [
                {
                    "AttributeName": "topic",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "created_at",
                    "KeyType": "RANGE"
                },
            ],
            "Projection": {
                "ProjectionType": "ALL"
            },
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 6,
                "WriteCapacityUnits": 1,
            }
        }
    ])


@mock_dynamodb2
def test_query_with_global_indexes():
    table = Table.create('messages', schema=[
        HashKey('subject'),
        RangeKey('version'),
    ], global_indexes=[
        GlobalAllIndex('topic-created_at-index',
            parts=[
                HashKey('topic'),
                RangeKey('created_at', data_type='N')
            ],
            throughput={
                'read': 6,
                'write': 1
            }
        ),
        GlobalAllIndex('status-created_at-index',
            parts=[
                HashKey('status'),
                RangeKey('created_at', data_type='N')
            ],
            throughput={
                'read': 2,
                'write': 1
            }
        )
    ])

    item_data = {
        'subject': 'Check this out!',
        'version': '1',
        'created_at': 0,
        'status': 'inactive'
    }
    item = Item(table, item_data)
    item.save(overwrite=True)

    item['version'] = '2'
    item.save(overwrite=True)

    results = table.query(status__eq='active')
    list(results).should.have.length_of(0)


@mock_dynamodb2
def test_lookup():
    from decimal import Decimal
    table = Table.create('messages', schema=[
        HashKey('test_hash'),
        RangeKey('test_range'),
    ], throughput={
        'read': 10,
        'write': 10,
    })

    hash_key = 3241526475
    range_key = 1234567890987
    data = {'test_hash': hash_key, 'test_range': range_key}
    table.put_item(data=data)
    message = table.lookup(hash_key, range_key)
    message.get('test_hash').should.equal(Decimal(hash_key))
    message.get('test_range').should.equal(Decimal(range_key))


@mock_dynamodb2
def test_failed_overwrite():
    table = Table.create('messages', schema=[
        HashKey('id'),
        RangeKey('range'),
    ], throughput={
        'read': 7,
        'write': 3,
    })

    data1 = {'id': '123', 'range': 'abc', 'data': '678'}
    table.put_item(data=data1)

    data2 = {'id': '123', 'range': 'abc', 'data': '345'}
    table.put_item(data=data2, overwrite=True)

    data3 = {'id': '123', 'range': 'abc', 'data': '812'}
    table.put_item.when.called_with(data=data3).should.throw(ConditionalCheckFailedException)

    returned_item = table.lookup('123', 'abc')
    dict(returned_item).should.equal(data2)

    data4 = {'id': '123', 'range': 'ghi', 'data': 812}
    table.put_item(data=data4)

    returned_item = table.lookup('123', 'ghi')
    dict(returned_item).should.equal(data4)


@mock_dynamodb2
def test_conflicting_writes():
    table = Table.create('messages', schema=[
        HashKey('id'),
        RangeKey('range'),
    ])

    item_data = {'id': '123', 'range': 'abc', 'data': '678'}
    item1 = Item(table, item_data)
    item2 = Item(table, item_data)
    item1.save()

    item1['data'] = '579'
    item2['data'] = '912'

    item1.save()
    item2.save.when.called_with().should.throw(ConditionalCheckFailedException)

"""
boto3
"""


@mock_dynamodb2
def test_boto3_conditions():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123'
    })
    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '456'
    })
    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '789'
    })

    # Test a query returning all items
    results = table.query(
        KeyConditionExpression=Key('forum_name').eq('the-key') & Key("subject").gt('1'),
        ScanIndexForward=True,
    )
    expected = ["123", "456", "789"]
    for index, item in enumerate(results['Items']):
        item["subject"].should.equal(expected[index])

    # Return all items again, but in reverse
    results = table.query(
        KeyConditionExpression=Key('forum_name').eq('the-key') & Key("subject").gt('1'),
        ScanIndexForward=False,
    )
    for index, item in enumerate(reversed(results['Items'])):
        item["subject"].should.equal(expected[index])

    # Filter the subjects to only return some of the results
    results = table.query(
        KeyConditionExpression=Key('forum_name').eq('the-key') & Key("subject").gt('234'),
        ConsistentRead=True,
    )
    results['Count'].should.equal(2)

    # Filter to return no results
    results = table.query(
        KeyConditionExpression=Key('forum_name').eq('the-key') & Key("subject").gt('9999')
    )
    results['Count'].should.equal(0)

    results = table.query(
        KeyConditionExpression=Key('forum_name').eq('the-key') & Key("subject").begins_with('12')
    )
    results['Count'].should.equal(1)

    results = table.query(
        KeyConditionExpression=Key("subject").begins_with('7') & Key('forum_name').eq('the-key')
    )
    results['Count'].should.equal(1)

    results = table.query(
        KeyConditionExpression=Key('forum_name').eq('the-key') & Key("subject").between('567', '890')
    )
    results['Count'].should.equal(1)



@mock_dynamodb2
def test_boto3_query_gsi_range_comparison():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        GlobalSecondaryIndexes=[{
            'IndexName': 'TestGSI',
            'KeySchema': [
                {
                    'AttributeName': 'username',
                    'KeyType': 'HASH',
                },
                {
                    'AttributeName': 'created',
                    'KeyType': 'RANGE',
                }
            ],
            'Projection': {
                'ProjectionType': 'ALL',
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        }],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table = dynamodb.Table('users')

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'username': 'johndoe',
        'created': 3,
    })
    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '456',
        'username': 'johndoe',
        'created': 1,
    })
    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '789',
        'username': 'johndoe',
        'created': 2,
    })
    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '159',
        'username': 'janedoe',
        'created': 2,
    })
    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '601',
        'username': 'janedoe',
        'created': 5,
    })

    # Test a query returning all johndoe items
    results = table.query(
        KeyConditionExpression=Key('username').eq('johndoe') & Key("created").gt('0'),
        ScanIndexForward=True,
        IndexName='TestGSI',
    )
    expected = ["456", "789", "123"]
    for index, item in enumerate(results['Items']):
        item["subject"].should.equal(expected[index])

    # Return all johndoe items again, but in reverse
    results = table.query(
        KeyConditionExpression=Key('username').eq('johndoe') & Key("created").gt('0'),
        ScanIndexForward=False,
        IndexName='TestGSI',
    )
    for index, item in enumerate(reversed(results['Items'])):
        item["subject"].should.equal(expected[index])

    # Filter the creation to only return some of the results
    # And reverse order of hash + range key
    results = table.query(
        KeyConditionExpression=Key("created").gt('1') & Key('username').eq('johndoe'),
        ConsistentRead=True,
        IndexName='TestGSI',
    )
    results['Count'].should.equal(2)

    # Filter to return no results
    results = table.query(
        KeyConditionExpression=Key('username').eq('janedoe') & Key("created").gt('9'),
        IndexName='TestGSI',
    )
    results['Count'].should.equal(0)

    results = table.query(
        KeyConditionExpression=Key('username').eq('janedoe') & Key("created").eq('5'),
        IndexName='TestGSI',
    )
    results['Count'].should.equal(1)

    # Test range key sorting
    results = table.query(
        KeyConditionExpression=Key('username').eq('johndoe') & Key("created").gt('0'),
        IndexName='TestGSI',
    )
    expected = [Decimal('1'), Decimal('2'), Decimal('3')]
    for index, item in enumerate(results['Items']):
        item["created"].should.equal(expected[index])


@mock_dynamodb2
def test_update_table_throughput():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 6
        }
    )
    table = dynamodb.Table('users')

    table.provisioned_throughput['ReadCapacityUnits'].should.equal(5)
    table.provisioned_throughput['WriteCapacityUnits'].should.equal(6)

    table.update(ProvisionedThroughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 11,
    })

    table = dynamodb.Table('users')

    table.provisioned_throughput['ReadCapacityUnits'].should.equal(10)
    table.provisioned_throughput['WriteCapacityUnits'].should.equal(11)


@mock_dynamodb2
def test_update_table_gsi_throughput():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        GlobalSecondaryIndexes=[{
            'IndexName': 'TestGSI',
            'KeySchema': [
                {
                    'AttributeName': 'username',
                    'KeyType': 'HASH',
                },
                {
                    'AttributeName': 'created',
                    'KeyType': 'RANGE',
                }
            ],
            'Projection': {
                'ProjectionType': 'ALL',
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 3,
                'WriteCapacityUnits': 4
            }
        }],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 6
        }
    )
    table = dynamodb.Table('users')

    gsi_throughput = table.global_secondary_indexes[0]['ProvisionedThroughput']
    gsi_throughput['ReadCapacityUnits'].should.equal(3)
    gsi_throughput['WriteCapacityUnits'].should.equal(4)

    table.provisioned_throughput['ReadCapacityUnits'].should.equal(5)
    table.provisioned_throughput['WriteCapacityUnits'].should.equal(6)

    table.update(GlobalSecondaryIndexUpdates=[{
        'Update': {
            'IndexName': 'TestGSI',
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 11,
            }
        },
    }])

    table = dynamodb.Table('users')

    # Primary throughput has not changed
    table.provisioned_throughput['ReadCapacityUnits'].should.equal(5)
    table.provisioned_throughput['WriteCapacityUnits'].should.equal(6)

    gsi_throughput = table.global_secondary_indexes[0]['ProvisionedThroughput']
    gsi_throughput['ReadCapacityUnits'].should.equal(10)
    gsi_throughput['WriteCapacityUnits'].should.equal(11)



@mock_dynamodb2
def test_update_table_gsi_create():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 6
        }
    )
    table = dynamodb.Table('users')

    table.global_secondary_indexes.should.have.length_of(0)

    table.update(GlobalSecondaryIndexUpdates=[{
        'Create': {
            'IndexName': 'TestGSI',
            'KeySchema': [
                {
                    'AttributeName': 'username',
                    'KeyType': 'HASH',
                },
                {
                    'AttributeName': 'created',
                    'KeyType': 'RANGE',
                }
            ],
            'Projection': {
                'ProjectionType': 'ALL',
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 3,
                'WriteCapacityUnits': 4
            }
        },
    }])

    table = dynamodb.Table('users')
    table.global_secondary_indexes.should.have.length_of(1)

    gsi_throughput = table.global_secondary_indexes[0]['ProvisionedThroughput']
    assert gsi_throughput['ReadCapacityUnits'].should.equal(3)
    assert gsi_throughput['WriteCapacityUnits'].should.equal(4)

    # Check update works
    table.update(GlobalSecondaryIndexUpdates=[{
        'Update': {
            'IndexName': 'TestGSI',
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 11,
            }
        },
    }])
    table = dynamodb.Table('users')

    gsi_throughput = table.global_secondary_indexes[0]['ProvisionedThroughput']
    assert gsi_throughput['ReadCapacityUnits'].should.equal(10)
    assert gsi_throughput['WriteCapacityUnits'].should.equal(11)

    table.update(GlobalSecondaryIndexUpdates=[{
        'Delete': {
            'IndexName': 'TestGSI',
        },
    }])

    table = dynamodb.Table('users')
    table.global_secondary_indexes.should.have.length_of(0)


@mock_dynamodb2
def test_update_table_gsi_throughput():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'forum_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'subject',
                'KeyType': 'RANGE'
            },
        ],
        GlobalSecondaryIndexes=[{
            'IndexName': 'TestGSI',
            'KeySchema': [
                {
                    'AttributeName': 'username',
                    'KeyType': 'HASH',
                },
                {
                    'AttributeName': 'created',
                    'KeyType': 'RANGE',
                }
            ],
            'Projection': {
                'ProjectionType': 'ALL',
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 3,
                'WriteCapacityUnits': 4
            }
        }],
        AttributeDefinitions=[
            {
                'AttributeName': 'forum_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'subject',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 6
        }
    )
    table = dynamodb.Table('users')
    table.global_secondary_indexes.should.have.length_of(1)

    table.update(GlobalSecondaryIndexUpdates=[{
        'Delete': {
            'IndexName': 'TestGSI',
        },
    }])

    table = dynamodb.Table('users')
    table.global_secondary_indexes.should.have.length_of(0)
