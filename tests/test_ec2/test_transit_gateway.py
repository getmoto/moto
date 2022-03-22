import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_ec2, settings
from moto.core import ACCOUNT_ID
from unittest import SkipTest


@mock_ec2
def test_describe_transit_gateways():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateways()
    response.should.have.key("TransitGateways").equal([])


@mock_ec2
def test_create_transit_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.create_transit_gateway(
        Description="my first gateway", Options={"DnsSupport": "disable"}
    )
    gateway = response["TransitGateway"]
    gateway.should.have.key("TransitGatewayId").match("tgw-[a-z0-9]+")
    gateway.should.have.key("State").equal("available")
    gateway.should.have.key("OwnerId").equal(ACCOUNT_ID)
    gateway.should.have.key("Description").equal("my first gateway")
    gateway.should.have.key("Tags").equal([])
    options = gateway["Options"]
    options.should.have.key("AmazonSideAsn").equal(64512)
    options.should.have.key("TransitGatewayCidrBlocks").equal([])
    options.should.have.key("AutoAcceptSharedAttachments").equal("disable")
    options.should.have.key("DefaultRouteTableAssociation").equal("enable")
    options.should.have.key("DefaultRouteTablePropagation").equal("enable")
    options.should.have.key("PropagationDefaultRouteTableId").match("tgw-rtb-[a-z0-9]+")
    options.should.have.key("VpnEcmpSupport").equal("enable")
    options.should.have.key("DnsSupport").equal("disable")
    #
    # Verify we can retrieve it
    all_gateways = retrieve_all_transit_gateways(ec2)
    [gw["TransitGatewayId"] for gw in all_gateways].should.contain(
        gateway["TransitGatewayId"]
    )
    gateways = ec2.describe_transit_gateways(
        TransitGatewayIds=[gateway["TransitGatewayId"]]
    )["TransitGateways"]

    gateways.should.have.length_of(1)
    gateways[0].should.have.key("CreationTime")
    gateways[0].should.have.key("TransitGatewayArn").equal(
        "arn:aws:ec2:us-east-1:{}:transit-gateway/{}".format(
            ACCOUNT_ID, gateway["TransitGatewayId"]
        )
    )
    gateways[0]["Options"].should.have.key("AssociationDefaultRouteTableId").equal(
        gateways[0]["Options"]["PropagationDefaultRouteTableId"]
    )
    del gateways[0]["CreationTime"]
    del gateways[0]["TransitGatewayArn"]
    del gateways[0]["Options"]["AssociationDefaultRouteTableId"]
    gateway.should.equal(gateways[0])


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
    gateway.should.have.key("TransitGatewayId").match("tgw-[a-z0-9]+")
    tags = gateway.get("Tags", [])
    tags.should.have.length_of(2)
    tags.should.contain({"Key": "tag1", "Value": "val1"})
    tags.should.contain({"Key": "tag2", "Value": "val2"})


@mock_ec2
def test_delete_transit_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    g = ec2.create_transit_gateway(Description="my first gateway")["TransitGateway"]
    g_id = g["TransitGatewayId"]

    all_gateways = retrieve_all_transit_gateways(ec2)
    [g["TransitGatewayId"] for g in all_gateways].should.contain(g_id)

    ec2.delete_transit_gateway(TransitGatewayId=g_id)

    all_gateways = retrieve_all_transit_gateways(ec2)
    [g["TransitGatewayId"] for g in all_gateways].shouldnt.contain(g_id)


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
    my_gateway["TransitGatewayId"].should.equal(g2_id)
    my_gateway["Description"].should.equal("my second gatway")


@mock_ec2
def test_modify_transit_gateway():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    g = ec2.create_transit_gateway(Description="my first gatway")["TransitGateway"]
    g_id = g["TransitGatewayId"]

    my_gateway = ec2.describe_transit_gateways(TransitGatewayIds=[g_id])[
        "TransitGateways"
    ][0]
    my_gateway["Description"].should.equal("my first gatway")

    ec2.modify_transit_gateway(TransitGatewayId=g_id, Description="my first gateway")

    my_gateway = ec2.describe_transit_gateways(TransitGatewayIds=[g_id])[
        "TransitGateways"
    ][0]
    my_gateway["Description"].should.equal("my first gateway")


@mock_ec2
def test_describe_transit_gateway_vpc_attachments():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateway_vpc_attachments()
    response.should.have.key("TransitGatewayVpcAttachments").equal([])


