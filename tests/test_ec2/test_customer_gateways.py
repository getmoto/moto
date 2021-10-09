from __future__ import unicode_literals
import boto
import boto3
import sure  # noqa
import pytest
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError

from moto import mock_ec2_deprecated, mock_ec2


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_customer_gateways():
    conn = boto.connect_vpc("the_key", "the_secret")

    customer_gateway = conn.create_customer_gateway("ipsec.1", "205.251.242.54", 65534)
    customer_gateway.should_not.be.none
    customer_gateway.id.should.match(r"cgw-\w+")
    customer_gateway.type.should.equal("ipsec.1")
    customer_gateway.bgp_asn.should.equal(65534)
    customer_gateway.ip_address.should.equal("205.251.242.54")


@mock_ec2
def test_create_customer_gateways_boto3():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    customer_gateway = create_customer_gateway(ec2)
    customer_gateway.should.have.key("CustomerGatewayId").match(r"cgw-\w+")
    customer_gateway.should.have.key("Type").equal("ipsec.1")
    customer_gateway.should.have.key("BgpAsn").equal("65534")
    customer_gateway.should.have.key("IpAddress").equal("205.251.242.54")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_describe_customer_gateways():
    conn = boto.connect_vpc("the_key", "the_secret")
    customer_gateway = conn.create_customer_gateway("ipsec.1", "205.251.242.54", 65534)
    cgws = conn.get_all_customer_gateways()
    cgws.should.have.length_of(1)
    cgws[0].id.should.match(customer_gateway.id)


@mock_ec2
def test_describe_customer_gateways_boto3():
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_delete_customer_gateways():
    conn = boto.connect_vpc("the_key", "the_secret")

    customer_gateway = conn.create_customer_gateway("ipsec.1", "205.251.242.54", 65534)
    customer_gateway.should_not.be.none
    cgws = conn.get_all_customer_gateways()
    cgws[0].id.should.match(customer_gateway.id)
    deleted = conn.delete_customer_gateway(customer_gateway.id)
    cgws = conn.get_all_customer_gateways()
    cgws[0].state.should.equal("deleted")
    cgws.should.have.length_of(1)


@mock_ec2
def test_delete_customer_gateways_boto3():
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_delete_customer_gateways_bad_id():
    conn = boto.connect_vpc("the_key", "the_secret")
    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_customer_gateway("cgw-0123abcd")


@mock_ec2
def test_delete_customer_gateways_bad_id_boto3():
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
