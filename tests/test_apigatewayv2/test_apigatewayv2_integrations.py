import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_get_integrations_empty():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.get_integrations(ApiId=api_id)
    assert resp["Items"] == []


@mock_apigatewayv2
def test_create_integration_minimum():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_integration(ApiId=api_id, IntegrationType="HTTP")

    assert "IntegrationId" in resp
    assert resp["IntegrationType"] == "HTTP"


@mock_apigatewayv2
def test_create_integration_for_internet_mock():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_integration(
        ApiId=api_id, ConnectionType="INTERNET", IntegrationType="MOCK"
    )

    assert "IntegrationId" in resp
    assert resp["IntegrationType"] == "MOCK"
    assert (
        resp["IntegrationResponseSelectionExpression"]
        == "${integration.response.statuscode}"
    )


@mock_apigatewayv2
def test_create_integration_full():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_integration(
        ApiId=api_id,
        ConnectionId="conn_id",
        ConnectionType="INTERNET",
        ContentHandlingStrategy="CONVERT_TO_BINARY",
        CredentialsArn="cred:arn",
        Description="my full integration",
        IntegrationMethod="PUT",
        IntegrationType="HTTP",
        IntegrationSubtype="n/a",
        PassthroughBehavior="WHEN_NO_MATCH",
        PayloadFormatVersion="1.0",
        RequestParameters={"r": "p"},
        RequestTemplates={"r": "t"},
        ResponseParameters={"res": {"par": "am"}},
        TemplateSelectionExpression="tse",
        TimeoutInMillis=123,
        TlsConfig={"ServerNameToVerify": "server"},
    )

    assert "IntegrationId" in resp
    assert resp["ConnectionId"] == "conn_id"
    assert resp["ConnectionType"] == "INTERNET"
    assert resp["ContentHandlingStrategy"] == "CONVERT_TO_BINARY"
    assert resp["CredentialsArn"] == "cred:arn"
    assert resp["Description"] == "my full integration"
    assert resp["IntegrationMethod"] == "PUT"
    assert resp["IntegrationType"] == "HTTP"
    assert resp["IntegrationSubtype"] == "n/a"
    assert resp["PassthroughBehavior"] == "WHEN_NO_MATCH"
    assert resp["PayloadFormatVersion"] == "1.0"
    assert resp["RequestParameters"] == {"r": "p"}
    assert resp["RequestTemplates"] == {"r": "t"}
    assert resp["ResponseParameters"] == {"res": {"par": "am"}}
    assert resp["TemplateSelectionExpression"] == "tse"
    assert resp["TimeoutInMillis"] == 123
    assert resp["TlsConfig"] == {"ServerNameToVerify": "server"}


@mock_apigatewayv2
def test_get_integration():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    integration_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    resp = client.get_integration(ApiId=api_id, IntegrationId=integration_id)

    assert "IntegrationId" in resp
    assert resp["IntegrationType"] == "HTTP"


@mock_apigatewayv2
def test_get_integration_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    with pytest.raises(ClientError) as exc:
        client.get_integration(ApiId=api_id, IntegrationId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid Integration identifier specified unknown"


@mock_apigatewayv2
def test_get_integrations():
    client = boto3.client("apigatewayv2", region_name="us-east-2")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    integration_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]
    resp = client.get_integrations(ApiId=api_id)

    assert len(resp["Items"]) == 1
    assert resp["Items"][0]["IntegrationId"] == integration_id


