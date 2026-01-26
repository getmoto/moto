"""Unit tests for connect-supported APIs."""

import boto3
import pytest

from moto import mock_aws

# ========== Instance API Tests ==========


@mock_aws
def test_create_instance():
    """Test creating a Connect instance."""
    client = boto3.client("connect", region_name="us-east-1")

    response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="test-instance",
    )

    assert "Id" in response
    assert "Arn" in response
    assert "arn:aws:connect:us-east-1:" in response["Arn"]


@mock_aws
def test_create_instance_with_tags():
    """Test creating a Connect instance with tags."""
    client = boto3.client("connect", region_name="us-east-1")

    response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=False,
        InstanceAlias="tagged-instance",
        Tags={"Environment": "Test", "Project": "Demo"},
    )

    assert "Id" in response
    instance_id = response["Id"]

    # Verify tags are stored
    describe_response = client.describe_instance(InstanceId=instance_id)
    instance = describe_response["Instance"]
    assert instance["Tags"]["Environment"] == "Test"
    assert instance["Tags"]["Project"] == "Demo"


@mock_aws
def test_describe_instance():
    """Test describing a Connect instance."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="SAML",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="describe-test",
    )
    instance_id = create_response["Id"]

    # Describe instance
    response = client.describe_instance(InstanceId=instance_id)

    instance = response["Instance"]
    assert instance["Id"] == instance_id
    assert instance["IdentityManagementType"] == "SAML"
    assert instance["InstanceAlias"] == "describe-test"
    assert instance["InstanceStatus"] == "ACTIVE"
    assert instance["InboundCallsEnabled"] is True
    assert instance["OutboundCallsEnabled"] is True
    assert "CreatedTime" in instance
    assert "ServiceRole" in instance
    assert "InstanceAccessUrl" in instance


@mock_aws
def test_describe_instance_not_found():
    """Test describing a non-existent instance."""
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.describe_instance(InstanceId="nonexistent-instance-id")


@mock_aws
def test_list_instances_empty():
    """Test listing instances when none exist."""
    client = boto3.client("connect", region_name="us-east-1")

    response = client.list_instances()

    assert response["InstanceSummaryList"] == []
    assert "NextToken" not in response


@mock_aws
def test_list_instances():
    """Test listing Connect instances."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create multiple instances
    client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="instance-1",
    )
    client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=False,
        InstanceAlias="instance-2",
    )

    response = client.list_instances()

    assert len(response["InstanceSummaryList"]) == 2
    aliases = {i["InstanceAlias"] for i in response["InstanceSummaryList"]}
    assert aliases == {"instance-1", "instance-2"}


@mock_aws
def test_list_instances_pagination():
    """Test pagination for listing instances."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create multiple instances
    for i in range(5):
        client.create_instance(
            IdentityManagementType="CONNECT_MANAGED",
            InboundCallsEnabled=True,
            OutboundCallsEnabled=True,
            InstanceAlias=f"instance-{i}",
        )

    # Get first page
    response = client.list_instances(MaxResults=2)

    assert len(response["InstanceSummaryList"]) == 2
    assert "NextToken" in response

    # Get second page
    response2 = client.list_instances(MaxResults=2, NextToken=response["NextToken"])

    assert len(response2["InstanceSummaryList"]) == 2
    assert "NextToken" in response2

    # Get last page
    response3 = client.list_instances(MaxResults=2, NextToken=response2["NextToken"])

    assert len(response3["InstanceSummaryList"]) == 1
    assert "NextToken" not in response3


@mock_aws
def test_delete_instance():
    """Test deleting a Connect instance."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    # Verify it exists
    response = client.list_instances()
    assert len(response["InstanceSummaryList"]) == 1

    # Delete instance
    client.delete_instance(InstanceId=instance_id)

    # Verify it's gone
    response = client.list_instances()
    assert len(response["InstanceSummaryList"]) == 0


@mock_aws
def test_delete_instance_not_found():
    """Test deleting a non-existent instance."""
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.delete_instance(InstanceId="nonexistent-instance-id")


