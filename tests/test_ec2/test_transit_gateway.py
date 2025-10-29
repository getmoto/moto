from time import sleep
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests.test_ec2 import (
    delete_tg_attachments,
    ec2_aws_verified,
    wait_for_transit_gateway_attachments,
    wait_for_vpn_connections,
)


@mock_aws
def test_describe_transit_gateways():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateways()
    assert response["TransitGateways"] == []


@mock_aws
def test_create_transit_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.create_transit_gateway(
        Description="my first gateway", Options={"DnsSupport": "disable"}
    )
    gateway = response["TransitGateway"]
    assert gateway["TransitGatewayId"].startswith("tgw-")
    assert (
        gateway["TransitGatewayArn"]
        == f"arn:aws:ec2:us-west-1:{ACCOUNT_ID}:transit-gateway/{gateway['TransitGatewayId']}"
    )
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
        == f"arn:aws:ec2:us-west-1:{ACCOUNT_ID}:transit-gateway/{gateway['TransitGatewayId']}"
    )
    assert (
        gateways[0]["Options"]["AssociationDefaultRouteTableId"]
        == gateways[0]["Options"]["PropagationDefaultRouteTableId"]
    )
    assert gateway == gateways[0]


@mock_aws
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


@mock_aws
def test_delete_transit_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    g = ec2.create_transit_gateway(Description="my first gateway")["TransitGateway"]
    g_id = g["TransitGatewayId"]

    all_gateways = retrieve_all_transit_gateways(ec2)
    assert g_id in [g["TransitGatewayId"] for g in all_gateways]

    ec2.delete_transit_gateway(TransitGatewayId=g_id)

    all_gateways = retrieve_all_transit_gateways(ec2)
    assert g_id not in [g["TransitGatewayId"] for g in all_gateways]


@mock_aws
def test_describe_transit_gateway_by_id():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2.create_transit_gateway(Description="my first gatway")["TransitGateway"]
    g2 = ec2.create_transit_gateway(Description="my second gatway")["TransitGateway"]
    g2_id = g2["TransitGatewayId"]
    ec2.create_transit_gateway(Description="my third gatway")["TransitGateway"]

    gateways = ec2.describe_transit_gateways(TransitGatewayIds=[g2_id])[
        "TransitGateways"
    ]
    assert len(gateways) == 1

    my_gateway = gateways[0]
    assert my_gateway["TransitGatewayId"] == g2_id
    assert my_gateway["Description"] == "my second gatway"


@mock_aws
def test_describe_transit_gateway_by_tags():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2.create_transit_gateway(
        Description="my first gatway",
        TagSpecifications=[
            {
                "ResourceType": "transit-gateway-route-table",
                "Tags": [
                    {"Key": "tag1", "Value": "val1"},
                    {"Key": "tag2", "Value": "val2"},
                ],
            }
        ],
    )["TransitGateway"]
    g2 = ec2.create_transit_gateway(Description="my second gatway")["TransitGateway"]
    g2 = ec2.create_transit_gateway(
        Description="my second gatway",
        TagSpecifications=[
            {
                "ResourceType": "transit-gateway-route-table",
                "Tags": [
                    {"Key": "the-tag", "Value": "the-value"},
                    {"Key": "tag2", "Value": "val2"},
                ],
            }
        ],
    )["TransitGateway"]
    g2_id = g2["TransitGatewayId"]
    ec2.create_transit_gateway(Description="my third gatway")["TransitGateway"]

    gateways = ec2.describe_transit_gateways(
        Filters=[{"Name": "tag:the-tag", "Values": ["the-value"]}]
    )["TransitGateways"]

    assert len(gateways) == 1

    my_gateway = gateways[0]
    assert my_gateway["TransitGatewayId"] == g2_id
    assert my_gateway["Description"] == "my second gatway"


@mock_aws
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


@mock_aws
def test_describe_transit_gateway_vpc_attachments():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateway_vpc_attachments()
    assert response["TransitGatewayVpcAttachments"] == []


