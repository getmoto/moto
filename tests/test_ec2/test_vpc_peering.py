import boto3
import pytest

from botocore.exceptions import ClientError

from moto import mock_ec2


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

    assert "VpcPeeringConnectionId" in vpc_pcx
    assert vpc_pcx["Status"]["Code"] == "initiating-request"


@mock_ec2
def test_vpc_peering_connections_get_all_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc_pcx = create_vpx_pcx(ec2, client)
    vpc_pcx_id = vpc_pcx["VpcPeeringConnectionId"]

    all_vpc_pcxs = retrieve_all(client)
    assert vpc_pcx_id in [vpc_pcx["VpcPeeringConnectionId"] for vpc_pcx in all_vpc_pcxs]
    my_vpc_pcx = [
        vpc_pcx
        for vpc_pcx in all_vpc_pcxs
        if vpc_pcx["VpcPeeringConnectionId"] == vpc_pcx_id
    ][0]
    assert my_vpc_pcx["Status"]["Code"] == "pending-acceptance"


@mock_ec2
def test_vpc_peering_connections_accept_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc_pcx = create_vpx_pcx(ec2, client)
    vpc_pcx_id = vpc_pcx["VpcPeeringConnectionId"]

    vpc_pcx = client.accept_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)
    vpc_pcx = vpc_pcx["VpcPeeringConnection"]
    assert vpc_pcx["Status"]["Code"] == "active"

    with pytest.raises(ClientError) as ex:
        client.reject_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidStateTransition"

    my_vpc_pcxs = client.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_id]
    )["VpcPeeringConnections"]
    assert len(my_vpc_pcxs) == 1
    assert my_vpc_pcxs[0]["Status"]["Code"] == "active"


@mock_ec2
def test_vpc_peering_connections_reject_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc_pcx = create_vpx_pcx(ec2, client)
    vpc_pcx_id = vpc_pcx["VpcPeeringConnectionId"]

    client.reject_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)

    with pytest.raises(ClientError) as ex:
        client.accept_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidStateTransition"

    my_pcxs = client.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_id]
    )["VpcPeeringConnections"]
    assert len(my_pcxs) == 1
    assert my_pcxs[0]["Status"]["Code"] == "rejected"


@mock_ec2
def test_vpc_peering_connections_delete_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc_pcx = create_vpx_pcx(ec2, client)
    vpc_pcx_id = vpc_pcx["VpcPeeringConnectionId"]

    client.delete_vpc_peering_connection(VpcPeeringConnectionId=vpc_pcx_id)

    all_vpc_pcxs = retrieve_all(client)
    assert vpc_pcx_id in [vpcx["VpcPeeringConnectionId"] for vpcx in all_vpc_pcxs]

    my_vpcx = [
        vpcx for vpcx in all_vpc_pcxs if vpcx["VpcPeeringConnectionId"] == vpc_pcx_id
    ][0]
    assert my_vpcx["Status"]["Code"] == "deleted"

    with pytest.raises(ClientError) as ex:
        client.delete_vpc_peering_connection(VpcPeeringConnectionId="pcx-1234abcd")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert (
        ex.value.response["Error"]["Code"] == "InvalidVpcPeeringConnectionId.NotFound"
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
    assert vpc_pcx_usw1.status["Code"] == "initiating-request"
    assert vpc_pcx_usw1.requester_vpc.id == vpc_usw1.id
    assert vpc_pcx_usw1.accepter_vpc.id == vpc_apn1.id
    # test cross region vpc peering connection exist
    vpc_pcx_apn1 = ec2_apn1.VpcPeeringConnection(vpc_pcx_usw1.id)
    assert vpc_pcx_apn1.id == vpc_pcx_usw1.id
    assert vpc_pcx_apn1.requester_vpc.id == vpc_usw1.id
    assert vpc_pcx_apn1.accepter_vpc.id == vpc_apn1.id
    # Quick check to verify the options have a default value
    accepter_options = vpc_pcx_apn1.accepter_vpc_info["PeeringOptions"]
    assert accepter_options["AllowDnsResolutionFromRemoteVpc"] is False
    assert accepter_options["AllowEgressFromLocalClassicLinkToRemoteVpc"] is False
    assert accepter_options["AllowEgressFromLocalVpcToRemoteClassicLink"] is False
    requester_options = vpc_pcx_apn1.requester_vpc_info["PeeringOptions"]
    assert requester_options["AllowDnsResolutionFromRemoteVpc"] is False
    assert requester_options["AllowEgressFromLocalClassicLinkToRemoteVpc"] is False
    assert requester_options["AllowEgressFromLocalVpcToRemoteClassicLink"] is False


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
        AccepterPeeringConnectionOptions={"AllowDnsResolutionFromRemoteVpc": True},
    )
    # Accepter options are different
    vpc_pcx_usw1.reload()
    accepter_options = vpc_pcx_usw1.accepter_vpc_info["PeeringOptions"]
    assert accepter_options["AllowDnsResolutionFromRemoteVpc"] is True
    assert accepter_options["AllowEgressFromLocalClassicLinkToRemoteVpc"] is False
    assert accepter_options["AllowEgressFromLocalVpcToRemoteClassicLink"] is False
    # Requester options are untouched
    requester_options = vpc_pcx_usw1.requester_vpc_info["PeeringOptions"]
    assert requester_options["AllowDnsResolutionFromRemoteVpc"] is False
    assert requester_options["AllowEgressFromLocalClassicLinkToRemoteVpc"] is False
    assert requester_options["AllowEgressFromLocalVpcToRemoteClassicLink"] is False


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
    assert requester_options["AllowDnsResolutionFromRemoteVpc"] is False
    assert requester_options["AllowEgressFromLocalClassicLinkToRemoteVpc"] is False
    assert requester_options["AllowEgressFromLocalVpcToRemoteClassicLink"] is True
    # Accepter options are untouched
    accepter_options = vpc_pcx_usw1.accepter_vpc_info["PeeringOptions"]
    assert accepter_options["AllowDnsResolutionFromRemoteVpc"] is False
    assert accepter_options["AllowEgressFromLocalClassicLinkToRemoteVpc"] is False
    assert accepter_options["AllowEgressFromLocalVpcToRemoteClassicLink"] is False


