import json
import boto3

import sure  # noqa

from moto import mock_cloudformation
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