@mock_aws
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


@pytest.mark.aws_verified
@ec2_aws_verified(create_transit_gateway=True, create_customer_gateway=True)
def test_create_transit_gateway_vpn_attachment(ec2_client=None, tg_id=None, cg_id=None):
    vpn_conn_id = None
    try:
        vpn_connection = ec2_client.create_vpn_connection(
            Type="ipsec.1",
            CustomerGatewayId=cg_id,
            TransitGatewayId=tg_id,
        )["VpnConnection"]
        vpn_conn_id = vpn_connection["VpnConnectionId"]
        wait_for_vpn_connections(ec2_client, vpn_connection_id=vpn_conn_id)

        # Get default RouteTableID
        default_route_table_id = ec2_client.describe_transit_gateway_route_tables(
            Filters=[{"Name": "transit-gateway-id", "Values": [tg_id]}]
        )["TransitGatewayRouteTables"][0]["TransitGatewayRouteTableId"]

        #
        # Verify we can retrieve it as a general attachment
        attachments = retrieve_all_attachments(ec2_client)
        assert vpn_conn_id in [a["ResourceId"] for a in attachments]

        my_attachments = [a for a in attachments if a["ResourceId"] == vpn_conn_id]

        assert len(my_attachments) == 1
        attachment = my_attachments[0]

        assert attachment["Association"] == {
            "State": "associated",
            "TransitGatewayRouteTableId": default_route_table_id,
        }
        assert attachment["ResourceType"] == "vpn"
        assert attachment["ResourceId"] == vpn_conn_id
        assert attachment["TransitGatewayId"] == tg_id
    finally:
        if vpn_conn_id:
            ec2_client.delete_vpn_connection(VpnConnectionId=vpn_conn_id)


def retrieve_all_attachments(client):
    resp = client.describe_transit_gateway_attachments()
    att = resp["TransitGatewayAttachments"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_transit_gateway_attachments(NextToken=token)
        att.extend(resp["TransitGatewayAttachments"])
        token = resp.get("NextToken")
    return att


@pytest.mark.aws_verified
@ec2_aws_verified(create_vpc=True, create_subnet=True, create_transit_gateway=True)
def test_create_and_describe_transit_gateway_vpc_attachment(
    account_id, ec2_client=None, vpc_id=None, subnet_id=None, tg_id=None
):
    response = ec2_client.create_transit_gateway_vpc_attachment(
        TransitGatewayId=tg_id,
        VpcId=vpc_id,
        SubnetIds=[subnet_id],
    )
    create = response["TransitGatewayVpcAttachment"]
    tg_attachment_id = create["TransitGatewayAttachmentId"]

    # Get default RouteTableID
    default_route_table_id = ec2_client.describe_transit_gateway_route_tables(
        Filters=[{"Name": "transit-gateway-id", "Values": [tg_id]}]
    )["TransitGatewayRouteTables"][0]["TransitGatewayRouteTableId"]

    assert create["TransitGatewayAttachmentId"].startswith("tgw-attach-")
    assert create["TransitGatewayId"] == tg_id
    assert create["VpcId"] == vpc_id
    assert create["VpcOwnerId"] == account_id
    # AWS returns 'pending' - Moto is immediately 'available'
    assert create["State"] in ["pending", "available"]
    assert create["SubnetIds"] == [subnet_id]
    assert create["Options"]["DnsSupport"] == "enable"
    assert create["Options"]["Ipv6Support"] == "disable"
    assert create["Options"]["ApplianceModeSupport"] == "disable"
    # When running this test against AWS, the value appears to be random at creation
    assert create["Options"]["SecurityGroupReferencingSupport"] in ["disable", "enable"]
    assert "Tags" not in create
    assert "CreationTime" in create

    # Wait until the attachment is fully ready
    wait_for_transit_gateway_attachments(ec2_client, tg_attachment_id=tg_attachment_id)

    #
    # Verify we can retrieve it as a VPC attachment
    attachments = ec2_client.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[tg_attachment_id]
    )["TransitGatewayVpcAttachments"]
    assert len(attachments) == 1
    describe = attachments[0]
    assert "CreationTime" in describe
    assert describe["Options"] == create["Options"]
    assert describe["State"] == "available"
    assert describe["TransitGatewayAttachmentId"] == tg_attachment_id
    assert describe["TransitGatewayId"] == tg_id
    assert describe["VpcId"] == vpc_id
    assert describe["VpcOwnerId"] == account_id

    #
    # Verify we can retrieve it as a general attachment
    attachments = ec2_client.describe_transit_gateway_attachments(
        TransitGatewayAttachmentIds=[tg_attachment_id]
    )["TransitGatewayAttachments"]
    assert len(attachments) == 1
    assert "CreationTime" in attachments[0]
    assert attachments[0]["TransitGatewayOwnerId"] == account_id
    assert attachments[0]["ResourceOwnerId"] == account_id
    assert attachments[0]["ResourceType"] == "vpc"
    assert attachments[0]["ResourceId"] == vpc_id
    assert attachments[0]["State"] == "available"
    assert attachments[0]["TransitGatewayAttachmentId"] == tg_attachment_id
    assert attachments[0]["TransitGatewayId"] == tg_id
    assert attachments[0]["Association"] == {
        "TransitGatewayRouteTableId": default_route_table_id,
        "State": "associated",
    }


