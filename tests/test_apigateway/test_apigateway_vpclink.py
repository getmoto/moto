import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigateway


@mock_apigateway
def test_get_vpc_links_empty():
    client = boto3.client("apigateway", region_name="eu-west-1")

    resp = client.get_vpc_links()
    resp.should.have.key("items").equals([])


@mock_apigateway
def test_create_vpc_link():
    client = boto3.client("apigateway", region_name="eu-west-1")

    resp = client.create_vpc_link(
        name="vpcl",
        description="my first vpc link",
        targetArns=["elb:target:arn"],
        tags={"key1": "value1"},
    )

    resp.should.have.key("id")
    resp.should.have.key("name").equals("vpcl")
    resp.should.have.key("description").equals("my first vpc link")
    resp.should.have.key("targetArns").equals(["elb:target:arn"])
    resp.should.have.key("status").equals("AVAILABLE")
    resp.should.have.key("tags").equals({"key1": "value1"})


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

    resp.should.have.key("id")
    resp.should.have.key("name").equals("vpcl")
    resp.should.have.key("description").equals("my first vpc link")
    resp.should.have.key("targetArns").equals(["elb:target:arn"])
    resp.should.have.key("status").equals("AVAILABLE")
    resp.should.have.key("tags").equals({"key1": "value1"})


@mock_apigateway
def test_get_vpc_link_unknown():
    client = boto3.client("apigateway", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_vpc_link(vpcLinkId="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("VPCLink not found")


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
    links.should.have.length_of(1)
    links[0]["id"].should.equal(vpc_link_id)

    client.create_vpc_link(
        name="vpcl2",
        description="my first vpc link",
        targetArns=["elb:target:arn"],
        tags={"key2": "value2"},
    )

    links = client.get_vpc_links()["items"]
    links.should.have.length_of(2)


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
    links.should.have.length_of(1)

    client.delete_vpc_link(vpcLinkId=vpc_link_id)

    links = client.get_vpc_links()["items"]
    links.should.have.length_of(0)
