import re

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_cloudformation, mock_sagemaker
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from .cloudformation_test_configs import (
    NotebookInstanceTestConfig,
    NotebookInstanceLifecycleConfigTestConfig,
    ModelTestConfig,
    EndpointConfigTestConfig,
    EndpointTestConfig,
)


def _get_stack_outputs(cf_client, stack_name):
    """Returns the outputs for the first entry in describe_stacks."""
    stack_description = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    return {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }


@mock_cloudformation
@mock_sagemaker
@pytest.mark.parametrize(
    "test_config",
    [
        NotebookInstanceTestConfig(),
        NotebookInstanceLifecycleConfigTestConfig(),
        ModelTestConfig(),
        EndpointConfigTestConfig(),
        EndpointTestConfig(),
    ],
)
def test_sagemaker_cloudformation_create(test_config):
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Utilize test configuration to set-up any mock SageMaker resources
    test_config.run_setup_procedure(sm)

    stack_name = f"{test_config.resource_name}_stack"
    cf.create_stack(
        StackName=stack_name,
        TemplateBody=test_config.get_cloudformation_template(include_outputs=False),
    )

    provisioned_resource = cf.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    assert provisioned_resource["LogicalResourceId"] == test_config.resource_name
    assert len(provisioned_resource["PhysicalResourceId"]) > 0


@mock_cloudformation
@mock_sagemaker
@pytest.mark.parametrize(
    "test_config",
    [
        NotebookInstanceTestConfig(),
        NotebookInstanceLifecycleConfigTestConfig(),
        ModelTestConfig(),
        EndpointConfigTestConfig(),
        EndpointTestConfig(),
    ],
)
def test_sagemaker_cloudformation_get_attr(test_config):
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Utilize test configuration to set-up any mock SageMaker resources
    test_config.run_setup_procedure(sm)

    # Create stack and get description for output values
    stack_name = f"{test_config.resource_name}_stack"
    cf.create_stack(
        StackName=stack_name, TemplateBody=test_config.get_cloudformation_template()
    )
    outputs = _get_stack_outputs(cf, stack_name)

    # Using the describe function, ensure output ARN matches resource ARN
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: outputs["Name"]}
    )
    assert outputs["Arn"] == resource_description[test_config.arn_parameter]


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
        (EndpointConfigTestConfig(), "Could not find endpoint configuration"),
        (EndpointTestConfig(), "Could not find endpoint"),
    ],
)
def test_sagemaker_cloudformation_notebook_instance_delete(test_config, error_message):
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    # Utilize test configuration to set-up any mock SageMaker resources
    test_config.run_setup_procedure(sm)

    # Create stack and verify existence
    stack_name = f"{test_config.resource_name}_stack"
    cf.create_stack(
        StackName=stack_name, TemplateBody=test_config.get_cloudformation_template()
    )
    outputs = _get_stack_outputs(cf, stack_name)

    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: outputs["Name"]}
    )
    assert outputs["Arn"] == resource_description[test_config.arn_parameter]

    # Delete the stack and verify resource has also been deleted
    cf.delete_stack(StackName=stack_name)
    with pytest.raises(ClientError) as ce:
        getattr(sm, test_config.describe_function_name)(
            **{test_config.name_parameter: outputs["Name"]}
        )
    assert error_message in ce.value.response["Error"]["Message"]


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_notebook_instance_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    test_config = NotebookInstanceTestConfig()

    # Set up template for stack with two different instance types
    stack_name = f"{test_config.resource_name}_stack"
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
    outputs = _get_stack_outputs(cf, stack_name)

    initial_notebook_name = outputs["Name"]
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: initial_notebook_name}
    )
    assert initial_instance_type == resource_description["InstanceType"]

    # Update stack and check attributes
    cf.update_stack(StackName=stack_name, TemplateBody=updated_template_json)
    outputs = _get_stack_outputs(cf, stack_name)

    updated_notebook_name = outputs["Name"]
    assert updated_notebook_name == initial_notebook_name

    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: updated_notebook_name}
    )
    assert updated_instance_type == resource_description["InstanceType"]


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_notebook_instance_lifecycle_config_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    test_config = NotebookInstanceLifecycleConfigTestConfig()

    # Set up template for stack with two different OnCreate scripts
    stack_name = f"{test_config.resource_name}_stack"
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
    outputs = _get_stack_outputs(cf, stack_name)

    initial_config_name = outputs["Name"]
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: initial_config_name}
    )
    assert len(resource_description["OnCreate"]) == 1
    assert initial_on_create_script == resource_description["OnCreate"][0]["Content"]

    # Update stack and check attributes
    cf.update_stack(StackName=stack_name, TemplateBody=updated_template_json)
    outputs = _get_stack_outputs(cf, stack_name)

    updated_config_name = outputs["Name"]
    assert updated_config_name == initial_config_name

    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: updated_config_name}
    )
    assert len(resource_description["OnCreate"]) == 1
    assert updated_on_create_script == resource_description["OnCreate"][0]["Content"]


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_model_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    test_config = ModelTestConfig()

    # Set up template for stack with two different image versions
    stack_name = f"{test_config.resource_name}_stack"
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
    outputs = _get_stack_outputs(cf, stack_name)

    initial_model_name = outputs["Name"]
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: initial_model_name}
    )
    assert resource_description["PrimaryContainer"]["Image"] == (
        image.format(initial_image_version)
    )

    # Update stack and check attributes
    cf.update_stack(StackName=stack_name, TemplateBody=updated_template_json)
    outputs = _get_stack_outputs(cf, stack_name)

    updated_model_name = outputs["Name"]
    assert updated_model_name != initial_model_name

    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: updated_model_name}
    )
    assert resource_description["PrimaryContainer"]["Image"] == (
        image.format(updated_image_version)
    )


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_endpoint_config_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    test_config = EndpointConfigTestConfig()

    # Utilize test configuration to set-up any mock SageMaker resources
    test_config.run_setup_procedure(sm)

    # Set up template for stack with two different production variant counts
    stack_name = f"{test_config.resource_name}_stack"
    initial_num_production_variants = 1
    updated_num_production_variants = 2
    initial_template_json = test_config.get_cloudformation_template(
        num_production_variants=initial_num_production_variants
    )
    updated_template_json = test_config.get_cloudformation_template(
        num_production_variants=updated_num_production_variants
    )

    # Create stack with initial template and check attributes
    cf.create_stack(StackName=stack_name, TemplateBody=initial_template_json)
    outputs = _get_stack_outputs(cf, stack_name)

    initial_endpoint_config_name = outputs["Name"]
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: initial_endpoint_config_name}
    )
    assert len(resource_description["ProductionVariants"]) == (
        initial_num_production_variants
    )

    # Update stack and check attributes
    cf.update_stack(StackName=stack_name, TemplateBody=updated_template_json)
    outputs = _get_stack_outputs(cf, stack_name)

    updated_endpoint_config_name = outputs["Name"]
    assert updated_endpoint_config_name != initial_endpoint_config_name

    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: updated_endpoint_config_name}
    )
    assert len(resource_description["ProductionVariants"]) == (
        updated_num_production_variants
    )


