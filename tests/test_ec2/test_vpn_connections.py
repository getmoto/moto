from __future__ import unicode_literals

import boto
import boto3
import pytest
import sure  # noqa
from boto.exception import EC2ResponseError
from moto import mock_ec2, mock_ec2_deprecated


@mock_ec2_deprecated
def test_create_vpn_connections():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_connection = conn.create_vpn_connection(
        "ipsec.1", "vgw-0123abcd", "cgw-0123abcd"
    )
    vpn_connection.should_not.be.none
    vpn_connection.id.should.match(r"vpn-\w+")
    vpn_connection.type.should.equal("ipsec.1")


@mock_ec2_deprecated
def test_delete_vpn_connections():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_connection = conn.create_vpn_connection(
        "ipsec.1", "vgw-0123abcd", "cgw-0123abcd"
    )
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(1)
    conn.delete_vpn_connection(vpn_connection.id)
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(0)


@mock_ec2_deprecated
def test_delete_vpn_connections_bad_id():
    conn = boto.connect_vpc("the_key", "the_secret")
    with pytest.raises(EC2ResponseError):
        conn.delete_vpn_connection("vpn-0123abcd")


@mock_ec2_deprecated
def test_describe_vpn_connections():
    conn = boto.connect_vpc("the_key", "the_secret")
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(0)
    conn.create_vpn_connection("ipsec.1", "vgw-0123abcd", "cgw-0123abcd")
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(1)
    vpn = conn.create_vpn_connection("ipsec.1", "vgw-1234abcd", "cgw-1234abcd")
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(2)
    list_of_vpn_connections = conn.get_all_vpn_connections(vpn.id)
    list_of_vpn_connections.should.have.length_of(1)


@mock_ec2
def test_create_vpn_connection_with_vpn_gateway():
    client = boto3.client("ec2", region_name="us-east-1")

    vpn_gateway = client.create_vpn_gateway(Type="ipsec.1").get("VpnGateway", {})
    customer_gateway = client.create_customer_gateway(
        Type="ipsec.1", PublicIp="205.251.242.54", BgpAsn=65534,
    ).get("CustomerGateway", {})
    vpn_connection = client.create_vpn_connection(
        Type="ipsec.1",
        VpnGatewayId=vpn_gateway["VpnGatewayId"],
        CustomerGatewayId=customer_gateway["CustomerGatewayId"],
    ).get("VpnConnection", {})

    vpn_connection["Type"].should.equal("ipsec.1")
    vpn_connection["VpnGatewayId"].should.equal(vpn_gateway["VpnGatewayId"])
    vpn_connection["CustomerGatewayId"].should.equal(
        customer_gateway["CustomerGatewayId"]
    )
