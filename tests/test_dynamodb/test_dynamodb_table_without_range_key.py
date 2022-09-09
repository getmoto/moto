import boto3
from boto3.dynamodb.conditions import Key
import sure  # noqa # pylint: disable=unused-import
import pytest
from datetime import datetime
from botocore.exceptions import ClientError
from moto import mock_dynamodb
from moto.core import ACCOUNT_ID
import botocore


@mock_dynamodb
def test_create_table_boto3():
    client = boto3.client("dynamodb", region_name="us-east-1")
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

    actual.should.have.key("AttributeDefinitions").equal(
        [
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "gsi_col", "AttributeType": "S"},
        ]
    )
    actual.should.have.key("CreationDateTime").be.a(datetime)
    actual.should.have.key("GlobalSecondaryIndexes").equal(
        [
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
    )
    actual.should.have.key("LocalSecondaryIndexes").equal([])
    actual.should.have.key("ProvisionedThroughput").equal(
        {"NumberOfDecreasesToday": 0, "ReadCapacityUnits": 1, "WriteCapacityUnits": 1}
    )
    actual.should.have.key("TableSizeBytes").equal(0)
    actual.should.have.key("TableName").equal("messages")
    actual.should.have.key("TableStatus").equal("ACTIVE")
    actual.should.have.key("TableArn").equal(
        f"arn:aws:dynamodb:us-east-1:{ACCOUNT_ID}:table/messages"
    )
    actual.should.have.key("KeySchema").equal(
        [{"AttributeName": "id", "KeyType": "HASH"}]
    )
    actual.should.have.key("ItemCount").equal(0)


@mock_dynamodb
def test_delete_table_boto3():
    conn = boto3.client("dynamodb", region_name="us-west-2")
    conn.create_table(
        TableName="messages",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    conn.list_tables()["TableNames"].should.have.length_of(1)

    conn.delete_table(TableName="messages")
    conn.list_tables()["TableNames"].should.have.length_of(0)

    with pytest.raises(ClientError) as ex:
        conn.delete_table(TableName="messages")

    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal("Requested resource not found")


@mock_dynamodb
def test_item_add_and_describe_and_update_boto3():
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
    returned_item.shouldnt.have.key("ConsumedCapacity")

    dict(returned_item["Item"]).should.equal(
        {"id": "LOLCat Forum", "Body": "http://url_to_lolcat.gif", "SentBy": "User A"}
    )

    table.update_item(
        Key={"id": "LOLCat Forum"},
        UpdateExpression="SET SentBy=:user",
        ExpressionAttributeValues={":user": "User B"},
    )

    returned_item = table.get_item(Key={"id": "LOLCat Forum"})
    returned_item["Item"].should.equal(
        {"id": "LOLCat Forum", "Body": "http://url_to_lolcat.gif", "SentBy": "User B"}
    )


@mock_dynamodb
def test_item_put_without_table_boto3():
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

    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal("Requested resource not found")


@mock_dynamodb
def test_get_item_with_undeclared_table_boto3():
    conn = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        conn.get_item(TableName="messages", Key={"forum_name": {"S": "LOLCat Forum"}})

    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal("Requested resource not found")


@mock_dynamodb
def test_delete_item_boto3():
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

    table.item_count.should.equal(1)

    table.delete_item(Key={"id": "LOLCat Forum"})

    table.item_count.should.equal(0)

    table.delete_item(Key={"id": "LOLCat Forum"})


@mock_dynamodb
def test_delete_item_with_undeclared_table_boto3():
    conn = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        conn.delete_item(
            TableName="messages", Key={"forum_name": {"S": "LOLCat Forum"}}
        )

    ex.value.response["Error"]["Code"].should.equal("ConditionalCheckFailedException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "A condition specified in the operation could not be evaluated."
    )


@mock_dynamodb
def test_scan_with_undeclared_table_boto3():
    conn = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        conn.scan(TableName="messages")

    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal("Requested resource not found")


@mock_dynamodb
def test_get_key_schema():
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = conn.create_table(
        TableName="messages",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    table.key_schema.should.equal([{"AttributeName": "id", "KeyType": "HASH"}])


@mock_dynamodb
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
    dict(returned_item["Item"]).should.equal(expected_item)


@mock_dynamodb
def test_update_item_set_boto3():
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
    dict(returned_item).should.equal({"username": "steve", "foo": "bar", "blah": "baz"})


@mock_dynamodb
def test_boto3_create_table():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table.name.should.equal("users")


def _create_user_table():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    return dynamodb.Table("users")


@mock_dynamodb
def test_boto3_conditions():
    table = _create_user_table()

    table.put_item(Item={"username": "johndoe"})
    table.put_item(Item={"username": "janedoe"})

    response = table.query(KeyConditionExpression=Key("username").eq("johndoe"))
    response["Count"].should.equal(1)
    response["Items"].should.have.length_of(1)
    response["Items"][0].should.equal({"username": "johndoe"})


@mock_dynamodb
def test_boto3_put_item_conditions_pass():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"foo": {"ComparisonOperator": "EQ", "AttributeValueList": ["bar"]}},
    )
    final_item = table.get_item(Key={"username": "johndoe"})
    assert dict(final_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb
def test_boto3_put_item_conditions_pass_because_expect_not_exists_by_compare_to_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"whatever": {"ComparisonOperator": "NULL"}},
    )
    final_item = table.get_item(Key={"username": "johndoe"})
    assert dict(final_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb
def test_boto3_put_item_conditions_pass_because_expect_exists_by_compare_to_not_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"foo": {"ComparisonOperator": "NOT_NULL"}},
    )
    final_item = table.get_item(Key={"username": "johndoe"})
    assert dict(final_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb
def test_boto3_put_item_conditions_fail():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item.when.called_with(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"foo": {"ComparisonOperator": "NE", "AttributeValueList": ["bar"]}},
    ).should.throw(botocore.client.ClientError)


