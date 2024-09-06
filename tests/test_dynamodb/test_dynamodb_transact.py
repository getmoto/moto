import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from . import dynamodb_aws_verified


@mock_aws
def test_invalid_transact_get_items():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test1",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("test1")
    table.put_item(Item={"id": "1", "val": "1"})
    table.put_item(Item={"id": "1", "val": "2"})

    client = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.transact_get_items(
            TransactItems=[
                {"Get": {"Key": {"id": {"S": "1"}}, "TableName": "test1"}}
                for i in range(26)
            ]
        )

    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        "Member must have length less than or equal to 25"
        in ex.value.response["Error"]["Message"]
    )

    with pytest.raises(ClientError) as ex:
        client.transact_get_items(
            TransactItems=[
                {"Get": {"Key": {"id": {"S": "1"}}, "TableName": "test1"}},
                {"Get": {"Key": {"id": {"S": "1"}}, "TableName": "non_exists_table"}},
            ]
        )

    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Message"] == "Requested resource not found"


@mock_aws
def test_transact_get_items_should_return_empty_map_for_non_existent_item():
    client = boto3.client("dynamodb", region_name="us-west-2")
    table_name = "test-table"
    key_schema = [{"AttributeName": "id", "KeyType": "HASH"}]
    attribute_definitions = [{"AttributeName": "id", "AttributeType": "S"}]
    client.create_table(
        TableName=table_name,
        KeySchema=key_schema,
        AttributeDefinitions=attribute_definitions,
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    item = {"id": {"S": "1"}}
    client.put_item(TableName=table_name, Item=item)
    items = client.transact_get_items(
        TransactItems=[
            {"Get": {"Key": {"id": {"S": "1"}}, "TableName": table_name}},
            {"Get": {"Key": {"id": {"S": "2"}}, "TableName": table_name}},
        ]
    ).get("Responses", [])
    assert len(items) == 2
    assert items[0] == {"Item": item}
    assert items[1] == {}


@mock_aws
def test_valid_transact_get_items():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test1",
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
            {"AttributeName": "sort_key", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "sort_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table1 = dynamodb.Table("test1")
    table1.put_item(Item={"id": "1", "sort_key": "1"})
    table1.put_item(Item={"id": "1", "sort_key": "2"})

    dynamodb.create_table(
        TableName="test2",
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
            {"AttributeName": "sort_key", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "sort_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table2 = dynamodb.Table("test2")
    table2.put_item(Item={"id": "1", "sort_key": "1"})

    client = boto3.client("dynamodb", region_name="us-east-1")
    res = client.transact_get_items(
        TransactItems=[
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "1"}},
                    "TableName": "test1",
                }
            },
            {
                "Get": {
                    "Key": {"id": {"S": "non_exists_key"}, "sort_key": {"S": "2"}},
                    "TableName": "test1",
                }
            },
        ]
    )
    assert res["Responses"][0]["Item"] == {"id": {"S": "1"}, "sort_key": {"S": "1"}}
    assert len(res["Responses"]) == 2
    assert res["Responses"][1] == {}

    res = client.transact_get_items(
        TransactItems=[
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "1"}},
                    "TableName": "test1",
                }
            },
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "2"}},
                    "TableName": "test1",
                }
            },
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "1"}},
                    "TableName": "test2",
                }
            },
        ]
    )

    assert res["Responses"][0]["Item"] == {"id": {"S": "1"}, "sort_key": {"S": "1"}}

    assert res["Responses"][1]["Item"] == {"id": {"S": "1"}, "sort_key": {"S": "2"}}

    assert res["Responses"][2]["Item"] == {"id": {"S": "1"}, "sort_key": {"S": "1"}}

    res = client.transact_get_items(
        TransactItems=[
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "1"}},
                    "TableName": "test1",
                }
            },
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "2"}},
                    "TableName": "test1",
                }
            },
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "1"}},
                    "TableName": "test2",
                }
            },
        ],
        ReturnConsumedCapacity="TOTAL",
    )

    assert res["ConsumedCapacity"][0] == {
        "TableName": "test1",
        "CapacityUnits": 4.0,
        "ReadCapacityUnits": 4.0,
    }

    assert res["ConsumedCapacity"][1] == {
        "TableName": "test2",
        "CapacityUnits": 2.0,
        "ReadCapacityUnits": 2.0,
    }

    res = client.transact_get_items(
        TransactItems=[
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "1"}},
                    "TableName": "test1",
                }
            },
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "2"}},
                    "TableName": "test1",
                }
            },
            {
                "Get": {
                    "Key": {"id": {"S": "1"}, "sort_key": {"S": "1"}},
                    "TableName": "test2",
                }
            },
        ],
        ReturnConsumedCapacity="INDEXES",
    )

    assert res["ConsumedCapacity"][0] == {
        "TableName": "test1",
        "CapacityUnits": 4.0,
        "ReadCapacityUnits": 4.0,
        "Table": {"CapacityUnits": 4.0, "ReadCapacityUnits": 4.0},
    }

    assert res["ConsumedCapacity"][1] == {
        "TableName": "test2",
        "CapacityUnits": 2.0,
        "ReadCapacityUnits": 2.0,
        "Table": {"CapacityUnits": 2.0, "ReadCapacityUnits": 2.0},
    }


