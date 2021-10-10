from __future__ import unicode_literals

import pytest
from moto.ec2.exceptions import EC2ClientError
from botocore.exceptions import ClientError

import boto3
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated
from tests.helpers import requires_boto_gte


# Has boto3 equivalent
@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_vpc_peering_connections():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    peer_vpc = conn.create_vpc("11.0.0.0/16")

    vpc_pcx = conn.create_vpc_peering_connection(vpc.id, peer_vpc.id)
    vpc_pcx._status.code.should.equal("initiating-request")

    return vpc_pcx


def create_vpx_pcx(ec2, client):
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    peer_vpc = ec2.create_vpc(CidrBlock="11.0.0.0/16")
    vpc_pcx = client.create_vpc_peering_connection(VpcId=vpc.id, PeerVpcId=peer_vpc.id)
    vpc_pcx = vpc_pcx["VpcPeeringConnection"]
    return vpc_pcx


@mock_ec2
def test_vpc_peering_connections_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")

    vpc_pcx = create_vpx_pcx(ec2, client)

    vpc_pcx.should.have.key("VpcPeeringConnectionId")
    vpc_pcx["Status"]["Code"].should.equal("initiating-request")


# Has boto3 equivalent
@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_vpc_peering_connections_get_all():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc_pcx = test_vpc_peering_connections()
    vpc_pcx._status.code.should.equal("initiating-request")

    all_vpc_pcxs = conn.get_all_vpc_peering_connections()
    all_vpc_pcxs.should.have.length_of(1)
    all_vpc_pcxs[0]._status.code.should.equal("pending-acceptance")


@mock_ec2
def test_vpc_peering_connections_get_all_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc_pcx = create_vpx_pcx(ec2, client)
    vpc_pcx_id = vpc_pcx["VpcPeeringConnectionId"]

    all_vpc_pcxs = retrieve_all(client)
    [vpc_pcx["VpcPeeringConnectionId"] for vpc_pcx in all_vpc_pcxs].should.contain(
        vpc_pcx_id
    )
    my_vpc_pcx = [
        vpc_pcx
        for vpc_pcx in all_vpc_pcxs
        if vpc_pcx["VpcPeeringConnectionId"] == vpc_pcx_id
    ][0]
    my_vpc_pcx["Status"]["Code"].should.equal("pending-acceptance")


# Has boto3 equivalent
@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_vpc_peering_connections_accept():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc_pcx = test_vpc_peering_connections()

    vpc_pcx = conn.accept_vpc_peering_connection(vpc_pcx.id)
    vpc_pcx._status.code.should.equal("active")

    with pytest.raises(EC2ResponseError) as cm:
        conn.reject_vpc_peering_connection(vpc_pcx.id)
    cm.value.code.should.equal("InvalidStateTransition")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    all_vpc_pcxs = conn.get_all_vpc_peering_connections()
    all_vpc_pcxs.should.have.length_of(1)
    all_vpc_pcxs[0]._status.code.should.equal("active")


@mock_ec2
def test_vpc_peering_connections_accept_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc_pcx = create_vpx_pcx(ec2, client)
    vpc_pcx_id = vpc_pcx["VpcPeeringConnectionId"]

    vpc_pcx = client.accept_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)
    vpc_pcx = vpc_pcx["VpcPeeringConnection"]
    vpc_pcx["Status"]["Code"].should.equal("active")

    with pytest.raises(ClientError) as ex:
        client.reject_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidStateTransition")

    my_vpc_pcxs = client.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_id]
    )["VpcPeeringConnections"]
    my_vpc_pcxs.should.have.length_of(1)
    my_vpc_pcxs[0]["Status"]["Code"].should.equal("active")


# Has boto3 equivalent
@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_vpc_peering_connections_reject():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc_pcx = test_vpc_peering_connections()

    verdict = conn.reject_vpc_peering_connection(vpc_pcx.id)
    verdict.should.equal(True)

    with pytest.raises(EC2ResponseError) as cm:
        conn.accept_vpc_peering_connection(vpc_pcx.id)
    cm.value.code.should.equal("InvalidStateTransition")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    all_vpc_pcxs = conn.get_all_vpc_peering_connections()
    all_vpc_pcxs.should.have.length_of(1)
    all_vpc_pcxs[0]._status.code.should.equal("rejected")


