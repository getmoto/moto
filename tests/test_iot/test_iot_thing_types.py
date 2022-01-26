import boto3

from moto import mock_iot


@mock_iot
def test_create_thing_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    type_name = "my-type-name"

    thing_type = client.create_thing_type(thingTypeName=type_name)
    thing_type.should.have.key("thingTypeName").which.should.equal(type_name)
    thing_type.should.have.key("thingTypeArn")
    thing_type["thingTypeArn"].should.contain(type_name)


@mock_iot
def test_describe_thing_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    type_name = "my-type-name"

    client.create_thing_type(thingTypeName=type_name)

    thing_type = client.describe_thing_type(thingTypeName=type_name)
    thing_type.should.have.key("thingTypeName").which.should.equal(type_name)
    thing_type.should.have.key("thingTypeProperties")
    thing_type.should.have.key("thingTypeMetadata")
    thing_type.should.have.key("thingTypeArn")
    thing_type["thingTypeArn"].should.contain(type_name)


@mock_iot
def test_list_thing_types():
    client = boto3.client("iot", region_name="ap-northeast-1")

    for i in range(0, 100):
        client.create_thing_type(thingTypeName=str(i + 1))

    thing_types = client.list_thing_types()
    thing_types.should.have.key("nextToken")
    thing_types.should.have.key("thingTypes").which.should.have.length_of(50)
    thing_types["thingTypes"][0]["thingTypeName"].should.equal("1")
    thing_types["thingTypes"][-1]["thingTypeName"].should.equal("50")

    thing_types = client.list_thing_types(nextToken=thing_types["nextToken"])
    thing_types.should.have.key("thingTypes").which.should.have.length_of(50)
    thing_types.should_not.have.key("nextToken")
    thing_types["thingTypes"][0]["thingTypeName"].should.equal("51")
    thing_types["thingTypes"][-1]["thingTypeName"].should.equal("100")


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
    thing_types.should_not.have.key("nextToken")
    thing_types.should.have.key("thingTypes").which.should.have.length_of(4)
    thing_types["thingTypes"][0]["thingTypeName"].should.equal("thing")
    thing_types["thingTypes"][-1]["thingTypeName"].should.equal("thingTypeNameGroup")

    thing_types = client.list_thing_types(thingTypeName="thingTypeName")
    thing_types.should_not.have.key("nextToken")
    thing_types.should.have.key("thingTypes").which.should.have.length_of(2)
    thing_types["thingTypes"][0]["thingTypeName"].should.equal("thingTypeName")
    thing_types["thingTypes"][-1]["thingTypeName"].should.equal("thingTypeNameGroup")


@mock_iot
def test_delete_thing_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    type_name = "my-type-name"

    client.create_thing_type(thingTypeName=type_name)

    # delete thing type
    client.delete_thing_type(thingTypeName=type_name)
    res = client.list_thing_types()
    res.should.have.key("thingTypes").which.should.have.length_of(0)
