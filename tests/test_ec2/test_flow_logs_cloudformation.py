import boto3

import json

from moto import mock_cloudformation, mock_ec2, mock_s3
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


@mock_cloudformation
@mock_ec2
@mock_s3
def test_flow_logs_by_cloudformation():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    cf_client = boto3.client("cloudformation", "us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket_name = str(uuid4())
    bucket = s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )

    flow_log_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Template for VPC Flow Logs creation.",
        "Resources": {
            "TestFlowLogs": {
                "Type": "AWS::EC2::FlowLog",
                "Properties": {
                    "ResourceType": "VPC",
                    "ResourceId": vpc["VpcId"],
                    "TrafficType": "ALL",
                    "LogDestinationType": "s3",
                    "LogDestination": "arn:aws:s3:::" + bucket.name,
                    "MaxAggregationInterval": "60",
                    "Tags": [{"Key": "foo", "Value": "bar"}],
                },
            }
        },
    }
    flow_log_template_json = json.dumps(flow_log_template)

    stack_name = str(uuid4())
    cf_client.create_stack(StackName=stack_name, TemplateBody=flow_log_template_json)

    flow_logs = client.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [vpc["VpcId"]]}]
    )["FlowLogs"]
    assert len(flow_logs) == 1
    assert flow_logs[0]["ResourceId"] == vpc["VpcId"]
    assert flow_logs[0]["LogDestination"] == "arn:aws:s3:::" + bucket.name
    assert flow_logs[0]["MaxAggregationInterval"] == 60


@mock_ec2
@mock_cloudformation
def test_cloudformation():
    dummy_template_json = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "InstanceProfile": {
                "Type": "AWS::IAM::InstanceProfile",
                "Properties": {"Path": "/", "Roles": []},
            },
            "Ec2Instance": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "IamInstanceProfile": {"Ref": "InstanceProfile"},
                    "KeyName": "mykey1",
                    "ImageId": EXAMPLE_AMI_ID,
                },
            },
        },
    }

    client = boto3.client("ec2", region_name="us-east-1")
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = str(uuid4())
    cf_conn.create_stack(
        StackName=stack_name, TemplateBody=json.dumps(dummy_template_json)
    )

    resources = cf_conn.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]
    iam_id = resources[0]["PhysicalResourceId"]
    iam_ip_arn = f"arn:aws:iam::{ACCOUNT_ID}:instance-profile/{iam_id}"

    all_assocs = client.describe_iam_instance_profile_associations()[
        "IamInstanceProfileAssociations"
    ]
    our_assoc = [a for a in all_assocs if a["IamInstanceProfile"]["Arn"] == iam_ip_arn]
    assert stack_name in our_assoc[0]["IamInstanceProfile"]["Arn"]
    our_assoc_id = our_assoc[0]["AssociationId"]

    cf_conn.delete_stack(StackName=stack_name)
    associations = client.describe_iam_instance_profile_associations()[
        "IamInstanceProfileAssociations"
    ]
    assert our_assoc_id not in [a["AssociationId"] for a in associations]
