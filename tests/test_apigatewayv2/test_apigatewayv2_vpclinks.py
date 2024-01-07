import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_get_vpc_links_empty():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    resp = client.get_vpc_links()
    assert resp["Items"] == []


@mock_aws
def test_create_vpc_links():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    resp = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )

    assert "CreatedDate" in resp
    assert resp["Name"] == "vpcl"
    assert resp["SecurityGroupIds"] == ["sg1", "sg2"]
    assert resp["SubnetIds"] == ["sid1", "sid2"]
    assert resp["Tags"] == {"key1": "value1"}
    assert "VpcLinkId" in resp
    assert resp["VpcLinkStatus"] == "AVAILABLE"
    assert resp["VpcLinkVersion"] == "V2"


@mock_aws
def test_get_vpc_link():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    vpc_link_id = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )["VpcLinkId"]

    resp = client.get_vpc_link(VpcLinkId=vpc_link_id)

    assert "CreatedDate" in resp
    assert resp["Name"] == "vpcl"
    assert resp["SecurityGroupIds"] == ["sg1", "sg2"]
    assert resp["SubnetIds"] == ["sid1", "sid2"]
    assert resp["Tags"] == {"key1": "value1"}
    assert "VpcLinkId" in resp
    assert resp["VpcLinkStatus"] == "AVAILABLE"
    assert resp["VpcLinkVersion"] == "V2"


@mock_aws
def test_get_vpc_link_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_vpc_link(VpcLinkId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid VpcLink identifier specified unknown"


@mock_aws
def test_get_vpc_links():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    vpc_link_id = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )["VpcLinkId"]

    links = client.get_vpc_links()["Items"]
    assert len(links) == 1
    assert links[0]["VpcLinkId"] == vpc_link_id

    client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )

    links = client.get_vpc_links()["Items"]
    assert len(links) == 2


@mock_aws
def test_delete_vpc_link():
    client = boto3.client("apigatewayv2", region_name="eu-north-1")

    vpc_link_id = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )["VpcLinkId"]

    links = client.get_vpc_links()["Items"]
    assert len(links) == 1

    client.delete_vpc_link(VpcLinkId=vpc_link_id)

    links = client.get_vpc_links()["Items"]
    assert len(links) == 0


@mock_aws
def test_update_vpc_link():
    client = boto3.client("apigatewayv2", region_name="eu-north-1")
    vpc_link_id = client.create_vpc_link(
        Name="vpcl",
        SecurityGroupIds=["sg1", "sg2"],
        SubnetIds=["sid1", "sid2"],
        Tags={"key1": "value1"},
    )["VpcLinkId"]

    resp = client.update_vpc_link(VpcLinkId=vpc_link_id, Name="vpcl2")

    assert "CreatedDate" in resp
    assert resp["Name"] == "vpcl2"
    assert resp["SecurityGroupIds"] == ["sg1", "sg2"]
    assert resp["SubnetIds"] == ["sid1", "sid2"]
    assert resp["Tags"] == {"key1": "value1"}
    assert "VpcLinkId" in resp
    assert resp["VpcLinkStatus"] == "AVAILABLE"
    assert resp["VpcLinkVersion"] == "V2"


@mock_aws
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

    assert "CreatedDate" in resp
    assert resp["Name"] == "vpcl"
    assert resp["SecurityGroupIds"] == ["sg1", "sg2"]
    assert resp["SubnetIds"] == ["sid1", "sid2"]
    assert resp["Tags"] == {"key2": "val2"}
    assert "VpcLinkId" in resp
    assert resp["VpcLinkStatus"] == "AVAILABLE"
    assert resp["VpcLinkVersion"] == "V2"
