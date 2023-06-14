import boto3
from moto import mock_apigateway
from botocore.exceptions import ClientError
import pytest

ID = "id"
NAME = "name"
VALIDATE_REQUEST_BODY = "validateRequestBody"
VALIDATE_REQUEST_PARAMETERS = "validateRequestParameters"
PARAM_NAME = "my-validator"
RESPONSE_METADATA = "ResponseMetadata"


@mock_apigateway
def test_create_request_validator():
    client = create_client()
    api_id = create_rest_api_id(client)
    response = create_validator(client, api_id)
    response.pop(RESPONSE_METADATA)
    response.pop(ID)
    assert response == {
        NAME: PARAM_NAME,
        VALIDATE_REQUEST_BODY: True,
        VALIDATE_REQUEST_PARAMETERS: True,
    }


@mock_apigateway
def test_get_request_validators():
    client = create_client()
    api_id = create_rest_api_id(client)
    response = client.get_request_validators(restApiId=api_id)

    validators = response["items"]
    assert len(validators) == 0

    response.pop(RESPONSE_METADATA)
    assert response == {"items": []}

    response = create_validator(client, api_id)
    validator_id1 = response[ID]
    response = create_validator(client, api_id)
    validator_id2 = response[ID]
    response = client.get_request_validators(restApiId=api_id)

    validators = response["items"]
    assert len(validators) == 2

    response.pop(RESPONSE_METADATA)
    assert response == {
        "items": [
            {
                ID: validator_id1,
                NAME: PARAM_NAME,
                VALIDATE_REQUEST_BODY: True,
                VALIDATE_REQUEST_PARAMETERS: True,
            },
            {
                ID: validator_id2,
                NAME: PARAM_NAME,
                VALIDATE_REQUEST_BODY: True,
                VALIDATE_REQUEST_PARAMETERS: True,
            },
        ]
    }


@mock_apigateway
def test_get_request_validator():
    client = create_client()
    api_id = create_rest_api_id(client)
    response = create_validator(client, api_id)
    validator_id = response[ID]
    response = client.get_request_validator(
        restApiId=api_id, requestValidatorId=validator_id
    )
    response.pop(RESPONSE_METADATA)
    assert response == {
        ID: validator_id,
        NAME: PARAM_NAME,
        VALIDATE_REQUEST_BODY: True,
        VALIDATE_REQUEST_PARAMETERS: True,
    }


@mock_apigateway
def test_delete_request_validator():
    client = create_client()
    api_id = create_rest_api_id(client)
    response = create_validator(client, api_id)
    # test get single validator by
    validator_id = response[ID]
    response = client.get_request_validator(
        restApiId=api_id, requestValidatorId=validator_id
    )

    response.pop(RESPONSE_METADATA)
    assert response == {
        ID: validator_id,
        NAME: PARAM_NAME,
        VALIDATE_REQUEST_BODY: True,
        VALIDATE_REQUEST_PARAMETERS: True,
    }

    # delete validator
    response = client.delete_request_validator(
        restApiId=api_id, requestValidatorId=validator_id
    )
    with pytest.raises(ClientError) as ex:
        client.get_request_validator(restApiId=api_id, requestValidatorId=validator_id)
    err = ex.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert err["Message"] == "Invalid Request Validator Id specified"


@mock_apigateway
def test_update_request_validator():
    client = create_client()
    api_id = create_rest_api_id(client)
    response = create_validator(client, api_id)

    validator_id = response[ID]
    response = client.update_request_validator(
        restApiId=api_id,
        requestValidatorId=validator_id,
        patchOperations=[
            {"op": "replace", "path": "/name", "value": PARAM_NAME + PARAM_NAME},
            {"op": "replace", "path": "/validateRequestBody", "value": "False"},
            {"op": "replace", "path": "/validateRequestParameters", "value": "False"},
        ],
    )
    response.pop(RESPONSE_METADATA)
    assert response == {
        ID: validator_id,
        NAME: PARAM_NAME + PARAM_NAME,
        VALIDATE_REQUEST_BODY: False,
        VALIDATE_REQUEST_PARAMETERS: False,
    }


def create_validator(client, api_id):
    response = client.create_request_validator(
        restApiId=api_id,
        name=PARAM_NAME,
        validateRequestBody=True,
        validateRequestParameters=True,
    )
    return response


def create_client():
    return boto3.client("apigateway", region_name="us-west-2")


def create_rest_api_id(client):
    response = client.create_rest_api(name="my_api", description="this is my api")
    return response[ID]