@mock_ec2
def test_modify_vpc_peering_connections_unknown_vpc():
    # create vpc in us-west-1 and ap-northeast-1
    ec2_usw1 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc_usw1 = ec2_usw1.create_vpc(CidrBlock="10.90.0.0/16")
    ec2_apn1 = boto3.resource("ec2", region_name="ap-northeast-1")
    vpc_apn1 = ec2_apn1.create_vpc(CidrBlock="10.20.0.0/16")
    # create peering
    ec2_usw1.create_vpc_peering_connection(
        VpcId=vpc_usw1.id, PeerVpcId=vpc_apn1.id, PeerRegion="ap-northeast-1"
    )
    #
    with pytest.raises(ClientError) as ex:
        client.modify_vpc_peering_connection_options(
            VpcPeeringConnectionId="vpx-unknown", RequesterPeeringConnectionOptions={}
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidVpcPeeringConnectionId.NotFound"
    assert err["Message"] == "VpcPeeringConnectionID vpx-unknown does not exist."


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
    assert cm.value.response["Error"]["Code"] == "InvalidVpcID.NotFound"


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
    assert vpc_pcx_usw1.id in our_vpcx
    assert vpc_pcx_usw2.id in our_vpcx
    assert vpc_apn1.id not in our_vpcx

    both_pcx = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id, vpc_pcx_usw2.id]
    )["VpcPeeringConnections"]
    assert len(both_pcx) == 2

    one_pcx = ec2_usw1.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[vpc_pcx_usw1.id]
    )["VpcPeeringConnections"]
    assert len(one_pcx) == 1


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
    assert acp_pcx_apn1["VpcPeeringConnection"]["Status"]["Code"] == "active"
    assert (
        acp_pcx_apn1["VpcPeeringConnection"]["AccepterVpcInfo"]["Region"]
        == "ap-northeast-1"
    )
    assert (
        acp_pcx_apn1["VpcPeeringConnection"]["RequesterVpcInfo"]["Region"]
        == "us-west-1"
    )
    assert des_pcx_apn1["VpcPeeringConnections"][0]["Status"]["Code"] == "active"
    assert (
        des_pcx_apn1["VpcPeeringConnections"][0]["AccepterVpcInfo"]["Region"]
        == "ap-northeast-1"
    )
    assert (
        des_pcx_apn1["VpcPeeringConnections"][0]["RequesterVpcInfo"]["Region"]
        == "us-west-1"
    )
    assert des_pcx_usw1["VpcPeeringConnections"][0]["Status"]["Code"] == "active"
    assert (
        des_pcx_usw1["VpcPeeringConnections"][0]["AccepterVpcInfo"]["Region"]
        == "ap-northeast-1"
    )
    assert (
        des_pcx_usw1["VpcPeeringConnections"][0]["RequesterVpcInfo"]["Region"]
        == "us-west-1"
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
    assert rej_pcx_apn1["Return"] is True
    assert des_pcx_apn1["VpcPeeringConnections"][0]["Status"]["Code"] == "rejected"
    assert des_pcx_usw1["VpcPeeringConnections"][0]["Status"]["Code"] == "rejected"


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
    assert del_pcx_apn1["Return"] is True
    assert des_pcx_apn1["VpcPeeringConnections"][0]["Status"]["Code"] == "deleted"
    assert des_pcx_usw1["VpcPeeringConnections"][0]["Status"]["Code"] == "deleted"


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
    assert cm.value.response["Error"]["Code"] == "OperationNotPermitted"
    exp_msg = f"Incorrect region (us-west-1) specified for this request.VPC peering connection {vpc_pcx_usw1.id} must be accepted in region ap-northeast-1"
    assert cm.value.response["Error"]["Message"] == exp_msg


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
    assert cm.value.response["Error"]["Code"] == "OperationNotPermitted"
    exp_msg = f"Incorrect region (us-west-1) specified for this request.VPC peering connection {vpc_pcx_usw1.id} must be accepted or rejected in region ap-northeast-1"
    assert cm.value.response["Error"]["Message"] == exp_msg


def retrieve_all(client):
    resp = client.describe_vpc_peering_connections()
    all_vpx = resp["VpcPeeringConnections"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_vpc_peering_connections(NextToken=token)
        all_vpx.extend(resp["VpcPeeringConnections"])
        token = resp.get("NextToken")
    return all_vpx
