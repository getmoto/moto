import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    billing_group_name = "test-billing-group"

    billing_group = client.create_billing_group(billingGroupName=billing_group_name)

    assert "billingGroupArn" in billing_group
    assert billing_group_name in billing_group["billingGroupArn"]
    

@mock_aws
def test_create_billing_group_with_properties():
    client = boto3.client("iot", region_name="ap-northeast-1")
    billing_group_name = "test-billing-group-with-props"
    billing_group_properties = {
        "billingGroupDescription": "Test billing group with properties",
        "attributePayload": {
            "attributes": {
                "key1": "value1",
                "key2": "value2"
            }
        }
    }

    billing_group = client.create_billing_group(
        billingGroupName=billing_group_name,
        billingGroupProperties=billing_group_properties
    )
    assert "billingGroupArn" in billing_group
    assert billing_group_name in billing_group["billingGroupArn"]
    # Only ARN should be returned for create operation
    assert len(billing_group) == 1

@mock_aws
def test_describe_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    billing_group_name = "test-describe-billing-group"
    
    client.create_billing_group(billingGroupName=billing_group_name)
    
    response = client.describe_billing_group(billingGroupName=billing_group_name)
    
    assert response["billingGroupName"] == billing_group_name
    assert "billingGroupArn" in response
    assert "billingGroupId" in response
    assert "billingGroupMetadata" in response
    assert "billingGroupProperties" in response
    assert "version" in response
    assert billing_group_name in response["billingGroupArn"]

@mock_aws
def test_describe_billing_group_not_found():
    client = boto3.client("iot", region_name="ap-northeast-1")
    
    with pytest.raises(ClientError) as exc_info:
        client.describe_billing_group(billingGroupName="non-existent-billing-group")
    
    error = exc_info.value.response["Error"]
    assert error["Code"] == "ResourceNotFoundException"

@mock_aws
def test_delete_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    billing_group_name = "test-delete-billing-group"
    
    client.create_billing_group(billingGroupName=billing_group_name)
    
    response = client.describe_billing_group(billingGroupName=billing_group_name)
    assert response["billingGroupName"] == billing_group_name
    
    delete_response = client.delete_billing_group(billingGroupName=billing_group_name)
    assert delete_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    with pytest.raises(ClientError) as exc_info:
        client.describe_billing_group(billingGroupName=billing_group_name)
    
    error = exc_info.value.response["Error"]
    assert error["Code"] == "ResourceNotFoundException"

@mock_aws
def test_delete_billing_group_not_found():
    client = boto3.client("iot", region_name="ap-northeast-1")
    
    response = client.delete_billing_group(billingGroupName="non-existent-billing-group")
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

@mock_aws
def test_list_billing_groups():
    client = boto3.client("iot", region_name="ap-northeast-1")
    
    # Initially no billing groups
    response = client.list_billing_groups()
    assert "billingGroups" in response
    assert len(response["billingGroups"]) == 0
    
    # Create some billing groups
    billing_group_names = ["group1", "group2", "group3"]
    for name in billing_group_names:
        client.create_billing_group(billingGroupName=name)
    
    # List all billing groups
    response = client.list_billing_groups()
    assert "billingGroups" in response
    assert len(response["billingGroups"]) == 3
    
    # Verify each billing group has required fields
    for billing_group in response["billingGroups"]:
        assert "billingGroupName" in billing_group
        assert "billingGroupArn" in billing_group
        assert "billingGroupId" in billing_group
        assert "billingGroupMetadata" in billing_group
        assert "billingGroupProperties" in billing_group
        assert "version" in billing_group

@mock_aws
def test_billing_group_lifecycle():
    client = boto3.client("iot", region_name="ap-northeast-1")
    billing_group_name = "lifecycle-test-group"
    
    # 1. Create billing group
    create_response = client.create_billing_group(billingGroupName=billing_group_name)
    assert "billingGroupArn" in create_response
    assert billing_group_name in create_response["billingGroupArn"]
    
    # 2. Describe billing group
    describe_response = client.describe_billing_group(billingGroupName=billing_group_name)
    assert describe_response["billingGroupName"] == billing_group_name
    assert describe_response["billingGroupArn"] == create_response["billingGroupArn"]
    
    # 3. List billing groups (should include our group)
    list_response = client.list_billing_groups()
    assert len(list_response["billingGroups"]) == 1
    assert list_response["billingGroups"][0]["billingGroupName"] == billing_group_name
    
    # 4. Delete billing group
    delete_response = client.delete_billing_group(billingGroupName=billing_group_name)
    assert delete_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # 5. Verify deletion
    with pytest.raises(ClientError) as exc_info:
        client.describe_billing_group(billingGroupName=billing_group_name)
    assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"
    
    # 6. List billing groups (should be empty)
    list_response = client.list_billing_groups()
    assert len(list_response["billingGroups"]) == 0

