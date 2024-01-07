import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_get_integration_responses_empty():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    int_id = client.create_integration(ApiId=api_id, IntegrationType="HTTP")[
        "IntegrationId"
    ]

    resp = client.get_integration_responses(ApiId=api_id, IntegrationId=int_id)
    assert resp["Items"] == []


@mock_aws
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

    assert int_res["ContentHandlingStrategy"] == "CONVERT_TO_BINARY"
    assert "IntegrationResponseId" in int_res
    assert int_res["IntegrationResponseKey"] == "int_res_key"
    assert int_res["ResponseParameters"] == {"x-header": "header-value"}
    assert int_res["ResponseTemplates"] == {"t": "template"}
    assert int_res["TemplateSelectionExpression"] == "tse"


@mock_aws
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

    assert int_res["ContentHandlingStrategy"] == "CONVERT_TO_BINARY"
    assert "IntegrationResponseId" in int_res
    assert int_res["IntegrationResponseKey"] == "int_res_key"
    assert int_res["ResponseParameters"] == {"x-header": "header-value"}
    assert int_res["ResponseTemplates"] == {"t": "template"}
    assert int_res["TemplateSelectionExpression"] == "tse"


@mock_aws
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
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid IntegrationResponse identifier specified unknown"


@mock_aws
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
    assert err["Code"] == "NotFoundException"


@mock_aws
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

    assert res["ContentHandlingStrategy"] == "CONVERT_TO_BINARY"
    assert "IntegrationResponseId" in res
    assert res["IntegrationResponseKey"] == "int_res_key"


@mock_aws
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

    assert res["ContentHandlingStrategy"] == "CONVERT_TO_BINARY"
    assert "IntegrationResponseId" in res
    assert res["IntegrationResponseKey"] == "int_res_key2"
    assert res["ResponseParameters"] == {"x-header": "header-value"}
    assert res["ResponseTemplates"] == {"t": "template"}
    assert res["TemplateSelectionExpression"] == "tse"
