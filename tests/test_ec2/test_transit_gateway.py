import boto3
import pytest

from moto import mock_ec2, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from unittest import SkipTest


@mock_ec2
def test_describe_transit_gateways():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateways()
    assert response["TransitGateways"] == []


@mock_ec2
def test_create_transit_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.create_transit_gateway(
        Description="my first gateway", Options={"DnsSupport": "disable"}
    )
    gateway = response["TransitGateway"]
    assert gateway["TransitGatewayId"].startswith("tgw-")
    assert gateway["State"] == "available"
    assert gateway["OwnerId"] == ACCOUNT_ID
    assert gateway["Description"] == "my first gateway"
    assert gateway["Tags"] == []
    options = gateway["Options"]
    assert options["AmazonSideAsn"] == 64512
    assert options["TransitGatewayCidrBlocks"] == []
    assert options["AutoAcceptSharedAttachments"] == "disable"
    assert options["DefaultRouteTableAssociation"] == "enable"
    assert options["DefaultRouteTablePropagation"] == "enable"
    assert options["PropagationDefaultRouteTableId"].startswith("tgw-rtb-")
    assert options["VpnEcmpSupport"] == "enable"
    assert options["DnsSupport"] == "disable"
    #
    # Verify we can retrieve it
    all_gateways = retrieve_all_transit_gateways(ec2)
    assert gateway["TransitGatewayId"] in [
        gw["TransitGatewayId"] for gw in all_gateways
    ]
    gateways = ec2.describe_transit_gateways(
        TransitGatewayIds=[gateway["TransitGatewayId"]]
    )["TransitGateways"]

    assert len(gateways) == 1
    assert "CreationTime" in gateways[0]
    assert (
        gateways[0]["TransitGatewayArn"]
        == f"arn:aws:ec2:us-east-1:{ACCOUNT_ID}:transit-gateway/{gateway['TransitGatewayId']}"
    )
    assert (
        gateways[0]["Options"]["AssociationDefaultRouteTableId"]
        == gateways[0]["Options"]["PropagationDefaultRouteTableId"]
    )
    del gateways[0]["CreationTime"]
    del gateways[0]["TransitGatewayArn"]
    del gateways[0]["Options"]["AssociationDefaultRouteTableId"]
    assert gateway == gateways[0]


@mock_ec2
def test_create_transit_gateway_with_tags():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.create_transit_gateway(
        Description="my first gateway",
        TagSpecifications=[
            {
                "ResourceType": "transit-gateway",
                "Tags": [
                    {"Key": "tag1", "Value": "val1"},
                    {"Key": "tag2", "Value": "val2"},
                ],
            }
        ],
    )
    gateway = response["TransitGateway"]
    assert gateway["TransitGatewayId"].startswith("tgw-")
    tags = gateway.get("Tags", [])
    assert len(tags) == 2
    assert {"Key": "tag1", "Value": "val1"} in tags
    assert {"Key": "tag2", "Value": "val2"} in tags


@mock_ec2
def test_delete_transit_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    g = ec2.create_transit_gateway(Description="my first gateway")["TransitGateway"]
    g_id = g["TransitGatewayId"]

    all_gateways = retrieve_all_transit_gateways(ec2)
    assert g_id in [g["TransitGatewayId"] for g in all_gateways]

    ec2.delete_transit_gateway(TransitGatewayId=g_id)

    all_gateways = retrieve_all_transit_gateways(ec2)
    assert g_id not in [g["TransitGatewayId"] for g in all_gateways]


@mock_ec2
def test_describe_transit_gateway_by_id():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2.create_transit_gateway(Description="my first gatway")["TransitGateway"]
    g2 = ec2.create_transit_gateway(Description="my second gatway")["TransitGateway"]
    g2_id = g2["TransitGatewayId"]
    ec2.create_transit_gateway(Description="my third gatway")["TransitGateway"]

    my_gateway = ec2.describe_transit_gateways(TransitGatewayIds=[g2_id])[
        "TransitGateways"
    ][0]
    assert my_gateway["TransitGatewayId"] == g2_id
    assert my_gateway["Description"] == "my second gatway"


