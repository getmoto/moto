import copy
from decimal import Decimal as dec

import boto3
import pytest
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from moto import mock_aws

from . import dynamodb_aws_verified


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True)
def test_scan_with_unknown_last_evaluated_key(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")

    for i in range(10):
        client.put_item(
            TableName=table_name,
            Item={
                "pk": {"S": "hash_value"},
                "sk": {"S": f"range_value{i}"},
            },
        )

    p1 = client.scan(
        TableName=table_name,
        FilterExpression="#h = :h",
        ExpressionAttributeNames={"#h": "pk"},
        ExpressionAttributeValues={":h": {"S": "hash_value"}},
        Limit=1,
    )
    assert p1["Items"] == [{"pk": {"S": "hash_value"}, "sk": {"S": "range_value0"}}]

    # Using the Exact ExclusiveStartKey provided
    p2 = client.scan(
        TableName=table_name,
        FilterExpression="#h = :h",
        ExpressionAttributeNames={"#h": "pk"},
        ExpressionAttributeValues={":h": {"S": "hash_value"}},
        Limit=1,
        ExclusiveStartKey=p1["LastEvaluatedKey"],
    )
    assert p2["Items"] == [{"pk": {"S": "hash_value"}, "sk": {"S": "range_value1"}}]

    # We can change ExclusiveStartKey
    # It doesn't need to match - it just needs to be >= page1, but < page1
    different_key = copy.copy(p1["LastEvaluatedKey"])
    different_key["sk"]["S"] = different_key["sk"]["S"] + "0"
    p3 = client.scan(
        TableName=table_name,
        FilterExpression="#h = :h",
        ExpressionAttributeNames={"#h": "pk"},
        ExpressionAttributeValues={":h": {"S": "hash_value"}},
        Limit=1,
        ExclusiveStartKey=different_key,
    )
    assert p3["Items"] == [{"pk": {"S": "hash_value"}, "sk": {"S": "range_value1"}}]

    # Sanity check - increasing the sk to something much greater will result in a different outcome
    different_key["sk"]["S"] = "range_value500"
    p4 = client.scan(
        TableName=table_name,
        FilterExpression="#h = :h",
        ExpressionAttributeNames={"#h": "pk"},
        ExpressionAttributeValues={":h": {"S": "hash_value"}},
        Limit=1,
        ExclusiveStartKey=different_key,
    )
    assert p4["Items"] == [{"pk": {"S": "hash_value"}, "sk": {"S": "range_value6"}}]


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True)
def test_scan_with_alternating_hash_keys(table_name=None):
    ddb = boto3.resource("dynamodb", "us-east-1")
    table = ddb.Table(table_name)

    # Insert Data
    data = [dict(pk="A" if i % 2 else "B", sk=str(i)) for i in range(8)]
    with table.batch_writer() as batch:
        for item in data:
            batch.put_item(Item=item)
    # Also add some range keys in reverse, to verify they come back in a natural order
    data = [dict(pk="A", sk=str(i)) for i in range(20, 15, -1)]
    with table.batch_writer() as batch:
        for item in data:
            batch.put_item(Item=item)

    responses = []

    resp = table.scan(Limit=3)
    responses.append(resp["Items"])

    while "LastEvaluatedKey" in resp:
        resp = table.scan(Limit=3, ExclusiveStartKey=resp["LastEvaluatedKey"])
        responses.append(resp["Items"])

    assert len(responses) == 5
    assert responses[0] == [
        {"pk": "A", "sk": "1"},
        {"pk": "A", "sk": "16"},
        {"pk": "A", "sk": "17"},
    ]
    assert responses[1] == [
        {"pk": "A", "sk": "18"},
        {"pk": "A", "sk": "19"},
        {"pk": "A", "sk": "20"},
    ]
    assert responses[2] == [
        {"pk": "A", "sk": "3"},
        {"pk": "A", "sk": "5"},
        {"pk": "A", "sk": "7"},
    ]
    assert responses[3] == [
        {"pk": "B", "sk": "0"},
        {"pk": "B", "sk": "2"},
        {"pk": "B", "sk": "4"},
    ]
    assert responses[4] == [{"pk": "B", "sk": "6"}]


