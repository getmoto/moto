import json
import os

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_import_rest_api__api_is_created():
    client = boto3.client("apigateway", region_name="us-west-2")

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/petstore-swagger-v3.yaml", "rb") as api_json:
        response = client.import_rest_api(body=api_json.read())
        api_id = response["id"]

    root_id = client.get_resources(restApiId=api_id)["items"][4]["id"]
    client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="POST")

    client.put_integration(
        restApiId=api_id, resourceId=root_id, httpMethod="POST", type="MOCK"
    )
    client.put_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="POST", statusCode="200"
    )

    deployment_id = client.create_deployment(restApiId=api_id, stageName="dep")["id"]

    client.create_stage(restApiId=api_id, stageName="stg", deploymentId=deployment_id)

    resp = client.get_export(restApiId=api_id, stageName="stg", exportType="swagger")
    assert resp["contentType"] == "application/octet-stream"
    assert 'attachment; filename="swagger' in resp["contentDisposition"]

    body = json.loads(resp["body"].read().decode("utf-8"))

    assert body["info"]["title"] == "Swagger Petstore - OpenAPI 3.0"
    assert len(body["paths"]) == 15

    assert len(body["paths"]["/pet/{petId}"]) == 3
    assert set(body["paths"]["/pet/{petId}"].keys()) == {"DELETE", "GET", "POST"}


@mock_aws
def test_export_api__unknown_api():
    client = boto3.client("apigateway", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        client.get_export(restApiId="unknown", stageName="l", exportType="a")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid stage identifier specified"


@mock_aws
def test_export_api__unknown_export_type():
    client = boto3.client("apigateway", region_name="us-east-1")

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/petstore-swagger-v3.yaml", "rb") as api_json:
        response = client.import_rest_api(body=api_json.read())
        api_id = response["id"]

    root_id = client.get_resources(restApiId=api_id)["items"][4]["id"]
    client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="POST")

    client.put_integration(
        restApiId=api_id, resourceId=root_id, httpMethod="POST", type="MOCK"
    )
    client.put_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="POST", statusCode="200"
    )
    client.create_deployment(restApiId=api_id, stageName="dep")

    with pytest.raises(ClientError) as exc:
        client.get_export(restApiId=api_id, stageName="dep", exportType="a")
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert err["Message"] == "No API exporter for type 'a'"
