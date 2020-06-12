from __future__ import unicode_literals

import boto3
import json
import sure  # noqa

from moto import mock_resourcegroups


@mock_resourcegroups
def test_create_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    response = resource_groups.create_group(
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
    response["Group"]["Name"].should.contain("test_resource_group")
    response["ResourceQuery"]["Type"].should.contain("TAG_FILTERS_1_0")
    response["Tags"]["resource_group_tag_key"].should.contain(
        "resource_group_tag_value"
    )


@mock_resourcegroups
def test_delete_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    test_create_group()

    response = resource_groups.delete_group(GroupName="test_resource_group")
    response["Group"]["Name"].should.contain("test_resource_group")

    response = resource_groups.list_groups()
    response["GroupIdentifiers"].should.have.length_of(0)
    response["Groups"].should.have.length_of(0)


@mock_resourcegroups
def test_get_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    test_create_group()

    response = resource_groups.get_group(GroupName="test_resource_group")
    response["Group"]["Description"].should.contain("description")

    return response


@mock_resourcegroups
def test_get_group_query():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    test_create_group()

    response = resource_groups.get_group_query(GroupName="test_resource_group")
    response["GroupQuery"]["ResourceQuery"]["Type"].should.contain("TAG_FILTERS_1_0")


@mock_resourcegroups
def test_get_tags():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    response = test_get_group()

    response = resource_groups.get_tags(Arn=response["Group"]["GroupArn"])
    response["Tags"].should.have.length_of(1)
    response["Tags"]["resource_group_tag_key"].should.contain(
        "resource_group_tag_value"
    )

    return response


@mock_resourcegroups
def test_list_groups():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    test_create_group()

    response = resource_groups.list_groups()
    response["GroupIdentifiers"].should.have.length_of(1)
    response["Groups"].should.have.length_of(1)


@mock_resourcegroups
def test_tag():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    response = test_get_tags()

    response = resource_groups.tag(
        Arn=response["Arn"],
        Tags={"resource_group_tag_key_2": "resource_group_tag_value_2"},
    )
    response["Tags"]["resource_group_tag_key_2"].should.contain(
        "resource_group_tag_value_2"
    )

    response = resource_groups.get_tags(Arn=response["Arn"])
    response["Tags"].should.have.length_of(2)
    response["Tags"]["resource_group_tag_key_2"].should.contain(
        "resource_group_tag_value_2"
    )


@mock_resourcegroups
def test_untag():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    response = test_get_tags()

    response = resource_groups.untag(
        Arn=response["Arn"], Keys=["resource_group_tag_key"]
    )
    response["Keys"].should.contain("resource_group_tag_key")

    response = resource_groups.get_tags(Arn=response["Arn"])
    response["Tags"].should.have.length_of(0)


@mock_resourcegroups
def test_update_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    test_get_group()

    response = resource_groups.update_group(
        GroupName="test_resource_group", Description="description_2"
    )
    response["Group"]["Description"].should.contain("description_2")

    response = resource_groups.get_group(GroupName="test_resource_group")
    response["Group"]["Description"].should.contain("description_2")


@mock_resourcegroups
def test_update_group_query():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    test_create_group()

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