@mock_ec2
def test_vpc_peering_connections_reject_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc_pcx = create_vpx_pcx(ec2, client)
    vpc_pcx_id = vpc_pcx["VpcPeeringConnectionId"]

    client.reject_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)

    with pytest.raises(ClientError) as ex:
        client.accept_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidStateTransition")

    my_pcxs = client.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_id]
    )["VpcPeeringConnections"]
    my_pcxs.should.have.length_of(1)
    my_pcxs[0]["Status"]["Code"].should.equal("rejected")


# Has boto3 equivalent
@requires_boto_gte("2.32.1")
@mock_ec2_deprecated
def test_vpc_peering_connections_delete():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc_pcx = test_vpc_peering_connections()

    verdict = vpc_pcx.delete()
    verdict.should.equal(True)

    all_vpc_pcxs = conn.get_all_vpc_peering_connections()
    all_vpc_pcxs.should.have.length_of(1)
    all_vpc_pcxs[0]._status.code.should.equal("deleted")

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_vpc_peering_connection("pcx-1234abcd")
    cm.value.code.should.equal("InvalidVpcPeeringConnectionId.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_vpc_peering_connections_delete_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc_pcx = create_vpx_pcx(ec2, client)
    vpc_pcx_id = vpc_pcx["VpcPeeringConnectionId"]

    client.delete_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)

    all_vpc_pcxs = retrieve_all(client)
    [vpcx["VpcPeeringConnectionId"] for vpcx in all_vpc_pcxs].should.contain(vpc_pcx_id)

    my_vpcx = [
        vpcx for vpcx in all_vpc_pcxs if vpcx["VpcPeeringConnectionId"] == vpc_pcx_id
    ][0]
    my_vpcx["Status"]["Code"].should.equal("deleted")

    with pytest.raises(ClientError) as ex:
        client.delete_vpc_peering_connection(VpcPeeringConnectionId="pcx-1234abcd")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal(
        "InvalidVpcPeeringConnectionId.NotFound"
    )


@mock_ec2
def test_vpc_peering_connections_cross_region():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    vpc_pcx_usw1.status["Code"].should.equal("initiating-request")
    vpc_pcx_usw1.requester_vpc.id.should.equal(vpc_usw1.id)
    vpc_pcx_usw1.accepter_vpc.id.should.equal(vpc_apn1.id)
    # test cross region vpc peering connection exist
    vpc_pcx_apn1 = ec2_apn1.VpcPeeringConnection(vpc_pcx_usw1.id)
    vpc_pcx_apn1.id.should.equal(vpc_pcx_usw1.id)
    vpc_pcx_apn1.requester_vpc.id.should.equal(vpc_usw1.id)
    vpc_pcx_apn1.accepter_vpc.id.should.equal(vpc_apn1.id)
    # Quick check to verify the options have a default value
    accepter_options = vpc_pcx_apn1.accepter_vpc_info["PeeringOptions"]
    accepter_options["AllowDnsResolutionFromRemoteVpc"].should.equal(False)
    accepter_options["AllowEgressFromLocalClassicLinkToRemoteVpc"].should.equal(False)
    accepter_options["AllowEgressFromLocalVpcToRemoteClassicLink"].should.equal(False)
    requester_options = vpc_pcx_apn1.requester_vpc_info["PeeringOptions"]
    requester_options["AllowDnsResolutionFromRemoteVpc"].should.equal(False)
    requester_options["AllowEgressFromLocalClassicLinkToRemoteVpc"].should.equal(False)
    requester_options["AllowEgressFromLocalVpcToRemoteClassicLink"].should.equal(False)


@mock_ec2
def test_modify_vpc_peering_connections_accepter_only():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    #
    client.modify_vpc_peering_connection_options(
        VpcPeeringConnectionId=vpc_pcx_usw1.id,
        AccepterPeeringConnectionOptions={"AllowDnsResolutionFromRemoteVpc": True,},
    )
    # Accepter options are different
    vpc_pcx_usw1.reload()
    accepter_options = vpc_pcx_usw1.accepter_vpc_info["PeeringOptions"]
    accepter_options["AllowDnsResolutionFromRemoteVpc"].should.equal(True)
    accepter_options["AllowEgressFromLocalClassicLinkToRemoteVpc"].should.equal(False)
    accepter_options["AllowEgressFromLocalVpcToRemoteClassicLink"].should.equal(False)
    # Requester options are untouched
    requester_options = vpc_pcx_usw1.requester_vpc_info["PeeringOptions"]
    requester_options["AllowDnsResolutionFromRemoteVpc"].should.equal(False)
    requester_options["AllowEgressFromLocalClassicLinkToRemoteVpc"].should.equal(False)
    requester_options["AllowEgressFromLocalVpcToRemoteClassicLink"].should.equal(False)