@mock_aws
def test_transact_write_items_put():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    # Put multiple items
    dynamodb.transact_write_items(
        TransactItems=[
            {
                "Put": {
                    "Item": {"id": {"S": f"foo{str(i)}"}, "foo": {"S": "bar"}},
                    "TableName": "test-table",
                }
            }
            for i in range(0, 5)
        ]
    )
    # Assert all are present
    items = dynamodb.scan(TableName="test-table")["Items"]
    assert len(items) == 5


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_transact_write_items_put_conditional_expressions(table_name=None):
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    dynamodb.put_item(TableName=table_name, Item={"pk": {"S": "foo2"}})
    # Put multiple items
    with pytest.raises(ClientError) as ex:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "Item": {
                            "pk": {"S": f"foo{i}"},
                            "foo": {"S": "bar"},
                        },
                        "TableName": table_name,
                        "ConditionExpression": "#i <> :i",
                        "ExpressionAttributeNames": {"#i": "pk"},
                        "ExpressionAttributeValues": {
                            ":i": {
                                "S": "foo2"
                            }  # This item already exist, so the ConditionExpression should fail
                        },
                    }
                }
                for i in range(0, 5)
            ]
        )
    # Assert the exception is correct
    assert ex.value.response["Error"]["Code"] == "TransactionCanceledException"
    reasons = ex.value.response["CancellationReasons"]
    assert len(reasons) == 5
    assert {
        "Code": "ConditionalCheckFailed",
        "Message": "The conditional request failed",
    } in reasons
    assert {"Code": "None"} in reasons
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    # Assert all are present
    items = dynamodb.scan(TableName=table_name)["Items"]
    assert len(items) == 1
    assert items[0] == {"pk": {"S": "foo2"}}


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_transact_write_items_failure__return_item(table_name=None):
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.put_item(TableName=table_name, Item={"pk": {"S": "foo2"}})
    # Put multiple items
    with pytest.raises(ClientError) as ex:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "Item": {
                            "pk": {"S": f"foo{i}"},
                            "foo": {"S": "bar"},
                        },
                        "TableName": table_name,
                        "ConditionExpression": "#i <> :i",
                        "ExpressionAttributeNames": {"#i": "pk"},
                        # This man right here - should return item as part of error message
                        "ReturnValuesOnConditionCheckFailure": "ALL_OLD",
                        "ExpressionAttributeValues": {
                            ":i": {
                                "S": "foo2"
                            }  # This item already exist, so the ConditionExpression should fail
                        },
                    }
                }
                for i in range(0, 5)
            ]
        )
    # Assert the exception is correct
    assert ex.value.response["Error"]["Code"] == "TransactionCanceledException"
    reasons = ex.value.response["CancellationReasons"]
    assert len(reasons) == 5
    assert {
        "Code": "ConditionalCheckFailed",
        "Message": "The conditional request failed",
        "Item": {"pk": {"S": "foo2"}},
    } in reasons
    assert {"Code": "None"} in reasons
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    # Assert all are present
    items = dynamodb.scan(TableName=table_name)["Items"]
    assert len(items) == 1
    assert items[0] == {"pk": {"S": "foo2"}}


