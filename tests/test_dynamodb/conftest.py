import os
import boto3
import pytest
from moto import mock_dynamodb2
from moto.core import DEFAULT_ACCOUNT_ID

# pylint: disable=redefined-outer-name
@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for Moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def ddb_client(aws_credentials):
    """Create a mocked DynamoDB client."""
    with mock_dynamodb2():
        yield boto3.client("dynamodb", region_name="us-east-1")


@pytest.fixture(scope="function")
def ddb_resource(aws_credentials):
    """Create a mocked DynamoDB resource."""
    with mock_dynamodb2():
        yield boto3.resource("dynamodb", region_name="us-east-1")


@pytest.fixture
def users_table_name():
    """Name of the DynamoDB table."""
    return "users"


@pytest.fixture
def create_user_table(ddb_client, users_table_name):
    """Create the 'users' table in DynamoDB with some initial data."""
    # Create a table
    ddb_client.create_table(
        TableName=users_table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    # Insert sample items
    ddb_client.put_item(
        TableName=users_table_name,
        Item={"username": {"S": "user1"}, "binaryfoo": {"B": b"bar"}}
    )
    ddb_client.put_item(
        TableName=users_table_name,
        Item={"username": {"S": "user2"}, "foo": {"S": "bar"}}
    )
    ddb_client.put_item(
        TableName=users_table_name,
        Item={"username": {"S": "user3"}, "foo": {"S": "bar"}}
    )
    return ddb_client


@pytest.fixture
def table():
    """Manually define a table using moto's Table object (for advanced use cases)."""
    return {
        "TableName": "Forums",
        "AccountId": DEFAULT_ACCOUNT_ID,
        "Region": "us-east-1",
        "KeySchema": [
            {"KeyType": "HASH", "AttributeName": "forum_name"},
            {"KeyType": "RANGE", "AttributeName": "subject"},
        ],
        "AttributeDefinitions": [
            {"AttributeType": "S", "AttributeName": "forum_name"},
            {"AttributeType": "S", "AttributeName": "subject"},
        ],
        "ProvisionedThroughput": {
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5
        }
    }