@mock_apigatewayv2
def test_delete_integration():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    integration_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    client.delete_integration(ApiId=api_id, IntegrationId=integration_id)

    with pytest.raises(ClientError) as exc:
        client.get_integration(ApiId=api_id, IntegrationId=integration_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"


@mock_apigatewayv2
def test_update_integration_single_attr():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    int_id = client.create_integration(
        ApiId=api_id,
        ConnectionId="conn_id",
        ConnectionType="INTERNET",
        ContentHandlingStrategy="CONVERT_TO_BINARY",
        CredentialsArn="cred:arn",
        Description="my full integration",
        IntegrationMethod="PUT",
        IntegrationType="HTTP",
        IntegrationSubtype="n/a",
        PassthroughBehavior="WHEN_NO_MATCH",
        PayloadFormatVersion="1.0",
        RequestParameters={"r": "p"},
        RequestTemplates={"r": "t"},
        ResponseParameters={"res": {"par": "am"}},
        TemplateSelectionExpression="tse",
        TimeoutInMillis=123,
        TlsConfig={"ServerNameToVerify": "server"},
    )["IntegrationId"]

    resp = client.update_integration(
        ApiId=api_id, IntegrationId=int_id, Description="updated int"
    )

    assert "IntegrationId" in resp
    assert resp["ConnectionId"] == "conn_id"
    assert resp["ConnectionType"] == "INTERNET"
    assert resp["ContentHandlingStrategy"] == "CONVERT_TO_BINARY"
    assert resp["CredentialsArn"] == "cred:arn"
    assert resp["Description"] == "updated int"
    assert resp["IntegrationMethod"] == "PUT"
    assert resp["IntegrationType"] == "HTTP"
    assert resp["IntegrationSubtype"] == "n/a"
    assert resp["PassthroughBehavior"] == "WHEN_NO_MATCH"
    assert resp["PayloadFormatVersion"] == "1.0"
    assert resp["RequestParameters"] == {"r": "p"}
    assert resp["RequestTemplates"] == {"r": "t"}
    assert resp["ResponseParameters"] == {"res": {"par": "am"}}
    assert resp["TemplateSelectionExpression"] == "tse"
    assert resp["TimeoutInMillis"] == 123
    assert resp["TlsConfig"] == {"ServerNameToVerify": "server"}


@mock_apigatewayv2
def test_update_integration_all_attrs():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    int_id = client.create_integration(
        ApiId=api_id,
        ConnectionId="conn_id",
        ConnectionType="INTERNET",
        ContentHandlingStrategy="CONVERT_TO_BINARY",
        CredentialsArn="cred:arn",
        Description="my full integration",
        IntegrationMethod="PUT",
        IntegrationType="HTTP",
        IntegrationSubtype="n/a",
        PassthroughBehavior="WHEN_NO_MATCH",
        PayloadFormatVersion="1.0",
        RequestParameters={"r": "p"},
        RequestTemplates={"r": "t"},
        ResponseParameters={"res": {"par": "am"}},
        TemplateSelectionExpression="tse",
        TimeoutInMillis=123,
        TlsConfig={"ServerNameToVerify": "server"},
    )["IntegrationId"]

    resp = client.update_integration(
        ApiId=api_id,
        IntegrationId=int_id,
        ConnectionType="VPC_LINK",
        ContentHandlingStrategy="CONVERT_TO_TEXT",
        CredentialsArn="",
        IntegrationMethod="PATCH",
        IntegrationType="AWS",
        PassthroughBehavior="NEVER",
    )

    assert "IntegrationId" in resp
    assert resp["ConnectionId"] == "conn_id"
    assert resp["ConnectionType"] == "VPC_LINK"
    assert resp["ContentHandlingStrategy"] == "CONVERT_TO_TEXT"
    assert resp["CredentialsArn"] == ""
    assert resp["Description"] == "my full integration"
    assert resp["IntegrationMethod"] == "PATCH"
    assert resp["IntegrationType"] == "AWS"
    assert resp["IntegrationSubtype"] == "n/a"
    assert resp["PassthroughBehavior"] == "NEVER"
    assert resp["PayloadFormatVersion"] == "1.0"
    assert resp["RequestParameters"] == {"r": "p"}
    assert resp["RequestTemplates"] == {"r": "t"}
    assert resp["ResponseParameters"] == {"res": {"par": "am"}}
    assert resp["TemplateSelectionExpression"] == "tse"
    assert resp["TimeoutInMillis"] == 123
    assert resp["TlsConfig"] == {"ServerNameToVerify": "server"}


@mock_apigatewayv2
def test_update_integration_request_parameters():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_integration(
        ApiId=api_id,
        ConnectionType="INTERNET",
        IntegrationMethod="ANY",
        IntegrationType="HTTP_PROXY",
        IntegrationUri="http://www.example.com",
        PayloadFormatVersion="1.0",
        RequestParameters={
            "append:header.header1": "$context.requestId",
            "remove:querystring.qs1": "''",
        },
        ResponseParameters={
            "404": {"append:header.error": "$stageVariables.environmentId"},
            "500": {
                "append:header.header1": "$context.requestId",
                "overwrite:statuscode": "403",
            },
        },
    )

    int_id = resp["IntegrationId"]
    # Having an empty value between quotes ("''") is valid
    assert resp["RequestParameters"] == {
        "append:header.header1": "$context.requestId",
        "remove:querystring.qs1": "''",
    }

    resp = client.update_integration(
        ApiId=api_id,
        IntegrationId=int_id,
        IntegrationType="HTTP_PROXY",
        RequestParameters={
            "append:header.header1": "$context.accountId",
            "overwrite:header.header2": "$stageVariables.environmentId",
            "remove:querystring.qs1": "",
        },
        ResponseParameters={
            "404": {},
            "500": {
                "append:header.header1": "$context.requestId",
                "overwrite:statuscode": "403",
            },
        },
    )

    assert "IntegrationId" in resp
    assert resp["IntegrationMethod"] == "ANY"
    assert resp["IntegrationType"] == "HTTP_PROXY"
    assert resp["PayloadFormatVersion"] == "1.0"
    # Having no value ("") is not valid, so that param should not be persisted
    assert resp["RequestParameters"] == {
        "append:header.header1": "$context.accountId",
        "overwrite:header.header2": "$stageVariables.environmentId",
    }
    assert resp["ResponseParameters"] == {
        "404": {},
        "500": {
            "append:header.header1": "$context.requestId",
            "overwrite:statuscode": "403",
        },
    }
