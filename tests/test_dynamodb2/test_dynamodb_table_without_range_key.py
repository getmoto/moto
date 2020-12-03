from __future__ import unicode_literals

import boto
import boto3
from boto3.dynamodb.conditions import Key
import sure  # noqa
from freezegun import freeze_time
from boto.exception import JSONResponseError
from moto import mock_dynamodb2, mock_dynamodb2_deprecated
from tests.helpers import requires_boto_gte
import botocore

try:
    from boto.dynamodb2.fields import HashKey
    from boto.dynamodb2.table import Table
    from boto.dynamodb2.table import Item
    from boto.dynamodb2.exceptions import ConditionalCheckFailedException, ItemNotFound
except ImportError:
    pass


def create_table():
    table = Table.create(
        "messages", schema=[HashKey("forum_name")], throughput={"read": 10, "write": 10}
    )
    return table


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
@freeze_time("2012-01-14")
def test_create_table():
    create_table()
    expected = {
        "Table": {
            "AttributeDefinitions": [
                {"AttributeName": "forum_name", "AttributeType": "S"}
            ],
            "ProvisionedThroughput": {
                "NumberOfDecreasesToday": 0,
                "WriteCapacityUnits": 10,
                "ReadCapacityUnits": 10,
            },
            "TableSizeBytes": 0,
            "TableName": "messages",
            "TableStatus": "ACTIVE",
            "TableArn": "arn:aws:dynamodb:us-east-1:123456789011:table/messages",
            "KeySchema": [{"KeyType": "HASH", "AttributeName": "forum_name"}],
            "ItemCount": 0,
            "CreationDateTime": 1326499200.0,
            "GlobalSecondaryIndexes": [],
            "LocalSecondaryIndexes": [],
        }
    }
    conn = boto.dynamodb2.connect_to_region(
        "us-east-1", aws_access_key_id="ak", aws_secret_access_key="sk"
    )

    conn.describe_table("messages").should.equal(expected)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_delete_table():
    create_table()
    conn = boto.dynamodb2.layer1.DynamoDBConnection()
    conn.list_tables()["TableNames"].should.have.length_of(1)

    conn.delete_table("messages")
    conn.list_tables()["TableNames"].should.have.length_of(0)

    conn.delete_table.when.called_with("messages").should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_update_table_throughput():
    table = create_table()
    table.throughput["read"].should.equal(10)
    table.throughput["write"].should.equal(10)

    table.update(throughput={"read": 5, "write": 6})

    table.throughput["read"].should.equal(5)
    table.throughput["write"].should.equal(6)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_item_add_and_describe_and_update():
    table = create_table()

    data = {
        "forum_name": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
    }

    table.put_item(data=data)
    returned_item = table.get_item(forum_name="LOLCat Forum")
    returned_item.should_not.be.none

    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User A",
        }
    )

    returned_item["SentBy"] = "User B"
    returned_item.save(overwrite=True)

    returned_item = table.get_item(forum_name="LOLCat Forum")
    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User B",
        }
    )


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_item_partial_save():
    table = create_table()

    data = {
        "forum_name": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
    }

    table.put_item(data=data)
    returned_item = table.get_item(forum_name="LOLCat Forum")

    returned_item["SentBy"] = "User B"
    returned_item.partial_save()

    returned_item = table.get_item(forum_name="LOLCat Forum")
    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User B",
        }
    )


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_item_put_without_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.put_item.when.called_with(
        table_name="undeclared-table",
        item={
            "forum_name": "LOLCat Forum",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User A",
        },
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_get_item_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.get_item.when.called_with(
        table_name="undeclared-table", key={"forum_name": {"S": "LOLCat Forum"}}
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.30.0")
@mock_dynamodb2_deprecated
def test_delete_item():
    table = create_table()

    item_data = {
        "forum_name": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = Item(table, item_data)
    item.save()
    table.count().should.equal(1)

    response = item.delete()

    response.should.equal(True)

    table.count().should.equal(0)

    # Deletes are idempotent and 'False' here would imply an error condition
    item.delete().should.equal(True)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_delete_item_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.delete_item.when.called_with(
        table_name="undeclared-table", key={"forum_name": {"S": "LOLCat Forum"}}
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query():
    table = create_table()

    item_data = {
        "forum_name": "the-key",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = Item(table, item_data)
    item.save(overwrite=True)
    table.count().should.equal(1)
    table = Table("messages")

    results = table.query(forum_name__eq="the-key")
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.query.when.called_with(
        table_name="undeclared-table",
        key_conditions={
            "forum_name": {
                "ComparisonOperator": "EQ",
                "AttributeValueList": [{"S": "the-key"}],
            }
        },
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_scan():
    table = create_table()

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item_data["forum_name"] = "the-key"

    item = Item(table, item_data)
    item.save()

    item["forum_name"] = "the-key2"
    item.save(overwrite=True)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User B",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
        "Ids": set([1, 2, 3]),
        "PK": 7,
    }
    item_data["forum_name"] = "the-key3"
    item = Item(table, item_data)
    item.save()

    results = table.scan()
    sum(1 for _ in results).should.equal(3)

    results = table.scan(SentBy__eq="User B")
    sum(1 for _ in results).should.equal(1)

    results = table.scan(Body__beginswith="http")
    sum(1 for _ in results).should.equal(3)

    results = table.scan(Ids__null=False)
    sum(1 for _ in results).should.equal(1)

    results = table.scan(Ids__null=True)
    sum(1 for _ in results).should.equal(2)

    results = table.scan(PK__between=[8, 9])
    sum(1 for _ in results).should.equal(0)

    results = table.scan(PK__between=[5, 8])
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_scan_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.scan.when.called_with(
        table_name="undeclared-table",
        scan_filter={
            "SentBy": {
                "AttributeValueList": [{"S": "User B"}],
                "ComparisonOperator": "EQ",
            }
        },
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_write_batch():
    table = create_table()

    with table.batch_write() as batch:
        batch.put_item(
            data={
                "forum_name": "the-key",
                "subject": "123",
                "Body": "http://url_to_lolcat.gif",
                "SentBy": "User A",
                "ReceivedTime": "12/9/2011 11:36:03 PM",
            }
        )
        batch.put_item(
            data={
                "forum_name": "the-key2",
                "subject": "789",
                "Body": "http://url_to_lolcat.gif",
                "SentBy": "User B",
                "ReceivedTime": "12/9/2011 11:36:03 PM",
            }
        )

    table.count().should.equal(2)
    with table.batch_write() as batch:
        batch.delete_item(forum_name="the-key", subject="789")

    table.count().should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_batch_read():
    table = create_table()

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item_data["forum_name"] = "the-key1"
    item = Item(table, item_data)
    item.save()

    item = Item(table, item_data)
    item_data["forum_name"] = "the-key2"
    item.save(overwrite=True)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User B",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
        "Ids": set([1, 2, 3]),
        "PK": 7,
    }
    item = Item(table, item_data)
    item_data["forum_name"] = "another-key"
    item.save(overwrite=True)

    results = table.batch_get(
        keys=[{"forum_name": "the-key1"}, {"forum_name": "another-key"}]
    )

    # Iterate through so that batch_item gets called
    count = len([x for x in results])
    count.should.equal(2)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_get_key_fields():
    table = create_table()
    kf = table.get_key_fields()
    kf[0].should.equal("forum_name")


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_get_missing_item():
    table = create_table()
    table.get_item.when.called_with(forum_name="missing").should.throw(ItemNotFound)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_get_special_item():
    table = Table.create(
        "messages",
        schema=[HashKey("date-joined")],
        throughput={"read": 10, "write": 10},
    )

    data = {"date-joined": 127549192, "SentBy": "User A"}
    table.put_item(data=data)
    returned_item = table.get_item(**{"date-joined": 127549192})
    dict(returned_item).should.equal(data)


@mock_dynamodb2_deprecated
def test_update_item_remove():
    conn = boto.dynamodb2.connect_to_region("us-east-1")
    table = Table.create("messages", schema=[HashKey("username")])

    data = {"username": "steve", "SentBy": "User A", "SentTo": "User B"}
    table.put_item(data=data)
    key_map = {"username": {"S": "steve"}}

    # Then remove the SentBy field
    conn.update_item("messages", key_map, update_expression="REMOVE SentBy, SentTo")

    returned_item = table.get_item(username="steve")
    dict(returned_item).should.equal({"username": "steve"})


@mock_dynamodb2_deprecated
def test_update_item_nested_remove():
    conn = boto.dynamodb2.connect_to_region("us-east-1")
    table = Table.create("messages", schema=[HashKey("username")])

    data = {"username": "steve", "Meta": {"FullName": "Steve Urkel"}}
    table.put_item(data=data)
    key_map = {"username": {"S": "steve"}}

    # Then remove the Meta.FullName field
    conn.update_item("messages", key_map, update_expression="REMOVE Meta.FullName")

    returned_item = table.get_item(username="steve")
    dict(returned_item).should.equal({"username": "steve", "Meta": {}})


@mock_dynamodb2
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


@mock_dynamodb2_deprecated
def test_update_item_set():
    conn = boto.dynamodb2.connect_to_region("us-east-1")
    table = Table.create("messages", schema=[HashKey("username")])

    data = {"username": "steve", "SentBy": "User A"}
    table.put_item(data=data)
    key_map = {"username": {"S": "steve"}}

    conn.update_item(
        "messages",
        key_map,
        update_expression="SET foo=:bar, blah=:baz REMOVE SentBy",
        expression_attribute_values={":bar": {"S": "bar"}, ":baz": {"S": "baz"}},
    )

    returned_item = table.get_item(username="steve")
    dict(returned_item).should.equal({"username": "steve", "foo": "bar", "blah": "baz"})


@mock_dynamodb2_deprecated
def test_failed_overwrite():
    table = Table.create(
        "messages", schema=[HashKey("id")], throughput={"read": 7, "write": 3}
    )

    data1 = {"id": "123", "data": "678"}
    table.put_item(data=data1)

    data2 = {"id": "123", "data": "345"}
    table.put_item(data=data2, overwrite=True)

    data3 = {"id": "123", "data": "812"}
    table.put_item.when.called_with(data=data3).should.throw(
        ConditionalCheckFailedException
    )

    returned_item = table.lookup("123")
    dict(returned_item).should.equal(data2)

    data4 = {"id": "124", "data": 812}
    table.put_item(data=data4)

    returned_item = table.lookup("124")
    dict(returned_item).should.equal(data4)


@mock_dynamodb2_deprecated
def test_conflicting_writes():
    table = Table.create("messages", schema=[HashKey("id")])

    item_data = {"id": "123", "data": "678"}
    item1 = Item(table, item_data)
    item2 = Item(table, item_data)
    item1.save()

    item1["data"] = "579"
    item2["data"] = "912"

    item1.save()
    item2.save.when.called_with().should.throw(ConditionalCheckFailedException)


"""
boto3
"""


@mock_dynamodb2
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

    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    return dynamodb.Table("users")


@mock_dynamodb2
def test_boto3_conditions():
    table = _create_user_table()

    table.put_item(Item={"username": "johndoe"})
    table.put_item(Item={"username": "janedoe"})

    response = table.query(KeyConditionExpression=Key("username").eq("johndoe"))
    response["Count"].should.equal(1)
    response["Items"].should.have.length_of(1)
    response["Items"][0].should.equal({"username": "johndoe"})


@mock_dynamodb2
def test_boto3_put_item_conditions_pass():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"foo": {"ComparisonOperator": "EQ", "AttributeValueList": ["bar"]}},
    )
    final_item = table.get_item(Key={"username": "johndoe"})
    assert dict(final_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb2
def test_boto3_put_item_conditions_pass_because_expect_not_exists_by_compare_to_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"whatever": {"ComparisonOperator": "NULL"}},
    )
    final_item = table.get_item(Key={"username": "johndoe"})
    assert dict(final_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb2
def test_boto3_put_item_conditions_pass_because_expect_exists_by_compare_to_not_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"foo": {"ComparisonOperator": "NOT_NULL"}},
    )
    final_item = table.get_item(Key={"username": "johndoe"})
    assert dict(final_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb2
def test_boto3_put_item_conditions_fail():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item.when.called_with(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"foo": {"ComparisonOperator": "NE", "AttributeValueList": ["bar"]}},
    ).should.throw(botocore.client.ClientError)


@mock_dynamodb2
def test_boto3_update_item_conditions_fail():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "baz"})
    table.update_item.when.called_with(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:bar",
        Expected={"foo": {"Value": "bar"}},
        ExpressionAttributeValues={":bar": "bar"},
    ).should.throw(botocore.client.ClientError)


