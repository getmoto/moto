from unittest.mock import patch

import boto3
import pytest
from boto3.dynamodb.conditions import Attr, Key

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID
from moto.dynamodb import dynamodb_backends


@pytest.mark.parametrize("key_type, key", [("S", "target"), ("N", 7), ("B", b"target")])
@pytest.mark.parametrize("range_key", [False, True])
@mock_aws
@pytest.mark.requires_clean_slate
def test_query_reads_only_requested_partition(key_type, key, range_key):
    if settings.TEST_SERVER_MODE:
        pytest.skip("Can't access backend directly in server mode")
    schema = [{"AttributeName": "pk", "KeyType": "HASH"}]
    attributes = [{"AttributeName": "pk", "AttributeType": key_type}]
    if range_key:
        schema.append({"AttributeName": "sk", "KeyType": "RANGE"})
        attributes.append({"AttributeName": "sk", "AttributeType": "N"})
    table = boto3.resource("dynamodb", region_name="us-east-1").create_table(
        TableName="query-partition",
        KeySchema=schema,
        AttributeDefinitions=attributes,
        BillingMode="PAY_PER_REQUEST",
    )
    for number in range(20):
        other_key = {
            "S": f"other-{number}",
            "N": number + 100,
            "B": f"other-{number}".encode(),
        }[key_type]
        item = {"pk": other_key}
        if range_key:
            item["sk"] = number
        table.put_item(Item=item)
    expected = []
    for number in [3, 1, 2] if range_key else [1]:
        item = {"pk": key, "value": number}
        if range_key:
            item["sk"] = number
        table.put_item(Item=item)
        expected.append(item)
    expected.sort(key=lambda item: item["value"])
    backend_table = dynamodb_backends[DEFAULT_ACCOUNT_ID]["us-east-1"].tables[
        table.name
    ]
    with patch.object(
        backend_table, "all_items", wraps=backend_table.all_items
    ) as all_items:
        result = table.query(KeyConditionExpression=Key("pk").eq(key))
        assert result["Items"] == expected
        assert result["ScannedCount"] == len(expected)
        if range_key:
            page = table.query(
                KeyConditionExpression=Key("pk").eq(key),
                ScanIndexForward=False,
                Limit=1,
            )
            assert page["Items"] == expected[-1:]
            assert page["LastEvaluatedKey"] == {"pk": key, "sk": 3}
            following = table.query(
                KeyConditionExpression=Key("pk").eq(key),
                ScanIndexForward=False,
                ExclusiveStartKey=page["LastEvaluatedKey"],
                FilterExpression=Attr("value").gt(1),
                ProjectionExpression="sk",
            )
            assert following["Items"] == [{"sk": 2}]
            assert following["ScannedCount"] == 2
            result = table.query(
                KeyConditionExpression=Key("pk").eq(key) & Key("sk").between(1, 2)
            )
            assert result["Items"] == expected[:2]
        all_items.assert_not_called()


@pytest.mark.parametrize("range_key", [False, True])
@mock_aws
@pytest.mark.requires_clean_slate
def test_query_missing_partition_does_not_create_it(range_key):
    if settings.TEST_SERVER_MODE:
        pytest.skip("Can't access backend directly in server mode")
    schema = [{"AttributeName": "pk", "KeyType": "HASH"}]
    attributes = [{"AttributeName": "pk", "AttributeType": "S"}]
    if range_key:
        schema.append({"AttributeName": "sk", "KeyType": "RANGE"})
        attributes.append({"AttributeName": "sk", "AttributeType": "S"})
    table = boto3.resource("dynamodb", region_name="us-east-1").create_table(
        TableName="missing-partition",
        KeySchema=schema,
        AttributeDefinitions=attributes,
        BillingMode="PAY_PER_REQUEST",
    )
    backend_table = dynamodb_backends[DEFAULT_ACCOUNT_ID]["us-east-1"].tables[
        table.name
    ]
    with patch.object(
        backend_table, "all_items", wraps=backend_table.all_items
    ) as all_items:
        result = table.query(KeyConditionExpression=Key("pk").eq("missing"))
        assert result["Items"] == []
        assert result["Count"] == result["ScannedCount"] == 0
        assert "LastEvaluatedKey" not in result
        assert not backend_table.items
        all_items.assert_not_called()
