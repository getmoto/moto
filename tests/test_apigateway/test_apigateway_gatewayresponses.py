import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_put_gateway_response_minimal():
    client = boto3.client("apigateway", region_name="us-east-2")
    api_id = client.create_rest_api(name="my_api", description="d")["id"]

    resp = client.put_gateway_response(restApiId=api_id, responseType="DEFAULT_4XX")

    assert resp["responseType"] == "DEFAULT_4XX"
    assert resp["defaultResponse"] is False


@mock_aws
def test_put_gateway_response():
    client = boto3.client("apigateway", region_name="us-east-2")
    api_id = client.create_rest_api(name="my_api", description="d")["id"]

    resp = client.put_gateway_response(
        restApiId=api_id,
        responseType="DEFAULT_4XX",
        statusCode="401",
        responseParameters={"gatewayresponse.header.Authorization": "'Basic'"},
        responseTemplates={
            "application/xml": "#set($inputRoot = $input.path('$'))\n{ }"
        },
    )

    assert resp["responseType"] == "DEFAULT_4XX"
    assert resp["defaultResponse"] is False
    assert resp["statusCode"] == "401"
    assert resp["responseParameters"] == {
        "gatewayresponse.header.Authorization": "'Basic'"
    }
    assert resp["responseTemplates"] == {
        "application/xml": "#set($inputRoot = $input.path('$'))\n{ }"
    }


@mock_aws
def test_get_gateway_response_minimal():
    client = boto3.client("apigateway", region_name="ap-southeast-1")
    api_id = client.create_rest_api(name="my_api", description="d")["id"]

    client.put_gateway_response(restApiId=api_id, responseType="DEFAULT_4XX")

    resp = client.get_gateway_response(restApiId=api_id, responseType="DEFAULT_4XX")

    assert resp["responseType"] == "DEFAULT_4XX"
    assert resp["defaultResponse"] is False


@mock_aws
def test_get_gateway_response():
    client = boto3.client("apigateway", region_name="us-east-2")
    api_id = client.create_rest_api(name="my_api", description="d")["id"]

    client.put_gateway_response(
        restApiId=api_id,
        responseType="DEFAULT_4XX",
        statusCode="401",
        responseParameters={"gatewayresponse.header.Authorization": "'Basic'"},
        responseTemplates={
            "application/xml": "#set($inputRoot = $input.path('$'))\n{ }"
        },
    )

    resp = client.get_gateway_response(restApiId=api_id, responseType="DEFAULT_4XX")

    assert resp["responseType"] == "DEFAULT_4XX"
    assert resp["defaultResponse"] is False
    assert resp["statusCode"] == "401"
    assert resp["responseParameters"] == {
        "gatewayresponse.header.Authorization": "'Basic'"
    }
    assert resp["responseTemplates"] == {
        "application/xml": "#set($inputRoot = $input.path('$'))\n{ }"
    }


@mock_aws
def test_get_gateway_response_unknown():
    client = boto3.client("apigateway", region_name="us-east-2")
    api_id = client.create_rest_api(name="my_api", description="d")["id"]

    with pytest.raises(ClientError) as exc:
        client.get_gateway_response(restApiId=api_id, responseType="DEFAULT_4XX")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"


@mock_aws
def test_get_gateway_responses_empty():
    client = boto3.client("apigateway", region_name="ap-southeast-1")
    api_id = client.create_rest_api(name="my_api", description="d")["id"]
    resp = client.get_gateway_responses(restApiId=api_id)

    assert resp["items"] == []


@mock_aws
def test_get_gateway_responses():
    client = boto3.client("apigateway", region_name="ap-southeast-1")
    api_id = client.create_rest_api(name="my_api", description="d")["id"]
    client.put_gateway_response(restApiId=api_id, responseType="DEFAULT_4XX")
    client.put_gateway_response(
        restApiId=api_id, responseType="DEFAULT_5XX", statusCode="503"
    )

    resp = client.get_gateway_responses(restApiId=api_id)
    assert len(resp["items"]) == 2

    assert {"responseType": "DEFAULT_4XX", "defaultResponse": False} in resp["items"]
    assert {
        "responseType": "DEFAULT_5XX",
        "defaultResponse": False,
        "statusCode": "503",
    } in resp["items"]


@mock_aws
def test_delete_gateway_response():
    client = boto3.client("apigateway", region_name="ap-southeast-1")
    api_id = client.create_rest_api(name="my_api", description="d")["id"]
    client.put_gateway_response(restApiId=api_id, responseType="DEFAULT_4XX")
    client.put_gateway_response(
        restApiId=api_id, responseType="DEFAULT_5XX", statusCode="503"
    )

    resp = client.get_gateway_responses(restApiId=api_id)
    assert len(resp["items"]) == 2

    client.delete_gateway_response(restApiId=api_id, responseType="DEFAULT_5XX")

    resp = client.get_gateway_responses(restApiId=api_id)
    assert len(resp["items"]) == 1
    assert {"responseType": "DEFAULT_4XX", "defaultResponse": False} in resp["items"]
