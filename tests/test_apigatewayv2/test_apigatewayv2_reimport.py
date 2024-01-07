import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_reimport_api_standard_fields():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.reimport_api(
        ApiId=api_id,
        Body="---\nopenapi: 3.0.1\ninfo:\n  title: tf-acc-test-2983214806752144669_DIFFERENT\n  version: 2.0\nx-amazon-apigateway-cors:\n  allow_methods:\n    - delete\n  allow_origins:\n    - https://www.google.de\npaths:\n  \"/test\":\n    get:\n      x-amazon-apigateway-integration:\n        type: HTTP_PROXY\n        httpMethod: GET\n        payloadFormatVersion: '1.0'\n        uri: https://www.google.de\n",
    )

    assert resp["CorsConfiguration"] == {}
    assert resp["Name"] == "tf-acc-test-2983214806752144669_DIFFERENT"
    assert resp["Version"] == "2.0"


@mock_aws
def test_reimport_api_failonwarnings():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-import-api", ProtocolType="HTTP")["ApiId"]

    with pytest.raises(ClientError) as exc:
        client.reimport_api(
            ApiId=api_id,
            Body='{\n  "openapi": "3.0.1",\n  "info": {\n    "title": "Title test",\n    "version": "2.0",\n    "description": "Description test"\n  },\n  "paths": {\n    "/update": {\n      "get": {\n        "x-amazon-apigateway-integration": {\n          "type": "HTTP_PROXY",\n          "httpMethod": "GET",\n          "payloadFormatVersion": "1.0",\n          "uri": "https://www.google.de"\n        },\n        "responses": {\n          "200": {\n            "description": "Response description",\n            "content": {\n              "application/json": {\n                "schema": {\n                  "$ref": "#/components/schemas/ModelThatDoesNotExist"\n                }\n              }\n            }\n          }\n        }\n      }\n    }\n  }\n}\n',
            FailOnWarnings=True,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert (
        err["Message"]
        == "Warnings found during import:\n\tParse issue: attribute paths.'/update'(get).responses.200.content.schema.#/components/schemas/ModelThatDoesNotExist is missing"
    )

    # Title should not have been updated
    resp = client.get_api(ApiId=api_id)
    assert resp["Name"] == "test-import-api"


@mock_aws
def test_reimport_api_do_not_failonwarnings():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-import-api", ProtocolType="HTTP")["ApiId"]

    client.reimport_api(
        ApiId=api_id,
        Body='{\n  "openapi": "3.0.1",\n  "info": {\n    "title": "Title test",\n    "version": "2.0",\n    "description": "Description test"\n  },\n  "paths": {\n    "/update": {\n      "get": {\n        "x-amazon-apigateway-integration": {\n          "type": "HTTP_PROXY",\n          "httpMethod": "GET",\n          "payloadFormatVersion": "1.0",\n          "uri": "https://www.google.de"\n        },\n        "responses": {\n          "200": {\n            "description": "Response description",\n            "content": {\n              "application/json": {\n                "schema": {\n                  "$ref": "#/components/schemas/ModelThatDoesNotExist"\n                }\n              }\n            }\n          }\n        }\n      }\n    }\n  }\n}\n',
        FailOnWarnings=False,
    )

    # Title should have been updated
    resp = client.get_api(ApiId=api_id)
    assert resp["Name"] == "Title test"


@mock_aws
def test_reimport_api_routes_and_integrations():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    resp = client.create_api(Name="test-import-api", ProtocolType="HTTP")
    api_id = resp["ApiId"]

    client.reimport_api(
        ApiId=api_id,
        Body='{\n  "openapi": "3.0.1",\n  "info": {\n    "title": "tf-acc-test-121780722915762033_DIFFERENT",\n    "version": "1.0"\n  },\n  "paths": {\n    "/test": {\n      "get": {\n        "x-amazon-apigateway-integration": {\n          "type": "HTTP_PROXY",\n          "httpMethod": "GET",\n          "payloadFormatVersion": "1.0",\n          "uri": "https://www.google.de"\n        }\n      }\n    }\n  }\n}\n',
    )

    resp = client.get_integrations(ApiId=api_id)
    assert len(resp["Items"]) == 1
    integration = resp["Items"][0]
    assert integration["ConnectionType"] == "INTERNET"
    assert "IntegrationId" in integration
    assert integration["IntegrationMethod"] == "GET"
    assert integration["IntegrationType"] == "HTTP_PROXY"
    assert integration["IntegrationUri"] == "https://www.google.de"
    assert integration["PayloadFormatVersion"] == "1.0"
    assert integration["TimeoutInMillis"] == 30000

    resp = client.get_routes(ApiId=api_id)
    assert len(resp["Items"]) == 1
    route = resp["Items"][0]
    assert route["ApiKeyRequired"] is False
    assert route["AuthorizationScopes"] == []
    assert route["RequestParameters"] == {}
    assert "RouteId" in route
    assert route["RouteKey"] == "GET /test"
    assert route["Target"] == f"integrations/{integration['IntegrationId']}"
