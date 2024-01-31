from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_describe_carrier_gateways_none():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    assert ec2.describe_carrier_gateways()["CarrierGateways"] == []


@mock_aws
def test_describe_carrier_gateways_multiple():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cg1 = client.create_carrier_gateway(VpcId=vpc.id)["CarrierGateway"]
    cg2 = client.create_carrier_gateway(VpcId=vpc.id)["CarrierGateway"]

    gateways = client.describe_carrier_gateways()["CarrierGateways"]
    gateway_ids = [g["CarrierGatewayId"] for g in gateways]

    assert cg1["CarrierGatewayId"] in gateway_ids
    assert cg2["CarrierGatewayId"] in gateway_ids

    find_one = client.describe_carrier_gateways(
        CarrierGatewayIds=[cg1["CarrierGatewayId"]]
    )["CarrierGateways"]
    assert len(find_one) == 1
    assert find_one[0]["CarrierGatewayId"] == cg1["CarrierGatewayId"]

    find_one = client.describe_carrier_gateways(
        CarrierGatewayIds=[cg2["CarrierGatewayId"], "non-existant"]
    )["CarrierGateways"]
    assert len(find_one) == 1
    assert find_one[0]["CarrierGatewayId"] == cg2["CarrierGatewayId"]


@mock_aws
def test_create_carrier_gateways_without_tags():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cg = client.create_carrier_gateway(VpcId=vpc.id)["CarrierGateway"]

    assert cg["CarrierGatewayId"].startswith("cagw-")
    assert cg["VpcId"] == vpc.id
    assert cg["State"] == "available"
    assert cg["OwnerId"] == ACCOUNT_ID
    assert cg["Tags"] == []


@mock_aws
def test_create_carrier_gateways_with_tags():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cg = client.create_carrier_gateway(
        VpcId=vpc.id,
        TagSpecifications=[
            {"ResourceType": "CarrierGateway", "Tags": [{"Key": "tk", "Value": "tv"}]}
        ],
    )["CarrierGateway"]

    assert cg["CarrierGatewayId"].startswith("cagw-")
    assert cg["VpcId"] == vpc.id
    assert cg["State"] == "available"
    assert cg["OwnerId"] == ACCOUNT_ID
    assert cg["Tags"] == [{"Key": "tk", "Value": "tv"}]


@mock_aws
def test_create_carrier_gateways_invalid_vpc():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        ec2.create_carrier_gateway(VpcId="vpc-asdf")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidVpcID.NotFound"
    assert err["Message"] == "VpcID vpc-asdf does not exist."


@mock_aws
def test_delete_carrier_gateways():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cg = client.create_carrier_gateway(VpcId=vpc.id)["CarrierGateway"]
    client.delete_carrier_gateway(CarrierGatewayId=cg["CarrierGatewayId"])

    gateways = client.describe_carrier_gateways()["CarrierGateways"]
    gateway_ids = [g["CarrierGatewayId"] for g in gateways]

    assert cg["CarrierGatewayId"] not in gateway_ids
