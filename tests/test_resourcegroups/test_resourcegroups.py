from datetime import datetime
import json

import boto3
import pytest
from botocore.exceptions import ClientError

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
def test_delete_group_by_arn():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    response = create_group(client=resource_groups)
    group_arn = response["Group"]["GroupArn"]

    response = resource_groups.delete_group(GroupName=group_arn)
    assert group_arn == response["Group"]["GroupArn"]

    with pytest.raises(ClientError) as exc:
        resource_groups.get_group(GroupName=group_arn)
    error = exc.value.response["Error"]
    assert error["Code"] == "NotFoundException"


@mock_aws
def test_get_group():
    resource_groups = boto3.client("resource-groups", region_name="us-east-1")

    response = create_group(client=resource_groups)
    group_name = response["Group"]["Name"]
    group_arn = response["Group"]["GroupArn"]

    response = resource_groups.get_group(GroupName=group_name)
    assert response["Group"]["GroupArn"] == group_arn

    response = resource_groups.get_group(GroupName=group_arn)
    assert response["Group"]["Name"] == group_name


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


@mock_aws
def test_start_tag_sync_task():
    client = boto3.client("resource-groups", region_name="us-east-2")
    resource_group = create_group(client)["Group"]["GroupArn"]
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    tag_key = "foo"
    tag_value = "bar"
    role_arn = f"arn:aws:iam::{account_id}:role/role"
    resp = client.start_tag_sync_task(Group=resource_group,
                                      TagKey=tag_key,
                                      TagValue=tag_value,
                                      RoleArn=role_arn)
    assert "GroupArn" in resp
    assert resp["GroupArn"] == resource_group
    assert "GroupName" in resp
    assert resp["GroupName"] == resource_group.split("group/")[-1]
    assert "TaskArn" in resp
    assert "TagKey" in resp
    assert resp["TagKey"] == tag_key
    assert "TagValue" in resp
    assert resp["TagValue"] == tag_value
    assert "RoleArn" in resp
    assert resp["RoleArn"] == role_arn

@mock_aws
def test_start_tag_sync_task_with_name():
    client = boto3.client("resource-groups", region_name="us-east-2")
    resource_group = create_group(client)["Group"]["Name"]
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    tag_key = "foo"
    tag_value = "bar"
    role_arn = f"arn:aws:iam::{account_id}:role/role"
    resp = client.start_tag_sync_task(Group=resource_group,
                                      TagKey=tag_key,
                                      TagValue=tag_value,
                                      RoleArn=role_arn)
    assert "GroupArn" in resp
    assert resource_group in resp["GroupArn"]
    assert "GroupName" in resp
    assert resp["GroupName"] == resource_group
    assert "TaskArn" in resp
    assert "ResourceQuery" not in resp
    assert "TagKey" in resp
    assert resp["TagKey"] == tag_key
    assert "TagValue" in resp
    assert resp["TagValue"] == tag_value
    assert "RoleArn" in resp
    assert resp["RoleArn"] == role_arn

@mock_aws
def test_start_tag_sync_task_with_query():
    client = boto3.client("resource-groups", region_name="us-east-2")
    resource_group = create_group(client)["Group"]["Name"]
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    query = {"Type":"TAG_FILTERS_1.0", "Query":"bar"}
    role_arn = f"arn:aws:iam::{account_id}:role/role"
    resp = client.start_tag_sync_task(Group=resource_group,
                                      ResourceQuery=query,
                                      RoleArn=role_arn)
    assert "GroupArn" in resp
    assert resource_group in resp["GroupArn"]
    assert "GroupName" in resp
    assert resp["GroupName"] == resource_group
    assert "TaskArn" in resp
    assert "ResourceQuery" in resp
    assert resp["ResourceQuery"] == query
    assert "TagKey" not in resp
    assert "TagValue" not in resp
    assert "RoleArn" in resp
    assert resp["RoleArn"] == role_arn

