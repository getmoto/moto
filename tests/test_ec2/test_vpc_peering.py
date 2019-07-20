from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises
from moto.ec2.exceptions import EC2ClientError
from botocore.exceptions import ClientError

import boto3
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated
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
    all_vpc_pcxs.should.have.length_of(1)
    all_vpc_pcxs[0]._status.code.should.equal('deleted')

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_vpc_peering_connection("pcx-1234abcd")
    cm.exception.code.should.equal('InvalidVpcPeeringConnectionId.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_vpc_peering_connections_cross_region():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource('ec2', region_name='us-west-1')
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock='10.90.0.0/16')
    ec2_apn1 = boto3.resource('ec2', region_name='ap-northeast-1')
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock='10.20.0.0/16')
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id,
        PeerVpcId=vpc_apn1.id,
        PeerRegion='ap-northeast-1',
    )
    vpc_pcx_usw1.status['Code'].should.equal('initiating-request')
    vpc_pcx_usw1.requester_vpc.id.should.equal(vpc_usw1.id)
    vpc_pcx_usw1.accepter_vpc.id.should.equal(vpc_apn1.id)
    # test cross region vpc peering connection exist
    vpc_pcx_apn1 = ec2_apn1.VpcPeeringConnection(vpc_pcx_usw1.id)
    vpc_pcx_apn1.id.should.equal(vpc_pcx_usw1.id)
    vpc_pcx_apn1.requester_vpc.id.should.equal(vpc_usw1.id)
    vpc_pcx_apn1.accepter_vpc.id.should.equal(vpc_apn1.id)


@mock_ec2
def test_vpc_peering_connections_cross_region_fail():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource('ec2', region_name='us-west-1')
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock='10.90.0.0/16')
    ec2_apn1 = boto3.resource('ec2', region_name='ap-northeast-1')
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock='10.20.0.0/16')
    # create peering wrong region with no vpc
    with assert_raises(ClientError) as cm:
        ec2_usw1.create_vpc_peering_connection(
            VpcId=vpc_usw1.id,
            PeerVpcId=vpc_apn1.id,
            PeerRegion='ap-northeast-2')
    cm.exception.response['Error']['Code'].should.equal('InvalidVpcID.NotFound')


@mock_ec2
def test_vpc_peering_connections_cross_region_accept():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource('ec2', region_name='us-west-1')
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock='10.90.0.0/16')
    ec2_apn1 = boto3.resource('ec2', region_name='ap-northeast-1')
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock='10.20.0.0/16')
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id,
        PeerVpcId=vpc_apn1.id,
        PeerRegion='ap-northeast-1',
    )
    # accept peering from ap-northeast-1
    ec2_apn1 = boto3.client('ec2', region_name='ap-northeast-1')
    ec2_usw1 = boto3.client('ec2', region_name='us-west-1')
    acp_pcx_apn1 = ec2_apn1.accept_vpc_peering_connection(
        VpcPeeringConnectionId=vpc_pcx_usw1.id
    )
    des_pcx_apn1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    des_pcx_usw1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    acp_pcx_apn1['VpcPeeringConnection']['Status']['Code'].should.equal('active')
    des_pcx_apn1['VpcPeeringConnections'][0]['Status']['Code'].should.equal('active')
    des_pcx_usw1['VpcPeeringConnections'][0]['Status']['Code'].should.equal('active')


@mock_ec2
def test_vpc_peering_connections_cross_region_reject():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource('ec2', region_name='us-west-1')
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock='10.90.0.0/16')
    ec2_apn1 = boto3.resource('ec2', region_name='ap-northeast-1')
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock='10.20.0.0/16')
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id,
        PeerVpcId=vpc_apn1.id,
        PeerRegion='ap-northeast-1',
    )
    # reject peering from ap-northeast-1
    ec2_apn1 = boto3.client('ec2', region_name='ap-northeast-1')
    ec2_usw1 = boto3.client('ec2', region_name='us-west-1')
    rej_pcx_apn1 = ec2_apn1.reject_vpc_peering_connection(
        VpcPeeringConnectionId=vpc_pcx_usw1.id
    )
    des_pcx_apn1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    des_pcx_usw1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    rej_pcx_apn1['Return'].should.equal(True)
    des_pcx_apn1['VpcPeeringConnections'][0]['Status']['Code'].should.equal('rejected')
    des_pcx_usw1['VpcPeeringConnections'][0]['Status']['Code'].should.equal('rejected')


