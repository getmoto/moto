from decimal import Decimal

import boto3
import pytest

from . import dynamodb_aws_verified


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_update_different_map_elements_in_single_request(table_name=None):
    # https://github.com/getmoto/moto/issues/5552
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    record = {
        "pk": "example_id",
        "d": {"hello": "h", "world": "w"},
    }
    table = dynamodb.Table(table_name)
    table.put_item(Item=record)
    updated = table.update_item(
        Key={"pk": "example_id"},
        UpdateExpression="set d.hello = :h, d.world = :w",
        ExpressionAttributeValues={":h": "H", ":w": "W"},
        ReturnValues="ALL_NEW",
    )
    assert updated["Attributes"] == {
        "pk": "example_id",
        "d": {"hello": "H", "world": "W"},
    }

    # Use UpdateExpression that contains a new-line
    # https://github.com/getmoto/moto/issues/7127
    table.update_item(
        Key={"pk": "example_id"},
        UpdateExpression=(
            """
            ADD 
              MyTotalCount :MyCount
            """
        ),
        ExpressionAttributeValues={":MyCount": 5},
    )
    assert table.get_item(Key={"pk": "example_id"})["Item"]["MyTotalCount"] == 5


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_update_item_add_float(table_name=None):
    table = boto3.resource("dynamodb", "us-east-1").Table(table_name)

    # DECIMAL - DECIMAL
    table.put_item(Item={"pk": "foo", "amount": Decimal(100), "nr": 5})
    table.update_item(
        Key={"pk": "foo"},
        UpdateExpression="ADD amount :delta",
        ExpressionAttributeValues={":delta": -Decimal("88.3")},
    )
    assert table.scan()["Items"][0]["amount"] == Decimal("11.7")

    # DECIMAL + DECIMAL
    table.update_item(
        Key={"pk": "foo"},
        UpdateExpression="ADD amount :delta",
        ExpressionAttributeValues={":delta": Decimal("25.41")},
    )
    assert table.scan()["Items"][0]["amount"] == Decimal("37.11")

    # DECIMAL + INT
    table.update_item(
        Key={"pk": "foo"},
        UpdateExpression="ADD amount :delta",
        ExpressionAttributeValues={":delta": 6},
    )
    assert table.scan()["Items"][0]["amount"] == Decimal("43.11")

    # INT + INT
    table.update_item(
        Key={"pk": "foo"},
        UpdateExpression="ADD nr :delta",
        ExpressionAttributeValues={":delta": 1},
    )
    assert table.scan()["Items"][0]["nr"] == Decimal("6")

    # INT + DECIMAL
    table.update_item(
        Key={"pk": "foo"},
        UpdateExpression="ADD nr :delta",
        ExpressionAttributeValues={":delta": Decimal("25.41")},
    )
    assert table.scan()["Items"][0]["nr"] == Decimal("31.41")
