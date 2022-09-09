import boto3

from moto import mock_iot
from moto.core import ACCOUNT_ID


@mock_iot
def test_create_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"

    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    res = client.list_things()
    res.should.have.key("things").which.should.have.length_of(1)
    res["things"][0].should.have.key("thingName").which.should_not.be.none
    res["things"][0].should.have.key("thingArn").which.should_not.be.none


@mock_iot
def test_create_thing_with_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"
    type_name = "my-type-name"

    client.create_thing_type(thingTypeName=type_name)

    thing = client.create_thing(thingName=name, thingTypeName=type_name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    res = client.list_things()
    res.should.have.key("things").which.should.have.length_of(1)
    res["things"][0].should.have.key("thingName").which.should_not.be.none
    res["things"][0].should.have.key("thingArn").which.should_not.be.none

    thing = client.describe_thing(thingName=name)
    thing.should.have.key("thingTypeName").equals(type_name)


@mock_iot
def test_update_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"

    client.create_thing(thingName=name)

    client.update_thing(thingName=name, attributePayload={"attributes": {"k1": "v1"}})
    res = client.list_things()
    res.should.have.key("things").which.should.have.length_of(1)
    res["things"][0].should.have.key("thingName").which.should_not.be.none
    res["things"][0].should.have.key("thingArn").which.should_not.be.none
    res["things"][0]["attributes"].should.have.key("k1").which.should.equal("v1")


@mock_iot
def test_describe_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"

    client.create_thing(thingName=name)
    client.update_thing(thingName=name, attributePayload={"attributes": {"k1": "v1"}})

    thing = client.describe_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("defaultClientId")
    thing.should.have.key("attributes").equals({"k1": "v1"})
    thing.should.have.key("version").equals(1)


@mock_iot
def test_delete_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"

    client.create_thing(thingName=name)

    # delete thing
    client.delete_thing(thingName=name)

    res = client.list_things()
    res.should.have.key("things").which.should.have.length_of(0)


@mock_iot
def test_list_things_with_next_token():
    client = boto3.client("iot", region_name="ap-northeast-1")

    for i in range(0, 200):
        client.create_thing(thingName=str(i + 1))

    things = client.list_things()
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("1")
    things["things"][0]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/1"
    )
    things["things"][-1]["thingName"].should.equal("50")
    things["things"][-1]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/50"
    )

    things = client.list_things(nextToken=things["nextToken"])
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("51")
    things["things"][0]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/51"
    )
    things["things"][-1]["thingName"].should.equal("100")
    things["things"][-1]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/100"
    )

    things = client.list_things(nextToken=things["nextToken"])
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("101")
    things["things"][0]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/101"
    )
    things["things"][-1]["thingName"].should.equal("150")
    things["things"][-1]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/150"
    )

    things = client.list_things(nextToken=things["nextToken"])
    things.should_not.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("151")
    things["things"][0]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/151"
    )
    things["things"][-1]["thingName"].should.equal("200")
    things["things"][-1]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/200"
    )


@mock_iot
def test_list_things_with_attribute_and_thing_type_filter_and_next_token():
    client = boto3.client("iot", region_name="ap-northeast-1")
    client.create_thing_type(thingTypeName="my-thing-type")

    for i in range(0, 200):
        if not (i + 1) % 3:
            attribute_payload = {"attributes": {"foo": "bar"}}
        elif not (i + 1) % 5:
            attribute_payload = {"attributes": {"bar": "foo"}}
        else:
            attribute_payload = {}

        if not (i + 1) % 2:
            thing_type_name = "my-thing-type"
            client.create_thing(
                thingName=str(i + 1),
                thingTypeName=thing_type_name,
                attributePayload=attribute_payload,
            )
        else:
            client.create_thing(
                thingName=str(i + 1), attributePayload=attribute_payload
            )

    # Test filter for thingTypeName
    things = client.list_things(thingTypeName=thing_type_name)
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("2")
    things["things"][0]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/2"
    )
    things["things"][-1]["thingName"].should.equal("100")
    things["things"][-1]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/100"
    )
    all(item["thingTypeName"] == thing_type_name for item in things["things"])

    things = client.list_things(
        nextToken=things["nextToken"], thingTypeName=thing_type_name
    )
    things.should_not.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("102")
    things["things"][0]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/102"
    )
    things["things"][-1]["thingName"].should.equal("200")
    things["things"][-1]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/200"
    )
    all(item["thingTypeName"] == thing_type_name for item in things["things"])

    # Test filter for attributes
    things = client.list_things(attributeName="foo", attributeValue="bar")
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("3")
    things["things"][0]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/3"
    )
    things["things"][-1]["thingName"].should.equal("150")
    things["things"][-1]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/150"
    )
    all(item["attributes"] == {"foo": "bar"} for item in things["things"])

    things = client.list_things(
        nextToken=things["nextToken"], attributeName="foo", attributeValue="bar"
    )
    things.should_not.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(16)
    things["things"][0]["thingName"].should.equal("153")
    things["things"][0]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/153"
    )
    things["things"][-1]["thingName"].should.equal("198")
    things["things"][-1]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/198"
    )
    all(item["attributes"] == {"foo": "bar"} for item in things["things"])

    # Test filter for attributes and thingTypeName
    things = client.list_things(
        thingTypeName=thing_type_name, attributeName="foo", attributeValue="bar"
    )
    things.should_not.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(33)
    things["things"][0]["thingName"].should.equal("6")
    things["things"][0]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/6"
    )
    things["things"][-1]["thingName"].should.equal("198")
    things["things"][-1]["thingArn"].should.equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/198"
    )
    all(
        item["attributes"] == {"foo": "bar"}
        and item["thingTypeName"] == thing_type_name
        for item in things["things"]
    )
