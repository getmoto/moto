import boto3

import json
import sure  # noqa # pylint: disable=unused-import

from moto import mock_cloudformation, mock_ec2
from uuid import uuid4


@mock_cloudformation
@mock_ec2
def test_transit_gateway_by_cloudformation_simple():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", "us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Template for Transit Gateway creation.",
        "Resources": {
            "ttg": {
                "Type": "AWS::EC2::TransitGateway",
                "Properties": {"Description": "My CF Gateway"},
            }
        },
    }
    template = json.dumps(template)
    stack_name = str(uuid4())
    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]
    gateway_id = resources[0]["PhysicalResourceId"]

    gateways = ec2.describe_transit_gateways(TransitGatewayIds=[gateway_id])[
        "TransitGateways"
    ]
    gateways.should.have.length_of(1)
    gateways[0]["TransitGatewayId"].should.match("tgw-[0-9a-z]+")
    gateways[0]["State"].should.equal("available")
    gateways[0]["Description"].should.equal("My CF Gateway")
    gateways[0]["Options"]["AmazonSideAsn"].should.equal(64512)
    gateways[0]["Options"]["AutoAcceptSharedAttachments"].should.equal("disable")
    gateways[0]["Options"]["DefaultRouteTableAssociation"].should.equal("enable")
    # Gateway will only have the OOTB CF tags
    gateways[0]["Tags"].should.have.length_of(3)


@mock_cloudformation
@mock_ec2
def test_transit_gateway_by_cloudformation():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", "us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Template for Transit Gateway creation.",
        "Resources": {
            "ttg": {
                "Type": "AWS::EC2::TransitGateway",
                "Properties": {
                    "Description": "My CF Gateway",
                    "AmazonSideAsn": 1,
                    "AutoAcceptSharedAttachments": "enable",
                    "DefaultRouteTableAssociation": "disable",
                    "Tags": [{"Key": "foo", "Value": "bar"}],
                },
            }
        },
    }
    template = json.dumps(template)
    stack_name = str(uuid4())
    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]
    gateway_id = resources[0]["PhysicalResourceId"]

    gateways = ec2.describe_transit_gateways(TransitGatewayIds=[gateway_id])[
        "TransitGateways"
    ]
    gateways.should.have.length_of(1)
    gateways[0]["TransitGatewayId"].should.match("tgw-[0-9a-z]+")
    gateways[0]["State"].should.equal("available")
    gateways[0]["Description"].should.equal("My CF Gateway")
    gateways[0]["Options"]["AmazonSideAsn"].should.equal(1)
    gateways[0]["Options"]["AutoAcceptSharedAttachments"].should.equal("enable")
    gateways[0]["Options"]["DefaultRouteTableAssociation"].should.equal("disable")
    tags = gateways[0].get("Tags", {})
    tags.should.have.length_of(4)
    tags.should.contain({"Key": "foo", "Value": "bar"})
    tags.should.contain({"Key": "aws:cloudformation:stack-name", "Value": stack_name})
    tags.should.contain({"Key": "aws:cloudformation:logical-id", "Value": "ttg"})
