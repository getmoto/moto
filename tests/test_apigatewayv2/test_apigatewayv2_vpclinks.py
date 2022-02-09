import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_get_vpc_links_empty():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    resp = client.get_vpc_links()
    resp.should.have.key("Items").equals([])


@mock_apigatewayv2
def test_create_vpc_links():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    resp = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )

    resp.should.have.key("CreatedDate")
    resp.should.have.key("Name").equals("vpcl")
    resp.should.have.key("SecurityGroupIds").equals(["sg1", "sg2"])
    resp.should.have.key("SubnetIds").equals(["sid1", "sid2"])
    resp.should.have.key("Tags").equals({"key1": "value1"})
    resp.should.have.key("VpcLinkId")
    resp.should.have.key("VpcLinkStatus").equals("AVAILABLE")
    resp.should.have.key("VpcLinkVersion").equals("V2")


@mock_apigatewayv2
def test_get_vpc_link():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    vpc_link_id = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )["VpcLinkId"]

    resp = client.get_vpc_link(VpcLinkId=vpc_link_id)

    resp.should.have.key("CreatedDate")
    resp.should.have.key("Name").equals("vpcl")
    resp.should.have.key("SecurityGroupIds").equals(["sg1", "sg2"])
    resp.should.have.key("SubnetIds").equals(["sid1", "sid2"])
    resp.should.have.key("Tags").equals({"key1": "value1"})
    resp.should.have.key("VpcLinkId")
    resp.should.have.key("VpcLinkStatus").equals("AVAILABLE")
    resp.should.have.key("VpcLinkVersion").equals("V2")


@mock_apigatewayv2
def test_get_vpc_link_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_vpc_link(VpcLinkId="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("Invalid VpcLink identifier specified unknown")


@mock_apigatewayv2
def test_get_vpc_links():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    vpc_link_id = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )["VpcLinkId"]

    links = client.get_vpc_links()["Items"]
    links.should.have.length_of(1)
    links[0]["VpcLinkId"].should.equal(vpc_link_id)

    client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )

    links = client.get_vpc_links()["Items"]
    links.should.have.length_of(2)


@mock_apigatewayv2
def test_delete_vpc_link():
    client = boto3.client("apigatewayv2", region_name="eu-north-1")

    vpc_link_id = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )["VpcLinkId"]

    links = client.get_vpc_links()["Items"]
    links.should.have.length_of(1)

    client.delete_vpc_link(VpcLinkId=vpc_link_id)

    links = client.get_vpc_links()["Items"]
    links.should.have.length_of(0)


@mock_apigatewayv2
def test_update_vpc_link():
    client = boto3.client("apigatewayv2", region_name="eu-north-1")
    vpc_link_id = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )["VpcLinkId"]

    resp = client.update_vpc_link(VpcLinkId=vpc_link_id, Name="vpcl2")

    resp.should.have.key("CreatedDate")
    resp.should.have.key("Name").equals("vpcl2")
    resp.should.have.key("SecurityGroupIds").equals(["sg1", "sg2"])
    resp.should.have.key("SubnetIds").equals(["sid1", "sid2"])
    resp.should.have.key("Tags").equals({"key1": "value1"})
    resp.should.have.key("VpcLinkId")
    resp.should.have.key("VpcLinkStatus").equals("AVAILABLE")
    resp.should.have.key("VpcLinkVersion").equals("V2")


@mock_apigatewayv2
def test_untag_vpc_link():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    vpc_link_id = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"Key1": "value1", "key2": "val2"},
    )["VpcLinkId"]

    arn = f"arn:aws:apigateway:eu-west-1::/vpclinks/{vpc_link_id}"
    client.untag_resource(ResourceArn=arn, TagKeys=["Key1"])

    resp = client.get_vpc_link(VpcLinkId=vpc_link_id)

    resp.should.have.key("CreatedDate")
    resp.should.have.key("Name").equals("vpcl")
    resp.should.have.key("SecurityGroupIds").equals(["sg1", "sg2"])
    resp.should.have.key("SubnetIds").equals(["sid1", "sid2"])
    resp.should.have.key("Tags").equals({"key2": "val2"})
    resp.should.have.key("VpcLinkId")
    resp.should.have.key("VpcLinkStatus").equals("AVAILABLE")
    resp.should.have.key("VpcLinkVersion").equals("V2")