@mock_aws
def test_describe_transit_gateway_route_tables():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateway_route_tables()
    assert response["TransitGatewayRouteTables"] == []


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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
    assert "Tags" not in attachment


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
def test_delete_transit_gateway_vpc_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    a1 = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )["TransitGatewayVpcAttachment"]["TransitGatewayAttachmentId"]
    a2 = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id2", SubnetIds=["sub1"]
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


@pytest.mark.aws_verified
@ec2_aws_verified(create_vpc=False, create_subnet=False, create_transit_gateway=True)
def test_default_route_table(account_id, ec2_client=None, tg_id=None):
    existing_tables = ec2_client.describe_transit_gateway_route_tables(
        Filters=[{"Name": "transit-gateway-id", "Values": [tg_id]}]
    )["TransitGatewayRouteTables"]
    assert len(existing_tables) == 1
    assert existing_tables[0]["TransitGatewayId"] == tg_id
    assert existing_tables[0]["DefaultAssociationRouteTable"] is True
    assert existing_tables[0]["DefaultPropagationRouteTable"] is True

    initial = ec2_client.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=existing_tables[0]["TransitGatewayRouteTableId"]
    )
    assert initial["Associations"] == []


@pytest.mark.aws_verified
@ec2_aws_verified(create_vpc=True, create_subnet=True, create_transit_gateway=True)
def test_new_attachment_is_immediately_associated_to_default_route_table(
    account_id, ec2_client=None, vpc_id=None, subnet_id=None, tg_id=None
):
    # Get default RouteTableID
    default_route_table_id = ec2_client.describe_transit_gateway_route_tables(
        Filters=[{"Name": "transit-gateway-id", "Values": [tg_id]}]
    )["TransitGatewayRouteTables"][0]["TransitGatewayRouteTableId"]

    # Create VPC Attachment
    attchmnt = ec2_client.create_transit_gateway_vpc_attachment(
        TransitGatewayId=tg_id, VpcId=vpc_id, SubnetIds=[subnet_id]
    )["TransitGatewayVpcAttachment"]
    tg_attachment_id = attchmnt["TransitGatewayAttachmentId"]
    wait_for_transit_gateway_attachments(ec2_client, tg_attachment_id=tg_attachment_id)

    # Verify Attachment is associated to default RouteTable
    assocs = ec2_client.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=default_route_table_id
    )["Associations"]
    assert len(assocs) == 1
    assert assocs[0] == {
        "TransitGatewayAttachmentId": tg_attachment_id,
        "ResourceId": vpc_id,
        "ResourceType": "vpc",
        "State": "associated",
    }


