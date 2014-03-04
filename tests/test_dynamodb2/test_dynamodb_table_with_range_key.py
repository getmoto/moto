import boto
import sure  # noqa
from freezegun import freeze_time
from moto import mock_dynamodb2
from boto.exception import JSONResponseError
from tests.helpers import requires_boto_gte
try:
    from boto.dynamodb2.fields import HashKey
    from boto.dynamodb2.fields import RangeKey
    from boto.dynamodb2.table import Table
    from boto.dynamodb2.table import Item
    from boto.dynamodb.exceptions import DynamoDBKeyNotFoundError
    from boto.dynamodb2.exceptions import ValidationException
    from boto.dynamodb2.exceptions import ConditionalCheckFailedException
except ImportError:
    print "This boto version is not supported"
    
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
        print i



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
            'ItemCount': 0, 'CreationDateTime': 1326499200.0
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
    
    table.get_item(forum_name="LOLCat Forum",subject='Check this out!').should_not.be.none

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
    item =Item(table,item_data)   
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
    table.put_item( data = {'test_hash':hash_key, 'test_range':range_key})
    table.get_item.when.called_with(test_hash=hash_key).should.throw(ValidationException)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_item():
    table = create_table()
    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item =Item(table,item_data)
    item['subject'] = 'Check this out!'        
    item.save()
    table.count().should.equal(1)

    response = item.delete()
    response.should.equal(True)
    
    table.count().should.equal(0)
    item.delete.when.called_with().should.throw(ConditionalCheckFailedException)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_item_with_undeclared_table():
    conn = boto.connect_dynamodb()
    table = Table("undeclared-table")
    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item =Item(table,item_data)
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
    item =Item(table,item_data)     
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

    results = table.query(forum_name__eq='the-key', subject__gt='1',consistent=True)
    expected = ["123", "456", "789"]
    for index, item in enumerate(results):
        item["subject"].should.equal(expected[index])

    results = table.query(forum_name__eq="the-key", subject__gt='1', reverse=True)
    for index, item in enumerate(results):
        item["subject"].should.equal(expected[len(expected)-1-index])

    results = table.query(forum_name__eq='the-key', subject__gt='1',consistent=True)
    sum(1 for _ in results).should.equal(3)

    results = table.query(forum_name__eq='the-key', subject__gt='234',consistent=True)
    sum(1 for _ in results).should.equal(2)
    
    results = table.query(forum_name__eq='the-key', subject__gt='9999')
    sum(1 for _ in results).should.equal(0)
    
    results = table.query(forum_name__eq='the-key', subject__beginswith='12')
    sum(1 for _ in results).should.equal(1)
    
    results = table.query(forum_name__eq='the-key', subject__beginswith='7')
    sum(1 for _ in results).should.equal(1)

    results = table.query(forum_name__eq='the-key', subject__between=['567', '890'])
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
    
    item = Item(table,item_data)     
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
    
    item = Item(table,item_data)     
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
    
    item = Item(table,item_data)     
    item.save()    

    item = Item(table,item_data) 
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
    item = Item(table,item_data) 
    item_data['forum_name'] = 'another-key'
    item_data['subject'] = '789'
    item.save() 
    results = table.batch_get(keys=[
                {'forum_name': 'the-key', 'subject': '123'},
                {'forum_name': 'another-key', 'subject': '789'}])

    # Iterate through so that batch_item gets called
    count = len([x for x in results])
    count.should.equal(2)

@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_key_fields():
    table = create_table()
    kf = table.get_key_fields()
    kf.should.equal(['forum_name','subject'])
