import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_ec2


@mock_ec2
def test_create_customer_gateways():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    customer_gateway = create_customer_gateway(ec2)
    assert customer_gateway["CustomerGatewayId"].startswith("cgw-")
    assert customer_gateway["Type"] == "ipsec.1"
    assert customer_gateway["BgpAsn"] == "65534"
    assert customer_gateway["IpAddress"] == "205.251.242.54"


@mock_ec2
def test_create_customer_gateways_using_publicip_argument():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    # The PublicIp-argument is deprecated, but should still be supported by Moto
    # https://github.com/boto/botocore/commit/86202c8698cf77fb6ecccfdbc05bbc218e861d14#diff-c51449716bfc26c1eac92ec403b470827d2dcba1126cf303567074b872d5c592
    customer_gateway = ec2.create_customer_gateway(
        Type="ipsec.1", IpAddress="205.251.242.53", BgpAsn=65534
    )["CustomerGateway"]
    customer_gateway["CustomerGatewayId"].startswith("cgw-")
    assert customer_gateway["Type"] == "ipsec.1"
    assert customer_gateway["BgpAsn"] == "65534"
    assert customer_gateway["IpAddress"] == "205.251.242.53"


@mock_ec2
def test_describe_customer_gateways_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_customer_gateways(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DescribeCustomerGateways operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_describe_customer_gateways():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    customer_gateway = create_customer_gateway(ec2)
    cg_id = customer_gateway["CustomerGatewayId"]

    cgws = ec2.describe_customer_gateways()["CustomerGateways"]
    cg_ids = [cg["CustomerGatewayId"] for cg in cgws]
    assert cg_id in cg_ids

    cgw = ec2.describe_customer_gateways(CustomerGatewayIds=[cg_id])[
        "CustomerGateways"
    ][0]
    assert "BgpAsn" in cgw
    assert cgw["CustomerGatewayId"] == cg_id
    assert "IpAddress" in cgw
    assert cgw["State"] == "available"
    assert cgw["Type"] == "ipsec.1"

    all_cgws = ec2.describe_customer_gateways()["CustomerGateways"]
    assert (
        len(all_cgws) >= 1
    ), "Should have at least the one CustomerGateway we just created"


@mock_ec2
def test_delete_customer_gateways():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    customer_gateway = create_customer_gateway(ec2)
    cg_id = customer_gateway["CustomerGatewayId"]

    cgws = ec2.describe_customer_gateways(CustomerGatewayIds=[cg_id])[
        "CustomerGateways"
    ]
    assert len(cgws) == 1
    assert cgws[0]["State"] == "available"

    ec2.delete_customer_gateway(CustomerGatewayId=customer_gateway["CustomerGatewayId"])

    cgws = ec2.describe_customer_gateways(CustomerGatewayIds=[cg_id])[
        "CustomerGateways"
    ]
    assert len(cgws) == 1
    assert cgws[0]["State"] == "deleted"


@mock_ec2
def test_delete_customer_gateways_bad_id():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        ec2.delete_customer_gateway(CustomerGatewayId="cgw-0123abcd")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidCustomerGatewayID.NotFound"


def create_customer_gateway(ec2):
    return ec2.create_customer_gateway(
        Type="ipsec.1", PublicIp="205.251.242.54", BgpAsn=65534
    )["CustomerGateway"]