@mock_cloudformation
@mock_sagemaker
def test_sagemaker_cloudformation_endpoint_update():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    sm = boto3.client("sagemaker", region_name="us-east-1")

    test_config = EndpointTestConfig()

    # Set up template for stack with two different endpoint config names
    stack_name = f"{test_config.resource_name}_stack"
    initial_endpoint_config_name = test_config.resource_name
    updated_endpoint_config_name = "updated-endpoint-config-name"
    initial_template_json = test_config.get_cloudformation_template(
        endpoint_config_name=initial_endpoint_config_name
    )
    updated_template_json = test_config.get_cloudformation_template(
        endpoint_config_name=updated_endpoint_config_name
    )

    # Create SM resources and stack with initial template and check attributes
    sm.create_model(
        ModelName=initial_endpoint_config_name,
        ExecutionRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        PrimaryContainer={
            "Image": "404615174143.dkr.ecr.us-east-2.amazonaws.com/linear-learner:1",
        },
    )
    sm.create_endpoint_config(
        EndpointConfigName=initial_endpoint_config_name,
        ProductionVariants=[
            {
                "InitialInstanceCount": 1,
                "InitialVariantWeight": 1,
                "InstanceType": "ml.c4.xlarge",
                "ModelName": initial_endpoint_config_name,
                "VariantName": "variant-name-1",
            },
        ],
    )
    cf.create_stack(StackName=stack_name, TemplateBody=initial_template_json)
    outputs = _get_stack_outputs(cf, stack_name)

    initial_endpoint_name = outputs["Name"]
    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: initial_endpoint_name}
    )
    assert re.match(
        initial_endpoint_config_name, resource_description["EndpointConfigName"]
    )

    # Create additional SM resources and update stack
    sm.create_model(
        ModelName=updated_endpoint_config_name,
        ExecutionRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        PrimaryContainer={
            "Image": "404615174143.dkr.ecr.us-east-2.amazonaws.com/linear-learner:1",
        },
    )
    sm.create_endpoint_config(
        EndpointConfigName=updated_endpoint_config_name,
        ProductionVariants=[
            {
                "InitialInstanceCount": 1,
                "InitialVariantWeight": 1,
                "InstanceType": "ml.c4.xlarge",
                "ModelName": updated_endpoint_config_name,
                "VariantName": "variant-name-1",
            },
        ],
    )
    cf.update_stack(StackName=stack_name, TemplateBody=updated_template_json)
    outputs = _get_stack_outputs(cf, stack_name)

    updated_endpoint_name = outputs["Name"]
    assert updated_endpoint_name == initial_endpoint_name

    resource_description = getattr(sm, test_config.describe_function_name)(
        **{test_config.name_parameter: updated_endpoint_name}
    )
    assert re.match(
        updated_endpoint_config_name, resource_description["EndpointConfigName"]
    )
