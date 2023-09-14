import boto3
import json

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
    assert len(gateways) == 1
    assert gateways[0]["TransitGatewayId"].startswith("tgw-")
    assert gateways[0]["State"] == "available"
    assert gateways[0]["Description"] == "My CF Gateway"
    assert gateways[0]["Options"]["AmazonSideAsn"] == 64512
    assert gateways[0]["Options"]["AutoAcceptSharedAttachments"] == "disable"
    assert gateways[0]["Options"]["DefaultRouteTableAssociation"] == "enable"
    # Gateway will only have the OOTB CF tags
    assert len(gateways[0]["Tags"]) == 3


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
    assert len(gateways) == 1
    assert gateways[0]["TransitGatewayId"].startswith("tgw-")
    assert gateways[0]["State"] == "available"
    assert gateways[0]["Description"] == "My CF Gateway"
    assert gateways[0]["Options"]["AmazonSideAsn"] == 1
    assert gateways[0]["Options"]["AutoAcceptSharedAttachments"] == "enable"
    assert gateways[0]["Options"]["DefaultRouteTableAssociation"] == "disable"
    tags = gateways[0].get("Tags", {})
    assert len(tags) == 4
    assert {"Key": "foo", "Value": "bar"} in tags
    assert {"Key": "aws:cloudformation:stack-name", "Value": stack_name} in tags
    assert {"Key": "aws:cloudformation:logical-id", "Value": "ttg"} in tags