@mock_ec2
def test_describe_transit_gateway_attachments():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateway_attachments()
    response.should.have.key("TransitGatewayAttachments").equal([])


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
    [a["ResourceId"] for a in attachments].should.contain(vpn_conn_id)

    my_attachments = [a for a in attachments if a["ResourceId"] == vpn_conn_id]
    my_attachments.should.have.length_of(1)

    my_attachments[0].should.have.key("ResourceType").equal("vpn")


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
    attachment.should.have.key("TransitGatewayAttachmentId").match("tgw-attach-*")
    attachment.should.have.key("TransitGatewayId").equal("gateway_id")
    attachment.should.have.key("VpcId").equal("some-vpc-id")
    attachment.should.have.key("VpcOwnerId").equal(ACCOUNT_ID)
    attachment.should.have.key("State").equal("available")
    attachment.should.have.key("SubnetIds").equal(["sub1"])
    attachment.should.have.key("Options").equal(
        {
            "DnsSupport": "enable",
            "Ipv6Support": "disable",
            "ApplianceModeSupport": "disable",
        }
    )
    attachment.should.have.key("Tags").equal([])
    #
    # Verify we can retrieve it as a VPC attachment
    attachments = ec2.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[attachment["TransitGatewayAttachmentId"]]
    )["TransitGatewayVpcAttachments"]
    attachments.should.have.length_of(1)
    attachments[0].should.have.key("CreationTime")
    del attachments[0]["CreationTime"]
    attachment.should.equal(attachments[0])
    #
    # Verify we can retrieve it as a general attachment
    attachments = ec2.describe_transit_gateway_attachments(
        TransitGatewayAttachmentIds=[attachment["TransitGatewayAttachmentId"]]
    )["TransitGatewayAttachments"]
    attachments.should.have.length_of(1)
    attachments[0].should.have.key("CreationTime")
    attachments[0].should.have.key("TransitGatewayOwnerId").equal(ACCOUNT_ID)
    attachments[0].should.have.key("ResourceOwnerId").equal(ACCOUNT_ID)
    attachments[0].should.have.key("ResourceType").equal("vpc")
    attachments[0].should.have.key("ResourceId").equal("some-vpc-id")
    attachments[0].should.have.key("State").equal("available")
    attachments[0].should.have.key("Tags").equal([])
    attachments[0].should.have.key("TransitGatewayAttachmentId").equal(
        attachment["TransitGatewayAttachmentId"]
    )
    attachments[0].should.have.key("TransitGatewayId").equal("gateway_id")


@mock_ec2
def test_describe_transit_gateway_route_tables():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to be empty")
    ec2 = boto3.client("ec2", region_name="us-west-1")
    response = ec2.describe_transit_gateway_route_tables()
    response.should.have.key("TransitGatewayRouteTables").equal([])


@mock_ec2
def test_create_transit_gateway_route_table():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    table = ec2.create_transit_gateway_route_table(TransitGatewayId=gateway_id)[
        "TransitGatewayRouteTable"
    ]
    table.should.have.key("TransitGatewayRouteTableId").match("tgw-rtb-[0-9a-z]+")
    table.should.have.key("TransitGatewayId").equals(gateway_id)
    table.should.have.key("State").equals("available")
    table.should.have.key("DefaultAssociationRouteTable").equals(False)
    table.should.have.key("DefaultPropagationRouteTable").equals(False)
    table.should.have.key("CreationTime")
    table.should.have.key("Tags").equals([])

    tables = ec2.describe_transit_gateway_route_tables(
        TransitGatewayRouteTableIds=[table["TransitGatewayRouteTableId"]]
    )["TransitGatewayRouteTables"]
    tables.should.have.length_of(1)


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
    table["Tags"].should.have.length_of(2)
    table["Tags"].should.contain({"Key": "tag1", "Value": "val1"})
    table["Tags"].should.contain({"Key": "tag2", "Value": "val2"})


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
    tables.should.have.length_of(1)
    tables[0]["State"].should.equal("available")

    table = ec2.delete_transit_gateway_route_table(TransitGatewayRouteTableId=table_id)

    table["TransitGatewayRouteTable"].should.have.key("State").equals("deleted")

    tables = ec2.describe_transit_gateway_route_tables(
        TransitGatewayRouteTableIds=[table_id]
    )["TransitGatewayRouteTables"]
    tables.should.have.length_of(1)
    tables[0]["State"].should.equal("deleted")


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
    response.should.have.key("Routes").equal([])
    response.should.have.key("AdditionalRoutesAvailable").equal(False)


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

    route.should.have.key("DestinationCidrBlock").equal("0.0.0.0")
    route.should.have.key("Type").equal("static")
    route.should.have.key("State").equal("active")


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

    route.should.have.key("DestinationCidrBlock").equal("192.168.0.1")
    route.should.have.key("Type").equal("static")
    route.should.have.key("State").equal("blackhole")


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

    routes.should.equal(
        [{"DestinationCidrBlock": "192.168.0.0", "Type": "static", "State": "active"}]
    )

    routes = ec2.search_transit_gateway_routes(
        TransitGatewayRouteTableId=table_id,
        Filters=[{"Name": "state", "Values": ["blackhole"]}],
    )["Routes"]

    routes.should.equal(
        [
            {
                "DestinationCidrBlock": "192.168.0.1",
                "Type": "static",
                "State": "blackhole",
            }
        ]
    )

    routes = ec2.search_transit_gateway_routes(
        TransitGatewayRouteTableId=table_id,
        Filters=[{"Name": "state", "Values": ["unknown"]}],
    )["Routes"]

    routes.should.equal([])


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

    response["Route"].should.equal(
        {"DestinationCidrBlock": "192.168.0.0", "Type": "static", "State": "deleted"}
    )

    routes = ec2.search_transit_gateway_routes(
        TransitGatewayRouteTableId=table_id,
        Filters=[{"Name": "state", "Values": ["active"]}],
    )["Routes"]

    routes.should.equal(
        [{"DestinationCidrBlock": "192.168.0.1", "Type": "static", "State": "active"}]
    )


