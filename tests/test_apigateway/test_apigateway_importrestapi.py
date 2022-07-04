import boto3
import os
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigateway


@mock_apigateway
def test_import_rest_api__api_is_created():
    client = boto3.client("apigateway", region_name="us-west-2")

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api.json", "rb") as api_json:
        response = client.import_rest_api(body=api_json.read())

    response.should.have.key("id")
    response.should.have.key("name").which.should.equal("doc")
    response.should.have.key("description").which.should.equal(
        "description from JSON file"
    )

    response = client.get_rest_api(restApiId=response["id"])
    response.should.have.key("name").which.should.equal("doc")
    response.should.have.key("description").which.should.equal(
        "description from JSON file"
    )


@mock_apigateway
def test_import_rest_api__invalid_api_creates_nothing():
    client = boto3.client("apigateway", region_name="us-west-2")

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api_invalid.json", "rb") as api_json:
        with pytest.raises(ClientError) as exc:
            client.import_rest_api(body=api_json.read(), failOnWarnings=True)
        err = exc.value.response["Error"]
        err["Code"].should.equal("BadRequestException")
        err["Message"].should.equal(
            "Failed to parse the uploaded OpenAPI document due to: 'paths' is a required property"
        )

    client.get_rest_apis().should.have.key("items").length_of(0)


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
    resp["methodResponses"].should.equal({"200": {"statusCode": "200"}})

    # We have a POST on /test
    test_path_id = [res for res in resources["items"] if res["path"] == "/test"][0][
        "id"
    ]
    resp = client.get_method(
        restApiId=api_id, resourceId=test_path_id, httpMethod="POST"
    )
    resp["methodResponses"].should.equal({"201": {"statusCode": "201"}})