@pytest.mark.aws_verified
@ec2_aws_verified(create_vpc=True, create_subnet=True)
def test_create_vpc_attachment_to_unknown_transit_gateway(
    account_id, ec2_client=None, vpc_id=None, subnet_id=None
):
    # Create VPC Attachment to unknown TransitGateway
    with pytest.raises(ClientError) as exc:
        ec2_client.create_transit_gateway_vpc_attachment(
            TransitGatewayId="tgw-fb63e95d22999bf27",
            VpcId=vpc_id,
            SubnetIds=[subnet_id],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidTransitGatewayID.NotFound"
    assert (
        err["Message"]
        == "Transit Gateway tgw-fb63e95d22999bf27 was deleted or does not exist."
    )


@pytest.mark.aws_verified
@ec2_aws_verified(create_vpc=True, create_subnet=True, create_transit_gateway=True)
def test_create_vpc_attachment_twice(
    account_id, ec2_client=None, vpc_id=None, subnet_id=None, tg_id=None
):
    # Create VPC Attachment one
    attchmnt1 = ec2_client.create_transit_gateway_vpc_attachment(
        TransitGatewayId=tg_id, VpcId=vpc_id, SubnetIds=[subnet_id]
    )["TransitGatewayVpcAttachment"]
    tg_attachment_id1 = attchmnt1["TransitGatewayAttachmentId"]
    wait_for_transit_gateway_attachments(ec2_client, tg_attachment_id=tg_attachment_id1)

    # Create VPC Attachment two
    with pytest.raises(ClientError) as exc:
        ec2_client.create_transit_gateway_vpc_attachment(
            TransitGatewayId=tg_id, VpcId=vpc_id, SubnetIds=[subnet_id]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "DuplicateTransitGatewayAttachment"
    assert (
        err["Message"]
        == f"{tg_id} has non-deleted Transit Gateway Attachments with same VPC ID."
    )


@pytest.mark.aws_verified
@ec2_aws_verified(create_vpc=True, create_subnet=True, create_transit_gateway=True)
def test_create_vpc_attachment_for_different_vpcs(
    account_id, ec2_client=None, vpc_id=None, subnet_id=None, tg_id=None
):
    vpc_id1 = vpc_id
    # Get default RouteTableID
    default_route_table_id = ec2_client.describe_transit_gateway_route_tables(
        Filters=[{"Name": "transit-gateway-id", "Values": [tg_id]}]
    )["TransitGatewayRouteTables"][0]["TransitGatewayRouteTableId"]

    # Create VPC Attachment one
    attchmnt1 = ec2_client.create_transit_gateway_vpc_attachment(
        TransitGatewayId=tg_id, VpcId=vpc_id, SubnetIds=[subnet_id]
    )["TransitGatewayVpcAttachment"]
    tg_attachment_id1 = attchmnt1["TransitGatewayAttachmentId"]
    wait_for_transit_gateway_attachments(ec2_client, tg_attachment_id=tg_attachment_id1)

    def _create_second_attachment(ec2_client=None, vpc_id=None, subnet_id=None):
        vpc_id2 = vpc_id
        try:
            # Create VPC Attachment one
            attchmnt2 = ec2_client.create_transit_gateway_vpc_attachment(
                TransitGatewayId=tg_id, VpcId=vpc_id, SubnetIds=[subnet_id]
            )["TransitGatewayVpcAttachment"]
            tg_attachment_id2 = attchmnt2["TransitGatewayAttachmentId"]
            wait_for_transit_gateway_attachments(
                ec2_client, tg_attachment_id=tg_attachment_id2
            )

            assocs = ec2_client.get_transit_gateway_route_table_associations(
                TransitGatewayRouteTableId=default_route_table_id
            )["Associations"]
            assert len(assocs) == 2
            assert {
                "TransitGatewayAttachmentId": tg_attachment_id1,
                "ResourceId": vpc_id1,
                "ResourceType": "vpc",
                "State": "associated",
            } in assocs
            assert {
                "TransitGatewayAttachmentId": tg_attachment_id2,
                "ResourceId": vpc_id2,
                "ResourceType": "vpc",
                "State": "associated",
            } in assocs
        finally:
            # The Attachment is deleted automatically, but only outside the scope of this function
            # Deleting the VPC inside this function is therefore impossible
            # That's why we delete the Attachment here manually
            delete_tg_attachments(ec2_client, tg_id=tg_id)

    # Create the second attachment inside the `ec2_aws_verified` function
    # This will automatically create (and destroy!) the VPC/subnet resources that we need
    ec2_aws_verified(create_vpc=True, create_subnet=True)(_create_second_attachment)()


@mock_aws
# TODO: run this against AWS, and check for Assocation-key
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


@mock_aws
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
    )["Associations"]
    assert len(updated) == 0


@mock_aws
def test_enable_transit_gateway_route_table_propagation():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2_resource = boto3.resource("ec2", region_name="us-east-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    vpc_id = ec2_resource.create_vpc(CidrBlock="10.0.0.0/16").id
    subnet_id = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/24")["Subnet"][
        "SubnetId"
    ]

    gateway1_status = "unknown"
    while gateway1_status != "available":
        sleep(0.5)
        gateway1_status = ec2.describe_transit_gateways(TransitGatewayIds=[gateway_id])[
            "TransitGateways"
        ][0]["State"]

    attchmnt_id = _create_attachment(ec2, gateway_id, subnet_id, vpc_id)

    table = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]
    table_status = "unknown"
    while table_status != "available":
        table_status = ec2.describe_transit_gateway_route_tables(
            TransitGatewayRouteTableIds=[table["TransitGatewayRouteTableId"]]
        )["TransitGatewayRouteTables"][0]["State"]
        sleep(0.5)

    initial = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["TransitGatewayRouteTablePropagations"]
    assert initial == []

    ec2.enable_transit_gateway_route_table_propagation(
        TransitGatewayAttachmentId=attchmnt_id,
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    propagations = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["TransitGatewayRouteTablePropagations"]
    assert propagations == [
        {
            "TransitGatewayAttachmentId": attchmnt_id,
            "ResourceId": vpc_id,
            "ResourceType": "vpc",
            "State": "enabled",
        }
    ]

    # Create second propagation
    vpc_id2 = ec2_resource.create_vpc(CidrBlock="10.0.0.1/16").id
    subnet_id2 = ec2.create_subnet(VpcId=vpc_id2, CidrBlock="10.0.0.1/24")["Subnet"][
        "SubnetId"
    ]
    attchmnt_id2 = _create_attachment(ec2, gateway_id, subnet_id2, vpc_id2)

    propagations = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["TransitGatewayRouteTablePropagations"]
    assert propagations == [
        {
            "TransitGatewayAttachmentId": attchmnt_id,
            "ResourceId": vpc_id,
            "ResourceType": "vpc",
            "State": "enabled",
        }
    ]

    ec2.enable_transit_gateway_route_table_propagation(
        TransitGatewayAttachmentId=attchmnt_id2,
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    propagations = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["TransitGatewayRouteTablePropagations"]
    assert propagations == [
        {
            "TransitGatewayAttachmentId": attchmnt_id,
            "ResourceId": vpc_id,
            "ResourceType": "vpc",
            "State": "enabled",
        },
        {
            "TransitGatewayAttachmentId": attchmnt_id2,
            "ResourceId": vpc_id2,
            "ResourceType": "vpc",
            "State": "enabled",
        },
    ]

    # Verify it disappears after deleting the attachment
    _delete_attachment(attchmnt_id2, ec2)
    ec2.delete_subnet(SubnetId=subnet_id2)
    ec2.delete_vpc(VpcId=vpc_id2)

    propagations = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["TransitGatewayRouteTablePropagations"]
    assert propagations == [
        {
            "TransitGatewayAttachmentId": attchmnt_id,
            "ResourceId": vpc_id,
            "ResourceType": "vpc",
            "State": "enabled",
        }
    ]

    # Create third propagation
    vpc_id3 = ec2_resource.create_vpc(CidrBlock="10.0.0.2/16").id
    subnet_id3 = ec2.create_subnet(VpcId=vpc_id3, CidrBlock="10.0.0.2/24")["Subnet"][
        "SubnetId"
    ]
    attchmnt_id3 = _create_attachment(ec2, gateway_id, subnet_id3, vpc_id3)

    ec2.enable_transit_gateway_route_table_propagation(
        TransitGatewayAttachmentId=attchmnt_id3,
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    propagations = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["TransitGatewayRouteTablePropagations"]
    assert propagations == [
        {
            "TransitGatewayAttachmentId": attchmnt_id,
            "ResourceId": vpc_id,
            "ResourceType": "vpc",
            "State": "enabled",
        },
        {
            "TransitGatewayAttachmentId": attchmnt_id3,
            "ResourceId": vpc_id3,
            "ResourceType": "vpc",
            "State": "enabled",
        },
    ]

    # Verify it disappears after deleting the attachment
    ec2.disable_transit_gateway_route_table_propagation(
        TransitGatewayAttachmentId=attchmnt_id3,
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    propagations = ec2.get_transit_gateway_route_table_propagations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["TransitGatewayRouteTablePropagations"]
    assert propagations == [
        {
            "TransitGatewayAttachmentId": attchmnt_id,
            "ResourceId": vpc_id,
            "ResourceType": "vpc",
            "State": "enabled",
        }
    ]
    _delete_attachment(attchmnt_id3, ec2)
    ec2.delete_subnet(SubnetId=subnet_id3)
    ec2.delete_vpc(VpcId=vpc_id3)

    _delete_attachment(attchmnt_id, ec2)
    ec2.delete_transit_gateway(TransitGatewayId=gateway_id)
    ec2.delete_subnet(SubnetId=subnet_id)
    ec2.delete_vpc(VpcId=vpc_id)


def _create_attachment(ec2, gateway_id, subnet_id, vpc_id):
    attchmnt = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId=vpc_id, SubnetIds=[subnet_id]
    )["TransitGatewayVpcAttachment"]
    attchmtn_status = "unknown"
    while attchmtn_status != "available":
        attchmtn_status = ec2.describe_transit_gateway_vpc_attachments(
            TransitGatewayAttachmentIds=[attchmnt["TransitGatewayAttachmentId"]]
        )["TransitGatewayVpcAttachments"][0]["State"]
        sleep(0.1)
    return attchmnt["TransitGatewayAttachmentId"]


def _delete_attachment(attchmnt_id, ec2):
    ec2.delete_transit_gateway_vpc_attachment(TransitGatewayAttachmentId=attchmnt_id)
    attchmtn_status = "unknown"
    while attchmtn_status != "deleted":
        attachments = ec2.describe_transit_gateway_vpc_attachments(
            TransitGatewayAttachmentIds=[attchmnt_id]
        )["TransitGatewayVpcAttachments"]
        if not attachments:
            break
        attchmtn_status = attachments[0]["State"]
        sleep(0.1)


@mock_aws
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
    assert initial["TransitGatewayRouteTablePropagations"] == []

    ec2.associate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    # Currently throws a KeyError
    with pytest.raises(Exception):  # noqa: B017 Do not assert blind exception: `Exception`
        ec2.disable_transit_gateway_route_table_propagation(
            TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
            TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
        )


@mock_aws
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
    assert initial["TransitGatewayRouteTablePropagations"] == []

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
    assert disabled["TransitGatewayRouteTablePropagations"] == []