@mock_dynamodb
def test_boto3_update_item_conditions_fail():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "baz"})
    table.update_item.when.called_with(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:bar",
        Expected={"foo": {"Value": "bar"}},
        ExpressionAttributeValues={":bar": "bar"},
    ).should.throw(botocore.client.ClientError)


@mock_dynamodb
def test_boto3_update_item_conditions_fail_because_expect_not_exists():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "baz"})
    table.update_item.when.called_with(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:bar",
        Expected={"foo": {"Exists": False}},
        ExpressionAttributeValues={":bar": "bar"},
    ).should.throw(botocore.client.ClientError)


@mock_dynamodb
def test_boto3_update_item_conditions_fail_because_expect_not_exists_by_compare_to_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "baz"})
    table.update_item.when.called_with(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:bar",
        Expected={"foo": {"ComparisonOperator": "NULL"}},
        ExpressionAttributeValues={":bar": "bar"},
    ).should.throw(botocore.client.ClientError)


@mock_dynamodb
def test_boto3_update_item_conditions_pass():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:baz",
        Expected={"foo": {"Value": "bar"}},
        ExpressionAttributeValues={":baz": "baz"},
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert dict(returned_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb
def test_boto3_update_item_conditions_pass_because_expect_not_exists():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:baz",
        Expected={"whatever": {"Exists": False}},
        ExpressionAttributeValues={":baz": "baz"},
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert dict(returned_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb
def test_boto3_update_item_conditions_pass_because_expect_not_exists_by_compare_to_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:baz",
        Expected={"whatever": {"ComparisonOperator": "NULL"}},
        ExpressionAttributeValues={":baz": "baz"},
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert dict(returned_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb
def test_boto3_update_item_conditions_pass_because_expect_exists_by_compare_to_not_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.update_item(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:baz",
        Expected={"foo": {"ComparisonOperator": "NOT_NULL"}},
        ExpressionAttributeValues={":baz": "baz"},
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert dict(returned_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb
def test_boto3_update_settype_item_with_conditions():
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
    assert dict(returned_item)["Item"]["foo"].should.equal(set(["baz"]))


@mock_dynamodb
def test_scan_pagination():
    table = _create_user_table()

    expected_usernames = ["user{0}".format(i) for i in range(10)]
    for u in expected_usernames:
        table.put_item(Item={"username": u})

    page1 = table.scan(Limit=6)
    page1["Count"].should.equal(6)
    page1["Items"].should.have.length_of(6)
    page1.should.have.key("LastEvaluatedKey")

    page2 = table.scan(Limit=6, ExclusiveStartKey=page1["LastEvaluatedKey"])
    page2["Count"].should.equal(4)
    page2["Items"].should.have.length_of(4)
    page2.should_not.have.key("LastEvaluatedKey")

    results = page1["Items"] + page2["Items"]
    usernames = set([r["username"] for r in results])
    usernames.should.equal(set(expected_usernames))


@mock_dynamodb
def test_scan_by_index():
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

    dynamodb.put_item(
        TableName="test",
        Item={"id": {"S": "1"}, "col1": {"S": "val1"}, "gsi_col": {"S": "gsi_val1"}},
    )

    dynamodb.put_item(
        TableName="test",
        Item={"id": {"S": "2"}, "col1": {"S": "val2"}, "gsi_col": {"S": "gsi_val2"}},
    )

    dynamodb.put_item(TableName="test", Item={"id": {"S": "3"}, "col1": {"S": "val3"}})

    res = dynamodb.scan(TableName="test")
    assert res["Count"] == 3
    assert len(res["Items"]) == 3

    res = dynamodb.scan(TableName="test", IndexName="test_gsi")
    assert res["Count"] == 2
    assert len(res["Items"]) == 2

    res = dynamodb.scan(TableName="test", IndexName="test_gsi", Limit=1)
    assert res["Count"] == 1
    assert len(res["Items"]) == 1
    last_eval_key = res["LastEvaluatedKey"]
    assert last_eval_key["id"]["S"] == "1"
    assert last_eval_key["gsi_col"]["S"] == "gsi_val1"
