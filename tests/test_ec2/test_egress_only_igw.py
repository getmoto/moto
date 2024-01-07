import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc = list(ec2.vpcs.all())[0]

    res = client.create_egress_only_internet_gateway(VpcId=vpc.id)
    gateway = res["EgressOnlyInternetGateway"]
    assert gateway["EgressOnlyInternetGatewayId"].startswith("eigw-")
    assert gateway["Tags"] == []
    assert "Attachments" in gateway
    assert len(gateway["Attachments"]) == 1
    assert gateway["Attachments"][0] == {"State": "attached", "VpcId": vpc.id}


@mock_aws
def test_create_with_unknown_vpc():
    client = boto3.client("ec2", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.create_egress_only_internet_gateway(VpcId="vpc-says-what")
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidVpcID.NotFound"
    assert err["Message"] == "VpcID vpc-says-what does not exist."


@mock_aws
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
    assert gw1 in gateways
    assert gw2 in gateways


@mock_aws
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
    assert len(gateways) == 2
    assert gw1 in gateways
    assert gw3 in gateways


@mock_aws
def test_create_and_delete():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc = list(ec2.vpcs.all())[0]

    gw1 = client.create_egress_only_internet_gateway(VpcId=vpc.id)[
        "EgressOnlyInternetGateway"
    ]
    gw1_id = gw1["EgressOnlyInternetGatewayId"]

    assert (
        len(
            client.describe_egress_only_internet_gateways(
                EgressOnlyInternetGatewayIds=[gw1_id]
            )["EgressOnlyInternetGateways"]
        )
        == 1
    )

    client.delete_egress_only_internet_gateway(EgressOnlyInternetGatewayId=gw1_id)

    assert (
        len(
            client.describe_egress_only_internet_gateways(
                EgressOnlyInternetGatewayIds=[gw1_id]
            )["EgressOnlyInternetGateways"]
        )
        == 0
    )
