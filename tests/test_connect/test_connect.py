import boto3
import pytest

from moto import mock_aws


@mock_aws
def test_create_instance():
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

    describe_response = client.describe_instance(InstanceId=instance_id)
    instance = describe_response["Instance"]
    assert instance["Tags"]["Environment"] == "Test"
    assert instance["Tags"]["Project"] == "Demo"


@mock_aws
def test_describe_instance():
    client = boto3.client("connect", region_name="us-east-1")

    create_response = client.create_instance(
        IdentityManagementType="SAML",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="describe-test",
    )
    instance_id = create_response["Id"]

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
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.describe_instance(InstanceId="nonexistent-instance-id")


@mock_aws
def test_list_instances_empty():
    client = boto3.client("connect", region_name="us-east-1")

    response = client.list_instances()

    assert response["InstanceSummaryList"] == []
    assert "NextToken" not in response


@mock_aws
def test_list_instances():
    client = boto3.client("connect", region_name="us-east-1")

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
    client = boto3.client("connect", region_name="us-east-1")

    for i in range(5):
        client.create_instance(
            IdentityManagementType="CONNECT_MANAGED",
            InboundCallsEnabled=True,
            OutboundCallsEnabled=True,
            InstanceAlias=f"instance-{i}",
        )

    response = client.list_instances(MaxResults=2)

    assert len(response["InstanceSummaryList"]) == 2
    assert "NextToken" in response

    response2 = client.list_instances(MaxResults=2, NextToken=response["NextToken"])

    assert len(response2["InstanceSummaryList"]) == 2
    assert "NextToken" in response2

    response3 = client.list_instances(MaxResults=2, NextToken=response2["NextToken"])

    assert len(response3["InstanceSummaryList"]) == 1
    assert "NextToken" not in response3


@mock_aws
def test_delete_instance():
    client = boto3.client("connect", region_name="us-east-1")

    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    response = client.list_instances()
    assert len(response["InstanceSummaryList"]) == 1

    client.delete_instance(InstanceId=instance_id)

    response = client.list_instances()
    assert len(response["InstanceSummaryList"]) == 0


@mock_aws
def test_delete_instance_not_found():
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.delete_instance(InstanceId="nonexistent-instance-id")


@mock_aws
def test_instance_summary_structure():
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


@mock_aws
def test_associate_analytics_data_set():
    client = boto3.client("connect", region_name="us-east-1")

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
    assert "123456789012" in response["ResourceShareArn"]


@mock_aws
def test_associate_analytics_data_set_with_target_account():
    client = boto3.client("connect", region_name="us-east-1")

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
    assert "123456789012" in response["ResourceShareArn"]


@mock_aws
def test_associate_analytics_data_set_instance_not_found():
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.associate_analytics_data_set(
            InstanceId="nonexistent-instance-id",
            DataSetId="dataset-001",
        )


@mock_aws
def test_associate_analytics_data_set_duplicate():
    client = boto3.client("connect", region_name="us-east-1")

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

    with pytest.raises(client.exceptions.InvalidParameterException):
        client.associate_analytics_data_set(
            InstanceId=instance_id,
            DataSetId="dataset-001",
        )


@mock_aws
def test_list_analytics_data_associations_empty():
    client = boto3.client("connect", region_name="us-east-1")

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
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.list_analytics_data_associations(
            InstanceId="nonexistent-instance-id",
        )


@mock_aws
def test_list_analytics_data_associations():
    client = boto3.client("connect", region_name="us-east-1")

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
    client = boto3.client("connect", region_name="us-east-1")

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
    client = boto3.client("connect", region_name="us-east-1")

    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    for i in range(5):
        client.associate_analytics_data_set(
            InstanceId=instance_id,
            DataSetId=f"dataset-{i:03d}",
        )

    response = client.list_analytics_data_associations(
        InstanceId=instance_id,
        MaxResults=2,
    )

    assert len(response["Results"]) == 2
    assert "NextToken" in response

    response2 = client.list_analytics_data_associations(
        InstanceId=instance_id,
        MaxResults=2,
        NextToken=response["NextToken"],
    )

    assert len(response2["Results"]) == 2
    assert "NextToken" in response2

    response3 = client.list_analytics_data_associations(
        InstanceId=instance_id,
        MaxResults=2,
        NextToken=response2["NextToken"],
    )

    assert len(response3["Results"]) == 1
    assert "NextToken" not in response3


