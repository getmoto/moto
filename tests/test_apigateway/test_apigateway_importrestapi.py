import boto3
import os
import pytest
import sys

from botocore.exceptions import ClientError
from moto import mock_apigateway, settings
from unittest import SkipTest


@mock_apigateway
def test_import_rest_api__api_is_created():
    client = boto3.client("apigateway", region_name="us-west-2")

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api.json", "rb") as api_json:
        response = client.import_rest_api(body=api_json.read())

    assert "id" in response
    assert response["name"] == "doc"
    assert response["description"] == "description from JSON file"

    response = client.get_rest_api(restApiId=response["id"])
    assert response["name"] == "doc"
    assert response["description"] == "description from JSON file"


@mock_apigateway
def test_import_rest_api__nested_api():
    client = boto3.client("apigateway", region_name="us-west-2")

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_deep_api.yaml", "rb") as api_json:
        response = client.import_rest_api(body=api_json.read())

    resources = client.get_resources(restApiId=response["id"])["items"]
    assert len(resources) == 5

    paths = [res["path"] for res in resources]
    assert "/" in paths
    assert "/test" in paths
    assert "/test/some" in paths
    assert "/test/some/deep" in paths
    assert "/test/some/deep/path" in paths


@mock_apigateway
def test_import_rest_api__invalid_api_creates_nothing():
    if sys.version_info < (3, 8) or settings.TEST_SERVER_MODE:
        raise SkipTest("openapi-module throws an error in Py3.7")

    client = boto3.client("apigateway", region_name="us-west-2")

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api_invalid.json", "rb") as api_json:
        with pytest.raises(ClientError) as exc:
            client.import_rest_api(body=api_json.read(), failOnWarnings=True)
        err = exc.value.response["Error"]
        assert err["Code"] == "BadRequestException"
        assert (
            err["Message"]
            == "Failed to parse the uploaded OpenAPI document due to: 'paths' is a required property"
        )

    assert len(client.get_rest_apis()["items"]) == 0


@mock_apigateway
def test_import_rest_api__methods_are_created():
    client = boto3.client("apigateway", region_name="us-east-1")

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api.json", "rb") as api_json:
        resp = client.import_rest_api(body=api_json.read())
        api_id = resp["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [res for res in resources["items"] if res["path"] == "/"][0]["id"]

    # We have a GET-method
    resp = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")
    assert resp["methodResponses"] == {"200": {"statusCode": "200"}}

    # We have a POST on /test
    test_path_id = [res for res in resources["items"] if res["path"] == "/test"][0][
        "id"
    ]
    resp = client.get_method(
        restApiId=api_id, resourceId=test_path_id, httpMethod="POST"
    )
    assert resp["methodResponses"] == {"201": {"statusCode": "201"}}