@mock_ec2
def test_modify_transit_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    g = ec2.create_transit_gateway(Description="my first gatway")["TransitGateway"]
    g_id = g["TransitGatewayId"]

    my_gateway = ec2.describe_transit_gateways(TransitGatewayIds=[g_id])[
        "TransitGateways"
    ][0]
    assert my_gateway["Description"] == "my first gatway"

    ec2.modify_transit_gateway(TransitGatewayId=g_id, Description="my first gateway")

    my_gateway = ec2.describe_transit_gateways(TransitGatewayIds=[g_id])[
        "TransitGateways"
    ][0]
    assert my_gateway["Description"] == "my first gateway"


@mock_ec2
def test_describe_transit_gateway_vpc_attachments():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateway_vpc_attachments()
    assert response["TransitGatewayVpcAttachments"] == []


@mock_ec2
def test_describe_transit_gateway_attachments():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateway_attachments()
    assert response["TransitGatewayAttachments"] == []


def retrieve_all_transit_gateways(ec2):
    resp = ec2.describe_transit_gateways()
    all_tg = resp["TransitGateways"]
    token = resp.get("NextToken")
    while token:
        resp = ec2.describe_transit_gateways(NextToken=token)
        all_tg.extend(resp["TransitGateways"])
        token = resp.get("NextToken")
    return all_tg


@mock_ec2
def test_create_transit_gateway_vpn_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    vpn_gateway = ec2.create_vpn_gateway(Type="ipsec.1").get("VpnGateway", {})
    customer_gateway = ec2.create_customer_gateway(
        Type="ipsec.1", PublicIp="205.251.242.54", BgpAsn=65534
    ).get("CustomerGateway", {})
    vpn_connection = ec2.create_vpn_connection(
        Type="ipsec.1",
        VpnGatewayId=vpn_gateway["VpnGatewayId"],
        CustomerGatewayId=customer_gateway["CustomerGatewayId"],
        TransitGatewayId="gateway_id",
    )["VpnConnection"]
    vpn_conn_id = vpn_connection["VpnConnectionId"]

    #
    # Verify we can retrieve it as a general attachment
    attachments = retrieve_all_attachments(ec2)
    assert vpn_conn_id in [a["ResourceId"] for a in attachments]

    my_attachments = [a for a in attachments if a["ResourceId"] == vpn_conn_id]
    assert len(my_attachments) == 1

    assert my_attachments[0]["ResourceType"] == "vpn"


def retrieve_all_attachments(client):
    resp = client.describe_transit_gateway_attachments()
    att = resp["TransitGatewayAttachments"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_transit_gateway_attachments(NextToken=token)
        att.extend(resp["TransitGatewayAttachments"])
        token = resp.get("NextToken")
    return att


@mock_ec2
def test_create_and_describe_transit_gateway_vpc_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId="gateway_id", VpcId="some-vpc-id", SubnetIds=["sub1"]
    )
    attachment = response["TransitGatewayVpcAttachment"]
    assert attachment["TransitGatewayAttachmentId"].startswith("tgw-attach-")
    assert attachment["TransitGatewayId"] == "gateway_id"
    assert attachment["VpcId"] == "some-vpc-id"
    assert attachment["VpcOwnerId"] == ACCOUNT_ID
    assert attachment["State"] == "available"
    assert attachment["SubnetIds"] == ["sub1"]
    assert attachment["Options"] == {
        "DnsSupport": "enable",
        "Ipv6Support": "disable",
        "ApplianceModeSupport": "disable",
    }
    assert attachment["Tags"] == []
    #
    # Verify we can retrieve it as a VPC attachment
    attachments = ec2.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[attachment["TransitGatewayAttachmentId"]]
    )["TransitGatewayVpcAttachments"]
    assert len(attachments) == 1
    assert "CreationTime" in attachments[0]
    del attachments[0]["CreationTime"]
    assert attachment == attachments[0]
    #
    # Verify we can retrieve it as a general attachment
    attachments = ec2.describe_transit_gateway_attachments(
        TransitGatewayAttachmentIds=[attachment["TransitGatewayAttachmentId"]]
    )["TransitGatewayAttachments"]
    assert len(attachments) == 1
    assert "CreationTime" in attachments[0]
    assert attachments[0]["TransitGatewayOwnerId"] == ACCOUNT_ID
    assert attachments[0]["ResourceOwnerId"] == ACCOUNT_ID
    assert attachments[0]["ResourceType"] == "vpc"
    assert attachments[0]["ResourceId"] == "some-vpc-id"
    assert attachments[0]["State"] == "available"
    assert attachments[0]["Tags"] == []
    assert (
        attachments[0]["TransitGatewayAttachmentId"]
        == attachment["TransitGatewayAttachmentId"]
    )
    assert attachments[0]["TransitGatewayId"] == "gateway_id"