@mock_aws
def test_disassociate_analytics_data_set():
    client = boto3.client("connect", region_name="us-east-1")

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
    assert len(response["Results"]) == 1

    client.disassociate_analytics_data_set(
        InstanceId=instance_id,
        DataSetId="dataset-001",
    )

    response = client.list_analytics_data_associations(InstanceId=instance_id)
    assert len(response["Results"]) == 0


@mock_aws
def test_disassociate_analytics_data_set_instance_not_found():
    client = boto3.client("connect", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.disassociate_analytics_data_set(
            InstanceId="nonexistent-instance-id",
            DataSetId="dataset-001",
        )


@mock_aws
def test_disassociate_analytics_data_set_not_found():
    client = boto3.client("connect", region_name="us-east-1")

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
    client = boto3.client("connect", region_name="us-east-1")

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
    assert result["ResourceShareStatus"] == "ACTIVE"


@mock_aws
def test_delete_instance_cleans_up_associations():
    client = boto3.client("connect", region_name="us-east-1")

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
    assert len(response["Results"]) == 1

    client.delete_instance(InstanceId=instance_id)

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.list_analytics_data_associations(InstanceId=instance_id)


@mock_aws
def test_list_instances_deterministic_order():
    client = boto3.client("connect", region_name="us-east-1")

    ids = []
    for i in range(3):
        response = client.create_instance(
            IdentityManagementType="CONNECT_MANAGED",
            InboundCallsEnabled=True,
            OutboundCallsEnabled=True,
            InstanceAlias=f"instance-{i}",
        )
        ids.append(response["Id"])

    response1 = client.list_instances()
    response2 = client.list_instances()

    order1 = [i["Id"] for i in response1["InstanceSummaryList"]]
    order2 = [i["Id"] for i in response2["InstanceSummaryList"]]

    assert order1 == order2


@mock_aws
def test_list_analytics_associations_deterministic_order():
    client = boto3.client("connect", region_name="us-east-1")

    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_id = create_response["Id"]

    for ds_id in ["dataset-c", "dataset-a", "dataset-b"]:
        client.associate_analytics_data_set(
            InstanceId=instance_id,
            DataSetId=ds_id,
        )

    response1 = client.list_analytics_data_associations(InstanceId=instance_id)
    response2 = client.list_analytics_data_associations(InstanceId=instance_id)

    order1 = [r["DataSetId"] for r in response1["Results"]]
    order2 = [r["DataSetId"] for r in response2["Results"]]

    assert order1 == order2
    assert order1 == ["dataset-a", "dataset-b", "dataset-c"]


@mock_aws
def test_tag_resource():
    client = boto3.client("connect", region_name="us-east-1")

    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="tag-test",
    )
    instance_arn = create_response["Arn"]

    client.tag_resource(
        resourceArn=instance_arn,
        tags={"Environment": "Production", "Team": "Engineering"},
    )

    response = client.list_tags_for_resource(resourceArn=instance_arn)
    assert response["tags"]["Environment"] == "Production"
    assert response["tags"]["Team"] == "Engineering"


@mock_aws
def test_untag_resource():
    client = boto3.client("connect", region_name="us-east-1")

    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="untag-test",
        Tags={"Environment": "Test", "Team": "QA", "Project": "Demo"},
    )
    instance_arn = create_response["Arn"]

    client.untag_resource(resourceArn=instance_arn, tagKeys=["Team", "Project"])

    response = client.list_tags_for_resource(resourceArn=instance_arn)
    assert "Environment" in response["tags"]
    assert "Team" not in response["tags"]
    assert "Project" not in response["tags"]


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("connect", region_name="us-east-1")

    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="list-tags-test",
        Tags={"Key1": "Value1", "Key2": "Value2"},
    )
    instance_arn = create_response["Arn"]

    response = client.list_tags_for_resource(resourceArn=instance_arn)

    assert response["tags"] == {"Key1": "Value1", "Key2": "Value2"}


@mock_aws
def test_list_tags_for_resource_empty():
    client = boto3.client("connect", region_name="us-east-1")

    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
    )
    instance_arn = create_response["Arn"]

    response = client.list_tags_for_resource(resourceArn=instance_arn)

    assert response["tags"] == {}
