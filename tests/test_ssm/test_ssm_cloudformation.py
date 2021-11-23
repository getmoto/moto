import boto3
import json


from moto import mock_ssm, mock_cloudformation
from tests import EXAMPLE_AMI_ID


@mock_ssm
@mock_cloudformation
def test_get_command_invocations_from_stack():
    stack_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Test Stack",
        "Resources": {
            "EC2Instance1": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": EXAMPLE_AMI_ID,
                    "KeyName": "test",
                    "InstanceType": "t2.micro",
                    "Tags": [
                        {"Key": "Test Description", "Value": "Test tag"},
                        {"Key": "Test Name", "Value": "Name tag for tests"},
                    ],
                },
            }
        },
        "Outputs": {
            "test": {
                "Description": "Test Output",
                "Value": "Test output value",
                "Export": {"Name": "Test value to export"},
            },
            "PublicIP": {"Value": "Test public ip"},
        },
    }

    cloudformation_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_template_str = json.dumps(stack_template)

    cloudformation_client.create_stack(
        StackName="test_stack",
        TemplateBody=stack_template_str,
        Capabilities=("CAPABILITY_IAM",),
    )

    client = boto3.client("ssm", region_name="us-east-1")

    ssm_document = "AWS-RunShellScript"
    params = {"commands": ["#!/bin/bash\necho 'hello world'"]}

    response = client.send_command(
        Targets=[
            {"Key": "tag:aws:cloudformation:stack-name", "Values": ("test_stack",)}
        ],
        DocumentName=ssm_document,
        Parameters=params,
        OutputS3Region="us-east-2",
        OutputS3BucketName="the-bucket",
        OutputS3KeyPrefix="pref",
    )

    cmd = response["Command"]
    cmd_id = cmd["CommandId"]
    instance_ids = cmd["InstanceIds"]

    client.get_command_invocation(
        CommandId=cmd_id, InstanceId=instance_ids[0], PluginName="aws:runShellScript"
    )
