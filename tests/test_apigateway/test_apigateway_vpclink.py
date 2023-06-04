import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigateway


@mock_apigateway
def test_get_vpc_links_empty():
    client = boto3.client("apigateway", region_name="eu-west-1")

    resp = client.get_vpc_links()
    assert resp["items"] == []


@mock_apigateway
def test_create_vpc_link():
    client = boto3.client("apigateway", region_name="eu-west-1")

    resp = client.create_vpc_link(
        name="vpcl",
        description="my first vpc link",
        targetArns=["elb:target:arn"],
        tags={"key1": "value1"},
    )

    assert "id" in resp
    assert resp["name"] == "vpcl"
    assert resp["description"] == "my first vpc link"
    assert resp["targetArns"] == ["elb:target:arn"]
    assert resp["status"] == "AVAILABLE"
    assert resp["tags"] == {"key1": "value1"}


@mock_apigateway
def test_get_vpc_link():
    client = boto3.client("apigateway", region_name="eu-west-1")

    vpc_link_id = client.create_vpc_link(
        name="vpcl",
        description="my first vpc link",
        targetArns=["elb:target:arn"],
        tags={"key1": "value1"},
    )["id"]

    resp = client.get_vpc_link(vpcLinkId=vpc_link_id)

    assert "id" in resp
    assert resp["name"] == "vpcl"
    assert resp["description"] == "my first vpc link"
    assert resp["targetArns"] == ["elb:target:arn"]
    assert resp["status"] == "AVAILABLE"
    assert resp["tags"] == {"key1": "value1"}


@mock_apigateway
def test_get_vpc_link_unknown():
    client = boto3.client("apigateway", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_vpc_link(vpcLinkId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "VPCLink not found"


@mock_apigateway
def test_get_vpc_links():
    client = boto3.client("apigateway", region_name="eu-west-1")

    vpc_link_id = client.create_vpc_link(
        name="vpcl",
        description="my first vpc link",
        targetArns=["elb:target:arn"],
        tags={"key1": "value1"},
    )["id"]

    links = client.get_vpc_links()["items"]
    assert len(links) == 1
    assert links[0]["id"] == vpc_link_id

    client.create_vpc_link(
        name="vpcl2",
        description="my first vpc link",
        targetArns=["elb:target:arn"],
        tags={"key2": "value2"},
    )

    links = client.get_vpc_links()["items"]
    assert len(links) == 2


@mock_apigateway
def test_delete_vpc_link():
    client = boto3.client("apigateway", region_name="eu-north-1")

    vpc_link_id = client.create_vpc_link(
        name="vpcl",
        description="my first vpc link",
        targetArns=["elb:target:arn"],
        tags={"key1": "value1"},
    )["id"]

    links = client.get_vpc_links()["items"]
    assert len(links) == 1

    client.delete_vpc_link(vpcLinkId=vpc_link_id)

    links = client.get_vpc_links()["items"]
    assert len(links) == 0
