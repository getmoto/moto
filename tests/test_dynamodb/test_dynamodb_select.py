import boto3
import pytest
from botocore.exceptions import ClientError

from . import dynamodb_aws_verified


def _read(client, operation, table_name, index_name=None, **kwargs):
    request = {"TableName": table_name, **kwargs}
    if index_name:
        request["IndexName"] = index_name

    if operation == "query":
        key_name = "gsi_pk" if index_name == "test_gsi" else "pk"
        request["KeyConditionExpression"] = f"{key_name} = :key"
        request["ExpressionAttributeValues"] = {":key": {"S": "value"}}
        return client.query(**request)

    return client.scan(**request)


def _validation_error(exc):
    error = exc.value.response["Error"]
    assert error["Code"] == "ValidationException"
    return error["Message"]


def _assert_validation_error(exc, expected_message):
    assert _validation_error(exc) == expected_message


def _assert_all_attributes_rejected_for_gsi(operation, table_name):
    client = boto3.client("dynamodb", region_name="us-east-1")

    response = _read(
        client,
        operation,
        table_name,
        index_name="test_lsi",
        Select="ALL_ATTRIBUTES",
    )
    assert response["Count"] == 0

    response = _read(
        client,
        operation,
        table_name,
        index_name="test_gsi",
        Select="ALL_PROJECTED_ATTRIBUTES",
    )
    assert response["Count"] == 0

    with pytest.raises(ClientError) as exc:
        _read(
            client,
            operation,
            table_name,
            index_name="test_gsi",
            Select="ALL_ATTRIBUTES",
        )

    _assert_validation_error(
        exc,
        "One or more parameter values were invalid: Select type ALL_ATTRIBUTES "
        "is not supported for global secondary index test_gsi because its projection "
        "type is not ALL",
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified(
    add_range=True,
    add_gsi=True,
    gsi_projection_type="KEYS_ONLY",
    add_lsi=True,
    lsi_projection_type="KEYS_ONLY",
)
@pytest.mark.parametrize("operation", ["query", "scan"])
def test_all_attributes_rejected_for_keys_only_gsi(operation, table_name=None):
    _assert_all_attributes_rejected_for_gsi(operation, table_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(
    add_range=True,
    add_gsi=True,
    gsi_projection_type="INCLUDE",
    gsi_non_key_attributes=["projected"],
    add_lsi=True,
    lsi_projection_type="KEYS_ONLY",
)
@pytest.mark.parametrize("operation", ["query", "scan"])
def test_all_attributes_rejected_for_include_gsi(operation, table_name=None):
    _assert_all_attributes_rejected_for_gsi(operation, table_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_gsi=True)
@pytest.mark.parametrize(
    "operation, expected_message",
    [
        (
            "query",
            (
                "1 validation error detected: ALL_PROJECTED_ATTRIBUTES can be used only "
                "when Querying using an IndexName"
            ),
        ),
        (
            "scan",
            "ALL_PROJECTED_ATTRIBUTES can be used only when Querying using an IndexName",
        ),
    ],
)
def test_all_projected_attributes_rejected_for_table(
    operation, expected_message, table_name=None
):
    client = boto3.client("dynamodb", region_name="us-east-1")

    response = _read(
        client,
        operation,
        table_name,
        index_name="test_gsi",
        Select="ALL_PROJECTED_ATTRIBUTES",
    )
    assert response["Count"] == 0

    with pytest.raises(ClientError) as exc:
        _read(client, operation, table_name, Select="ALL_PROJECTED_ATTRIBUTES")

    _assert_validation_error(exc, expected_message)


@pytest.mark.aws_verified
@dynamodb_aws_verified()
@pytest.mark.parametrize(
    "operation, expected_message",
    [
        (
            "query",
            (
                "1 validation error detected: Must specify the AttributesToGet or "
                "ProjectionExpression when choosing to get SPECIFIC_ATTRIBUTES"
            ),
        ),
        (
            "scan",
            (
                "Must specify the AttributesToGet or ProjectionExpression when choosing "
                "to get SPECIFIC_ATTRIBUTES"
            ),
        ),
    ],
)
def test_specific_attributes_requires_attribute_selection(
    operation, expected_message, table_name=None
):
    client = boto3.client("dynamodb", region_name="us-east-1")

    response = _read(
        client,
        operation,
        table_name,
        Select="SPECIFIC_ATTRIBUTES",
        ProjectionExpression="pk",
    )
    assert response["Count"] == 0

    with pytest.raises(ClientError) as exc:
        _read(client, operation, table_name, Select="SPECIFIC_ATTRIBUTES")

    _assert_validation_error(exc, expected_message)


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_gsi=True)
@pytest.mark.parametrize(
    "select, selection_description",
    [
        ("ALL_ATTRIBUTES", "ALL_ATTRIBUTES"),
        ("ALL_PROJECTED_ATTRIBUTES", "ALL_PROJECTED_ATTRIBUTES"),
        ("COUNT", "only the Count"),
    ],
)
@pytest.mark.parametrize(
    "operation, message_prefix",
    [("query", "1 validation error detected: "), ("scan", "")],
)
def test_projection_expression_rejected_for_non_specific_select(
    select, selection_description, operation, message_prefix, table_name=None
):
    client = boto3.client("dynamodb", region_name="us-east-1")

    response = _read(
        client,
        operation,
        table_name,
        index_name="test_gsi",
        Select=select,
    )
    assert response["Count"] == 0

    with pytest.raises(ClientError) as exc:
        _read(
            client,
            operation,
            table_name,
            index_name="test_gsi",
            Select=select,
            ProjectionExpression="gsi_pk",
        )

    _assert_validation_error(
        exc,
        f"{message_prefix}Cannot specify the ProjectionExpression when choosing "
        f"to get {selection_description}",
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_gsi=True)
@pytest.mark.parametrize(
    "operation, message_prefix",
    [("query", "1 validation error detected: "), ("scan", "")],
)
def test_attributes_to_get_rejected_for_non_specific_select(
    operation, message_prefix, table_name=None
):
    client = boto3.client("dynamodb", region_name="us-east-1")
    request = {
        "TableName": table_name,
        "IndexName": "test_gsi",
        "AttributesToGet": ["gsi_pk"],
    }
    if operation == "query":
        request["KeyConditions"] = {
            "gsi_pk": {
                "ComparisonOperator": "EQ",
                "AttributeValueList": [{"S": "value"}],
            }
        }

    response = getattr(client, operation)(Select="SPECIFIC_ATTRIBUTES", **request)
    assert response["Count"] == 0

    for select, selection_description in [
        ("ALL_ATTRIBUTES", "ALL_ATTRIBUTES"),
        ("ALL_PROJECTED_ATTRIBUTES", "ALL_PROJECTED_ATTRIBUTES"),
        ("COUNT", "only the Count"),
    ]:
        with pytest.raises(ClientError) as exc:
            getattr(client, operation)(Select=select, **request)

        _assert_validation_error(
            exc,
            f"{message_prefix}Cannot specify the AttributesToGet when choosing "
            f"to get {selection_description}",
        )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
@pytest.mark.parametrize("operation", ["query", "scan"])
def test_select_values_are_case_sensitive(operation, table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")

    response = _read(client, operation, table_name, Select="COUNT")
    assert response["Count"] == 0
    assert "Items" not in response

    with pytest.raises(ClientError) as exc:
        _read(client, operation, table_name, Select="count")

    _assert_validation_error(
        exc,
        "1 validation error detected: Value 'count' at 'select' failed to satisfy "
        "constraint: Member must satisfy enum value set: [SPECIFIC_ATTRIBUTES, "
        "COUNT, ALL_ATTRIBUTES, ALL_PROJECTED_ATTRIBUTES]",
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_scan_count_omits_items_and_preserves_pagination(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.put_item(TableName=table_name, Item={"pk": {"S": "first"}})
    client.put_item(TableName=table_name, Item={"pk": {"S": "second"}})

    response = client.scan(
        TableName=table_name,
        Select="COUNT",
        Limit=1,
        ConsistentRead=True,
    )

    assert response["Count"] == 1
    assert response["ScannedCount"] == 1
    assert "Items" not in response
    assert "LastEvaluatedKey" in response