@mock_ec2
def test_modify_vpc_peering_connections_requester_only():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    #
    client.modify_vpc_peering_connection_options(
        VpcPeeringConnectionId=vpc_pcx_usw1.id,
        RequesterPeeringConnectionOptions={
            "AllowEgressFromLocalVpcToRemoteClassicLink": True,
        },
    )
    # Requester options are different
    vpc_pcx_usw1.reload()
    requester_options = vpc_pcx_usw1.requester_vpc_info["PeeringOptions"]
    requester_options["AllowDnsResolutionFromRemoteVpc"].should.equal(False)
    requester_options["AllowEgressFromLocalClassicLinkToRemoteVpc"].should.equal(False)
    requester_options["AllowEgressFromLocalVpcToRemoteClassicLink"].should.equal(True)
    # Accepter options are untouched
    accepter_options = vpc_pcx_usw1.accepter_vpc_info["PeeringOptions"]
    accepter_options["AllowDnsResolutionFromRemoteVpc"].should.equal(False)
    accepter_options["AllowEgressFromLocalClassicLinkToRemoteVpc"].should.equal(False)
    accepter_options["AllowEgressFromLocalVpcToRemoteClassicLink"].should.equal(False)


@mock_ec2
def test_modify_vpc_peering_connections_unknown_vpc():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    #
    with pytest.raises(ClientError) as ex:
        client.modify_vpc_peering_connection_options(
            VpcPeeringConnectionId="vpx-unknown", RequesterPeeringConnectionOptions={}
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidVpcPeeringConnectionId.NotFound")
    err["Message"].should.equal("VpcPeeringConnectionID vpx-unknown does not exist.")


@mock_ec2
def test_vpc_peering_connections_cross_region_fail():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering wrong region with no vpc
    with pytest.raises(ClientError) as cm:
        ec2_usw1.create_vpc_peering_connection(
            VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-2"
        )
    cm.value.response["Error"]["Code"].should.equal("InvalidVpcID.NotFound")


@mock_ec2
def test_describe_vpc_peering_connections_only_returns_requested_id():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    vpc_pcx_usw2 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    # describe peering
    ec2_usw1 = boto3.client("ec2", region_name="us-west-1")
    our_vpcx = [vpcx["VpcPeeringConnectionId"] for vpcx in retrieve_all(ec2_usw1)]
    our_vpcx.should.contain(vpc_pcx_usw1.id)
    our_vpcx.should.contain(vpc_pcx_usw2.id)
    our_vpcx.shouldnt.contain(vpc_apn1.id)

    both_pcx = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id, vpc_pcx_usw2.id]
    )["VpcPeeringConnections"]
    both_pcx.should.have.length_of(2)

    one_pcx = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )["VpcPeeringConnections"]
    one_pcx.should.have.length_of(1)


@mock_ec2
def test_vpc_peering_connections_cross_region_accept():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    # accept peering from ap-northeast-1
    ec2_apn1 = boto3.client("ec2", region_name="ap-northeast-1")
    ec2_usw1 = boto3.client("ec2", region_name="us-west-1")
    acp_pcx_apn1 = ec2_apn1.accept_vpc_peering_connection(
        VpcPeeringConnectionId=vpc_pcx_usw1.id
    )
    des_pcx_apn1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    des_pcx_usw1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    acp_pcx_apn1["VpcPeeringConnection"]["Status"]["Code"].should.equal("active")
    acp_pcx_apn1["VpcPeeringConnection"]["AccepterVpcInfo"]["Region"].should.equal(
        "ap-northeast-1"
    )
    acp_pcx_apn1["VpcPeeringConnection"]["RequesterVpcInfo"]["Region"].should.equal(
        "us-west-1"
    )
    des_pcx_apn1["VpcPeeringConnections"][0]["Status"]["Code"].should.equal("active")
    des_pcx_apn1["VpcPeeringConnections"][0]["AccepterVpcInfo"]["Region"].should.equal(
        "ap-northeast-1"
    )
    des_pcx_apn1["VpcPeeringConnections"][0]["RequesterVpcInfo"]["Region"].should.equal(
        "us-west-1"
    )
    des_pcx_usw1["VpcPeeringConnections"][0]["Status"]["Code"].should.equal("active")
    des_pcx_usw1["VpcPeeringConnections"][0]["AccepterVpcInfo"]["Region"].should.equal(
        "ap-northeast-1"
    )
    des_pcx_usw1["VpcPeeringConnections"][0]["RequesterVpcInfo"]["Region"].should.equal(
        "us-west-1"
    )