@mock_aws
def test_billing_group_with_properties_lifecycle():
    client = boto3.client("iot", region_name="ap-northeast-1")
    billing_group_name = "props-lifecycle-test"
    properties = {
        "billingGroupDescription": "Test description",
        "attributePayload": {
            "attributes": {
                "environment": "test",
                "project": "iot-billing"
            }
        }
    }
    
    # Create with properties
    create_response = client.create_billing_group(
        billingGroupName=billing_group_name,
        billingGroupProperties=properties
    )
    assert "billingGroupArn" in create_response
    assert billing_group_name in create_response["billingGroupArn"]
    
    # Describe and verify properties
    describe_response = client.describe_billing_group(billingGroupName=billing_group_name)
    assert describe_response["billingGroupProperties"] == properties
    
    # Delete
    client.delete_billing_group(billingGroupName=billing_group_name)
    
    # Verify deletion
    with pytest.raises(ClientError) as exc_info:
        client.describe_billing_group(billingGroupName=billing_group_name)
    assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_add_thing_to_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "test-thing-for-billing"
    billing_group_name = "test-billing-group-for-things"
    
    # Create a thing first
    client.create_thing(thingName=thing_name)
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Add thing to billing group
    response = client.add_thing_to_billing_group(
        billingGroupName=billing_group_name,
        thingName=thing_name
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Verify thing is in billing group
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert thing_name in things_in_group["things"]


@mock_aws
def test_add_thing_to_billing_group_with_arns():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "test-thing-with-arns"
    billing_group_name = "test-billing-group-with-arns"
    
    # Create a thing first
    thing = client.create_thing(thingName=thing_name)
    
    # Create a billing group first
    billing_group = client.create_billing_group(billingGroupName=billing_group_name)
    
    # Add thing to billing group using ARNs
    response = client.add_thing_to_billing_group(
        billingGroupArn=billing_group["billingGroupArn"],
        thingArn=thing["thingArn"]
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Verify thing is in billing group
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert thing_name in things_in_group["things"]


@mock_aws
def test_add_thing_to_billing_group_duplicate():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "test-thing-duplicate"
    billing_group_name = "test-billing-group-duplicate"
    
    # Create a thing first
    client.create_thing(thingName=thing_name)
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Add thing to billing group first time
    response1 = client.add_thing_to_billing_group(
        billingGroupName=billing_group_name,
        thingName=thing_name
    )
    assert response1["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Add same thing again (should not fail, AWS ignores duplicates)
    response2 = client.add_thing_to_billing_group(
        billingGroupName=billing_group_name,
        thingName=thing_name
    )
    assert response2["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Verify thing is still in billing group (only once)
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert things_in_group["things"].count(thing_name) == 1


@mock_aws
def test_remove_thing_from_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "test-thing-to-remove"
    billing_group_name = "test-billing-group-remove"
    
    # Create a thing first
    client.create_thing(thingName=thing_name)
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Add thing to billing group
    client.add_thing_to_billing_group(
        billingGroupName=billing_group_name,
        thingName=thing_name
    )
    
    # Verify thing is in billing group
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert thing_name in things_in_group["things"]
    
    # Remove thing from billing group
    response = client.remove_thing_from_billing_group(
        billingGroupName=billing_group_name,
        thingName=thing_name
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Verify thing is no longer in billing group
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert thing_name not in things_in_group["things"]


@mock_aws
def test_remove_thing_from_billing_group_not_member():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "test-thing-not-member"
    billing_group_name = "test-billing-group-not-member"
    
    # Create a thing first
    client.create_thing(thingName=thing_name)
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Try to remove thing that's not in billing group (should not fail, AWS ignores)
    response = client.remove_thing_from_billing_group(
        billingGroupName=billing_group_name,
        thingName=thing_name
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Verify billing group is still empty
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(things_in_group["things"]) == 0


@mock_aws
def test_list_things_in_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    billing_group_name = "test-billing-group-list"
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Initially no things in billing group
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(things_in_group["things"]) == 0
    
    # Create some things
    thing_names = ["thing1", "thing2", "thing3"]
    for name in thing_names:
        client.create_thing(thingName=name)
        client.add_thing_to_billing_group(
            billingGroupName=billing_group_name,
            thingName=name
        )
    
    # List things in billing group
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert len(things_in_group["things"]) == 3
    
    # Verify all things are included
    for name in thing_names:
        assert name in things_in_group["things"]


@mock_aws
def test_list_billing_groups_for_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "test-thing-for-groups"
    
    # Create a thing first
    client.create_thing(thingName=thing_name)
    
    # Initially no billing groups for thing
    billing_groups_for_thing = client.list_billing_groups_for_thing(thingName=thing_name)
    assert len(billing_groups_for_thing["billingGroups"]) == 0
    
    # Create some billing groups
    billing_group_names = ["group1", "group2", "group3"]
    for name in billing_group_names:
        client.create_billing_group(billingGroupName=name)
        client.add_thing_to_billing_group(
            billingGroupName=name,
            thingName=thing_name
        )
    
    # List billing groups for thing
    billing_groups_for_thing = client.list_billing_groups_for_thing(thingName=thing_name)
    assert len(billing_groups_for_thing["billingGroups"]) == 3
    
    # Verify all billing groups are included
    for group_info in billing_groups_for_thing["billingGroups"]:
        assert "billingGroupName" in group_info
        assert "billingGroupArn" in group_info
        assert group_info["billingGroupName"] in billing_group_names


@mock_aws
def test_update_billing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    billing_group_name = "test-billing-group-update"
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Get initial version
    initial_details = client.describe_billing_group(billingGroupName=billing_group_name)
    initial_version = initial_details["version"]
    
    # Update billing group properties
    new_properties = {
        "billingGroupDescription": "Updated description",
        "attributePayload": {
            "attributes": {
                "environment": "production",
                "updated": "true"
            }
        }
    }
    
    response = client.update_billing_group(
        billingGroupName=billing_group_name,
        billingGroupProperties=new_properties
    )
    
    assert "version" in response
    assert response["version"] == initial_version + 1
    
    # Verify properties were updated
    updated_details = client.describe_billing_group(billingGroupName=billing_group_name)
    assert updated_details["version"] == initial_version + 1
    assert updated_details["billingGroupProperties"] == new_properties


@mock_aws
def test_update_billing_group_with_version():
    client = boto3.client("iot", region_name="ap-northeast-1")
    billing_group_name = "test-billing-group-version"
    
    # Create a billing group first
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # Get initial version
    initial_details = client.describe_billing_group(billingGroupName=billing_group_name)
    initial_version = initial_details["version"]
    
    # Update with correct version
    new_properties = {"billingGroupDescription": "Versioned update"}
    response = client.update_billing_group(
        billingGroupName=billing_group_name,
        billingGroupProperties=new_properties,
        expectedVersion=initial_version
    )
    
    assert response["version"] == initial_version + 1
    
    # Try to update with wrong version (should fail)
    with pytest.raises(ClientError) as exc_info:
        client.update_billing_group(
            billingGroupName=billing_group_name,
            billingGroupProperties={"description": "Wrong version"},
            expectedVersion=initial_version  # This is now wrong
        )
    
    error = exc_info.value.response["Error"]
    assert error["Code"] == "VersionConflictException"


@mock_aws
def test_billing_group_thing_management_lifecycle():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "lifecycle-test-thing"
    billing_group_name = "lifecycle-test-billing-group"
    
    # 1. Create thing and billing group
    client.create_thing(thingName=thing_name)
    client.create_billing_group(billingGroupName=billing_group_name)
    
    # 2. Add thing to billing group
    client.add_thing_to_billing_group(
        billingGroupName=billing_group_name,
        thingName=thing_name
    )
    
    # 3. Verify thing is in billing group
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert thing_name in things_in_group["things"]
    
    # 4. Verify billing group is listed for thing
    billing_groups_for_thing = client.list_billing_groups_for_thing(thingName=thing_name)
    assert len(billing_groups_for_thing["billingGroups"]) == 1
    assert billing_groups_for_thing["billingGroups"][0]["billingGroupName"] == billing_group_name
    
    # 5. Remove thing from billing group
    client.remove_thing_from_billing_group(
        billingGroupName=billing_group_name,
        thingName=thing_name
    )
    
    # 6. Verify thing is no longer in billing group
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert thing_name not in things_in_group["things"]
    
    # 7. Verify billing group is no longer listed for thing
    billing_groups_for_thing = client.list_billing_groups_for_thing(thingName=thing_name)
    assert len(billing_groups_for_thing["billingGroups"]) == 0


@mock_aws
def test_billing_group_thing_management_with_arns():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "arn-test-thing"
    billing_group_name = "arn-test-billing-group"
    
    # Create thing and billing group
    thing = client.create_thing(thingName=thing_name)
    billing_group = client.create_billing_group(billingGroupName=billing_group_name)
    
    # Add using ARNs
    client.add_thing_to_billing_group(
        billingGroupArn=billing_group["billingGroupArn"],
        thingArn=thing["thingArn"]
    )
    
    # Verify using name
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert thing_name in things_in_group["things"]
    
    # Remove using ARNs
    client.remove_thing_from_billing_group(
        billingGroupArn=billing_group["billingGroupArn"],
        thingArn=thing["thingArn"]
    )
    
    # Verify removal
    things_in_group = client.list_things_in_billing_group(billingGroupName=billing_group_name)
    assert thing_name not in things_in_group["things"]
