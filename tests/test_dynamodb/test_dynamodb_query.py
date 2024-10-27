from decimal import Decimal

import boto3
import pytest
from boto3.dynamodb.conditions import Attr, Key

from moto import mock_aws

from . import dynamodb_aws_verified


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True, numeric_gsi_range=True)
def test_query_gsi_range_comparison(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    table.put_item(
        Item={"pk": "the-key", "sk": "123", "gsi_pk": "johndoe", "gsi_sk": 3}
    )
    table.put_item(
        Item={"pk": "the-key", "sk": "456", "gsi_pk": "johndoe", "gsi_sk": 1}
    )
    table.put_item(
        Item={"pk": "the-key", "sk": "789", "gsi_pk": "johndoe", "gsi_sk": 2}
    )
    table.put_item(
        Item={"pk": "the-key", "sk": "159", "gsi_pk": "janedoe", "gsi_sk": 2}
    )
    table.put_item(
        Item={"pk": "the-key", "sk": "601", "gsi_pk": "janedoe", "gsi_sk": 5}
    )

    # Test a query returning all johndoe items
    results = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("johndoe") & Key("gsi_sk").gt(0),
        ScanIndexForward=True,
        IndexName="test_gsi",
    )
    assert results["ScannedCount"] == 3
    assert [r["sk"] for r in results["Items"]] == ["456", "789", "123"]

    # Return all johndoe items again, but in reverse
    results = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("johndoe") & Key("gsi_sk").gt(0),
        ScanIndexForward=False,
        IndexName="test_gsi",
    )
    assert [r["sk"] for r in results["Items"]] == ["123", "789", "456"]

    # Filter the creation to only return some of the results
    # And reverse order of hash + range key
    results = table.query(
        KeyConditionExpression=Key("gsi_sk").gt(1) & Key("gsi_pk").eq("johndoe"),
        IndexName="test_gsi",
    )
    assert results["Count"] == 2
    assert [r["gsi_sk"] for r in results["Items"]] == [Decimal("2"), Decimal("3")]

    # Filter to return no results
    results = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("janedoe") & Key("gsi_sk").gt(9),
        IndexName="test_gsi",
    )
    assert results["Count"] == 0

    results = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("janedoe") & Key("gsi_sk").eq(5),
        IndexName="test_gsi",
    )
    assert results["Count"] == 1

    # Test range key sorting
    results = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("johndoe") & Key("gsi_sk").gt(0),
        IndexName="test_gsi",
    )
    expected = [Decimal("1"), Decimal("2"), Decimal("3")]
    assert [r["gsi_sk"] for r in results["Items"]] == expected


