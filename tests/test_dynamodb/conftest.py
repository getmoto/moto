import os
from uuid import uuid4

import boto3
import pytest

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID
from moto.dynamodb.models import Table


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
def user_table(ddb_resource):
    table = ddb_resource.create_table(
        TableName=f"T{uuid4()}",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table.put_item(Item={"username": "user1", "binaryfoo": b"bar"})
    table.put_item(Item={"username": "user2", "foo": "bar"})
    table.put_item(Item={"username": "user3", "foo": "bar"})
    return table


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
