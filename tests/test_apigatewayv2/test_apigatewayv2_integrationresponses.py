import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_get_integration_responses_empty():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    int_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    resp = client.get_integration_responses(ApiId=api_id, IntegrationId=int_id)
    resp.should.have.key("Items").equals([])


@mock_apigatewayv2
def test_create_integration_response():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    int_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    int_res = client.create_integration_response(
        ApiId=api_id,
        ContentHandlingStrategy="CONVERT_TO_BINARY",
        IntegrationId=int_id,
        IntegrationResponseKey="int_res_key",
        ResponseParameters={"x-header": "header-value"},
        ResponseTemplates={"t": "template"},
        TemplateSelectionExpression="tse",
    )

    int_res.should.have.key("ContentHandlingStrategy").equals("CONVERT_TO_BINARY")
    int_res.should.have.key("IntegrationResponseId")
    int_res.should.have.key("IntegrationResponseKey").equals("int_res_key")
    int_res.should.have.key("ResponseParameters").equals({"x-header": "header-value"})
    int_res.should.have.key("ResponseTemplates").equals({"t": "template"})
    int_res.should.have.key("TemplateSelectionExpression").equals("tse")


@mock_apigatewayv2
def test_get_integration_response():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    int_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    int_res_id = client.create_integration_response(
        ApiId=api_id,
        ContentHandlingStrategy="CONVERT_TO_BINARY",
        IntegrationId=int_id,
        IntegrationResponseKey="int_res_key",
        ResponseParameters={"x-header": "header-value"},
        ResponseTemplates={"t": "template"},
        TemplateSelectionExpression="tse",
    )["IntegrationResponseId"]

    int_res = client.get_integration_response(
        ApiId=api_id, IntegrationId=int_id, IntegrationResponseId=int_res_id
    )

    int_res.should.have.key("ContentHandlingStrategy").equals("CONVERT_TO_BINARY")
    int_res.should.have.key("IntegrationResponseId")
    int_res.should.have.key("IntegrationResponseKey").equals("int_res_key")
    int_res.should.have.key("ResponseParameters").equals({"x-header": "header-value"})
    int_res.should.have.key("ResponseTemplates").equals({"t": "template"})
    int_res.should.have.key("TemplateSelectionExpression").equals("tse")


@mock_apigatewayv2
def test_get_integration_response_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    int_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    with pytest.raises(ClientError) as exc:
        client.get_integration_response(
            ApiId=api_id, IntegrationId=int_id, IntegrationResponseId="unknown"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal(
        "Invalid IntegrationResponse identifier specified unknown"
    )


@mock_apigatewayv2
def test_delete_integration_response():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    int_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    int_res_id = client.create_integration_response(
        ApiId=api_id, IntegrationId=int_id, IntegrationResponseKey="int_res_key"
    )["IntegrationResponseId"]

    client.delete_integration_response(
        ApiId=api_id, IntegrationId=int_id, IntegrationResponseId=int_res_id
    )

    with pytest.raises(ClientError) as exc:
        client.get_integration_response(
            ApiId=api_id, IntegrationId=int_id, IntegrationResponseId=int_res_id
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")


@mock_apigatewayv2
def test_update_integration_response_single_attr():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    int_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    int_res_id = client.create_integration_response(
        ApiId=api_id, IntegrationId=int_id, IntegrationResponseKey="int_res_key"
    )["IntegrationResponseId"]

    res = client.update_integration_response(
        ApiId=api_id,
        IntegrationId=int_id,
        IntegrationResponseId=int_res_id,
        ContentHandlingStrategy="CONVERT_TO_BINARY",
    )

    res.should.have.key("ContentHandlingStrategy").equals("CONVERT_TO_BINARY")
    res.should.have.key("IntegrationResponseId")
    res.should.have.key("IntegrationResponseKey").equals("int_res_key")


@mock_apigatewayv2
def test_update_integration_response_multiple_attrs():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    int_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    int_res_id = client.create_integration_response(
        ApiId=api_id,
        IntegrationId=int_id,
        IntegrationResponseKey="int_res_key",
        ContentHandlingStrategy="CONVERT_TO_BINARY",
    )["IntegrationResponseId"]

    res = client.update_integration_response(
        ApiId=api_id,
        IntegrationId=int_id,
        IntegrationResponseId=int_res_id,
        IntegrationResponseKey="int_res_key2",
        ResponseParameters={"x-header": "header-value"},
        ResponseTemplates={"t": "template"},
        TemplateSelectionExpression="tse",
    )

    res.should.have.key("ContentHandlingStrategy").equals("CONVERT_TO_BINARY")
    res.should.have.key("IntegrationResponseId")
    res.should.have.key("IntegrationResponseKey").equals("int_res_key2")
    res.should.have.key("ResponseParameters").equals({"x-header": "header-value"})
    res.should.have.key("ResponseTemplates").equals({"t": "template"})
    res.should.have.key("TemplateSelectionExpression").equals("tse")
