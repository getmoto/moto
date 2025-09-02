import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_billing_group():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"
    properties = {"billingGroupDescription": "Test billing group"}

    response = client.create_billing_group(
        billingGroupName=billing_group_name,
        billingGroupProperties=properties,
    )

    assert response["billingGroupName"] == billing_group_name
    assert "billingGroupArn" in response
    assert "billingGroupId" in response

    # Test creating a billing group that already exists
    with pytest.raises(ClientError) as exc:
        client.create_billing_group(
            billingGroupName=billing_group_name,
            billingGroupProperties=properties,
        )
    assert exc.value.response["Error"]["Code"] == "ResourceAlreadyExistsException"


@mock_aws
def test_describe_billing_group():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"
    properties = {"billingGroupDescription": "Test billing group"}

    client.create_billing_group(
        billingGroupName=billing_group_name,
        billingGroupProperties=properties,
    )

    response = client.describe_billing_group(billingGroupName=billing_group_name)

    assert response["billingGroupName"] == billing_group_name
    assert "billingGroupArn" in response
    assert "billingGroupId" in response
    assert response["billingGroupProperties"] == properties
    assert "billingGroupMetadata" in response

    # Test describing a non-existent billing group
    with pytest.raises(ClientError) as exc:
        client.describe_billing_group(billingGroupName="non-existent-group")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_delete_billing_group():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"
    properties = {"billingGroupDescription": "Test billing group"}

    client.create_billing_group(
        billingGroupName=billing_group_name,
        billingGroupProperties=properties,
    )

    client.delete_billing_group(billingGroupName=billing_group_name)

    # Verify the billing group is deleted
    with pytest.raises(ClientError) as exc:
        client.describe_billing_group(billingGroupName=billing_group_name)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

    # Test deleting a non-existent billing group
    with pytest.raises(ClientError) as exc:
        client.delete_billing_group(billingGroupName="non-existent-group")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_billing_groups():
    client = boto3.client("iot", region_name="us-east-1")

    for i in range(5):
        client.create_billing_group(
            billingGroupName=f"billing-group-{i}",
            billingGroupProperties={"billingGroupDescription": f"Group {i}"},
        )

    response = client.list_billing_groups()
    assert len(response["billingGroups"]) == 5

    response = client.list_billing_groups(maxResults=2)
    assert len(response["billingGroups"]) == 2
    assert "nextToken" in response

    response = client.list_billing_groups(maxResults=3, nextToken=response["nextToken"])
    assert len(response["billingGroups"]) == 3


@mock_aws
def test_update_billing_group():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"
    properties = {"billingGroupDescription": "Test billing group"}

    client.create_billing_group(
        billingGroupName=billing_group_name,
        billingGroupProperties=properties,
    )

    new_properties = {"billingGroupDescription": "Updated test billing group"}
    response = client.update_billing_group(
        billingGroupName=billing_group_name,
        billingGroupProperties=new_properties,
    )

    assert "version" in response

    described = client.describe_billing_group(billingGroupName=billing_group_name)
    assert described["billingGroupProperties"] == new_properties


@mock_aws
def test_add_thing_to_billing_group():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"
    thing_name = "test-thing"

    client.create_billing_group(billingGroupName=billing_group_name)
    client.create_thing(thingName=thing_name)

    client.add_thing_to_billing_group(
        billingGroupName=billing_group_name, thingName=thing_name
    )

    response = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(response["things"]) == 1
    assert thing_name in response["things"]


@mock_aws
def test_remove_thing_from_billing_group():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"
    thing_name = "test-thing"

    client.create_billing_group(billingGroupName=billing_group_name)
    client.create_thing(thingName=thing_name)
    client.add_thing_to_billing_group(
        billingGroupName=billing_group_name, thingName=thing_name
    )

    client.remove_thing_from_billing_group(
        billingGroupName=billing_group_name, thingName=thing_name
    )

    response = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(response["things"]) == 0


@mock_aws
def test_remove_thing_from_billing_group_by_arn():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"
    thing_name = "test-thing"

    # Create billing group and thing
    create_bg_resp = client.create_billing_group(billingGroupName=billing_group_name)
    create_thing_resp = client.create_thing(thingName=thing_name)

    # Add thing to billing group using names
    client.add_thing_to_billing_group(
        billingGroupName=billing_group_name, thingName=thing_name
    )

    # Verify the thing is in the billing group
    response = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(response["things"]) == 1
    assert thing_name in response["things"]

    # Get ARNs
    billing_group_arn = create_bg_resp["billingGroupArn"]
    thing_arn = create_thing_resp["thingArn"]

    # Remove thing from billing group using ARNs
    client.remove_thing_from_billing_group(
        billingGroupArn=billing_group_arn, thingArn=thing_arn
    )

    # Verify the thing is no longer in the billing group
    response = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(response["things"]) == 0


@mock_aws
def test_list_things_in_billing_group():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"

    client.create_billing_group(billingGroupName=billing_group_name)

    for i in range(5):
        thing_name = f"thing-{i}"
        client.create_thing(thingName=thing_name)
        client.add_thing_to_billing_group(
            billingGroupName=billing_group_name, thingName=thing_name
        )

    response = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(response["things"]) == 5

    response = client.list_things_in_billing_group(
        billingGroupName=billing_group_name, maxResults=2
    )
    assert len(response["things"]) == 2
    assert "nextToken" in response

    response = client.list_things_in_billing_group(
        billingGroupName=billing_group_name,
        maxResults=3,
        nextToken=response["nextToken"],
    )
    assert len(response["things"]) == 3


@mock_aws
def test_create_thing_with_billing_group():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"
    thing_name = "test-thing"

    client.create_billing_group(billingGroupName=billing_group_name)
    client.create_thing(thingName=thing_name, billingGroupName=billing_group_name)

    response = client.describe_thing(thingName=thing_name)
    assert response["billingGroupName"] == billing_group_name


@mock_aws
def test_thing_removed_from_billing_group_on_thing_deletion():
    client = boto3.client("iot", region_name="us-east-1")
    billing_group_name = "test-billing-group"
    thing_name = "test-thing"

    client.create_billing_group(billingGroupName=billing_group_name)
    client.create_thing(thingName=thing_name, billingGroupName=billing_group_name)

    # Verify the thing is in the billing group
    response = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(response["things"]) == 1
    assert thing_name in response["things"]

    # Delete the thing
    client.delete_thing(thingName=thing_name)

    # Verify the thing is no longer in the billing group
    response = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(response["things"]) == 0


@mock_aws
def test_simple_list_billing_groups_with_prefix():
    client = boto3.client("iot", region_name="us-east-1")
    client.create_billing_group(billingGroupName="test-prefix-group")
    client.create_billing_group(billingGroupName="other-prefix-group")

    response = client.list_billing_groups(namePrefixFilter="test-prefix-")
    assert len(response["billingGroups"]) == 1
    assert response["billingGroups"][0]["groupName"] == "test-prefix-group"
