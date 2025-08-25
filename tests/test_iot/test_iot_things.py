import boto3
import pytest

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


@mock_aws
def test_create_thing_with_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "my-thing-with-billing"
    billing_group_name = "my-billing-group"
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Create a thing with billing group
    thing = client.create_thing(
        thingName=thing_name,
        billingGroupName=billing_group_name
    )
    
    assert thing["thingName"] == thing_name
    assert thing["thingArn"] is not None
    assert thing["thingId"] is not None
    
    # Verify the thing was created with billing group
    thing_details = client.describe_thing(thingName=thing_name)
    assert thing_details["billingGroupName"] == billing_group_name


@mock_aws
def test_create_thing_with_billing_group_and_type():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "my-thing-with-billing-and-type"
    thing_type_name = "my-thing-type"
    billing_group_name = "my-billing-group"
    
    # Create a thing type first
    client.create_thing_type(thingTypeName=thing_type_name)
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Create a thing with both billing group and thing type
    thing = client.create_thing(
        thingName=thing_name,
        thingTypeName=thing_type_name,
        billingGroupName=billing_group_name
    )
    
    assert thing["thingName"] == thing_name
    assert thing["thingArn"] is not None
    assert thing["thingId"] is not None
    
    # Verify the thing was created with both billing group and thing type
    thing_details = client.describe_thing(thingName=thing_name)
    assert thing_details["billingGroupName"] == billing_group_name
    assert thing_details["thingTypeName"] == thing_type_name


@mock_aws
def test_create_thing_with_invalid_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "my-thing-invalid-billing"
    invalid_billing_group = "non-existent-billing-group"
    
    # Attempt to create a thing with non-existent billing group
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.create_thing(
            thingName=thing_name,
            billingGroupName=invalid_billing_group
        )


@mock_aws
def test_describe_thing_with_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "my-thing-to-describe"
    billing_group_name = "my-billing-group-to-describe"
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Create a thing with billing group
    client.create_thing(
        thingName=thing_name,
        billingGroupName=billing_group_name
    )
    
    # Describe the thing and verify billing group is included
    thing_details = client.describe_thing(thingName=thing_name)
    
    assert thing_details["thingName"] == thing_name
    assert thing_details["thingArn"] is not None
    assert thing_details["thingId"] is not None
    assert thing_details["billingGroupName"] == billing_group_name
    assert "attributes" in thing_details
    assert "version" in thing_details


@mock_aws
def test_list_things_includes_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "my-thing-for-listing"
    billing_group_name = "my-billing-group-for-listing"
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Create a thing with billing group
    client.create_thing(
        thingName=thing_name,
        billingGroupName=billing_group_name
    )
    
    # List things and verify billing group information is included
    things = client.list_things()
    assert len(things["things"]) == 1
    
    thing_info = things["things"][0]
    assert thing_info["thingName"] == thing_name
    assert thing_info["thingArn"] is not None
    assert thing_info["billingGroupName"] == billing_group_name


@mock_aws
def test_thing_lifecycle_with_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "lifecycle-test-thing"
    billing_group_name = "lifecycle-test-billing-group"
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # 1. Create thing with billing group
    create_response = client.create_thing(
        thingName=thing_name,
        billingGroupName=billing_group_name
    )
    assert create_response["thingName"] == thing_name
    assert "thingArn" in create_response
    
    # 2. Describe thing and verify billing group
    describe_response = client.describe_thing(thingName=thing_name)
    assert describe_response["thingName"] == thing_name
    assert describe_response["billingGroupName"] == billing_group_name
    
    # 3. List things and verify billing group is included
    list_response = client.list_things()
    assert len(list_response["things"]) == 1
    assert list_response["things"][0]["billingGroupName"] == billing_group_name
    
    # 4. Delete thing
    client.delete_thing(thingName=thing_name)
    
    # 5. Verify deletion
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.describe_thing(thingName=thing_name)
    
    # 6. List things (should be empty)
    list_response = client.list_things()
    assert len(list_response["things"]) == 0
