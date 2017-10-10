from __future__ import unicode_literals, print_function

import six
import boto
import boto3
from boto3.dynamodb.conditions import Attr
import sure  # noqa
import requests
from moto import mock_dynamodb2, mock_dynamodb2_deprecated
from moto.dynamodb2 import dynamodb_backend2
from boto.exception import JSONResponseError
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from tests.helpers import requires_boto_gte
import tests.backport_assert_raises

import moto.dynamodb2.comparisons
import moto.dynamodb2.models

from nose.tools import assert_raises
try:
    import boto.dynamodb2
except ImportError:
    print("This boto version is not supported")


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_list_tables():
    name = 'TestTable'
    #{'schema': }
    dynamodb_backend2.create_table(name, schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'forum_name'},
        {u'KeyType': u'RANGE', u'AttributeName': u'subject'}
    ])
    conn = boto.dynamodb2.connect_to_region(
        'us-west-2',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")
    assert conn.list_tables()["TableNames"] == [name]


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_list_tables_layer_1():
    dynamodb_backend2.create_table("test_1", schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'name'}
    ])
    dynamodb_backend2.create_table("test_2", schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'name'}
    ])
    conn = boto.dynamodb2.connect_to_region(
        'us-west-2',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")

    res = conn.list_tables(limit=1)
    expected = {"TableNames": ["test_1"], "LastEvaluatedTableName": "test_1"}
    res.should.equal(expected)

    res = conn.list_tables(limit=1, exclusive_start_table_name="test_1")
    expected = {"TableNames": ["test_2"]}
    res.should.equal(expected)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_describe_missing_table():
    conn = boto.dynamodb2.connect_to_region(
        'us-west-2',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")
    with assert_raises(JSONResponseError):
        conn.describe_table('messages')


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_table_tags():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'id','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'id','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})
    table_description = conn.describe_table(TableName=name)
    arn = table_description['Table']['TableArn']
    tags = [{'Key':'TestTag', 'Value': 'TestValue'}]
    conn.tag_resource(ResourceArn=arn,
                      Tags=tags)
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert resp["Tags"] == tags


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_table_tags_empty():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'id','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'id','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})
    table_description = conn.describe_table(TableName=name)
    arn = table_description['Table']['TableArn']
    tags = [{'Key':'TestTag', 'Value': 'TestValue'}]
    # conn.tag_resource(ResourceArn=arn,
    #                   Tags=tags)
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert resp["Tags"] == []


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_table_tags_paginated():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'id','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'id','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})
    table_description = conn.describe_table(TableName=name)
    arn = table_description['Table']['TableArn']
    for i in range(11):
        tags = [{'Key':'TestTag%d' % i, 'Value': 'TestValue'}]
        conn.tag_resource(ResourceArn=arn,
                          Tags=tags)
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert len(resp["Tags"]) == 10
    assert 'NextToken' in resp.keys()
    resp2 = conn.list_tags_of_resource(ResourceArn=arn,
                                       NextToken=resp['NextToken'])
    assert len(resp2["Tags"]) == 1
    assert 'NextToken' not in resp2.keys()


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_not_found_table_tags():
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    arn = 'DymmyArn'
    try:
        conn.list_tags_of_resource(ResourceArn=arn)
    except ClientError as exception:
        assert exception.response['Error']['Code'] == "ResourceNotFoundException"


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_item_add_empty_string_exception():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'forum_name','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'forum_name','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})

    with assert_raises(ClientError) as ex:
        conn.put_item(
            TableName=name,
            Item={
                'forum_name': { 'S': 'LOLCat Forum' },
                'subject': { 'S': 'Check this out!' },
                'Body': { 'S': 'http://url_to_lolcat.gif'},
                'SentBy': { 'S': "" },
                'ReceivedTime': { 'S': '12/9/2011 11:36:03 PM'},
            }
        )

    ex.exception.response['Error']['Code'].should.equal('ValidationException')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)
    ex.exception.response['Error']['Message'].should.equal(
        'One or more parameter values were invalid: An AttributeValue may not contain an empty string'
    )


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query_invalid_table():
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")
    try:
        conn.query(TableName='invalid_table', KeyConditionExpression='index1 = :partitionkeyval', ExpressionAttributeValues={':partitionkeyval': {'S':'test'}})
    except ClientError as exception:
        assert exception.response['Error']['Code'] == "ResourceNotFoundException"


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_scan_returns_consumed_capacity():
    name = 'TestTable'
    conn = boto3.client('dynamodb',
                        region_name='us-west-2',
                        aws_access_key_id="ak",
                        aws_secret_access_key="sk")

    conn.create_table(TableName=name,
                      KeySchema=[{'AttributeName':'forum_name','KeyType':'HASH'}],
                      AttributeDefinitions=[{'AttributeName':'forum_name','AttributeType':'S'}],
                      ProvisionedThroughput={'ReadCapacityUnits':5,'WriteCapacityUnits':5})

    conn.put_item(
            TableName=name,
            Item={
                'forum_name': { 'S': 'LOLCat Forum' },
                'subject': { 'S': 'Check this out!' },
                'Body': { 'S': 'http://url_to_lolcat.gif'},
                'SentBy': { 'S': "test" },
                'ReceivedTime': { 'S': '12/9/2011 11:36:03 PM'},
            }
        )

    response = conn.scan(
        TableName=name,
    )

    assert 'ConsumedCapacity' in response
    assert 'CapacityUnits' in response['ConsumedCapacity']
    assert response['ConsumedCapacity']['TableName'] == name


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query_returns_consumed_capacity():
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
        'subject': '123',
        'body': 'some test message'
    })

    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key')
    )

    assert 'ConsumedCapacity' in results
    assert 'CapacityUnits' in results['ConsumedCapacity']
    assert results['ConsumedCapacity']['CapacityUnits'] == 1