@mock_ec2
def test_describe_transit_gateway_route_tables():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateway_route_tables()
    assert response["TransitGatewayRouteTables"] == []


@mock_ec2
def test_create_transit_gateway_route_table():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    table = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]
    assert table["TransitGatewayRouteTableId"].startswith("tgw-rtb")
    assert table["TransitGatewayId"] == gateway_id
    assert table["State"] == "available"
    assert table["DefaultAssociationRouteTable"] is False
    assert table["DefaultPropagationRouteTable"] is False
    assert "CreationTime" in table
    assert table["Tags"] == []

    tables = ec2.describe_transit_gateway_route_tables(
        TransitGatewayRouteTableIds=[table["TransitGatewayRouteTableId"]]
    )["TransitGatewayRouteTables"]
    assert len(tables) == 1


@mock_ec2
def test_create_transit_gateway_route_table_with_tags():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    response = ec2.create_transit_gateway_route_table(
        TransitGatewayId=gateway_id,
        TagSpecifications=[
            {
                "ResourceType": "transit-gateway-route-table",
                "Tags": [
                    {"Key": "tag1", "Value": "val1"},
                    {"Key": "tag2", "Value": "val2"},
                ],
            }
        ],
    )
    table = response["TransitGatewayRouteTable"]
    assert len(table["Tags"]) == 2
    assert {"Key": "tag1", "Value": "val1"} in table["Tags"]
    assert {"Key": "tag2", "Value": "val2"} in table["Tags"]


@mock_ec2
def test_delete_transit_gateway_route_table():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    table = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]
    table_id = table["TransitGatewayRouteTableId"]

    tables = ec2.describe_transit_gateway_route_tables(
        TransitGatewayRouteTableIds=[table_id]
    )["TransitGatewayRouteTables"]
    assert len(tables) == 1
    assert tables[0]["State"] == "available"

    table = ec2.delete_transit_gateway_route_table(TransitGatewayRouteTableId=table_id)

    assert table["TransitGatewayRouteTable"]["State"] == "deleted"

    tables = ec2.describe_transit_gateway_route_tables(
        TransitGatewayRouteTableIds=[table_id]
    )["TransitGatewayRouteTables"]
    assert len(tables) == 1
    assert tables[0]["State"] == "deleted"


@mock_ec2
def test_search_transit_gateway_routes_empty():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    table_id = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]["TransitGatewayRouteTableId"]

    response = ec2.search_transit_gateway_routes(
        TransitGatewayRouteTableId=table_id,
        Filters=[{"Name": "state", "Values": ["active"]}],
    )
    assert response["Routes"] == []
    assert response["AdditionalRoutesAvailable"] is False


@mock_ec2
def test_create_transit_gateway_route():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    table_id = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]["TransitGatewayRouteTableId"]

    route = ec2.create_transit_gateway_route(
        DestinationCidrBlock="0.0.0.0", TransitGatewayRouteTableId=table_id
    )["Route"]

    assert route["DestinationCidrBlock"] == "0.0.0.0"
    assert route["Type"] == "static"
    assert route["State"] == "active"


