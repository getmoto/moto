# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_subnets():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(1)

    conn.delete_subnet(subnet.id)

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(0)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_subnet(subnet.id)
    cm.exception.code.should.equal('InvalidSubnetID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_subnet_tagging():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    subnet.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the subnet
    subnet = conn.get_all_subnets()[0]
    subnet.tags.should.have.length_of(1)
    subnet.tags["a key"].should.equal("some value")
