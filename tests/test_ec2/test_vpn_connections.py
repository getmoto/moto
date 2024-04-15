import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_vpn_connections_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    vpn_connection = client.create_vpn_connection(
        Type="ipsec.1", VpnGatewayId="vgw-0123abcd", CustomerGatewayId="cgw-0123abcd"
    )["VpnConnection"]
    assert vpn_connection["VpnConnectionId"].startswith("vpn-")
    assert vpn_connection["Type"] == "ipsec.1"


@mock_aws
def test_delete_vpn_connections_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    vpn_connection = client.create_vpn_connection(
        Type="ipsec.1", VpnGatewayId="vgw-0123abcd", CustomerGatewayId="cgw-0123abcd"
    )["VpnConnection"]

    conns = retrieve_all_vpncs(client)
    assert vpn_connection["VpnConnectionId"] in [c["VpnConnectionId"] for c in conns]

    client.delete_vpn_connection(VpnConnectionId=vpn_connection["VpnConnectionId"])

    conns = retrieve_all_vpncs(client)
    assert vpn_connection["VpnConnectionId"] in [c["VpnConnectionId"] for c in conns]
    my_cnx = [
        c for c in conns if c["VpnConnectionId"] == vpn_connection["VpnConnectionId"]
    ][0]
    assert my_cnx["State"] == "deleted"


@mock_aws
def test_delete_vpn_connections_bad_id_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.delete_vpn_connection(VpnConnectionId="vpn-0123abcd")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidVpnConnectionID.NotFound"


@mock_aws
def test_create_vpn_connection_with_vpn_gateway():
    client = boto3.client("ec2", region_name="us-east-1")

    vpn_gateway = client.create_vpn_gateway(Type="ipsec.1").get("VpnGateway", {})
    customer_gateway = client.create_customer_gateway(
        Type="ipsec.1", PublicIp="205.251.242.54", BgpAsn=65534
    ).get("CustomerGateway", {})
    vpn_connection = client.create_vpn_connection(
        Type="ipsec.1",
        VpnGatewayId=vpn_gateway["VpnGatewayId"],
        CustomerGatewayId=customer_gateway["CustomerGatewayId"],
    ).get("VpnConnection", {})

    assert vpn_connection["Type"] == "ipsec.1"
    assert vpn_connection["VpnGatewayId"] == vpn_gateway["VpnGatewayId"]
    assert vpn_connection["CustomerGatewayId"] == customer_gateway["CustomerGatewayId"]


@mock_aws
def test_describe_vpn_connections_boto3():
    client = boto3.client("ec2", region_name="us-east-1")

    vpn_gateway = client.create_vpn_gateway(Type="ipsec.1").get("VpnGateway", {})
    customer_gateway = client.create_customer_gateway(
        Type="ipsec.1", PublicIp="205.251.242.54", BgpAsn=65534
    ).get("CustomerGateway", {})
    vpn_connection1 = client.create_vpn_connection(
        Type="ipsec.1",
        VpnGatewayId=vpn_gateway["VpnGatewayId"],
        CustomerGatewayId=customer_gateway["CustomerGatewayId"],
    )["VpnConnection"]
    vpn_connection2 = client.create_vpn_connection(
        Type="ipsec.1",
        VpnGatewayId=vpn_gateway["VpnGatewayId"],
        CustomerGatewayId=customer_gateway["CustomerGatewayId"],
    )["VpnConnection"]

    conns = retrieve_all_vpncs(client)
    assert vpn_connection1["VpnConnectionId"] in [c["VpnConnectionId"] for c in conns]
    assert vpn_connection2["VpnConnectionId"] in [c["VpnConnectionId"] for c in conns]

    conns = client.describe_vpn_connections(
        VpnConnectionIds=[vpn_connection2["VpnConnectionId"]]
    )["VpnConnections"]

    assert conns[0]["VpnConnectionId"] == vpn_connection2["VpnConnectionId"]
    assert conns[0]["VpnGatewayId"] == vpn_gateway["VpnGatewayId"]
    assert conns[0]["Type"] == "ipsec.1"
    assert conns[0]["CustomerGatewayId"] == customer_gateway["CustomerGatewayId"]
    assert conns[0]["State"] == "available"


@mock_aws
def test_describe_vpn_connections_unknown():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_vpn_connections(VpnConnectionIds=["?"])
    err = ex.value.response["Error"]
    assert err["Message"] == "The vpnConnection ID '?' does not exist"
    assert err["Code"] == "InvalidVpnConnectionID.NotFound"


def retrieve_all_vpncs(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_vpn_connections(Filters=filters)
    all_vpncs = resp["VpnConnections"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_vpn_connections(NextToken=token, Filters=filters)
        all_vpncs.extend(resp["VpnConnections"])
        token = resp.get("NextToken")
    return all_vpncs
