from contextlib import nullcontext
from functools import wraps
from time import sleep
from uuid import uuid4

import boto3

from moto import mock_aws
from tests import allow_aws_request


def ec2_aws_verified(
    create_vpc: bool = False,
    create_sg: bool = False,
    create_subnet: bool = False,
    create_transit_gateway: bool = False,
    create_customer_gateway: bool = False,
):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.

    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper(**kwargs):
            context = nullcontext() if allow_aws_request() else mock_aws()

            with context:
                return _invoke_func(
                    create_vpc,
                    create_sg=create_sg,
                    create_subnet=create_subnet,
                    create_transit_gateway=create_transit_gateway,
                    create_customer_gateway=create_customer_gateway,
                    func=func,
                    kwargs=kwargs,
                )

        return pagination_wrapper

    return inner


def _invoke_func(
    create_vpc: bool,
    create_sg: bool,
    create_subnet: bool,
    create_transit_gateway: bool,
    create_customer_gateway: bool,
    func,
    kwargs,
):
    ec2_client = boto3.client("ec2", "us-east-1")
    kwargs["ec2_client"] = ec2_client

    vpc_id = sg_id = subnet_id = tg_id = cg_id = None
    if create_vpc:
        vpc = ec2_client.create_vpc(
            CidrBlock="10.0.0.0/16",
            TagSpecifications=[
                {"ResourceType": "vpc", "Tags": [{"Key": "project", "Value": "test"}]}
            ],
        )
        vpc_id = vpc["Vpc"]["VpcId"]
        kwargs["vpc_id"] = vpc_id

        if create_subnet:
            subnet_id = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/24")[
                "Subnet"
            ]["SubnetId"]
            kwargs["subnet_id"] = subnet_id

    if create_sg:
        sg_name = f"test_{str(uuid4())[0:6]}"
        sg = ec2_client.create_security_group(
            Description="test", GroupName=sg_name, VpcId=vpc_id
        )
        sg_id = sg["GroupId"]
        kwargs["sg_id"] = sg_id

    if create_transit_gateway:
        gateway = ec2_client.create_transit_gateway(Description="test")
        tg_id = gateway["TransitGateway"]["TransitGatewayId"]
        wait_for_transit_gateway(ec2_client, tg_id=tg_id)
        kwargs["tg_id"] = tg_id

    if create_customer_gateway:
        customer_gateway = ec2_client.create_customer_gateway(
            Type="ipsec.1", PublicIp="205.251.242.54", BgpAsn=65534
        )
        cg_id = customer_gateway["CustomerGateway"]["CustomerGatewayId"]
        kwargs["cg_id"] = cg_id

    try:
        func(**kwargs)
    finally:
        if cg_id:
            ec2_client.delete_customer_gateway(CustomerGatewayId=cg_id)
        if tg_id:
            delete_transit_gateway_dependencies(ec2_client, tg_id=tg_id)
            ec2_client.delete_transit_gateway(TransitGatewayId=tg_id)
        if subnet_id:
            ec2_client.delete_subnet(SubnetId=subnet_id)
        if sg_id:
            ec2_client.delete_security_group(GroupId=sg_id)
        if vpc_id:
            ec2_client.delete_vpc(VpcId=vpc_id)


def wait_for_transit_gateway(ec2_client, tg_id):
    for idx in range(10):
        gateway = ec2_client.describe_transit_gateways(TransitGatewayIds=[tg_id])[
            "TransitGateways"
        ][0]

        if gateway["State"] == "available":
            return

        sleep(10 * idx)


def wait_for_transit_gateway_route_table(ec2_client, tg_rt_id):
    for idx in range(10):
        route_table = ec2_client.describe_transit_gateway_route_tables(
            TransitGatewayRouteTableIds=[tg_rt_id]
        )["TransitGatewayRouteTables"][0]

        if route_table["State"] == "available":
            return

        sleep(5 * idx)


def wait_for_transit_gateway_attachments(ec2_client, tg_attachment_id):
    for idx in range(10):
        attachment = ec2_client.describe_transit_gateway_vpc_attachments(
            TransitGatewayAttachmentIds=[tg_attachment_id]
        )["TransitGatewayVpcAttachments"][0]

        if attachment["State"] == "available":
            return

        sleep(5 * idx)


def wait_for_transit_gateway_association(
    ec2_client, tg_rt_id, tg_attachment_id, expected_state
):
    for idx in range(10):
        associations = ec2_client.get_transit_gateway_route_table_associations(
            TransitGatewayRouteTableId=tg_rt_id,
            Filters=[
                {"Name": "transit-gateway-attachment-id", "Values": [tg_attachment_id]}
            ],
        )["Associations"]

        if not associations or associations[0]["State"] == expected_state:
            # If we're disassociating, AWS will never return anything after it has finished
            # Initial calls will return State=disassociating - after it has successfully disassociated, it is no longer returned
            return

        sleep(5 * idx)


def wait_for_vpn_connections(ec2_client, vpn_connection_id):
    for idx in range(10):
        connections = ec2_client.describe_vpn_connections(
            VpnConnectionIds=[vpn_connection_id]
        )["VpnConnections"]
        if not connections or connections[0]["State"] == "available":
            return
        sleep(5 * idx)


def wait_for_ipv6_cidr_block_associations(ec2_client, vpc_id):
    for idx in range(10):
        vpcs = ec2_client.describe_vpcs(VpcIds=[vpc_id])["Vpcs"]
        if (
            vpcs[0]["Ipv6CidrBlockAssociationSet"][0]["Ipv6CidrBlockState"]["State"]
            == "associated"
        ):
            return vpcs[0]["Ipv6CidrBlockAssociationSet"][0]
        sleep(5 * idx)


def delete_transit_gateway_dependencies(ec2_client, tg_id):
    delete_tg_attachments(ec2_client, tg_id)

    for idx in range(10):
        route_tables = ec2_client.describe_transit_gateway_route_tables(
            Filters=[
                {"Name": "transit-gateway-id", "Values": [tg_id]},
                {"Name": "default-association-route-table", "Values": ["false"]},
            ]
        )["TransitGatewayRouteTables"]

        if not route_tables:
            return

        for table in route_tables:
            if table["State"] == "available":
                ec2_client.delete_transit_gateway_route_table(
                    TransitGatewayRouteTableId=table["TransitGatewayRouteTableId"]
                )

        if set(rt["State"] for rt in route_tables) == {"deleted"}:
            return

        sleep(5 * idx)


def delete_tg_attachments(ec2_client, tg_id):
    for idx in range(10):
        attachments = ec2_client.describe_transit_gateway_attachments(
            Filters=[{"Name": "transit-gateway-id", "Values": [tg_id]}]
        )["TransitGatewayAttachments"]

        if not attachments:
            return

        for attachment in attachments:
            if attachment["State"] == "available":
                ec2_client.delete_transit_gateway_vpc_attachment(
                    TransitGatewayAttachmentId=attachment["TransitGatewayAttachmentId"]
                )

        if set(a["State"] for a in attachments) == {"deleted"}:
            return

        sleep(5 * idx)
