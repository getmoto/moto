import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigateway

from .test_apigateway import create_method_integration


@mock_apigateway
def test_create_stage_minimal():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    create_method_integration(client, api_id)
    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    new_stage_name = "current"
    response = client.create_stage(
        restApiId=api_id, stageName=new_stage_name, deploymentId=deployment_id
    )

    assert response["stageName"] == new_stage_name
    assert response["deploymentId"] == deployment_id
    assert response["methodSettings"] == {}
    assert response["variables"] == {}
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert response["description"] == ""
    assert "cacheClusterStatus" not in response
    assert response["cacheClusterEnabled"] is False

    stage = client.get_stage(restApiId=api_id, stageName=new_stage_name)
    assert stage["stageName"] == new_stage_name
    assert stage["deploymentId"] == deployment_id


@mock_apigateway
def test_create_stage_with_env_vars():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    create_method_integration(client, api_id)
    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    new_stage_name_with_vars = "stage_with_vars"
    response = client.create_stage(
        restApiId=api_id,
        stageName=new_stage_name_with_vars,
        deploymentId=deployment_id,
        variables={"env": "dev"},
    )

    assert response["stageName"] == new_stage_name_with_vars
    assert response["deploymentId"] == deployment_id
    assert response["methodSettings"] == {}
    assert response["variables"] == {"env": "dev"}
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert response["description"] == ""
    assert "cacheClusterStatus" not in response
    assert response["cacheClusterEnabled"] is False

    stage = client.get_stage(restApiId=api_id, stageName=new_stage_name_with_vars)
    assert stage["stageName"] == new_stage_name_with_vars
    assert stage["deploymentId"] == deployment_id
    assert stage["variables"]["env"] == "dev"


@mock_apigateway
def test_create_stage_with_vars_and_cache():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    create_method_integration(client, api_id)
    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    new_stage_name = "stage_with_vars_and_cache_settings"
    response = client.create_stage(
        restApiId=api_id,
        stageName=new_stage_name,
        deploymentId=deployment_id,
        variables={"env": "dev"},
        cacheClusterEnabled=True,
        description="hello moto",
    )

    assert response["stageName"] == new_stage_name
    assert response["deploymentId"] == deployment_id
    assert response["methodSettings"] == {}
    assert response["variables"] == {"env": "dev"}
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert response["description"] == "hello moto"
    assert response["cacheClusterStatus"] == "AVAILABLE"
    assert response["cacheClusterEnabled"] is True
    assert response["cacheClusterSize"] == "0.5"

    stage = client.get_stage(restApiId=api_id, stageName=new_stage_name)

    assert stage["cacheClusterSize"] == "0.5"


@mock_apigateway
def test_create_stage_with_cache_settings():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    create_method_integration(client, api_id)
    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    new_stage_name = "stage_with_vars_and_cache_settings_and_size"
    response = client.create_stage(
        restApiId=api_id,
        stageName=new_stage_name,
        deploymentId=deployment_id,
        variables={"env": "dev"},
        cacheClusterEnabled=True,
        cacheClusterSize="1.6",
        tracingEnabled=True,
        description="hello moto",
    )

    assert response["stageName"] == new_stage_name
    assert response["deploymentId"] == deployment_id
    assert response["methodSettings"] == {}
    assert response["variables"] == {"env": "dev"}
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert response["description"] == "hello moto"
    assert response["cacheClusterStatus"] == "AVAILABLE"
    assert response["cacheClusterEnabled"] is True
    assert response["cacheClusterSize"] == "1.6"
    assert response["tracingEnabled"] is True

    stage = client.get_stage(restApiId=api_id, stageName=new_stage_name)
    assert stage["stageName"] == new_stage_name
    assert stage["deploymentId"] == deployment_id
    assert stage["variables"]["env"] == "dev"
    assert stage["cacheClusterSize"] == "1.6"


@mock_apigateway
def test_recreate_stage_from_deployment():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)
    depl_id1 = client.create_deployment(restApiId=api_id, stageName=stage_name)["id"]

    with pytest.raises(ClientError) as exc:
        client.create_stage(
            restApiId=api_id, stageName=stage_name, deploymentId=depl_id1
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert err["Message"] == "Stage already exists"


@mock_apigateway
def test_create_stage_twice():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)
    depl_id1 = client.create_deployment(restApiId=api_id, stageName=stage_name)["id"]

    new_stage_name = "current"
    client.create_stage(
        restApiId=api_id, stageName=new_stage_name, deploymentId=depl_id1
    )

    with pytest.raises(ClientError) as exc:
        client.create_stage(
            restApiId=api_id, stageName=new_stage_name, deploymentId=depl_id1
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert err["Message"] == "Stage already exists"


@mock_apigateway
def test_delete_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)
    depl_id1 = client.create_deployment(restApiId=api_id, stageName=stage_name)["id"]
    depl_id2 = client.create_deployment(restApiId=api_id, stageName=stage_name)["id"]

    new_stage_name = "current"
    client.create_stage(
        restApiId=api_id, stageName=new_stage_name, deploymentId=depl_id1
    )

    new_stage_name_with_vars = "stage_with_vars"
    client.create_stage(
        restApiId=api_id,
        stageName=new_stage_name_with_vars,
        deploymentId=depl_id2,
        variables={"env": "dev"},
    )
    stages = client.get_stages(restApiId=api_id)["item"]
    stage_names = [stage["stageName"] for stage in stages]
    assert len(stage_names) == 3
    assert stage_name in stage_names
    assert new_stage_name in stage_names
    assert new_stage_name_with_vars in stage_names

    # delete stage
    response = client.delete_stage(restApiId=api_id, stageName=new_stage_name_with_vars)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 202

    # verify other stage still exists
    stages = client.get_stages(restApiId=api_id)["item"]
    stage_names = [stage["stageName"] for stage in stages]
    assert len(stage_names) == 2
    assert new_stage_name_with_vars not in stage_names