@mock_ec2
def test_create_transit_gateway_route_as_blackhole():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    table_id = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]["TransitGatewayRouteTableId"]

    route = ec2.create_transit_gateway_route(
        DestinationCidrBlock="192.168.0.1",
        TransitGatewayRouteTableId=table_id,
        Blackhole=True,
    )["Route"]

    assert route["DestinationCidrBlock"] == "192.168.0.1"
    assert route["Type"] == "static"
    assert route["State"] == "blackhole"


@mock_ec2
def test_search_transit_gateway_routes_by_state():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    table_id = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]["TransitGatewayRouteTableId"]

    ec2.create_transit_gateway_route(
        DestinationCidrBlock="192.168.0.0", TransitGatewayRouteTableId=table_id
    )

    ec2.create_transit_gateway_route(
        DestinationCidrBlock="192.168.0.1",
        TransitGatewayRouteTableId=table_id,
        Blackhole=True,
    )

    routes = ec2.search_transit_gateway_routes(
        TransitGatewayRouteTableId=table_id,
        Filters=[{"Name": "state", "Values": ["active"]}],
    )["Routes"]

    assert routes == [
        {"DestinationCidrBlock": "192.168.0.0", "Type": "static", "State": "active"}
    ]

    routes = ec2.search_transit_gateway_routes(
        TransitGatewayRouteTableId=table_id,
        Filters=[{"Name": "state", "Values": ["blackhole"]}],
    )["Routes"]

    assert routes == [
        {
            "DestinationCidrBlock": "192.168.0.1",
            "Type": "static",
            "State": "blackhole",
        }
    ]

    routes = ec2.search_transit_gateway_routes(
        TransitGatewayRouteTableId=table_id,
        Filters=[{"Name": "state", "Values": ["unknown"]}],
    )["Routes"]

    assert routes == []


@mock_ec2
def test_search_transit_gateway_routes_by_routesearch():
    client = boto3.client("ec2", region_name="us-west-2")
    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = client.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")["Subnet"]

    tgw = client.create_transit_gateway(Description="description")
    tgw_id = tgw["TransitGateway"]["TransitGatewayId"]
    route_table = client.create_transit_gateway_route_table(TransitGatewayId=tgw_id)
    transit_gateway_route_id = route_table["TransitGatewayRouteTable"][
        "TransitGatewayRouteTableId"
    ]

    attachment = client.create_transit_gateway_vpc_attachment(
        TransitGatewayId=tgw_id, VpcId=vpc["VpcId"], SubnetIds=[subnet["SubnetId"]]
    )
    transit_gateway_attachment_id = attachment["TransitGatewayVpcAttachment"][
        "TransitGatewayAttachmentId"
    ]

    exported_cidr_ranges = ["172.17.0.0/24", "192.160.0.0/24"]
    for route in exported_cidr_ranges:
        client.create_transit_gateway_route(
            DestinationCidrBlock=route,
            TransitGatewayRouteTableId=transit_gateway_route_id,
            TransitGatewayAttachmentId=transit_gateway_attachment_id,
        )

    for route in exported_cidr_ranges:
        expected_route = client.search_transit_gateway_routes(
            TransitGatewayRouteTableId=transit_gateway_route_id,
            Filters=[{"Name": "route-search.exact-match", "Values": [route]}],
        )

        assert expected_route["Routes"][0]["DestinationCidrBlock"] == route


