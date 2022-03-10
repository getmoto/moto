import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from boto3.dynamodb.conditions import Key
from moto import mock_dynamodb2


def test_deprecation_warning():
    with pytest.warns(None) as record:
        mock_dynamodb2()
    str(record[0].message).should.contain(
        "Module mock_dynamodb2 has been deprecated, and will be removed in a later release"
    )


"""
Copy some basics test from DynamoDB
Verify that the behaviour still works using the 'mock_dynamodb2' decorator
"""


@mock_dynamodb2
def test_basic_projection_expression_using_get_item():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")

    table.put_item(
        Item={"forum_name": "the-key", "subject": "123", "body": "some test message"}
    )

    table.put_item(
        Item={
            "forum_name": "not-the-key",
            "subject": "123",
            "body": "some other test message",
        }
    )
    result = table.get_item(
        Key={"forum_name": "the-key", "subject": "123"},
        ProjectionExpression="body, subject",
    )

    result["Item"].should.be.equal({"subject": "123", "body": "some test message"})

    # The projection expression should not remove data from storage
    result = table.get_item(Key={"forum_name": "the-key", "subject": "123"})

    result["Item"].should.be.equal(
        {"forum_name": "the-key", "subject": "123", "body": "some test message"}
    )


@mock_dynamodb2
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
    item.should.equal({"id": "key-0", "first": {}})


@mock_dynamodb2
def test_query_filter_boto3():
    table_schema = {
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
    }

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )

    for i in range(0, 3):
        table.put_item(Item={"pk": "pk".format(i), "sk": "sk-{}".format(i)})

    res = table.query(KeyConditionExpression=Key("pk").eq("pk"))
    res["Items"].should.have.length_of(3)

    res = table.query(KeyConditionExpression=Key("pk").eq("pk") & Key("sk").lt("sk-1"))
    res["Items"].should.have.length_of(1)
    res["Items"].should.equal([{"pk": "pk", "sk": "sk-0"}])

    res = table.query(KeyConditionExpression=Key("pk").eq("pk") & Key("sk").lte("sk-1"))
    res["Items"].should.have.length_of(2)
    res["Items"].should.equal([{"pk": "pk", "sk": "sk-0"}, {"pk": "pk", "sk": "sk-1"}])

    res = table.query(KeyConditionExpression=Key("pk").eq("pk") & Key("sk").gt("sk-1"))
    res["Items"].should.have.length_of(1)
    res["Items"].should.equal([{"pk": "pk", "sk": "sk-2"}])

    res = table.query(KeyConditionExpression=Key("pk").eq("pk") & Key("sk").gte("sk-1"))
    res["Items"].should.have.length_of(2)
    res["Items"].should.equal([{"pk": "pk", "sk": "sk-1"}, {"pk": "pk", "sk": "sk-2"}])
