from __future__ import unicode_literals

import boto3

import json
import sure  # noqa

from moto import (
    mock_cloudformation,
    mock_ec2,
    mock_s3,
)
from tests import EXAMPLE_AMI_ID


@mock_cloudformation
@mock_ec2
@mock_s3
def test_flow_logs_by_cloudformation():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    cf_client = boto3.client("cloudformation", "us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
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
    stack_id = cf_client.create_stack(
        StackName="test_stack", TemplateBody=flow_log_template_json
    )["StackId"]

    flow_logs = client.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(1)
    flow_logs[0]["ResourceId"].should.equal(vpc["VpcId"])
    flow_logs[0]["LogDestination"].should.equal("arn:aws:s3:::" + bucket.name)
    flow_logs[0]["MaxAggregationInterval"].should.equal(60)


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
    cf_conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(dummy_template_json)
    )
    associations = client.describe_iam_instance_profile_associations()
    associations["IamInstanceProfileAssociations"].should.have.length_of(1)
    associations["IamInstanceProfileAssociations"][0]["IamInstanceProfile"][
        "Arn"
    ].should.contain("test_stack")

    cf_conn.delete_stack(StackName="test_stack")
    associations = client.describe_iam_instance_profile_associations()
    associations["IamInstanceProfileAssociations"].should.have.length_of(0)
