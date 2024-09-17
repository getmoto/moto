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
def test_delete_last_item_from_map(table_name=None):
    table = boto3.resource("dynamodb", "us-east-1").Table(table_name)

    table.put_item(Item={"pk": "foo", "map": {"sset": {"foo"}}})
    resp = table.update_item(
        Key={"pk": "foo"},
        UpdateExpression="DELETE #map.#sset :s",
        ExpressionAttributeNames={"#map": "map", "#sset": "sset"},
        ExpressionAttributeValues={":s": {"foo"}},
        ReturnValues="ALL_NEW",
    )
    assert {"pk": "foo", "map": {}} == resp["Attributes"]


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
        "ExpressionAttributeValues contains invalid value: One or more parameter values were invalid: An string set  may not be empty"
        in err["Message"]
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
        "ExpressionAttributeValues contains invalid value: One or more parameter values were invalid: An string set  may not be empty"
        in err["Message"]
    )

    assert dynamodb.scan(TableName=table_name)["Items"] == [
        {"pk": {"S": "foo"}, "stringset": {"SS": ["item1"]}}
    ]


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_update_item_with_empty_values(table_name=None):
    dynamodb = boto3.client("dynamodb", "us-east-1")

    dynamodb.put_item(TableName=table_name, Item={"pk": {"S": "foo"}})
    with pytest.raises(ClientError) as exc:
        dynamodb.update_item(
            TableName=table_name,
            Key={"pk": {"S": "foo"}},
            UpdateExpression="SET #d = :s",
            ExpressionAttributeNames={"#d": "d"},
            ExpressionAttributeValues={},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "ExpressionAttributeValues must not be empty"


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_update_item_with_empty_expression(table_name=None):
    dynamodb = boto3.client("dynamodb", "us-east-1")

    dynamodb.put_item(TableName=table_name, Item={"pk": {"S": "foo"}})
    with pytest.raises(ClientError) as exc:
        dynamodb.update_item(
            TableName=table_name,
            Key={"pk": {"S": "foo"}},
            UpdateExpression="",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"] == "Invalid UpdateExpression: The expression can not be empty;"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_update_expression_with_multiple_remove_clauses(table_name=None):
    ddb_client = boto3.client("dynamodb", "us-east-1")
    payload = {
        "pk": {"S": "primary_key"},
        "current_user": {"M": {"name": {"S": "John"}, "surname": {"S": "Doe"}}},
        "user_list": {
            "L": [
                {"M": {"name": {"S": "John"}, "surname": {"S": "Doe"}}},
                {"M": {"name": {"S": "Jane"}, "surname": {"S": "Smith"}}},
            ]
        },
        "some_param": {"NULL": True},
    }
    ddb_client.put_item(TableName=table_name, Item=payload)
    with pytest.raises(ClientError) as exc:
        ddb_client.update_item(
            TableName=table_name,
            Key={"pk": {"S": "primary_key"}},
            UpdateExpression="REMOVE #ulist[0] SET current_user = :current_user REMOVE some_param",
            ExpressionAttributeNames={"#ulist": "user_list"},
            ExpressionAttributeValues={":current_user": {"M": {"name": {"S": "Jane"}}}},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == 'Invalid UpdateExpression: The "REMOVE" section can only be used once in an update expression;'
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_update_expression_remove_list_and_attribute(table_name=None):
    ddb_client = boto3.client("dynamodb", "us-east-1")
    payload = {
        "pk": {"S": "primary_key"},
        "user_list": {
            "L": [
                {"M": {"name": {"S": "John"}, "surname": {"S": "Doe"}}},
                {"M": {"name": {"S": "Jane"}, "surname": {"S": "Smith"}}},
            ]
        },
        "some_param": {"NULL": True},
    }
    ddb_client.put_item(TableName=table_name, Item=payload)
    ddb_client.update_item(
        TableName=table_name,
        Key={"pk": {"S": "primary_key"}},
        UpdateExpression="REMOVE #ulist[0], some_param",
        ExpressionAttributeNames={"#ulist": "user_list"},
    )
    item = ddb_client.get_item(
        TableName=table_name, Key={"pk": {"S": "primary_key"}, "sk": {"S": "sort_key"}}
    )["Item"]
    assert item == {
        "user_list": {"L": [{"M": {"name": {"S": "Jane"}, "surname": {"S": "Smith"}}}]},
        "pk": {"S": "primary_key"},
    }
