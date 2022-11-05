import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
import sys

from botocore.exceptions import ClientError
from moto import mock_ec2
from unittest import SkipTest


@mock_ec2
def test_create_customer_gateways():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    customer_gateway = create_customer_gateway(ec2)
    customer_gateway.should.have.key("CustomerGatewayId").match(r"cgw-\w+")
    customer_gateway.should.have.key("Type").equal("ipsec.1")
    customer_gateway.should.have.key("BgpAsn").equal("65534")
    customer_gateway.should.have.key("IpAddress").equal("205.251.242.54")


@mock_ec2
def test_create_customer_gateways_using_publicip_argument():
    version_info = sys.version_info
    if version_info.major == 3 and version_info.minor <= 6:
        raise SkipTest(
            "Py 3.6 has an older versions of botocore, and does not support the IpAddress-argument"
        )
    ec2 = boto3.client("ec2", region_name="us-east-1")

    # The PublicIp-argument is deprecated, but should still be supported by Moto
    # https://github.com/boto/botocore/commit/86202c8698cf77fb6ecccfdbc05bbc218e861d14#diff-c51449716bfc26c1eac92ec403b470827d2dcba1126cf303567074b872d5c592
    customer_gateway = ec2.create_customer_gateway(
        Type="ipsec.1", IpAddress="205.251.242.53", BgpAsn=65534
    )["CustomerGateway"]
    customer_gateway.should.have.key("CustomerGatewayId").match(r"cgw-\w+")
    customer_gateway.should.have.key("Type").equal("ipsec.1")
    customer_gateway.should.have.key("BgpAsn").equal("65534")
    customer_gateway.should.have.key("IpAddress").equal("205.251.242.53")


@mock_ec2
def test_describe_customer_gateways_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_customer_gateways(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DescribeCustomerGateways operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_describe_customer_gateways():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    customer_gateway = create_customer_gateway(ec2)
    cg_id = customer_gateway["CustomerGatewayId"]

    cgws = ec2.describe_customer_gateways()["CustomerGateways"]
    cg_ids = [cg["CustomerGatewayId"] for cg in cgws]
    cg_ids.should.contain(cg_id)

    cgw = ec2.describe_customer_gateways(CustomerGatewayIds=[cg_id])[
        "CustomerGateways"
    ][0]
    cgw.should.have.key("BgpAsn")
    cgw.should.have.key("CustomerGatewayId").equal(cg_id)
    cgw.should.have.key("IpAddress")
    cgw.should.have.key("State").equal("available")
    cgw.should.have.key("Type").equal("ipsec.1")

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
    cgws.should.have.length_of(1)
    cgws[0].should.have.key("State").equal("available")

    ec2.delete_customer_gateway(CustomerGatewayId=customer_gateway["CustomerGatewayId"])

    cgws = ec2.describe_customer_gateways(CustomerGatewayIds=[cg_id])[
        "CustomerGateways"
    ]
    cgws.should.have.length_of(1)
    cgws[0].should.have.key("State").equal("deleted")


@mock_ec2
def test_delete_customer_gateways_bad_id():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        ec2.delete_customer_gateway(CustomerGatewayId="cgw-0123abcd")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidCustomerGatewayID.NotFound")


def create_customer_gateway(ec2):
    return ec2.create_customer_gateway(
        Type="ipsec.1", PublicIp="205.251.242.54", BgpAsn=65534
    )["CustomerGateway"]