@mock_aws
def test_start_tag_sync_task_with_with_query_and_tags():
    client = boto3.client("resource-groups", region_name="us-east-2")
    resource_group = create_group(client)["Group"]["Name"]
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    tag_key = "foo"
    tag_value = "bar"
    role_arn = f"arn:aws:iam::{account_id}:role/role"
    with pytest.raises(ClientError) as exc:
        client.start_tag_sync_task(Group=resource_group,
                                          TagKey=tag_key,
                                          TagValue=tag_value,
                                          ResourceQuery={"Type": "TAG_FILTERS_1_0",
                                                          "Query": tag_value},
                                          RoleArn=role_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert err["Message"] == "To define a task, you can use TagKey and TagValue with non-null values, or use a ResourceQuery"

@mock_aws
def test_list_tag_sync_tasks():
    client = boto3.client("resource-groups", region_name="us-east-2")
    resource_group = create_group(client)["Group"]["GroupArn"]
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    tag_key = "foo"
    tag_value = "bar"
    role_arn = f"arn:aws:iam::{account_id}:role/role"
    resp = client.start_tag_sync_task(Group=resource_group,
                                      TagKey=tag_key,
                                      TagValue=tag_value,
                                      RoleArn=role_arn)
    resp = client.list_tag_sync_tasks()

    assert "TagSyncTasks" in resp
    assert isinstance(resp["TagSyncTasks"], list)
    assert len(resp["TagSyncTasks"]) == 1
    assert "GroupArn" in resp["TagSyncTasks"][0]
    assert resp["TagSyncTasks"][0]["GroupArn"] == resource_group
    assert "GroupName" in resp["TagSyncTasks"][0]
    assert resp["TagSyncTasks"][0]["GroupName"] == resource_group.split("group/")[-1]
    assert "TaskArn" in resp["TagSyncTasks"][0]
    assert "TagKey" in resp["TagSyncTasks"][0]
    assert resp["TagSyncTasks"][0]["TagKey"] == tag_key
    assert "TagValue" in resp["TagSyncTasks"][0]
    assert resp["TagSyncTasks"][0]["TagValue"] == tag_value
    assert "RoleArn" in resp["TagSyncTasks"][0]
    assert resp["TagSyncTasks"][0]["RoleArn"] == role_arn
    assert "Status" in resp["TagSyncTasks"][0]
    assert resp["TagSyncTasks"][0]["Status"] in ["ACTIVE", "ERROR"]
    if resp["TagSyncTasks"][0]["Status"] == "ERROR":
        assert "ErrorMessage" in resp["TagSyncTasks"][0]
    assert "CreatedAt" in resp["TagSyncTasks"][0]
    assert isinstance(resp["TagSyncTasks"][0]["CreatedAt"], datetime)



@mock_aws
def test_cancel_tag_sync_task():
    client = boto3.client("resource-groups", region_name="us-east-2")
    resource_group = create_group(client)["Group"]["GroupArn"]
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    tag_key = "foo"
    tag_value = "bar"
    role_arn = f"arn:aws:iam::{account_id}:role/role"
    task_arn = client.start_tag_sync_task(Group=resource_group,
                                      TagKey=tag_key,
                                      TagValue=tag_value,
                                      RoleArn=role_arn)["TaskArn"]
    resp = client.cancel_tag_sync_task(TaskArn=task_arn)

    assert isinstance(resp, dict)

@mock_aws
def test_get_tag_sync_task():
    client = boto3.client("resource-groups", region_name="us-east-2")
    resource_group = create_group(client)["Group"]["GroupArn"]
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    tag_key = "foo"
    tag_value = "bar"
    role_arn = f"arn:aws:iam::{account_id}:role/role"
    task_arn = client.start_tag_sync_task(Group=resource_group,
                                      TagKey=tag_key,
                                      TagValue=tag_value,
                                      RoleArn=role_arn)["TaskArn"]
    resp = client.get_tag_sync_task(TaskArn=task_arn)


    assert "GroupArn" in resp
    assert resp["GroupArn"] == resource_group
    assert "GroupName" in resp
    assert resp["GroupName"] == resource_group.split("group/")[-1]
    assert "TaskArn" in resp
    assert "TagKey" in resp
    assert resp["TagKey"] == tag_key
    assert "TagValue" in resp
    assert resp["TagValue"] == tag_value
    assert "RoleArn" in resp
    assert resp["RoleArn"] == role_arn
    assert "Status" in resp
    assert resp["Status"] in ["ACTIVE", "ERROR"]
    if resp["Status"] == "ERROR":
        assert "ErrorMessage" in resp
    assert "CreatedAt" in resp
    assert isinstance(resp["CreatedAt"], datetime)

