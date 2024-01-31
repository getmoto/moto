import boto3
import pytest
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.dynamodb.limits import HASH_KEY_MAX_LENGTH, RANGE_KEY_MAX_LENGTH


@mock_aws
def test_item_add_long_string_hash_key_exception():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="us-west-2")
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    conn.put_item(
        TableName=name,
        Item={
            "forum_name": {"S": "x" * HASH_KEY_MAX_LENGTH},
            "subject": {"S": "Check this out!"},
            "Body": {"S": "http://url_to_lolcat.gif"},
            "SentBy": {"S": "test"},
            "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
        },
    )

    with pytest.raises(ClientError) as ex:
        conn.put_item(
            TableName=name,
            Item={
                "forum_name": {"S": "x" * (HASH_KEY_MAX_LENGTH + 1)},
                "subject": {"S": "Check this out!"},
                "Body": {"S": "http://url_to_lolcat.gif"},
                "SentBy": {"S": "test"},
                "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
            },
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    # deliberately no space between "of" and "2048"
    assert (
        ex.value.response["Error"]["Message"]
        == "One or more parameter values were invalid: Size of hashkey has exceeded the maximum size limit of2048 bytes"
    )


@mock_aws
def test_item_add_long_string_nonascii_hash_key_exception():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="us-west-2")
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    emoji_b = b"\xf0\x9f\x98\x83"  # smile emoji
    emoji = emoji_b.decode("utf-8")  # 1 character, but 4 bytes
    short_enough = emoji * int(HASH_KEY_MAX_LENGTH / len(emoji.encode("utf-8")))
    too_long = "x" + short_enough

    conn.put_item(
        TableName=name,
        Item={
            "forum_name": {"S": short_enough},
            "subject": {"S": "Check this out!"},
            "Body": {"S": "http://url_to_lolcat.gif"},
            "SentBy": {"S": "test"},
            "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
        },
    )

    with pytest.raises(ClientError) as ex:
        conn.put_item(
            TableName=name,
            Item={
                "forum_name": {"S": too_long},
                "subject": {"S": "Check this out!"},
                "Body": {"S": "http://url_to_lolcat.gif"},
                "SentBy": {"S": "test"},
                "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
            },
        )

    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    # deliberately no space between "of" and "2048"
    assert (
        ex.value.response["Error"]["Message"]
        == "One or more parameter values were invalid: Size of hashkey has exceeded the maximum size limit of2048 bytes"
    )


@mock_aws
def test_item_add_long_string_range_key_exception():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="us-west-2")
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

    conn.put_item(
        TableName=name,
        Item={
            "forum_name": {"S": "LOLCat Forum"},
            "subject": {"S": "Check this out!"},
            "Body": {"S": "http://url_to_lolcat.gif"},
            "SentBy": {"S": "someone@somewhere.edu"},
            "ReceivedTime": {"S": "x" * RANGE_KEY_MAX_LENGTH},
        },
    )

    with pytest.raises(ClientError) as ex:
        conn.put_item(
            TableName=name,
            Item={
                "forum_name": {"S": "LOLCat Forum"},
                "subject": {"S": "Check this out!"},
                "Body": {"S": "http://url_to_lolcat.gif"},
                "SentBy": {"S": "someone@somewhere.edu"},
                "ReceivedTime": {"S": "x" * (RANGE_KEY_MAX_LENGTH + 1)},
            },
        )

    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "One or more parameter values were invalid: Aggregated size of all range keys has exceeded the size limit of 1024 bytes"
    )


