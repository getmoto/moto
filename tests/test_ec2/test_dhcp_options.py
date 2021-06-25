from __future__ import unicode_literals

import pytest

import boto3
import boto
from boto.exception import EC2ResponseError

import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated

SAMPLE_DOMAIN_NAME = "example.com"
SAMPLE_NAME_SERVERS = ["10.0.0.6", "10.0.0.7"]


@mock_ec2_deprecated
def test_dhcp_options_associate():
    """ associate dhcp option """
    conn = boto.connect_vpc("the_key", "the_secret")
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    vpc = conn.create_vpc("10.0.0.0/16")

    rval = conn.associate_dhcp_options(dhcp_options.id, vpc.id)
    rval.should.be.equal(True)


@mock_ec2_deprecated
def test_dhcp_options_associate_invalid_dhcp_id():
    """ associate dhcp option bad dhcp options id """
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")

    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_dhcp_options("foo", vpc.id)
    cm.value.code.should.equal("InvalidDhcpOptionID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2_deprecated
def test_dhcp_options_associate_invalid_vpc_id():
    """ associate dhcp option invalid vpc id """
    conn = boto.connect_vpc("the_key", "the_secret")
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)

    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_dhcp_options(dhcp_options.id, "foo")
    cm.value.code.should.equal("InvalidVpcID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2_deprecated
def test_dhcp_options_delete_with_vpc():
    """Test deletion of dhcp options with vpc"""
    conn = boto.connect_vpc("the_key", "the_secret")
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    dhcp_options_id = dhcp_options.id
    vpc = conn.create_vpc("10.0.0.0/16")

    rval = conn.associate_dhcp_options(dhcp_options_id, vpc.id)
    rval.should.be.equal(True)

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_dhcp_options(dhcp_options_id)
    cm.value.code.should.equal("DependencyViolation")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    vpc.delete()

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_dhcp_options([dhcp_options_id])
    cm.value.code.should.equal("InvalidDhcpOptionID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2_deprecated
def test_create_dhcp_options():
    """Create most basic dhcp option"""
    conn = boto.connect_vpc("the_key", "the_secret")

    dhcp_option = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    dhcp_option.options["domain-name"][0].should.be.equal(SAMPLE_DOMAIN_NAME)
    dhcp_option.options["domain-name-servers"][0].should.be.equal(
        SAMPLE_NAME_SERVERS[0]
    )
    dhcp_option.options["domain-name-servers"][1].should.be.equal(
        SAMPLE_NAME_SERVERS[1]
    )


@mock_ec2_deprecated
def test_create_dhcp_options_invalid_options():
    """Create invalid dhcp options"""
    conn = boto.connect_vpc("the_key", "the_secret")
    servers = ["f", "f", "f", "f", "f"]

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_dhcp_options(ntp_servers=servers)
    cm.value.code.should.equal("InvalidParameterValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_dhcp_options(netbios_node_type="0")
    cm.value.code.should.equal("InvalidParameterValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2_deprecated
def test_describe_dhcp_options():
    """Test dhcp options lookup by id"""
    conn = boto.connect_vpc("the_key", "the_secret")

    dhcp_option = conn.create_dhcp_options()
    dhcp_options = conn.get_all_dhcp_options([dhcp_option.id])
    dhcp_options.should.be.length_of(1)

    dhcp_options = conn.get_all_dhcp_options()
    dhcp_options.should.be.length_of(1)


@mock_ec2_deprecated
def test_describe_dhcp_options_invalid_id():
    """get error on invalid dhcp_option_id lookup"""
    conn = boto.connect_vpc("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_dhcp_options(["1"])
    cm.value.code.should.equal("InvalidDhcpOptionID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2_deprecated
def test_delete_dhcp_options():
    """delete dhcp option"""
    conn = boto.connect_vpc("the_key", "the_secret")

    dhcp_option = conn.create_dhcp_options()
    dhcp_options = conn.get_all_dhcp_options([dhcp_option.id])
    dhcp_options.should.be.length_of(1)

    conn.delete_dhcp_options(dhcp_option.id)  # .should.be.equal(True)

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_dhcp_options([dhcp_option.id])
    cm.value.code.should.equal("InvalidDhcpOptionID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2_deprecated
def test_delete_dhcp_options_invalid_id():
    conn = boto.connect_vpc("the_key", "the_secret")

    conn.create_dhcp_options()

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_dhcp_options("dopt-abcd1234")
    cm.value.code.should.equal("InvalidDhcpOptionID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2_deprecated
def test_delete_dhcp_options_malformed_id():
    conn = boto.connect_vpc("the_key", "the_secret")

    conn.create_dhcp_options()

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_dhcp_options("foo-abcd1234")
    cm.value.code.should.equal("InvalidDhcpOptionsId.Malformed")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2_deprecated
def test_dhcp_tagging():
    conn = boto.connect_vpc("the_key", "the_secret")
    dhcp_option = conn.create_dhcp_options()

    dhcp_option.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the DHCP options
    dhcp_option = conn.get_all_dhcp_options()[0]
    dhcp_option.tags.should.have.length_of(1)
    dhcp_option.tags["a key"].should.equal("some value")


@mock_ec2_deprecated
def test_dhcp_options_get_by_tag():
    conn = boto.connect_vpc("the_key", "the_secret")

    dhcp1 = conn.create_dhcp_options("example.com", ["10.0.10.2"])
    dhcp1.add_tag("Name", "TestDhcpOptions1")
    dhcp1.add_tag("test-tag", "test-value")

    dhcp2 = conn.create_dhcp_options("example.com", ["10.0.20.2"])
    dhcp2.add_tag("Name", "TestDhcpOptions2")
    dhcp2.add_tag("test-tag", "test-value")

    filters = {"tag:Name": "TestDhcpOptions1", "tag:test-tag": "test-value"}
    dhcp_options_sets = conn.get_all_dhcp_options(filters=filters)

    dhcp_options_sets.should.have.length_of(1)
    dhcp_options_sets[0].options["domain-name"][0].should.be.equal("example.com")
    dhcp_options_sets[0].options["domain-name-servers"][0].should.be.equal("10.0.10.2")
    dhcp_options_sets[0].tags["Name"].should.equal("TestDhcpOptions1")
    dhcp_options_sets[0].tags["test-tag"].should.equal("test-value")

    filters = {"tag:Name": "TestDhcpOptions2", "tag:test-tag": "test-value"}
    dhcp_options_sets = conn.get_all_dhcp_options(filters=filters)

    dhcp_options_sets.should.have.length_of(1)
    dhcp_options_sets[0].options["domain-name"][0].should.be.equal("example.com")
    dhcp_options_sets[0].options["domain-name-servers"][0].should.be.equal("10.0.20.2")
    dhcp_options_sets[0].tags["Name"].should.equal("TestDhcpOptions2")
    dhcp_options_sets[0].tags["test-tag"].should.equal("test-value")

    filters = {"tag:test-tag": "test-value"}
    dhcp_options_sets = conn.get_all_dhcp_options(filters=filters)

    dhcp_options_sets.should.have.length_of(2)


@mock_ec2_deprecated
def test_dhcp_options_get_by_id():
    conn = boto.connect_vpc("the_key", "the_secret")

    dhcp1 = conn.create_dhcp_options("test1.com", ["10.0.10.2"])
    dhcp1.add_tag("Name", "TestDhcpOptions1")
    dhcp1.add_tag("test-tag", "test-value")
    dhcp1_id = dhcp1.id

    dhcp2 = conn.create_dhcp_options("test2.com", ["10.0.20.2"])
    dhcp2.add_tag("Name", "TestDhcpOptions2")
    dhcp2.add_tag("test-tag", "test-value")
    dhcp2_id = dhcp2.id

    dhcp_options_sets = conn.get_all_dhcp_options()
    dhcp_options_sets.should.have.length_of(2)

    dhcp_options_sets = conn.get_all_dhcp_options(filters={"dhcp-options-id": dhcp1_id})

    dhcp_options_sets.should.have.length_of(1)
    dhcp_options_sets[0].options["domain-name"][0].should.be.equal("test1.com")
    dhcp_options_sets[0].options["domain-name-servers"][0].should.be.equal("10.0.10.2")

    dhcp_options_sets = conn.get_all_dhcp_options(filters={"dhcp-options-id": dhcp2_id})

    dhcp_options_sets.should.have.length_of(1)
    dhcp_options_sets[0].options["domain-name"][0].should.be.equal("test2.com")
    dhcp_options_sets[0].options["domain-name-servers"][0].should.be.equal("10.0.20.2")


@mock_ec2
def test_dhcp_options_get_by_value_filter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.10.2"]},
        ]
    )

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.20.2"]},
        ]
    )

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.30.2"]},
        ]
    )

    filters = [{"Name": "value", "Values": ["10.0.10.2"]}]
    dhcp_options_sets = list(ec2.dhcp_options_sets.filter(Filters=filters))
    dhcp_options_sets.should.have.length_of(1)


@mock_ec2
def test_dhcp_options_get_by_key_filter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.10.2"]},
        ]
    )

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.20.2"]},
        ]
    )

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.30.2"]},
        ]
    )

    filters = [{"Name": "key", "Values": ["domain-name"]}]
    dhcp_options_sets = list(ec2.dhcp_options_sets.filter(Filters=filters))
    dhcp_options_sets.should.have.length_of(3)


@mock_ec2_deprecated
def test_dhcp_options_get_by_invalid_filter():
    conn = boto.connect_vpc("the_key", "the_secret")

    conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    filters = {"invalid-filter": "invalid-value"}

    conn.get_all_dhcp_options.when.called_with(filters=filters).should.throw(
        NotImplementedError
    )
