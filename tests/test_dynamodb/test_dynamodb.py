import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key
import re
import sure  # noqa # pylint: disable=unused-import
from moto import mock_dynamodb, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.dynamodb import dynamodb_backends
from botocore.exceptions import ClientError

import moto.dynamodb.comparisons
import moto.dynamodb.models

import pytest


@mock_dynamodb
@pytest.mark.parametrize(
    "names",
    [[], ["TestTable"], ["TestTable1", "TestTable2"]],
    ids=["no-table", "one-table", "multiple-tables"],
)
def test_list_tables_boto3(names):
    conn = boto3.client("dynamodb", region_name="us-west-2")
    for name in names:
        conn.create_table(
            TableName=name,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
    conn.list_tables()["TableNames"].should.equal(names)


@mock_dynamodb
def test_list_tables_paginated():
    conn = boto3.client("dynamodb", region_name="us-west-2")
    for name in ["name1", "name2", "name3"]:
        conn.create_table(
            TableName=name,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )

    res = conn.list_tables(Limit=2)
    res.should.have.key("TableNames").equal(["name1", "name2"])
    res.should.have.key("LastEvaluatedTableName").equal("name2")

    res = conn.list_tables(Limit=1, ExclusiveStartTableName="name1")
    res.should.have.key("TableNames").equal(["name2"])
    res.should.have.key("LastEvaluatedTableName").equal("name2")

    res = conn.list_tables(ExclusiveStartTableName="name1")
    res.should.have.key("TableNames").equal(["name2", "name3"])
    res.shouldnt.have.key("LastEvaluatedTableName")


@mock_dynamodb
def test_describe_missing_table_boto3():
    conn = boto3.client("dynamodb", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.describe_table(TableName="messages")
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal("Requested resource not found")


@mock_dynamodb
def test_list_table_tags():
    name = "TestTable"
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table_description = conn.describe_table(TableName=name)
    arn = table_description["Table"]["TableArn"]

    # Tag table
    tags = [
        {"Key": "TestTag", "Value": "TestValue"},
        {"Key": "TestTag2", "Value": "TestValue2"},
    ]
    conn.tag_resource(ResourceArn=arn, Tags=tags)

    # Check tags
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert resp["Tags"] == tags

    # Remove 1 tag
    conn.untag_resource(ResourceArn=arn, TagKeys=["TestTag"])

    # Check tags
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert resp["Tags"] == [{"Key": "TestTag2", "Value": "TestValue2"}]


@mock_dynamodb
def test_list_table_tags_empty():
    name = "TestTable"
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table_description = conn.describe_table(TableName=name)
    arn = table_description["Table"]["TableArn"]
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert resp["Tags"] == []


@mock_dynamodb
def test_list_table_tags_paginated():
    name = "TestTable"
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table_description = conn.describe_table(TableName=name)
    arn = table_description["Table"]["TableArn"]
    for i in range(11):
        tags = [{"Key": f"TestTag{i}", "Value": "TestValue"}]
        conn.tag_resource(ResourceArn=arn, Tags=tags)
    resp = conn.list_tags_of_resource(ResourceArn=arn)
    assert len(resp["Tags"]) == 10
    assert "NextToken" in resp.keys()
    resp2 = conn.list_tags_of_resource(ResourceArn=arn, NextToken=resp["NextToken"])
    assert len(resp2["Tags"]) == 1
    assert "NextToken" not in resp2.keys()


@mock_dynamodb
def test_list_not_found_table_tags():
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )
    arn = "DymmyArn"
    try:
        conn.list_tags_of_resource(ResourceArn=arn)
    except ClientError as exception:
        assert exception.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_dynamodb
def test_item_add_empty_string_hash_key_exception():
    name = "TestTable"
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    with pytest.raises(ClientError) as ex:
        conn.put_item(
            TableName=name,
            Item={
                "forum_name": {"S": ""},
                "subject": {"S": "Check this out!"},
                "Body": {"S": "http://url_to_lolcat.gif"},
                "SentBy": {"S": "someone@somewhere.edu"},
                "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
            },
        )

    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.match(
        "One or more parameter values were invalid: An AttributeValue may not contain an empty string"
    )


@mock_dynamodb
def test_item_add_empty_string_range_key_exception():
    name = "TestTable"
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )
    conn.create_table(
        TableName=name,
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "ReceivedTime", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "ReceivedTime", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    with pytest.raises(ClientError) as ex:
        conn.put_item(
            TableName=name,
            Item={
                "forum_name": {"S": "LOLCat Forum"},
                "subject": {"S": "Check this out!"},
                "Body": {"S": "http://url_to_lolcat.gif"},
                "SentBy": {"S": "someone@somewhere.edu"},
                "ReceivedTime": {"S": ""},
            },
        )

    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.match(
        "One or more parameter values were invalid: An AttributeValue may not contain an empty string"
    )


@mock_dynamodb
def test_item_add_empty_string_attr_no_exception():
    name = "TestTable"
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    conn.put_item(
        TableName=name,
        Item={
            "forum_name": {"S": "LOLCat Forum"},
            "subject": {"S": "Check this out!"},
            "Body": {"S": "http://url_to_lolcat.gif"},
            "SentBy": {"S": ""},
            "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
        },
    )


@mock_dynamodb
def test_update_item_with_empty_string_attr_no_exception():
    name = "TestTable"
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    conn.put_item(
        TableName=name,
        Item={
            "forum_name": {"S": "LOLCat Forum"},
            "subject": {"S": "Check this out!"},
            "Body": {"S": "http://url_to_lolcat.gif"},
            "SentBy": {"S": "test"},
            "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
        },
    )

    conn.update_item(
        TableName=name,
        Key={"forum_name": {"S": "LOLCat Forum"}},
        UpdateExpression="set Body=:Body",
        ExpressionAttributeValues={":Body": {"S": ""}},
    )


@mock_dynamodb
def test_query_invalid_table():
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )
    try:
        conn.query(
            TableName="invalid_table",
            KeyConditionExpression="index1 = :partitionkeyval",
            ExpressionAttributeValues={":partitionkeyval": {"S": "test"}},
        )
    except ClientError as exception:
        assert exception.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_dynamodb
def test_put_item_with_special_chars():
    name = "TestTable"
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )

    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    conn.put_item(
        TableName=name,
        Item={
            "forum_name": {"S": "LOLCat Forum"},
            "subject": {"S": "Check this out!"},
            "Body": {"S": "http://url_to_lolcat.gif"},
            "SentBy": {"S": "test"},
            "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
            '"': {"S": "foo"},
        },
    )


@mock_dynamodb
def test_put_item_with_streams():
    name = "TestTable"
    conn = boto3.client(
        "dynamodb",
        region_name="us-west-2",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
    )

    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    conn.put_item(
        TableName=name,
        Item={
            "forum_name": {"S": "LOLCat Forum"},
            "subject": {"S": "Check this out!"},
            "Body": {"S": "http://url_to_lolcat.gif"},
            "SentBy": {"S": "test"},
            "Data": {"M": {"Key1": {"S": "Value1"}, "Key2": {"S": "Value2"}}},
        },
    )

    result = conn.get_item(TableName=name, Key={"forum_name": {"S": "LOLCat Forum"}})

    result["Item"].should.be.equal(
        {
            "forum_name": {"S": "LOLCat Forum"},
            "subject": {"S": "Check this out!"},
            "Body": {"S": "http://url_to_lolcat.gif"},
            "SentBy": {"S": "test"},
            "Data": {"M": {"Key1": {"S": "Value1"}, "Key2": {"S": "Value2"}}},
        }
    )

    if not settings.TEST_SERVER_MODE:
        table = dynamodb_backends[ACCOUNT_ID]["us-west-2"].get_table(name)
        len(table.stream_shard.items).should.be.equal(1)
        stream_record = table.stream_shard.items[0].record
        stream_record["eventName"].should.be.equal("INSERT")
        stream_record["dynamodb"]["SizeBytes"].should.be.equal(447)


@mock_dynamodb
def test_basic_projection_expression_using_get_item():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    client = boto3.client("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
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

    # Running this against AWS DDB gives an exception so make sure it also fails.:
    with pytest.raises(client.exceptions.ClientError):
        # botocore.exceptions.ClientError: An error occurred (ValidationException) when calling the GetItem
        # operation: "Can not use both expression and non-expression parameters in the same request:
        #  Non-expression parameters: {AttributesToGet} Expression parameters: {ProjectionExpression}"
        table.get_item(
            Key={"forum_name": "the-key", "subject": "123"},
            ProjectionExpression="body",
            AttributesToGet=["body"],
        )


@mock_dynamodb
def test_basic_projection_expressions_using_scan():
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
    # Test a scan returning all items
    results = table.scan(
        FilterExpression=Key("forum_name").eq("the-key"),
        ProjectionExpression="body, subject",
    )

    assert "body" in results["Items"][0]
    assert results["Items"][0]["body"] == "some test message"
    assert "subject" in results["Items"][0]

    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "1234",
            "body": "yet another test message",
        }
    )

    results = table.scan(
        FilterExpression=Key("forum_name").eq("the-key"), ProjectionExpression="body"
    )

    bodies = [item["body"] for item in results["Items"]]
    bodies.should.contain("some test message")
    bodies.should.contain("yet another test message")
    assert "subject" not in results["Items"][0]
    assert "forum_name" not in results["Items"][0]
    assert "subject" not in results["Items"][1]
    assert "forum_name" not in results["Items"][1]

    # The projection expression should not remove data from storage
    results = table.query(KeyConditionExpression=Key("forum_name").eq("the-key"))
    assert "subject" in results["Items"][0]
    assert "body" in results["Items"][1]
    assert "forum_name" in results["Items"][1]


@mock_dynamodb
def test_nested_projection_expression_using_get_item():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")
    table.put_item(
        Item={
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
            "foo": "bar",
        }
    )
    table.put_item(
        Item={
            "forum_name": "key2",
            "nested": {"id": "id2", "incode": "code2"},
            "foo": "bar",
        }
    )

    # Test a get_item returning all items
    result = table.get_item(
        Key={"forum_name": "key1"},
        ProjectionExpression="nested.level1.id, nested.level2",
    )["Item"]
    result.should.equal(
        {"nested": {"level1": {"id": "id1"}, "level2": {"id": "id2", "include": "all"}}}
    )
    # Assert actual data has not been deleted
    result = table.get_item(Key={"forum_name": "key1"})["Item"]
    result.should.equal(
        {
            "foo": "bar",
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
        }
    )


@mock_dynamodb
def test_basic_projection_expressions_using_query():
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

    # Test a query returning all items
    result = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key"),
        ProjectionExpression="body, subject",
    )["Items"][0]

    assert "body" in result
    assert result["body"] == "some test message"
    assert "subject" in result
    assert "forum_name" not in result

    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "1234",
            "body": "yet another test message",
        }
    )

    items = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key"),
        ProjectionExpression="body",
    )["Items"]

    assert "body" in items[0]
    assert "subject" not in items[0]
    assert items[0]["body"] == "some test message"
    assert "body" in items[1]
    assert "subject" not in items[1]
    assert items[1]["body"] == "yet another test message"

    # The projection expression should not remove data from storage
    items = table.query(KeyConditionExpression=Key("forum_name").eq("the-key"))["Items"]
    assert "subject" in items[0]
    assert "body" in items[1]
    assert "forum_name" in items[1]


@mock_dynamodb
def test_nested_projection_expression_using_query():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")
    table.put_item(
        Item={
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
            "foo": "bar",
        }
    )
    table.put_item(
        Item={
            "forum_name": "key2",
            "nested": {"id": "id2", "incode": "code2"},
            "foo": "bar",
        }
    )

    # Test a query returning all items
    result = table.query(
        KeyConditionExpression=Key("forum_name").eq("key1"),
        ProjectionExpression="nested.level1.id, nested.level2",
    )["Items"][0]

    assert "nested" in result
    result["nested"].should.equal(
        {"level1": {"id": "id1"}, "level2": {"id": "id2", "include": "all"}}
    )
    assert "foo" not in result
    # Assert actual data has not been deleted
    result = table.query(KeyConditionExpression=Key("forum_name").eq("key1"))["Items"][
        0
    ]
    result.should.equal(
        {
            "foo": "bar",
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
        }
    )


@mock_dynamodb
def test_nested_projection_expression_using_scan():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")
    table.put_item(
        Item={
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
            "foo": "bar",
        }
    )
    table.put_item(
        Item={
            "forum_name": "key2",
            "nested": {"id": "id2", "incode": "code2"},
            "foo": "bar",
        }
    )

    # Test a scan
    results = table.scan(
        FilterExpression=Key("forum_name").eq("key1"),
        ProjectionExpression="nested.level1.id, nested.level2",
    )["Items"]
    results.should.equal(
        [
            {
                "nested": {
                    "level1": {"id": "id1"},
                    "level2": {"include": "all", "id": "id2"},
                }
            }
        ]
    )
    # Assert original data is still there
    results = table.scan(FilterExpression=Key("forum_name").eq("key1"))["Items"]
    results.should.equal(
        [
            {
                "forum_name": "key1",
                "foo": "bar",
                "nested": {
                    "level1": {"att": "irrelevant", "id": "id1"},
                    "level2": {"include": "all", "id": "id2"},
                    "level3": {"id": "irrelevant"},
                },
            }
        ]
    )


@mock_dynamodb
def test_basic_projection_expression_using_get_item_with_attr_expression_names():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
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
        Item={
            "forum_name": "the-key",
            "subject": "123",
            "body": "some test message",
            "attachment": "something",
        }
    )

    table.put_item(
        Item={
            "forum_name": "not-the-key",
            "subject": "123",
            "body": "some other test message",
            "attachment": "something",
        }
    )
    result = table.get_item(
        Key={"forum_name": "the-key", "subject": "123"},
        ProjectionExpression="#rl, #rt, subject",
        ExpressionAttributeNames={"#rl": "body", "#rt": "attachment"},
    )

    result["Item"].should.be.equal(
        {"subject": "123", "body": "some test message", "attachment": "something"}
    )


@mock_dynamodb
def test_basic_projection_expressions_using_query_with_attr_expression_names():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
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
        Item={
            "forum_name": "the-key",
            "subject": "123",
            "body": "some test message",
            "attachment": "something",
        }
    )

    table.put_item(
        Item={
            "forum_name": "not-the-key",
            "subject": "123",
            "body": "some other test message",
            "attachment": "something",
        }
    )
    # Test a query returning all items

    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key"),
        ProjectionExpression="#rl, #rt, subject",
        ExpressionAttributeNames={"#rl": "body", "#rt": "attachment"},
    )

    assert "body" in results["Items"][0]
    assert results["Items"][0]["body"] == "some test message"
    assert "subject" in results["Items"][0]
    assert results["Items"][0]["subject"] == "123"
    assert "attachment" in results["Items"][0]
    assert results["Items"][0]["attachment"] == "something"


@mock_dynamodb
def test_nested_projection_expression_using_get_item_with_attr_expression():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")
    table.put_item(
        Item={
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
            "foo": "bar",
        }
    )
    table.put_item(
        Item={
            "forum_name": "key2",
            "nested": {"id": "id2", "incode": "code2"},
            "foo": "bar",
        }
    )

    # Test a get_item returning all items
    result = table.get_item(
        Key={"forum_name": "key1"},
        ProjectionExpression="#nst.level1.id, #nst.#lvl2",
        ExpressionAttributeNames={"#nst": "nested", "#lvl2": "level2"},
    )["Item"]
    result.should.equal(
        {"nested": {"level1": {"id": "id1"}, "level2": {"id": "id2", "include": "all"}}}
    )
    # Assert actual data has not been deleted
    result = table.get_item(Key={"forum_name": "key1"})["Item"]
    result.should.equal(
        {
            "foo": "bar",
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
        }
    )


@mock_dynamodb
def test_nested_projection_expression_using_query_with_attr_expression_names():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")
    table.put_item(
        Item={
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
            "foo": "bar",
        }
    )
    table.put_item(
        Item={
            "forum_name": "key2",
            "nested": {"id": "id2", "incode": "code2"},
            "foo": "bar",
        }
    )

    # Test a query returning all items
    result = table.query(
        KeyConditionExpression=Key("forum_name").eq("key1"),
        ProjectionExpression="#nst.level1.id, #nst.#lvl2",
        ExpressionAttributeNames={"#nst": "nested", "#lvl2": "level2"},
    )["Items"][0]

    assert "nested" in result
    result["nested"].should.equal(
        {"level1": {"id": "id1"}, "level2": {"id": "id2", "include": "all"}}
    )
    assert "foo" not in result
    # Assert actual data has not been deleted
    result = table.query(KeyConditionExpression=Key("forum_name").eq("key1"))["Items"][
        0
    ]
    result.should.equal(
        {
            "foo": "bar",
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
        }
    )


