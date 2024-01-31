import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_create_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"

    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert thing["thingArn"] is not None
    assert thing["thingId"] is not None

    res = client.list_things()
    assert len(res["things"]) == 1
    assert res["things"][0]["thingName"] == name
    assert res["things"][0]["thingArn"] == thing["thingArn"]


@mock_aws
def test_create_thing_with_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"
    type_name = "my-type-name"

    client.create_thing_type(thingTypeName=type_name)

    thing = client.create_thing(thingName=name, thingTypeName=type_name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    res = client.list_things()
    assert len(res["things"]) == 1
    assert res["things"][0]["thingName"] is not None
    assert res["things"][0]["thingArn"] is not None

    thing = client.describe_thing(thingName=name)
    assert thing["thingTypeName"] == type_name


@mock_aws
def test_update_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"

    client.create_thing(thingName=name)

    client.update_thing(thingName=name, attributePayload={"attributes": {"k1": "v1"}})
    res = client.list_things()
    assert len(res["things"]) == 1
    assert res["things"][0]["thingName"] is not None
    assert res["things"][0]["thingArn"] is not None
    assert res["things"][0]["attributes"] == {"k1": "v1"}

    client.update_thing(thingName=name, attributePayload={"attributes": {"k2": "v2"}})
    res = client.list_things()
    assert len(res["things"]) == 1
    assert res["things"][0]["thingName"] is not None
    assert res["things"][0]["thingArn"] is not None
    assert res["things"][0]["attributes"] == {"k2": "v2"}

    client.update_thing(
        thingName=name, attributePayload={"attributes": {"k1": "v1"}, "merge": True}
    )
    res = client.list_things()
    assert len(res["things"]) == 1
    assert res["things"][0]["thingName"] is not None
    assert res["things"][0]["thingArn"] is not None
    assert res["things"][0]["attributes"] == {"k1": "v1", "k2": "v2"}

    client.update_thing(
        thingName=name, attributePayload={"attributes": {"k1": "v1.1"}, "merge": True}
    )
    res = client.list_things()
    assert len(res["things"]) == 1
    assert res["things"][0]["thingName"] is not None
    assert res["things"][0]["thingArn"] is not None
    assert res["things"][0]["attributes"] == {"k1": "v1.1", "k2": "v2"}

    client.update_thing(
        thingName=name, attributePayload={"attributes": {"k1": ""}, "merge": True}
    )
    res = client.list_things()
    assert len(res["things"]) == 1
    assert res["things"][0]["thingName"] is not None
    assert res["things"][0]["thingArn"] is not None
    assert res["things"][0]["attributes"] == {"k2": "v2"}

    client.update_thing(thingName=name, attributePayload={"attributes": {"k2": ""}})
    res = client.list_things()
    assert len(res["things"]) == 1
    assert res["things"][0]["thingName"] is not None
    assert res["things"][0]["thingArn"] is not None
    assert res["things"][0]["attributes"] == {}


@mock_aws
def test_describe_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"

    client.create_thing(thingName=name)
    client.update_thing(thingName=name, attributePayload={"attributes": {"k1": "v1"}})

    thing = client.describe_thing(thingName=name)
    assert thing["thingId"] is not None
    assert thing["thingName"] == name
    assert "defaultClientId" in thing
    assert thing["attributes"] == {"k1": "v1"}
    assert thing["version"] == 1


@mock_aws
def test_delete_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"

    client.create_thing(thingName=name)

    # delete thing
    client.delete_thing(thingName=name)

    res = client.list_things()
    assert len(res["things"]) == 0


@mock_aws
def test_list_things_with_next_token():
    client = boto3.client("iot", region_name="ap-northeast-1")

    for i in range(0, 200):
        client.create_thing(thingName=str(i + 1))

    things = client.list_things()
    assert len(things["things"]) == 50
    assert things["things"][0]["thingName"] == "1"
    assert (
        things["things"][0]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/1"
    )
    assert things["things"][-1]["thingName"] == "50"
    assert (
        things["things"][-1]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/50"
    )

    things = client.list_things(nextToken=things["nextToken"])
    assert len(things["things"]) == 50
    assert things["things"][0]["thingName"] == "51"
    assert (
        things["things"][0]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/51"
    )
    assert things["things"][-1]["thingName"] == "100"
    assert (
        things["things"][-1]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/100"
    )

    things = client.list_things(nextToken=things["nextToken"])
    assert len(things["things"]) == 50
    assert things["things"][0]["thingName"] == "101"
    assert (
        things["things"][0]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/101"
    )
    assert things["things"][-1]["thingName"] == "150"
    assert (
        things["things"][-1]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/150"
    )

    things = client.list_things(nextToken=things["nextToken"])
    assert "nextToken" not in things
    assert len(things["things"]) == 50
    assert things["things"][0]["thingName"] == "151"
    assert (
        things["things"][0]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/151"
    )
    assert things["things"][-1]["thingName"] == "200"
    assert (
        things["things"][-1]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/200"
    )


@mock_aws
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
    assert "nextToken" in things
    assert len(things["things"]) == 50
    assert things["things"][0]["thingName"] == "2"
    assert (
        things["things"][0]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/2"
    )
    assert things["things"][-1]["thingName"] == "100"
    assert (
        things["things"][-1]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/100"
    )
    assert all(item["thingTypeName"] == thing_type_name for item in things["things"])

    things = client.list_things(
        nextToken=things["nextToken"], thingTypeName=thing_type_name
    )
    assert "nextToken" not in things
    assert len(things["things"]) == 50
    assert things["things"][0]["thingName"] == "102"
    assert (
        things["things"][0]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/102"
    )
    assert things["things"][-1]["thingName"] == "200"
    assert (
        things["things"][-1]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/200"
    )
    assert all(item["thingTypeName"] == thing_type_name for item in things["things"])

    # Test filter for attributes
    things = client.list_things(attributeName="foo", attributeValue="bar")
    assert "nextToken" in things
    assert len(things["things"]) == 50
    assert things["things"][0]["thingName"] == "3"
    assert (
        things["things"][0]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/3"
    )
    assert things["things"][-1]["thingName"] == "150"
    assert (
        things["things"][-1]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/150"
    )
    assert all(item["attributes"] == {"foo": "bar"} for item in things["things"])

    things = client.list_things(
        nextToken=things["nextToken"], attributeName="foo", attributeValue="bar"
    )
    assert "nextToken" not in things
    assert len(things["things"]) == 16
    assert things["things"][0]["thingName"] == "153"
    assert (
        things["things"][0]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/153"
    )
    assert things["things"][-1]["thingName"] == "198"
    assert (
        things["things"][-1]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/198"
    )
    assert all(item["attributes"] == {"foo": "bar"} for item in things["things"])

    # Test filter for attributes and thingTypeName
    things = client.list_things(
        thingTypeName=thing_type_name, attributeName="foo", attributeValue="bar"
    )
    assert "nextToken" not in things
    assert len(things["things"]) == 33
    assert things["things"][0]["thingName"] == "6"
    assert (
        things["things"][0]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/6"
    )
    assert things["things"][-1]["thingName"] == "198"
    assert (
        things["things"][-1]["thingArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/198"
    )
    assert all(
        item["attributes"] == {"foo": "bar"}
        and item["thingTypeName"] == thing_type_name
        for item in things["things"]
    )
