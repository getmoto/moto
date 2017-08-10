from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2_deprecated
from tests.helpers import requires_boto_gte


@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_vpc_peering_connections():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    peer_vpc = conn.create_vpc("11.0.0.0/16")

    vpc_pcx = conn.create_vpc_peering_connection(vpc.id, peer_vpc.id)
    vpc_pcx._status.code.should.equal('initiating-request')

    return vpc_pcx


@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_vpc_peering_connections_get_all():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc_pcx = test_vpc_peering_connections()
    vpc_pcx._status.code.should.equal('initiating-request')

    all_vpc_pcxs = conn.get_all_vpc_peering_connections()
    all_vpc_pcxs.should.have.length_of(1)
    all_vpc_pcxs[0]._status.code.should.equal('pending-acceptance')


@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_vpc_peering_connections_accept():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc_pcx = test_vpc_peering_connections()

    vpc_pcx = conn.accept_vpc_peering_connection(vpc_pcx.id)
    vpc_pcx._status.code.should.equal('active')

    with assert_raises(EC2ResponseError) as cm:
        conn.reject_vpc_peering_connection(vpc_pcx.id)
    cm.exception.code.should.equal('InvalidStateTransition')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    all_vpc_pcxs = conn.get_all_vpc_peering_connections()
    all_vpc_pcxs.should.have.length_of(1)
    all_vpc_pcxs[0]._status.code.should.equal('active')


@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_vpc_peering_connections_reject():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc_pcx = test_vpc_peering_connections()

    verdict = conn.reject_vpc_peering_connection(vpc_pcx.id)
    verdict.should.equal(True)

    with assert_raises(EC2ResponseError) as cm:
        conn.accept_vpc_peering_connection(vpc_pcx.id)
    cm.exception.code.should.equal('InvalidStateTransition')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    all_vpc_pcxs = conn.get_all_vpc_peering_connections()
    all_vpc_pcxs.should.have.length_of(1)
    all_vpc_pcxs[0]._status.code.should.equal('rejected')


@requires_boto_gte("2.32.1")
@mock_ec2_deprecated
def test_vpc_peering_connections_delete():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc_pcx = test_vpc_peering_connections()

    verdict = vpc_pcx.delete()
    verdict.should.equal(True)

    all_vpc_pcxs = conn.get_all_vpc_peering_connections()
    all_vpc_pcxs.should.have.length_of(0)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_vpc_peering_connection("pcx-1234abcd")
    cm.exception.code.should.equal('InvalidVpcPeeringConnectionId.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none