@mock_dynamodb
def test_basic_projection_expressions_using_scan_with_attr_expression_names():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
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
        Item={
            "forum_name": "the-key",
            "subject": "123",
            "body": "some test message",
            "attachment": "something",
        }
    )

    table.put_item(
        Item={
            "forum_name": "not-the-key",
            "subject": "123",
            "body": "some other test message",
            "attachment": "something",
        }
    )
    # Test a scan returning all items

    results = table.scan(
        FilterExpression=Key("forum_name").eq("the-key"),
        ProjectionExpression="#rl, #rt, subject",
        ExpressionAttributeNames={"#rl": "body", "#rt": "attachment"},
    )

    assert "body" in results["Items"][0]
    assert "attachment" in results["Items"][0]
    assert "subject" in results["Items"][0]
    assert "form_name" not in results["Items"][0]

    # Test without a FilterExpression
    results = table.scan(
        ProjectionExpression="#rl, #rt, subject",
        ExpressionAttributeNames={"#rl": "body", "#rt": "attachment"},
    )

    assert "body" in results["Items"][0]
    assert "attachment" in results["Items"][0]
    assert "subject" in results["Items"][0]
    assert "form_name" not in results["Items"][0]


@mock_dynamodb
def test_nested_projection_expression_using_scan_with_attr_expression_names():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")
    table.put_item(
        Item={
            "forum_name": "key1",
            "nested": {
                "level1": {"id": "id1", "att": "irrelevant"},
                "level2": {"id": "id2", "include": "all"},
                "level3": {"id": "irrelevant"},
            },
            "foo": "bar",
        }
    )
    table.put_item(
        Item={
            "forum_name": "key2",
            "nested": {"id": "id2", "incode": "code2"},
            "foo": "bar",
        }
    )

    # Test a scan
    results = table.scan(
        FilterExpression=Key("forum_name").eq("key1"),
        ProjectionExpression="nested.level1.id, nested.level2",
        ExpressionAttributeNames={"#nst": "nested", "#lvl2": "level2"},
    )["Items"]
    results.should.equal(
        [
            {
                "nested": {
                    "level1": {"id": "id1"},
                    "level2": {"include": "all", "id": "id2"},
                }
            }
        ]
    )
    # Assert original data is still there
    results = table.scan(FilterExpression=Key("forum_name").eq("key1"))["Items"]
    results.should.equal(
        [
            {
                "forum_name": "key1",
                "foo": "bar",
                "nested": {
                    "level1": {"att": "irrelevant", "id": "id1"},
                    "level2": {"include": "all", "id": "id2"},
                    "level3": {"id": "irrelevant"},
                },
            }
        ]
    )


@mock_dynamodb
def test_put_empty_item():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        AttributeDefinitions=[{"AttributeName": "structure_id", "AttributeType": "S"}],
        TableName="test",
        KeySchema=[{"AttributeName": "structure_id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
    )
    table = dynamodb.Table("test")

    with pytest.raises(ClientError) as ex:
        table.put_item(Item={})
    ex.value.response["Error"]["Message"].should.equal(
        "One or more parameter values were invalid: Missing the key structure_id in the item"
    )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")


@mock_dynamodb
def test_put_item_nonexisting_hash_key():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        AttributeDefinitions=[{"AttributeName": "structure_id", "AttributeType": "S"}],
        TableName="test",
        KeySchema=[{"AttributeName": "structure_id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
    )
    table = dynamodb.Table("test")

    with pytest.raises(ClientError) as ex:
        table.put_item(Item={"a_terribly_misguided_id_attribute": "abcdef"})
    ex.value.response["Error"]["Message"].should.equal(
        "One or more parameter values were invalid: Missing the key structure_id in the item"
    )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")


@mock_dynamodb
def test_put_item_nonexisting_range_key():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        AttributeDefinitions=[
            {"AttributeName": "structure_id", "AttributeType": "S"},
            {"AttributeName": "added_at", "AttributeType": "N"},
        ],
        TableName="test",
        KeySchema=[
            {"AttributeName": "structure_id", "KeyType": "HASH"},
            {"AttributeName": "added_at", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
    )
    table = dynamodb.Table("test")

    with pytest.raises(ClientError) as ex:
        table.put_item(Item={"structure_id": "abcdef"})
    ex.value.response["Error"]["Message"].should.equal(
        "One or more parameter values were invalid: Missing the key added_at in the item"
    )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")


def test_filter_expression():
    row1 = moto.dynamodb.models.Item(
        hash_key=None,
        range_key=None,
        attrs={
            "Id": {"N": "8"},
            "Subs": {"N": "5"},
            "Des": {"S": "Some description"},
            "KV": {"SS": ["test1", "test2"]},
        },
    )
    row2 = moto.dynamodb.models.Item(
        hash_key=None,
        range_key=None,
        attrs={
            "Id": {"N": "8"},
            "Subs": {"N": "10"},
            "Des": {"S": "A description"},
            "KV": {"SS": ["test3", "test4"]},
        },
    )

    # NOT test 1
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "NOT attribute_not_exists(Id)", {}, {}
    )
    filter_expr.expr(row1).should.be(True)

    # NOT test 2
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "NOT (Id = :v0)", {}, {":v0": {"N": "8"}}
    )
    filter_expr.expr(row1).should.be(False)  # Id = 8 so should be false

    # AND test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "Id > :v0 AND Subs < :v1", {}, {":v0": {"N": "5"}, ":v1": {"N": "7"}}
    )
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # lowercase AND test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "Id > :v0 and Subs < :v1", {}, {":v0": {"N": "5"}, ":v1": {"N": "7"}}
    )
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # OR test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "Id = :v0 OR Id=:v1", {}, {":v0": {"N": "5"}, ":v1": {"N": "8"}}
    )
    filter_expr.expr(row1).should.be(True)

    # BETWEEN test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "Id BETWEEN :v0 AND :v1", {}, {":v0": {"N": "5"}, ":v1": {"N": "10"}}
    )
    filter_expr.expr(row1).should.be(True)

    # BETWEEN integer test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "Id BETWEEN :v0 AND :v1", {}, {":v0": {"N": "0"}, ":v1": {"N": "10"}}
    )
    filter_expr.expr(row1).should.be(True)

    # PAREN test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "Id = :v0 AND (Subs = :v0 OR Subs = :v1)",
        {},
        {":v0": {"N": "8"}, ":v1": {"N": "5"}},
    )
    filter_expr.expr(row1).should.be(True)

    # IN test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "Id IN (:v0, :v1, :v2)",
        {},
        {":v0": {"N": "7"}, ":v1": {"N": "8"}, ":v2": {"N": "9"}},
    )
    filter_expr.expr(row1).should.be(True)

    # attribute function tests (with extra spaces)
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "attribute_exists(Id) AND attribute_not_exists (UnknownAttribute)", {}, {}
    )
    filter_expr.expr(row1).should.be(True)

    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "attribute_type(Id, :v0)", {}, {":v0": {"S": "N"}}
    )
    filter_expr.expr(row1).should.be(True)

    # beginswith function test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "begins_with(Des, :v0)", {}, {":v0": {"S": "Some"}}
    )
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # contains function test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "contains(KV, :v0)", {}, {":v0": {"S": "test1"}}
    )
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)

    # size function test
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "size(Des) > size(KV)", {}, {}
    )
    filter_expr.expr(row1).should.be(True)

    # Expression from @batkuip
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "(#n0 < :v0 AND attribute_not_exists(#n1))",
        {"#n0": "Subs", "#n1": "fanout_ts"},
        {":v0": {"N": "7"}},
    )
    filter_expr.expr(row1).should.be(True)
    # Expression from to check contains on string value
    filter_expr = moto.dynamodb.comparisons.get_filter_expression(
        "contains(#n0, :v0)", {"#n0": "Des"}, {":v0": {"S": "Some"}}
    )
    filter_expr.expr(row1).should.be(True)
    filter_expr.expr(row2).should.be(False)


@mock_dynamodb
def test_query_filter():
    client = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

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
            "nested": {
                "M": {
                    "version": {"S": "version1"},
                    "contents": {"L": [{"S": "value1"}, {"S": "value2"}]},
                }
            },
        },
    )
    client.put_item(
        TableName="test1",
        Item={
            "client": {"S": "client1"},
            "app": {"S": "app2"},
            "nested": {
                "M": {
                    "version": {"S": "version2"},
                    "contents": {"L": [{"S": "value1"}, {"S": "value2"}]},
                }
            },
        },
    )

    table = dynamodb.Table("test1")
    response = table.query(KeyConditionExpression=Key("client").eq("client1"))
    assert response["Count"] == 2

    response = table.query(
        KeyConditionExpression=Key("client").eq("client1"),
        FilterExpression=Attr("app").eq("app2"),
    )
    assert response["Count"] == 1
    assert response["Items"][0]["app"] == "app2"
    response = table.query(
        KeyConditionExpression=Key("client").eq("client1"),
        FilterExpression=Attr("app").contains("app"),
    )
    assert response["Count"] == 2

    response = table.query(
        KeyConditionExpression=Key("client").eq("client1"),
        FilterExpression=Attr("nested.version").contains("version"),
    )
    assert response["Count"] == 2

    response = table.query(
        KeyConditionExpression=Key("client").eq("client1"),
        FilterExpression=Attr("nested.contents[0]").eq("value1"),
    )
    assert response["Count"] == 2


@mock_dynamodb
def test_query_filter_overlapping_expression_prefixes():
    client = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

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
            "nested": {
                "M": {
                    "version": {"S": "version1"},
                    "contents": {"L": [{"S": "value1"}, {"S": "value2"}]},
                }
            },
        },
    )

    table = dynamodb.Table("test1")
    response = table.query(
        KeyConditionExpression=Key("client").eq("client1") & Key("app").eq("app1"),
        ProjectionExpression="#1, #10, nested",
        ExpressionAttributeNames={"#1": "client", "#10": "app"},
    )

    assert response["Count"] == 1
    assert response["Items"][0] == {
        "client": "client1",
        "app": "app1",
        "nested": {"version": "version1", "contents": ["value1", "value2"]},
    }


@mock_dynamodb
def test_scan_filter():
    client = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

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
        TableName="test1", Item={"client": {"S": "client1"}, "app": {"S": "app1"}}
    )

    table = dynamodb.Table("test1")
    response = table.scan(FilterExpression=Attr("app").eq("app2"))
    assert response["Count"] == 0

    response = table.scan(FilterExpression=Attr("app").eq("app1"))
    assert response["Count"] == 1

    response = table.scan(FilterExpression=Attr("app").ne("app2"))
    assert response["Count"] == 1

    response = table.scan(FilterExpression=Attr("app").ne("app1"))
    assert response["Count"] == 0


@mock_dynamodb
def test_scan_filter2():
    client = boto3.client("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    client.create_table(
        TableName="test1",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "N"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
    )
    client.put_item(
        TableName="test1", Item={"client": {"S": "client1"}, "app": {"N": "1"}}
    )

    response = client.scan(
        TableName="test1",
        Select="ALL_ATTRIBUTES",
        FilterExpression="#tb >= :dt",
        ExpressionAttributeNames={"#tb": "app"},
        ExpressionAttributeValues={":dt": {"N": str(1)}},
    )
    assert response["Count"] == 1


@mock_dynamodb
def test_scan_filter3():
    client = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    client.create_table(
        TableName="test1",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "N"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
    )
    client.put_item(
        TableName="test1",
        Item={"client": {"S": "client1"}, "app": {"N": "1"}, "active": {"BOOL": True}},
    )

    table = dynamodb.Table("test1")
    response = table.scan(FilterExpression=Attr("active").eq(True))
    assert response["Count"] == 1

    response = table.scan(FilterExpression=Attr("active").ne(True))
    assert response["Count"] == 0

    response = table.scan(FilterExpression=Attr("active").ne(False))
    assert response["Count"] == 1

    response = table.scan(FilterExpression=Attr("app").ne(1))
    assert response["Count"] == 0

    response = table.scan(FilterExpression=Attr("app").ne(2))
    assert response["Count"] == 1


@mock_dynamodb
def test_scan_filter4():
    client = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    client.create_table(
        TableName="test1",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "N"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
    )

    table = dynamodb.Table("test1")
    response = table.scan(
        FilterExpression=Attr("epoch_ts").lt(7) & Attr("fanout_ts").not_exists()
    )
    # Just testing
    assert response["Count"] == 0


@mock_dynamodb
def test_scan_filter_should_not_return_non_existing_attributes():
    table_name = "my-table"
    item = {"partitionKey": "pk-2", "my-attr": 42}
    # Create table
    res = boto3.resource("dynamodb", region_name="us-east-1")
    res.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "partitionKey", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "partitionKey", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table = res.Table(table_name)
    # Insert items
    table.put_item(Item={"partitionKey": "pk-1"})
    table.put_item(Item=item)
    # Verify a few operations
    # Assert we only find the item that has this attribute
    table.scan(FilterExpression=Attr("my-attr").lt(43))["Items"].should.equal([item])
    table.scan(FilterExpression=Attr("my-attr").lte(42))["Items"].should.equal([item])
    table.scan(FilterExpression=Attr("my-attr").gte(42))["Items"].should.equal([item])
    table.scan(FilterExpression=Attr("my-attr").gt(41))["Items"].should.equal([item])
    # Sanity check that we can't find the item if the FE is wrong
    table.scan(FilterExpression=Attr("my-attr").gt(43))["Items"].should.equal([])


@mock_dynamodb
def test_bad_scan_filter():
    client = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

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
    table = dynamodb.Table("test1")

    # Bad expression
    with pytest.raises(ClientError) as exc:
        table.scan(FilterExpression="client test")
    exc.value.response["Error"]["Code"].should.equal("ValidationException")


@mock_dynamodb
def test_duplicate_create():
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

    try:
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
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceInUseException")
    else:
        raise RuntimeError("Should have raised ResourceInUseException")


@mock_dynamodb
def test_delete_table():
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

    client.delete_table(TableName="test1")

    resp = client.list_tables()
    len(resp["TableNames"]).should.equal(0)

    try:
        client.delete_table(TableName="test1")
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    else:
        raise RuntimeError("Should have raised ResourceNotFoundException")


@mock_dynamodb
def test_delete_item():
    client = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

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
        TableName="test1", Item={"client": {"S": "client1"}, "app": {"S": "app1"}}
    )
    client.put_item(
        TableName="test1", Item={"client": {"S": "client1"}, "app": {"S": "app2"}}
    )

    table = dynamodb.Table("test1")
    response = table.scan()
    assert response["Count"] == 2

    # Test ReturnValues validation
    with pytest.raises(ClientError) as ex:
        table.delete_item(
            Key={"client": "client1", "app": "app1"}, ReturnValues="ALL_NEW"
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("Return values set to invalid value")

    # Test deletion and returning old value
    response = table.delete_item(
        Key={"client": "client1", "app": "app1"}, ReturnValues="ALL_OLD"
    )
    response["Attributes"].should.contain("client")
    response["Attributes"].should.contain("app")

    response = table.scan()
    assert response["Count"] == 1

    # Test deletion returning nothing
    response = table.delete_item(Key={"client": "client1", "app": "app2"})
    len(response["Attributes"]).should.equal(0)

    response = table.scan()
    assert response["Count"] == 0


@mock_dynamodb
def test_describe_limits():
    client = boto3.client("dynamodb", region_name="eu-central-1")
    resp = client.describe_limits()

    resp["AccountMaxReadCapacityUnits"].should.equal(20000)
    resp["AccountMaxWriteCapacityUnits"].should.equal(20000)
    resp["TableMaxWriteCapacityUnits"].should.equal(10000)
    resp["TableMaxReadCapacityUnits"].should.equal(10000)


@mock_dynamodb
def test_set_ttl():
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

    client.update_time_to_live(
        TableName="test1",
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "expire"},
    )

    resp = client.describe_time_to_live(TableName="test1")
    resp["TimeToLiveDescription"]["TimeToLiveStatus"].should.equal("ENABLED")
    resp["TimeToLiveDescription"]["AttributeName"].should.equal("expire")

    client.update_time_to_live(
        TableName="test1",
        TimeToLiveSpecification={"Enabled": False, "AttributeName": "expire"},
    )

    resp = client.describe_time_to_live(TableName="test1")
    resp["TimeToLiveDescription"]["TimeToLiveStatus"].should.equal("DISABLED")


