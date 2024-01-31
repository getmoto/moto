import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_model():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_model(
        ApiId=api_id, ContentType="app/xml", Description="desc", Name="nm", Schema="cs"
    )

    assert resp["ContentType"] == "app/xml"
    assert resp["Description"] == "desc"
    assert "ModelId" in resp
    assert resp["Name"] == "nm"
    assert resp["Schema"] == "cs"


@mock_aws
def test_get_model():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    model_id = client.create_model(
        ApiId=api_id, ContentType="app/xml", Description="desc", Name="nm", Schema="cs"
    )["ModelId"]

    resp = client.get_model(ApiId=api_id, ModelId=model_id)

    assert resp["ContentType"] == "app/xml"
    assert resp["Description"] == "desc"
    assert "ModelId" in resp
    assert resp["Name"] == "nm"
    assert resp["Schema"] == "cs"


@mock_aws
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
    assert err["Code"] == "NotFoundException"


@mock_aws
def test_get_model_unknown():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    with pytest.raises(ClientError) as exc:
        client.get_model(ApiId=api_id, ModelId="unknown")

    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"


@mock_aws
def test_update_model_single_attr():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    model_id = client.create_model(
        ApiId=api_id, ContentType="app/xml", Description="desc", Name="nm", Schema="cs"
    )["ModelId"]

    model_id = client.get_model(ApiId=api_id, ModelId=model_id)["ModelId"]

    resp = client.update_model(ApiId=api_id, ModelId=model_id, Schema="cs2")

    assert resp["ContentType"] == "app/xml"
    assert resp["Description"] == "desc"
    assert "ModelId" in resp
    assert resp["Name"] == "nm"
    assert resp["Schema"] == "cs2"


@mock_aws
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

    assert resp["ContentType"] == "app/html"
    assert resp["Description"] == "html2.x"
    assert resp["Name"] == "html-schema"
    assert resp["Schema"] == "cs2"
