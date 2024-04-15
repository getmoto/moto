import os

import boto3
import pytest

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID
from moto.dynamodb.models import Table


# pylint: disable=redefined-outer-name
@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def ddb_client(aws_credentials):
    with mock_aws():
        yield boto3.client("dynamodb")


@pytest.fixture(scope="function")
def ddb_resource(aws_credentials):
    with mock_aws():
        yield boto3.resource("dynamodb")


@pytest.fixture
def users_table_name():
    return "users"


@pytest.fixture
def create_user_table(ddb_client, users_table_name):
    ddb_client.create_table(
        TableName=users_table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    ddb_client.put_item(
        TableName="users", Item={"username": {"S": "user1"}, "binaryfoo": {"B": b"bar"}}
    )
    ddb_client.put_item(
        TableName="users", Item={"username": {"S": "user2"}, "foo": {"S": "bar"}}
    )
    ddb_client.put_item(
        TableName="users", Item={"username": {"S": "user3"}, "foo": {"S": "bar"}}
    )
    return ddb_client


@pytest.fixture
def table():
    return Table(
        "Forums",
        account_id=DEFAULT_ACCOUNT_ID,
        region="us-east-1",
        schema=[
            {"KeyType": "HASH", "AttributeName": "forum_name"},
            {"KeyType": "RANGE", "AttributeName": "subject"},
        ],
        attr=[
            {"AttributeType": "S", "AttributeName": "forum_name"},
            {"AttributeType": "S", "AttributeName": "subject"},
        ],
    )