@pytest.mark.aws_verified
@dynamodb_aws_verified(numeric_range=True)
def test_scan_with_numeric_range_key(table_name=None):
    ddb = boto3.resource("dynamodb", "us-east-1")
    table = ddb.Table(table_name)

    # Insert Data
    data = [dict(pk="A" if i % 2 else "B", sk=i) for i in range(8)]
    with table.batch_writer() as batch:
        for item in data:
            batch.put_item(Item=item)
    # Also add some range keys in reverse, to verify they come back in a natural order
    data = [dict(pk="A", sk=i) for i in range(20, 15, -1)]
    with table.batch_writer() as batch:
        for item in data:
            batch.put_item(Item=item)

    responses = []

    resp = table.scan(Limit=3)
    responses.append(resp["Items"])

    while "LastEvaluatedKey" in resp:
        resp = table.scan(Limit=3, ExclusiveStartKey=resp["LastEvaluatedKey"])
        responses.append(resp["Items"])

    assert len(responses) == 5
    assert responses[0] == [
        {"pk": "A", "sk": dec("1")},
        {"pk": "A", "sk": dec("3")},
        {"pk": "A", "sk": dec("5")},
    ]
    assert responses[1] == [
        {"pk": "A", "sk": dec("7")},
        {"pk": "A", "sk": dec("16")},
        {"pk": "A", "sk": dec("17")},
    ]
    assert responses[2] == [
        {"pk": "A", "sk": dec("18")},
        {"pk": "A", "sk": dec("19")},
        {"pk": "A", "sk": dec("20")},
    ]
    assert responses[3] == [
        {"pk": "B", "sk": dec("0")},
        {"pk": "B", "sk": dec("2")},
        {"pk": "B", "sk": dec("4")},
    ]
    assert responses[4] == [{"pk": "B", "sk": dec("6")}]


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_gsi=True)
def test_scan_by_global_index(table_name=None):
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    resource = boto3.resource("dynamodb", region_name="us-east-1")
    table = resource.Table(table_name)

    # Insert Data
    data = [dict(pk=f"A{i}", gsi_pk=f"gsi{i}") for i in range(5)]
    with table.batch_writer() as batch:
        for item in data:
            batch.put_item(Item=item)
    # Also add some range keys in reverse, to verify they come back in a natural order
    data = [dict(pk=f"A{i}", gsi_pk=f"gsi{i}") for i in range(20, 15, -1)]
    with table.batch_writer() as batch:
        for item in data:
            batch.put_item(Item=item)

    res = dynamodb.scan(TableName=table_name)
    assert res["Count"] == 10
    assert len(res["Items"]) == 10

    res = dynamodb.scan(TableName=table_name, ConsistentRead=True)
    assert res["Count"] == 10
    assert len(res["Items"]) == 10

    res = dynamodb.scan(TableName=table_name, IndexName="test_gsi")
    assert res["Count"] == 10

    page1 = dynamodb.scan(TableName=table_name, IndexName="test_gsi", Limit=6)
    assert page1["Count"] == 6
    page1_items = {i["gsi_pk"]["S"] for i in page1["Items"]}

    page2 = dynamodb.scan(
        TableName=table_name,
        IndexName="test_gsi",
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 4
    page2_items = {i["gsi_pk"]["S"] for i in page2["Items"]}

    # AWS does not order items
    # So we can only verify that all items appear at some point
    expected = {
        "gsi0",
        "gsi1",
        "gsi16",
        "gsi17",
        "gsi18",
        "gsi19",
        "gsi2",
        "gsi20",
        "gsi3",
        "gsi4",
    }
    assert page1_items.union(page2_items) == expected


@mock_aws
def test_scan_by_global_and_local_index():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="test",
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
            {"AttributeName": "range_key", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "range_key", "AttributeType": "S"},
            {"AttributeName": "gsi_col", "AttributeType": "S"},
            {"AttributeName": "gsi_range_key", "AttributeType": "S"},
            {"AttributeName": "lsi_range_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [
                    {"AttributeName": "gsi_col", "KeyType": "HASH"},
                    {"AttributeName": "gsi_range_key", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
        LocalSecondaryIndexes=[
            {
                "IndexName": "test_lsi",
                "KeySchema": [
                    {"AttributeName": "id", "KeyType": "HASH"},
                    {"AttributeName": "lsi_range_key", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )

    dynamodb.put_item(
        TableName="test",
        Item={
            "id": {"S": "1"},
            "range_key": {"S": "1"},
            "col1": {"S": "val1"},
            "gsi_col": {"S": "1"},
            "gsi_range_key": {"S": "1"},
            "lsi_range_key": {"S": "1"},
        },
    )

    dynamodb.put_item(
        TableName="test",
        Item={
            "id": {"S": "1"},
            "range_key": {"S": "2"},
            "col1": {"S": "val2"},
            "gsi_col": {"S": "1"},
            "gsi_range_key": {"S": "2"},
            "lsi_range_key": {"S": "2"},
        },
    )

    dynamodb.put_item(
        TableName="test",
        Item={"id": {"S": "3"}, "range_key": {"S": "1"}, "col1": {"S": "val3"}},
    )

    res = dynamodb.scan(TableName="test")
    assert res["Count"] == 3
    assert len(res["Items"]) == 3

    res = dynamodb.scan(TableName="test", Limit=1)
    assert res["Count"] == 1
    assert res["ScannedCount"] == 1

    res = dynamodb.scan(TableName="test", ExclusiveStartKey=res["LastEvaluatedKey"])
    assert res["Count"] == 2
    assert res["ScannedCount"] == 2

    res = dynamodb.scan(TableName="test", IndexName="test_gsi")
    assert res["Count"] == 2
    assert res["ScannedCount"] == 2
    assert len(res["Items"]) == 2

    res = dynamodb.scan(TableName="test", IndexName="test_gsi", Limit=1)
    assert res["Count"] == 1
    assert res["ScannedCount"] == 1
    assert len(res["Items"]) == 1
    last_eval_key = res["LastEvaluatedKey"]
    assert last_eval_key["id"]["S"] == "1"
    assert last_eval_key["gsi_col"]["S"] == "1"
    assert last_eval_key["gsi_range_key"]["S"] == "1"

    res = dynamodb.scan(
        TableName="test", IndexName="test_gsi", ExclusiveStartKey=last_eval_key
    )
    assert res["Count"] == 1
    assert res["ScannedCount"] == 1

    res = dynamodb.scan(TableName="test", IndexName="test_lsi")
    assert res["Count"] == 2
    assert res["ScannedCount"] == 2
    assert len(res["Items"]) == 2

    res = dynamodb.scan(TableName="test", IndexName="test_lsi", ConsistentRead=True)
    assert res["Count"] == 2
    assert res["ScannedCount"] == 2
    assert len(res["Items"]) == 2

    res = dynamodb.scan(TableName="test", IndexName="test_lsi", Limit=1)
    assert res["Count"] == 1
    assert res["ScannedCount"] == 1
    assert len(res["Items"]) == 1
    last_eval_key = res["LastEvaluatedKey"]
    assert last_eval_key["id"]["S"] == "1"
    assert last_eval_key["range_key"]["S"] == "1"
    assert last_eval_key["lsi_range_key"]["S"] == "1"


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=True, add_gsi_range=True)
def test_scan_gsi_pagination_with_string_gsi_range(table_name=None):
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

    page1 = table.scan(IndexName="test_gsi", Limit=6)
    assert page1["Count"] == 6
    assert page1["ScannedCount"] == 6
    assert len(page1["Items"]) == 6

    page2 = table.scan(
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
def test_scan_gsi_pagination_with_string_gsi_range_and_empty_gsi_pk(table_name=None):
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

    page1 = table.scan(IndexName="test_gsi", Limit=6)
    assert page1["Count"] == 6

    page2 = table.scan(
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
def test_scan_gsi_pagination_with_string_gsi_range_and_empty_gsi_sk(table_name=None):
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

    page1 = table.scan(IndexName="test_gsi", Limit=5)
    assert page1["Count"] == 5

    page2 = table.scan(
        IndexName="test_gsi",
        Limit=6,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    assert page2["Count"] == 1
    assert "LastEvaluatedKey" not in page2

    results = page1["Items"] + page2["Items"]
    assert set([r["sk"] for r in results]) == {"0", "1", "2", "7", "8", "9"}


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=False, add_gsi_range=True)
def test_scan_gsi_pagination_with_string_gsi_range_no_sk(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    for i in range(3, 7):
        table.put_item(Item={"pk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"})

    for i in range(9, 6, -1):
        table.put_item(Item={"pk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"})

    for i in range(3):
        table.put_item(Item={"pk": f"{i}", "gsi_pk": "john", "gsi_sk": "jane"})

    page1 = table.scan(IndexName="test_gsi", Limit=6)
    assert page1["Count"] == 6
    assert page1["ScannedCount"] == 6
    assert len(page1["Items"]) == 6

    page2 = table.scan(
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


@mock_aws
class TestFilterExpression:
    def test_scan_filter(self):
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

    def test_scan_filter2(self):
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

    def test_scan_filter3(self):
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
            Item={
                "client": {"S": "client1"},
                "app": {"N": "1"},
                "active": {"BOOL": True},
            },
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

    def test_scan_filter4(self):
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

    def test_filter_should_not_return_non_existing_attributes(self):
        table_name = "my-table"
        item = {"partitionKey": "pk-2", "my-attr": 42}
        # Create table
        res = boto3.resource("dynamodb", region_name="us-east-1")
        res.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "partitionKey", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "partitionKey", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table = res.Table(table_name)
        # Insert items
        table.put_item(Item={"partitionKey": "pk-1"})
        table.put_item(Item=item)
        # Verify a few operations
        # Assert we only find the item that has this attribute
        assert table.scan(FilterExpression=Attr("my-attr").lt(43))["Items"] == [item]
        assert table.scan(FilterExpression=Attr("my-attr").lte(42))["Items"] == [item]
        assert table.scan(FilterExpression=Attr("my-attr").gte(42))["Items"] == [item]
        assert table.scan(FilterExpression=Attr("my-attr").gt(41))["Items"] == [item]
        # Sanity check that we can't find the item if the FE is wrong
        assert table.scan(FilterExpression=Attr("my-attr").gt(43))["Items"] == []

    def test_bad_scan_filter(self):
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
        assert exc.value.response["Error"]["Code"] == "ValidationException"

    def test_scan_with_scanfilter(self):
        table_name = "my-table"
        item = {"partitionKey": "pk-2", "my-attr": 42}
        client = boto3.client("dynamodb", region_name="us-east-1")
        res = boto3.resource("dynamodb", region_name="us-east-1")
        res.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "partitionKey", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "partitionKey", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table = res.Table(table_name)
        table.put_item(Item={"partitionKey": "pk-1"})
        table.put_item(Item=item)

        # ScanFilter: EQ
        # The DynamoDB table-resource sends the AttributeValueList in the wrong format
        # So this operation never finds any data, in Moto or AWS
        table.scan(
            ScanFilter={
                "my-attr": {
                    "AttributeValueList": [{"N": "42"}],
                    "ComparisonOperator": "EQ",
                }
            }
        )

        # ScanFilter: EQ
        # If we use the boto3-client, we do receive the correct data
        items = client.scan(
            TableName=table_name,
            ScanFilter={
                "partitionKey": {
                    "AttributeValueList": [{"S": "pk-1"}],
                    "ComparisonOperator": "EQ",
                }
            },
        )["Items"]
        assert items == [{"partitionKey": {"S": "pk-1"}}]

        # ScanFilter: NONE
        # Note that we can use the table-resource here, because we're not using the AttributeValueList
        items = table.scan(ScanFilter={"my-attr": {"ComparisonOperator": "NULL"}})[
            "Items"
        ]
        assert items == [{"partitionKey": "pk-1"}]
