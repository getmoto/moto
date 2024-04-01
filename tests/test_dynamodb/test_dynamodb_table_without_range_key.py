from datetime import datetime

import boto3
import pytest
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from . import dynamodb_aws_verified


@mock_aws
def test_create_table():
    client = boto3.client("dynamodb", region_name="us-east-2")
    client.create_table(
        TableName="messages",
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

    actual = client.describe_table(TableName="messages")["Table"]

    assert actual["AttributeDefinitions"] == [
        {"AttributeName": "id", "AttributeType": "S"},
        {"AttributeName": "gsi_col", "AttributeType": "S"},
    ]
    assert isinstance(actual["CreationDateTime"], datetime)
    assert actual["GlobalSecondaryIndexes"] == [
        {
            "IndexName": "test_gsi",
            "KeySchema": [{"AttributeName": "gsi_col", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
            "IndexStatus": "ACTIVE",
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 1,
                "WriteCapacityUnits": 1,
            },
        }
    ]
    assert actual["LocalSecondaryIndexes"] == []
    assert actual["ProvisionedThroughput"] == {
        "NumberOfDecreasesToday": 0,
        "ReadCapacityUnits": 1,
        "WriteCapacityUnits": 1,
    }
    assert actual["TableSizeBytes"] == 0
    assert actual["TableName"] == "messages"
    assert actual["TableStatus"] == "ACTIVE"
    assert (
        actual["TableArn"] == f"arn:aws:dynamodb:us-east-2:{ACCOUNT_ID}:table/messages"
    )
    assert actual["KeySchema"] == [{"AttributeName": "id", "KeyType": "HASH"}]
    assert actual["ItemCount"] == 0


@mock_aws
def test_delete_table():
    conn = boto3.client("dynamodb", region_name="us-west-2")
    conn.create_table(
        TableName="messages",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    assert len(conn.list_tables()["TableNames"]) == 1

    conn.delete_table(TableName="messages")
    assert conn.list_tables()["TableNames"] == []

    with pytest.raises(ClientError) as ex:
        conn.delete_table(TableName="messages")

    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Message"] == "Requested resource not found"


@mock_aws
def test_item_add_and_describe_and_update():
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = conn.create_table(
        TableName="messages",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    data = {
        "id": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
    }

    table.put_item(Item=data)
    returned_item = table.get_item(Key={"id": "LOLCat Forum"})
    assert "ConsumedCapacity" not in returned_item

    assert returned_item["Item"] == {
        "id": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
    }

    table.update_item(
        Key={"id": "LOLCat Forum"},
        UpdateExpression="SET SentBy=:user",
        ExpressionAttributeValues={":user": "User B"},
    )

    returned_item = table.get_item(Key={"id": "LOLCat Forum"})
    assert returned_item["Item"] == {
        "id": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User B",
    }


@mock_aws
def test_item_put_without_table():
    conn = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        conn.put_item(
            TableName="messages",
            Item={
                "forum_name": {"S": "LOLCat Forum"},
                "Body": {"S": "http://url_to_lolcat.gif"},
                "SentBy": {"S": "User A"},
            },
        )

    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Message"] == "Requested resource not found"


@mock_aws
def test_get_item_with_undeclared_table():
    conn = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        conn.get_item(TableName="messages", Key={"forum_name": {"S": "LOLCat Forum"}})

    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Message"] == "Requested resource not found"


@mock_aws
def test_delete_item():
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = conn.create_table(
        TableName="messages",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    item_data = {
        "id": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    table.put_item(Item=item_data)

    assert table.item_count == 1

    table.delete_item(Key={"id": "LOLCat Forum"})

    assert table.item_count == 0

    table.delete_item(Key={"id": "LOLCat Forum"})


@mock_aws
def test_delete_item_with_undeclared_table():
    conn = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        conn.delete_item(
            TableName="messages", Key={"forum_name": {"S": "LOLCat Forum"}}
        )

    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Message"] == "Requested resource not found"


@mock_aws
def test_scan_with_undeclared_table():
    conn = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        conn.scan(TableName="messages")

    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Message"] == "Requested resource not found"


@mock_aws
def test_get_key_schema():
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = conn.create_table(
        TableName="messages",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    assert table.key_schema == [{"AttributeName": "id", "KeyType": "HASH"}]


@mock_aws
def test_update_item_double_nested_remove():
    conn = boto3.client("dynamodb", region_name="us-east-1")
    conn.create_table(
        TableName="messages",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    item = {
        "username": {"S": "steve"},
        "Meta": {
            "M": {"Name": {"M": {"First": {"S": "Steve"}, "Last": {"S": "Urkel"}}}}
        },
    }
    conn.put_item(TableName="messages", Item=item)
    key_map = {"username": {"S": "steve"}}

    # Then remove the Meta.FullName field
    conn.update_item(
        TableName="messages",
        Key=key_map,
        UpdateExpression="REMOVE Meta.#N.#F",
        ExpressionAttributeNames={"#N": "Name", "#F": "First"},
    )

    returned_item = conn.get_item(TableName="messages", Key=key_map)
    expected_item = {
        "username": {"S": "steve"},
        "Meta": {"M": {"Name": {"M": {"Last": {"S": "Urkel"}}}}},
    }
    assert returned_item["Item"] == expected_item


@mock_aws
def test_update_item_set():
    conn = boto3.resource("dynamodb", region_name="us-east-1")
    table = conn.create_table(
        TableName="messages",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    data = {"username": "steve", "SentBy": "User A"}
    table.put_item(Item=data)
    key_map = {"username": "steve"}

    table.update_item(
        Key=key_map,
        UpdateExpression="SET foo=:bar, blah=:baz REMOVE SentBy",
        ExpressionAttributeValues={":bar": "bar", ":baz": "baz"},
    )

    returned_item = table.get_item(Key=key_map)["Item"]
    assert returned_item == {"username": "steve", "foo": "bar", "blah": "baz"}


@mock_aws
def test_create_table__using_resource():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    assert table.name == "users"


def _create_user_table():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    return dynamodb.Table("users")


@mock_aws
def test_conditions():
    table = _create_user_table()

    table.put_item(Item={"username": "johndoe"})
    table.put_item(Item={"username": "janedoe"})

    response = table.query(KeyConditionExpression=Key("username").eq("johndoe"))
    assert response["Count"] == 1
    assert response["Items"] == [{"username": "johndoe"}]


@mock_aws
def test_put_item_conditions_pass():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"foo": {"ComparisonOperator": "EQ", "AttributeValueList": ["bar"]}},
    )
    final_item = table.get_item(Key={"username": "johndoe"})
    assert final_item["Item"]["foo"] == "baz"


@mock_aws
def test_put_item_conditions_pass_because_expect_not_exists_by_compare_to_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"whatever": {"ComparisonOperator": "NULL"}},
    )
    final_item = table.get_item(Key={"username": "johndoe"})
    assert final_item["Item"]["foo"] == "baz"


@mock_aws
def test_put_item_conditions_pass_because_expect_exists_by_compare_to_not_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"foo": {"ComparisonOperator": "NOT_NULL"}},
    )
    final_item = table.get_item(Key={"username": "johndoe"})
    assert final_item["Item"]["foo"] == "baz"


@mock_aws
def test_put_item_conditions_fail():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    with pytest.raises(ClientError) as exc:
        table.put_item(
            Item={"username": "johndoe", "foo": "baz"},
            Expected={
                "foo": {"ComparisonOperator": "NE", "AttributeValueList": ["bar"]}
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ConditionalCheckFailedException"


@mock_aws
def test_update_item_conditions_fail():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "baz"})
    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"username": "johndoe"},
            UpdateExpression="SET foo=:bar",
            Expected={"foo": {"Value": "bar"}},
            ExpressionAttributeValues={":bar": "bar"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ConditionalCheckFailedException"


@mock_aws
def test_update_item_conditions_fail_because_expect_not_exists():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "baz"})
    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"username": "johndoe"},
            UpdateExpression="SET foo=:bar",
            Expected={"foo": {"Exists": False}},
            ExpressionAttributeValues={":bar": "bar"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ConditionalCheckFailedException"


@mock_aws
def test_update_item_conditions_fail_because_expect_not_exists_by_compare_to_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "baz"})
    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"username": "johndoe"},
            UpdateExpression="SET foo=:bar",
            Expected={"foo": {"ComparisonOperator": "NULL"}},
            ExpressionAttributeValues={":bar": "bar"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ConditionalCheckFailedException"


@mock_aws
def test_update_item_conditions_pass():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:baz",
        Expected={"foo": {"Value": "bar"}},
        ExpressionAttributeValues={":baz": "baz"},
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert returned_item["Item"]["foo"] == "baz"


@mock_aws
def test_update_item_conditions_pass_because_expect_not_exists():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:baz",
        Expected={"whatever": {"Exists": False}},
        ExpressionAttributeValues={":baz": "baz"},
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert returned_item["Item"]["foo"] == "baz"


@mock_aws
def test_update_item_conditions_pass_because_expect_not_exists_by_compare_to_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:baz",
        Expected={"whatever": {"ComparisonOperator": "NULL"}},
        ExpressionAttributeValues={":baz": "baz"},
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert returned_item["Item"]["foo"] == "baz"


@mock_aws
def test_update_item_conditions_pass_because_expect_exists_by_compare_to_not_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:baz",
        Expected={"foo": {"ComparisonOperator": "NOT_NULL"}},
        ExpressionAttributeValues={":baz": "baz"},
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert returned_item["Item"]["foo"] == "baz"


@mock_aws
def test_update_settype_item_with_conditions():
    class OrderedSet(set):
        """A set with predictable iteration order"""

        def __init__(self, values):
            super().__init__(values)
            self.__ordered_values = values

        def __iter__(self):
            return iter(self.__ordered_values)

    table = _create_user_table()
    table.put_item(Item={"username": "johndoe"})
    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:new_value",
        ExpressionAttributeValues={":new_value": OrderedSet(["hello", "world"])},
    )

    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:new_value",
        ExpressionAttributeValues={":new_value": set(["baz"])},
        Expected={
            "foo": {
                "ComparisonOperator": "EQ",
                "AttributeValueList": [
                    OrderedSet(["world", "hello"])  # Opposite order to original
                ],
            }
        },
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert returned_item["Item"]["foo"] == set(["baz"])


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_scan_pagination(table_name=None):
    table = boto3.resource("dynamodb", "us-east-1").Table(table_name)
    expected_usernames = [f"user{i}" for i in range(10)]
    for u in expected_usernames:
        table.put_item(Item={"pk": u})

    page1 = table.scan(Limit=6)
    assert page1["Count"] == 6
    assert len(page1["Items"]) == 6
    page1_results = [r["pk"] for r in page1["Items"]]

    page2 = table.scan(Limit=6, ExclusiveStartKey=page1["LastEvaluatedKey"])
    assert page2["Count"] == 4
    assert len(page2["Items"]) == 4
    assert "LastEvaluatedKey" not in page2
    page2_results = [r["pk"] for r in page2["Items"]]

    usernames = set(page1_results + page2_results)
    assert usernames == set(expected_usernames)