@mock_dynamodb
def test_describe_continuous_backups():
    # given
    client = boto3.client("dynamodb", region_name="us-east-1")
    table_name = client.create_table(
        TableName="test",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )["TableDescription"]["TableName"]

    # when
    response = client.describe_continuous_backups(TableName=table_name)

    # then
    response["ContinuousBackupsDescription"].should.equal(
        {
            "ContinuousBackupsStatus": "ENABLED",
            "PointInTimeRecoveryDescription": {"PointInTimeRecoveryStatus": "DISABLED"},
        }
    )


@mock_dynamodb
def test_describe_continuous_backups_errors():
    # given
    client = boto3.client("dynamodb", region_name="us-east-1")

    # when
    with pytest.raises(Exception) as e:
        client.describe_continuous_backups(TableName="not-existing-table")

    # then
    ex = e.value
    ex.operation_name.should.equal("DescribeContinuousBackups")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("TableNotFoundException")
    ex.response["Error"]["Message"].should.equal("Table not found: not-existing-table")


@mock_dynamodb
def test_update_continuous_backups():
    # given
    client = boto3.client("dynamodb", region_name="us-east-1")
    table_name = client.create_table(
        TableName="test",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )["TableDescription"]["TableName"]

    # when
    response = client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    # then
    response["ContinuousBackupsDescription"]["ContinuousBackupsStatus"].should.equal(
        "ENABLED"
    )
    point_in_time = response["ContinuousBackupsDescription"][
        "PointInTimeRecoveryDescription"
    ]
    earliest_datetime = point_in_time["EarliestRestorableDateTime"]
    earliest_datetime.should.be.a(datetime)
    latest_datetime = point_in_time["LatestRestorableDateTime"]
    latest_datetime.should.be.a(datetime)
    point_in_time["PointInTimeRecoveryStatus"].should.equal("ENABLED")

    # when
    # a second update should not change anything
    response = client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    # then
    response["ContinuousBackupsDescription"]["ContinuousBackupsStatus"].should.equal(
        "ENABLED"
    )
    point_in_time = response["ContinuousBackupsDescription"][
        "PointInTimeRecoveryDescription"
    ]
    point_in_time["EarliestRestorableDateTime"].should.equal(earliest_datetime)
    point_in_time["LatestRestorableDateTime"].should.equal(latest_datetime)
    point_in_time["PointInTimeRecoveryStatus"].should.equal("ENABLED")

    # when
    response = client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": False},
    )

    # then
    response["ContinuousBackupsDescription"].should.equal(
        {
            "ContinuousBackupsStatus": "ENABLED",
            "PointInTimeRecoveryDescription": {"PointInTimeRecoveryStatus": "DISABLED"},
        }
    )


@mock_dynamodb
def test_update_continuous_backups_errors():
    # given
    client = boto3.client("dynamodb", region_name="us-east-1")

    # when
    with pytest.raises(Exception) as e:
        client.update_continuous_backups(
            TableName="not-existing-table",
            PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("UpdateContinuousBackups")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("TableNotFoundException")
    ex.response["Error"]["Message"].should.equal("Table not found: not-existing-table")


# https://github.com/spulec/moto/issues/1043
@mock_dynamodb
def test_query_missing_expr_names():
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
        TableName="test1", Item={"client": {"S": "test1"}, "app": {"S": "test1"}}
    )
    client.put_item(
        TableName="test1", Item={"client": {"S": "test2"}, "app": {"S": "test2"}}
    )

    resp = client.query(
        TableName="test1",
        KeyConditionExpression="client=:client",
        ExpressionAttributeValues={":client": {"S": "test1"}},
    )

    resp["Count"].should.equal(1)
    resp["Items"][0]["client"]["S"].should.equal("test1")

    resp = client.query(
        TableName="test1",
        KeyConditionExpression=":name=test2",
        ExpressionAttributeNames={":name": "client"},
    )

    resp["Count"].should.equal(1)
    resp["Items"][0]["client"]["S"].should.equal("test2")


# https://github.com/spulec/moto/issues/2328
@mock_dynamodb
def test_update_item_with_list():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="Table",
        KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table = dynamodb.Table("Table")
    table.update_item(
        Key={"key": "the-key"},
        AttributeUpdates={"list": {"Value": [1, 2], "Action": "PUT"}},
    )

    resp = table.get_item(Key={"key": "the-key"})
    resp["Item"].should.equal({"key": "the-key", "list": [1, 2]})


# https://github.com/spulec/moto/issues/2328
@mock_dynamodb
def test_update_item_with_no_action_passed_with_list():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="Table",
        KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table = dynamodb.Table("Table")
    table.update_item(
        Key={"key": "the-key"},
        # Do not pass 'Action' key, in order to check that the
        # parameter's default value will be used.
        AttributeUpdates={"list": {"Value": [1, 2]}},
    )

    resp = table.get_item(Key={"key": "the-key"})
    resp["Item"].should.equal({"key": "the-key", "list": [1, 2]})


# https://github.com/spulec/moto/issues/1342
@mock_dynamodb
def test_update_item_on_map():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    client = boto3.client("dynamodb", region_name="us-east-1")

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
        Item={
            "forum_name": "the-key",
            "subject": "123",
            "body": {"nested": {"data": "test"}},
        }
    )

    resp = table.scan()
    resp["Items"][0]["body"].should.equal({"nested": {"data": "test"}})

    # Nonexistent nested attributes are supported for existing top-level attributes.
    table.update_item(
        Key={"forum_name": "the-key", "subject": "123"},
        UpdateExpression="SET body.#nested.#data = :tb",
        ExpressionAttributeNames={"#nested": "nested", "#data": "data"},
        ExpressionAttributeValues={":tb": "new_value"},
    )
    # Running this against AWS DDB gives an exception so make sure it also fails.:
    with pytest.raises(client.exceptions.ClientError):
        # botocore.exceptions.ClientError: An error occurred (ValidationException) when calling the UpdateItem
        # operation: The document path provided in the update expression is invalid for update
        table.update_item(
            Key={"forum_name": "the-key", "subject": "123"},
            UpdateExpression="SET body.#nested.#nonexistentnested.#data = :tb2",
            ExpressionAttributeNames={
                "#nested": "nested",
                "#nonexistentnested": "nonexistentnested",
                "#data": "data",
            },
            ExpressionAttributeValues={":tb2": "other_value"},
        )

    table.update_item(
        Key={"forum_name": "the-key", "subject": "123"},
        UpdateExpression="SET body.#nested.#nonexistentnested = :tb2",
        ExpressionAttributeNames={
            "#nested": "nested",
            "#nonexistentnested": "nonexistentnested",
        },
        ExpressionAttributeValues={":tb2": {"data": "other_value"}},
    )

    resp = table.scan()
    resp["Items"][0]["body"].should.equal(
        {"nested": {"data": "new_value", "nonexistentnested": {"data": "other_value"}}}
    )

    # Test nested value for a nonexistent attribute throws a ClientError.
    with pytest.raises(client.exceptions.ClientError):
        table.update_item(
            Key={"forum_name": "the-key", "subject": "123"},
            UpdateExpression="SET nonexistent.#nested = :tb",
            ExpressionAttributeNames={"#nested": "nested"},
            ExpressionAttributeValues={":tb": "new_value"},
        )


# https://github.com/spulec/moto/issues/1358
@mock_dynamodb
def test_update_if_not_exists():
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

    table.put_item(Item={"forum_name": "the-key", "subject": "123"})

    table.update_item(
        Key={"forum_name": "the-key", "subject": "123"},
        # if_not_exists without space
        UpdateExpression="SET created_at=if_not_exists(created_at,:created_at)",
        ExpressionAttributeValues={":created_at": 123},
    )

    resp = table.scan()
    assert resp["Items"][0]["created_at"] == 123

    table.update_item(
        Key={"forum_name": "the-key", "subject": "123"},
        # if_not_exists with space
        UpdateExpression="SET created_at = if_not_exists (created_at, :created_at)",
        ExpressionAttributeValues={":created_at": 456},
    )

    resp = table.scan()
    # Still the original value
    assert resp["Items"][0]["created_at"] == 123


# https://github.com/spulec/moto/issues/1937
@mock_dynamodb
def test_update_return_attributes():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="moto-test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    def update(col, to, rv):
        return dynamodb.update_item(
            TableName="moto-test",
            Key={"id": {"S": "foo"}},
            AttributeUpdates={col: {"Value": {"S": to}, "Action": "PUT"}},
            ReturnValues=rv,
        )

    r = update("col1", "val1", "ALL_NEW")
    assert r["Attributes"] == {"id": {"S": "foo"}, "col1": {"S": "val1"}}

    r = update("col1", "val2", "ALL_OLD")
    assert r["Attributes"] == {"id": {"S": "foo"}, "col1": {"S": "val1"}}

    r = update("col2", "val3", "UPDATED_NEW")
    assert r["Attributes"] == {"col2": {"S": "val3"}}

    r = update("col2", "val4", "UPDATED_OLD")
    assert r["Attributes"] == {"col2": {"S": "val3"}}

    r = update("col1", "val5", "NONE")
    assert r["Attributes"] == {}

    with pytest.raises(ClientError) as ex:
        update("col1", "val6", "WRONG")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("Return values set to invalid value")


