import boto3
import json
import sure  # noqa # pylint: disable=unused-import

from moto import mock_resourcegroups


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


@mock_resourcegroups
def test_create_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    response = create_group(client=resource_groups)
    response["Group"]["Name"].should.contain("test_resource_group")
    response["ResourceQuery"]["Type"].should.contain("TAG_FILTERS_1_0")
    response["Tags"]["resource_group_tag_key"].should.contain(
        "resource_group_tag_value"
    )


@mock_resourcegroups
def test_delete_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    create_group(client=resource_groups)

    response = resource_groups.delete_group(GroupName="test_resource_group")
    response["Group"]["Name"].should.contain("test_resource_group")

    response = resource_groups.list_groups()
    response["GroupIdentifiers"].should.have.length_of(0)
    response["Groups"].should.have.length_of(0)


@mock_resourcegroups
def test_get_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    create_group(client=resource_groups)

    response = resource_groups.get_group(GroupName="test_resource_group")
    response["Group"]["Description"].should.contain("description")


@mock_resourcegroups
def test_get_group_query():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group_arn = create_group(resource_groups)["Group"]["GroupArn"]

    response = resource_groups.get_group_query(GroupName="test_resource_group")
    response["GroupQuery"]["ResourceQuery"]["Type"].should.contain("TAG_FILTERS_1_0")

    response_get = resource_groups.get_group_query(Group=group_arn)
    response_get["GroupQuery"]["ResourceQuery"]["Type"].should.contain(
        "TAG_FILTERS_1_0"
    )


@mock_resourcegroups
def test_get_tags():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group_arn = create_group(resource_groups)["Group"]["GroupArn"]

    response = resource_groups.get_tags(Arn=group_arn)
    response["Tags"].should.have.length_of(1)
    response["Tags"]["resource_group_tag_key"].should.contain(
        "resource_group_tag_value"
    )


@mock_resourcegroups
def test_list_groups():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    create_group(resource_groups)

    response = resource_groups.list_groups()
    response["GroupIdentifiers"].should.have.length_of(1)
    response["Groups"].should.have.length_of(1)


@mock_resourcegroups
def test_tag():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group_arn = create_group(resource_groups)["Group"]["GroupArn"]

    response = resource_groups.tag(
        Arn=group_arn,
        Tags={"resource_group_tag_key_2": "resource_group_tag_value_2"},
    )
    response["Tags"]["resource_group_tag_key_2"].should.contain(
        "resource_group_tag_value_2"
    )

    response = resource_groups.get_tags(Arn=group_arn)
    response["Tags"].should.have.length_of(2)
    response["Tags"]["resource_group_tag_key_2"].should.contain(
        "resource_group_tag_value_2"
    )


@mock_resourcegroups
def test_untag():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    group_arn = create_group(resource_groups)["Group"]["GroupArn"]

    response = resource_groups.untag(Arn=group_arn, Keys=["resource_group_tag_key"])
    response["Keys"].should.contain("resource_group_tag_key")

    response = resource_groups.get_tags(Arn=group_arn)
    response["Tags"].should.have.length_of(0)


@mock_resourcegroups
def test_update_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    create_group(client=resource_groups)

    response = resource_groups.update_group(
        GroupName="test_resource_group", Description="description_2"
    )
    response["Group"]["Description"].should.contain("description_2")

    response = resource_groups.get_group(GroupName="test_resource_group")
    response["Group"]["Description"].should.contain("description_2")


@mock_resourcegroups
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


@mock_resourcegroups
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

    response["Group"]["Name"].should.contain("test_resource_group_new")

    assert response["GroupConfiguration"]["Configuration"] == configuration
    response["Tags"]["resource_group_tag_key"].should.contain(
        "resource_group_tag_value"
    )


@mock_resourcegroups
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
    response["GroupQuery"]["ResourceQuery"]["Type"].should.contain(
        "CLOUDFORMATION_STACK_1_0"
    )

    response = resource_groups.get_group_query(GroupName="test_resource_group")
    response["GroupQuery"]["ResourceQuery"]["Type"].should.contain(
        "CLOUDFORMATION_STACK_1_0"
    )

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

    response["GroupQuery"]["ResourceQuery"]["Type"].should.contain("TAG_FILTERS_1_0")

    response = resource_groups.get_group_query(Group=group_arn)
    response["GroupQuery"]["ResourceQuery"]["Type"].should.contain("TAG_FILTERS_1_0")
