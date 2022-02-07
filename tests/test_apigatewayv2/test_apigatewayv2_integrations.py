import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_get_integrations_empty():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.get_integrations(ApiId=api_id)
    resp.should.have.key("Items").equals([])


@mock_apigatewayv2
def test_create_integration_minimum():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_integration(ApiId=api_id, IntegrationType="HTTP")

    resp.should.have.key("IntegrationId")
    resp.should.have.key("IntegrationType").equals("HTTP")


@mock_apigatewayv2
def test_create_integration_for_internet_mock():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_integration(
        ApiId=api_id, ConnectionType="INTERNET", IntegrationType="MOCK"
    )

    resp.should.have.key("IntegrationId")
    resp.should.have.key("IntegrationType").equals("MOCK")
    resp.should.have.key("IntegrationResponseSelectionExpression").equals(
        "${integration.response.statuscode}"
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

    resp.should.have.key("IntegrationId")
    resp.should.have.key("ConnectionId").equals("conn_id")
    resp.should.have.key("ConnectionType").equals("INTERNET")
    resp.should.have.key("ContentHandlingStrategy").equals("CONVERT_TO_BINARY")
    resp.should.have.key("CredentialsArn").equals("cred:arn")
    resp.should.have.key("Description").equals("my full integration")
    resp.should.have.key("IntegrationMethod").equals("PUT")
    resp.should.have.key("IntegrationType").equals("HTTP")
    resp.should.have.key("IntegrationSubtype").equals("n/a")
    resp.should.have.key("PassthroughBehavior").equals("WHEN_NO_MATCH")
    resp.should.have.key("PayloadFormatVersion").equals("1.0")
    resp.should.have.key("RequestParameters").equals({"r": "p"})
    resp.should.have.key("RequestTemplates").equals({"r": "t"})
    resp.should.have.key("ResponseParameters").equals({"res": {"par": "am"}})
    resp.should.have.key("TemplateSelectionExpression").equals("tse")
    resp.should.have.key("TimeoutInMillis").equals(123)
    resp.should.have.key("TlsConfig").equals({"ServerNameToVerify": "server"})


@mock_apigatewayv2
def test_get_integration():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    integration_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    resp = client.get_integration(ApiId=api_id, IntegrationId=integration_id)

    resp.should.have.key("IntegrationId")
    resp.should.have.key("IntegrationType").equals("HTTP")


@mock_apigatewayv2
def test_get_integration_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    with pytest.raises(ClientError) as exc:
        client.get_integration(ApiId=api_id, IntegrationId="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("Invalid Integration identifier specified unknown")


@mock_apigatewayv2
def test_get_integrations():
    client = boto3.client("apigatewayv2", region_name="us-east-2")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    integration_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]
    resp = client.get_integrations(ApiId=api_id)

    resp.should.have.key("Items").length_of(1)
    resp["Items"][0].should.have.key("IntegrationId").equals(integration_id)


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
    err["Code"].should.equal("NotFoundException")


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

    resp.should.have.key("IntegrationId")
    resp.should.have.key("ConnectionId").equals("conn_id")
    resp.should.have.key("ConnectionType").equals("INTERNET")
    resp.should.have.key("ContentHandlingStrategy").equals("CONVERT_TO_BINARY")
    resp.should.have.key("CredentialsArn").equals("cred:arn")
    resp.should.have.key("Description").equals("updated int")
    resp.should.have.key("IntegrationMethod").equals("PUT")
    resp.should.have.key("IntegrationType").equals("HTTP")
    resp.should.have.key("IntegrationSubtype").equals("n/a")
    resp.should.have.key("PassthroughBehavior").equals("WHEN_NO_MATCH")
    resp.should.have.key("PayloadFormatVersion").equals("1.0")
    resp.should.have.key("RequestParameters").equals({"r": "p"})
    resp.should.have.key("RequestTemplates").equals({"r": "t"})
    resp.should.have.key("ResponseParameters").equals({"res": {"par": "am"}})
    resp.should.have.key("TemplateSelectionExpression").equals("tse")
    resp.should.have.key("TimeoutInMillis").equals(123)
    resp.should.have.key("TlsConfig").equals({"ServerNameToVerify": "server"})


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

    resp.should.have.key("IntegrationId")
    resp.should.have.key("ConnectionId").equals("conn_id")
    resp.should.have.key("ConnectionType").equals("VPC_LINK")
    resp.should.have.key("ContentHandlingStrategy").equals("CONVERT_TO_TEXT")
    resp.should.have.key("CredentialsArn").equals("")
    resp.should.have.key("Description").equals("my full integration")
    resp.should.have.key("IntegrationMethod").equals("PATCH")
    resp.should.have.key("IntegrationType").equals("AWS")
    resp.should.have.key("IntegrationSubtype").equals("n/a")
    resp.should.have.key("PassthroughBehavior").equals("NEVER")
    resp.should.have.key("PayloadFormatVersion").equals("1.0")
    resp.should.have.key("RequestParameters").equals({"r": "p"})
    resp.should.have.key("RequestTemplates").equals({"r": "t"})
    resp.should.have.key("ResponseParameters").equals({"res": {"par": "am"}})
    resp.should.have.key("TemplateSelectionExpression").equals("tse")
    resp.should.have.key("TimeoutInMillis").equals(123)
    resp.should.have.key("TlsConfig").equals({"ServerNameToVerify": "server"})


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
    resp["RequestParameters"].should.equal(
        {"append:header.header1": "$context.requestId", "remove:querystring.qs1": "''"}
    )

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

    resp.should.have.key("IntegrationId")
    resp.should.have.key("IntegrationMethod").equals("ANY")
    resp.should.have.key("IntegrationType").equals("HTTP_PROXY")
    resp.should.have.key("PayloadFormatVersion").equals("1.0")
    # Having no value ("") is not valid, so that param should not be persisted
    resp.should.have.key("RequestParameters").equals(
        {
            "append:header.header1": "$context.accountId",
            "overwrite:header.header2": "$stageVariables.environmentId",
        }
    )
    resp.should.have.key("ResponseParameters").equals(
        {
            "404": {},
            "500": {
                "append:header.header1": "$context.requestId",
                "overwrite:statuscode": "403",
            },
        }
    )