@mock_aws
def test_key_condition_expressions():
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
    table.put_item(Item={"forum_name": "the-key", "subject": "456"})
    table.put_item(Item={"forum_name": "the-key", "subject": "789"})

    # Test a query returning all items
    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key") & Key("subject").gt("1"),
        ScanIndexForward=True,
    )
    expected = ["123", "456", "789"]
    for index, item in enumerate(results["Items"]):
        assert item["subject"] == expected[index]

    # Return all items again, but in reverse
    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key") & Key("subject").gt("1"),
        ScanIndexForward=False,
    )
    for index, item in enumerate(reversed(results["Items"])):
        assert item["subject"] == expected[index]

    # Filter the subjects to only return some of the results
    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key")
        & Key("subject").gt("234"),
        ConsistentRead=True,
    )
    assert results["Count"] == 2

    # Filter to return no results
    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key")
        & Key("subject").gt("9999")
    )
    assert results["Count"] == 0

    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key")
        & Key("subject").begins_with("12")
    )
    assert results["Count"] == 1

    results = table.query(
        KeyConditionExpression=Key("subject").begins_with("7")
        & Key("forum_name").eq("the-key")
    )
    assert results["Count"] == 1

    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key")
        & Key("subject").between("567", "890")
    )
    assert results["Count"] == 1


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True)
def test_query_pagination(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}"})

    for i in range(9, 6, -1):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}"})

    for i in range(3):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}"})

    page1 = table.query(KeyConditionExpression=Key("pk").eq("the-key"), Limit=6)
    assert page1["Count"] == 6
    assert page1["ScannedCount"] == 6
    assert len(page1["Items"]) == 6
    assert [i["sk"] for i in page1["Items"]] == ["0", "1", "2", "3", "4", "5"]

    page2 = table.query(
        KeyConditionExpression=Key("pk").eq("the-key"),
        Limit=6,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 4
    assert page2["ScannedCount"] == 4
    assert len(page2["Items"]) == 4
    assert "LastEvaluatedKey" not in page2
    assert [i["sk"] for i in page2["Items"]] == ["6", "7", "8", "9"]

    results = page1["Items"] + page2["Items"]
    subjects = set([int(r["sk"]) for r in results])
    assert subjects == set(range(10))


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_gsi=True)
def test_query_gsi_pagination(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(Item={"pk": f"pk{i}", "gsi_pk": "a"})

    for i in range(11, 6, -1):
        table.put_item(Item={"pk": f"pk{i}", "gsi_pk": "b"})

    for i in range(3):
        table.put_item(Item={"pk": f"pk{i}", "gsi_pk": "c"})

    page1 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("b"),
        IndexName="test_gsi",
        Limit=2,
    )
    p1_items = [i["pk"] for i in page1["Items"]]
    assert len(p1_items) == 2

    page2 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("b"),
        IndexName="test_gsi",
        Limit=2,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    p2_items = [i["pk"] for i in page2["Items"]]
    assert len(p2_items) == 2

    page3 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("b"),
        IndexName="test_gsi",
        Limit=2,
        ExclusiveStartKey=page2["LastEvaluatedKey"],
    )
    p3_items = [i["pk"] for i in page3["Items"]]
    assert len(p3_items) == 1

    assert sorted(set(p1_items + p2_items + p3_items)) == [
        "pk10",
        "pk11",
        "pk7",
        "pk8",
        "pk9",
    ]


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True, add_gsi=True)
def test_query_gsi_pagination_with_string_range(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "johndoe"})

    for i in range(9, 6, -1):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "johndoe"})

    for i in range(3):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "johndoe"})

    page1 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("johndoe"),
        IndexName="test_gsi",
        Limit=6,
    )
    assert page1["Count"] == 6
    assert page1["ScannedCount"] == 6
    assert len(page1["Items"]) == 6

    page2 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("johndoe"),
        IndexName="test_gsi",
        Limit=6,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 4
    assert page2["ScannedCount"] == 4
    assert len(page2["Items"]) == 4
    assert "LastEvaluatedKey" not in page2

    results = page1["Items"] + page2["Items"]
    subjects = set([int(r["sk"]) for r in results])
    assert subjects == set(range(10))


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True, add_gsi_range=True)
def test_query_gsi_pagination_with_string_gsi_range(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(
            Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"}
        )

    for i in range(9, 6, -1):
        table.put_item(
            Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"}
        )

    for i in range(3):
        table.put_item(
            Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"}
        )

    page1 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("john"),
        IndexName="test_gsi",
        Limit=6,
    )
    assert page1["Count"] == 6
    assert page1["ScannedCount"] == 6
    assert len(page1["Items"]) == 6

    page2 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("john"),
        IndexName="test_gsi",
        Limit=6,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 4
    assert page2["ScannedCount"] == 4
    assert len(page2["Items"]) == 4
    assert "LastEvaluatedKey" not in page2

    results = page1["Items"] + page2["Items"]
    subjects = set([int(r["sk"]) for r in results])
    assert subjects == set(range(10))