@mock_aws
def test_put_long_string_gsi_range_key_exception():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="us-west-2")
    conn.create_table(
        TableName=name,
        KeySchema=[
            {"AttributeName": "partition_key", "KeyType": "HASH"},
            {"AttributeName": "sort_key", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "partition_key", "AttributeType": "S"},
            {"AttributeName": "sort_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    conn.put_item(
        TableName=name,
        Item={
            # partition_key is only used as the HASH key
            # so we can set it to range key length
            "partition_key": {"S": "x" * (RANGE_KEY_MAX_LENGTH + 1)},
            "sort_key": {"S": "sk"},
        },
    )

    conn.update_table(
        TableName=name,
        AttributeDefinitions=[
            {"AttributeName": "partition_key", "AttributeType": "S"},
            {"AttributeName": "sort_key", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexUpdates=[
            {
                "Create": {
                    "IndexName": "random-table-index",
                    "KeySchema": [
                        {"AttributeName": "sort_key", "KeyType": "HASH"},
                        {"AttributeName": "partition_key", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "KEYS_ONLY"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 20,
                        "WriteCapacityUnits": 20,
                    },
                }
            },
        ],
    )

    with pytest.raises(ClientError) as ex:
        conn.put_item(
            TableName=name,
            Item={
                # partition_key is used as a range key in the GSI
                # so updating this should still fail
                "partition_key": {"S": "y" * (RANGE_KEY_MAX_LENGTH + 1)},
                "sort_key": {"S": "sk2"},
            },
        )

    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "One or more parameter values were invalid: Aggregated size of all range keys has exceeded the size limit of 1024 bytes"
    )


@mock_aws
def test_update_item_with_long_string_hash_key_exception():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="us-west-2")
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    conn.update_item(
        TableName=name,
        Key={
            "forum_name": {"S": "x" * HASH_KEY_MAX_LENGTH},
            "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
        },
        UpdateExpression="set body=:New",
        ExpressionAttributeValues={":New": {"S": "hello"}},
    )

    with pytest.raises(ClientError) as ex:
        conn.update_item(
            TableName=name,
            Key={
                "forum_name": {"S": "x" * (HASH_KEY_MAX_LENGTH + 1)},
                "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
            },
            UpdateExpression="set body=:New",
            ExpressionAttributeValues={":New": {"S": "hello"}},
        )

    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    # deliberately no space between "of" and "2048"
    assert (
        ex.value.response["Error"]["Message"]
        == "One or more parameter values were invalid: Size of hashkey has exceeded the maximum size limit of2048 bytes"
    )


@mock_aws
def test_update_item_with_long_string_range_key_exception():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="us-west-2")
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
    conn.update_item(
        TableName=name,
        Key={
            "forum_name": {"S": "Lolcat Forum"},
            "ReceivedTime": {"S": "x" * RANGE_KEY_MAX_LENGTH},
        },
        UpdateExpression="set body=:New",
        ExpressionAttributeValues={":New": {"S": "hello"}},
    )

    with pytest.raises(ClientError) as ex:
        conn.update_item(
            TableName=name,
            Key={
                "forum_name": {"S": "Lolcat Forum"},
                "ReceivedTime": {"S": "x" * (RANGE_KEY_MAX_LENGTH + 1)},
            },
            UpdateExpression="set body=:New",
            ExpressionAttributeValues={":New": {"S": "hello"}},
        )

    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    # deliberately no space between "of" and "2048"
    assert (
        ex.value.response["Error"]["Message"]
        == "One or more parameter values were invalid: Aggregated size of all range keys has exceeded the size limit of 1024 bytes"
    )


@mock_aws
def test_item_add_empty_key_exception():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="us-west-2")
    conn.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "forum_name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "forum_name", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    with pytest.raises(ClientError) as ex:
        conn.get_item(
            TableName=name,
            Key={"forum_name": {"S": ""}},
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "One or more parameter values are not valid. The AttributeValue for a key attribute cannot contain an empty string value. Key: forum_name"
    )


@mock_aws
def test_query_empty_key_exception():
    name = "TestTable"
    conn = boto3.client("dynamodb", region_name="us-west-2")
    conn.create_table(
        TableName=name,
        KeySchema=[
            {"AttributeName": "hk", "KeyType": "HASH"},
            {"AttributeName": "rk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "hk", "AttributeType": "S"},
            {"AttributeName": "rk", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = boto3.resource("dynamodb", "us-west-2").Table(name)

    with pytest.raises(ClientError) as ex:
        table.query(KeyConditionExpression=Key("hk").eq(""))
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "One or more parameter values are not valid. The AttributeValue for a key attribute cannot contain an empty string value. Key: hk"
    )

    with pytest.raises(ClientError) as ex:
        table.query(KeyConditionExpression=Key("hk").eq("sth") & Key("rk").eq(""))
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "One or more parameter values are not valid. The AttributeValue for a key attribute cannot contain an empty string value. Key: rk"
    )
