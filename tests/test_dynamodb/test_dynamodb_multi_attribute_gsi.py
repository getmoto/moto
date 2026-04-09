"""
Tests for multi-attribute GSI key support in DynamoDB.

DynamoDB announced support for multi-attribute composite keys in GSIs in November 2025.
This allows up to 4 attributes each for partition (HASH) and sort (RANGE) keys.

Key semantics:
- ALL hash key attributes must use equality (=)
- Sort keys must be specified left-to-right (cannot skip)
- Only the LAST sort key in your query can use range operators (<, >, BETWEEN, begins_with)
- Earlier sort keys in your query must use equality (=)
- You don't have to specify all range keys - partial prefix is allowed

The decorator `dynamodb_aws_verified(add_multi_attribute_gsi=True)` creates a table with:
- Table key: pk (HASH, S)
- GSI "test_gsi": gsi_pk (HASH, S), gsi_sk (RANGE, S), gsi_sk2 (RANGE, N)
"""

import boto3
import pytest
from botocore.exceptions import ClientError

from tests.test_dynamodb import dynamodb_aws_verified


def _insert_test_items(table_name: str):
    """Insert test items using the decorator's attribute names."""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)
    items = [
        {"pk": "1", "gsi_pk": "pk1", "gsi_sk": "skA", "gsi_sk2": 100},
        {"pk": "2", "gsi_pk": "pk1", "gsi_sk": "skA", "gsi_sk2": 200},
        {"pk": "3", "gsi_pk": "pk1", "gsi_sk": "skA", "gsi_sk2": 300},
        {"pk": "4", "gsi_pk": "pk1", "gsi_sk": "skB", "gsi_sk2": 150},
        {"pk": "5", "gsi_pk": "pk2", "gsi_sk": "skA", "gsi_sk2": 250},
    ]
    for item in items:
        table.put_item(Item=item)


# === Table creation ===


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_create_gsi_with_multi_range_keys(table_name=None):
    """Verify GSI with multiple range keys can be created and described."""
    client = boto3.client("dynamodb", region_name="us-east-1")
    desc = client.describe_table(TableName=table_name)
    gsi = desc["Table"]["GlobalSecondaryIndexes"][0]

    assert gsi["IndexName"] == "test_gsi"
    assert len(gsi["KeySchema"]) == 3
    assert gsi["KeySchema"][0] == {"AttributeName": "gsi_pk", "KeyType": "HASH"}
    assert gsi["KeySchema"][1] == {"AttributeName": "gsi_sk", "KeyType": "RANGE"}
    assert gsi["KeySchema"][2] == {"AttributeName": "gsi_sk2", "KeyType": "RANGE"}


# === Query tests ===


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_query_hash_only(table_name=None):
    """Query with just hash key returns all matching items."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk",
        ExpressionAttributeValues={":pk": {"S": "pk1"}},
    )

    assert result["Count"] == 4


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_query_partial_range_equality(table_name=None):
    """Query with hash + first range key (equality) filters correctly."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk AND gsi_sk = :sk",
        ExpressionAttributeValues={
            ":pk": {"S": "pk1"},
            ":sk": {"S": "skA"},
        },
    )

    assert result["Count"] == 3
    for item in result["Items"]:
        assert item["gsi_sk"]["S"] == "skA"


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_query_partial_range_comparison(table_name=None):
    """Query with range operator on first range key (valid - last in query)."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk AND gsi_sk > :sk",
        ExpressionAttributeValues={
            ":pk": {"S": "pk1"},
            ":sk": {"S": "skA"},
        },
    )

    # Should only return skB (which is > skA lexicographically)
    assert result["Count"] == 1
    assert result["Items"][0]["gsi_sk"]["S"] == "skB"


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_query_full_range_equality(table_name=None):
    """Query with all range keys using equality."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk AND gsi_sk = :sk AND gsi_sk2 = :sk2",
        ExpressionAttributeValues={
            ":pk": {"S": "pk1"},
            ":sk": {"S": "skA"},
            ":sk2": {"N": "200"},
        },
    )

    assert result["Count"] == 1
    assert result["Items"][0]["gsi_sk2"]["N"] == "200"


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_query_full_range_comparison(table_name=None):
    """Query with range operator on last range key."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk AND gsi_sk = :sk AND gsi_sk2 > :sk2",
        ExpressionAttributeValues={
            ":pk": {"S": "pk1"},
            ":sk": {"S": "skA"},
            ":sk2": {"N": "100"},
        },
    )

    # Should return items with gsi_sk2 > 100 (i.e., 200 and 300)
    assert result["Count"] == 2
    values = sorted([int(item["gsi_sk2"]["N"]) for item in result["Items"]])
    assert values == [200, 300]


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_query_between_last_key(table_name=None):
    """BETWEEN operator on last range key in query."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk AND gsi_sk = :sk AND gsi_sk2 BETWEEN :lo AND :hi",
        ExpressionAttributeValues={
            ":pk": {"S": "pk1"},
            ":sk": {"S": "skA"},
            ":lo": {"N": "150"},
            ":hi": {"N": "250"},
        },
    )

    # Should return item with gsi_sk2 = 200
    assert result["Count"] == 1
    assert result["Items"][0]["gsi_sk2"]["N"] == "200"


