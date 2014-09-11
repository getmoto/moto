from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_vpcs():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    vpc.cidr_block.should.equal('10.0.0.0/16')

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(1)

    vpc.delete()

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(0)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_vpc("vpc-1234abcd")
    cm.exception.code.should.equal('InvalidVpcID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_vpc_defaults():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    conn.get_all_vpcs().should.have.length_of(1)
    conn.get_all_route_tables().should.have.length_of(1)
    conn.get_all_security_groups().should.have.length_of(1)

    vpc.delete()

    conn.get_all_vpcs().should.have.length_of(0)
    conn.get_all_route_tables().should.have.length_of(0)
    conn.get_all_security_groups().should.have.length_of(0)


@mock_ec2
def test_vpc_tagging():
    conn = boto.connect_vpc()
    vpc = conn.create_vpc("10.0.0.0/16")

    vpc.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the vpc
    vpc = conn.get_all_vpcs()[0]
    vpc.tags.should.have.length_of(1)
    vpc.tags["a key"].should.equal("some value")
