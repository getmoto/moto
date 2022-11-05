import boto3
import pytest

from moto import mock_iot


@mock_iot
def test_deprecate_undeprecate_thing_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_type_name = "my-type-name"
    client.create_thing_type(
        thingTypeName=thing_type_name,
        thingTypeProperties={"searchableAttributes": ["s1", "s2", "s3"]},
    )

    res = client.describe_thing_type(thingTypeName=thing_type_name)
    res["thingTypeMetadata"]["deprecated"].should.equal(False)
    client.deprecate_thing_type(thingTypeName=thing_type_name, undoDeprecate=False)

    res = client.describe_thing_type(thingTypeName=thing_type_name)
    res["thingTypeMetadata"]["deprecated"].should.equal(True)

    client.deprecate_thing_type(thingTypeName=thing_type_name, undoDeprecate=True)

    res = client.describe_thing_type(thingTypeName=thing_type_name)
    res["thingTypeMetadata"]["deprecated"].should.equal(False)


@mock_iot
def test_deprecate_thing_type_not_exist():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_type_name = "my-type-name"
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.deprecate_thing_type(thingTypeName=thing_type_name, undoDeprecate=False)


@mock_iot
def test_create_thing_with_deprecated_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_type_name = "my-type-name"
    client.create_thing_type(
        thingTypeName=thing_type_name,
        thingTypeProperties={"searchableAttributes": ["s1", "s2", "s3"]},
    )
    client.deprecate_thing_type(thingTypeName=thing_type_name, undoDeprecate=False)
    with pytest.raises(client.exceptions.InvalidRequestException):
        client.create_thing(thingName="thing-name", thingTypeName=thing_type_name)


@mock_iot
def test_update_thing_with_deprecated_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_type_name = "my-type-name"
    thing_name = "thing-name"

    client.create_thing_type(
        thingTypeName=thing_type_name,
        thingTypeProperties={"searchableAttributes": ["s1", "s2", "s3"]},
    )
    deprecated_thing_type_name = "my-type-name-deprecated"
    client.create_thing_type(
        thingTypeName=deprecated_thing_type_name,
        thingTypeProperties={"searchableAttributes": ["s1", "s2", "s3"]},
    )
    client.deprecate_thing_type(
        thingTypeName=deprecated_thing_type_name, undoDeprecate=False
    )
    client.create_thing(thingName=thing_name, thingTypeName=thing_type_name)
    with pytest.raises(client.exceptions.InvalidRequestException):
        client.update_thing(
            thingName=thing_name, thingTypeName=deprecated_thing_type_name
        )
