import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_create_model():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_model(
        ApiId=api_id, ContentType="app/xml", Description="desc", Name="nm", Schema="cs"
    )

    resp.should.have.key("ContentType").equals("app/xml")
    resp.should.have.key("Description").equals("desc")
    resp.should.have.key("ModelId")
    resp.should.have.key("Name").equals("nm")
    resp.should.have.key("Schema").equals("cs")


@mock_apigatewayv2
def test_get_model():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    model_id = client.create_model(
        ApiId=api_id, ContentType="app/xml", Description="desc", Name="nm", Schema="cs"
    )["ModelId"]

    resp = client.get_model(ApiId=api_id, ModelId=model_id)

    resp.should.have.key("ContentType").equals("app/xml")
    resp.should.have.key("Description").equals("desc")
    resp.should.have.key("ModelId")
    resp.should.have.key("Name").equals("nm")
    resp.should.have.key("Schema").equals("cs")


@mock_apigatewayv2
def test_delete_model():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    model_id = client.create_model(
        ApiId=api_id, ContentType="app/xml", Description="desc", Name="nm", Schema="cs"
    )["ModelId"]

    client.delete_model(ApiId=api_id, ModelId=model_id)

    with pytest.raises(ClientError) as exc:
        client.get_model(ApiId=api_id, ModelId=model_id)

    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")


@mock_apigatewayv2
def test_get_model_unknown():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    with pytest.raises(ClientError) as exc:
        client.get_model(ApiId=api_id, ModelId="unknown")

    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")


@mock_apigatewayv2
def test_update_model_single_attr():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    model_id = client.create_model(
        ApiId=api_id, ContentType="app/xml", Description="desc", Name="nm", Schema="cs"
    )["ModelId"]

    model_id = client.get_model(ApiId=api_id, ModelId=model_id)["ModelId"]

    resp = client.update_model(ApiId=api_id, ModelId=model_id, Schema="cs2")

    resp.should.have.key("ContentType").equals("app/xml")
    resp.should.have.key("Description").equals("desc")
    resp.should.have.key("ModelId")
    resp.should.have.key("Name").equals("nm")
    resp.should.have.key("Schema").equals("cs2")


@mock_apigatewayv2
def test_update_model_all_attrs():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    model_id = client.create_model(
        ApiId=api_id, ContentType="app/xml", Description="desc", Name="nm", Schema="cs"
    )["ModelId"]

    model_id = client.get_model(ApiId=api_id, ModelId=model_id)["ModelId"]

    resp = client.update_model(
        ApiId=api_id,
        ModelId=model_id,
        ContentType="app/html",
        Description="html2.x",
        Name="html-schema",
        Schema="cs2",
    )

    resp.should.have.key("ContentType").equals("app/html")
    resp.should.have.key("Description").equals("html2.x")
    resp.should.have.key("Name").equals("html-schema")
    resp.should.have.key("Schema").equals("cs2")
