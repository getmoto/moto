from __future__ import unicode_literals
import boto
import sure  # noqa
import pytest
from boto.exception import EC2ResponseError

from moto import mock_ec2_deprecated


@mock_ec2_deprecated
def test_create_customer_gateways():
    conn = boto.connect_vpc("the_key", "the_secret")

    customer_gateway = conn.create_customer_gateway("ipsec.1", "205.251.242.54", 65534)
    customer_gateway.should_not.be.none
    customer_gateway.id.should.match(r"cgw-\w+")
    customer_gateway.type.should.equal("ipsec.1")
    customer_gateway.bgp_asn.should.equal(65534)
    customer_gateway.ip_address.should.equal("205.251.242.54")


@mock_ec2_deprecated
def test_describe_customer_gateways():
    conn = boto.connect_vpc("the_key", "the_secret")
    customer_gateway = conn.create_customer_gateway("ipsec.1", "205.251.242.54", 65534)
    cgws = conn.get_all_customer_gateways()
    cgws.should.have.length_of(1)
    cgws[0].id.should.match(customer_gateway.id)


@mock_ec2_deprecated
def test_delete_customer_gateways():
    conn = boto.connect_vpc("the_key", "the_secret")

    customer_gateway = conn.create_customer_gateway("ipsec.1", "205.251.242.54", 65534)
    customer_gateway.should_not.be.none
    cgws = conn.get_all_customer_gateways()
    cgws[0].id.should.match(customer_gateway.id)
    deleted = conn.delete_customer_gateway(customer_gateway.id)
    cgws = conn.get_all_customer_gateways()
    cgws.should.have.length_of(0)


@mock_ec2_deprecated
def test_delete_customer_gateways_bad_id():
    conn = boto.connect_vpc("the_key", "the_secret")
    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_customer_gateway("cgw-0123abcd")