@mock_aws
def test_instance_summary_structure():
    """Test that instance summary has correct structure."""
    client = boto3.client("connect", region_name="us-east-1")

    client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="structure-test",
    )

    response = client.list_instances()
    summary = response["InstanceSummaryList"][0]

    assert "Id" in summary
    assert "Arn" in summary
    assert "IdentityManagementType" in summary
    assert "InstanceAlias" in summary
    assert "CreatedTime" in summary
    assert "ServiceRole" in summary
    assert "InstanceStatus" in summary
    assert "InboundCallsEnabled" in summary
    assert "OutboundCallsEnabled" in summary
    assert "InstanceAccessUrl" in summary


# ========== Analytics Data Association Tests ==========


@mock_aws
def test_associate_analytics_data_set():
    """Test associating an analytics data set with a Connect instance."""
    client = boto3.client("connect", region_name="us-east-1")

    # First create an instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    response = client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )

    assert response["DataSetId"] == "dataset-001"
    assert "TargetAccountId" in response
    assert "ResourceShareId" in response
    assert "ResourceShareArn" in response
    # Verify ARN uses source account (123456789012 is moto's default)
    assert "123456789012" in response["ResourceShareArn"]


@mock_aws
def test_associate_analytics_data_set_with_target_account():
    """Test associating with a specific target account."""
    client = boto3.client("connect", region_name="us-east-1")

    # First create an instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    response = client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
        TargetAccountId="987654321098",
    )

    assert response["DataSetId"] == "dataset-001"
    assert response["TargetAccountId"] == "987654321098"
    # RAM ARN should still use source account, not target
    assert "123456789012" in response["ResourceShareArn"]


@mock_aws
def test_associate_analytics_data_set_instance_not_found():
    """Test associating with a non-existent instance."""
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.associate_analytics_data_set(
            InstanceId="nonexistent-instance-id",
            DataSetId="dataset-001",
        )


@mock_aws
def test_associate_analytics_data_set_duplicate():
    """Test that duplicate associations raise an error."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    # First association should succeed
    client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )

    # Duplicate should fail
    with pytest.raises(client.exceptions.InvalidParameterException):
        client.associate_analytics_data_set(
            InstanceId=instance_id,
            DataSetId="dataset-001",
        )


@mock_aws
def test_list_analytics_data_associations_empty():
    """Test listing associations when none exist."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance first
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    response = client.list_analytics_data_associations(
        InstanceId=instance_id,
    )

    assert response["Results"] == []
    assert "NextToken" not in response


@mock_aws
def test_list_analytics_data_associations_instance_not_found():
    """Test listing associations for a non-existent instance."""
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.list_analytics_data_associations(
            InstanceId="nonexistent-instance-id",
        )


@mock_aws
def test_list_analytics_data_associations():
    """Test listing analytics data associations."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    # Create some associations
    client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )
    client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-002",
    )

    response = client.list_analytics_data_associations(
        InstanceId=instance_id,
    )

    assert len(response["Results"]) == 2
    data_set_ids = {r["DataSetId"] for r in response["Results"]}
    assert data_set_ids == {"dataset-001", "dataset-002"}


@mock_aws
def test_list_analytics_data_associations_with_filter():
    """Test listing associations with DataSetId filter."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    # Create some associations
    client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )
    client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-002",
    )

    response = client.list_analytics_data_associations(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )

    assert len(response["Results"]) == 1
    assert response["Results"][0]["DataSetId"] == "dataset-001"


