import boto3
import pytest

from moto import mock_aws, settings
from moto.apigateway.utils import (
    ApigwApiKeyIdentifier,
    ApigwDeploymentIdentifier,
    ApigwModelIdentifier,
    ApigwRequestValidatorIdentifier,
    ApigwResourceIdentifier,
    ApigwRestApiIdentifier,
    ApigwUsagePlanIdentifier,
)

API_ID = "ApiId"
API_KEY_ID = "ApiKeyId"
DEPLOYMENT_ID = "DeployId"
MODEL_ID = "ModelId"
PET_1_RESOURCE_ID = "Pet1Id"
PET_2_RESOURCE_ID = "Pet2Id"
REQUEST_VALIDATOR_ID = "ReqValId"
ROOT_RESOURCE_ID = "RootId"
USAGE_PLAN_ID = "UPlanId"


@mock_aws
@pytest.mark.skipif(
    not settings.TEST_DECORATOR_MODE, reason="Can't access the id manager in proxy mode"
)
def test_custom_id_rest_api(set_custom_id, account_id):
    region_name = "us-west-2"
    rest_api_name = "my-api"
    model_name = "modelName"
    request_validator_name = "request-validator-name"
    stage_name = "stage-name"

    client = boto3.client("apigateway", region_name=region_name)

    set_custom_id(
        ApigwRestApiIdentifier(account_id, region_name, rest_api_name), API_ID
    )
    set_custom_id(
        ApigwResourceIdentifier(account_id, region_name, path_name="/"),
        ROOT_RESOURCE_ID,
    )
    set_custom_id(
        ApigwResourceIdentifier(
            account_id, region_name, parent_id=ROOT_RESOURCE_ID, path_name="pet"
        ),
        PET_1_RESOURCE_ID,
    )
    set_custom_id(
        ApigwResourceIdentifier(
            account_id, region_name, parent_id=PET_1_RESOURCE_ID, path_name="pet"
        ),
        PET_2_RESOURCE_ID,
    )
    set_custom_id(ApigwModelIdentifier(account_id, region_name, model_name), MODEL_ID)
    set_custom_id(
        ApigwRequestValidatorIdentifier(
            account_id, region_name, request_validator_name
        ),
        REQUEST_VALIDATOR_ID,
    )
    set_custom_id(
        ApigwDeploymentIdentifier(account_id, region_name, stage_name=stage_name),
        DEPLOYMENT_ID,
    )

    rest_api = client.create_rest_api(name=rest_api_name)
    assert rest_api["id"] == API_ID
    assert rest_api["rootResourceId"] == ROOT_RESOURCE_ID

    pet_resource_1 = client.create_resource(
        restApiId=API_ID, parentId=ROOT_RESOURCE_ID, pathPart="pet"
    )
    assert pet_resource_1["id"] == PET_1_RESOURCE_ID

    # we create a second resource with the same path part to ensure we can pass different ids
    pet_resource_2 = client.create_resource(
        restApiId=API_ID, parentId=PET_1_RESOURCE_ID, pathPart="pet"
    )
    assert pet_resource_2["id"] == PET_2_RESOURCE_ID

    model = client.create_model(
        restApiId=API_ID,
        name=model_name,
        schema="EMPTY",
        contentType="application/json",
    )
    assert model["id"] == MODEL_ID

    request_validator = client.create_request_validator(
        restApiId=API_ID, name=request_validator_name
    )
    assert request_validator["id"] == REQUEST_VALIDATOR_ID

    # Creating the resource to make a deployment
    client.put_method(
        restApiId=API_ID,
        httpMethod="ANY",
        resourceId=PET_2_RESOURCE_ID,
        authorizationType="NONE",
    )
    client.put_integration(
        restApiId=API_ID, resourceId=PET_2_RESOURCE_ID, httpMethod="ANY", type="MOCK"
    )
    deployment = client.create_deployment(restApiId=API_ID, stageName=stage_name)
    assert deployment["id"] == DEPLOYMENT_ID


@mock_aws
@pytest.mark.skipif(
    not settings.TEST_DECORATOR_MODE, reason="Can't access the id manager in proxy mode"
)
def test_custom_id_api_key(account_id, set_custom_id):
    region_name = "us-west-2"
    api_key_value = "01234567890123456789"
    usage_plan_name = "usage-plan"

    client = boto3.client("apigateway", region_name=region_name)

    set_custom_id(
        ApigwApiKeyIdentifier(account_id, region_name, value=api_key_value), API_KEY_ID
    )
    set_custom_id(
        ApigwUsagePlanIdentifier(account_id, region_name, usage_plan_name),
        USAGE_PLAN_ID,
    )

    api_key = client.create_api_key(name="api-key", value=api_key_value)
    usage_plan = client.create_usage_plan(name=usage_plan_name)

    # verify that we can create a usage plan key using the custom ids
    client.create_usage_plan_key(
        usagePlanId=USAGE_PLAN_ID, keyId=API_KEY_ID, keyType="API_KEY"
    )

    assert api_key["id"] == API_KEY_ID
    assert usage_plan["id"] == USAGE_PLAN_ID