@mock_ec2
def test_delete_transit_gateway_route():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    table_id = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]["TransitGatewayRouteTableId"]

    ec2.create_transit_gateway_route(
        DestinationCidrBlock="192.168.0.0", TransitGatewayRouteTableId=table_id
    )
    ec2.create_transit_gateway_route(
        DestinationCidrBlock="192.168.0.1", TransitGatewayRouteTableId=table_id
    )

    response = ec2.delete_transit_gateway_route(
        DestinationCidrBlock="192.168.0.0", TransitGatewayRouteTableId=table_id
    )

    assert response["Route"] == {
        "DestinationCidrBlock": "192.168.0.0",
        "Type": "static",
        "State": "deleted",
    }

    routes = ec2.search_transit_gateway_routes(
        TransitGatewayRouteTableId=table_id,
        Filters=[{"Name": "state", "Values": ["active"]}],
    )["Routes"]

    assert routes == [
        {"DestinationCidrBlock": "192.168.0.1", "Type": "static", "State": "active"}
    ]


@mock_ec2
def test_create_transit_gateway_vpc_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    response = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )
    assert "TransitGatewayVpcAttachment" in response
    attachment = response["TransitGatewayVpcAttachment"]
    attachment["TransitGatewayAttachmentId"].startswith("tgw-attach-")
    assert attachment["TransitGatewayId"] == gateway_id
    assert attachment["VpcId"] == "vpc-id"
    assert attachment["VpcOwnerId"] == ACCOUNT_ID
    assert attachment["SubnetIds"] == ["sub1"]
    assert attachment["State"] == "available"
    assert attachment["Tags"] == []


@mock_ec2
def test_modify_transit_gateway_vpc_attachment_add_subnets():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    response = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1", "sub3"]
    )
    attchmnt_id = response["TransitGatewayVpcAttachment"]["TransitGatewayAttachmentId"]

    ec2.modify_transit_gateway_vpc_attachment(
        TransitGatewayAttachmentId=attchmnt_id, AddSubnetIds=["sub2"]
    )

    attachment = ec2.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[attchmnt_id]
    )["TransitGatewayVpcAttachments"][0]
    assert sorted(attachment["SubnetIds"]) == ["sub1", "sub2", "sub3"]


@mock_ec2
def test_modify_transit_gateway_vpc_attachment_remove_subnets():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    response = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1", "sub2", "sub3"]
    )
    attchmnt_id = response["TransitGatewayVpcAttachment"]["TransitGatewayAttachmentId"]

    ec2.modify_transit_gateway_vpc_attachment(
        TransitGatewayAttachmentId=attchmnt_id, RemoveSubnetIds=["sub2"]
    )

    attachment = ec2.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[attchmnt_id]
    )["TransitGatewayVpcAttachments"][0]
    assert attachment["SubnetIds"] == ["sub1", "sub3"]


@mock_ec2
def test_modify_transit_gateway_vpc_attachment_change_options():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    response = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id,
        VpcId="vpc-id",
        SubnetIds=["sub1"],
        Options={
            "DnsSupport": "enable",
            "Ipv6Support": "enable",
            "ApplianceModeSupport": "enable",
        },
    )
    attchmnt_id = response["TransitGatewayVpcAttachment"]["TransitGatewayAttachmentId"]

    ec2.modify_transit_gateway_vpc_attachment(
        TransitGatewayAttachmentId=attchmnt_id,
        Options={"ApplianceModeSupport": "disabled"},
    )

    attachment = ec2.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[attchmnt_id]
    )["TransitGatewayVpcAttachments"][0]
    assert attachment["Options"]["ApplianceModeSupport"] == "disabled"
    assert attachment["Options"]["DnsSupport"] == "enable"
    assert attachment["Options"]["Ipv6Support"] == "enable"


@mock_ec2
def test_delete_transit_gateway_vpc_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    a1 = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )["TransitGatewayVpcAttachment"]["TransitGatewayAttachmentId"]
    a2 = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )["TransitGatewayVpcAttachment"]["TransitGatewayAttachmentId"]

    available = ec2.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[a1, a2],
        Filters=[{"Name": "state", "Values": ["available"]}],
    )["TransitGatewayVpcAttachments"]
    assert len(available) == 2

    a1_removed = ec2.delete_transit_gateway_vpc_attachment(
        TransitGatewayAttachmentId=a1
    )["TransitGatewayVpcAttachment"]
    assert a1_removed["TransitGatewayAttachmentId"] == a1
    assert a1_removed["State"] == "deleted"

    all_attchmnts = ec2.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[a1, a2]
    )["TransitGatewayVpcAttachments"]
    assert len(all_attchmnts) == 1
    assert [a["TransitGatewayAttachmentId"] for a in all_attchmnts] == [a2]


