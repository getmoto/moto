import json
import boto3

import sure  # noqa

from moto import mock_cloudformation, mock_sagemaker
from moto.sts.models import ACCOUNT_ID


FAKE_ROLE_ARN = "arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID)


@mock_cloudformation
def test_sagemaker_cloudformation_create_notebook_instance():
    cf = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "test_sagemaker_notebook_instance"

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "TestNotebookInstance": {
                "Type": "AWS::SageMaker::NotebookInstance",
                "Properties": {
                    "InstanceType": "ml.c4.xlarge",
                    "RoleArn": FAKE_ROLE_ARN,
                },
            },
        },
    }
    cf.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    provisioned_resource = cf.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    provisioned_resource["LogicalResourceId"].should.equal("TestNotebookInstance")
    len(provisioned_resource["PhysicalResourceId"]).should.be.greater_than(0)


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_notebook_instance_get_attr():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    stack_name = "test_sagemaker_notebook_instance"

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "TestNotebookInstance": {
                "Type": "AWS::SageMaker::NotebookInstance",
                "Properties": {
                    "InstanceType": "ml.c4.xlarge",
                    "RoleArn": FAKE_ROLE_ARN,
                },
            },
        },
        "Outputs": {
            "NotebookInstanceArn": {"Value": {"Ref": "TestNotebookInstance"}},
            "NotebookInstanceName": {
                "Value": {
                    "Fn::GetAtt": ["TestNotebookInstance", "NotebookInstanceName"]
                },
            },
        },
    }
    cf.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    notebook_instance_name = outputs["NotebookInstanceName"]
    notebook_instance_arn = outputs["NotebookInstanceArn"]

    notebook_instance_description = sm.describe_notebook_instance(
        NotebookInstanceName=notebook_instance_name,
    )
    notebook_instance_arn.should.equal(
        notebook_instance_description["NotebookInstanceArn"]
    )
