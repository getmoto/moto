import json

import boto3

from moto import mock_aws


def create_group(client):
    return client.create_group(
        Name="test_resource_group",
        Description="description",
        ResourceQuery={
            "Type": "TAG_FILTERS_1_0",
            "Query": json.dumps(
                {
                    "ResourceTypeFilters": ["AWS::AllSupported"],
                    "TagFilters": [
                        {"Key": "resources_tag_key", "Values": ["resources_tag_value"]}
                    ],
                }
            ),
        },
        Tags={"resource_group_tag_key": "resource_group_tag_value"},
    )


@mock_aws
def test_create_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    response = create_group(client=resource_groups)
    assert "test_resource_group" in response["Group"]["Name"]
    assert "TAG_FILTERS_1_0" in response["ResourceQuery"]["Type"]
    assert "resource_group_tag_value" in response["Tags"]["resource_group_tag_key"]


@mock_aws
def test_delete_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    create_group(client=resource_groups)

    response = resource_groups.delete_group(GroupName="test_resource_group")
    assert "test_resource_group" in response["Group"]["Name"]

    response = resource_groups.list_groups()
    assert len(response["GroupIdentifiers"]) == 0
    assert len(response["Groups"]) == 0


@mock_aws
def test_get_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    create_group(client=resource_groups)

    response = resource_groups.get_group(GroupName="test_resource_group")
    assert "description" in response["Group"]["Description"]


@mock_aws
def test_get_group_query():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group_arn = create_group(resource_groups)["Group"]["GroupArn"]

    response = resource_groups.get_group_query(GroupName="test_resource_group")
    assert "TAG_FILTERS_1_0" in response["GroupQuery"]["ResourceQuery"]["Type"]

    response_get = resource_groups.get_group_query(Group=group_arn)
    assert "TAG_FILTERS_1_0" in response_get["GroupQuery"]["ResourceQuery"]["Type"]


@mock_aws
def test_get_tags():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group_arn = create_group(resource_groups)["Group"]["GroupArn"]

    response = resource_groups.get_tags(Arn=group_arn)
    assert len(response["Tags"]) == 1
    assert "resource_group_tag_value" in response["Tags"]["resource_group_tag_key"]


@mock_aws
def test_list_groups():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    create_group(resource_groups)

    response = resource_groups.list_groups()
    assert len(response["GroupIdentifiers"]) == 1
    assert len(response["Groups"]) == 1


@mock_aws
def test_tag():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group_arn = create_group(resource_groups)["Group"]["GroupArn"]

    response = resource_groups.tag(
        Arn=group_arn,
        Tags={"resource_group_tag_key_2": "resource_group_tag_value_2"},
    )
    assert "resource_group_tag_value_2" in response["Tags"]["resource_group_tag_key_2"]

    response = resource_groups.get_tags(Arn=group_arn)
    assert len(response["Tags"]) == 2
    assert "resource_group_tag_value_2" in response["Tags"]["resource_group_tag_key_2"]


@mock_aws
def test_untag():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group_arn = create_group(resource_groups)["Group"]["GroupArn"]

    response = resource_groups.untag(Arn=group_arn, Keys=["resource_group_tag_key"])
    assert "resource_group_tag_key" in response["Keys"]

    response = resource_groups.get_tags(Arn=group_arn)
    assert len(response["Tags"]) == 0


@mock_aws
def test_update_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    create_group(client=resource_groups)

    response = resource_groups.update_group(
        GroupName="test_resource_group", Description="description_2"
    )
    assert "description_2" in response["Group"]["Description"]

    response = resource_groups.get_group(GroupName="test_resource_group")
    assert "description_2" in response["Group"]["Description"]


@mock_aws
def test_get_group_configuration():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group = create_group(client=resource_groups)

    configuration = [
        {
            "Type": "AWS::ResourceGroups::Generic",
            "Parameters": [
                {"Name": "allowed-resource-types", "Values": ["AWS::EC2::Host"]},
                {"Name": "deletion-protection", "Values": ["UNLESS_EMPTY"]},
            ],
        }
    ]

    resource_groups.put_group_configuration(
        Group=group["Group"]["Name"], Configuration=configuration
    )

    configuration_resp = resource_groups.get_group_configuration(
        Group=group["Group"]["Name"]
    )

    assert (
        configuration_resp.get("GroupConfiguration").get("Configuration")
        == configuration
    )


@mock_aws
def test_create_group_with_configuration():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    configuration = [
        {
            "Type": "AWS::ResourceGroups::Generic",
            "Parameters": [
                {"Name": "allowed-resource-types", "Values": ["AWS::EC2::Host"]},
                {"Name": "deletion-protection", "Values": ["UNLESS_EMPTY"]},
            ],
        }
    ]
    response = resource_groups.create_group(
        Name="test_resource_group_new",
        Description="description",
        ResourceQuery={
            "Type": "TAG_FILTERS_1_0",
            "Query": json.dumps(
                {
                    "ResourceTypeFilters": ["AWS::AllSupported"],
                    "TagFilters": [
                        {"Key": "resources_tag_key", "Values": ["resources_tag_value"]}
                    ],
                }
            ),
        },
        Configuration=configuration,
        Tags={"resource_group_tag_key": "resource_group_tag_value"},
    )

    assert "test_resource_group_new" in response["Group"]["Name"]

    assert response["GroupConfiguration"]["Configuration"] == configuration
    assert "resource_group_tag_value" in response["Tags"]["resource_group_tag_key"]


@mock_aws
def test_update_group_query():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group_arn = create_group(resource_groups)["Group"]["GroupArn"]

    response = resource_groups.update_group_query(
        GroupName="test_resource_group",
        ResourceQuery={
            "Type": "CLOUDFORMATION_STACK_1_0",
            "Query": json.dumps(
                {
                    "ResourceTypeFilters": ["AWS::AllSupported"],
                    "StackIdentifier": (
                        "arn:aws:cloudformation:eu-west-1:012345678912:stack/"
                        "test_stack/c223eca0-e744-11e8-8910-500c41f59083"
                    ),
                }
            ),
        },
    )
    assert "CLOUDFORMATION_STACK_1_0" in response["GroupQuery"]["ResourceQuery"]["Type"]

    response = resource_groups.get_group_query(GroupName="test_resource_group")
    assert "CLOUDFORMATION_STACK_1_0" in response["GroupQuery"]["ResourceQuery"]["Type"]

    response = resource_groups.update_group_query(
        Group=group_arn,
        ResourceQuery={
            "Type": "TAG_FILTERS_1_0",
            "Query": json.dumps(
                {
                    "ResourceTypeFilters": ["AWS::AllSupported"],
                    "TagFilters": [
                        {"Key": "resources_tag_key", "Values": ["resources_tag_value"]}
                    ],
                }
            ),
        },
    )

    assert "TAG_FILTERS_1_0" in response["GroupQuery"]["ResourceQuery"]["Type"]

    response = resource_groups.get_group_query(Group=group_arn)
    assert "TAG_FILTERS_1_0" in response["GroupQuery"]["ResourceQuery"]["Type"]
