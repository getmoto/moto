from decimal import Decimal

import boto3
import pytest
from botocore.exceptions import ClientError

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


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_delete_non_existing_item(table_name=None):
    table = boto3.resource("dynamodb", "us-east-1").Table(table_name)

    name = "name"
    user_name = "karl"

    # Initial item does not contain users
    initial_item = {"pk": name}
    table.put_item(Item=initial_item)

    # We can remove a (non-existing) user without it failing
    table.update_item(
        Key={"pk": name},
        UpdateExpression="DELETE #users :users",
        ExpressionAttributeValues={":users": {user_name}},
        ExpressionAttributeNames={"#users": "users"},
        ReturnValues="ALL_NEW",
    )
    assert table.get_item(Key={"pk": name})["Item"] == {"pk": "name"}

    # IF the item does exist
    table.update_item(
        Key={"pk": name},
        UpdateExpression="ADD #users :delta",
        ExpressionAttributeNames={"#users": "users"},
        ExpressionAttributeValues={":delta": {user_name}},
    )
    assert table.get_item(Key={"pk": name})["Item"] == {"pk": "name", "users": {"karl"}}

    # We can delete a non-existing item from it
    table.update_item(
        Key={"pk": name},
        UpdateExpression="DELETE #users :users",
        ExpressionAttributeValues={":users": {f"{user_name}2"}},
        ExpressionAttributeNames={"#users": "users"},
        ReturnValues="ALL_NEW",
    )
    assert table.get_item(Key={"pk": name})["Item"] == {"pk": "name", "users": {"karl"}}

    table.update_item(
        Key={"pk": name},
        UpdateExpression="DELETE #users :users",
        ExpressionAttributeValues={":users": {user_name}},
        ExpressionAttributeNames={"#users": "users"},
        ReturnValues="ALL_NEW",
    )
    assert table.get_item(Key={"pk": name})["Item"] == {"pk": "name"}


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_update_item_add_empty_set(table_name=None):
    dynamodb = boto3.client("dynamodb", "us-east-1")

    # Add to non-existing attribute
    dynamodb.put_item(TableName=table_name, Item={"pk": {"S": "foo"}})
    with pytest.raises(ClientError) as exc:
        dynamodb.update_item(
            TableName=table_name,
            Key={"pk": {"S": "foo"}},
            UpdateExpression="ADD stringset :emptySet",
            ExpressionAttributeValues={":emptySet": {"SS": ()}},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "ExpressionAttributeValues contains invalid value: One or more parameter values were invalid: An string set  may not be empty"
    )

    assert dynamodb.scan(TableName=table_name)["Items"] == [{"pk": {"S": "foo"}}]

    # Still not allowed when the attribute exists
    dynamodb.put_item(
        TableName=table_name, Item={"pk": {"S": "foo"}, "stringset": {"SS": ("item1",)}}
    )
    with pytest.raises(ClientError) as exc:
        dynamodb.update_item(
            TableName=table_name,
            Key={"pk": {"S": "foo"}},
            UpdateExpression="ADD stringset :emptySet",
            ExpressionAttributeValues={":emptySet": {"SS": ()}},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "ExpressionAttributeValues contains invalid value: One or more parameter values were invalid: An string set  may not be empty"
    )

    assert dynamodb.scan(TableName=table_name)["Items"] == [
        {"pk": {"S": "foo"}, "stringset": {"SS": ["item1"]}}
    ]
