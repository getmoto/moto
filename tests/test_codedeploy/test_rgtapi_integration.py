import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

REGION = "us-west-2"
SERVICE_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/CodeDeployDemoRole"


def application_arn(name: str) -> str:
    return f"arn:aws:codedeploy:{REGION}:{ACCOUNT_ID}:application:{name}"


def deployment_group_arn(app_name: str, dg_name: str) -> str:
    return (
        f"arn:aws:codedeploy:{REGION}:{ACCOUNT_ID}:deploymentgroup:{app_name}/{dg_name}"
    )


@mock_aws
def test_resourcegroupstaggingapi_get_codedeploy_resources():
    client = boto3.client("codedeploy", region_name=REGION)
    tagging = boto3.client("resourcegroupstaggingapi", region_name=REGION)
    client.create_application(
        applicationName="app",
        computePlatform="Server",
        tags=[{"Key": "env", "Value": "test"}],
    )
    client.create_deployment_group(
        applicationName="app",
        deploymentGroupName="dg",
        serviceRoleArn=SERVICE_ROLE_ARN,
        tags=[{"Key": "team", "Value": "platform"}],
    )
    client.create_deployment_group(
        applicationName="app",
        deploymentGroupName="dg-env",
        serviceRoleArn=SERVICE_ROLE_ARN,
        tags=[{"Key": "env", "Value": "test"}],
    )
    client.create_application(applicationName="untagged", computePlatform="Server")
    client.create_deployment_group(
        applicationName="untagged",
        deploymentGroupName="untagged-dg",
        serviceRoleArn=SERVICE_ROLE_ARN,
    )
    app_arn = application_arn("app")
    dg_arn = deployment_group_arn("app", "dg")
    dg_env_arn = deployment_group_arn("app", "dg-env")

    resources = tagging.get_resources()["ResourceTagMappingList"]
    assert {r["ResourceARN"] for r in resources} == {app_arn, dg_arn, dg_env_arn}

    # Filter by type
    assert [
        r["ResourceARN"]
        for r in tagging.get_resources(ResourceTypeFilters=["codedeploy:application"])[
            "ResourceTagMappingList"
        ]
    ] == [app_arn]
    assert {
        r["ResourceARN"]
        for r in tagging.get_resources(
            ResourceTypeFilters=["codedeploy:deploymentgroup"]
        )["ResourceTagMappingList"]
    } == {dg_arn, dg_env_arn}

    # Filter by Tag
    assert {
        r["ResourceARN"]
        for r in tagging.get_resources(TagFilters=[{"Key": "env", "Values": ["test"]}])[
            "ResourceTagMappingList"
        ]
    } == {app_arn, dg_env_arn}


@mock_aws
def test_resourcegroupstaggingapi_tag_and_untag_codedeploy_resources():
    client = boto3.client("codedeploy", region_name=REGION)
    tagging = boto3.client("resourcegroupstaggingapi", region_name=REGION)
    client.create_application(
        applicationName="app",
        computePlatform="Server",
        tags=[{"Key": "env", "Value": "test"}],
    )
    client.create_deployment_group(
        applicationName="app",
        deploymentGroupName="dg",
        serviceRoleArn=SERVICE_ROLE_ARN,
    )
    app_arn = application_arn("app")
    dg_arn = deployment_group_arn("app", "dg")

    # Only the application is tagged initially
    assert [
        r["ResourceARN"] for r in tagging.get_resources()["ResourceTagMappingList"]
    ] == [app_arn]

    # Tag all resources through the Resource Groups Tagging API
    resp = tagging.tag_resources(
        ResourceARNList=[app_arn, dg_arn], Tags={"team": "data", "owner": "alice"}
    )
    assert resp["FailedResourcesMap"] == {}

    assert client.list_tags_for_resource(ResourceArn=app_arn)["Tags"] == [
        {"Key": "env", "Value": "test"},
        {"Key": "team", "Value": "data"},
        {"Key": "owner", "Value": "alice"},
    ]
    assert client.list_tags_for_resource(ResourceArn=dg_arn)["Tags"] == [
        {"Key": "team", "Value": "data"},
        {"Key": "owner", "Value": "alice"},
    ]
    assert {
        r["ResourceARN"]
        for r in tagging.get_resources(
            TagFilters=[{"Key": "team", "Values": ["data"]}]
        )["ResourceTagMappingList"]
    } == {app_arn, dg_arn}

    # Untag through the Resource Groups Tagging API
    resp = tagging.untag_resources(
        ResourceARNList=[app_arn, dg_arn], TagKeys=["team", "owner"]
    )
    assert resp["FailedResourcesMap"] == {}

    assert client.list_tags_for_resource(ResourceArn=app_arn)["Tags"] == [
        {"Key": "env", "Value": "test"}
    ]
    assert client.list_tags_for_resource(ResourceArn=dg_arn)["Tags"] == []
    assert [
        r["ResourceARN"] for r in tagging.get_resources()["ResourceTagMappingList"]
    ] == [app_arn]
