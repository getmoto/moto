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
    func,
    kwargs,
):
    ec2_client = boto3.client("ec2", "us-east-1")
    kwargs["ec2_client"] = ec2_client

    vpc_id = sg_id = subnet_id = tg_id = None
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

    try:
        func(**kwargs)
    finally:
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

        sleep(5 * idx)


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


def delete_transit_gateway_dependencies(ec2_client, tg_id):
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

    for idx in range(10):
        route_tables = ec2_client.describe_transit_gateway_route_tables(
            Filters=[{"Name": "transit-gateway-id", "Values": [tg_id]}]
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
