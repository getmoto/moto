import boto
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError
from moto import mock_ec2, mock_ec2_deprecated


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_vpn_connections():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_connection = conn.create_vpn_connection(
        "ipsec.1", "vgw-0123abcd", "cgw-0123abcd"
    )
    vpn_connection.should_not.be.none
    vpn_connection.id.should.match(r"vpn-\w+")
    vpn_connection.type.should.equal("ipsec.1")


@mock_ec2
def test_create_vpn_connections_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    vpn_connection = client.create_vpn_connection(
        Type="ipsec.1", VpnGatewayId="vgw-0123abcd", CustomerGatewayId="cgw-0123abcd"
    )["VpnConnection"]
    vpn_connection["VpnConnectionId"].should.match(r"vpn-\w+")
    vpn_connection["Type"].should.equal("ipsec.1")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_delete_vpn_connections():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_connection = conn.create_vpn_connection(
        "ipsec.1", "vgw-0123abcd", "cgw-0123abcd"
    )
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(1)
    conn.delete_vpn_connection(vpn_connection.id)
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections[0].state.should.equal("deleted")


@mock_ec2
def test_delete_vpn_connections_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    vpn_connection = client.create_vpn_connection(
        Type="ipsec.1", VpnGatewayId="vgw-0123abcd", CustomerGatewayId="cgw-0123abcd"
    )["VpnConnection"]

    conns = retrieve_all_vpncs(client)
    [c["VpnConnectionId"] for c in conns].should.contain(
        vpn_connection["VpnConnectionId"]
    )

    client.delete_vpn_connection(VpnConnectionId=vpn_connection["VpnConnectionId"])

    conns = retrieve_all_vpncs(client)
    [c["VpnConnectionId"] for c in conns].should.contain(
        vpn_connection["VpnConnectionId"]
    )
    my_cnx = [
        c for c in conns if c["VpnConnectionId"] == vpn_connection["VpnConnectionId"]
    ][0]
    my_cnx.should.have.key("State").equal("deleted")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_delete_vpn_connections_bad_id():
    conn = boto.connect_vpc("the_key", "the_secret")
    with pytest.raises(EC2ResponseError):
        conn.delete_vpn_connection("vpn-0123abcd")


@mock_ec2
def test_delete_vpn_connections_bad_id_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.delete_vpn_connection(VpnConnectionId="vpn-0123abcd")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidVpnConnectionID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_describe_vpn_connections():
    conn = boto.connect_vpc("the_key", "the_secret")
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(0)
    conn.create_vpn_connection("ipsec.1", "vgw-0123abcd", "cgw-0123abcd")
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(1)
    vpn = conn.create_vpn_connection("ipsec.1", "vgw-1234abcd", "cgw-1234abcd")
    list_of_vpn_connections = conn.get_all_vpn_connections()
    list_of_vpn_connections.should.have.length_of(2)
    list_of_vpn_connections = conn.get_all_vpn_connections(vpn.id)
    list_of_vpn_connections.should.have.length_of(1)


@mock_ec2
def test_create_vpn_connection_with_vpn_gateway():
    client = boto3.client("ec2", region_name="us-east-1")

    vpn_gateway = client.create_vpn_gateway(Type="ipsec.1").get("VpnGateway", {})
    customer_gateway = client.create_customer_gateway(
        Type="ipsec.1", PublicIp="205.251.242.54", BgpAsn=65534,
    ).get("CustomerGateway", {})
    vpn_connection = client.create_vpn_connection(
        Type="ipsec.1",
        VpnGatewayId=vpn_gateway["VpnGatewayId"],
        CustomerGatewayId=customer_gateway["CustomerGatewayId"],
    ).get("VpnConnection", {})

    vpn_connection["Type"].should.equal("ipsec.1")
    vpn_connection["VpnGatewayId"].should.equal(vpn_gateway["VpnGatewayId"])
    vpn_connection["CustomerGatewayId"].should.equal(
        customer_gateway["CustomerGatewayId"]
    )


@mock_ec2
def test_describe_vpn_connections_boto3():
    client = boto3.client("ec2", region_name="us-east-1")

    vpn_gateway = client.create_vpn_gateway(Type="ipsec.1").get("VpnGateway", {})
    customer_gateway = client.create_customer_gateway(
        Type="ipsec.1", PublicIp="205.251.242.54", BgpAsn=65534,
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
    [c["VpnConnectionId"] for c in conns].should.contain(
        vpn_connection1["VpnConnectionId"]
    )
    [c["VpnConnectionId"] for c in conns].should.contain(
        vpn_connection2["VpnConnectionId"]
    )

    conns = client.describe_vpn_connections(
        VpnConnectionIds=[vpn_connection2["VpnConnectionId"]]
    )["VpnConnections"]

    conns[0]["VpnConnectionId"].should.equal(vpn_connection2["VpnConnectionId"])
    conns[0]["VpnGatewayId"].should.equal(vpn_gateway["VpnGatewayId"])
    conns[0]["Type"].should.equal("ipsec.1")
    conns[0]["CustomerGatewayId"].should.equal(customer_gateway["CustomerGatewayId"])
    conns[0]["State"].should.equal("available")


@mock_ec2
def test_describe_vpn_connections_unknown():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_vpn_connections(VpnConnectionIds=["?"])
    err = ex.value.response["Error"]
    err["Message"].should.equal("The vpnConnection ID '?' does not exist")
    err["Code"].should.equal("InvalidVpnConnectionID.NotFound")


def retrieve_all_vpncs(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_vpn_connections(Filters=filters)
    all_vpncs = resp["VpnConnections"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_vpn_connections(NextToken=token, Filters=filters)
        all_vpncs.extend(resp["VpnConnections"])
        token = resp.get("NextToken")
    return all_vpncs