@mock_aws
def test_transact_write_items_conditioncheck_passes():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    # Insert an item with email address
    dynamodb.put_item(
        TableName="test-table",
        Item={"id": {"S": "foo"}, "email_address": {"S": "foo@moto.com"}},
    )
    # Put a new item, after verifying the exising item also has email address
    dynamodb.transact_write_items(
        TransactItems=[
            {
                "ConditionCheck": {
                    "Key": {"id": {"S": "foo"}},
                    "TableName": "test-table",
                    "ConditionExpression": "attribute_exists(#e)",
                    "ExpressionAttributeNames": {"#e": "email_address"},
                }
            },
            {
                "Put": {
                    "Item": {
                        "id": {"S": "bar"},
                        "email_address": {"S": "bar@moto.com"},
                    },
                    "TableName": "test-table",
                }
            },
        ]
    )
    # Assert all are present
    items = dynamodb.scan(TableName="test-table")["Items"]
    assert len(items) == 2
    assert {"email_address": {"S": "foo@moto.com"}, "id": {"S": "foo"}} in items
    assert {"email_address": {"S": "bar@moto.com"}, "id": {"S": "bar"}} in items


@mock_aws
def test_transact_write_items_conditioncheck_fails():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    # Insert an item without email address
    dynamodb.put_item(
        TableName="test-table",
        Item={"id": {"S": "foo"}},
    )
    # Try putting a new item, after verifying the exising item also has email address
    # ConditionCheck should fail
    with pytest.raises(ClientError) as ex:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "ConditionCheck": {
                        "Key": {"id": {"S": "foo"}},
                        "TableName": "test-table",
                        "ConditionExpression": "attribute_exists(#e)",
                        "ExpressionAttributeNames": {"#e": "email_address"},
                    }
                },
                {
                    "Put": {
                        "Item": {
                            "id": {"S": "bar"},
                            "email_address": {"S": "bar@moto.com"},
                        },
                        "TableName": "test-table",
                    }
                },
            ]
        )
    # Assert the exception is correct
    assert ex.value.response["Error"]["Code"] == "TransactionCanceledException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Assert the original item is still present
    items = dynamodb.scan(TableName="test-table")["Items"]
    assert len(items) == 1
    assert items[0] == {"id": {"S": "foo"}}


@mock_aws
def test_transact_write_items_delete():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    # Insert an item
    dynamodb.put_item(TableName="test-table", Item={"id": {"S": "foo"}})
    # Delete the item
    dynamodb.transact_write_items(
        TransactItems=[
            {"Delete": {"Key": {"id": {"S": "foo"}}, "TableName": "test-table"}}
        ]
    )
    # Assert the item is deleted
    items = dynamodb.scan(TableName="test-table")["Items"]
    assert len(items) == 0


@mock_aws
def test_transact_write_items_delete_with_successful_condition_expression():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    # Insert an item without email address
    dynamodb.put_item(TableName="test-table", Item={"id": {"S": "foo"}})
    # ConditionExpression will pass - no email address has been specified yet
    dynamodb.transact_write_items(
        TransactItems=[
            {
                "Delete": {
                    "Key": {"id": {"S": "foo"}},
                    "TableName": "test-table",
                    "ConditionExpression": "attribute_not_exists(#e)",
                    "ExpressionAttributeNames": {"#e": "email_address"},
                }
            }
        ]
    )
    # Assert the item is deleted
    items = dynamodb.scan(TableName="test-table")["Items"]
    assert len(items) == 0


@mock_aws
def test_transact_write_items_delete_with_failed_condition_expression():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    # Insert an item with email address
    dynamodb.put_item(
        TableName="test-table",
        Item={"id": {"S": "foo"}, "email_address": {"S": "test@moto.com"}},
    )
    # Try to delete an item that does not have an email address
    # ConditionCheck should fail
    with pytest.raises(ClientError) as ex:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Delete": {
                        "Key": {"id": {"S": "foo"}},
                        "TableName": "test-table",
                        "ConditionExpression": "attribute_not_exists(#e)",
                        "ExpressionAttributeNames": {"#e": "email_address"},
                    }
                }
            ]
        )
    # Assert the exception is correct
    assert ex.value.response["Error"]["Code"] == "TransactionCanceledException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    # Assert the original item is still present
    items = dynamodb.scan(TableName="test-table")["Items"]
    assert len(items) == 1
    assert items[0] == {"email_address": {"S": "test@moto.com"}, "id": {"S": "foo"}}


