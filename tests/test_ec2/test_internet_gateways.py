from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import re

import boto
from boto.exception import EC2ResponseError

import sure  # noqa

from moto import mock_ec2_deprecated


VPC_CIDR = "10.0.0.0/16"
BAD_VPC = "vpc-deadbeef"
BAD_IGW = "igw-deadbeef"


@mock_ec2_deprecated
def test_igw_create():
    """ internet gateway create """
    conn = boto.connect_vpc('the_key', 'the_secret')

    conn.get_all_internet_gateways().should.have.length_of(0)

    with assert_raises(EC2ResponseError) as ex:
        igw = conn.create_internet_gateway(dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the CreateInternetGateway operation: Request would have succeeded, but DryRun flag is set')

    igw = conn.create_internet_gateway()
    conn.get_all_internet_gateways().should.have.length_of(1)
    igw.id.should.match(r'igw-[0-9a-f]+')

    igw = conn.get_all_internet_gateways()[0]
    igw.attachments.should.have.length_of(0)


@mock_ec2_deprecated
def test_igw_attach():
    """ internet gateway attach """
    conn = boto.connect_vpc('the_key', 'the_secret')
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)

    with assert_raises(EC2ResponseError) as ex:
        conn.attach_internet_gateway(igw.id, vpc.id, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the AttachInternetGateway operation: Request would have succeeded, but DryRun flag is set')

    conn.attach_internet_gateway(igw.id, vpc.id)

    igw = conn.get_all_internet_gateways()[0]
    igw.attachments[0].vpc_id.should.be.equal(vpc.id)


@mock_ec2_deprecated
def test_igw_attach_bad_vpc():
    """ internet gateway fail to attach w/ bad vpc """
    conn = boto.connect_vpc('the_key', 'the_secret')
    igw = conn.create_internet_gateway()

    with assert_raises(EC2ResponseError) as cm:
        conn.attach_internet_gateway(igw.id, BAD_VPC)
    cm.exception.code.should.equal('InvalidVpcID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_igw_attach_twice():
    """ internet gateway fail to attach twice """
    conn = boto.connect_vpc('the_key', 'the_secret')
    igw = conn.create_internet_gateway()
    vpc1 = conn.create_vpc(VPC_CIDR)
    vpc2 = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc1.id)

    with assert_raises(EC2ResponseError) as cm:
        conn.attach_internet_gateway(igw.id, vpc2.id)
    cm.exception.code.should.equal('Resource.AlreadyAssociated')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_igw_detach():
    """ internet gateway detach"""
    conn = boto.connect_vpc('the_key', 'the_secret')
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc.id)

    with assert_raises(EC2ResponseError) as ex:
        conn.detach_internet_gateway(igw.id, vpc.id, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the DetachInternetGateway operation: Request would have succeeded, but DryRun flag is set')

    conn.detach_internet_gateway(igw.id, vpc.id)
    igw = conn.get_all_internet_gateways()[0]
    igw.attachments.should.have.length_of(0)


@mock_ec2_deprecated
def test_igw_detach_wrong_vpc():
    """ internet gateway fail to detach w/ wrong vpc """
    conn = boto.connect_vpc('the_key', 'the_secret')
    igw = conn.create_internet_gateway()
    vpc1 = conn.create_vpc(VPC_CIDR)
    vpc2 = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc1.id)

    with assert_raises(EC2ResponseError) as cm:
        conn.detach_internet_gateway(igw.id, vpc2.id)
    cm.exception.code.should.equal('Gateway.NotAttached')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_igw_detach_invalid_vpc():
    """ internet gateway fail to detach w/ invalid vpc """
    conn = boto.connect_vpc('the_key', 'the_secret')
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc.id)

    with assert_raises(EC2ResponseError) as cm:
        conn.detach_internet_gateway(igw.id, BAD_VPC)
    cm.exception.code.should.equal('Gateway.NotAttached')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_igw_detach_unattached():
    """ internet gateway fail to detach unattached """
    conn = boto.connect_vpc('the_key', 'the_secret')
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)

    with assert_raises(EC2ResponseError) as cm:
        conn.detach_internet_gateway(igw.id, vpc.id)
    cm.exception.code.should.equal('Gateway.NotAttached')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_igw_delete():
    """ internet gateway delete"""
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc(VPC_CIDR)
    conn.get_all_internet_gateways().should.have.length_of(0)
    igw = conn.create_internet_gateway()
    conn.get_all_internet_gateways().should.have.length_of(1)

    with assert_raises(EC2ResponseError) as ex:
        conn.delete_internet_gateway(igw.id, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the DeleteInternetGateway operation: Request would have succeeded, but DryRun flag is set')

    conn.delete_internet_gateway(igw.id)
    conn.get_all_internet_gateways().should.have.length_of(0)


@mock_ec2_deprecated
def test_igw_delete_attached():
    """ internet gateway fail to delete attached """
    conn = boto.connect_vpc('the_key', 'the_secret')
    igw = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw.id, vpc.id)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_internet_gateway(igw.id)
    cm.exception.code.should.equal('DependencyViolation')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_igw_desribe():
    """ internet gateway fetch by id """
    conn = boto.connect_vpc('the_key', 'the_secret')
    igw = conn.create_internet_gateway()
    igw_by_search = conn.get_all_internet_gateways([igw.id])[0]
    igw.id.should.equal(igw_by_search.id)


@mock_ec2_deprecated
def test_igw_describe_bad_id():
    """ internet gateway fail to fetch by bad id """
    conn = boto.connect_vpc('the_key', 'the_secret')
    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_internet_gateways([BAD_IGW])
    cm.exception.code.should.equal('InvalidInternetGatewayID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_igw_filter_by_vpc_id():
    """ internet gateway filter by vpc id """
    conn = boto.connect_vpc('the_key', 'the_secret')

    igw1 = conn.create_internet_gateway()
    igw2 = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw1.id, vpc.id)

    result = conn.get_all_internet_gateways(
        filters={"attachment.vpc-id": vpc.id})
    result.should.have.length_of(1)
    result[0].id.should.equal(igw1.id)


@mock_ec2_deprecated
def test_igw_filter_by_tags():
    """ internet gateway filter by vpc id """
    conn = boto.connect_vpc('the_key', 'the_secret')

    igw1 = conn.create_internet_gateway()
    igw2 = conn.create_internet_gateway()
    igw1.add_tag("tests", "yes")

    result = conn.get_all_internet_gateways(filters={"tag:tests": "yes"})
    result.should.have.length_of(1)
    result[0].id.should.equal(igw1.id)


@mock_ec2_deprecated
def test_igw_filter_by_internet_gateway_id():
    """ internet gateway filter by internet gateway id """
    conn = boto.connect_vpc('the_key', 'the_secret')

    igw1 = conn.create_internet_gateway()
    igw2 = conn.create_internet_gateway()

    result = conn.get_all_internet_gateways(
        filters={"internet-gateway-id": igw1.id})
    result.should.have.length_of(1)
    result[0].id.should.equal(igw1.id)


@mock_ec2_deprecated
def test_igw_filter_by_attachment_state():
    """ internet gateway filter by attachment state """
    conn = boto.connect_vpc('the_key', 'the_secret')

    igw1 = conn.create_internet_gateway()
    igw2 = conn.create_internet_gateway()
    vpc = conn.create_vpc(VPC_CIDR)
    conn.attach_internet_gateway(igw1.id, vpc.id)

    result = conn.get_all_internet_gateways(
        filters={"attachment.state": "available"})
    result.should.have.length_of(1)
    result[0].id.should.equal(igw1.id)
