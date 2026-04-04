import json
from uuid import uuid4

import boto3

from moto import mock_aws
from tests import EXAMPLE_AMI_ID


@mock_aws
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


@mock_aws
def test_ssm_documents():
    # SETUP
    doc_name = str(uuid4())
    stack_name = f"Stack{str(uuid4())[0:6]}"
    ssm_template_json = json.dumps(get_ssm_document_template(doc_name))

    # CREATE
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(StackName=stack_name, TemplateBody=ssm_template_json)

    # VERIFY
    ssm = boto3.client("ssm", region_name="us-east-1")
    document = ssm.describe_document(Name=doc_name)["Document"]

    assert document["Description"] == "Sample Yaml"
    assert document["Name"] == doc_name
    assert document["Parameters"] == [
        {
            "DefaultValue": "3",
            "Description": "Command Duration.",
            "Name": "Parameter1",
            "Type": "Integer",
        }
    ]

    # DELETE
    cf.delete_stack(StackName=stack_name)

    # VERIFY
    assert not ssm.list_documents()["DocumentIdentifiers"]


def _get_document_content():
    return {
        "schemaVersion": "2.2",
        "description": "Sample Yaml",
        "parameters": {
            "Parameter1": {
                "type": "Integer",
                "default": 3,
                "description": "Command Duration.",
                "allowedValues": [1, 2, 3, 4],
            }
        },
        "mainSteps": [
            {
                "action": "aws:runShellScript",
                "name": "sampleCommand",
                "inputs": {"runCommand": ["echo hi"]},
            }
        ],
    }


def get_ssm_document_template(document_name: str):
    attachment1 = {"Key": "attachment1_key", "Name": "My First", "Values": ["value1"]}
    attachment2 = {"Key": "attachment2_key", "Name": "My Second", "Values": ["value2"]}
    doc_requires1 = {"Name": "doc1", "Version": "doc1version"}
    doc_requires2 = {"Name": "doc2", "Version": "doc2version"}
    tag1 = {"Key": "key1", "Value": "value1"}
    tag2 = {"Key": "tag2", "Value": "value2"}
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "ImportantDocument": {
                "Type": "AWS::SSM::Document",
                "Properties": {
                    "Attachments": [attachment1, attachment2],
                    "Content": json.dumps(_get_document_content()),
                    "DocumentFormat": "JSON",
                    "DocumentType": "Policy",
                    "Name": document_name,
                    "Requires": [doc_requires1, doc_requires2],
                    "Tags": [tag1, tag2],
                    "TargetType": "TargetType",
                    "UpdateMethod": "UpdateMethod",
                    "VersionName": "VersionName",
                },
            }
        },
    }
