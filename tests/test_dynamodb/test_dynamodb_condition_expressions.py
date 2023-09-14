from decimal import Decimal
import re

import boto3
import pytest
from moto import mock_dynamodb


@mock_dynamodb
def test_condition_expression_with_dot_in_attr_name():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
    table_name = "Test"
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table = dynamodb.Table(table_name)

    email_like_str = "test@foo.com"
    record = {"id": "key-0", "first": {email_like_str: {"third": {"VALUE"}}}}
    table.put_item(Item=record)

    table.update_item(
        Key={"id": "key-0"},
        UpdateExpression="REMOVE #first.#second, #other",
        ExpressionAttributeNames={
            "#first": "first",
            "#second": email_like_str,
            "#third": "third",
            "#other": "other",
        },
        ExpressionAttributeValues={":value": "VALUE", ":one": 1},
        ConditionExpression="size(#first.#second.#third) = :one AND contains(#first.#second.#third, :value)",
        ReturnValues="ALL_NEW",
    )

    item = table.get_item(Key={"id": "key-0"})["Item"]
    assert item == {"id": "key-0", "first": {}}


@mock_dynamodb
def test_condition_expressions():
    client = boto3.client("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    client.create_table(
        TableName="test1",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
    )
    client.put_item(
        TableName="test1",
        Item={
            "client": {"S": "client1"},
            "app": {"S": "app1"},
            "match": {"S": "match"},
            "existing": {"S": "existing"},
        },
    )

    client.put_item(
        TableName="test1",
        Item={
            "client": {"S": "client1"},
            "app": {"S": "app1"},
            "match": {"S": "match"},
            "existing": {"S": "existing"},
        },
        ConditionExpression="attribute_exists(#existing) AND attribute_not_exists(#nonexistent) AND #match = :match",
        ExpressionAttributeNames={
            "#existing": "existing",
            "#nonexistent": "nope",
            "#match": "match",
        },
        ExpressionAttributeValues={":match": {"S": "match"}},
    )

    client.put_item(
        TableName="test1",
        Item={
            "client": {"S": "client1"},
            "app": {"S": "app1"},
            "match": {"S": "match"},
            "existing": {"S": "existing"},
        },
        ConditionExpression="NOT(attribute_exists(#nonexistent1) AND attribute_exists(#nonexistent2))",
        ExpressionAttributeNames={"#nonexistent1": "nope", "#nonexistent2": "nope2"},
    )

    client.put_item(
        TableName="test1",
        Item={
            "client": {"S": "client1"},
            "app": {"S": "app1"},
            "match": {"S": "match"},
            "existing": {"S": "existing"},
        },
        ConditionExpression="attribute_exists(#nonexistent) OR attribute_exists(#existing)",
        ExpressionAttributeNames={"#nonexistent": "nope", "#existing": "existing"},
    )

    client.put_item(
        TableName="test1",
        Item={
            "client": {"S": "client1"},
            "app": {"S": "app1"},
            "match": {"S": "match"},
            "existing": {"S": "existing"},
        },
        ConditionExpression="#client BETWEEN :a AND :z",
        ExpressionAttributeNames={"#client": "client"},
        ExpressionAttributeValues={":a": {"S": "a"}, ":z": {"S": "z"}},
    )

    client.put_item(
        TableName="test1",
        Item={
            "client": {"S": "client1"},
            "app": {"S": "app1"},
            "match": {"S": "match"},
            "existing": {"S": "existing"},
        },
        ConditionExpression="#client IN (:client1, :client2)",
        ExpressionAttributeNames={"#client": "client"},
        ExpressionAttributeValues={
            ":client1": {"S": "client1"},
            ":client2": {"S": "client2"},
        },
    )

    with pytest.raises(client.exceptions.ConditionalCheckFailedException):
        client.put_item(
            TableName="test1",
            Item={
                "client": {"S": "client1"},
                "app": {"S": "app1"},
                "match": {"S": "match"},
                "existing": {"S": "existing"},
            },
            ConditionExpression="attribute_exists(#nonexistent1) AND attribute_exists(#nonexistent2)",
            ExpressionAttributeNames={
                "#nonexistent1": "nope",
                "#nonexistent2": "nope2",
            },
        )

    with pytest.raises(client.exceptions.ConditionalCheckFailedException):
        client.put_item(
            TableName="test1",
            Item={
                "client": {"S": "client1"},
                "app": {"S": "app1"},
                "match": {"S": "match"},
                "existing": {"S": "existing"},
            },
            ConditionExpression="NOT(attribute_not_exists(#nonexistent1) AND attribute_not_exists(#nonexistent2))",
            ExpressionAttributeNames={
                "#nonexistent1": "nope",
                "#nonexistent2": "nope2",
            },
        )

    with pytest.raises(client.exceptions.ConditionalCheckFailedException):
        client.put_item(
            TableName="test1",
            Item={
                "client": {"S": "client1"},
                "app": {"S": "app1"},
                "match": {"S": "match"},
                "existing": {"S": "existing"},
            },
            ConditionExpression="attribute_exists(#existing) AND attribute_not_exists(#nonexistent) AND #match = :match",
            ExpressionAttributeNames={
                "#existing": "existing",
                "#nonexistent": "nope",
                "#match": "match",
            },
            ExpressionAttributeValues={":match": {"S": "match2"}},
        )

    # Make sure update_item honors ConditionExpression as well
    client.update_item(
        TableName="test1",
        Key={"client": {"S": "client1"}, "app": {"S": "app1"}},
        UpdateExpression="set #match=:match",
        ConditionExpression="attribute_exists(#existing)",
        ExpressionAttributeNames={"#existing": "existing", "#match": "match"},
        ExpressionAttributeValues={":match": {"S": "match"}},
    )

    with pytest.raises(client.exceptions.ConditionalCheckFailedException) as exc:
        client.update_item(
            TableName="test1",
            Key={"client": {"S": "client1"}, "app": {"S": "app1"}},
            UpdateExpression="set #match=:match",
            ConditionExpression="attribute_not_exists(#existing)",
            ExpressionAttributeValues={":match": {"S": "match"}},
            ExpressionAttributeNames={"#existing": "existing", "#match": "match"},
        )
    _assert_conditional_check_failed_exception(exc)

    with pytest.raises(client.exceptions.ConditionalCheckFailedException) as exc:
        client.update_item(
            TableName="test1",
            Key={"client": {"S": "client2"}, "app": {"S": "app1"}},
            UpdateExpression="set #match=:match",
            ConditionExpression="attribute_exists(#existing)",
            ExpressionAttributeValues={":match": {"S": "match"}},
            ExpressionAttributeNames={"#existing": "existing", "#match": "match"},
        )
    _assert_conditional_check_failed_exception(exc)

    with pytest.raises(client.exceptions.ConditionalCheckFailedException):
        client.delete_item(
            TableName="test1",
            Key={"client": {"S": "client1"}, "app": {"S": "app1"}},
            ConditionExpression="attribute_not_exists(#existing)",
            ExpressionAttributeValues={":match": {"S": "match"}},
            ExpressionAttributeNames={"#existing": "existing", "#match": "match"},
        )


