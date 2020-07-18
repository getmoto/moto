from __future__ import unicode_literals
import boto
import sure  # noqa

from moto import mock_ec2_deprecated


@mock_ec2_deprecated
def test_virtual_private_gateways():
    conn = boto.connect_vpc("the_key", "the_secret")

    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")
    vpn_gateway.should_not.be.none
    vpn_gateway.id.should.match(r"vgw-\w+")
    vpn_gateway.type.should.equal("ipsec.1")
    vpn_gateway.state.should.equal("available")
    vpn_gateway.availability_zone.should.equal("us-east-1a")


@mock_ec2_deprecated
def test_describe_vpn_gateway():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")

    vgws = conn.get_all_vpn_gateways()
    vgws.should.have.length_of(1)

    gateway = vgws[0]
    gateway.id.should.match(r"vgw-\w+")
    gateway.id.should.equal(vpn_gateway.id)
    vpn_gateway.type.should.equal("ipsec.1")
    vpn_gateway.state.should.equal("available")
    vpn_gateway.availability_zone.should.equal("us-east-1a")


@mock_ec2_deprecated
def test_vpn_gateway_vpc_attachment():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")

    conn.attach_vpn_gateway(vpn_gateway_id=vpn_gateway.id, vpc_id=vpc.id)

    gateway = conn.get_all_vpn_gateways()[0]
    attachments = gateway.attachments
    attachments.should.have.length_of(1)
    attachments[0].vpc_id.should.equal(vpc.id)
    attachments[0].state.should.equal("attached")


@mock_ec2_deprecated
def test_delete_vpn_gateway():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")

    conn.delete_vpn_gateway(vpn_gateway.id)
    vgws = conn.get_all_vpn_gateways()
    vgws.should.have.length_of(0)


@mock_ec2_deprecated
def test_vpn_gateway_tagging():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")
    vpn_gateway.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the subnet
    vpn_gateway = conn.get_all_vpn_gateways()[0]
    vpn_gateway.tags.should.have.length_of(1)
    vpn_gateway.tags["a key"].should.equal("some value")


@mock_ec2_deprecated
def test_detach_vpn_gateway():

    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")

    conn.attach_vpn_gateway(vpn_gateway_id=vpn_gateway.id, vpc_id=vpc.id)

    gateway = conn.get_all_vpn_gateways()[0]
    attachments = gateway.attachments
    attachments.should.have.length_of(1)
    attachments[0].vpc_id.should.equal(vpc.id)
    attachments[0].state.should.equal("attached")

    conn.detach_vpn_gateway(vpn_gateway_id=vpn_gateway.id, vpc_id=vpc.id)

    gateway = conn.get_all_vpn_gateways()[0]
    attachments = gateway.attachments
    attachments.should.have.length_of(0)
