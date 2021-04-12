import json
import boto3

import pytest
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_cloudformation, mock_sagemaker
from moto.sts.models import ACCOUNT_ID


def _get_notebook_instance_template_string(
    resource_name="TestNotebook",
    instance_type="ml.c4.xlarge",
    role_arn="arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID),
    include_outputs=True,
):
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            resource_name: {
                "Type": "AWS::SageMaker::NotebookInstance",
                "Properties": {"InstanceType": instance_type, "RoleArn": role_arn},
            },
        },
    }
    if include_outputs:
        template["Outputs"] = {
            "Arn": {"Value": {"Ref": resource_name}},
            "Name": {"Value": {"Fn::GetAtt": [resource_name, "NotebookInstanceName"]}},
        }
    return json.dumps(template)


def _get_notebook_instance_lifecycle_config_template_string(
    resource_name="TestConfig", on_create=None, on_start=None, include_outputs=True,
):
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            resource_name: {
                "Type": "AWS::SageMaker::NotebookInstanceLifecycleConfig",
                "Properties": {},
            },
        },
    }
    if on_create is not None:
        template["Resources"][resource_name]["Properties"]["OnCreate"] = [
            {"Content": on_create}
        ]
    if on_start is not None:
        template["Resources"][resource_name]["Properties"]["OnStart"] = [
            {"Content": on_start}
        ]
    if include_outputs:
        template["Outputs"] = {
            "Arn": {"Value": {"Ref": resource_name}},
            "Name": {
                "Value": {
                    "Fn::GetAtt": [
                        resource_name,
                        "NotebookInstanceLifecycleConfigName",
                    ]
                }
            },
        }
    return json.dumps(template)


@mock_cloudformation
@pytest.mark.parametrize(
    "stack_name,resource_name,template",
    [
        (
            "test_sagemaker_notebook_instance",
            "TestNotebookInstance",
            _get_notebook_instance_template_string(
                resource_name="TestNotebookInstance", include_outputs=False
            ),
        ),
        (
            "test_sagemaker_notebook_instance_lifecycle_config",
            "TestNotebookInstanceLifecycleConfig",
            _get_notebook_instance_lifecycle_config_template_string(
                resource_name="TestNotebookInstanceLifecycleConfig",
                include_outputs=False,
            ),
        ),
    ],
)
def test_sagemaker_cloudformation_create(stack_name, resource_name, template):
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    provisioned_resource["LogicalResourceId"].should.equal(resource_name)
    len(provisioned_resource["PhysicalResourceId"]).should.be.greater_than(0)


@mock_cloudformation
@mock_sagemaker
@pytest.mark.parametrize(
    "stack_name,template,describe_function_name,name_parameter,arn_parameter",
    [
        (
            "test_sagemaker_notebook_instance",
            _get_notebook_instance_template_string(),
            "describe_notebook_instance",
            "NotebookInstanceName",
            "NotebookInstanceArn",
        ),
        (
            "test_sagemaker_notebook_instance_lifecycle_config",
            _get_notebook_instance_lifecycle_config_template_string(),
            "describe_notebook_instance_lifecycle_config",
            "NotebookInstanceLifecycleConfigName",
            "NotebookInstanceLifecycleConfigArn",
        ),
    ],
)
def test_sagemaker_cloudformation_get_attr(
    stack_name, template, describe_function_name, name_parameter, arn_parameter
):
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Create stack and get description for output values
    cf.create_stack(StackName=stack_name, TemplateBody=template)
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }

    # Using the describe function, ensure output ARN matches resource ARN
    resource_description = getattr(sm, describe_function_name)(
        **{name_parameter: outputs["Name"]}
    )
    outputs["Arn"].should.equal(resource_description[arn_parameter])


@mock_cloudformation
@mock_sagemaker
@pytest.mark.parametrize(
    "stack_name,template,describe_function_name,name_parameter,arn_parameter,error_message",
    [
        (
            "test_sagemaker_notebook_instance",
            _get_notebook_instance_template_string(),
            "describe_notebook_instance",
            "NotebookInstanceName",
            "NotebookInstanceArn",
            "RecordNotFound",
        ),
        (
            "test_sagemaker_notebook_instance_lifecycle_config",
            _get_notebook_instance_lifecycle_config_template_string(),
            "describe_notebook_instance_lifecycle_config",
            "NotebookInstanceLifecycleConfigName",
            "NotebookInstanceLifecycleConfigArn",
            "Notebook Instance Lifecycle Config does not exist",
        ),
    ],
)
def test_sagemaker_cloudformation_notebook_instance_delete(
    stack_name,
    template,
    describe_function_name,
    name_parameter,
    arn_parameter,
    error_message,
):
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Create stack and verify existence
    cf.create_stack(StackName=stack_name, TemplateBody=template)
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    resource_description = getattr(sm, describe_function_name)(
        **{name_parameter: outputs["Name"]}
    )
    outputs["Arn"].should.equal(resource_description[arn_parameter])

    # Delete the stack and verify resource has also been deleted
    cf.delete_stack(StackName=stack_name)
    with pytest.raises(ClientError) as ce:
        getattr(sm, describe_function_name)(**{name_parameter: outputs["Name"]})
    ce.value.response["Error"]["Message"].should.contain(error_message)


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
    initial_notebook_name = outputs["Name"]
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
    updated_notebook_name = outputs["Name"]
    updated_notebook_name.should.equal(initial_notebook_name)

    notebook_instance_description = sm.describe_notebook_instance(
        NotebookInstanceName=updated_notebook_name,
    )
    updated_instance_type.should.equal(notebook_instance_description["InstanceType"])


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_notebook_instance_lifecycle_config_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Set up template for stack with initial and update instance types
    stack_name = "test_sagemaker_notebook_instance_lifecycle_config"
    initial_on_create_script = "echo Hello World"
    updated_on_create_script = "echo Goodbye World"
    initial_template_json = _get_notebook_instance_lifecycle_config_template_string(
        on_create=initial_on_create_script
    )
    updated_template_json = _get_notebook_instance_lifecycle_config_template_string(
        on_create=updated_on_create_script
    )

    # Create stack with initial template and check attributes
    cf.create_stack(StackName=stack_name, TemplateBody=initial_template_json)
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    initial_config_name = outputs["Name"]
    notebook_lifecycle_config_description = sm.describe_notebook_instance_lifecycle_config(
        NotebookInstanceLifecycleConfigName=initial_config_name,
    )
    len(notebook_lifecycle_config_description["OnCreate"]).should.equal(1)
    initial_on_create_script.should.equal(
        notebook_lifecycle_config_description["OnCreate"][0]["Content"]
    )

    # Update stack with new instance type and check attributes
    cf.update_stack(StackName=stack_name, TemplateBody=updated_template_json)
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    updated_config_name = outputs["Name"]
    updated_config_name.should.equal(initial_config_name)

    notebook_lifecycle_config_description = sm.describe_notebook_instance_lifecycle_config(
        NotebookInstanceLifecycleConfigName=updated_config_name,
    )
    len(notebook_lifecycle_config_description["OnCreate"]).should.equal(1)
    updated_on_create_script.should.equal(
        notebook_lifecycle_config_description["OnCreate"][0]["Content"]
    )