@mock_apigateway
def test_delete_stage_created_by_deployment():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)
    depl_id1 = client.create_deployment(restApiId=api_id, stageName=stage_name)["id"]

    # Sanity check that the deployment exists
    depls = client.get_deployments(restApiId=api_id)["items"]
    assert len(depls) == 1
    assert set(depls[0].keys()) == {"id", "createdDate"}

    # Sanity check that the stage exists
    stage = client.get_stages(restApiId=api_id)["item"][0]
    assert stage["deploymentId"] == depl_id1
    assert stage["stageName"] == stage_name

    # delete stage
    response = client.delete_stage(restApiId=api_id, stageName=stage_name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 202

    # verify no stage exists
    stages = client.get_stages(restApiId=api_id)
    assert stages["item"] == []

    # verify deployment still exists, unchanged
    depls = client.get_deployments(restApiId=api_id)["items"]
    assert len(depls) == 1
    assert set(depls[0].keys()) == {"id", "createdDate"}


@mock_apigateway
def test_delete_stage_unknown_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    with pytest.raises(ClientError) as exc:
        client.delete_stage(restApiId=api_id, stageName="unknown")
    err = exc.value.response["Error"]
    assert err["Message"] == "Invalid stage identifier specified"
    assert err["Code"] == "NotFoundException"


@mock_apigateway
def test_update_stage_configuration():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    response = client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )
    deployment_id = response["id"]

    response = client.get_deployment(restApiId=api_id, deploymentId=deployment_id)

    assert response["id"] == deployment_id
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["description"] == "1.0.1"

    response = client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.2"
    )
    deployment_id2 = response["id"]

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)
    assert stage["stageName"] == stage_name
    assert stage["deploymentId"] == deployment_id2
    assert "cacheClusterSize" not in stage
    assert "cacheClusterStatus" not in stage

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "replace", "path": "/cacheClusterEnabled", "value": "True"}
        ],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)

    assert stage["cacheClusterSize"] == "0.5"
    assert stage["cacheClusterStatus"] == "AVAILABLE"

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "replace", "path": "/cacheClusterSize", "value": "1.6"}
        ],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)

    assert stage["cacheClusterSize"] == "1.6"

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "replace", "path": "/deploymentId", "value": deployment_id},
            {"op": "replace", "path": "/variables/environment", "value": "dev"},
            {"op": "replace", "path": "/variables/region", "value": "eu-west-1"},
            {"op": "replace", "path": "/*/*/caching/dataEncrypted", "value": "True"},
            {"op": "replace", "path": "/cacheClusterEnabled", "value": "True"},
            {
                "op": "replace",
                "path": "/description",
                "value": "stage description update",
            },
            {"op": "replace", "path": "/cacheClusterSize", "value": "1.6"},
        ],
    )

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "remove", "path": "/variables/region", "value": "eu-west-1"}
        ],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)

    assert stage["description"] == "stage description update"
    assert stage["cacheClusterSize"] == "1.6"
    assert stage["variables"]["environment"] == "dev"
    assert "region" not in stage["variables"]
    assert stage["cacheClusterEnabled"] is True
    assert stage["deploymentId"] == deployment_id
    assert "*/*" in stage["methodSettings"]
    assert stage["methodSettings"]["*/*"]["cacheDataEncrypted"] is True


@mock_apigateway
def test_update_stage_add_access_log_settings():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {
                "op": "replace",
                "path": "/accessLogSettings/destinationArn",
                "value": "arn:aws:logs:us-east-1:123456789012:log-group:foo-bar-x0hyv",
            },
            {
                "op": "replace",
                "path": "/accessLogSettings/format",
                "value": "$context.identity.sourceIp msg",
            },
        ],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)
    assert stage["accessLogSettings"] == {
        "format": "$context.identity.sourceIp msg",
        "destinationArn": "arn:aws:logs:us-east-1:123456789012:log-group:foo-bar-x0hyv",
    }


@mock_apigateway
def test_update_stage_tracing_disabled():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)
    response = client.create_deployment(restApiId=api_id, stageName=stage_name)

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "replace", "path": "/tracingEnabled", "value": "false"}
        ],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)
    assert stage["tracingEnabled"] is False

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[{"op": "replace", "path": "/tracingEnabled", "value": "true"}],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)
    assert stage["tracingEnabled"] is True


@mock_apigateway
def test_update_stage_remove_access_log_settings():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[{"op": "remove", "path": "/accessLogSettings"}],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)
    assert "accessLogSettings" not in stage


@mock_apigateway
def test_update_stage_configuration_unknown_operation():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )

    with pytest.raises(ClientError) as exc:
        client.update_stage(
            restApiId=api_id,
            stageName=stage_name,
            patchOperations=[
                {"op": "unknown_op", "path": "/notasetting", "value": "eu-west-1"}
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Member must satisfy enum value set: [add, remove, move, test, replace, copy]"
    )


@mock_apigateway
def test_non_existent_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    with pytest.raises(ClientError) as exc:
        client.get_stage(restApiId=api_id, stageName="xxx")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
