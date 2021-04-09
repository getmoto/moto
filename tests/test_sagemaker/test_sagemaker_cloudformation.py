import json
import boto3

import pytest
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_cloudformation, mock_sagemaker
from moto.sts.models import ACCOUNT_ID


def _get_notebook_instance_template_string(
    instance_type="ml.c4.xlarge",
    role_arn="arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID),
    include_outputs=True,
):
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "TestNotebookInstance": {
                "Type": "AWS::SageMaker::NotebookInstance",
                "Properties": {"InstanceType": instance_type, "RoleArn": role_arn},
            },
        },
    }
    if include_outputs:
        template["Outputs"] = {
            "NotebookInstanceArn": {"Value": {"Ref": "TestNotebookInstance"}},
            "NotebookInstanceName": {
                "Value": {
                    "Fn::GetAtt": ["TestNotebookInstance", "NotebookInstanceName"]
                },
            },
        }
    return json.dumps(template)


@mock_cloudformation
def test_sagemaker_cloudformation_create_notebook_instance():
    cf = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "test_sagemaker_notebook_instance"
    template = _get_notebook_instance_template_string(include_outputs=False)
    cf.create_stack(StackName=stack_name, TemplateBody=template)

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
    template = _get_notebook_instance_template_string()
    cf.create_stack(StackName=stack_name, TemplateBody=template)

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


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_notebook_instance_delete():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Create stack with notebook instance and verify existence
    stack_name = "test_sagemaker_notebook_instance"
    template = _get_notebook_instance_template_string()
    cf.create_stack(StackName=stack_name, TemplateBody=template)

    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    notebook_instance = sm.describe_notebook_instance(
        NotebookInstanceName=outputs["NotebookInstanceName"],
    )
    outputs["NotebookInstanceArn"].should.equal(
        notebook_instance["NotebookInstanceArn"]
    )

    # Delete the stack and verify notebook instance has also been deleted
    # TODO replace exception check with `list_notebook_instances` method when implemented
    cf.delete_stack(StackName=stack_name)
    with pytest.raises(ClientError) as ce:
        sm.describe_notebook_instance(
            NotebookInstanceName=outputs["NotebookInstanceName"]
        )
    ce.value.response["Error"]["Message"].should.contain("RecordNotFound")


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_notebook_instance_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Set up template for stack with initial and update instance types
    stack_name = "test_sagemaker_notebook_instance"
    initial_instance_type = "ml.c4.xlarge"
    updated_instance_type = "ml.c4.4xlarge"
    initial_template_json = _get_notebook_instance_template_string(
        instance_type=initial_instance_type
    )
    updated_template_json = _get_notebook_instance_template_string(
        instance_type=updated_instance_type
    )

    # Create stack with initial template and check attributes
    cf.create_stack(StackName=stack_name, TemplateBody=initial_template_json)
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    initial_notebook_name = outputs["NotebookInstanceName"]
    notebook_instance_description = sm.describe_notebook_instance(
        NotebookInstanceName=initial_notebook_name,
    )
    initial_instance_type.should.equal(notebook_instance_description["InstanceType"])

    # Update stack with new instance type and check attributes
    cf.update_stack(StackName=stack_name, TemplateBody=updated_template_json)
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    updated_notebook_name = outputs["NotebookInstanceName"]
    updated_notebook_name.should.equal(initial_notebook_name)

    notebook_instance_description = sm.describe_notebook_instance(
        NotebookInstanceName=updated_notebook_name,
    )
    updated_instance_type.should.equal(notebook_instance_description["InstanceType"])
