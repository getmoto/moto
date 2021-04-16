import boto3

import pytest
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_cloudformation, mock_sagemaker

from .cloudformation_test_configs import (
    NotebookInstanceTestConfig,
    NotebookInstanceLifecycleConfigTestConfig,
    ModelTestConfig,
)


@mock_cloudformation
@pytest.mark.parametrize(
    "test_config",
    [
        NotebookInstanceTestConfig(),
        NotebookInstanceLifecycleConfigTestConfig(),
        ModelTestConfig(),
    ],
)
def test_sagemaker_cloudformation_create(test_config):
    cf = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "{}_stack".format(test_config.resource_name)
    cf.create_stack(
        StackName=stack_name,
        TemplateBody=test_config.get_cloudformation_template(include_outputs=False),
    )

    provisioned_resource = cf.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    provisioned_resource["LogicalResourceId"].should.equal(test_config.resource_name)
    len(provisioned_resource["PhysicalResourceId"]).should.be.greater_than(0)


@mock_cloudformation
@mock_sagemaker
@pytest.mark.parametrize(
    "test_config",
    [
        NotebookInstanceTestConfig(),
        NotebookInstanceLifecycleConfigTestConfig(),
        ModelTestConfig(),
    ],
)
def test_sagemaker_cloudformation_get_attr(test_config):
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Create stack and get description for output values
    stack_name = "{}_stack".format(test_config.resource_name)
    cf.create_stack(
        StackName=stack_name, TemplateBody=test_config.get_cloudformation_template()
    )
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }

    # Using the describe function, ensure output ARN matches resource ARN
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: outputs["Name"]}
    )
    outputs["Arn"].should.equal(resource_description[test_config.arn_parameter])


@mock_cloudformation
@mock_sagemaker
@pytest.mark.parametrize(
    "test_config,error_message",
    [
        (NotebookInstanceTestConfig(), "RecordNotFound"),
        (
            NotebookInstanceLifecycleConfigTestConfig(),
            "Notebook Instance Lifecycle Config does not exist",
        ),
        (ModelTestConfig(), "Could not find model"),
    ],
)
def test_sagemaker_cloudformation_notebook_instance_delete(test_config, error_message):
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Create stack and verify existence
    stack_name = "{}_stack".format(test_config.resource_name)
    cf.create_stack(
        StackName=stack_name, TemplateBody=test_config.get_cloudformation_template()
    )
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: outputs["Name"]}
    )
    outputs["Arn"].should.equal(resource_description[test_config.arn_parameter])

    # Delete the stack and verify resource has also been deleted
    cf.delete_stack(StackName=stack_name)
    with pytest.raises(ClientError) as ce:
        getattr(sm, test_config.describe_function_name)(
            **{test_config.name_parameter: outputs["Name"]}
        )
    ce.value.response["Error"]["Message"].should.contain(error_message)


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_notebook_instance_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    test_config = NotebookInstanceTestConfig()

    # Set up template for stack with initial and update instance types
    stack_name = "{}_stack".format(test_config.resource_name)
    initial_instance_type = "ml.c4.xlarge"
    updated_instance_type = "ml.c4.4xlarge"
    initial_template_json = test_config.get_cloudformation_template(
        instance_type=initial_instance_type
    )
    updated_template_json = test_config.get_cloudformation_template(
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
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: initial_notebook_name}
    )
    initial_instance_type.should.equal(resource_description["InstanceType"])

    # Update stack with new instance type and check attributes
    cf.update_stack(StackName=stack_name, TemplateBody=updated_template_json)
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    updated_notebook_name = outputs["Name"]
    updated_notebook_name.should.equal(initial_notebook_name)

    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: updated_notebook_name}
    )
    updated_instance_type.should.equal(resource_description["InstanceType"])


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_notebook_instance_lifecycle_config_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    test_config = NotebookInstanceLifecycleConfigTestConfig()

    # Set up template for stack with initial and update instance types
    stack_name = "{}_stack".format(test_config.resource_name)
    initial_on_create_script = "echo Hello World"
    updated_on_create_script = "echo Goodbye World"
    initial_template_json = test_config.get_cloudformation_template(
        on_create=initial_on_create_script
    )
    updated_template_json = test_config.get_cloudformation_template(
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
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: initial_config_name}
    )
    len(resource_description["OnCreate"]).should.equal(1)
    initial_on_create_script.should.equal(
        resource_description["OnCreate"][0]["Content"]
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

    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: updated_config_name}
    )
    len(resource_description["OnCreate"]).should.equal(1)
    updated_on_create_script.should.equal(
        resource_description["OnCreate"][0]["Content"]
    )


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_model_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    test_config = ModelTestConfig()

    # Set up template for stack with initial and update instance types
    stack_name = "{}_stack".format(test_config.resource_name)
    image = "404615174143.dkr.ecr.us-east-2.amazonaws.com/kmeans:{}"
    initial_image_version = 1
    updated_image_version = 2
    initial_template_json = test_config.get_cloudformation_template(
        image=image.format(initial_image_version)
    )
    updated_template_json = test_config.get_cloudformation_template(
        image=image.format(updated_image_version)
    )

    # Create stack with initial template and check attributes
    cf.create_stack(StackName=stack_name, TemplateBody=initial_template_json)
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    inital_model_name = outputs["Name"]
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: inital_model_name}
    )
    resource_description["PrimaryContainer"]["Image"].should.equal(
        image.format(initial_image_version)
    )

    # Update stack with new instance type and check attributes
    cf.update_stack(StackName=stack_name, TemplateBody=updated_template_json)
    stack_description = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
    updated_notebook_name = outputs["Name"]
    updated_notebook_name.should_not.equal(inital_model_name)

    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: updated_notebook_name}
    )
    resource_description["PrimaryContainer"]["Image"].should.equal(
        image.format(updated_image_version)
    )