# https://github.com/spulec/moto/issues/3448
@mock_dynamodb
def test_update_return_updated_new_attributes_when_same():
    dynamo_client = boto3.resource("dynamodb", region_name="us-east-1")
    dynamo_client.create_table(
        TableName="moto-test",
        KeySchema=[{"AttributeName": "HashKey1", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "HashKey1", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    dynamodb_table = dynamo_client.Table("moto-test")
    dynamodb_table.put_item(
        Item={"HashKey1": "HashKeyValue1", "listValuedAttribute1": ["a", "b"]}
    )

    def update(col, to, rv):
        return dynamodb_table.update_item(
            TableName="moto-test",
            Key={"HashKey1": "HashKeyValue1"},
            UpdateExpression="SET listValuedAttribute1=:" + col,
            ExpressionAttributeValues={":" + col: to},
            ReturnValues=rv,
        )

    r = update("a", ["a", "c"], "UPDATED_NEW")
    assert r["Attributes"] == {"listValuedAttribute1": ["a", "c"]}

    r = update("a", {"a", "c"}, "UPDATED_NEW")
    assert r["Attributes"] == {"listValuedAttribute1": {"a", "c"}}

    r = update("a", {1, 2}, "UPDATED_NEW")
    assert r["Attributes"] == {"listValuedAttribute1": {1, 2}}

    with pytest.raises(ClientError) as ex:
        update("a", ["a", "c"], "WRONG")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("Return values set to invalid value")


@mock_dynamodb
def test_put_return_attributes():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="moto-test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    r = dynamodb.put_item(
        TableName="moto-test",
        Item={"id": {"S": "foo"}, "col1": {"S": "val1"}},
        ReturnValues="NONE",
    )
    assert "Attributes" not in r

    r = dynamodb.put_item(
        TableName="moto-test",
        Item={"id": {"S": "foo"}, "col1": {"S": "val2"}},
        ReturnValues="ALL_OLD",
    )
    assert r["Attributes"] == {"id": {"S": "foo"}, "col1": {"S": "val1"}}

    with pytest.raises(ClientError) as ex:
        dynamodb.put_item(
            TableName="moto-test",
            Item={"id": {"S": "foo"}, "col1": {"S": "val3"}},
            ReturnValues="ALL_NEW",
        )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "Return values set to invalid value"
    )


@mock_dynamodb
def test_query_global_secondary_index_when_created_via_update_table_resource():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "N"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")
    table.update(
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        GlobalSecondaryIndexUpdates=[
            {
                "Create": {
                    "IndexName": "forum_name_index",
                    "KeySchema": [{"AttributeName": "forum_name", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            }
        ],
    )

    next_user_id = 1
    for my_forum_name in ["cats", "dogs"]:
        for my_subject in [
            "my pet is the cutest",
            "wow look at what my pet did",
            "don't you love my pet?",
        ]:
            table.put_item(
                Item={
                    "user_id": next_user_id,
                    "forum_name": my_forum_name,
                    "subject": my_subject,
                }
            )
            next_user_id += 1

    # get all the cat users
    forum_only_query_response = table.query(
        IndexName="forum_name_index",
        Select="ALL_ATTRIBUTES",
        KeyConditionExpression=Key("forum_name").eq("cats"),
    )
    forum_only_items = forum_only_query_response["Items"]
    assert len(forum_only_items) == 3
    for item in forum_only_items:
        assert item["forum_name"] == "cats"

    # query all cat users with a particular subject
    forum_and_subject_query_results = table.query(
        IndexName="forum_name_index",
        Select="ALL_ATTRIBUTES",
        KeyConditionExpression=Key("forum_name").eq("cats"),
        FilterExpression=Attr("subject").eq("my pet is the cutest"),
    )
    forum_and_subject_items = forum_and_subject_query_results["Items"]
    assert len(forum_and_subject_items) == 1
    assert forum_and_subject_items[0] == {
        "user_id": Decimal("1"),
        "forum_name": "cats",
        "subject": "my pet is the cutest",
    }


@mock_dynamodb
def test_query_gsi_with_range_key():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "gsi_hash_key", "AttributeType": "S"},
            {"AttributeName": "gsi_range_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [
                    {"AttributeName": "gsi_hash_key", "KeyType": "HASH"},
                    {"AttributeName": "gsi_range_key", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )

    dynamodb.put_item(
        TableName="test",
        Item={
            "id": {"S": "test1"},
            "gsi_hash_key": {"S": "key1"},
            "gsi_range_key": {"S": "range1"},
        },
    )
    dynamodb.put_item(
        TableName="test", Item={"id": {"S": "test2"}, "gsi_hash_key": {"S": "key1"}}
    )

    res = dynamodb.query(
        TableName="test",
        IndexName="test_gsi",
        KeyConditionExpression="gsi_hash_key = :gsi_hash_key and gsi_range_key = :gsi_range_key",
        ExpressionAttributeValues={
            ":gsi_hash_key": {"S": "key1"},
            ":gsi_range_key": {"S": "range1"},
        },
    )
    res.should.have.key("Count").equal(1)
    res.should.have.key("Items")
    res["Items"][0].should.equal(
        {
            "id": {"S": "test1"},
            "gsi_hash_key": {"S": "key1"},
            "gsi_range_key": {"S": "range1"},
        }
    )


@mock_dynamodb
def test_scan_by_non_exists_index():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "gsi_col", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [{"AttributeName": "gsi_col", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )

    with pytest.raises(ClientError) as ex:
        dynamodb.scan(TableName="test", IndexName="non_exists_index")

    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "The table does not have the specified index: non_exists_index"
    )


@mock_dynamodb
def test_query_by_non_exists_index():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "gsi_col", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [{"AttributeName": "gsi_col", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )

    with pytest.raises(ClientError) as ex:
        dynamodb.query(
            TableName="test",
            IndexName="non_exists_index",
            KeyConditionExpression="CarModel=M",
        )

    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["Error"]["Message"].should.equal(
        "Invalid index: non_exists_index for table: test. Available indexes are: test_gsi"
    )


@mock_dynamodb
def test_index_with_unknown_attributes_should_fail():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    expected_exception = (
        "Some index key attributes are not defined in AttributeDefinitions."
    )

    with pytest.raises(ClientError) as ex:
        dynamodb.create_table(
            AttributeDefinitions=[
                {"AttributeName": "customer_nr", "AttributeType": "S"},
                {"AttributeName": "last_name", "AttributeType": "S"},
            ],
            TableName="table_with_missing_attribute_definitions",
            KeySchema=[
                {"AttributeName": "customer_nr", "KeyType": "HASH"},
                {"AttributeName": "last_name", "KeyType": "RANGE"},
            ],
            LocalSecondaryIndexes=[
                {
                    "IndexName": "indexthataddsanadditionalattribute",
                    "KeySchema": [
                        {"AttributeName": "customer_nr", "KeyType": "HASH"},
                        {"AttributeName": "postcode", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.contain(expected_exception)


@mock_dynamodb
def test_update_list_index__set_existing_index():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name,
        Item={
            "id": {"S": "foo"},
            "itemlist": {"L": [{"S": "bar1"}, {"S": "bar2"}, {"S": "bar3"}]},
        },
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo"}},
        UpdateExpression="set itemlist[1]=:Item",
        ExpressionAttributeValues={":Item": {"S": "bar2_update"}},
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo"}})["Item"]
    result["id"].should.equal({"S": "foo"})
    result["itemlist"].should.equal(
        {"L": [{"S": "bar1"}, {"S": "bar2_update"}, {"S": "bar3"}]}
    )


@mock_dynamodb
def test_update_list_index__set_existing_nested_index():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name,
        Item={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {"itemlist": {"L": [{"S": "bar1"}, {"S": "bar2"}, {"S": "bar3"}]}}
            },
        },
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo2"}},
        UpdateExpression="set itemmap.itemlist[1]=:Item",
        ExpressionAttributeValues={":Item": {"S": "bar2_update"}},
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo2"}})["Item"]
    result["id"].should.equal({"S": "foo2"})
    result["itemmap"]["M"]["itemlist"]["L"].should.equal(
        [{"S": "bar1"}, {"S": "bar2_update"}, {"S": "bar3"}]
    )


@mock_dynamodb
def test_update_list_index__set_index_out_of_range():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name,
        Item={
            "id": {"S": "foo"},
            "itemlist": {"L": [{"S": "bar1"}, {"S": "bar2"}, {"S": "bar3"}]},
        },
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo"}},
        UpdateExpression="set itemlist[10]=:Item",
        ExpressionAttributeValues={":Item": {"S": "bar10"}},
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo"}})["Item"]
    assert result["id"] == {"S": "foo"}
    assert result["itemlist"] == {
        "L": [{"S": "bar1"}, {"S": "bar2"}, {"S": "bar3"}, {"S": "bar10"}]
    }


@mock_dynamodb
def test_update_list_index__set_nested_index_out_of_range():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name,
        Item={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {"itemlist": {"L": [{"S": "bar1"}, {"S": "bar2"}, {"S": "bar3"}]}}
            },
        },
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo2"}},
        UpdateExpression="set itemmap.itemlist[10]=:Item",
        ExpressionAttributeValues={":Item": {"S": "bar10"}},
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo2"}})["Item"]
    assert result["id"] == {"S": "foo2"}
    assert result["itemmap"]["M"]["itemlist"]["L"] == [
        {"S": "bar1"},
        {"S": "bar2"},
        {"S": "bar3"},
        {"S": "bar10"},
    ]


@mock_dynamodb
def test_update_list_index__set_double_nested_index():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name,
        Item={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {
                    "itemlist": {
                        "L": [
                            {"M": {"foo": {"S": "bar11"}, "foos": {"S": "bar12"}}},
                            {"M": {"foo": {"S": "bar21"}, "foos": {"S": "bar21"}}},
                        ]
                    }
                }
            },
        },
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo2"}},
        UpdateExpression="set itemmap.itemlist[1].foos=:Item",
        ExpressionAttributeValues={":Item": {"S": "bar22"}},
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo2"}})["Item"]
    assert result["id"] == {"S": "foo2"}
    len(result["itemmap"]["M"]["itemlist"]["L"]).should.equal(2)
    result["itemmap"]["M"]["itemlist"]["L"][0].should.equal(
        {"M": {"foo": {"S": "bar11"}, "foos": {"S": "bar12"}}}
    )  # unchanged
    result["itemmap"]["M"]["itemlist"]["L"][1].should.equal(
        {"M": {"foo": {"S": "bar21"}, "foos": {"S": "bar22"}}}
    )  # updated


@mock_dynamodb
def test_update_list_index__set_index_of_a_string():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name, Item={"id": {"S": "foo2"}, "itemstr": {"S": "somestring"}}
    )
    with pytest.raises(ClientError) as ex:
        client.update_item(
            TableName=table_name,
            Key={"id": {"S": "foo2"}},
            UpdateExpression="set itemstr[1]=:Item",
            ExpressionAttributeValues={":Item": {"S": "string_update"}},
        )
        client.get_item(TableName=table_name, Key={"id": {"S": "foo2"}})["Item"]

    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.equal(
        "The document path provided in the update expression is invalid for update"
    )


@mock_dynamodb
def test_remove_top_level_attribute():
    table_name = "test_remove"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name, Item={"id": {"S": "foo"}, "item": {"S": "bar"}}
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo"}},
        UpdateExpression="REMOVE #i",
        ExpressionAttributeNames={"#i": "item"},
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo"}})["Item"]
    result.should.equal({"id": {"S": "foo"}})


@mock_dynamodb
def test_remove_top_level_attribute_non_existent():
    """
    Remove statements do not require attribute to exist they silently pass
    """
    table_name = "test_remove"
    client = create_table_with_list(table_name)
    ddb_item = {"id": {"S": "foo"}, "item": {"S": "bar"}}
    client.put_item(TableName=table_name, Item=ddb_item)
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo"}},
        UpdateExpression="REMOVE non_existent_attribute",
        ExpressionAttributeNames={"#i": "item"},
    )
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo"}})["Item"]
    result.should.equal(ddb_item)


@mock_dynamodb
def test_remove_list_index__remove_existing_index():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name,
        Item={
            "id": {"S": "foo"},
            "itemlist": {"L": [{"S": "bar1"}, {"S": "bar2"}, {"S": "bar3"}]},
        },
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo"}},
        UpdateExpression="REMOVE itemlist[1]",
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo"}})["Item"]
    result["id"].should.equal({"S": "foo"})
    result["itemlist"].should.equal({"L": [{"S": "bar1"}, {"S": "bar3"}]})


@mock_dynamodb
def test_remove_list_index__remove_existing_nested_index():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name,
        Item={
            "id": {"S": "foo2"},
            "itemmap": {"M": {"itemlist": {"L": [{"S": "bar1"}, {"S": "bar2"}]}}},
        },
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo2"}},
        UpdateExpression="REMOVE itemmap.itemlist[1]",
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo2"}})["Item"]
    result["id"].should.equal({"S": "foo2"})
    result["itemmap"]["M"]["itemlist"]["L"].should.equal([{"S": "bar1"}])


@mock_dynamodb
def test_remove_list_index__remove_existing_double_nested_index():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name,
        Item={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {
                    "itemlist": {
                        "L": [
                            {"M": {"foo00": {"S": "bar1"}, "foo01": {"S": "bar2"}}},
                            {"M": {"foo10": {"S": "bar1"}, "foo11": {"S": "bar2"}}},
                        ]
                    }
                }
            },
        },
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo2"}},
        UpdateExpression="REMOVE itemmap.itemlist[1].foo10",
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo2"}})["Item"]
    assert result["id"] == {"S": "foo2"}
    assert result["itemmap"]["M"]["itemlist"]["L"][0]["M"].should.equal(
        {"foo00": {"S": "bar1"}, "foo01": {"S": "bar2"}}
    )  # untouched
    assert result["itemmap"]["M"]["itemlist"]["L"][1]["M"].should.equal(
        {"foo11": {"S": "bar2"}}
    )  # changed


@mock_dynamodb
def test_remove_list_index__remove_index_out_of_range():
    table_name = "test_list_index_access"
    client = create_table_with_list(table_name)
    client.put_item(
        TableName=table_name,
        Item={
            "id": {"S": "foo"},
            "itemlist": {"L": [{"S": "bar1"}, {"S": "bar2"}, {"S": "bar3"}]},
        },
    )
    client.update_item(
        TableName=table_name,
        Key={"id": {"S": "foo"}},
        UpdateExpression="REMOVE itemlist[10]",
    )
    #
    result = client.get_item(TableName=table_name, Key={"id": {"S": "foo"}})["Item"]
    assert result["id"] == {"S": "foo"}
    assert result["itemlist"] == {"L": [{"S": "bar1"}, {"S": "bar2"}, {"S": "bar3"}]}


def create_table_with_list(table_name):
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    return client


@mock_dynamodb
def test_sorted_query_with_numerical_sort_key():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="CarCollection",
        KeySchema=[
            {"AttributeName": "CarModel", "KeyType": "HASH"},
            {"AttributeName": "CarPrice", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "CarModel", "AttributeType": "S"},
            {"AttributeName": "CarPrice", "AttributeType": "N"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    def create_item(price):
        return {"CarModel": "M", "CarPrice": price}

    table = dynamodb.Table("CarCollection")
    items = list(map(create_item, [2, 1, 10, 3]))
    for item in items:
        table.put_item(Item=item)

    response = table.query(KeyConditionExpression=Key("CarModel").eq("M"))

    response_items = response["Items"]
    assert len(items) == len(response_items)
    assert all(isinstance(item["CarPrice"], Decimal) for item in response_items)
    response_prices = [item["CarPrice"] for item in response_items]
    expected_prices = [Decimal(item["CarPrice"]) for item in items]
    expected_prices.sort()
    assert (
        expected_prices == response_prices
    ), "result items are not sorted by numerical value"


# https://github.com/spulec/moto/issues/1874
@mock_dynamodb
def test_item_size_is_under_400KB():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    client = boto3.client("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="moto-test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table = dynamodb.Table("moto-test")

    large_item = "x" * 410 * 1000
    assert_failure_due_to_item_size(
        func=client.put_item,
        TableName="moto-test",
        Item={"id": {"S": "foo"}, "cont": {"S": large_item}},
    )
    assert_failure_due_to_item_size(
        func=table.put_item, Item={"id": "bar", "cont": large_item}
    )
    assert_failure_due_to_item_size_to_update(
        func=client.update_item,
        TableName="moto-test",
        Key={"id": {"S": "foo2"}},
        UpdateExpression="set cont=:Item",
        ExpressionAttributeValues={":Item": {"S": large_item}},
    )
    # Assert op fails when updating a nested item
    assert_failure_due_to_item_size(
        func=table.put_item, Item={"id": "bar", "itemlist": [{"cont": large_item}]}
    )
    assert_failure_due_to_item_size(
        func=client.put_item,
        TableName="moto-test",
        Item={
            "id": {"S": "foo"},
            "itemlist": {"L": [{"M": {"item1": {"S": large_item}}}]},
        },
    )


def assert_failure_due_to_item_size(func, **kwargs):
    with pytest.raises(ClientError) as ex:
        func(**kwargs)
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.equal(
        "Item size has exceeded the maximum allowed size"
    )


def assert_failure_due_to_item_size_to_update(func, **kwargs):
    with pytest.raises(ClientError) as ex:
        func(**kwargs)
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.equal(
        "Item size to update has exceeded the maximum allowed size"
    )


@mock_dynamodb
def test_update_supports_complex_expression_attribute_values():
    client = boto3.client("dynamodb", region_name="us-east-1")

    client.create_table(
        AttributeDefinitions=[{"AttributeName": "SHA256", "AttributeType": "S"}],
        TableName="TestTable",
        KeySchema=[{"AttributeName": "SHA256", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    client.update_item(
        TableName="TestTable",
        Key={"SHA256": {"S": "sha-of-file"}},
        UpdateExpression=(
            "SET MD5 = :md5," "MyStringSet = :string_set," "MyMap = :map"
        ),
        ExpressionAttributeValues={
            ":md5": {"S": "md5-of-file"},
            ":string_set": {"SS": ["string1", "string2"]},
            ":map": {"M": {"EntryKey": {"SS": ["thing1", "thing2"]}}},
        },
    )
    result = client.get_item(
        TableName="TestTable", Key={"SHA256": {"S": "sha-of-file"}}
    )["Item"]
    result.should.equal(
        {
            "MyStringSet": {"SS": ["string1", "string2"]},
            "MyMap": {"M": {"EntryKey": {"SS": ["thing1", "thing2"]}}},
            "SHA256": {"S": "sha-of-file"},
            "MD5": {"S": "md5-of-file"},
        }
    )


@mock_dynamodb
def test_update_supports_list_append():
    # Verify whether the list_append operation works as expected
    client = boto3.client("dynamodb", region_name="us-east-1")

    client.create_table(
        AttributeDefinitions=[{"AttributeName": "SHA256", "AttributeType": "S"}],
        TableName="TestTable",
        KeySchema=[{"AttributeName": "SHA256", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    client.put_item(
        TableName="TestTable",
        Item={"SHA256": {"S": "sha-of-file"}, "crontab": {"L": [{"S": "bar1"}]}},
    )

    # Update item using list_append expression
    updated_item = client.update_item(
        TableName="TestTable",
        Key={"SHA256": {"S": "sha-of-file"}},
        UpdateExpression="SET crontab = list_append(crontab, :i)",
        ExpressionAttributeValues={":i": {"L": [{"S": "bar2"}]}},
        ReturnValues="UPDATED_NEW",
    )

    # Verify updated item is correct
    updated_item["Attributes"].should.equal(
        {"crontab": {"L": [{"S": "bar1"}, {"S": "bar2"}]}}
    )
    # Verify item is appended to the existing list
    result = client.get_item(
        TableName="TestTable", Key={"SHA256": {"S": "sha-of-file"}}
    )["Item"]
    result.should.equal(
        {
            "SHA256": {"S": "sha-of-file"},
            "crontab": {"L": [{"S": "bar1"}, {"S": "bar2"}]},
        }
    )


@mock_dynamodb
def test_update_supports_nested_list_append():
    # Verify whether we can append a list that's inside a map
    client = boto3.client("dynamodb", region_name="us-east-1")

    client.create_table(
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        TableName="TestTable",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    client.put_item(
        TableName="TestTable",
        Item={
            "id": {"S": "nested_list_append"},
            "a": {"M": {"b": {"L": [{"S": "bar1"}]}}},
        },
    )

    # Update item using list_append expression
    updated_item = client.update_item(
        TableName="TestTable",
        Key={"id": {"S": "nested_list_append"}},
        UpdateExpression="SET a.#b = list_append(a.#b, :i)",
        ExpressionAttributeValues={":i": {"L": [{"S": "bar2"}]}},
        ExpressionAttributeNames={"#b": "b"},
        ReturnValues="UPDATED_NEW",
    )

    # Verify updated item is correct
    updated_item["Attributes"].should.equal(
        {"a": {"M": {"b": {"L": [{"S": "bar1"}, {"S": "bar2"}]}}}}
    )
    result = client.get_item(
        TableName="TestTable", Key={"id": {"S": "nested_list_append"}}
    )["Item"]
    result.should.equal(
        {
            "id": {"S": "nested_list_append"},
            "a": {"M": {"b": {"L": [{"S": "bar1"}, {"S": "bar2"}]}}},
        }
    )


@mock_dynamodb
def test_update_supports_multiple_levels_nested_list_append():
    # Verify whether we can append a list that's inside a map that's inside a map  (Inception!)
    client = boto3.client("dynamodb", region_name="us-east-1")

    client.create_table(
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        TableName="TestTable",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    client.put_item(
        TableName="TestTable",
        Item={
            "id": {"S": "nested_list_append"},
            "a": {"M": {"b": {"M": {"c": {"L": [{"S": "bar1"}]}}}}},
        },
    )

    # Update item using list_append expression
    updated_item = client.update_item(
        TableName="TestTable",
        Key={"id": {"S": "nested_list_append"}},
        UpdateExpression="SET a.#b.c = list_append(a.#b.#c, :i)",
        ExpressionAttributeValues={":i": {"L": [{"S": "bar2"}]}},
        ExpressionAttributeNames={"#b": "b", "#c": "c"},
        ReturnValues="UPDATED_NEW",
    )

    # Verify updated item is correct
    updated_item["Attributes"].should.equal(
        {"a": {"M": {"b": {"M": {"c": {"L": [{"S": "bar1"}, {"S": "bar2"}]}}}}}}
    )
    # Verify item is appended to the existing list
    result = client.get_item(
        TableName="TestTable", Key={"id": {"S": "nested_list_append"}}
    )["Item"]
    result.should.equal(
        {
            "id": {"S": "nested_list_append"},
            "a": {"M": {"b": {"M": {"c": {"L": [{"S": "bar1"}, {"S": "bar2"}]}}}}},
        }
    )


@mock_dynamodb
def test_update_supports_nested_list_append_onto_another_list():
    # Verify whether we can take the contents of one list, and use that to fill another list
    # Note that the contents of the other list is completely overwritten
    client = boto3.client("dynamodb", region_name="us-east-1")

    client.create_table(
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        TableName="TestTable",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    client.put_item(
        TableName="TestTable",
        Item={
            "id": {"S": "list_append_another"},
            "a": {"M": {"b": {"L": [{"S": "bar1"}]}, "c": {"L": [{"S": "car1"}]}}},
        },
    )

    # Update item using list_append expression
    updated_item = client.update_item(
        TableName="TestTable",
        Key={"id": {"S": "list_append_another"}},
        UpdateExpression="SET a.#c = list_append(a.#b, :i)",
        ExpressionAttributeValues={":i": {"L": [{"S": "bar2"}]}},
        ExpressionAttributeNames={"#b": "b", "#c": "c"},
        ReturnValues="UPDATED_NEW",
    )

    # Verify updated item is correct
    updated_item["Attributes"].should.equal(
        {"a": {"M": {"c": {"L": [{"S": "bar1"}, {"S": "bar2"}]}}}}
    )
    # Verify item is appended to the existing list
    result = client.get_item(
        TableName="TestTable", Key={"id": {"S": "list_append_another"}}
    )["Item"]
    result.should.equal(
        {
            "id": {"S": "list_append_another"},
            "a": {
                "M": {
                    "b": {"L": [{"S": "bar1"}]},
                    "c": {"L": [{"S": "bar1"}, {"S": "bar2"}]},
                }
            },
        }
    )


@mock_dynamodb
def test_update_supports_list_append_maps():
    client = boto3.client("dynamodb", region_name="us-west-1")
    client.create_table(
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "rid", "AttributeType": "S"},
        ],
        TableName="TestTable",
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
            {"AttributeName": "rid", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    client.put_item(
        TableName="TestTable",
        Item={
            "id": {"S": "nested_list_append"},
            "rid": {"S": "range_key"},
            "a": {"L": [{"M": {"b": {"S": "bar1"}}}]},
        },
    )

    # Update item using list_append expression
    updated_item = client.update_item(
        TableName="TestTable",
        Key={"id": {"S": "nested_list_append"}, "rid": {"S": "range_key"}},
        UpdateExpression="SET a = list_append(a, :i)",
        ExpressionAttributeValues={":i": {"L": [{"M": {"b": {"S": "bar2"}}}]}},
        ReturnValues="UPDATED_NEW",
    )

    # Verify updated item is correct
    updated_item["Attributes"].should.equal(
        {"a": {"L": [{"M": {"b": {"S": "bar1"}}}, {"M": {"b": {"S": "bar2"}}}]}}
    )
    # Verify item is appended to the existing list
    result = client.query(
        TableName="TestTable",
        KeyConditionExpression="id = :i AND begins_with(rid, :r)",
        ExpressionAttributeValues={
            ":i": {"S": "nested_list_append"},
            ":r": {"S": "range_key"},
        },
    )["Items"]
    result.should.equal(
        [
            {
                "a": {"L": [{"M": {"b": {"S": "bar1"}}}, {"M": {"b": {"S": "bar2"}}}]},
                "rid": {"S": "range_key"},
                "id": {"S": "nested_list_append"},
            }
        ]
    )


@mock_dynamodb
def test_update_supports_nested_update_if_nested_value_not_exists():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    name = "TestTable"

    dynamodb.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    table = dynamodb.Table(name)
    table.put_item(
        Item={"user_id": "1234", "friends": {"5678": {"name": "friend_5678"}}}
    )
    table.update_item(
        Key={"user_id": "1234"},
        ExpressionAttributeNames={"#friends": "friends", "#friendid": "0000"},
        ExpressionAttributeValues={":friend": {"name": "friend_0000"}},
        UpdateExpression="SET #friends.#friendid = :friend",
        ReturnValues="UPDATED_NEW",
    )
    item = table.get_item(Key={"user_id": "1234"})["Item"]
    assert item == {
        "user_id": "1234",
        "friends": {"5678": {"name": "friend_5678"}, "0000": {"name": "friend_0000"}},
    }


@mock_dynamodb
def test_update_supports_list_append_with_nested_if_not_exists_operation():
    dynamo = boto3.resource("dynamodb", region_name="us-west-1")
    table_name = "test"

    dynamo.create_table(
        TableName=table_name,
        AttributeDefinitions=[{"AttributeName": "Id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "Id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 20, "WriteCapacityUnits": 20},
    )

    table = dynamo.Table(table_name)

    table.put_item(Item={"Id": "item-id", "nest1": {"nest2": {}}})
    updated_item = table.update_item(
        Key={"Id": "item-id"},
        UpdateExpression="SET nest1.nest2.event_history = list_append(if_not_exists(nest1.nest2.event_history, :empty_list), :new_value)",
        ExpressionAttributeValues={":empty_list": [], ":new_value": ["some_value"]},
        ReturnValues="UPDATED_NEW",
    )

    # Verify updated item is correct
    updated_item["Attributes"].should.equal(
        {"nest1": {"nest2": {"event_history": ["some_value"]}}}
    )

    table.get_item(Key={"Id": "item-id"})["Item"].should.equal(
        {"Id": "item-id", "nest1": {"nest2": {"event_history": ["some_value"]}}}
    )


@mock_dynamodb
def test_update_supports_list_append_with_nested_if_not_exists_operation_and_property_already_exists():
    dynamo = boto3.resource("dynamodb", region_name="us-west-1")
    table_name = "test"

    dynamo.create_table(
        TableName=table_name,
        AttributeDefinitions=[{"AttributeName": "Id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "Id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 20, "WriteCapacityUnits": 20},
    )

    table = dynamo.Table(table_name)

    table.put_item(Item={"Id": "item-id", "event_history": ["other_value"]})
    updated_item = table.update_item(
        Key={"Id": "item-id"},
        UpdateExpression="SET event_history = list_append(if_not_exists(event_history, :empty_list), :new_value)",
        ExpressionAttributeValues={":empty_list": [], ":new_value": ["some_value"]},
        ReturnValues="UPDATED_NEW",
    )

    # Verify updated item is correct
    updated_item["Attributes"].should.equal(
        {"event_history": ["other_value", "some_value"]}
    )

    table.get_item(Key={"Id": "item-id"})["Item"].should.equal(
        {"Id": "item-id", "event_history": ["other_value", "some_value"]}
    )


@mock_dynamodb
def test_update_item_if_original_value_is_none():
    dynamo = boto3.resource("dynamodb", region_name="eu-central-1")
    dynamo.create_table(
        AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
        TableName="origin-rbu-dev",
        KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table = dynamo.Table("origin-rbu-dev")
    table.put_item(Item={"job_id": "a", "job_name": None})
    table.update_item(
        Key={"job_id": "a"},
        UpdateExpression="SET job_name = :output",
        ExpressionAttributeValues={":output": "updated"},
    )
    table.scan()["Items"][0]["job_name"].should.equal("updated")


@mock_dynamodb
def test_update_nested_item_if_original_value_is_none():
    dynamo = boto3.resource("dynamodb", region_name="eu-central-1")
    dynamo.create_table(
        AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
        TableName="origin-rbu-dev",
        KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table = dynamo.Table("origin-rbu-dev")
    table.put_item(Item={"job_id": "a", "job_details": {"job_name": None}})
    updated_item = table.update_item(
        Key={"job_id": "a"},
        UpdateExpression="SET job_details.job_name = :output",
        ExpressionAttributeValues={":output": "updated"},
        ReturnValues="UPDATED_NEW",
    )

    # Verify updated item is correct
    updated_item["Attributes"].should.equal({"job_details": {"job_name": "updated"}})

    table.scan()["Items"][0]["job_details"]["job_name"].should.equal("updated")


@mock_dynamodb
def test_allow_update_to_item_with_different_type():
    dynamo = boto3.resource("dynamodb", region_name="eu-central-1")
    dynamo.create_table(
        AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
        TableName="origin-rbu-dev",
        KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table = dynamo.Table("origin-rbu-dev")
    table.put_item(Item={"job_id": "a", "job_details": {"job_name": {"nested": "yes"}}})
    table.put_item(Item={"job_id": "b", "job_details": {"job_name": {"nested": "yes"}}})
    updated_item = table.update_item(
        Key={"job_id": "a"},
        UpdateExpression="SET job_details.job_name = :output",
        ExpressionAttributeValues={":output": "updated"},
        ReturnValues="UPDATED_NEW",
    )

    # Verify updated item is correct
    updated_item["Attributes"].should.equal({"job_details": {"job_name": "updated"}})

    table.get_item(Key={"job_id": "a"})["Item"]["job_details"][
        "job_name"
    ].should.be.equal("updated")
    table.get_item(Key={"job_id": "b"})["Item"]["job_details"][
        "job_name"
    ].should.be.equal({"nested": "yes"})


@mock_dynamodb
def test_query_catches_when_no_filters():
    dynamo = boto3.resource("dynamodb", region_name="eu-central-1")
    dynamo.create_table(
        AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
        TableName="origin-rbu-dev",
        KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table = dynamo.Table("origin-rbu-dev")

    with pytest.raises(ClientError) as ex:
        table.query(TableName="original-rbu-dev")

    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "Either KeyConditions or QueryFilter should be present"
    )


@mock_dynamodb
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

    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.match(
        r"failed to satisfy constraint: Member must have length less than or equal to 25",
        re.I,
    )

    with pytest.raises(ClientError) as ex:
        client.transact_get_items(
            TransactItems=[
                {"Get": {"Key": {"id": {"S": "1"}}, "TableName": "test1"}},
                {"Get": {"Key": {"id": {"S": "1"}}, "TableName": "non_exists_table"}},
            ]
        )

    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal("Requested resource not found")


@mock_dynamodb
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
    res["Responses"][0]["Item"].should.equal({"id": {"S": "1"}, "sort_key": {"S": "1"}})
    len(res["Responses"]).should.equal(2)
    res["Responses"][1].should.equal({})

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

    res["Responses"][0]["Item"].should.equal({"id": {"S": "1"}, "sort_key": {"S": "1"}})

    res["Responses"][1]["Item"].should.equal({"id": {"S": "1"}, "sort_key": {"S": "2"}})

    res["Responses"][2]["Item"].should.equal({"id": {"S": "1"}, "sort_key": {"S": "1"}})

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

    res["ConsumedCapacity"][0].should.equal(
        {"TableName": "test1", "CapacityUnits": 4.0, "ReadCapacityUnits": 4.0}
    )

    res["ConsumedCapacity"][1].should.equal(
        {"TableName": "test2", "CapacityUnits": 2.0, "ReadCapacityUnits": 2.0}
    )

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

    res["ConsumedCapacity"][0].should.equal(
        {
            "TableName": "test1",
            "CapacityUnits": 4.0,
            "ReadCapacityUnits": 4.0,
            "Table": {"CapacityUnits": 4.0, "ReadCapacityUnits": 4.0},
        }
    )

    res["ConsumedCapacity"][1].should.equal(
        {
            "TableName": "test2",
            "CapacityUnits": 2.0,
            "ReadCapacityUnits": 2.0,
            "Table": {"CapacityUnits": 2.0, "ReadCapacityUnits": 2.0},
        }
    )


@mock_dynamodb
def test_gsi_verify_negative_number_order():
    table_schema = {
        "KeySchema": [{"AttributeName": "partitionKey", "KeyType": "HASH"}],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "GSI-K1",
                "KeySchema": [
                    {"AttributeName": "gsiK1PartitionKey", "KeyType": "HASH"},
                    {"AttributeName": "gsiK1SortKey", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            }
        ],
        "AttributeDefinitions": [
            {"AttributeName": "partitionKey", "AttributeType": "S"},
            {"AttributeName": "gsiK1PartitionKey", "AttributeType": "S"},
            {"AttributeName": "gsiK1SortKey", "AttributeType": "N"},
        ],
    }

    item1 = {
        "partitionKey": "pk-1",
        "gsiK1PartitionKey": "gsi-k1",
        "gsiK1SortKey": Decimal("-0.6"),
    }

    item2 = {
        "partitionKey": "pk-2",
        "gsiK1PartitionKey": "gsi-k1",
        "gsiK1SortKey": Decimal("-0.7"),
    }

    item3 = {
        "partitionKey": "pk-3",
        "gsiK1PartitionKey": "gsi-k1",
        "gsiK1SortKey": Decimal("0.7"),
    }

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = dynamodb.Table("test-table")
    table.put_item(Item=item3)
    table.put_item(Item=item1)
    table.put_item(Item=item2)

    resp = table.query(
        KeyConditionExpression=Key("gsiK1PartitionKey").eq("gsi-k1"), IndexName="GSI-K1"
    )
    # Items should be ordered with the lowest number first
    [float(item["gsiK1SortKey"]) for item in resp["Items"]].should.equal(
        [-0.7, -0.6, 0.7]
    )


@mock_dynamodb
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
    items.should.have.length_of(5)


@mock_dynamodb
def test_transact_write_items_put_conditional_expressions():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    dynamodb.put_item(TableName="test-table", Item={"id": {"S": "foo2"}})
    # Put multiple items
    with pytest.raises(ClientError) as ex:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "Item": {
                            "id": {"S": f"foo{i}"},
                            "foo": {"S": "bar"},
                        },
                        "TableName": "test-table",
                        "ConditionExpression": "#i <> :i",
                        "ExpressionAttributeNames": {"#i": "id"},
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
    ex.value.response["Error"]["Code"].should.equal("TransactionCanceledException")
    reasons = ex.value.response["CancellationReasons"]
    reasons.should.have.length_of(5)
    reasons.should.contain(
        {
            "Code": "ConditionalCheckFailed",
            "Message": "The conditional request failed",
            "Item": {"id": {"S": "foo2"}, "foo": {"S": "bar"}},
        }
    )
    reasons.should.contain({"Code": "None"})
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    # Assert all are present
    items = dynamodb.scan(TableName="test-table")["Items"]
    items.should.have.length_of(1)
    items[0].should.equal({"id": {"S": "foo2"}})


@mock_dynamodb
def test_transact_write_items_put_conditional_expressions_return_values_on_condition_check_failure_all_old():
    table_schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    dynamodb.put_item(TableName="test-table", Item={"id": {"S": "foo2"}})
    # Put multiple items
    with pytest.raises(ClientError) as ex:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "Item": {
                            "id": {"S": f"foo{i}"},
                            "foo": {"S": "bar"},
                        },
                        "TableName": "test-table",
                        "ConditionExpression": "#i <> :i",
                        "ExpressionAttributeNames": {"#i": "id"},
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
    ex.value.response["Error"]["Code"].should.equal("TransactionCanceledException")
    reasons = ex.value.response["CancellationReasons"]
    reasons.should.have.length_of(5)
    reasons.should.contain(
        {
            "Code": "ConditionalCheckFailed",
            "Message": "The conditional request failed",
            "Item": {"id": {"S": "foo2"}},
        }
    )
    reasons.should.contain({"Code": "None"})
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    # Assert all are present
    items = dynamodb.scan(TableName="test-table")["Items"]
    items.should.have.length_of(1)
    items[0].should.equal({"id": {"S": "foo2"}})


@mock_dynamodb
def test_transact_write_items_conditioncheck_passes():
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
    # Put an email address, after verifying it doesn't exist yet
    dynamodb.transact_write_items(
        TransactItems=[
            {
                "ConditionCheck": {
                    "Key": {"id": {"S": "foo"}},
                    "TableName": "test-table",
                    "ConditionExpression": "attribute_not_exists(#e)",
                    "ExpressionAttributeNames": {"#e": "email_address"},
                }
            },
            {
                "Put": {
                    "Item": {
                        "id": {"S": "foo"},
                        "email_address": {"S": "test@moto.com"},
                    },
                    "TableName": "test-table",
                }
            },
        ]
    )
    # Assert all are present
    items = dynamodb.scan(TableName="test-table")["Items"]
    items.should.have.length_of(1)
    items[0].should.equal({"email_address": {"S": "test@moto.com"}, "id": {"S": "foo"}})


@mock_dynamodb
def test_transact_write_items_conditioncheck_fails():
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
    # Try to put an email address, but verify whether it exists
    # ConditionCheck should fail
    with pytest.raises(ClientError) as ex:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "ConditionCheck": {
                        "Key": {"id": {"S": "foo"}},
                        "TableName": "test-table",
                        "ConditionExpression": "attribute_not_exists(#e)",
                        "ExpressionAttributeNames": {"#e": "email_address"},
                    }
                },
                {
                    "Put": {
                        "Item": {
                            "id": {"S": "foo"},
                            "email_address": {"S": "update@moto.com"},
                        },
                        "TableName": "test-table",
                    }
                },
            ]
        )
    # Assert the exception is correct
    ex.value.response["Error"]["Code"].should.equal("TransactionCanceledException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)

    # Assert the original email address is still present
    items = dynamodb.scan(TableName="test-table")["Items"]
    items.should.have.length_of(1)
    items[0].should.equal({"email_address": {"S": "test@moto.com"}, "id": {"S": "foo"}})


@mock_dynamodb
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
    items.should.have.length_of(0)


@mock_dynamodb
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
    items.should.have.length_of(0)


@mock_dynamodb
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
    ex.value.response["Error"]["Code"].should.equal("TransactionCanceledException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    # Assert the original item is still present
    items = dynamodb.scan(TableName="test-table")["Items"]
    items.should.have.length_of(1)
    items[0].should.equal({"email_address": {"S": "test@moto.com"}, "id": {"S": "foo"}})


@mock_dynamodb
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
    items.should.have.length_of(1)
    items[0].should.equal({"id": {"S": "foo"}, "email_address": {"S": "test@moto.com"}})


@mock_dynamodb
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
    ex.value.response["Error"]["Code"].should.equal("TransactionCanceledException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    # Assert the original item is still present
    items = dynamodb.scan(TableName="test-table")["Items"]
    items.should.have.length_of(1)
    items[0].should.equal({"email_address": {"S": "test@moto.com"}, "id": {"S": "foo"}})


@mock_dynamodb
def test_dynamodb_max_1mb_limit():
    ddb = boto3.resource("dynamodb", region_name="eu-west-1")

    table_name = "populated-mock-table"
    table = ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "partition_key", "KeyType": "HASH"},
            {"AttributeName": "sort_key", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "partition_key", "AttributeType": "S"},
            {"AttributeName": "sort_key", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Populate the table
    items = [
        {
            "partition_key": "partition_key_val",  # size=30
            "sort_key": "sort_key_value____" + str(i),  # size=30
        }
        for i in range(10000, 29999)
    ]
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    response = table.query(
        KeyConditionExpression=Key("partition_key").eq("partition_key_val")
    )
    # We shouldn't get everything back - the total result set is well over 1MB
    len(items).should.be.greater_than(response["Count"])
    response["LastEvaluatedKey"].shouldnt.be(None)


def assert_raise_syntax_error(client_error, token, near):
    """
    Assert whether a client_error is as expected Syntax error. Syntax error looks like: `syntax_error_template`

    Args:
        client_error(ClientError): The ClientError exception that was raised
        token(str): The token that ws unexpected
        near(str): The part in the expression that shows where the error occurs it generally has the preceding token the
        optional separation and the problematic token.
    """
    syntax_error_template = (
        'Invalid UpdateExpression: Syntax error; token: "{token}", near: "{near}"'
    )
    expected_syntax_error = syntax_error_template.format(token=token, near=near)
    assert client_error.response["Error"]["Code"] == "ValidationException"
    assert expected_syntax_error == client_error.response["Error"]["Message"]


@mock_dynamodb
def test_update_expression_with_numeric_literal_instead_of_value():
    """
    DynamoDB requires literals to be passed in as values. If they are put literally in the expression a token error will
    be raised
    """
    dynamodb = boto3.client("dynamodb", region_name="eu-west-1")

    dynamodb.create_table(
        TableName="moto-test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    try:
        dynamodb.update_item(
            TableName="moto-test",
            Key={"id": {"S": "1"}},
            UpdateExpression="SET MyStr = myNum + 1",
        )
        assert False, "Validation exception not thrown"
    except dynamodb.exceptions.ClientError as e:
        assert_raise_syntax_error(e, "1", "+ 1")


@mock_dynamodb
def test_update_expression_with_multiple_set_clauses_must_be_comma_separated():
    """
    An UpdateExpression can have multiple set clauses but if they are passed in without the separating comma.
    """
    dynamodb = boto3.client("dynamodb", region_name="eu-west-1")

    dynamodb.create_table(
        TableName="moto-test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    try:
        dynamodb.update_item(
            TableName="moto-test",
            Key={"id": {"S": "1"}},
            UpdateExpression="SET MyStr = myNum Mystr2 myNum2",
        )
        assert False, "Validation exception not thrown"
    except dynamodb.exceptions.ClientError as e:
        assert_raise_syntax_error(e, "Mystr2", "myNum Mystr2 myNum2")


@mock_dynamodb
def test_list_tables_exclusive_start_table_name_empty():
    client = boto3.client("dynamodb", region_name="us-east-1")

    resp = client.list_tables(Limit=1, ExclusiveStartTableName="whatever")

    len(resp["TableNames"]).should.equal(0)


def assert_correct_client_error(
    client_error, code, message_template, message_values=None, braces=None
):
    """
    Assert whether a client_error is as expected. Allow for a list of values to be passed into the message

    Args:
        client_error(ClientError): The ClientError exception that was raised
        code(str): The code for the error (e.g. ValidationException)
        message_template(str): Error message template. if message_values is not None then this template has a {values}
            as placeholder. For example:
            'Value provided in ExpressionAttributeValues unused in expressions: keys: {values}'
        message_values(list of str|None): The values that are passed in the error message
        braces(list of str|None): List of length 2 with opening and closing brace for the values. By default it will be
                                  surrounded by curly brackets
    """
    braces = braces or ["{", "}"]
    assert client_error.response["Error"]["Code"] == code
    if message_values is not None:
        values_string = f"{braces[0]}(?P<values>.*){braces[1]}"
        re_msg = re.compile(message_template.format(values=values_string))
        match_result = re_msg.match(client_error.response["Error"]["Message"])
        assert match_result is not None
        values_string = match_result.groupdict()["values"]
        values = [key for key in values_string.split(", ")]
        assert len(message_values) == len(values)
        for value in message_values:
            assert value in values
    else:
        assert client_error.response["Error"]["Message"] == message_template


def create_simple_table_and_return_client():
    dynamodb = boto3.client("dynamodb", region_name="eu-west-1")
    dynamodb.create_table(
        TableName="moto-test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    dynamodb.put_item(
        TableName="moto-test",
        Item={"id": {"S": "1"}, "myNum": {"N": "1"}, "MyStr": {"S": "1"}},
    )
    return dynamodb


# https://github.com/spulec/moto/issues/2806
# https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_UpdateItem.html
#       #DDB-UpdateItem-request-UpdateExpression
@mock_dynamodb
def test_update_item_with_attribute_in_right_hand_side_and_operation():
    dynamodb = create_simple_table_and_return_client()

    dynamodb.update_item(
        TableName="moto-test",
        Key={"id": {"S": "1"}},
        UpdateExpression="SET myNum = myNum+:val",
        ExpressionAttributeValues={":val": {"N": "3"}},
    )

    result = dynamodb.get_item(TableName="moto-test", Key={"id": {"S": "1"}})
    assert result["Item"]["myNum"]["N"] == "4"

    dynamodb.update_item(
        TableName="moto-test",
        Key={"id": {"S": "1"}},
        UpdateExpression="SET myNum = myNum - :val",
        ExpressionAttributeValues={":val": {"N": "1"}},
    )
    result = dynamodb.get_item(TableName="moto-test", Key={"id": {"S": "1"}})
    assert result["Item"]["myNum"]["N"] == "3"


@mock_dynamodb
def test_non_existing_attribute_should_raise_exception():
    """
    Does error message get correctly raised if attribute is referenced but it does not exist for the item.
    """
    dynamodb = create_simple_table_and_return_client()

    try:
        dynamodb.update_item(
            TableName="moto-test",
            Key={"id": {"S": "1"}},
            UpdateExpression="SET MyStr = no_attr + MyStr",
        )
        assert False, "Validation exception not thrown"
    except dynamodb.exceptions.ClientError as e:
        assert_correct_client_error(
            e,
            "ValidationException",
            "The provided expression refers to an attribute that does not exist in the item",
        )


@mock_dynamodb
def test_update_expression_with_plus_in_attribute_name():
    """
    Does error message get correctly raised if attribute contains a plus and is passed in without an AttributeName. And
    lhs & rhs are not attribute IDs by themselve.
    """
    dynamodb = create_simple_table_and_return_client()

    dynamodb.put_item(
        TableName="moto-test",
        Item={"id": {"S": "1"}, "my+Num": {"S": "1"}, "MyStr": {"S": "aaa"}},
    )
    try:
        dynamodb.update_item(
            TableName="moto-test",
            Key={"id": {"S": "1"}},
            UpdateExpression="SET MyStr = my+Num",
        )
        assert False, "Validation exception not thrown"
    except dynamodb.exceptions.ClientError as e:
        assert_correct_client_error(
            e,
            "ValidationException",
            "The provided expression refers to an attribute that does not exist in the item",
        )


@mock_dynamodb
def test_update_expression_with_minus_in_attribute_name():
    """
    Does error message get correctly raised if attribute contains a minus and is passed in without an AttributeName. And
    lhs & rhs are not attribute IDs by themselve.
    """
    dynamodb = create_simple_table_and_return_client()

    dynamodb.put_item(
        TableName="moto-test",
        Item={"id": {"S": "1"}, "my-Num": {"S": "1"}, "MyStr": {"S": "aaa"}},
    )
    try:
        dynamodb.update_item(
            TableName="moto-test",
            Key={"id": {"S": "1"}},
            UpdateExpression="SET MyStr = my-Num",
        )
        assert False, "Validation exception not thrown"
    except dynamodb.exceptions.ClientError as e:
        assert_correct_client_error(
            e,
            "ValidationException",
            "The provided expression refers to an attribute that does not exist in the item",
        )


@mock_dynamodb
def test_update_expression_with_space_in_attribute_name():
    """
    Does error message get correctly raised if attribute contains a space and is passed in without an AttributeName. And
    lhs & rhs are not attribute IDs by themselves.
    """
    dynamodb = create_simple_table_and_return_client()

    dynamodb.put_item(
        TableName="moto-test",
        Item={"id": {"S": "1"}, "my Num": {"S": "1"}, "MyStr": {"S": "aaa"}},
    )

    try:
        dynamodb.update_item(
            TableName="moto-test",
            Key={"id": {"S": "1"}},
            UpdateExpression="SET MyStr = my Num",
        )
        assert False, "Validation exception not thrown"
    except dynamodb.exceptions.ClientError as e:
        assert_raise_syntax_error(e, "Num", "my Num")


@mock_dynamodb
def test_summing_up_2_strings_raises_exception():
    """
    Update set supports different DynamoDB types but some operations are not supported. For example summing up 2 strings
    raises an exception.  It results in ClientError with code ValidationException:
        Saying An operand in the update expression has an incorrect data type
    """
    dynamodb = create_simple_table_and_return_client()

    try:
        dynamodb.update_item(
            TableName="moto-test",
            Key={"id": {"S": "1"}},
            UpdateExpression="SET MyStr = MyStr + MyStr",
        )
        assert False, "Validation exception not thrown"
    except dynamodb.exceptions.ClientError as e:
        assert_correct_client_error(
            e,
            "ValidationException",
            "An operand in the update expression has an incorrect data type",
        )


# https://github.com/spulec/moto/issues/2806
@mock_dynamodb
def test_update_item_with_attribute_in_right_hand_side():
    """
    After tokenization and building expression make sure referenced attributes are replaced with their current value
    """
    dynamodb = create_simple_table_and_return_client()

    # Make sure there are 2 values
    dynamodb.put_item(
        TableName="moto-test",
        Item={"id": {"S": "1"}, "myVal1": {"S": "Value1"}, "myVal2": {"S": "Value2"}},
    )

    dynamodb.update_item(
        TableName="moto-test",
        Key={"id": {"S": "1"}},
        UpdateExpression="SET myVal1 = myVal2",
    )

    result = dynamodb.get_item(TableName="moto-test", Key={"id": {"S": "1"}})
    assert result["Item"]["myVal1"]["S"] == result["Item"]["myVal2"]["S"] == "Value2"


@mock_dynamodb
def test_multiple_updates():
    dynamodb = create_simple_table_and_return_client()
    dynamodb.put_item(
        TableName="moto-test",
        Item={"id": {"S": "1"}, "myNum": {"N": "1"}, "path": {"N": "6"}},
    )
    dynamodb.update_item(
        TableName="moto-test",
        Key={"id": {"S": "1"}},
        UpdateExpression="SET myNum = #p + :val, newAttr = myNum",
        ExpressionAttributeValues={":val": {"N": "1"}},
        ExpressionAttributeNames={"#p": "path"},
    )
    result = dynamodb.get_item(TableName="moto-test", Key={"id": {"S": "1"}})["Item"]
    expected_result = {
        "myNum": {"N": "7"},
        "newAttr": {"N": "1"},
        "path": {"N": "6"},
        "id": {"S": "1"},
    }
    assert result == expected_result


@mock_dynamodb
def test_update_item_atomic_counter():
    table = "table_t"
    ddb_mock = boto3.client("dynamodb", region_name="eu-west-3")
    ddb_mock.create_table(
        TableName=table,
        KeySchema=[{"AttributeName": "t_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "t_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    key = {"t_id": {"S": "item1"}}

    ddb_mock.put_item(
        TableName=table,
        Item={"t_id": {"S": "item1"}, "n_i": {"N": "5"}, "n_f": {"N": "5.3"}},
    )

    ddb_mock.update_item(
        TableName=table,
        Key=key,
        UpdateExpression="set n_i = n_i + :inc1, n_f = n_f + :inc2",
        ExpressionAttributeValues={":inc1": {"N": "1.2"}, ":inc2": {"N": "0.05"}},
    )
    updated_item = ddb_mock.get_item(TableName=table, Key=key)["Item"]
    updated_item["n_i"]["N"].should.equal("6.2")
    updated_item["n_f"]["N"].should.equal("5.35")


@mock_dynamodb
def test_update_item_atomic_counter_return_values():
    table = "table_t"
    ddb_mock = boto3.client("dynamodb", region_name="eu-west-3")
    ddb_mock.create_table(
        TableName=table,
        KeySchema=[{"AttributeName": "t_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "t_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    key = {"t_id": {"S": "item1"}}

    ddb_mock.put_item(TableName=table, Item={"t_id": {"S": "item1"}, "v": {"N": "5"}})

    response = ddb_mock.update_item(
        TableName=table,
        Key=key,
        UpdateExpression="set v = v + :inc",
        ExpressionAttributeValues={":inc": {"N": "1"}},
        ReturnValues="UPDATED_OLD",
    )
    assert (
        "v" in response["Attributes"]
    ), "v has been updated, and should be returned here"
    response["Attributes"]["v"]["N"].should.equal("5")

    # second update
    response = ddb_mock.update_item(
        TableName=table,
        Key=key,
        UpdateExpression="set v = v + :inc",
        ExpressionAttributeValues={":inc": {"N": "1"}},
        ReturnValues="UPDATED_OLD",
    )
    assert (
        "v" in response["Attributes"]
    ), "v has been updated, and should be returned here"
    response["Attributes"]["v"]["N"].should.equal("6")

    # third update
    response = ddb_mock.update_item(
        TableName=table,
        Key=key,
        UpdateExpression="set v = v + :inc",
        ExpressionAttributeValues={":inc": {"N": "1"}},
        ReturnValues="UPDATED_NEW",
    )
    assert (
        "v" in response["Attributes"]
    ), "v has been updated, and should be returned here"
    response["Attributes"]["v"]["N"].should.equal("8")


@mock_dynamodb
def test_update_item_atomic_counter_from_zero():
    table = "table_t"
    ddb_mock = boto3.client("dynamodb", region_name="eu-west-1")
    ddb_mock.create_table(
        TableName=table,
        KeySchema=[{"AttributeName": "t_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "t_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    key = {"t_id": {"S": "item1"}}

    ddb_mock.put_item(TableName=table, Item=key)

    ddb_mock.update_item(
        TableName=table,
        Key=key,
        UpdateExpression="add n_i :inc1, n_f :inc2",
        ExpressionAttributeValues={":inc1": {"N": "1.2"}, ":inc2": {"N": "-0.5"}},
    )
    updated_item = ddb_mock.get_item(TableName=table, Key=key)["Item"]
    assert updated_item["n_i"]["N"] == "1.2"
    assert updated_item["n_f"]["N"] == "-0.5"


@mock_dynamodb
def test_update_item_add_to_non_existent_set():
    table = "table_t"
    ddb_mock = boto3.client("dynamodb", region_name="eu-west-1")
    ddb_mock.create_table(
        TableName=table,
        KeySchema=[{"AttributeName": "t_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "t_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    key = {"t_id": {"S": "item1"}}
    ddb_mock.put_item(TableName=table, Item=key)

    ddb_mock.update_item(
        TableName=table,
        Key=key,
        UpdateExpression="add s_i :s1",
        ExpressionAttributeValues={":s1": {"SS": ["hello"]}},
    )
    updated_item = ddb_mock.get_item(TableName=table, Key=key)["Item"]
    assert updated_item["s_i"]["SS"] == ["hello"]


@mock_dynamodb
def test_update_item_add_to_non_existent_number_set():
    table = "table_t"
    ddb_mock = boto3.client("dynamodb", region_name="eu-west-1")
    ddb_mock.create_table(
        TableName=table,
        KeySchema=[{"AttributeName": "t_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "t_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    key = {"t_id": {"S": "item1"}}
    ddb_mock.put_item(TableName=table, Item=key)

    ddb_mock.update_item(
        TableName=table,
        Key=key,
        UpdateExpression="add s_i :s1",
        ExpressionAttributeValues={":s1": {"NS": ["3"]}},
    )
    updated_item = ddb_mock.get_item(TableName=table, Key=key)["Item"]
    assert updated_item["s_i"]["NS"] == ["3"]


@mock_dynamodb
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
    ex.value.response["Error"]["Code"].should.equal("TransactionCanceledException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "Transaction cancelled, please refer cancellation reasons for specific reasons [None, ConditionalCheckFailed]"
    )


@mock_dynamodb
def test_gsi_projection_type_keys_only():
    table_schema = {
        "KeySchema": [{"AttributeName": "partitionKey", "KeyType": "HASH"}],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "GSI-K1",
                "KeySchema": [
                    {"AttributeName": "gsiK1PartitionKey", "KeyType": "HASH"},
                    {"AttributeName": "gsiK1SortKey", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            }
        ],
        "AttributeDefinitions": [
            {"AttributeName": "partitionKey", "AttributeType": "S"},
            {"AttributeName": "gsiK1PartitionKey", "AttributeType": "S"},
            {"AttributeName": "gsiK1SortKey", "AttributeType": "S"},
        ],
    }

    item = {
        "partitionKey": "pk-1",
        "gsiK1PartitionKey": "gsi-pk",
        "gsiK1SortKey": "gsi-sk",
        "someAttribute": "lore ipsum",
    }

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = dynamodb.Table("test-table")
    table.put_item(Item=item)

    items = table.query(
        KeyConditionExpression=Key("gsiK1PartitionKey").eq("gsi-pk"), IndexName="GSI-K1"
    )["Items"]
    items.should.have.length_of(1)
    # Item should only include GSI Keys and Table Keys, as per the ProjectionType
    items[0].should.equal(
        {
            "gsiK1PartitionKey": "gsi-pk",
            "gsiK1SortKey": "gsi-sk",
            "partitionKey": "pk-1",
        }
    )


@mock_dynamodb
def test_gsi_projection_type_include():
    table_schema = {
        "KeySchema": [{"AttributeName": "partitionKey", "KeyType": "HASH"}],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "GSI-INC",
                "KeySchema": [
                    {"AttributeName": "gsiK1PartitionKey", "KeyType": "HASH"},
                    {"AttributeName": "gsiK1SortKey", "KeyType": "RANGE"},
                ],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["projectedAttribute"],
                },
            }
        ],
        "AttributeDefinitions": [
            {"AttributeName": "partitionKey", "AttributeType": "S"},
            {"AttributeName": "gsiK1PartitionKey", "AttributeType": "S"},
            {"AttributeName": "gsiK1SortKey", "AttributeType": "S"},
        ],
    }

    item = {
        "partitionKey": "pk-1",
        "gsiK1PartitionKey": "gsi-pk",
        "gsiK1SortKey": "gsi-sk",
        "projectedAttribute": "lore ipsum",
        "nonProjectedAttribute": "dolor sit amet",
    }

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = dynamodb.Table("test-table")
    table.put_item(Item=item)

    items = table.query(
        KeyConditionExpression=Key("gsiK1PartitionKey").eq("gsi-pk"),
        IndexName="GSI-INC",
    )["Items"]
    items.should.have.length_of(1)
    # Item should only include keys and additionally projected attributes only
    items[0].should.equal(
        {
            "gsiK1PartitionKey": "gsi-pk",
            "gsiK1SortKey": "gsi-sk",
            "partitionKey": "pk-1",
            "projectedAttribute": "lore ipsum",
        }
    )


@mock_dynamodb
def test_lsi_projection_type_keys_only():
    table_schema = {
        "KeySchema": [
            {"AttributeName": "partitionKey", "KeyType": "HASH"},
            {"AttributeName": "sortKey", "KeyType": "RANGE"},
        ],
        "LocalSecondaryIndexes": [
            {
                "IndexName": "LSI",
                "KeySchema": [
                    {"AttributeName": "partitionKey", "KeyType": "HASH"},
                    {"AttributeName": "lsiK1SortKey", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            }
        ],
        "AttributeDefinitions": [
            {"AttributeName": "partitionKey", "AttributeType": "S"},
            {"AttributeName": "sortKey", "AttributeType": "S"},
            {"AttributeName": "lsiK1SortKey", "AttributeType": "S"},
        ],
    }

    item = {
        "partitionKey": "pk-1",
        "sortKey": "sk-1",
        "lsiK1SortKey": "lsi-sk",
        "someAttribute": "lore ipsum",
    }

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = dynamodb.Table("test-table")
    table.put_item(Item=item)

    items = table.query(
        KeyConditionExpression=Key("partitionKey").eq("pk-1"), IndexName="LSI"
    )["Items"]
    items.should.have.length_of(1)
    # Item should only include GSI Keys and Table Keys, as per the ProjectionType
    items[0].should.equal(
        {"partitionKey": "pk-1", "sortKey": "sk-1", "lsiK1SortKey": "lsi-sk"}
    )


@mock_dynamodb
@pytest.mark.parametrize(
    "attr_name",
    ["orders", "#placeholder"],
    ids=["use attribute name", "use expression attribute name"],
)
def test_set_attribute_is_dropped_if_empty_after_update_expression(attr_name):
    table_name, item_key, set_item = "test-table", "test-id", "test-data"
    expression_attribute_names = {"#placeholder": "orders"}
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "customer", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "customer", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    client.update_item(
        TableName=table_name,
        Key={"customer": {"S": item_key}},
        UpdateExpression=f"ADD {attr_name} :order",
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues={":order": {"SS": [set_item]}},
    )
    resp = client.scan(TableName=table_name, ProjectionExpression="customer, orders")
    item = resp["Items"][0]
    item.should.have.key("customer")
    item.should.have.key("orders")

    client.update_item(
        TableName=table_name,
        Key={"customer": {"S": item_key}},
        UpdateExpression=f"DELETE {attr_name} :order",
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues={":order": {"SS": [set_item]}},
    )
    resp = client.scan(TableName=table_name, ProjectionExpression="customer, orders")
    item = resp["Items"][0]
    item.should.have.key("customer")
    item.should_not.have.key("orders")


@mock_dynamodb
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
    items.should.have.length_of(2)
    items[0].should.equal({"Item": item})
    items[1].should.equal({})


@mock_dynamodb
def test_dynamodb_update_item_fails_on_string_sets():
    dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
    client = boto3.client("dynamodb", region_name="eu-west-1")

    table = dynamodb.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "record_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "record_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table.meta.client.get_waiter("table_exists").wait(TableName="test")
    attribute = {"test_field": {"Value": {"SS": ["test1", "test2"]}, "Action": "PUT"}}

    client.update_item(
        TableName="test",
        Key={"record_id": {"S": "testrecord"}},
        AttributeUpdates=attribute,
    )


@mock_dynamodb
def test_update_item_add_to_list_using_legacy_attribute_updates():
    resource = boto3.resource("dynamodb", region_name="us-west-2")
    resource.create_table(
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        TableName="TestTable",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = resource.Table("TestTable")
    table.wait_until_exists()
    table.put_item(Item={"id": "list_add", "attr": ["a", "b", "c"]})

    table.update_item(
        TableName="TestTable",
        Key={"id": "list_add"},
        AttributeUpdates={"attr": {"Action": "ADD", "Value": ["d", "e"]}},
    )

    resp = table.get_item(Key={"id": "list_add"})
    resp["Item"]["attr"].should.equal(["a", "b", "c", "d", "e"])


@mock_dynamodb
def test_get_item_for_non_existent_table_raises_error():
    client = boto3.client("dynamodb", "us-east-1")
    with pytest.raises(ClientError) as ex:
        client.get_item(TableName="non-existent", Key={"site-id": {"S": "foo"}})
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["Error"]["Message"].should.equal("Requested resource not found")


@mock_dynamodb
def test_error_when_providing_expression_and_nonexpression_params():
    client = boto3.client("dynamodb", "eu-central-1")
    table_name = "testtable"
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "pkey", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "pkey", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    with pytest.raises(ClientError) as ex:
        client.update_item(
            TableName=table_name,
            Key={"pkey": {"S": "testrecord"}},
            AttributeUpdates={
                "test_field": {"Value": {"SS": ["test1", "test2"]}, "Action": "PUT"}
            },
            UpdateExpression="DELETE orders :order",
            ExpressionAttributeValues={":order": {"SS": ["item"]}},
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Can not use both expression and non-expression parameters in the same request: Non-expression parameters: {AttributeUpdates} Expression parameters: {UpdateExpression}"
    )


@mock_dynamodb
def test_attribute_item_delete():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="eu-west-1")
    conn.create_table(
        TableName=name,
        AttributeDefinitions=[{"AttributeName": "name", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "name", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )

    item_name = "foo"
    conn.put_item(
        TableName=name, Item={"name": {"S": item_name}, "extra": {"S": "bar"}}
    )

    conn.update_item(
        TableName=name,
        Key={"name": {"S": item_name}},
        AttributeUpdates={"extra": {"Action": "DELETE"}},
    )
    items = conn.scan(TableName=name)["Items"]
    items.should.equal([{"name": {"S": "foo"}}])


@mock_dynamodb
def test_gsi_key_can_be_updated():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="eu-west-2")
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "main_key", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "main_key", "AttributeType": "S"},
            {"AttributeName": "index_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_index",
                "KeySchema": [{"AttributeName": "index_key", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )

    conn.put_item(
        TableName=name,
        Item={
            "main_key": {"S": "testkey1"},
            "extra_data": {"S": "testdata"},
            "index_key": {"S": "indexkey1"},
        },
    )

    conn.update_item(
        TableName=name,
        Key={"main_key": {"S": "testkey1"}},
        UpdateExpression="set index_key=:new_index_key",
        ExpressionAttributeValues={":new_index_key": {"S": "new_value"}},
    )

    item = conn.scan(TableName=name)["Items"][0]
    item["index_key"].should.equal({"S": "new_value"})
    item["main_key"].should.equal({"S": "testkey1"})


@mock_dynamodb
def test_gsi_key_cannot_be_empty():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="eu-west-2")
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "main_key", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "main_key", "AttributeType": "S"},
            {"AttributeName": "index_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_index",
                "KeySchema": [{"AttributeName": "index_key", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )

    conn.put_item(
        TableName=name,
        Item={
            "main_key": {"S": "testkey1"},
            "extra_data": {"S": "testdata"},
            "index_key": {"S": "indexkey1"},
        },
    )

    with pytest.raises(ClientError) as ex:
        conn.update_item(
            TableName=name,
            Key={"main_key": {"S": "testkey1"}},
            UpdateExpression="set index_key=:new_index_key",
            ExpressionAttributeValues={":new_index_key": {"S": ""}},
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values are not valid. The update expression attempted to update a secondary index key to a value that is not supported. The AttributeValue for a key attribute cannot contain an empty string value."
    )


@mock_dynamodb
def test_create_backup_for_non_existent_table_raises_error():
    client = boto3.client("dynamodb", "us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_backup(TableName="non-existent", BackupName="backup")
    error = ex.value.response["Error"]
    error["Code"].should.equal("TableNotFoundException")
    error["Message"].should.equal("Table not found: non-existent")


@mock_dynamodb
def test_create_backup():
    client = boto3.client("dynamodb", "us-east-1")
    table_name = "test-table"
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    backup_name = "backup-test-table"
    resp = client.create_backup(TableName=table_name, BackupName=backup_name)
    details = resp.get("BackupDetails")
    details.should.have.key("BackupArn").should.contain(table_name)
    details.should.have.key("BackupName").should.equal(backup_name)
    details.should.have.key("BackupSizeBytes").should.be.a(int)
    details.should.have.key("BackupStatus")
    details.should.have.key("BackupType").should.equal("USER")
    details.should.have.key("BackupCreationDateTime").should.be.a(datetime)


@mock_dynamodb
def test_create_multiple_backups_with_same_name():
    client = boto3.client("dynamodb", "us-east-1")
    table_name = "test-table"
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    backup_name = "backup-test-table"
    backup_arns = []
    for _ in range(4):
        backup = client.create_backup(TableName=table_name, BackupName=backup_name).get(
            "BackupDetails"
        )
        backup["BackupName"].should.equal(backup_name)
        backup_arns.should_not.contain(backup["BackupArn"])
        backup_arns.append(backup["BackupArn"])


@mock_dynamodb
def test_describe_backup_for_non_existent_backup_raises_error():
    client = boto3.client("dynamodb", "us-east-1")
    non_existent_arn = "arn:aws:dynamodb:us-east-1:123456789012:table/table-name/backup/01623095754481-2cfcd6f9"
    with pytest.raises(ClientError) as ex:
        client.describe_backup(BackupArn=non_existent_arn)
    error = ex.value.response["Error"]
    error["Code"].should.equal("BackupNotFoundException")
    error["Message"].should.equal(f"Backup not found: {non_existent_arn}")


@mock_dynamodb
def test_describe_backup():
    client = boto3.client("dynamodb", "us-east-1")
    table_name = "test-table"
    table = client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    ).get("TableDescription")
    backup_name = "backup-test-table"
    backup_arn = (
        client.create_backup(TableName=table_name, BackupName=backup_name)
        .get("BackupDetails")
        .get("BackupArn")
    )
    resp = client.describe_backup(BackupArn=backup_arn)
    description = resp.get("BackupDescription")
    details = description.get("BackupDetails")
    details.should.have.key("BackupArn").should.contain(table_name)
    details.should.have.key("BackupName").should.equal(backup_name)
    details.should.have.key("BackupSizeBytes").should.be.a(int)
    details.should.have.key("BackupStatus")
    details.should.have.key("BackupType").should.equal("USER")
    details.should.have.key("BackupCreationDateTime").should.be.a(datetime)
    source = description.get("SourceTableDetails")
    source.should.have.key("TableName").should.equal(table_name)
    source.should.have.key("TableArn").should.equal(table["TableArn"])
    source.should.have.key("TableSizeBytes").should.be.a(int)
    source.should.have.key("KeySchema").should.equal(table["KeySchema"])
    source.should.have.key("TableCreationDateTime").should.equal(
        table["CreationDateTime"]
    )
    source.should.have.key("ProvisionedThroughput").should.be.a(dict)
    source.should.have.key("ItemCount").should.equal(table["ItemCount"])


@mock_dynamodb
def test_list_backups_for_non_existent_table():
    client = boto3.client("dynamodb", "us-east-1")
    resp = client.list_backups(TableName="non-existent")
    resp["BackupSummaries"].should.have.length_of(0)


@mock_dynamodb
def test_list_backups():
    client = boto3.client("dynamodb", "us-east-1")
    table_names = ["test-table-1", "test-table-2"]
    backup_names = ["backup-1", "backup-2"]
    for table_name in table_names:
        client.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        for backup_name in backup_names:
            client.create_backup(TableName=table_name, BackupName=backup_name)
    resp = client.list_backups(BackupType="USER")
    resp["BackupSummaries"].should.have.length_of(4)
    for table_name in table_names:
        resp = client.list_backups(TableName=table_name)
        resp["BackupSummaries"].should.have.length_of(2)
        for summary in resp["BackupSummaries"]:
            summary.should.have.key("TableName").should.equal(table_name)
            summary.should.have.key("TableArn").should.contain(table_name)
            summary.should.have.key("BackupName").should.be.within(backup_names)
            summary.should.have.key("BackupArn")
            summary.should.have.key("BackupCreationDateTime").should.be.a(datetime)
            summary.should.have.key("BackupStatus")
            summary.should.have.key("BackupType").should.be.within(["USER", "SYSTEM"])
            summary.should.have.key("BackupSizeBytes").should.be.a(int)


@mock_dynamodb
def test_restore_table_from_non_existent_backup_raises_error():
    client = boto3.client("dynamodb", "us-east-1")
    non_existent_arn = "arn:aws:dynamodb:us-east-1:123456789012:table/table-name/backup/01623095754481-2cfcd6f9"
    with pytest.raises(ClientError) as ex:
        client.restore_table_from_backup(
            TargetTableName="from-backup", BackupArn=non_existent_arn
        )
    error = ex.value.response["Error"]
    error["Code"].should.equal("BackupNotFoundException")
    error["Message"].should.equal(f"Backup not found: {non_existent_arn}")


@mock_dynamodb
def test_restore_table_from_backup_raises_error_when_table_already_exists():
    client = boto3.client("dynamodb", "us-east-1")
    table_name = "test-table"
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    resp = client.create_backup(TableName=table_name, BackupName="backup")
    backup = resp.get("BackupDetails")
    with pytest.raises(ClientError) as ex:
        client.restore_table_from_backup(
            TargetTableName=table_name, BackupArn=backup["BackupArn"]
        )
    error = ex.value.response["Error"]
    error["Code"].should.equal("TableAlreadyExistsException")
    error["Message"].should.equal(f"Table already exists: {table_name}")


@mock_dynamodb
def test_restore_table_from_backup():
    client = boto3.client("dynamodb", "us-east-1")
    table_name = "test-table"
    resp = client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = resp.get("TableDescription")
    for i in range(5):
        client.put_item(TableName=table_name, Item={"id": {"S": f"item {i}"}})

    backup_arn = (
        client.create_backup(TableName=table_name, BackupName="backup")
        .get("BackupDetails")
        .get("BackupArn")
    )

    restored_table_name = "restored-from-backup"
    restored = client.restore_table_from_backup(
        TargetTableName=restored_table_name, BackupArn=backup_arn
    ).get("TableDescription")
    restored.should.have.key("AttributeDefinitions").should.equal(
        table["AttributeDefinitions"]
    )
    restored.should.have.key("TableName").should.equal(restored_table_name)
    restored.should.have.key("KeySchema").should.equal(table["KeySchema"])
    restored.should.have.key("TableStatus")
    restored.should.have.key("ItemCount").should.equal(5)
    restored.should.have.key("TableArn").should.contain(restored_table_name)
    restored.should.have.key("RestoreSummary").should.be.a(dict)
    summary = restored.get("RestoreSummary")
    summary.should.have.key("SourceBackupArn").should.equal(backup_arn)
    summary.should.have.key("SourceTableArn").should.equal(table["TableArn"])
    summary.should.have.key("RestoreDateTime").should.be.a(datetime)
    summary.should.have.key("RestoreInProgress").should.equal(False)


@mock_dynamodb
def test_restore_table_to_point_in_time():
    client = boto3.client("dynamodb", "us-east-1")
    table_name = "test-table"
    resp = client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = resp.get("TableDescription")
    for i in range(5):
        client.put_item(TableName=table_name, Item={"id": {"S": f"item {i}"}})

    restored_table_name = "restored-from-pit"
    restored = client.restore_table_to_point_in_time(
        TargetTableName=restored_table_name, SourceTableName=table_name
    ).get("TableDescription")
    restored.should.have.key("TableName").should.equal(restored_table_name)
    restored.should.have.key("KeySchema").should.equal(table["KeySchema"])
    restored.should.have.key("TableStatus")
    restored.should.have.key("ItemCount").should.equal(5)
    restored.should.have.key("TableArn").should.contain(restored_table_name)
    restored.should.have.key("RestoreSummary").should.be.a(dict)
    summary = restored.get("RestoreSummary")
    summary.should.have.key("SourceTableArn").should.equal(table["TableArn"])
    summary.should.have.key("RestoreDateTime").should.be.a(datetime)
    summary.should.have.key("RestoreInProgress").should.equal(False)


@mock_dynamodb
def test_restore_table_to_point_in_time_raises_error_when_source_not_exist():
    client = boto3.client("dynamodb", "us-east-1")
    table_name = "test-table"
    restored_table_name = "restored-from-pit"
    with pytest.raises(ClientError) as ex:
        client.restore_table_to_point_in_time(
            TargetTableName=restored_table_name, SourceTableName=table_name
        )
    error = ex.value.response["Error"]
    error["Code"].should.equal("SourceTableNotFoundException")
    error["Message"].should.equal(f"Source table not found: {table_name}")


@mock_dynamodb
def test_restore_table_to_point_in_time_raises_error_when_dest_exist():
    client = boto3.client("dynamodb", "us-east-1")
    table_name = "test-table"
    restored_table_name = "restored-from-pit"
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    client.create_table(
        TableName=restored_table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    with pytest.raises(ClientError) as ex:
        client.restore_table_to_point_in_time(
            TargetTableName=restored_table_name, SourceTableName=table_name
        )
    error = ex.value.response["Error"]
    error["Code"].should.equal("TableAlreadyExistsException")
    error["Message"].should.equal(f"Table already exists: {restored_table_name}")


@mock_dynamodb
def test_delete_non_existent_backup_raises_error():
    client = boto3.client("dynamodb", "us-east-1")
    non_existent_arn = "arn:aws:dynamodb:us-east-1:123456789012:table/table-name/backup/01623095754481-2cfcd6f9"
    with pytest.raises(ClientError) as ex:
        client.delete_backup(BackupArn=non_existent_arn)
    error = ex.value.response["Error"]
    error["Code"].should.equal("BackupNotFoundException")
    error["Message"].should.equal(f"Backup not found: {non_existent_arn}")


@mock_dynamodb
def test_delete_backup():
    client = boto3.client("dynamodb", "us-east-1")
    table_name = "test-table-1"
    backup_names = ["backup-1", "backup-2"]
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    for backup_name in backup_names:
        client.create_backup(TableName=table_name, BackupName=backup_name)
    resp = client.list_backups(TableName=table_name, BackupType="USER")
    resp["BackupSummaries"].should.have.length_of(2)
    backup_to_delete = resp["BackupSummaries"][0]["BackupArn"]
    backup_deleted = client.delete_backup(BackupArn=backup_to_delete).get(
        "BackupDescription"
    )
    backup_deleted.should.have.key("SourceTableDetails")
    backup_deleted.should.have.key("BackupDetails")
    details = backup_deleted["BackupDetails"]
    details.should.have.key("BackupArn").should.equal(backup_to_delete)
    details.should.have.key("BackupName").should.be.within(backup_names)
    details.should.have.key("BackupStatus").should.equal("DELETED")
    resp = client.list_backups(TableName=table_name, BackupType="USER")
    resp["BackupSummaries"].should.have.length_of(1)


@mock_dynamodb
def test_source_and_restored_table_items_are_not_linked():
    client = boto3.client("dynamodb", "us-east-1")

    def add_guids_to_table(table, num_items):
        guids = []
        for _ in range(num_items):
            guid = str(uuid.uuid4())
            client.put_item(TableName=table, Item={"id": {"S": guid}})
            guids.append(guid)
        return guids

    source_table_name = "source-table"
    client.create_table(
        TableName=source_table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    guids_original = add_guids_to_table(source_table_name, 5)

    backup_arn = (
        client.create_backup(TableName=source_table_name, BackupName="backup")
        .get("BackupDetails")
        .get("BackupArn")
    )
    guids_added_after_backup = add_guids_to_table(source_table_name, 5)

    restored_table_name = "restored-from-backup"
    client.restore_table_from_backup(
        TargetTableName=restored_table_name, BackupArn=backup_arn
    )
    guids_added_after_restore = add_guids_to_table(restored_table_name, 5)

    source_table_items = client.scan(TableName=source_table_name)
    source_table_items.should.have.key("Count").should.equal(10)
    source_table_guids = [x["id"]["S"] for x in source_table_items["Items"]]
    set(source_table_guids).should.equal(
        set(guids_original) | set(guids_added_after_backup)
    )

    restored_table_items = client.scan(TableName=restored_table_name)
    restored_table_items.should.have.key("Count").should.equal(10)
    restored_table_guids = [x["id"]["S"] for x in restored_table_items["Items"]]
    set(restored_table_guids).should.equal(
        set(guids_original) | set(guids_added_after_restore)
    )


@mock_dynamodb
@pytest.mark.parametrize("region", ["eu-central-1", "ap-south-1"])
def test_describe_endpoints(region):
    client = boto3.client("dynamodb", region)
    res = client.describe_endpoints()["Endpoints"]
    res.should.equal(
        [
            {
                "Address": f"dynamodb.{region}.amazonaws.com",
                "CachePeriodInMinutes": 1440,
            },
        ]
    )


@mock_dynamodb
def test_update_non_existing_item_raises_error_and_does_not_contain_item_afterwards():
    """
    https://github.com/spulec/moto/issues/3729
    Exception is raised, but item was persisted anyway
    Happened because we would create a placeholder, before validating/executing the UpdateExpression
    :return:
    """
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="us-west-2")
    hkey = "primary_partition_key"
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": hkey, "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": hkey, "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    update_expression = {
        "Key": {hkey: "some_identification_string"},
        "UpdateExpression": "set #AA.#AB = :aa",
        "ExpressionAttributeValues": {":aa": "abc"},
        "ExpressionAttributeNames": {"#AA": "some_dict", "#AB": "key1"},
        "ConditionExpression": "attribute_not_exists(#AA.#AB)",
    }
    table = boto3.resource("dynamodb", region_name="us-west-2").Table(name)
    with pytest.raises(ClientError) as err:
        table.update_item(**update_expression)
    err.value.response["Error"]["Code"].should.equal("ValidationException")

    conn.scan(TableName=name)["Items"].should.have.length_of(0)


@mock_dynamodb
def test_batch_write_item():
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    tables = [f"table-{i}" for i in range(3)]
    for name in tables:
        conn.create_table(
            TableName=name,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

    conn.batch_write_item(
        RequestItems={
            tables[0]: [{"PutRequest": {"Item": {"id": "0"}}}],
            tables[1]: [{"PutRequest": {"Item": {"id": "1"}}}],
            tables[2]: [{"PutRequest": {"Item": {"id": "2"}}}],
        }
    )

    for idx, name in enumerate(tables):
        table = conn.Table(f"table-{idx}")
        res = table.get_item(Key={"id": str(idx)})
        assert res["Item"].should.equal({"id": str(idx)})
        scan = table.scan()
        assert scan["Count"].should.equal(1)

    conn.batch_write_item(
        RequestItems={
            tables[0]: [{"DeleteRequest": {"Key": {"id": "0"}}}],
            tables[1]: [{"DeleteRequest": {"Key": {"id": "1"}}}],
            tables[2]: [{"DeleteRequest": {"Key": {"id": "2"}}}],
        }
    )

    for idx, name in enumerate(tables):
        table = conn.Table(f"table-{idx}")
        scan = table.scan()
        assert scan["Count"].should.equal(0)


@mock_dynamodb
def test_gsi_lastevaluatedkey():
    # github.com/spulec/moto/issues/3968
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    name = "test-table"
    table = conn.Table(name)

    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "main_key", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "main_key", "AttributeType": "S"},
            {"AttributeName": "index_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_index",
                "KeySchema": [{"AttributeName": "index_key", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )

    table.put_item(
        Item={
            "main_key": "testkey1",
            "extra_data": "testdata",
            "index_key": "indexkey",
        }
    )
    table.put_item(
        Item={
            "main_key": "testkey2",
            "extra_data": "testdata",
            "index_key": "indexkey",
        }
    )

    response = table.query(
        Limit=1,
        KeyConditionExpression=Key("index_key").eq("indexkey"),
        IndexName="test_index",
    )

    items = response["Items"]
    items.should.have.length_of(1)
    items[0].should.equal(
        {"main_key": "testkey1", "extra_data": "testdata", "index_key": "indexkey"}
    )

    last_evaluated_key = response["LastEvaluatedKey"]
    last_evaluated_key.should.have.length_of(2)
    last_evaluated_key.should.equal({"main_key": "testkey1", "index_key": "indexkey"})


@mock_dynamodb
def test_filter_expression_execution_order():
    # As mentioned here: https://github.com/spulec/moto/issues/3909
    # and documented here: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html#Query.FilterExpression
    # the filter expression should be evaluated after the query.
    # The same applies to scan operations:
    # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html#Scan.FilterExpression

    # If we set limit=1 and apply a filter expression whixh excludes the first result
    # then we should get no items in response.

    conn = boto3.resource("dynamodb", region_name="us-west-2")
    name = "test-filter-expression-table"
    table = conn.Table(name)

    conn.create_table(
        TableName=name,
        KeySchema=[
            {"AttributeName": "hash_key", "KeyType": "HASH"},
            {"AttributeName": "range_key", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "hash_key", "AttributeType": "S"},
            {"AttributeName": "range_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    table.put_item(
        Item={"hash_key": "keyvalue", "range_key": "A", "filtered_attribute": "Y"}
    )
    table.put_item(
        Item={"hash_key": "keyvalue", "range_key": "B", "filtered_attribute": "Z"}
    )

    # test query

    query_response_1 = table.query(
        Limit=1,
        KeyConditionExpression=Key("hash_key").eq("keyvalue"),
        FilterExpression=Attr("filtered_attribute").eq("Z"),
    )

    query_items_1 = query_response_1["Items"]
    query_items_1.should.have.length_of(0)

    query_last_evaluated_key = query_response_1["LastEvaluatedKey"]
    query_last_evaluated_key.should.have.length_of(2)
    query_last_evaluated_key.should.equal({"hash_key": "keyvalue", "range_key": "A"})

    query_response_2 = table.query(
        Limit=1,
        KeyConditionExpression=Key("hash_key").eq("keyvalue"),
        FilterExpression=Attr("filtered_attribute").eq("Z"),
        ExclusiveStartKey=query_last_evaluated_key,
    )

    query_items_2 = query_response_2["Items"]
    query_items_2.should.have.length_of(1)
    query_items_2[0].should.equal(
        {"hash_key": "keyvalue", "filtered_attribute": "Z", "range_key": "B"}
    )

    # test scan

    scan_response_1 = table.scan(
        Limit=1, FilterExpression=Attr("filtered_attribute").eq("Z")
    )

    scan_items_1 = scan_response_1["Items"]
    scan_items_1.should.have.length_of(0)

    scan_last_evaluated_key = scan_response_1["LastEvaluatedKey"]
    scan_last_evaluated_key.should.have.length_of(2)
    scan_last_evaluated_key.should.equal({"hash_key": "keyvalue", "range_key": "A"})

    scan_response_2 = table.scan(
        Limit=1,
        FilterExpression=Attr("filtered_attribute").eq("Z"),
        ExclusiveStartKey=query_last_evaluated_key,
    )

    scan_items_2 = scan_response_2["Items"]
    scan_items_2.should.have.length_of(1)
    scan_items_2[0].should.equal(
        {"hash_key": "keyvalue", "filtered_attribute": "Z", "range_key": "B"}
    )


@mock_dynamodb
def test_projection_expression_execution_order():
    # projection expression needs to be applied after calculation of
    # LastEvaluatedKey as it is possible for LastEvaluatedKey to
    # include attributes which are not projected.

    conn = boto3.resource("dynamodb", region_name="us-west-2")
    name = "test-projection-expression-with-gsi"
    table = conn.Table(name)

    conn.create_table(
        TableName=name,
        KeySchema=[
            {"AttributeName": "hash_key", "KeyType": "HASH"},
            {"AttributeName": "range_key", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "hash_key", "AttributeType": "S"},
            {"AttributeName": "range_key", "AttributeType": "S"},
            {"AttributeName": "index_key", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_index",
                "KeySchema": [{"AttributeName": "index_key", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    table.put_item(Item={"hash_key": "keyvalue", "range_key": "A", "index_key": "Z"})
    table.put_item(Item={"hash_key": "keyvalue", "range_key": "B", "index_key": "Z"})

    # test query

    # if projection expression is applied before LastEvaluatedKey is computed
    # then this raises an exception.
    table.query(
        Limit=1,
        IndexName="test_index",
        KeyConditionExpression=Key("index_key").eq("Z"),
        ProjectionExpression="#a",
        ExpressionAttributeNames={"#a": "hashKey"},
    )
    # if projection expression is applied before LastEvaluatedKey is computed
    # then this raises an exception.
    table.scan(
        Limit=1,
        IndexName="test_index",
        ProjectionExpression="#a",
        ExpressionAttributeNames={"#a": "hashKey"},
    )


@mock_dynamodb
def test_invalid_projection_expressions():
    table_name = "test-projection-expressions-table"
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "customer", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "customer", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    with pytest.raises(
        ClientError,
        match="ProjectionExpression: Attribute name is a reserved keyword; reserved keyword: name",
    ):
        client.scan(TableName=table_name, ProjectionExpression="name")
    with pytest.raises(
        ClientError, match="ProjectionExpression: Attribute name starts with a number"
    ):
        client.scan(TableName=table_name, ProjectionExpression="3ame")
    with pytest.raises(
        ClientError, match="ProjectionExpression: Attribute name contains white space"
    ):
        client.scan(TableName=table_name, ProjectionExpression="na me")

    with pytest.raises(
        ClientError,
        match="ProjectionExpression: Attribute name is a reserved keyword; reserved keyword: name",
    ):
        client.get_item(
            TableName=table_name,
            Key={"customer": {"S": "a"}},
            ProjectionExpression="name",
        )

    with pytest.raises(
        ClientError,
        match="ProjectionExpression: Attribute name is a reserved keyword; reserved keyword: name",
    ):
        client.query(
            TableName=table_name,
            KeyConditionExpression="a",
            ProjectionExpression="name",
        )

    with pytest.raises(
        ClientError,
        match="ProjectionExpression: Attribute name is a reserved keyword; reserved keyword: name",
    ):
        client.scan(TableName=table_name, ProjectionExpression="not_a_keyword, name")
    with pytest.raises(
        ClientError, match="ProjectionExpression: Attribute name starts with a number"
    ):
        client.scan(TableName=table_name, ProjectionExpression="not_a_keyword, 3ame")
    with pytest.raises(
        ClientError, match="ProjectionExpression: Attribute name contains white space"
    ):
        client.scan(TableName=table_name, ProjectionExpression="not_a_keyword, na me")