@mock_dynamodb2
def test_basic_projection_expressions():
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
        'subject': '123',
        'body': 'some test message'
    })

    table.put_item(Item={
        'forum_name': 'not-the-key',
        'subject': '123',
        'body': 'some other test message'
    })
    # Test a query returning all items
    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key'),
        ProjectionExpression='body, subject'
    )

    assert 'body' in results['Items'][0]
    assert results['Items'][0]['body'] == 'some test message'
    assert 'subject' in results['Items'][0]

    table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '1234',
        'body': 'yet another test message'
    })

    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key'),
        ProjectionExpression='body'
    )

    assert 'body' in results['Items'][0]
    assert results['Items'][0]['body'] == 'some test message'
    assert 'body' in results['Items'][1]
    assert results['Items'][1]['body'] == 'yet another test message'


@mock_dynamodb2
def test_basic_projection_expressions_with_attr_expression_names():
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
        'subject': '123',
        'body': 'some test message',
        'attachment': 'something'
    })

    table.put_item(Item={
        'forum_name': 'not-the-key',
        'subject': '123',
        'body': 'some other test message',
        'attachment': 'something'
    })
    # Test a query returning all items

    results = table.query(
        KeyConditionExpression=Key('forum_name').eq(
            'the-key'),
        ProjectionExpression='#rl, #rt, subject',
        ExpressionAttributeNames={
            '#rl': 'body',
            '#rt': 'attachment'
            },
    )

    assert 'body' in results['Items'][0]
    assert results['Items'][0]['body'] == 'some test message'
    assert 'subject' in results['Items'][0]
    assert results['Items'][0]['subject'] == '123'
    assert 'attachment' in results['Items'][0]
    assert results['Items'][0]['attachment'] == 'something'


@mock_dynamodb2
def test_put_item_returns_consumed_capacity():
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

    response = table.put_item(Item={
        'forum_name': 'the-key',
        'subject': '123',
        'body': 'some test message',
    })

    assert 'ConsumedCapacity' in response


@mock_dynamodb2
def test_update_item_returns_consumed_capacity():
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
        'subject': '123',
        'body': 'some test message',
    })

    response = table.update_item(Key={
        'forum_name': 'the-key',
        'subject': '123'
        },
        UpdateExpression='set body=:tb',
        ExpressionAttributeValues={
            ':tb': 'a new message'
    })

    assert 'ConsumedCapacity' in response
    assert 'CapacityUnits' in response['ConsumedCapacity']
    assert 'TableName' in response['ConsumedCapacity']


@mock_dynamodb2
def test_get_item_returns_consumed_capacity():
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
        'subject': '123',
        'body': 'some test message',
    })

    response = table.get_item(Key={
        'forum_name': 'the-key',
        'subject': '123'
    })

    assert 'ConsumedCapacity' in response
    assert 'CapacityUnits' in response['ConsumedCapacity']
    assert 'TableName' in response['ConsumedCapacity']