@mock_aws
def test_query_gsi_pagination_with_opposite_pk_order():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "gsi_hash", "AttributeType": "S"},
            {"AttributeName": "gsi_sort", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "gsi",
                "KeySchema": [
                    {"AttributeName": "gsi_hash", "KeyType": "HASH"},
                    {"AttributeName": "gsi_sort", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    table = dynamodb.Table("users")

    table.put_item(Item={"pk": "b", "gsi_hash": "a", "gsi_sort": "a"})
    table.put_item(Item={"pk": "a", "gsi_hash": "a", "gsi_sort": "b"})

    page1 = table.query(
        KeyConditionExpression=Key("gsi_hash").eq("a"),
        IndexName="gsi",
        Limit=1,
    )
    assert page1["Count"] == 1
    assert page1["ScannedCount"] == 1
    assert len(page1["Items"]) == 1

    page2 = table.query(
        KeyConditionExpression=Key("gsi_hash").eq("a"),
        IndexName="gsi",
        Limit=1,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 1
    assert page2["ScannedCount"] == 1
    assert len(page2["Items"]) == 1
    assert "LastEvaluatedKey" not in page2

    results = page1["Items"] + page2["Items"]
    subjects = [(r["pk"]) for r in results]
    assert subjects == ["b", "a"]


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True, add_gsi_range=True)
def test_query_gsi_pagination_with_string_gsi_range_and_empty_gsi_pk(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(
            Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"}
        )

    for i in range(9, 6, -1):
        table.put_item(
            Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"}
        )

    for i in range(3):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "gsi_sk": "jane"})

    page1 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("john"),
        IndexName="test_gsi",
        Limit=6,
    )
    assert page1["Count"] == 6

    page2 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("john"),
        IndexName="test_gsi",
        Limit=6,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 1
    assert "LastEvaluatedKey" not in page2

    results = page1["Items"] + page2["Items"]
    assert set([r["sk"] for r in results]) == {"3", "4", "5", "6", "7", "8", "9"}


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True, add_gsi_range=True)
def test_query_gsi_pagination_with_string_gsi_range_and_empty_gsi_sk(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "john"})

    for i in range(9, 6, -1):
        table.put_item(
            Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"}
        )

    for i in range(3):
        table.put_item(
            Item={"pk": "the-key", "sk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"}
        )

    page1 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("john"),
        IndexName="test_gsi",
        Limit=5,
    )
    assert page1["Count"] == 5

    page2 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("john"),
        IndexName="test_gsi",
        Limit=6,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 1
    assert "LastEvaluatedKey" not in page2

    results = page1["Items"] + page2["Items"]
    assert set([r["sk"] for r in results]) == {"0", "1", "2", "7", "8", "9"}


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True, numeric_gsi_range=True)
def test_query_gsi_pagination_with_numeric_range(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(
            Item={
                "pk": "the-key",
                "sk": f"{i}",
                "gsi_pk": "johndoe",
                "gsi_sk": Decimal(f"{i}"),
            }
        )

    for i in range(9, 6, -1):
        table.put_item(
            Item={
                "pk": "the-key",
                "sk": f"{i}",
                "gsi_pk": "johndoe",
                "gsi_sk": Decimal(f"{i}"),
            }
        )

    for i in range(3):
        table.put_item(
            Item={
                "pk": "the-key",
                "sk": f"{i}",
                "gsi_pk": "johndoe",
                "gsi_sk": Decimal(f"{i}"),
            }
        )

    page1 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("johndoe"),
        IndexName="test_gsi",
        Limit=6,
    )
    assert page1["Count"] == 6
    assert page1["ScannedCount"] == 6
    assert len(page1["Items"]) == 6
    assert [i["sk"] for i in page1["Items"]] == ["0", "1", "2", "3", "4", "5"]

    page2 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("johndoe"),
        IndexName="test_gsi",
        Limit=6,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 4
    assert page2["ScannedCount"] == 4
    assert len(page2["Items"]) == 4
    assert "LastEvaluatedKey" not in page2
    assert [i["sk"] for i in page2["Items"]] == ["6", "7", "8", "9"]

    results = page1["Items"] + page2["Items"]
    subjects = set([int(r["sk"]) for r in results])
    assert subjects == set(range(10))


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True, add_lsi=True)
def test_query_lsi_pagination(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "lsi_sk": f"{i}"})
    for i in range(9, 6, -1):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "lsi_sk": f"{i}"})
    for i in range(3):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "lsi_sk": f"{i}"})
    for i in range(15, 20):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}"})
    for i in range(25, 30):
        table.put_item(Item={"pk": "other", "sk": f"{i}"})
    for i in range(35, 40):
        table.put_item(Item={"pk": "other_in_lsi", "sk": f"{i}", "lsi_sk": f"{i}"})

    res = table.query(
        KeyConditionExpression=Key("pk").eq("the-key") & Key("lsi_sk").eq("1"),
        IndexName="test_lsi",
    )
    assert res["Count"] == 1
    assert res["Items"] == [{"lsi_sk": "1", "pk": "the-key", "sk": "1"}]

    res = table.query(
        KeyConditionExpression=Key("pk").eq("the-key") & Key("lsi_sk").eq("2"),
        IndexName="test_lsi",
        ConsistentRead=True,
    )
    assert res["Count"] == 1
    assert res["Items"] == [{"lsi_sk": "2", "pk": "the-key", "sk": "2"}]

    # Verify pagination when getting all items with a specific hash
    page1 = table.query(
        KeyConditionExpression=Key("pk").eq("the-key"),
        IndexName="test_lsi",
        Limit=6,
    )
    assert [i["sk"] for i in page1["Items"]] == ["0", "1", "2", "3", "4", "5"]
    assert page1["LastEvaluatedKey"] == {"pk": "the-key", "sk": "5", "lsi_sk": "5"}

    page2 = table.query(
        KeyConditionExpression=Key("pk").eq("the-key"),
        IndexName="test_lsi",
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert [i["sk"] for i in page2["Items"]] == ["6", "7", "8", "9"]


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True, numeric_lsi_range=True)
def test_query_lsi_pagination_with_numerical_local_range_key(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "lsi_sk": Decimal(f"{i}")})
    for i in range(9, 6, -1):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "lsi_sk": Decimal(f"{i}")})
    for i in range(3):
        table.put_item(Item={"pk": "the-key", "sk": f"{i}", "lsi_sk": Decimal(f"{i}")})

    items = table.query(
        KeyConditionExpression=Key("pk").eq("the-key") & Key("lsi_sk").eq(Decimal("1")),
        IndexName="test_lsi",
    )["Items"]
    items == [{"pk": "the-key", "sk": "1", "lsi_sk": Decimal("1")}]

    # Verify pagination when getting all items with a specific hash
    page1 = table.query(
        KeyConditionExpression=Key("pk").eq("the-key"),
        IndexName="test_lsi",
        Limit=6,
    )
    assert [i["lsi_sk"] for i in page1["Items"]] == [Decimal(i) for i in range(6)]
    assert page1["LastEvaluatedKey"] == {
        "pk": "the-key",
        "sk": "5",
        "lsi_sk": Decimal("5"),
    }

    page2 = table.query(
        KeyConditionExpression=Key("pk").eq("the-key"),
        IndexName="test_lsi",
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert [i["lsi_sk"] for i in page2["Items"]] == [Decimal(i) for i in range(6, 10)]


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_gsi_range=True)
def test_query_gsi_with_range_key(table_name=None):
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    item_with_gsi_pk_and_sk = {
        "pk": {"S": "test1"},
        "gsi_pk": {"S": "key1"},
        "gsi_sk": {"S": "range1"},
    }
    dynamodb.put_item(TableName=table_name, Item=item_with_gsi_pk_and_sk)
    dynamodb.put_item(
        TableName=table_name, Item={"pk": {"S": "test2"}, "gsi_pk": {"S": "key1"}}
    )

    res = dynamodb.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :gsi_hash_key and gsi_sk = :gsi_range_key",
        ExpressionAttributeValues={
            ":gsi_hash_key": {"S": "key1"},
            ":gsi_range_key": {"S": "range1"},
        },
    )
    assert res["Count"] == 1
    assert res["Items"][0] == item_with_gsi_pk_and_sk