def _assert_conditional_check_failed_exception(exc):
    err = exc.value.response["Error"]
    assert err["Code"] == "ConditionalCheckFailedException"
    assert err["Message"] == "The conditional request failed"


@mock_dynamodb
def test_condition_expression_numerical_attribute():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="my-table",
        KeySchema=[{"AttributeName": "partitionKey", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "partitionKey", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table = dynamodb.Table("my-table")
    table.put_item(Item={"partitionKey": "pk-pos", "myAttr": 5})
    table.put_item(Item={"partitionKey": "pk-neg", "myAttr": -5})

    # try to update the item we put in the table using numerical condition expression
    # Specifically, verify that we can compare with a zero-value
    # First verify that > and >= work on positive numbers
    update_numerical_con_expr(
        key="pk-pos", con_expr="myAttr > :zero", res="6", table=table
    )
    update_numerical_con_expr(
        key="pk-pos", con_expr="myAttr >= :zero", res="7", table=table
    )
    # Second verify that < and <= work on negative numbers
    update_numerical_con_expr(
        key="pk-neg", con_expr="myAttr < :zero", res="-4", table=table
    )
    update_numerical_con_expr(
        key="pk-neg", con_expr="myAttr <= :zero", res="-3", table=table
    )


def update_numerical_con_expr(key, con_expr, res, table):
    table.update_item(
        Key={"partitionKey": key},
        UpdateExpression="ADD myAttr :one",
        ExpressionAttributeValues={":zero": 0, ":one": 1},
        ConditionExpression=con_expr,
    )
    assert table.get_item(Key={"partitionKey": key})["Item"]["myAttr"] == Decimal(res)


@mock_dynamodb
def test_condition_expression__attr_doesnt_exist():
    client = boto3.client("dynamodb", region_name="us-east-1")

    client.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    client.put_item(
        TableName="test", Item={"forum_name": {"S": "foo"}, "ttl": {"N": "bar"}}
    )

    def update_if_attr_doesnt_exist():
        # Test nonexistent top-level attribute.
        client.update_item(
            TableName="test",
            Key={"forum_name": {"S": "the-key"}, "subject": {"S": "the-subject"}},
            UpdateExpression="set #new_state=:new_state, #ttl=:ttl",
            ConditionExpression="attribute_not_exists(#new_state)",
            ExpressionAttributeNames={"#new_state": "foobar", "#ttl": "ttl"},
            ExpressionAttributeValues={
                ":new_state": {"S": "some-value"},
                ":ttl": {"N": "12345.67"},
            },
            ReturnValues="ALL_NEW",
        )

    update_if_attr_doesnt_exist()

    # Second time should fail
    with pytest.raises(client.exceptions.ConditionalCheckFailedException) as exc:
        update_if_attr_doesnt_exist()
    _assert_conditional_check_failed_exception(exc)


@mock_dynamodb
def test_condition_expression__or_order():
    client = boto3.client("dynamodb", region_name="us-east-1")

    client.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    # ensure that the RHS of the OR expression is not evaluated if the LHS
    # returns true (as it would result an error)
    client.update_item(
        TableName="test",
        Key={"forum_name": {"S": "the-key"}},
        UpdateExpression="set #ttl=:ttl",
        ConditionExpression="attribute_not_exists(#ttl) OR #ttl <= :old_ttl",
        ExpressionAttributeNames={"#ttl": "ttl"},
        ExpressionAttributeValues={":ttl": {"N": "6"}, ":old_ttl": {"N": "5"}},
    )


@mock_dynamodb
def test_condition_expression__and_order():
    client = boto3.client("dynamodb", region_name="us-east-1")

    client.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    # ensure that the RHS of the AND expression is not evaluated if the LHS
    # returns true (as it would result an error)
    with pytest.raises(client.exceptions.ConditionalCheckFailedException) as exc:
        client.update_item(
            TableName="test",
            Key={"forum_name": {"S": "the-key"}},
            UpdateExpression="set #ttl=:ttl",
            ConditionExpression="attribute_exists(#ttl) AND #ttl <= :old_ttl",
            ExpressionAttributeNames={"#ttl": "ttl"},
            ExpressionAttributeValues={":ttl": {"N": "6"}, ":old_ttl": {"N": "5"}},
        )
    _assert_conditional_check_failed_exception(exc)


@mock_dynamodb
def test_condition_expression_with_reserved_keyword_as_attr_name():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
    table_name = "Test"
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table = dynamodb.Table(table_name)

    email_like_str = "test@foo.com"
    record = {"id": "key-0", "first": {email_like_str: {"end": {"VALUE"}}}}
    table.put_item(Item=record)

    expected_error_message = re.escape(
        "An error occurred (ValidationException) when "
        "calling the UpdateItem operation: Invalid ConditionExpression: Attribute name "
        "is a reserved keyword; reserved keyword: end"
    )
    with pytest.raises(
        dynamodb.meta.client.exceptions.ClientError, match=expected_error_message
    ):
        table.update_item(
            Key={"id": "key-0"},
            UpdateExpression="REMOVE #first.#second, #other",
            ExpressionAttributeNames={
                "#first": "first",
                "#second": email_like_str,
                "#other": "other",
            },
            ExpressionAttributeValues={":value": "VALUE", ":one": 1},
            ConditionExpression="size(#first.#second.end) = :one AND contains(#first.#second.end, :value)",
            ReturnValues="ALL_NEW",
        )

    # table is unchanged
    item = table.get_item(Key={"id": "key-0"})["Item"]
    assert item == record

    # using attribute names solves the issue
    table.update_item(
        Key={"id": "key-0"},
        UpdateExpression="REMOVE #first.#second, #other",
        ExpressionAttributeNames={
            "#first": "first",
            "#second": email_like_str,
            "#other": "other",
            "#end": "end",
        },
        ExpressionAttributeValues={":value": "VALUE", ":one": 1},
        ConditionExpression="size(#first.#second.#end) = :one AND contains(#first.#second.#end, :value)",
        ReturnValues="ALL_NEW",
    )

    item = table.get_item(Key={"id": "key-0"})["Item"]
    assert item == {"id": "key-0", "first": {}}
