import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest
from botocore.exceptions import ClientError
from moto import mock_ec2, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from unittest import SkipTest


@mock_ec2
def test_describe_carrier_gateways_none():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.describe_carrier_gateways()["CarrierGateways"].should.equal([])


@mock_ec2
def test_describe_carrier_gateways_multiple():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cg1 = client.create_carrier_gateway(VpcId=vpc.id)["CarrierGateway"]
    cg2 = client.create_carrier_gateway(VpcId=vpc.id)["CarrierGateway"]

    gateways = client.describe_carrier_gateways()["CarrierGateways"]
    gateway_ids = [g["CarrierGatewayId"] for g in gateways]

    gateway_ids.should.contain(cg1["CarrierGatewayId"])
    gateway_ids.should.contain(cg2["CarrierGatewayId"])

    find_one = client.describe_carrier_gateways(
        CarrierGatewayIds=[cg1["CarrierGatewayId"]]
    )["CarrierGateways"]
    find_one.should.have.length_of(1)
    find_one[0]["CarrierGatewayId"].should.equal(cg1["CarrierGatewayId"])

    find_one = client.describe_carrier_gateways(
        CarrierGatewayIds=[cg2["CarrierGatewayId"], "non-existant"]
    )["CarrierGateways"]
    find_one.should.have.length_of(1)
    find_one[0]["CarrierGatewayId"].should.equal(cg2["CarrierGatewayId"])


@mock_ec2
def test_create_carrier_gateways_without_tags():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cg = client.create_carrier_gateway(VpcId=vpc.id)["CarrierGateway"]

    cg.should.have.key("CarrierGatewayId").match("cagw-[a-z0-9]+")
    cg.should.have.key("VpcId").equal(vpc.id)
    cg.should.have.key("State").equal("available")
    cg.should.have.key("OwnerId").equal(ACCOUNT_ID)
    cg.should.have.key("Tags").equal([])


@mock_ec2
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

    cg.should.have.key("CarrierGatewayId").match("cagw-[a-z0-9]+")
    cg.should.have.key("VpcId").equal(vpc.id)
    cg.should.have.key("State").equal("available")
    cg.should.have.key("OwnerId").equal(ACCOUNT_ID)
    cg.should.have.key("Tags").should.equal([{"Key": "tk", "Value": "tv"}])


@mock_ec2
def test_create_carrier_gateways_invalid_vpc():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        ec2.create_carrier_gateway(VpcId="vpc-asdf")
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidVpcID.NotFound")
    err["Message"].should.equal("VpcID vpc-asdf does not exist.")


@mock_ec2
def test_delete_carrier_gateways():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cg = client.create_carrier_gateway(VpcId=vpc.id)["CarrierGateway"]
    client.delete_carrier_gateway(CarrierGatewayId=cg["CarrierGatewayId"])

    gateways = client.describe_carrier_gateways()["CarrierGateways"]
    gateway_ids = [g["CarrierGatewayId"] for g in gateways]

    gateway_ids.shouldnt.contain(cg["CarrierGatewayId"])