@pytest.mark.aws_verified
@dynamodb_aws_verified(numeric_range=True)
def test_sorted_query_with_numerical_sort_key(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    def create_item(price):
        return {"pk": "M", "sk": price}

    table = dynamodb.Table(table_name)
    items = list(map(create_item, [2, 1, 10, 3]))
    for item in items:
        table.put_item(Item=item)

    response = table.query(KeyConditionExpression=Key("pk").eq("M"))

    response_items = response["Items"]
    assert len(items) == len(response_items)
    assert all(isinstance(item["sk"], Decimal) for item in response_items)
    response_prices = [item["sk"] for item in response_items]
    expected_prices = [Decimal(item["sk"]) for item in items]
    expected_prices.sort()
    assert expected_prices == response_prices


@pytest.mark.aws_verified
@dynamodb_aws_verified(numeric_gsi_range=True)
def test_gsi_verify_negative_number_order(table_name=None):
    item1 = {"pk": "pk-1", "gsi_pk": "gsi-k1", "gsi_sk": Decimal("-0.6")}
    item2 = {"pk": "pk-2", "gsi_pk": "gsi-k1", "gsi_sk": Decimal("-0.7")}
    item3 = {"pk": "pk-3", "gsi_pk": "gsi-k1", "gsi_sk": Decimal("0.7")}

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)
    table.put_item(Item=item3)
    table.put_item(Item=item1)
    table.put_item(Item=item2)

    resp = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("gsi-k1"), IndexName="test_gsi"
    )
    # Items should be ordered with the lowest number first
    assert [float(item["gsi_sk"]) for item in resp["Items"]] == [-0.7, -0.6, 0.7]