def test_filter_expression():
    # TODO NOT not yet supported
    row1 = moto.dynamodb2.models.Item(None, None, None, None, {'Id': {'N': '8'}, 'Subs': {'N': '5'}, 'Desc': {'S': 'Some description'}, 'KV': {'SS': ['test1', 'test2']}})
    row2 = moto.dynamodb2.models.Item(None, None, None, None, {'Id': {'N': '8'}, 'Subs': {'N': '10'}, 'Desc': {'S': 'A description'}, 'KV': {'SS': ['test3', 'test4']}})

    # AND test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id > 5 AND Subs < 7', {}, {})
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # OR test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id = 5 OR Id=8', {}, {})
    filter_expr.expr(row1).should.be(True)

    # BETWEEN test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id BETWEEN 5 AND 10', {}, {})
    filter_expr.expr(row1).should.be(True)

    # PAREN test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id = 8 AND (Subs = 8 OR Subs = 5)', {}, {})
    filter_expr.expr(row1).should.be(True)

    # IN test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('Id IN (7,8, 9)', {}, {})
    filter_expr.expr(row1).should.be(True)

    # attribute function tests
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('attribute_exists(Id) AND attribute_not_exists(User)', {}, {})
    filter_expr.expr(row1).should.be(True)

    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('attribute_type(Id, N)', {}, {})
    filter_expr.expr(row1).should.be(True)

    # beginswith function test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('begins_with(Desc, Some)', {}, {})
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # contains function test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('contains(KV, test1)', {}, {})
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # size function test
    filter_expr = moto.dynamodb2.comparisons.get_filter_expression('size(Desc) > size(KV)', {}, {})
    filter_expr.expr(row1).should.be(True)


@mock_dynamodb2
def test_scan_filter():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'}
        }
    )

    table = dynamodb.Table('test1')
    response = table.scan(
        FilterExpression=Attr('app').eq('app2')
    )
    assert response['Count'] == 0

    response = table.scan(
        FilterExpression=Attr('app').eq('app1')
    )
    assert response['Count'] == 1


@mock_dynamodb2
def test_bad_scan_filter():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    table = dynamodb.Table('test1')

    # Bad expression
    try:
        table.scan(
            FilterExpression='client test'
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ValidationError')
    else:
        raise RuntimeError('Should of raised ResourceInUseException')



@mock_dynamodb2
def test_duplicate_create():
    client = boto3.client('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )

    try:
        client.create_table(
            TableName='test1',
            AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
            KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
            ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceInUseException')
    else:
        raise RuntimeError('Should of raised ResourceInUseException')


@mock_dynamodb2
def test_delete_table():
    client = boto3.client('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )

    client.delete_table(TableName='test1')

    resp = client.list_tables()
    len(resp['TableNames']).should.equal(0)

    try:
        client.delete_table(TableName='test1')
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFoundException')
    else:
        raise RuntimeError('Should of raised ResourceNotFoundException')


@mock_dynamodb2
def test_delete_item():
    client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Create the DynamoDB table.
    client.create_table(
        TableName='test1',
        AttributeDefinitions=[{'AttributeName': 'client', 'AttributeType': 'S'}, {'AttributeName': 'app', 'AttributeType': 'S'}],
        KeySchema=[{'AttributeName': 'client', 'KeyType': 'HASH'}, {'AttributeName': 'app', 'KeyType': 'RANGE'}],
        ProvisionedThroughput={'ReadCapacityUnits': 123, 'WriteCapacityUnits': 123}
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app1'}
        }
    )
    client.put_item(
        TableName='test1',
        Item={
            'client': {'S': 'client1'},
            'app': {'S': 'app2'}
        }
    )

    table = dynamodb.Table('test1')
    response = table.scan()
    assert response['Count'] == 2

    # Test deletion and returning old value
    response = table.delete_item(Key={'client': 'client1', 'app': 'app1'}, ReturnValues='ALL_OLD')
    response['Attributes'].should.contain('client')
    response['Attributes'].should.contain('app')

    response = table.scan()
    assert response['Count'] == 1

    # Test deletion returning nothing
    response = table.delete_item(Key={'client': 'client1', 'app': 'app2'})
    len(response['Attributes']).should.equal(0)

    response = table.scan()
    assert response['Count'] == 0
