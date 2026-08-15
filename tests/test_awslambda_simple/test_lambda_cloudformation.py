"""Regression tests for #9852: Lambdas created via CloudFormation must respect
the `lambda.use_docker: False` config option so they land in the simple
backend instead of pulling Docker images on hosts without Docker.
"""

import io
import zipfile
from string import Template
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings

# Copy of tests/test_awslambda/test_awslambda_cloudformation
# Except that we verify the CloudFormation entry points respect the
# use_docker=False config and do not require Docker.

if settings.TEST_SERVER_MODE:
    raise SkipTest("No point in testing awslambda_simple in ServerMode")


def _process_lambda(func_str):
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", func_str)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def get_zip_file():
    return _process_lambda("def lambda_handler(event, context):\n    return event\n")


template = Template(
    """{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "LF3ABOV": {
            "Type": "AWS::Lambda::Function",
            "Properties": {
                "Handler": "$handler",
                "Role": "$role_arn",
                "Runtime": "$runtime",
                "Code": {
                    "S3Bucket": "$bucket_name",
                    "S3Key": "$key"
                }
            }
        }
    }
}"""
)


def _get_role_arn():
    iam = boto3.client("iam", region_name="us-east-1")
    try:
        iam.create_role(
            RoleName="my-role",
            AssumeRolePolicyDocument="some policy",
            Path="/my-path/",
        )
    except ClientError:
        pass
    return iam.get_role(RoleName="my-role")["Role"]["Arn"]


def _create_stack(cf, s3) -> dict:
    bucket_name = f"bucket-{uuid4().hex[:8]}"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_object(Bucket=bucket_name, Key="test.zip", Body=get_zip_file())
    body = template.substitute(
        handler="lambda_function.lambda_handler",
        role_arn=_get_role_arn(),
        runtime="python3.11",
        bucket_name=bucket_name,
        key="test.zip",
    )
    stack_name = f"stack{uuid4().hex[:6]}"
    stack = cf.create_stack(StackName=stack_name, TemplateBody=body)
    return stack


def _get_created_function_name(cf, stack) -> str:
    stack_id = stack["StackId"]
    resources = cf.list_stack_resources(StackName=stack_id)["StackResourceSummaries"]
    return resources[0]["PhysicalResourceId"]


@mock_aws(config={"lambda": {"use_docker": False}})
def test_lambda_function_can_be_created_by_cloudformation_without_docker():
    s3 = boto3.client("s3", "us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    lmbda = boto3.client("lambda", region_name="us-east-1")

    stack = _create_stack(cf, s3)
    created_fn_name = _get_created_function_name(cf, stack)

    # The function must be visible through the regular Lambda API
    # (which uses the same get_backend() router).
    created_fn = lmbda.get_function(FunctionName=created_fn_name)
    assert created_fn["Configuration"]["Handler"] == "lambda_function.lambda_handler"
    assert created_fn["Configuration"]["Runtime"] == "python3.11"

    # And invocation must succeed without Docker.
    result = lmbda.invoke(FunctionName=created_fn_name)
    assert result["StatusCode"] == 200


@mock_aws(config={"lambda": {"use_docker": False}})
def test_lambda_function_can_be_deleted_by_cloudformation_without_docker():
    s3 = boto3.client("s3", "us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    lmbda = boto3.client("lambda", region_name="us-east-1")

    stack = _create_stack(cf, s3)
    created_fn_name = _get_created_function_name(cf, stack)
    # Pre-condition: visible
    lmbda.get_function(FunctionName=created_fn_name)

    cf.delete_stack(StackName=stack["StackId"])

    with pytest.raises(ClientError) as err:
        lmbda.get_function(FunctionName=created_fn_name)
    assert err.value.response["Error"]["Code"] == "ResourceNotFoundException"


event_source_mapping_template = Template(
    """{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "$resource_name": {
            "Type": "AWS::Lambda::EventSourceMapping",
            "Properties": {
                "BatchSize": $batch_size,
                "EventSourceArn": "$event_source_arn",
                "FunctionName": "$function_name",
                "Enabled": $enabled
            }
        }
    }
}"""
)


@mock_aws(config={"lambda": {"use_docker": False}})
def test_event_source_mapping_create_and_delete_by_cloudformation_without_docker():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    s3 = boto3.client("s3", "us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    lmbda = boto3.client("lambda", region_name="us-east-1")

    queue = sqs.create_queue(QueueName=uuid4().hex[:6])
    lambda_stack = _create_stack(cf, s3)
    created_fn_name = _get_created_function_name(cf, lambda_stack)

    esm_body = event_source_mapping_template.substitute(
        resource_name="Foo",
        batch_size=1,
        event_source_arn=queue.attributes["QueueArn"],
        function_name=created_fn_name,
        enabled="true",
    )
    esm_stack = cf.create_stack(
        StackName=f"esm{uuid4().hex[:6]}", TemplateBody=esm_body
    )

    event_sources = lmbda.list_event_source_mappings(FunctionName=created_fn_name)
    assert len(event_sources["EventSourceMappings"]) == 1
    assert (
        event_sources["EventSourceMappings"][0]["EventSourceArn"]
        == queue.attributes["QueueArn"]
    )

    cf.delete_stack(StackName=esm_stack["StackId"])
    event_sources = lmbda.list_event_source_mappings(FunctionName=created_fn_name)
    assert len(event_sources["EventSourceMappings"]) == 0