@mock_dynamodb2
def test_boto3_update_item_conditions_fail_because_expect_not_exists():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "baz"})
    table.update_item.when.called_with(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:bar",
        Expected={"foo": {"Exists": False}},
        ExpressionAttributeValues={":bar": "bar"},
    ).should.throw(botocore.client.ClientError)


@mock_dynamodb2
def test_boto3_update_item_conditions_fail_because_expect_not_exists_by_compare_to_null():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "baz"})
    table.update_item.when.called_with(
        Key={"username": "johndoe"},
        UpdateExpression="SET foo=:bar",
        Expected={"foo": {"ComparisonOperator": "NULL"}},
        ExpressionAttributeValues={":bar": "bar"},
    ).should.throw(botocore.client.ClientError)


@mock_dynamodb2
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


@mock_dynamodb2
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


@mock_dynamodb2
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


@mock_dynamodb2
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


@mock_dynamodb2
def test_boto3_update_settype_item_with_conditions():
    class OrderedSet(set):
        """A set with predictable iteration order"""

        def __init__(self, values):
            super(OrderedSet, self).__init__(values)
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


@mock_dynamodb2
def test_boto3_put_item_conditions_pass():
    table = _create_user_table()
    table.put_item(Item={"username": "johndoe", "foo": "bar"})
    table.put_item(
        Item={"username": "johndoe", "foo": "baz"},
        Expected={"foo": {"ComparisonOperator": "EQ", "AttributeValueList": ["bar"]}},
    )
    returned_item = table.get_item(Key={"username": "johndoe"})
    assert dict(returned_item)["Item"]["foo"].should.equal("baz")


@mock_dynamodb2
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


@mock_dynamodb2
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