@mock_ec2
def test_create_transit_gateway_vpc_attachment():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    gateway_id = ec2.create_transit_gateway(Description="g")["TransitGateway"][
        "TransitGatewayId"
    ]
    response = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id, VpcId="vpc-id", SubnetIds=["sub1"]
    )
    response.should.have.key("TransitGatewayVpcAttachment")
    attachment = response["TransitGatewayVpcAttachment"]
    attachment.should.have.key("TransitGatewayAttachmentId").match(
        "tgw-attach-[0-9a-z]+"
    )
    attachment.should.have.key("TransitGatewayId").equal(gateway_id)
    attachment.should.have.key("VpcId").equal("vpc-id")
    attachment.should.have.key("VpcOwnerId").equal(ACCOUNT_ID)
    attachment.should.have.key("SubnetIds").equal(["sub1"])
    attachment.should.have.key("State").equal("available")
    attachment.should.have.key("Tags").equal([])


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
    sorted(attachment["SubnetIds"]).should.equal(["sub1", "sub2", "sub3"])


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
    attachment["SubnetIds"].should.equal(["sub1", "sub3"])


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
    attachment["Options"]["ApplianceModeSupport"].should.equal("disabled")
    attachment["Options"]["DnsSupport"].should.equal("enable")
    attachment["Options"]["Ipv6Support"].should.equal("enable")


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
    available.should.have.length_of(2)

    a1_removed = ec2.delete_transit_gateway_vpc_attachment(
        TransitGatewayAttachmentId=a1
    )["TransitGatewayVpcAttachment"]
    a1_removed.should.have.key("TransitGatewayAttachmentId").equal(a1)
    a1_removed.should.have.key("State").equal("deleted")

    all_attchmnts = ec2.describe_transit_gateway_vpc_attachments(
        TransitGatewayAttachmentIds=[a1, a2]
    )["TransitGatewayVpcAttachments"]
    all_attchmnts.should.have.length_of(1)
    [a["TransitGatewayAttachmentId"] for a in all_attchmnts].should.equal([a2])


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
    initial["Associations"].should.equal(
        [
            {
                "TransitGatewayAttachmentId": "",
                "ResourceId": "",
                "ResourceType": "",
                "State": "",
            }
        ]
    )

    ec2.associate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    updated = ec2.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )
    updated["Associations"].should.equal(
        [
            {
                "TransitGatewayAttachmentId": attchmnt["TransitGatewayAttachmentId"],
                "ResourceId": "vpc-id",
                "ResourceType": "vpc",
                "State": "associated",
            }
        ]
    )


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
    initial["TransitGatewayAttachmentId"].should.equal("")

    ec2.associate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    updated = ec2.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["Associations"][0]
    updated["TransitGatewayAttachmentId"].should.equal(
        attchmnt["TransitGatewayAttachmentId"]
    )
    updated["State"].should.equal("associated")

    dis = ec2.disassociate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )["Association"]
    dis["State"].should.equal("disassociated")

    updated = ec2.get_transit_gateway_route_table_associations(
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
    )["Associations"][0]
    updated["TransitGatewayAttachmentId"].should.equal("")
    updated["State"].should.equal("")


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
    initial["TransitGatewayRouteTablePropagations"].should.equal(
        [
            {
                "TransitGatewayAttachmentId": "",
                "ResourceId": "",
                "ResourceType": "",
                "State": "",
            }
        ]
    )

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
    enabled["TransitGatewayRouteTablePropagations"].should.equal(
        [
            {
                "TransitGatewayAttachmentId": attchmnt["TransitGatewayAttachmentId"],
                "ResourceId": "vpc-id",
                "ResourceType": "vpc",
                "State": "enabled",
            }
        ]
    )


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
    initial["TransitGatewayRouteTablePropagations"].should.equal(
        [
            {
                "TransitGatewayAttachmentId": "",
                "ResourceId": "",
                "ResourceType": "",
                "State": "",
            }
        ]
    )

    ec2.associate_transit_gateway_route_table(
        TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
        TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
    )

    try:
        ec2.disable_transit_gateway_route_table_propagation(
            TransitGatewayAttachmentId=attchmnt["TransitGatewayAttachmentId"],
            TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"],
        )
        assert False, "Should not be able to disable before enabling it"
    except Exception:
        pass


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
    initial["TransitGatewayRouteTablePropagations"].should.equal(
        [
            {
                "TransitGatewayAttachmentId": "",
                "ResourceId": "",
                "ResourceType": "",
                "State": "",
            }
        ]
    )

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
    disabled["TransitGatewayRouteTablePropagations"].should.equal(
        [
            {
                "ResourceId": "",
                "ResourceType": "",
                "State": "",
                "TransitGatewayAttachmentId": "",
            }
        ]
    )