@mock_aws
def test_transact_write_items_update():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    # Insert an item
    dynamodb.put_item(TableName="test-table", Item={"id": {"S": "foo"}})
    # Update the item
    dynamodb.transact_write_items(
        TransactItems=[
            {
                "Update": {
                    "Key": {"id": {"S": "foo"}},
                    "TableName": "test-table",
                    "UpdateExpression": "SET #e = :v",
                    "ExpressionAttributeNames": {"#e": "email_address"},
                    "ExpressionAttributeValues": {":v": {"S": "test@moto.com"}},
                }
            }
        ]
    )
    # Assert the item is updated
    items = dynamodb.scan(TableName="test-table")["Items"]
    assert len(items) == 1
    assert items[0] == {"id": {"S": "foo"}, "email_address": {"S": "test@moto.com"}}


@mock_aws
def test_transact_write_items_update_with_failed_condition_expression():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    # Insert an item with email address
    dynamodb.put_item(
        TableName="test-table",
        Item={"id": {"S": "foo"}, "email_address": {"S": "test@moto.com"}},
    )
    # Try to update an item that does not have an email address
    # ConditionCheck should fail
    with pytest.raises(ClientError) as ex:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "Key": {"id": {"S": "foo"}},
                        "TableName": "test-table",
                        "UpdateExpression": "SET #e = :v",
                        "ConditionExpression": "attribute_not_exists(#e)",
                        "ExpressionAttributeNames": {"#e": "email_address"},
                        "ExpressionAttributeValues": {":v": {"S": "update@moto.com"}},
                    }
                }
            ]
        )
    # Assert the exception is correct
    assert ex.value.response["Error"]["Code"] == "TransactionCanceledException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    # Assert the original item is still present
    items = dynamodb.scan(TableName="test-table")["Items"]
    assert len(items) == 1
    assert items[0] == {"email_address": {"S": "test@moto.com"}, "id": {"S": "foo"}}


@mock_aws
def test_transact_write_items_fails_with_transaction_canceled_exception():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    # Insert one item
    dynamodb.put_item(TableName="test-table", Item={"id": {"S": "foo"}})
    # Update two items, the one that exists and another that doesn't
    with pytest.raises(ClientError) as ex:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "Key": {"id": {"S": "foo"}},
                        "TableName": "test-table",
                        "UpdateExpression": "SET #k = :v",
                        "ConditionExpression": "attribute_exists(id)",
                        "ExpressionAttributeNames": {"#k": "key"},
                        "ExpressionAttributeValues": {":v": {"S": "value"}},
                    }
                },
                {
                    "Update": {
                        "Key": {"id": {"S": "doesnotexist"}},
                        "TableName": "test-table",
                        "UpdateExpression": "SET #e = :v",
                        "ConditionExpression": "attribute_exists(id)",
                        "ExpressionAttributeNames": {"#e": "key"},
                        "ExpressionAttributeValues": {":v": {"S": "value"}},
                    }
                },
            ]
        )
    assert ex.value.response["Error"]["Code"] == "TransactionCanceledException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "Transaction cancelled, please refer cancellation reasons for specific reasons [None, ConditionalCheckFailed]"
    )


@mock_aws
def test_transact_using_arns():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    table_arn = dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )["TableDescription"]["TableArn"]

    dynamodb.transact_write_items(
        TransactItems=[{"Put": {"Item": {"id": {"S": "foo"}}, "TableName": table_arn}}]
    )

    items = dynamodb.transact_get_items(
        TransactItems=[{"Get": {"Key": {"id": {"S": "foo"}}, "TableName": table_arn}}]
    )["Responses"]
    assert items == [{"Item": {"id": {"S": "foo"}}}]
