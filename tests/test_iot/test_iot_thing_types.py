import boto3

from moto import mock_iot


@mock_iot
def test_create_thing_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    type_name = "my-type-name"

    thing_type = client.create_thing_type(thingTypeName=type_name)
    assert thing_type["thingTypeName"] == type_name
    assert type_name in thing_type["thingTypeArn"]


@mock_iot
def test_describe_thing_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    type_name = "my-type-name"

    client.create_thing_type(thingTypeName=type_name)

    thing_type = client.describe_thing_type(thingTypeName=type_name)
    assert thing_type["thingTypeName"] == type_name
    assert "thingTypeProperties" in thing_type
    assert "thingTypeMetadata" in thing_type
    assert type_name in thing_type["thingTypeArn"]


@mock_iot
def test_list_thing_types():
    client = boto3.client("iot", region_name="ap-northeast-1")

    for i in range(0, 100):
        client.create_thing_type(thingTypeName=str(i + 1))

    thing_types = client.list_thing_types()
    assert "nextToken" in thing_types
    assert len(thing_types["thingTypes"]) == 50
    assert thing_types["thingTypes"][0]["thingTypeName"] == "1"
    assert thing_types["thingTypes"][-1]["thingTypeName"] == "50"

    thing_types = client.list_thing_types(nextToken=thing_types["nextToken"])
    assert len(thing_types["thingTypes"]) == 50
    assert "nextToken" not in thing_types
    assert thing_types["thingTypes"][0]["thingTypeName"] == "51"
    assert thing_types["thingTypes"][-1]["thingTypeName"] == "100"


@mock_iot
def test_list_thing_types_with_typename_filter():
    client = boto3.client("iot", region_name="ap-northeast-1")

    client.create_thing_type(thingTypeName="thing")
    client.create_thing_type(thingTypeName="thingType")
    client.create_thing_type(thingTypeName="thingTypeName")
    client.create_thing_type(thingTypeName="thingTypeNameGroup")
    client.create_thing_type(thingTypeName="shouldNotFind")
    client.create_thing_type(thingTypeName="find me it shall not")

    thing_types = client.list_thing_types(thingTypeName="thing")
    assert "nextToken" not in thing_types
    assert len(thing_types["thingTypes"]) == 4
    assert thing_types["thingTypes"][0]["thingTypeName"] == "thing"
    assert thing_types["thingTypes"][-1]["thingTypeName"] == "thingTypeNameGroup"

    thing_types = client.list_thing_types(thingTypeName="thingTypeName")
    assert "nextToken" not in thing_types
    assert len(thing_types["thingTypes"]) == 2
    assert thing_types["thingTypes"][0]["thingTypeName"] == "thingTypeName"
    assert thing_types["thingTypes"][-1]["thingTypeName"] == "thingTypeNameGroup"


@mock_iot
def test_delete_thing_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    type_name = "my-type-name"

    client.create_thing_type(thingTypeName=type_name)

    # delete thing type
    client.delete_thing_type(thingTypeName=type_name)
    res = client.list_thing_types()
    assert len(res["thingTypes"]) == 0
