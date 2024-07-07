import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from .. import dynamodb_aws_verified


@mock_aws
def test_multiple_transactions_on_same_item():
    schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **schema
    )
    # Insert an item
    dynamodb.put_item(TableName="test-table", Item={"id": {"S": "foo"}})

    def update_email_transact(email):
        return {
            "Update": {
                "Key": {"id": {"S": "foo"}},
                "TableName": "test-table",
                "UpdateExpression": "SET #e = :v",
                "ExpressionAttributeNames": {"#e": "email_address"},
                "ExpressionAttributeValues": {":v": {"S": email}},
            }
        }

    with pytest.raises(ClientError) as exc:
        dynamodb.transact_write_items(
            TransactItems=[
                update_email_transact("test1@moto.com"),
                update_email_transact("test2@moto.com"),
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Transaction request cannot include multiple operations on one item"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True)
def test_transact_write_items__put_and_delete_on_same_item(table_name=None):
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": {
                            "pk": {"S": "test-pk"},
                            "sk": {"S": "test-sk"},
                            "field": {"S": "test-field"},
                        },
                    }
                },
                {
                    "Delete": {
                        "TableName": table_name,
                        "Key": {
                            "pk": {"S": "test-pk"},
                            "sk": {"S": "test-sk"},
                        },
                    }
                },
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Transaction request cannot include multiple operations on one item"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True)
def test_transact_write_items__update_with_multiple_set_clauses(table_name=None):
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {"pk": {"S": "s"}},
                        "UpdateExpression": "SET expire_at_utc = :expire_at_utc SET is_final = :true ADD version :one",
                        "ExpressionAttributeValues": {
                            ":true": {"BOOL": True},
                            ":one": {"N": "1"},
                            ":expire_at_utc": {"S": "asdf"},
                        },
                    }
                }
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == 'Invalid UpdateExpression: The "SET" section can only be used once in an update expression;'
    )

    # Note that we can do this by simply separating the statements with a comma
    dynamodb.transact_write_items(
        TransactItems=[
            {
                "Update": {
                    "TableName": table_name,
                    "Key": {"pk": {"S": "s"}, "sk": {"S": "t"}},
                    "UpdateExpression": "SET a1 = :v1, a2 = :v2",
                    "ExpressionAttributeValues": {
                        ":v1": {"S": "v1"},
                        ":v2": {"S": "v1"},
                    },
                }
            }
        ]
    )

    inventory = dynamodb.scan(TableName=table_name)["Items"]
    assert inventory == [
        {"a1": {"S": "v1"}, "sk": {"S": "t"}, "a2": {"S": "v1"}, "pk": {"S": "s"}}
    ]


@mock_aws
def test_transact_write_items__too_many_transactions():
    schema = {
        "KeySchema": [{"AttributeName": "pk", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "pk", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **schema
    )

    def update_email_transact(email):
        return {
            "Put": {
                "TableName": "test-table",
                "Item": {"pk": {"S": ":v"}},
                "ExpressionAttributeValues": {":v": {"S": email}},
            }
        }

    update_email_transact("test1@moto.com")
    with pytest.raises(ClientError) as exc:
        dynamodb.transact_write_items(
            TransactItems=[
                update_email_transact(f"test{idx}@moto.com") for idx in range(101)
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected at 'transactItems' failed to satisfy constraint: Member must have length less than or equal to 100."
    )


@mock_aws
def test_transact_write_items_multiple_operations_fail():
    # Setup
    schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    table_name = "test-table"
    dynamodb.create_table(TableName=table_name, BillingMode="PAY_PER_REQUEST", **schema)

    # Execute
    with pytest.raises(ClientError) as exc:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "Item": {"id": {"S": "test"}},
                        "TableName": table_name,
                    },
                    "Delete": {
                        "Key": {"id": {"S": "test"}},
                        "TableName": table_name,
                    },
                }
            ]
        )
    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "TransactItems can only contain one of Check, Put, Update or Delete"
    )


@mock_aws
def test_transact_write_items_with_empty_gsi_key():
    client = boto3.client("dynamodb", "us-east-2")

    client.create_table(
        TableName="test_table",
        KeySchema=[{"AttributeName": "unique_code", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "unique_code", "AttributeType": "S"},
            {"AttributeName": "unique_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "gsi_index",
                "KeySchema": [{"AttributeName": "unique_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    transact_items = [
        {
            "Put": {
                "Item": {"unique_code": {"S": "some code"}, "unique_id": {"S": ""}},
                "TableName": "test_table",
            }
        }
    ]

    with pytest.raises(ClientError) as exc:
        client.transact_write_items(TransactItems=transact_items)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values are not valid. A value specified for a secondary index key is not supported. The AttributeValue for a key attribute cannot contain an empty string value. IndexName: gsi_index, IndexKey: unique_id"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_transaction_with_empty_key(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    client = boto3.client("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)
    table.put_item(Item={"pk": "mark", "lock": {"acquired_at": 123}})

    with pytest.raises(ClientError) as exc:
        client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {"pk": {"S": ""}},
                        "UpdateExpression": "SET sth = :v",
                        "ExpressionAttributeValues": {":v": {"N": "0"}},
                    }
                }
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values are not valid. The AttributeValue for a key attribute cannot contain an empty string value. Key: pk"
    )
