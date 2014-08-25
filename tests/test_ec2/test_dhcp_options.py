# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
from boto.exception import EC2ResponseError

import sure  # noqa

from moto import mock_ec2

SAMPLE_DOMAIN_NAME = u'example.com'
SAMPLE_NAME_SERVERS = [u'10.0.0.6', u'10.0.0.7']


@mock_ec2
def test_dhcp_options_associate():
    """ associate dhcp option """
    conn = boto.connect_vpc('the_key', 'the_secret')
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    vpc = conn.create_vpc("10.0.0.0/16")

    rval = conn.associate_dhcp_options(dhcp_options.id, vpc.id)
    rval.should.be.equal(True)


@mock_ec2
def test_dhcp_options_associate_invalid_dhcp_id():
    """ associate dhcp option bad dhcp options id """
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    with assert_raises(EC2ResponseError) as cm:
        conn.associate_dhcp_options("foo", vpc.id)
    cm.exception.code.should.equal('InvalidDhcpOptionID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_dhcp_options_associate_invalid_vpc_id():
    """ associate dhcp option invalid vpc id """
    conn = boto.connect_vpc('the_key', 'the_secret')
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)

    with assert_raises(EC2ResponseError) as cm:
        conn.associate_dhcp_options(dhcp_options.id, "foo")
    cm.exception.code.should.equal('InvalidVpcID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_dhcp_options_delete_with_vpc():
    """Test deletion of dhcp options with vpc"""
    conn = boto.connect_vpc('the_key', 'the_secret')
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    dhcp_options_id = dhcp_options.id
    vpc = conn.create_vpc("10.0.0.0/16")

    rval = conn.associate_dhcp_options(dhcp_options_id, vpc.id)
    rval.should.be.equal(True)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_dhcp_options(dhcp_options_id)
    cm.exception.code.should.equal('DependencyViolation')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    vpc.delete()

    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_dhcp_options([dhcp_options_id])
    cm.exception.code.should.equal('InvalidDhcpOptionID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_create_dhcp_options():
    """Create most basic dhcp option"""
    conn = boto.connect_vpc('the_key', 'the_secret')

    dhcp_option = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    dhcp_option.options[u'domain-name'][0].should.be.equal(SAMPLE_DOMAIN_NAME)
    dhcp_option.options[u'domain-name-servers'][0].should.be.equal(SAMPLE_NAME_SERVERS[0])
    dhcp_option.options[u'domain-name-servers'][1].should.be.equal(SAMPLE_NAME_SERVERS[1])


@mock_ec2
def test_create_dhcp_options_invalid_options():
    """Create invalid dhcp options"""
    conn = boto.connect_vpc('the_key', 'the_secret')
    servers = ["f", "f", "f", "f", "f"]

    with assert_raises(EC2ResponseError) as cm:
        conn.create_dhcp_options(ntp_servers=servers)
    cm.exception.code.should.equal('InvalidParameterValue')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    with assert_raises(EC2ResponseError) as cm:
        conn.create_dhcp_options(netbios_node_type="0")
    cm.exception.code.should.equal('InvalidParameterValue')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_describe_dhcp_options():
    """Test dhcp options lookup by id"""
    conn = boto.connect_vpc('the_key', 'the_secret')

    dhcp_option = conn.create_dhcp_options()
    dhcp_options = conn.get_all_dhcp_options([dhcp_option.id])
    dhcp_options.should.be.length_of(1)

    dhcp_options = conn.get_all_dhcp_options()
    dhcp_options.should.be.length_of(1)


@mock_ec2
def test_describe_dhcp_options_invalid_id():
    """get error on invalid dhcp_option_id lookup"""
    conn = boto.connect_vpc('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_dhcp_options(["1"])
    cm.exception.code.should.equal('InvalidDhcpOptionID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_delete_dhcp_options():
    """delete dhcp option"""
    conn = boto.connect_vpc('the_key', 'the_secret')

    dhcp_option = conn.create_dhcp_options()
    dhcp_options = conn.get_all_dhcp_options([dhcp_option.id])
    dhcp_options.should.be.length_of(1)

    conn.delete_dhcp_options(dhcp_option.id)  # .should.be.equal(True)

    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_dhcp_options([dhcp_option.id])
    cm.exception.code.should.equal('InvalidDhcpOptionID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_delete_dhcp_options_invalid_id():
    conn = boto.connect_vpc('the_key', 'the_secret')

    conn.create_dhcp_options()

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_dhcp_options("dopt-abcd1234")
    cm.exception.code.should.equal('InvalidDhcpOptionID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_delete_dhcp_options_malformed_id():
    conn = boto.connect_vpc('the_key', 'the_secret')

    conn.create_dhcp_options()

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_dhcp_options("foo-abcd1234")
    cm.exception.code.should.equal('InvalidDhcpOptionsId.Malformed')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_dhcp_tagging():
    conn = boto.connect_vpc('the_key', 'the_secret')
    dhcp_option = conn.create_dhcp_options()

    dhcp_option.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the DHCP options
    dhcp_option = conn.get_all_dhcp_options()[0]
    dhcp_option.tags.should.have.length_of(1)
    dhcp_option.tags["a key"].should.equal("some value")
