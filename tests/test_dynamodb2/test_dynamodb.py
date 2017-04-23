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
    assert conn.list_tags_of_resource(ResourceArn=arn)["Tags"] == tags


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