import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_reimport_api_standard_fields():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.reimport_api(
        ApiId=api_id,
        Body="---\nopenapi: 3.0.1\ninfo:\n  title: tf-acc-test-2983214806752144669_DIFFERENT\n  version: 2.0\nx-amazon-apigateway-cors:\n  allow_methods:\n    - delete\n  allow_origins:\n    - https://www.google.de\npaths:\n  \"/test\":\n    get:\n      x-amazon-apigateway-integration:\n        type: HTTP_PROXY\n        httpMethod: GET\n        payloadFormatVersion: '1.0'\n        uri: https://www.google.de\n",
    )

    resp.should.have.key("CorsConfiguration").equals({})
    resp.should.have.key("Name").equals("tf-acc-test-2983214806752144669_DIFFERENT")
    resp.should.have.key("Version").equals("2.0")


@mock_apigatewayv2
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
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.equal(
        "Warnings found during import:\n\tParse issue: attribute paths.'/update'(get).responses.200.content.schema.#/components/schemas/ModelThatDoesNotExist is missing"
    )

    # Title should not have been updated
    resp = client.get_api(ApiId=api_id)
    resp.should.have.key("Name").equals("test-import-api")


@mock_apigatewayv2
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
    resp.should.have.key("Name").equals("Title test")


@mock_apigatewayv2
def test_reimport_api_routes_and_integrations():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    resp = client.create_api(Name="test-import-api", ProtocolType="HTTP")
    api_id = resp["ApiId"]

    client.reimport_api(
        ApiId=api_id,
        Body='{\n  "openapi": "3.0.1",\n  "info": {\n    "title": "tf-acc-test-121780722915762033_DIFFERENT",\n    "version": "1.0"\n  },\n  "paths": {\n    "/test": {\n      "get": {\n        "x-amazon-apigateway-integration": {\n          "type": "HTTP_PROXY",\n          "httpMethod": "GET",\n          "payloadFormatVersion": "1.0",\n          "uri": "https://www.google.de"\n        }\n      }\n    }\n  }\n}\n',
    )

    resp = client.get_integrations(ApiId=api_id)
    resp.should.have.key("Items").length_of(1)
    integration = resp["Items"][0]
    integration.should.have.key("ConnectionType").equals("INTERNET")
    integration.should.have.key("IntegrationId")
    integration.should.have.key("IntegrationMethod").equals("GET")
    integration.should.have.key("IntegrationType").equals("HTTP_PROXY")
    integration.should.have.key("IntegrationUri").equals("https://www.google.de")
    integration.should.have.key("PayloadFormatVersion").equals("1.0")
    integration.should.have.key("TimeoutInMillis").equals(30000)

    resp = client.get_routes(ApiId=api_id)
    resp.should.have.key("Items").length_of(1)
    route = resp["Items"][0]
    route.should.have.key("ApiKeyRequired").equals(False)
    route.should.have.key("AuthorizationScopes").equals([])
    route.should.have.key("RequestParameters").equals({})
    route.should.have.key("RouteId")
    route.should.have.key("RouteKey").equals("GET /test")
    route.should.have.key("Target").should.equal(
        f"integrations/{integration['IntegrationId']}"
    )
