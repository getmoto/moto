import boto
import sure  # flake8: noqa
from freezegun import freeze_time

from moto import mock_dynamodb
from moto.dynamodb import dynamodb_backend

from boto.dynamodb import condition
from boto.exception import DynamoDBResponseError


@mock_dynamodb
def test_list_tables():
    name = 'TestTable'
    dynamodb_backend.create_table(name)
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    assert conn.list_tables() == ['TestTable']


@mock_dynamodb
def test_list_tables_layer_1():
    dynamodb_backend.create_table("test_1")
    dynamodb_backend.create_table("test_2")
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    res = conn.layer1.list_tables(limit=1)
    expected = {"TableNames": ["test_1"], "LastEvaluatedTableName": "test_1"}
    res.should.equal(expected)

    res = conn.layer1.list_tables(limit=1, start_table="test_1")
    expected = {"TableNames": ["test_2"]}
    res.should.equal(expected)


@mock_dynamodb
def test_describe_missing_table():
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    conn.describe_table.when.called_with('messages').should.throw(DynamoDBResponseError)


def create_table(conn):
    message_table_schema = conn.create_schema(
        hash_key_name='forum_name',
        hash_key_proto_value=str,
        range_key_name='subject',
        range_key_proto_value=str
    )

    table = conn.create_table(
        name='messages',
        schema=message_table_schema,
        read_units=10,
        write_units=10
    )
    return table


@freeze_time("2012-01-14")
@mock_dynamodb
def test_create_table():
    conn = boto.connect_dynamodb()
    create_table(conn)

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
    conn.describe_table('messages').should.equal(expected)


@mock_dynamodb
def test_delete_table():
    conn = boto.connect_dynamodb()
    create_table(conn)
    conn.list_tables().should.have.length_of(1)

    conn.layer1.delete_table('messages')
    conn.list_tables().should.have.length_of(0)

    conn.layer1.delete_table.when.called_with('messages').should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_update_table_throughput():
    conn = boto.connect_dynamodb()
    table = create_table(conn)
    table.read_units.should.equal(10)
    table.write_units.should.equal(10)

    table.update_throughput(5, 6)
    table.refresh()

    table.read_units.should.equal(5)
    table.write_units.should.equal(6)


@mock_dynamodb
def test_item_add_and_describe_and_update():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='LOLCat Forum',
        range_key='Check this out!',
        attrs=item_data,
    )
    item.put()

    returned_item = table.get_item(
        hash_key='LOLCat Forum',
        range_key='Check this out!',
        attributes_to_get=['Body', 'SentBy']
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
    })

    item['SentBy'] = 'User B'
    item.put()

    returned_item = table.get_item(
        hash_key='LOLCat Forum',
        range_key='Check this out!',
        attributes_to_get=['Body', 'SentBy']
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
    })


@mock_dynamodb
def test_delete_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='LOLCat Forum',
        range_key='Check this out!',
        attrs=item_data,
    )
    item.put()

    table.refresh()
    table.item_count.should.equal(1)

    item.delete()
    table.refresh()
    table.item_count.should.equal(0)

    item.delete.when.called_with().should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_query():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='the-key',
        range_key='456',
        attrs=item_data,
    )
    item.put()

    item = table.new_item(
        hash_key='the-key',
        range_key='123',
        attrs=item_data,
    )
    item.put()

    item = table.new_item(
        hash_key='the-key',
        range_key='789',
        attrs=item_data,
    )
    item.put()

    results = table.query(hash_key='the-key', range_key_condition=condition.GT('1'))
    results.response['Items'].should.have.length_of(3)

    results = table.query(hash_key='the-key', range_key_condition=condition.GT('234'))
    results.response['Items'].should.have.length_of(2)

    results = table.query(hash_key='the-key', range_key_condition=condition.GT('9999'))
    results.response['Items'].should.have.length_of(0)

    results = table.query(hash_key='the-key', range_key_condition=condition.CONTAINS('12'))
    results.response['Items'].should.have.length_of(1)

    results = table.query(hash_key='the-key', range_key_condition=condition.BEGINS_WITH('7'))
    results.response['Items'].should.have.length_of(1)

    results = table.query(hash_key='the-key', range_key_condition=condition.BETWEEN('567', '890'))
    results.response['Items'].should.have.length_of(1)


@mock_dynamodb
def test_scan():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='the-key',
        range_key='456',
        attrs=item_data,
    )
    item.put()

    item = table.new_item(
        hash_key='the-key',
        range_key='123',
        attrs=item_data,
    )
    item.put()

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'Ids': {1, 2, 3},
        'PK': 7,
    }
    item = table.new_item(
        hash_key='the-key',
        range_key='789',
        attrs=item_data,
    )
    item.put()

    results = table.scan(scan_filter={'SentBy': condition.EQ('User B')})
    results.response['Items'].should.have.length_of(1)

    results = table.scan(scan_filter={'Body': condition.BEGINS_WITH('http')})
    results.response['Items'].should.have.length_of(3)

    results = table.scan(scan_filter={'Ids': condition.CONTAINS(2)})
    results.response['Items'].should.have.length_of(1)

    results = table.scan(scan_filter={'Ids': condition.NOT_NULL()})
    results.response['Items'].should.have.length_of(1)

    results = table.scan(scan_filter={'Ids': condition.NULL()})
    results.response['Items'].should.have.length_of(2)

    results = table.scan(scan_filter={'PK': condition.BETWEEN(8, 9)})
    results.response['Items'].should.have.length_of(0)

    results = table.scan(scan_filter={'PK': condition.BETWEEN(5, 8)})
    results.response['Items'].should.have.length_of(1)


@mock_dynamodb
def test_write_batch():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    batch_list = conn.new_batch_write_list()

    items = []
    items.append(table.new_item(
        hash_key='the-key',
        range_key='123',
        attrs={
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User A',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        },
    ))

    items.append(table.new_item(
        hash_key='the-key',
        range_key='789',
        attrs={
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User B',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
            'Ids': {1, 2, 3},
            'PK': 7,
        },
    ))

    batch_list.add_batch(table, puts=items)
    conn.batch_write_item(batch_list)

    table.refresh()
    table.item_count.should.equal(2)

    batch_list = conn.new_batch_write_list()
    batch_list.add_batch(table, deletes=[('the-key', '789')])
    conn.batch_write_item(batch_list)

    table.refresh()
    table.item_count.should.equal(1)


# Batch read
# Batch write