# === Error tests ===


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_query_error_skip_range_key(table_name=None):
    """Error when skipping a range key."""
    client = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.query(
            TableName=table_name,
            IndexName="test_gsi",
            KeyConditionExpression="gsi_pk = :pk AND gsi_sk2 > :sk2",
            ExpressionAttributeValues={
                ":pk": {"S": "pk1"},
                ":sk2": {"N": "100"},
            },
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "gsi_sk" in err["Message"]


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_query_error_range_on_non_last_in_query(table_name=None):
    """Error when range operator used on non-last key in query."""
    client = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.query(
            TableName=table_name,
            IndexName="test_gsi",
            KeyConditionExpression="gsi_pk = :pk AND gsi_sk > :sk AND gsi_sk2 = :sk2",
            ExpressionAttributeValues={
                ":pk": {"S": "pk1"},
                ":sk": {"S": "skA"},
                ":sk2": {"N": "100"},
            },
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


# === Sorting tests ===


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_sorting_by_composite_key(table_name=None):
    """Items are sorted by composite (gsi_sk, gsi_sk2) key."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk",
        ExpressionAttributeValues={":pk": {"S": "pk1"}},
        ScanIndexForward=True,
    )

    # Should be sorted by (gsi_sk, gsi_sk2)
    # skA comes before skB
    # Within skA: 100, 200, 300
    items = result["Items"]
    assert items[0]["gsi_sk"]["S"] == "skA"
    assert items[0]["gsi_sk2"]["N"] == "100"
    assert items[1]["gsi_sk"]["S"] == "skA"
    assert items[1]["gsi_sk2"]["N"] == "200"
    assert items[2]["gsi_sk"]["S"] == "skA"
    assert items[2]["gsi_sk2"]["N"] == "300"
    assert items[3]["gsi_sk"]["S"] == "skB"


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_sorting_by_second_range_key_not_pk(table_name=None):
    """Verify sorting uses second range key (gsi_sk2), not pk.

    This test ensures items are sorted by the composite range key
    even when pk values would produce a different order.
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    # Insert items where pk order differs from gsi_sk2 order
    # pk=10 has gsi_sk2=300 (should be last)
    # pk=20 has gsi_sk2=100 (should be first)
    # pk=30 has gsi_sk2=200 (should be middle)
    table.put_item(Item={"pk": "10", "gsi_pk": "pk1", "gsi_sk": "skA", "gsi_sk2": 300})
    table.put_item(Item={"pk": "20", "gsi_pk": "pk1", "gsi_sk": "skA", "gsi_sk2": 100})
    table.put_item(Item={"pk": "30", "gsi_pk": "pk1", "gsi_sk": "skA", "gsi_sk2": 200})

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk",
        ExpressionAttributeValues={":pk": {"S": "pk1"}},
        ScanIndexForward=True,
    )

    # Should be sorted by gsi_sk2: 100, 200, 300
    # NOT by pk: 10, 20, 30
    items = result["Items"]
    assert items[0]["gsi_sk2"]["N"] == "100"
    assert items[0]["pk"]["S"] == "20"
    assert items[1]["gsi_sk2"]["N"] == "200"
    assert items[1]["pk"]["S"] == "30"
    assert items[2]["gsi_sk2"]["N"] == "300"
    assert items[2]["pk"]["S"] == "10"


# === KeyConditions tests ===


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_key_conditions_hash_only(table_name=None):
    """KeyConditions with hash key only works on multi-attribute GSI."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditions={
            "gsi_pk": {
                "ComparisonOperator": "EQ",
                "AttributeValueList": [{"S": "pk1"}],
            },
        },
    )

    assert result["Count"] == 4


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_key_conditions_with_range_keys(table_name=None):
    """KeyConditions with hash + range keys works on multi-attribute GSI."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditions={
            "gsi_pk": {
                "ComparisonOperator": "EQ",
                "AttributeValueList": [{"S": "pk1"}],
            },
            "gsi_sk": {
                "ComparisonOperator": "EQ",
                "AttributeValueList": [{"S": "skA"}],
            },
            "gsi_sk2": {
                "ComparisonOperator": "GT",
                "AttributeValueList": [{"N": "100"}],
            },
        },
    )

    assert result["Count"] == 2
    values = sorted([int(item["gsi_sk2"]["N"]) for item in result["Items"]])
    assert values == [200, 300]


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_key_conditions_error_skip_range_key(table_name=None):
    """KeyConditions error when skipping a range key on multi-attribute GSI."""
    client = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.query(
            TableName=table_name,
            IndexName="test_gsi",
            KeyConditions={
                "gsi_pk": {
                    "ComparisonOperator": "EQ",
                    "AttributeValueList": [{"S": "pk1"}],
                },
                "gsi_sk2": {
                    "ComparisonOperator": "GT",
                    "AttributeValueList": [{"N": "100"}],
                },
            },
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "gsi_sk" in err["Message"]


# === Sparse GSI tests ===


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_items_missing_range_key_excluded(table_name=None):
    """Items missing ANY range key attribute should be excluded from GSI.

    DynamoDB only indexes items that have ALL key attributes present.
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    # Complete - should be in GSI
    table.put_item(Item={"pk": "1", "gsi_pk": "pk1", "gsi_sk": "skA", "gsi_sk2": 100})
    # Missing gsi_sk2 - should NOT be in GSI
    table.put_item(Item={"pk": "2", "gsi_pk": "pk1", "gsi_sk": "skB"})
    # Missing gsi_sk - should NOT be in GSI
    table.put_item(Item={"pk": "3", "gsi_pk": "pk1", "gsi_sk2": 200})
    # Complete - should be in GSI
    table.put_item(Item={"pk": "4", "gsi_pk": "pk1", "gsi_sk": "skC", "gsi_sk2": 300})

    client = boto3.client("dynamodb", region_name="us-east-1")
    result = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk",
        ExpressionAttributeValues={":pk": {"S": "pk1"}},
    )

    # Only items with ALL key attributes should be returned
    assert result["Count"] == 2
    pks = {item["pk"]["S"] for item in result["Items"]}
    assert pks == {"1", "4"}


# === Pagination tests ===


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_multi_attribute_gsi=True)
def test_pagination_with_composite_key(table_name=None):
    """Pagination works correctly with composite range key."""
    _insert_test_items(table_name)

    client = boto3.client("dynamodb", region_name="us-east-1")

    # First page
    page1 = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk",
        ExpressionAttributeValues={":pk": {"S": "pk1"}},
        Limit=2,
    )

    assert len(page1["Items"]) == 2
    assert "LastEvaluatedKey" in page1

    # LastEvaluatedKey should include all key attributes
    lek = page1["LastEvaluatedKey"]
    assert "gsi_pk" in lek
    assert "gsi_sk" in lek
    assert "gsi_sk2" in lek

    # Second page
    page2 = client.query(
        TableName=table_name,
        IndexName="test_gsi",
        KeyConditionExpression="gsi_pk = :pk",
        ExpressionAttributeValues={":pk": {"S": "pk1"}},
        Limit=2,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )

    assert len(page2["Items"]) == 2

    # Verify no duplicates
    page1_pks = {item["pk"]["S"] for item in page1["Items"]}
    page2_pks = {item["pk"]["S"] for item in page2["Items"]}
    assert len(page1_pks & page2_pks) == 0
