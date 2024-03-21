"""Unit tests for apigatewayv2-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_api_with_unknown_protocol_type():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.create_api(Name="test-api", ProtocolType="?")
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert (
        err["Message"] == "Invalid protocol specified. Must be one of [HTTP, WEBSOCKET]"
    )


@mock_aws
def test_create_api_minimal():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    resp = client.create_api(Name="test-api", ProtocolType="HTTP")

    assert "ApiId" in resp
    assert (
        resp["ApiEndpoint"]
        == f"https://{resp['ApiId']}.execute-api.eu-west-1.amazonaws.com"
    )
    assert resp["ApiKeySelectionExpression"] == "$request.header.x-api-key"
    assert "CreatedDate" in resp
    assert resp["DisableExecuteApiEndpoint"] is False
    assert resp["Name"] == "test-api"
    assert resp["ProtocolType"] == "HTTP"
    assert resp["RouteSelectionExpression"] == "$request.method $request.path"


@mock_aws
def test_create_api():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    resp = client.create_api(
        ApiKeySelectionExpression="s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["x-header1"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header1"],
            "MaxAge": 2,
        },
        Description="my first api",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="test-api",
        ProtocolType="HTTP",
        RouteSelectionExpression="route_s3l3ction",
        Version="1.0",
    )

    assert "ApiId" in resp
    assert (
        resp["ApiEndpoint"]
        == f"https://{resp['ApiId']}.execute-api.eu-west-1.amazonaws.com"
    )
    assert resp["ApiKeySelectionExpression"] == "s3l3ction"
    assert "CreatedDate" in resp
    assert resp["CorsConfiguration"] == {
        "AllowCredentials": True,
        "AllowHeaders": ["x-header1"],
        "AllowMethods": ["GET", "PUT"],
        "AllowOrigins": ["google.com"],
        "ExposeHeaders": ["x-header1"],
        "MaxAge": 2,
    }
    assert resp["Description"] == "my first api"
    assert resp["DisableExecuteApiEndpoint"] is True
    assert resp["DisableSchemaValidation"] is True
    assert resp["Name"] == "test-api"
    assert resp["ProtocolType"] == "HTTP"
    assert resp["RouteSelectionExpression"] == "route_s3l3ction"
    assert resp["Version"] == "1.0"


@mock_aws
def test_delete_api():
    client = boto3.client("apigatewayv2", region_name="us-east-2")
    api_id = client.create_api(Name="t", ProtocolType="HTTP")["ApiId"]

    client.delete_api(ApiId=api_id)

    with pytest.raises(ClientError) as exc:
        client.get_api(ApiId=api_id)
    assert exc.value.response["Error"]["Code"] == "NotFoundException"


@mock_aws
def test_delete_cors_configuration():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(
        ApiKeySelectionExpression="s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["x-header1"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header1"],
            "MaxAge": 2,
        },
        Description="my first api",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="test-api",
        ProtocolType="HTTP",
        RouteSelectionExpression="route_s3l3ction",
        Version="1.0",
    )["ApiId"]

    client.delete_cors_configuration(ApiId=api_id)

    resp = client.get_api(ApiId=api_id)

    assert "CorsConfiguration" not in resp
    assert resp["Description"] == "my first api"
    assert resp["Name"] == "test-api"


@mock_aws
def test_get_api_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.get_api(ApiId="unknown")

    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid API identifier specified unknown"


@mock_aws
def test_get_api():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-get-api", ProtocolType="WEBSOCKET")["ApiId"]

    resp = client.get_api(ApiId=api_id)

    assert resp["ApiId"] == api_id
    assert (
        resp["ApiEndpoint"]
        == f"https://{resp['ApiId']}.execute-api.ap-southeast-1.amazonaws.com"
    )
    assert resp["ApiKeySelectionExpression"] == "$request.header.x-api-key"
    assert "CreatedDate" in resp
    assert resp["DisableExecuteApiEndpoint"] is False
    assert resp["Name"] == "test-get-api"
    assert resp["ProtocolType"] == "WEBSOCKET"
    assert resp["RouteSelectionExpression"] == "$request.method $request.path"


@mock_aws
def test_get_apis():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    assert len(client.get_apis()["Items"]) == 0

    api_id_1 = client.create_api(Name="api1", ProtocolType="HTTP")["ApiId"]
    api_id_2 = client.create_api(Name="api2", ProtocolType="WEBSOCKET")["ApiId"]
    assert len(client.get_apis()["Items"]) == 2

    api_ids = [i["ApiId"] for i in client.get_apis()["Items"]]
    assert api_id_1 in api_ids
    assert api_id_2 in api_ids


@mock_aws
def test_update_api_minimal():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(
        ApiKeySelectionExpression="s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["x-header1"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header1"],
            "MaxAge": 2,
        },
        Description="my first api",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="test-api",
        ProtocolType="HTTP",
        RouteSelectionExpression="route_s3l3ction",
        Version="1.0",
    )["ApiId"]

    resp = client.update_api(
        ApiId=api_id,
        CorsConfiguration={
            "AllowCredentials": False,
            "AllowHeaders": ["x-header2"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header2"],
            "MaxAge": 2,
        },
    )

    assert "ApiId" in resp
    assert (
        resp["ApiEndpoint"]
        == f"https://{resp['ApiId']}.execute-api.eu-west-1.amazonaws.com"
    )
    assert resp["ApiKeySelectionExpression"] == "s3l3ction"
    assert "CreatedDate" in resp
    assert resp["CorsConfiguration"] == {
        "AllowCredentials": False,
        "AllowHeaders": ["x-header2"],
        "AllowMethods": ["GET", "PUT"],
        "AllowOrigins": ["google.com"],
        "ExposeHeaders": ["x-header2"],
        "MaxAge": 2,
    }
    assert resp["Description"] == "my first api"
    assert resp["DisableExecuteApiEndpoint"] is True
    assert resp["DisableSchemaValidation"] is True
    assert resp["Name"] == "test-api"
    assert resp["ProtocolType"] == "HTTP"
    assert resp["RouteSelectionExpression"] == "route_s3l3ction"
    assert resp["Version"] == "1.0"


@mock_aws
def test_update_api_empty_fields():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(
        ApiKeySelectionExpression="s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["x-header1"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header1"],
            "MaxAge": 2,
        },
        Description="my first api",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="test-api",
        ProtocolType="HTTP",
        RouteSelectionExpression="route_s3l3ction",
        Version="1.0",
    )["ApiId"]

    resp = client.update_api(ApiId=api_id, Description="", Name="updated", Version="")

    assert "ApiId" in resp
    assert (
        resp["ApiEndpoint"]
        == f"https://{resp['ApiId']}.execute-api.eu-west-1.amazonaws.com"
    )
    assert resp["ApiKeySelectionExpression"] == "s3l3ction"
    assert resp["Description"] == ""
    assert resp["DisableExecuteApiEndpoint"] is True
    assert resp["DisableSchemaValidation"] is True
    assert resp["Name"] == "updated"
    assert resp["ProtocolType"] == "HTTP"
    assert resp["RouteSelectionExpression"] == "route_s3l3ction"
    assert resp["Version"] == ""


@mock_aws
def test_update_api():
    client = boto3.client("apigatewayv2", region_name="us-east-2")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.update_api(
        ApiId=api_id,
        ApiKeySelectionExpression="api_key_s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["X-Amz-Target"],
            "AllowMethods": ["GET"],
        },
        CredentialsArn="credentials:arn",
        Description="updated API",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="new name",
        RouteKey="route key",
        RouteSelectionExpression="route_s3l3ction",
        Target="updated target",
        Version="1.1",
    )

    assert "ApiId" in resp
    assert (
        resp["ApiEndpoint"]
        == f"https://{resp['ApiId']}.execute-api.us-east-2.amazonaws.com"
    )
    assert resp["ApiKeySelectionExpression"] == "api_key_s3l3ction"
    assert resp["CorsConfiguration"] == {
        "AllowCredentials": True,
        "AllowHeaders": ["X-Amz-Target"],
        "AllowMethods": ["GET"],
    }
    assert "CreatedDate" in resp
    assert resp["Description"] == "updated API"
    assert resp["DisableSchemaValidation"] is True
    assert resp["DisableExecuteApiEndpoint"] is True
    assert resp["Name"] == "new name"
    assert resp["ProtocolType"] == "HTTP"
    assert resp["RouteSelectionExpression"] == "route_s3l3ction"
    assert resp["Version"] == "1.1"