@mock_ec2
def test_vpc_peering_connections_cross_region_delete():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource('ec2', region_name='us-west-1')
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock='10.90.0.0/16')
    ec2_apn1 = boto3.resource('ec2', region_name='ap-northeast-1')
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock='10.20.0.0/16')
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id,
        PeerVpcId=vpc_apn1.id,
        PeerRegion='ap-northeast-1',
    )
    # reject peering from ap-northeast-1
    ec2_apn1 = boto3.client('ec2', region_name='ap-northeast-1')
    ec2_usw1 = boto3.client('ec2', region_name='us-west-1')
    del_pcx_apn1 = ec2_apn1.delete_vpc_peering_connection(
        VpcPeeringConnectionId=vpc_pcx_usw1.id
    )
    des_pcx_apn1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    des_pcx_usw1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    del_pcx_apn1['Return'].should.equal(True)
    des_pcx_apn1['VpcPeeringConnections'][0]['Status']['Code'].should.equal('deleted')
    des_pcx_usw1['VpcPeeringConnections'][0]['Status']['Code'].should.equal('deleted')


@mock_ec2
def test_vpc_peering_connections_cross_region_accept_wrong_region():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource('ec2', region_name='us-west-1')
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock='10.90.0.0/16')
    ec2_apn1 = boto3.resource('ec2', region_name='ap-northeast-1')
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock='10.20.0.0/16')
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id,
        PeerVpcId=vpc_apn1.id,
        PeerRegion='ap-northeast-1',
    )

    # accept wrong peering from us-west-1 which will raise error
    ec2_apn1 = boto3.client('ec2', region_name='ap-northeast-1')
    ec2_usw1 = boto3.client('ec2', region_name='us-west-1')
    with assert_raises(ClientError) as cm:
        ec2_usw1.accept_vpc_peering_connection(
            VpcPeeringConnectionId=vpc_pcx_usw1.id
        )
    cm.exception.response['Error']['Code'].should.equal('OperationNotPermitted')
    exp_msg = 'Incorrect region ({0}) specified for this request.VPC ' \
              'peering connection {1} must be ' \
              'accepted in region {2}'.format('us-west-1', vpc_pcx_usw1.id, 'ap-northeast-1')
    cm.exception.response['Error']['Message'].should.equal(exp_msg)


@mock_ec2
def test_vpc_peering_connections_cross_region_reject_wrong_region():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource('ec2', region_name='us-west-1')
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock='10.90.0.0/16')
    ec2_apn1 = boto3.resource('ec2', region_name='ap-northeast-1')
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock='10.20.0.0/16')
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id,
        PeerVpcId=vpc_apn1.id,
        PeerRegion='ap-northeast-1',
    )
    # reject wrong peering from us-west-1 which will raise error
    ec2_apn1 = boto3.client('ec2', region_name='ap-northeast-1')
    ec2_usw1 = boto3.client('ec2', region_name='us-west-1')
    with assert_raises(ClientError) as cm:
        ec2_usw1.reject_vpc_peering_connection(
            VpcPeeringConnectionId=vpc_pcx_usw1.id
        )
    cm.exception.response['Error']['Code'].should.equal('OperationNotPermitted')
    exp_msg = 'Incorrect region ({0}) specified for this request.VPC ' \
              'peering connection {1} must be accepted or ' \
              'rejected in region {2}'.format('us-west-1', vpc_pcx_usw1.id, 'ap-northeast-1')
    cm.exception.response['Error']['Message'].should.equal(exp_msg)