@mock_ec2
def test_vpc_peering_connections_cross_region_reject():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    # reject peering from ap-northeast-1
    ec2_apn1 = boto3.client("ec2", region_name="ap-northeast-1")
    ec2_usw1 = boto3.client("ec2", region_name="us-west-1")
    rej_pcx_apn1 = ec2_apn1.reject_vpc_peering_connection(
        VpcPeeringConnectionId=vpc_pcx_usw1.id
    )
    des_pcx_apn1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    des_pcx_usw1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    rej_pcx_apn1["Return"].should.equal(True)
    des_pcx_apn1["VpcPeeringConnections"][0]["Status"]["Code"].should.equal("rejected")
    des_pcx_usw1["VpcPeeringConnections"][0]["Status"]["Code"].should.equal("rejected")


@mock_ec2
def test_vpc_peering_connections_cross_region_delete():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    # reject peering from ap-northeast-1
    ec2_apn1 = boto3.client("ec2", region_name="ap-northeast-1")
    ec2_usw1 = boto3.client("ec2", region_name="us-west-1")
    del_pcx_apn1 = ec2_apn1.delete_vpc_peering_connection(
        VpcPeeringConnectionId=vpc_pcx_usw1.id
    )
    des_pcx_apn1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    des_pcx_usw1 = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )
    del_pcx_apn1["Return"].should.equal(True)
    des_pcx_apn1["VpcPeeringConnections"][0]["Status"]["Code"].should.equal("deleted")
    des_pcx_usw1["VpcPeeringConnections"][0]["Status"]["Code"].should.equal("deleted")


@mock_ec2
def test_vpc_peering_connections_cross_region_accept_wrong_region():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )

    # accept wrong peering from us-west-1 which will raise error
    ec2_apn1 = boto3.client("ec2", region_name="ap-northeast-1")
    ec2_usw1 = boto3.client("ec2", region_name="us-west-1")
    with pytest.raises(ClientError) as cm:
        ec2_usw1.accept_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_usw1.id)
    cm.value.response["Error"]["Code"].should.equal("OperationNotPermitted")
    exp_msg = (
        "Incorrect region ({0}) specified for this request.VPC "
        "peering connection {1} must be "
        "accepted in region {2}".format("us-west-1", vpc_pcx_usw1.id, "ap-northeast-1")
    )
    cm.value.response["Error"]["Message"].should.equal(exp_msg)


@mock_ec2
def test_vpc_peering_connections_cross_region_reject_wrong_region():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    vpc_pcx_usw1 = ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    # reject wrong peering from us-west-1 which will raise error
    ec2_apn1 = boto3.client("ec2", region_name="ap-northeast-1")
    ec2_usw1 = boto3.client("ec2", region_name="us-west-1")
    with pytest.raises(ClientError) as cm:
        ec2_usw1.reject_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_usw1.id)
    cm.value.response["Error"]["Code"].should.equal("OperationNotPermitted")
    exp_msg = (
        "Incorrect region ({0}) specified for this request.VPC "
        "peering connection {1} must be accepted or "
        "rejected in region {2}".format("us-west-1", vpc_pcx_usw1.id, "ap-northeast-1")
    )
    cm.value.response["Error"]["Message"].should.equal(exp_msg)


def retrieve_all(client):
    resp = client.describe_vpc_peering_connections()
    all_vpx = resp["VpcPeeringConnections"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_vpc_peering_connections(NextToken=token)
        all_vpx.extend(resp["VpcPeeringConnections"])
        token = resp.get("NextToken")
    return all_vpx
