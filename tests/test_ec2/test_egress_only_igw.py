import boto3
import pytest
import sure  # noqa

from botocore.exceptions import ClientError
from moto import mock_ec2


@mock_ec2
def test_create():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc = list(ec2.vpcs.all())[0]

    res = client.create_egress_only_internet_gateway(VpcId=vpc.id)
    gateway = res["EgressOnlyInternetGateway"]
    gateway.should.have.key("EgressOnlyInternetGatewayId").match("eigw-[a-z0-9]+")
    gateway.should.have.key("Tags").equal([])
    gateway.should.have.key("Attachments")
    gateway["Attachments"].should.have.length_of(1)
    gateway["Attachments"][0].should.equal({"State": "attached", "VpcId": vpc.id})


@mock_ec2
def test_create_with_unknown_vpc():
    client = boto3.client("ec2", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.create_egress_only_internet_gateway(VpcId="vpc-says-what")
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidVpcID.NotFound")
    err["Message"].should.equal("VpcID vpc-says-what does not exist.")


@mock_ec2
def test_describe_all():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc = list(ec2.vpcs.all())[0]

    gw1 = client.create_egress_only_internet_gateway(VpcId=vpc.id)[
        "EgressOnlyInternetGateway"
    ]
    gw2 = client.create_egress_only_internet_gateway(VpcId=vpc.id)[
        "EgressOnlyInternetGateway"
    ]

    gateways = client.describe_egress_only_internet_gateways()[
        "EgressOnlyInternetGateways"
    ]
    assert len(gateways) >= 2, "Should have two recently created gateways"
    gateways.should.contain(gw1)
    gateways.should.contain(gw2)


@mock_ec2
def test_describe_one():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc = list(ec2.vpcs.all())[0]

    gw1 = client.create_egress_only_internet_gateway(VpcId=vpc.id)[
        "EgressOnlyInternetGateway"
    ]
    gw1_id = gw1["EgressOnlyInternetGatewayId"]
    client.create_egress_only_internet_gateway(VpcId=vpc.id)[
        "EgressOnlyInternetGateway"
    ]
    gw3 = client.create_egress_only_internet_gateway(VpcId=vpc.id)[
        "EgressOnlyInternetGateway"
    ]
    gw3_id = gw3["EgressOnlyInternetGatewayId"]

    gateways = client.describe_egress_only_internet_gateways(
        EgressOnlyInternetGatewayIds=[gw1_id, gw3_id]
    )["EgressOnlyInternetGateways"]
    gateways.should.have.length_of(2)
    gateways.should.contain(gw1)
    gateways.should.contain(gw3)


@mock_ec2
def test_create_and_delete():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc = list(ec2.vpcs.all())[0]

    gw1 = client.create_egress_only_internet_gateway(VpcId=vpc.id)[
        "EgressOnlyInternetGateway"
    ]
    gw1_id = gw1["EgressOnlyInternetGatewayId"]

    client.describe_egress_only_internet_gateways(
        EgressOnlyInternetGatewayIds=[gw1_id]
    )["EgressOnlyInternetGateways"].should.have.length_of(1)

    client.delete_egress_only_internet_gateway(EgressOnlyInternetGatewayId=gw1_id)

    client.describe_egress_only_internet_gateways(
        EgressOnlyInternetGatewayIds=[gw1_id]
    )["EgressOnlyInternetGateways"].should.have.length_of(0)