@mock_ec2
def test_associate_transit_gateway_route_table():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    attchmnt = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )["TransitGatewayVpcAttachment"]
    table = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]

    initial = ec2.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )
    assert initial["Associations"] == [
        {
            "TransitGatewayAttachmentId": "",
            "ResourceId": "",
            "ResourceType": "",
            "State": "",
        }
    ]

    ec2.associate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    updated = ec2.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )
    assert updated["Associations"] == [
        {
            "TransitGatewayAttachmentId": attchmnt["TransitGatewayAttachmentId"],
            "ResourceId": "vpc-id",
            "ResourceType": "vpc",
            "State": "associated",
        }
    ]


@mock_ec2
def test_disassociate_transit_gateway_route_table():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    attchmnt = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )["TransitGatewayVpcAttachment"]
    table = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]

    initial = ec2.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["Associations"][0]
    assert initial["TransitGatewayAttachmentId"] == ""

    ec2.associate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    updated = ec2.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["Associations"][0]
    assert (
        updated["TransitGatewayAttachmentId"] == attchmnt["TransitGatewayAttachmentId"]
    )
    assert updated["State"] == "associated"

    dis = ec2.disassociate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )["Association"]
    assert dis["State"] == "disassociated"

    updated = ec2.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["Associations"][0]
    assert updated["TransitGatewayAttachmentId"] == ""
    assert updated["State"] == ""


@mock_ec2
def test_enable_transit_gateway_route_table_propagation():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    attchmnt = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )["TransitGatewayVpcAttachment"]
    table = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]

    initial = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )
    assert initial["TransitGatewayRouteTablePropagations"] == [
        {
            "TransitGatewayAttachmentId": "",
            "ResourceId": "",
            "ResourceType": "",
            "State": "",
        }
    ]

    ec2.associate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    ec2.enable_transit_gateway_route_table_propagation(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    enabled = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )
    assert enabled["TransitGatewayRouteTablePropagations"] == [
        {
            "TransitGatewayAttachmentId": attchmnt["TransitGatewayAttachmentId"],
            "ResourceId": "vpc-id",
            "ResourceType": "vpc",
            "State": "enabled",
        }
    ]


@mock_ec2
def test_disable_transit_gateway_route_table_propagation_without_enabling_first():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    attchmnt = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )["TransitGatewayVpcAttachment"]
    table = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]

    initial = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )
    assert initial["TransitGatewayRouteTablePropagations"] == [
        {
            "TransitGatewayAttachmentId": "",
            "ResourceId": "",
            "ResourceType": "",
            "State": "",
        }
    ]

    ec2.associate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    with pytest.raises(Exception):
        ec2.disable_transit_gateway_route_table_propagation(
            TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
            TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
        )


@mock_ec2
def test_disable_transit_gateway_route_table_propagation():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    attchmnt = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )["TransitGatewayVpcAttachment"]
    table = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]

    initial = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )
    assert initial["TransitGatewayRouteTablePropagations"] == [
        {
            "TransitGatewayAttachmentId": "",
            "ResourceId": "",
            "ResourceType": "",
            "State": "",
        }
    ]

    ec2.associate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    ec2.enable_transit_gateway_route_table_propagation(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )
    ec2.disable_transit_gateway_route_table_propagation(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    disabled = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )
    assert disabled["TransitGatewayRouteTablePropagations"] == [
        {
            "ResourceId": "",
            "ResourceType": "",
            "State": "",
            "TransitGatewayAttachmentId": "",
        }
    ]
