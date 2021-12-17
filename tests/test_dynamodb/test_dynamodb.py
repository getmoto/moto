import boto
import boto.dynamodb
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_dynamodb, mock_dynamodb_deprecated
from moto.dynamodb import dynamodb_backend

from boto.exception import DynamoDBResponseError


def test_deprecation_warning():
    with pytest.warns(None) as record:
        mock_dynamodb()
    str(record[0].message).should.contain(
        "Module mock_dynamodb has been deprecated, and will be repurposed in a later release"
    )


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_list_tables():
    name = "TestTable"
    dynamodb_backend.create_table(name, hash_key_attr="name", hash_key_type="S")
    conn = boto.connect_dynamodb("the_key", "the_secret")
    assert conn.list_tables() == ["TestTable"]


@mock_dynamodb_deprecated
def test_list_tables_layer_1():
    dynamodb_backend.create_table("test_1", hash_key_attr="name", hash_key_type="S")
    dynamodb_backend.create_table("test_2", hash_key_attr="name", hash_key_type="S")
    conn = boto.connect_dynamodb("the_key", "the_secret")
    res = conn.layer1.list_tables(limit=1)
    expected = {"TableNames": ["test_1"], "LastEvaluatedTableName": "test_1"}
    res.should.equal(expected)

    res = conn.layer1.list_tables(limit=1, start_table="test_1")
    expected = {"TableNames": ["test_2"]}
    res.should.equal(expected)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_describe_missing_table():
    conn = boto.connect_dynamodb("the_key", "the_secret")
    with pytest.raises(DynamoDBResponseError):
        conn.describe_table("messages")


# Has boto3 equivalent
# This test is pointless though, as we treat DynamoDB as a global resource
@mock_dynamodb_deprecated
def test_dynamodb_with_connect_to_region():
    # this will work if connected with boto.connect_dynamodb()
    dynamodb = boto.dynamodb.connect_to_region("us-west-2")

    schema = dynamodb.create_schema("column1", str(), "column2", int())
    dynamodb.create_table("table1", schema, 200, 200)
