"""Unit tests for codedeploy-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_application():
    client = boto3.client("codedeploy", region_name="ap-southeast-1")
    for platform in ["Server", "Lambda", "ECS"]:
        name = f"test-application-{platform}"
        response = client.create_application(
            applicationName=name,
            computePlatform=platform,
            tags=[{"Key": "Name", "Value": "Test"}],
        )
        assert "applicationId" in response

        resp = client.get_application(applicationName=name)
        application = resp["application"]
        assert application["applicationId"] == response["applicationId"]
        assert application["applicationName"] == name
        assert application["computePlatform"] == platform
        assert "createTime" in application


@mock_aws
def test_create_application_existing():
    client = boto3.client("codedeploy", region_name="ap-southeast-1")

    response = client.create_application(
        applicationName="sample_app", computePlatform="Server"
    )
    assert "applicationId" in response

    with pytest.raises(ClientError) as exc:
        response = client.create_application(
            applicationName="sample_app", computePlatform="Server"
        )
    assert exc.value.response["Error"]["Code"] == "ApplicationAlreadyExistsException"


@mock_aws
def test_create_deployment_group_required():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    application_name = "mytestapp"
    client.create_application(
        applicationName=application_name, computePlatform="Lambda"
    )

    with pytest.raises(ClientError) as exc:
        client.create_deployment(applicationName=application_name)
    assert exc.value.response["Error"]["Code"] == "DeploymentGroupNameRequiredException"


@mock_aws
def test_create_deployment_revision_s3():
    client = boto3.client("codedeploy", region_name="us-west-2")

    application_name = "mytestapp"
    compute_platform = "Server"
    deployment_group_name = "test-deployment-group"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"
    description = "Test deployment"

    # Create an application
    client.create_application(
        applicationName=application_name, computePlatform=compute_platform
    )

    # Create a deployment group
    client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        serviceRoleArn=service_role_arn,
    )

    revision_S3 = {
        "revisionType": "S3",
        "s3Location": {
            "bucket": "my-bucket",
            "key": "my-key",
            "bundleType": "zip",
            "version": "1",
            "eTag": "my-etag",
        },
    }

    response = client.create_deployment(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        revision=revision_S3,
        description=description,
    )
    deployment_id = response["deploymentId"]

    # Get the deployment
    response = client.get_deployment(deploymentId=deployment_id)

    assert "deploymentInfo" in response
    assert response["deploymentInfo"]["applicationName"] == application_name
    assert response["deploymentInfo"]["revision"]["revisionType"] == "S3"
    assert (
        response["deploymentInfo"]["revision"]["s3Location"]
        == revision_S3["s3Location"]
    )
    assert response["deploymentInfo"]["status"] == "Created"
    assert "createTime" in response["deploymentInfo"]


@mock_aws
def test_create_deployment_revision_github():
    client = boto3.client("codedeploy", region_name="us-west-2")

    application_name = "mytestapp-2"
    compute_platform = "Server"
    deployment_group_name = "test-deployment-group"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"
    description = "Test deployment"

    # Create an application
    client.create_application(
        applicationName=application_name, computePlatform=compute_platform
    )

    # Create a deployment group
    client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        serviceRoleArn=service_role_arn,
    )

    revision_github = {
        "revisionType": "GitHub",
        "gitHubLocation": {
            "repository": "MyGitHubUserName/CodeDeployGitHubDemo",
            "commitId": "1234567890abcdef1234567890abcdef12345678",
        },
    }

    response = client.create_deployment(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        revision=revision_github,
        description=description,
    )
    deployment_id = response["deploymentId"]

    # Get the deployment
    response = client.get_deployment(deploymentId=deployment_id)
    assert "deploymentInfo" in response
    assert response["deploymentInfo"]["applicationName"] == application_name
    assert response["deploymentInfo"]["revision"]["revisionType"] == "GitHub"
    assert (
        response["deploymentInfo"]["revision"]["gitHubLocation"]
        == revision_github["gitHubLocation"]
    )
    assert response["deploymentInfo"]["status"] == "Created"
    assert "createTime" in response["deploymentInfo"]


@mock_aws
def test_create_deployment_nonexistent_app():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_deployment(applicationName="nonexistent-app")
    assert exc.value.response["Error"]["Code"] == "ApplicationDoesNotExistException"


@mock_aws
def test_create_deployment_nonexistent_group():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    application_name = "mytestapp"

    client.create_application(
        applicationName=application_name, computePlatform="Lambda"
    )

    with pytest.raises(ClientError) as exc:
        client.create_deployment(
            applicationName=application_name,
            deploymentGroupName="non-existent-group-name",
            revision={
                "revisionType": "S3",
                "s3Location": {
                    "bucket": "my-bucket",
                    "key": "my-key",
                    "bundleType": "zip",
                    "version": "1",
                    "eTag": "my-etag",
                },
            },
        )
    assert exc.value.response["Error"]["Code"] == "DeploymentGroupDoesNotExistException"


@mock_aws
def test_create_deployment_group():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    application_name = "mytestapp"
    deployment_group_name = "mytestdeploymentgroup"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"

    client.create_application(
        applicationName=application_name, computePlatform="Lambda"
    )

    response = client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        serviceRoleArn=service_role_arn,
    )

    assert "deploymentGroupId" in response


@mock_aws
def test_create_deployment_group_app_nonexistent():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    deployment_group_name = "mytestdeploymentgroup"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"

    with pytest.raises(ClientError) as exc:
        client.create_deployment_group(
            applicationName="nonexistent-app-name",
            deploymentGroupName=deployment_group_name,
            serviceRoleArn=service_role_arn,
        )
    assert exc.value.response["Error"]["Code"] == "ApplicationDoesNotExistException"


@mock_aws
def test_create_deployment_group_existing():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    application_name = "mytestapp"
    deployment_group_name = "mytestdeploymentgroup"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"

    client.create_application(
        applicationName=application_name, computePlatform="Lambda"
    )

    client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        serviceRoleArn=service_role_arn,
    )

    with pytest.raises(ClientError) as exc:
        client.create_deployment_group(
            applicationName=application_name,
            deploymentGroupName=deployment_group_name,
            serviceRoleArn=service_role_arn,
        )
    assert (
        exc.value.response["Error"]["Code"] == "DeploymentGroupAlreadyExistsException"
    )


@mock_aws
def test_get_deployment():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    application_name = "mytestapp"
    deployment_group_name = "mytestdeploymentgroup"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"

    client.create_application(
        applicationName=application_name, computePlatform="Lambda"
    )
    client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        serviceRoleArn=service_role_arn,
    )
    revision_content = "test-content"
    revision_sha256 = "test-sha256"
    description = "Test deployment"
    deployment_response = client.create_deployment(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        description=description,
        revision={
            "revisionType": "String",
            "string": {"content": revision_content, "sha256": revision_sha256},
        },
    )
    deployment_id = deployment_response["deploymentId"]

    response = client.get_deployment(deploymentId=deployment_id)
    assert "deploymentInfo" in response
    assert response["deploymentInfo"]["deploymentId"] == deployment_id
    assert response["deploymentInfo"]["applicationName"] == application_name
    assert response["deploymentInfo"]["deploymentGroupName"] == deployment_group_name
    assert response["deploymentInfo"]["deploymentId"] == deployment_id
    assert response["deploymentInfo"]["description"] == description
    assert response["deploymentInfo"]["revision"]["revisionType"] == "String"
    assert (
        response["deploymentInfo"]["revision"]["string"]["content"] == revision_content
    )
    assert response["deploymentInfo"]["revision"]["string"]["sha256"] == revision_sha256
    assert response["deploymentInfo"]["status"] == "Created"
    assert "createTime" in response["deploymentInfo"]


@mock_aws
def test_get_deployment_nonexistent_deployment():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.get_deployment(deploymentId="nonexistent-deployment-id")
    assert exc.value.response["Error"]["Code"] == "DeploymentDoesNotExistException"


@mock_aws
def test_get_deployment_group():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    application_name = "mytestapp"
    deployment_group_name = "mytestdeploymentgroup"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"

    client.create_application(
        applicationName=application_name, computePlatform="Lambda"
    )
    client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        serviceRoleArn=service_role_arn,
    )

    response = client.get_deployment_group(
        applicationName=application_name, deploymentGroupName=deployment_group_name
    )
    assert "deploymentGroupInfo" in response
    deployment_group_info = response["deploymentGroupInfo"]

    # required fields
    assert deployment_group_info["applicationName"] == application_name
    assert deployment_group_info["deploymentGroupName"] == deployment_group_name
    assert deployment_group_info["serviceRoleArn"] == service_role_arn

    # TODO assert other fields to be added
    # assert "alarmConfiguration" in deployment_group_info


@mock_aws
def test_get_deployment_group_nonexistent_app():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.get_deployment_group(
            applicationName="nonexistent-app-name",
            deploymentGroupName="mytestdeploymentgroup",
        )
    assert exc.value.response["Error"]["Code"] == "ApplicationDoesNotExistException"


@mock_aws
def test_get_deployment_group_nonexistent_group():
    client = boto3.client("codedeploy", region_name="eu-west-1")
    application_name = "mytestapp"

    client.create_application(
        applicationName=application_name, computePlatform="Lambda"
    )

    with pytest.raises(ClientError) as exc:
        client.get_deployment_group(
            applicationName=application_name,
            deploymentGroupName="nonexistent-group-name",
        )
    assert exc.value.response["Error"]["Code"] == "DeploymentGroupDoesNotExistException"


@mock_aws
def test_batch_get_applications_invalid_name():
    client = boto3.client("codedeploy", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.batch_get_applications(applicationNames=["app_does_not_exist"])
    assert exc.value.response["Error"]["Code"] == "ApplicationDoesNotExistException"


@mock_aws
def test_batch_get_applications():
    client = boto3.client("codedeploy", region_name="us-east-2")
    client.create_application(applicationName="sample_app1", computePlatform="Lambda")
    client.create_application(applicationName="sample_app2", computePlatform="Server")
    client.create_application(applicationName="sample_app3", computePlatform="ECS")

    resp = client.batch_get_applications(
        applicationNames=["sample_app1", "sample_app2", "sample_app3"]
    )

    assert len(resp["applicationsInfo"]) == 3


@mock_aws
def test_batch_get_deployments():
    client = boto3.client("codedeploy", region_name="us-east-2")

    deployment_ids = []
    # create 2 deployments
    for i in range(0, 2):
        application_name = f"sample_app{i}"
        deployment_group_name = f"sample_deployment_group{i}"
        service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"
        client.create_application(
            applicationName=application_name, computePlatform="Server"
        )
        client.create_deployment_group(
            applicationName=application_name,
            deploymentGroupName=deployment_group_name,
            serviceRoleArn=service_role_arn,
        )

        resp = client.create_deployment(
            applicationName=application_name,
            deploymentGroupName=deployment_group_name,
            revision={
                "revisionType": "S3",
                "s3Location": {
                    "bucket": "my-bucket",
                    "key": "my-key",
                    "bundleType": "zip",
                    "version": "1",
                    "eTag": "my-etag",
                },
            },
        )

        deployment_ids.append(resp["deploymentId"])

    resp = client.batch_get_deployments(deploymentIds=deployment_ids)
    assert len(resp["deploymentsInfo"]) == len(deployment_ids)


@mock_aws
def test_list_applications():
    client = boto3.client("codedeploy", region_name="us-east-2")
    resp = client.list_applications()
    assert len(resp["applications"]) == 0

    client.create_application(applicationName="sample_app", computePlatform="Server")
    client.create_application(applicationName="sample_app2", computePlatform="Server")
    resp = client.list_applications()
    assert len(resp["applications"]) == 2


@mock_aws
def test_list_deployments():
    client = boto3.client("codedeploy", region_name="ap-southeast-1")
    application_name = "mytestapp"
    deployment_group_name = "mytestdeploymentgroup"
    deployment_group_name2 = "mytestdeploymentgroup2"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"

    resp = client.list_deployments()
    assert len(resp["deployments"]) == 0

    client.create_application(
        applicationName=application_name, computePlatform="Server"
    )
    client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        serviceRoleArn=service_role_arn,
    )

    client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name2,
        serviceRoleArn=service_role_arn,
    )
    client.create_deployment(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        revision={
            "revisionType": "S3",
            "s3Location": {
                "bucket": "my-bucket",
                "key": "my-key",
                "bundleType": "zip",
                "version": "1",
                "eTag": "my-etag",
            },
        },
    )

    client.create_deployment(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name2,
        revision={
            "revisionType": "S3",
            "s3Location": {
                "bucket": "my-bucket",
                "key": "my-key",
                "bundleType": "zip",
                "version": "1",
                "eTag": "my-etag",
            },
        },
    )

    resp = client.list_deployments()
    assert len(resp["deployments"]) == 2


@mock_aws
def test_list_deployments_group_required():
    client = boto3.client("codedeploy", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.list_deployments(applicationName="mytestapp")
    assert exc.value.response["Error"]["Code"] == "DeploymentGroupNameRequiredException"


@mock_aws
def test_list_deployments_app_required():
    client = boto3.client("codedeploy", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.list_deployments(deploymentGroupName="mygroupname")
    assert exc.value.response["Error"]["Code"] == "ApplicationNameRequiredException"


@mock_aws
def test_list_deployment_groups():
    client = boto3.client("codedeploy", region_name="ap-southeast-1")

    application_name = "mytestapp"
    deployment_group_name = "mytestdeploymentgroup"
    deployment_group_name2 = "mytestdeploymentgroup2"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"

    resp = client.list_deployment_groups(applicationName=application_name)
    assert len(resp["deploymentGroups"]) == 0

    client.create_application(
        applicationName=application_name, computePlatform="Server"
    )
    client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name,
        serviceRoleArn=service_role_arn,
    )

    client.create_deployment_group(
        applicationName=application_name,
        deploymentGroupName=deployment_group_name2,
        serviceRoleArn=service_role_arn,
    )

    resp = client.list_deployment_groups(applicationName=application_name)
    assert len(resp["deploymentGroups"]) == 2


@mock_aws
def test_application_tagging():
    client = boto3.client("codedeploy", region_name="us-west-2")
    app_name = "test-tag-application"
    initial_tags = [{"Key": "Environment", "Value": "Test"}]

    response = client.create_application(
        applicationName=app_name, computePlatform="Server", tags=initial_tags
    )

    app_arn = f"arn:aws:codedeploy:us-west-2:123456789012:application:{app_name}"

    response = client.list_tags_for_resource(ResourceArn=app_arn)
    assert "Tags" in response
    assert len(response["Tags"]) == 1
    assert response["Tags"][0]["Key"] == "Environment"
    assert response["Tags"][0]["Value"] == "Test"


@mock_aws
def test_deployment_group_tagging():
    client = boto3.client("codedeploy", region_name="us-west-2")
    app_name = "test-tag-dg-app"
    dg_name = "test-tag-deployment-group"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"

    client.create_application(applicationName=app_name, computePlatform="Server")

    initial_tags = [{"Key": "Team", "Value": "Platform"}]
    response = client.create_deployment_group(
        applicationName=app_name,
        deploymentGroupName=dg_name,
        serviceRoleArn=service_role_arn,
        tags=initial_tags,
    )

    dg_arn = f"arn:aws:codedeploy:us-west-2:123456789012:deploymentgroup:{app_name}/{dg_name}"

    response = client.list_tags_for_resource(ResourceArn=dg_arn)
    assert "Tags" in response
    assert len(response["Tags"]) == 1
    assert response["Tags"][0]["Key"] == "Team"
    assert response["Tags"][0]["Value"] == "Platform"


@mock_aws
def test_deployment_inherits_tags():
    """Test that deployments inherit tags from deployment groups."""
    client = boto3.client("codedeploy", region_name="us-west-2")
    app_name = "test-tag-inherit-app"
    dg_name = "test-tag-inherit-group"
    service_role_arn = "arn:aws:iam::123456789012:role/CodeDeployDemoRole"

    client.create_application(applicationName=app_name, computePlatform="Server")

    dg_tags = [{"Key": "Environment", "Value": "Production"}]
    client.create_deployment_group(
        applicationName=app_name,
        deploymentGroupName=dg_name,
        serviceRoleArn=service_role_arn,
        tags=dg_tags,
    )

    response = client.create_deployment(
        applicationName=app_name,
        deploymentGroupName=dg_name,
        revision={
            "revisionType": "S3",
            "s3Location": {
                "bucket": "my-bucket",
                "key": "my-key",
                "bundleType": "zip",
                "version": "1",
                "eTag": "my-etag",
            },
        },
    )
    deployment_id = response["deploymentId"]

    deployment_arn = (
        f"arn:aws:codedeploy:us-west-2:123456789012:deployment:{deployment_id}"
    )

    response = client.list_tags_for_resource(ResourceArn=deployment_arn)
    assert "Tags" in response
    assert len(response["Tags"]) == 1
