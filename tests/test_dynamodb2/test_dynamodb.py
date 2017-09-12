from __future__ import unicode_literals, print_function

import six
import boto
import boto3
import sure  # noqa
import requests
from moto import mock_dynamodb2, mock_dynamodb2_deprecated
from moto.dynamodb2 import dynamodb_backend2
from boto.exception import JSONResponseError
from botocore.exceptions import ClientError
from tests.helpers import requires_boto_gte
import tests.backport_assert_raises
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