@mock_aws
def test_list_analytics_data_associations_pagination():
    """Test pagination for listing associations."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    # Create multiple associations
    for i in range(5):
        client.associate_analytics_data_set(
            InstanceId=instance_id,
            DataSetId=f"dataset-{i:03d}",
        )

    # Get first page
    response = client.list_analytics_data_associations(
        InstanceId=instance_id,
        MaxResults=2,
    )

    assert len(response["Results"]) == 2
    assert "NextToken" in response

    # Get second page
    response2 = client.list_analytics_data_associations(
        InstanceId=instance_id,
        MaxResults=2,
        NextToken=response["NextToken"],
    )

    assert len(response2["Results"]) == 2
    assert "NextToken" in response2

    # Get last page
    response3 = client.list_analytics_data_associations(
        InstanceId=instance_id,
        MaxResults=2,
        NextToken=response2["NextToken"],
    )

    assert len(response3["Results"]) == 1
    assert "NextToken" not in response3


@mock_aws
def test_disassociate_analytics_data_set():
    """Test disassociating an analytics data set."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    # First associate
    client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )

    # Verify it exists
    response = client.list_analytics_data_associations(InstanceId=instance_id)
    assert len(response["Results"]) == 1

    # Disassociate
    client.disassociate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )

    # Verify it's gone
    response = client.list_analytics_data_associations(InstanceId=instance_id)
    assert len(response["Results"]) == 0


@mock_aws
def test_disassociate_analytics_data_set_instance_not_found():
    """Test disassociating from a non-existent instance."""
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.disassociate_analytics_data_set(
            InstanceId="nonexistent-instance-id",
            DataSetId="dataset-001",
        )


@mock_aws
def test_disassociate_analytics_data_set_not_found():
    """Test disassociating a non-existent data set."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.disassociate_analytics_data_set(
            InstanceId=instance_id,
            DataSetId="nonexistent-dataset",
        )


@mock_aws
def test_association_response_structure():
    """Test that association response has correct structure."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )

    response = client.list_analytics_data_associations(InstanceId=instance_id)

    result = response["Results"][0]
    assert "DataSetId" in result
    assert "TargetAccountId" in result
    assert "ResourceShareId" in result
    assert "ResourceShareArn" in result
    assert "ResourceShareStatus" in result
    # Verify status is uppercase (AWS convention)
    assert result["ResourceShareStatus"] == "ACTIVE"


@mock_aws
def test_delete_instance_cleans_up_associations():
    """Test that deleting an instance cleans up its analytics associations."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    # Add analytics association
    client.associate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )

    # Verify association exists
    response = client.list_analytics_data_associations(InstanceId=instance_id)
    assert len(response["Results"]) == 1

    # Delete instance
    client.delete_instance(InstanceId=instance_id)

    # Verify instance is gone (and associations too)
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.list_analytics_data_associations(InstanceId=instance_id)


@mock_aws
def test_list_instances_deterministic_order():
    """Test that list_instances returns instances in deterministic order."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instances
    ids = []
    for i in range(3):
        response = client.create_instance(
            IdentityManagementType="CONNECT_MANAGED",
            InboundCallsEnabled=True,
            OutboundCallsEnabled=True,
            InstanceAlias=f"instance-{i}",
        )
        ids.append(response["Id"])

    # List multiple times and verify order is consistent
    response1 = client.list_instances()
    response2 = client.list_instances()

    order1 = [i["Id"] for i in response1["InstanceSummaryList"]]
    order2 = [i["Id"] for i in response2["InstanceSummaryList"]]

    assert order1 == order2


@mock_aws
def test_list_analytics_associations_deterministic_order():
    """Test that list_analytics_data_associations returns in deterministic order."""
    client = boto3.client("connect", region_name="us-east-1")

    # Create instance
    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    # Create associations in non-alphabetical order
    for ds_id in ["dataset-c", "dataset-a", "dataset-b"]:
        client.associate_analytics_data_set(
            InstanceId=instance_id,
            DataSetId=ds_id,
        )

    # List multiple times and verify order is consistent
    response1 = client.list_analytics_data_associations(InstanceId=instance_id)
    response2 = client.list_analytics_data_associations(InstanceId=instance_id)

    order1 = [r["DataSetId"] for r in response1["Results"]]
    order2 = [r["DataSetId"] for r in response2["Results"]]

    assert order1 == order2
    # Should be sorted by DataSetId
    assert order1 == ["dataset-a", "dataset-b", "dataset-c"]