@mock_aws
class TestFilterExpression:
    def test_query_filter(self):
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
        assert response["ScannedCount"] == 2

        response = table.query(
            KeyConditionExpression=Key("client").eq("client1"),
            FilterExpression=Attr("app").eq("app2"),
        )
        assert response["Count"] == 1
        assert response["ScannedCount"] == 2
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

        # Combine Limit + Scan
        response = table.query(
            KeyConditionExpression=Key("client").eq("client1"),
            Limit=1,
            ScanIndexForward=False,
        )
        assert response["Count"] == 1
        assert response["ScannedCount"] == 1
        assert response["Items"][0]["app"] == "app2"

        response = table.query(
            KeyConditionExpression=Key("client").eq("client1"),
            Limit=1,
            ScanIndexForward=True,
        )
        assert response["Count"] == 1
        assert response["ScannedCount"] == 1
        assert response["Items"][0]["app"] == "app1"

    def test_query_filter_overlapping_expression_prefixes(self):
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


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=False, add_gsi_range=True)
def test_query_gsi_pagination_with_string_gsi_range_no_sk(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(Item={"pk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"})

    for i in range(9, 6, -1):
        table.put_item(Item={"pk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"})

    for i in range(3):
        table.put_item(Item={"pk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"})

    page1 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("john"),
        IndexName="test_gsi",
        Limit=6,
    )
    assert page1["Count"] == 6
    assert page1["ScannedCount"] == 6
    assert len(page1["Items"]) == 6

    page2 = table.query(
        KeyConditionExpression=Key("gsi_pk").eq("john"),
        IndexName="test_gsi",
        Limit=6,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 4
    assert page2["ScannedCount"] == 4
    assert len(page2["Items"]) == 4
    assert "LastEvaluatedKey" not in page2

    results = page1["Items"] + page2["Items"]
    subjects = set([int(r["pk"]) for r in results])
    assert subjects == set(range(10))
