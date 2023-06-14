import boto3
import io
import zipfile
from botocore.exceptions import ClientError
from moto import mock_cloudformation, mock_iam, mock_lambda, mock_s3, mock_sqs
import pytest
import re
from string import Template
from uuid import uuid4


def random_stack_name():
    return str(uuid4())[0:6]


def _process_lambda(func_str):
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", func_str)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def get_zip_file():
    pfunc = """
def lambda_handler1(event, context):
    return event
def lambda_handler2(event, context):
    return event
"""
    return _process_lambda(pfunc)


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
                },
            }
        }
    }
}"""
)

event_source_mapping_template = Template(
    """{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "$resource_name": {
            "Type": "AWS::Lambda::EventSourceMapping",
            "Properties": {
                "BatchSize": $batch_size,
                "EventSourceArn": $event_source_arn,
                "FunctionName": $function_name,
                "Enabled": $enabled
            }
        }
    }
}"""
)


@mock_cloudformation
@mock_lambda
@mock_s3
def test_lambda_can_be_updated_by_cloudformation():
    s3 = boto3.client("s3", "us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    lmbda = boto3.client("lambda", region_name="us-east-1")
    body2, stack = create_stack(cf, s3)
    stack_name = re.search(":stack/(.+)/", stack["StackId"]).group(1)
    created_fn_name = get_created_function_name(cf, stack)
    # Verify function has been created
    created_fn = lmbda.get_function(FunctionName=created_fn_name)
    assert created_fn["Configuration"]["Handler"] == "lambda_function.lambda_handler1"
    assert created_fn["Configuration"]["Runtime"] == "python3.7"
    assert "/test1.zip" in created_fn["Code"]["Location"]
    # Update CF stack
    cf.update_stack(StackName=stack_name, TemplateBody=body2)
    updated_fn_name = get_created_function_name(cf, stack)
    # Verify function has been updated
    updated_fn = lmbda.get_function(FunctionName=updated_fn_name)
    assert (
        updated_fn["Configuration"]["FunctionArn"]
        == created_fn["Configuration"]["FunctionArn"]
    )
    assert updated_fn["Configuration"]["Handler"] == "lambda_function.lambda_handler2"
    assert updated_fn["Configuration"]["Runtime"] == "python3.8"
    assert "/test2.zip" in updated_fn["Code"]["Location"]


@mock_cloudformation
@mock_lambda
@mock_s3
def test_lambda_can_be_deleted_by_cloudformation():
    s3 = boto3.client("s3", "us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    lmbda = boto3.client("lambda", region_name="us-east-1")
    _, stack = create_stack(cf, s3)
    created_fn_name = get_created_function_name(cf, stack)
    # Delete Stack
    cf.delete_stack(StackName=stack["StackId"])
    # Verify function was deleted
    with pytest.raises(ClientError) as e:
        lmbda.get_function(FunctionName=created_fn_name)
    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_cloudformation
@mock_lambda
@mock_s3
@mock_sqs
def test_event_source_mapping_create_from_cloudformation_json():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    s3 = boto3.client("s3", "us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    lmbda = boto3.client("lambda", region_name="us-east-1")

    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    # Creates lambda
    _, lambda_stack = create_stack(cf, s3)
    created_fn_name = get_created_function_name(cf, lambda_stack)
    created_fn_arn = lmbda.get_function(FunctionName=created_fn_name)["Configuration"][
        "FunctionArn"
    ]

    esm_template = event_source_mapping_template.substitute(
        {
            "resource_name": "Foo",
            "batch_size": 1,
            "event_source_arn": queue.attributes["QueueArn"],
            "function_name": created_fn_name,
            "enabled": True,
        }
    )

    cf.create_stack(StackName=random_stack_name(), TemplateBody=esm_template)
    event_sources = lmbda.list_event_source_mappings(FunctionName=created_fn_name)

    assert len(event_sources["EventSourceMappings"]) == 1
    event_source = event_sources["EventSourceMappings"][0]
    assert event_source["EventSourceArn"] == queue.attributes["QueueArn"]
    assert event_source["FunctionArn"] == created_fn_arn


@mock_cloudformation
@mock_lambda
@mock_s3
@mock_sqs
def test_event_source_mapping_delete_stack():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    s3 = boto3.client("s3", "us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    lmbda = boto3.client("lambda", region_name="us-east-1")

    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    # Creates lambda
    _, lambda_stack = create_stack(cf, s3)
    created_fn_name = get_created_function_name(cf, lambda_stack)

    esm_template = event_source_mapping_template.substitute(
        {
            "resource_name": "Foo",
            "batch_size": 1,
            "event_source_arn": queue.attributes["QueueArn"],
            "function_name": created_fn_name,
            "enabled": True,
        }
    )

    esm_stack = cf.create_stack(
        StackName=random_stack_name(), TemplateBody=esm_template
    )
    event_sources = lmbda.list_event_source_mappings(FunctionName=created_fn_name)

    assert len(event_sources["EventSourceMappings"]) == 1

    cf.delete_stack(StackName=esm_stack["StackId"])
    event_sources = lmbda.list_event_source_mappings(FunctionName=created_fn_name)

    assert len(event_sources["EventSourceMappings"]) == 0


@mock_cloudformation
@mock_lambda
@mock_s3
@mock_sqs
def test_event_source_mapping_update_from_cloudformation_json():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    s3 = boto3.client("s3", "us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    lmbda = boto3.client("lambda", region_name="us-east-1")

    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    # Creates lambda
    _, lambda_stack = create_stack(cf, s3)
    created_fn_name = get_created_function_name(cf, lambda_stack)

    original_template = event_source_mapping_template.substitute(
        {
            "resource_name": "Foo",
            "batch_size": 1,
            "event_source_arn": queue.attributes["QueueArn"],
            "function_name": created_fn_name,
            "enabled": True,
        }
    )

    stack_name = random_stack_name()
    cf.create_stack(StackName=stack_name, TemplateBody=original_template)
    event_sources = lmbda.list_event_source_mappings(FunctionName=created_fn_name)
    original_esm = event_sources["EventSourceMappings"][0]

    assert original_esm["State"] == "Enabled"
    assert original_esm["BatchSize"] == 1

    # Update
    new_template = event_source_mapping_template.substitute(
        {
            "resource_name": "Foo",
            "batch_size": 10,
            "event_source_arn": queue.attributes["QueueArn"],
            "function_name": created_fn_name,
            "enabled": False,
        }
    )

    cf.update_stack(StackName=stack_name, TemplateBody=new_template)
    event_sources = lmbda.list_event_source_mappings(FunctionName=created_fn_name)
    updated_esm = event_sources["EventSourceMappings"][0]

    assert updated_esm["State"] == "Disabled"
    assert updated_esm["BatchSize"] == 10


@mock_cloudformation
@mock_lambda
@mock_s3
@mock_sqs
def test_event_source_mapping_delete_from_cloudformation_json():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    s3 = boto3.client("s3", "us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    lmbda = boto3.client("lambda", region_name="us-east-1")

    queue = sqs.create_queue(QueueName=str(uuid4())[0:6])

    # Creates lambda
    _, lambda_stack = create_stack(cf, s3)
    created_fn_name = get_created_function_name(cf, lambda_stack)

    original_template = event_source_mapping_template.substitute(
        {
            "resource_name": "Foo",
            "batch_size": 1,
            "event_source_arn": queue.attributes["QueueArn"],
            "function_name": created_fn_name,
            "enabled": True,
        }
    )

    stack_name = random_stack_name()
    cf.create_stack(StackName=stack_name, TemplateBody=original_template)
    event_sources = lmbda.list_event_source_mappings(FunctionName=created_fn_name)
    original_esm = event_sources["EventSourceMappings"][0]

    assert original_esm["State"] == "Enabled"
    assert original_esm["BatchSize"] == 1

    # Update with deletion of old resources
    new_template = event_source_mapping_template.substitute(
        {
            "resource_name": "Bar",  # changed name
            "batch_size": 10,
            "event_source_arn": queue.attributes["QueueArn"],
            "function_name": created_fn_name,
            "enabled": False,
        }
    )

    cf.update_stack(StackName=stack_name, TemplateBody=new_template)
    event_sources = lmbda.list_event_source_mappings(FunctionName=created_fn_name)

    assert len(event_sources["EventSourceMappings"]) == 1
    updated_esm = event_sources["EventSourceMappings"][0]

    assert updated_esm["State"] == "Disabled"
    assert updated_esm["BatchSize"] == 10
    assert updated_esm["UUID"] != original_esm["UUID"]


def create_stack(cf, s3):
    bucket_name = str(uuid4())
    stack_name = random_stack_name()
    s3.create_bucket(Bucket=bucket_name)
    s3.put_object(Bucket=bucket_name, Key="test1.zip", Body=get_zip_file())
    s3.put_object(Bucket=bucket_name, Key="test2.zip", Body=get_zip_file())
    body1 = get_template(bucket_name, "1", "python3.7")
    body2 = get_template(bucket_name, "2", "python3.8")
    stack = cf.create_stack(StackName=stack_name, TemplateBody=body1)
    return body2, stack


def get_created_function_name(cf, stack):
    res = cf.list_stack_resources(StackName=stack["StackId"])
    return res["StackResourceSummaries"][0]["PhysicalResourceId"]


def get_template(bucket_name, version, runtime):
    key = "test" + version + ".zip"
    handler = "lambda_function.lambda_handler" + version
    return template.substitute(
        bucket_name=bucket_name,
        key=key,
        handler=handler,
        role_arn=get_role_arn(),
        runtime=runtime,
    )


def get_role_arn():
    with mock_iam():
        iam = boto3.client("iam", region_name="us-west-2")
        try:
            iam.create_role(
                RoleName="my-role",
                AssumeRolePolicyDocument="some policy",
                Path="/my-path/",
            )
        except ClientError:
            pass  # Will fail second/third time - difficult to execute once with parallel tests

        return iam.get_role(RoleName="my-role")["Role"]["Arn"]
