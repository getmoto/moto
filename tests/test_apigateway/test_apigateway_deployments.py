import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from .test_apigateway import create_method_integration


@mock_aws
def test_create_deployment_requires_REST_methods():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    with pytest.raises(ClientError) as ex:
        client.create_deployment(restApiId=api_id, stageName=stage_name)["id"]
    assert ex.value.response["Error"]["Code"] == "BadRequestException"
    assert (
        ex.value.response["Error"]["Message"]
        == "The REST API doesn't contain any methods"
    )


@mock_aws
def test_create_deployment_requires_REST_method_integrations():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    resources = client.get_resources(restApiId=api_id)
    root_id = [r for r in resources["items"] if r["path"] == "/"][0]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="NONE"
    )

    with pytest.raises(ClientError) as ex:
        client.create_deployment(restApiId=api_id, stageName=stage_name)["id"]
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["Error"]["Message"] == "No integration defined for method"


@mock_aws
def test_create_simple_deployment_with_get_method():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    deployment = client.create_deployment(restApiId=api_id, stageName=stage_name)
    assert "id" in deployment


@mock_aws
def test_create_simple_deployment_with_post_method():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id, httpMethod="POST")

    deployment = client.create_deployment(restApiId=api_id, stageName=stage_name)
    assert "id" in deployment


@mock_aws
def test_create_deployment_minimal():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    response = client.get_deployment(restApiId=api_id, deploymentId=deployment_id)
    assert response["id"] == deployment_id
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_create_deployment_with_empty_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    response = client.create_deployment(restApiId=api_id, stageName="")
    deployment_id = response["id"]

    response = client.get_deployment(restApiId=api_id, deploymentId=deployment_id)
    assert "id" in response
    assert "createdDate" in response
    assert "stageName" not in response

    # This should not create an empty stage
    stages = client.get_stages(restApiId=api_id)["item"]
    assert stages == []


@mock_aws
def test_get_deployments():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    response = client.get_deployments(restApiId=api_id)
    assert len(response["items"]) == 1

    response["items"][0].pop("createdDate")
    assert response["items"] == [{"id": deployment_id}]


@mock_aws
def test_create_multiple_deployments():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    create_method_integration(client, api_id)
    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    response = client.get_deployment(restApiId=api_id, deploymentId=deployment_id)

    response = client.create_deployment(restApiId=api_id, stageName=stage_name)

    deployment_id2 = response["id"]

    response = client.get_deployments(restApiId=api_id)

    assert response["items"][0]["id"] in [deployment_id, deployment_id2]
    assert response["items"][1]["id"] in [deployment_id, deployment_id2]


@mock_aws
def test_delete_deployment__requires_stage_to_be_deleted():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    # Can't delete deployment immediately
    with pytest.raises(ClientError) as exc:
        client.delete_deployment(restApiId=api_id, deploymentId=deployment_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert (
        err["Message"]
        == "Active stages pointing to this deployment must be moved or deleted"
    )

    # Deployment still exists
    deployments = client.get_deployments(restApiId=api_id)["items"]
    assert len(deployments) == 1

    # Stage still exists
    stages = client.get_stages(restApiId=api_id)["item"]
    assert len(stages) == 1

    # Delete stage first
    resp = client.delete_stage(restApiId=api_id, stageName=stage_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 202

    # Deployment still exists
    deployments = client.get_deployments(restApiId=api_id)["items"]
    assert len(deployments) == 1

    # Now delete deployment
    resp = client.delete_deployment(restApiId=api_id, deploymentId=deployment_id)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 202

    # Deployment is gone
    deployments = client.get_deployments(restApiId=api_id)["items"]
    assert len(deployments) == 0

    # Stage is gone
    stages = client.get_stages(restApiId=api_id)["item"]
    assert len(stages) == 0


@mock_aws
def test_delete_unknown_deployment():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    with pytest.raises(ClientError) as exc:
        client.delete_deployment(restApiId=api_id, deploymentId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid Deployment identifier specified"
