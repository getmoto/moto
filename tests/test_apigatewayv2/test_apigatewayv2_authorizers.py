import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_create_authorizer_minimum():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_authorizer(
        ApiId=api_id, AuthorizerType="REQUEST", IdentitySource=[], Name="auth1"
    )

    resp.should.have.key("AuthorizerId")
    resp.should.have.key("AuthorizerType").equals("REQUEST")
    resp.should.have.key("Name").equals("auth1")


@mock_apigatewayv2
def test_create_authorizer():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_authorizer(
        ApiId=api_id,
        AuthorizerCredentialsArn="auth:creds:arn",
        AuthorizerPayloadFormatVersion="2.0",
        AuthorizerResultTtlInSeconds=3,
        AuthorizerType="REQUEST",
        AuthorizerUri="auth_uri",
        EnableSimpleResponses=True,
        IdentitySource=["$request.header.Authorization"],
        IdentityValidationExpression="ive",
        JwtConfiguration={"Audience": ["a1"], "Issuer": "moto.com"},
        Name="auth1",
    )

    resp.should.have.key("AuthorizerId")
    resp.should.have.key("AuthorizerCredentialsArn").equals("auth:creds:arn")
    resp.should.have.key("AuthorizerPayloadFormatVersion").equals("2.0")
    resp.should.have.key("AuthorizerResultTtlInSeconds").equals(3)
    resp.should.have.key("AuthorizerType").equals("REQUEST")
    resp.should.have.key("AuthorizerUri").equals("auth_uri")
    resp.should.have.key("EnableSimpleResponses").equals(True)
    resp.should.have.key("IdentitySource").equals(["$request.header.Authorization"])
    resp.should.have.key("IdentityValidationExpression").equals("ive")
    resp.should.have.key("JwtConfiguration").equals(
        {"Audience": ["a1"], "Issuer": "moto.com"}
    )
    resp.should.have.key("Name").equals("auth1")


@mock_apigatewayv2
def test_get_authorizer():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    authorizer_id = client.create_authorizer(
        ApiId=api_id, AuthorizerType="REQUEST", IdentitySource=[], Name="auth1"
    )["AuthorizerId"]

    resp = client.get_authorizer(ApiId=api_id, AuthorizerId=authorizer_id)

    resp.should.have.key("AuthorizerId")
    resp.should.have.key("AuthorizerType").equals("REQUEST")
    resp.should.have.key("Name").equals("auth1")


@mock_apigatewayv2
def test_delete_authorizer():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    authorizer_id = client.create_authorizer(
        ApiId=api_id, AuthorizerType="REQUEST", IdentitySource=[], Name="auth1"
    )["AuthorizerId"]

    client.delete_authorizer(ApiId=api_id, AuthorizerId=authorizer_id)

    with pytest.raises(ClientError) as exc:
        client.get_authorizer(ApiId=api_id, AuthorizerId="unknown")

    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")


@mock_apigatewayv2
def test_get_authorizer_unknown():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    with pytest.raises(ClientError) as exc:
        client.get_authorizer(ApiId=api_id, AuthorizerId="unknown")

    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")


@mock_apigatewayv2
def test_update_authorizer_single():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    auth_id = client.create_authorizer(
        ApiId=api_id,
        AuthorizerCredentialsArn="auth:creds:arn",
        AuthorizerPayloadFormatVersion="2.0",
        AuthorizerResultTtlInSeconds=3,
        AuthorizerType="REQUEST",
        AuthorizerUri="auth_uri",
        EnableSimpleResponses=True,
        IdentitySource=["$request.header.Authorization"],
        IdentityValidationExpression="ive",
        JwtConfiguration={"Audience": ["a1"], "Issuer": "moto.com"},
        Name="auth1",
    )["AuthorizerId"]

    resp = client.update_authorizer(ApiId=api_id, AuthorizerId=auth_id, Name="auth2")

    resp.should.have.key("AuthorizerId")
    resp.should.have.key("AuthorizerCredentialsArn").equals("auth:creds:arn")
    resp.should.have.key("AuthorizerPayloadFormatVersion").equals("2.0")
    resp.should.have.key("AuthorizerResultTtlInSeconds").equals(3)
    resp.should.have.key("AuthorizerType").equals("REQUEST")
    resp.should.have.key("AuthorizerUri").equals("auth_uri")
    resp.should.have.key("EnableSimpleResponses").equals(True)
    resp.should.have.key("IdentitySource").equals(["$request.header.Authorization"])
    resp.should.have.key("IdentityValidationExpression").equals("ive")
    resp.should.have.key("JwtConfiguration").equals(
        {"Audience": ["a1"], "Issuer": "moto.com"}
    )
    resp.should.have.key("Name").equals("auth2")


@mock_apigatewayv2
def test_update_authorizer_all_attributes():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    auth_id = client.create_authorizer(
        ApiId=api_id, AuthorizerType="REQUEST", IdentitySource=[], Name="auth1"
    )["AuthorizerId"]

    auth_id = client.update_authorizer(
        ApiId=api_id,
        AuthorizerId=auth_id,
        AuthorizerCredentialsArn="",
        AuthorizerPayloadFormatVersion="3.0",
        AuthorizerResultTtlInSeconds=5,
        AuthorizerType="REQUEST",
        AuthorizerUri="auth_uri",
        EnableSimpleResponses=False,
        IdentitySource=["$request.header.Authentication"],
        IdentityValidationExpression="ive2",
        JwtConfiguration={"Audience": ["a2"], "Issuer": "moto.com"},
        Name="auth1",
    )["AuthorizerId"]

    resp = client.update_authorizer(ApiId=api_id, AuthorizerId=auth_id, Name="auth2")

    resp.should.have.key("AuthorizerId")
    resp.should.have.key("AuthorizerCredentialsArn").equals("")
    resp.should.have.key("AuthorizerPayloadFormatVersion").equals("3.0")
    resp.should.have.key("AuthorizerResultTtlInSeconds").equals(5)
    resp.should.have.key("AuthorizerType").equals("REQUEST")
    resp.should.have.key("AuthorizerUri").equals("auth_uri")
    resp.should.have.key("EnableSimpleResponses").equals(False)
    resp.should.have.key("IdentitySource").equals(["$request.header.Authentication"])
    resp.should.have.key("IdentityValidationExpression").equals("ive2")
    resp.should.have.key("JwtConfiguration").equals(
        {"Audience": ["a2"], "Issuer": "moto.com"}
    )
    resp.should.have.key("Name").equals("auth2")
