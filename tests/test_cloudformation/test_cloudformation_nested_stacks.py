import json
from uuid import uuid4

import boto3

from moto import mock_aws


@mock_aws
def test_create_basic_stack():
    # Create inner template
    cf = boto3.client("cloudformation", "us-east-1")
    bucket_created_by_cf = str(uuid4())
    template = get_inner_template(bucket_created_by_cf)
    # Upload inner template to S3
    s3 = boto3.client("s3", "us-east-1")
    cf_storage_bucket = str(uuid4())
    s3.create_bucket(Bucket=cf_storage_bucket)
    s3.put_object(Bucket=cf_storage_bucket, Key="stack.json", Body=json.dumps(template))

    # Create template that includes the inner template
    stack_name = "a" + str(uuid4())[0:6]
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "NestedStack": {
                "Type": "AWS::CloudFormation::Stack",
                "Properties": {
                    "TemplateURL": f"https://s3.amazonaws.com/{cf_storage_bucket}/stack.json",
                },
            },
        },
    }
    cf.create_stack(StackName=stack_name, TemplateBody=str(template))

    # Verify the inner S3 bucket has been created
    bucket_names = sorted([b["Name"] for b in s3.list_buckets()["Buckets"]])
    assert bucket_names == sorted([cf_storage_bucket, bucket_created_by_cf])

    # Verify both stacks are created
    stacks = cf.list_stacks()["StackSummaries"]
    assert len(stacks) == 2


@mock_aws
def test_create_stack_with_params():
    # Create inner template
    cf = boto3.client("cloudformation", "us-east-1")
    bucket_created_by_cf = str(uuid4())
    inner_template = json.dumps(get_inner_template_with_params())

    # Upload inner template to S3
    s3 = boto3.client("s3", "us-east-1")
    cf_storage_bucket = str(uuid4())
    s3.create_bucket(Bucket=cf_storage_bucket)
    s3.put_object(Bucket=cf_storage_bucket, Key="stack.json", Body=inner_template)

    # Create template that includes the inner template
    stack_name = "a" + str(uuid4())[0:6]
    template = get_outer_template_with_params(cf_storage_bucket, bucket_created_by_cf)
    cf.create_stack(StackName=stack_name, TemplateBody=str(template))

    # Verify the inner S3 bucket has been created
    bucket_names = sorted([b["Name"] for b in s3.list_buckets()["Buckets"]])
    assert bucket_names == sorted([cf_storage_bucket, bucket_created_by_cf])


@mock_aws
def test_update_stack_with_params():
    # Create inner template
    cf = boto3.client("cloudformation", "us-east-1")
    first_bucket = str(uuid4())
    second_bucket = str(uuid4())
    inner_template = json.dumps(get_inner_template_with_params())

    # Upload inner template to S3
    s3 = boto3.client("s3", "us-east-1")
    cf_storage_bucket = str(uuid4())
    s3.create_bucket(Bucket=cf_storage_bucket)
    s3.put_object(Bucket=cf_storage_bucket, Key="stack.json", Body=inner_template)

    # Create template that includes the inner template
    stack_name = "a" + str(uuid4())[0:6]
    template = get_outer_template_with_params(cf_storage_bucket, first_bucket)
    cf.create_stack(StackName=stack_name, TemplateBody=str(template))

    # Verify the inner S3 bucket has been created
    bucket_names = sorted([b["Name"] for b in s3.list_buckets()["Buckets"]])
    assert bucket_names == sorted([cf_storage_bucket, first_bucket])

    # Update stack
    template = get_outer_template_with_params(cf_storage_bucket, second_bucket)
    cf.update_stack(StackName=stack_name, TemplateBody=str(template))

    # Verify the inner S3 bucket has been created
    bucket_names = sorted([b["Name"] for b in s3.list_buckets()["Buckets"]])
    assert bucket_names == sorted([cf_storage_bucket, second_bucket])


@mock_aws
def test_delete_basic_stack():
    # Create inner template
    cf = boto3.client("cloudformation", "us-east-1")
    bucket_created_by_cf = str(uuid4())
    template = get_inner_template(bucket_created_by_cf)

    # Upload inner template to S3
    s3 = boto3.client("s3", "us-east-1")
    cf_storage_bucket = str(uuid4())
    s3.create_bucket(Bucket=cf_storage_bucket)
    s3.put_object(Bucket=cf_storage_bucket, Key="stack.json", Body=json.dumps(template))

    # Create template that includes the inner template
    stack_name = "a" + str(uuid4())[0:6]
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "NestedStack": {
                "Type": "AWS::CloudFormation::Stack",
                "Properties": {
                    "TemplateURL": f"https://s3.amazonaws.com/{cf_storage_bucket}/stack.json",
                },
            },
        },
    }
    cf.create_stack(StackName=stack_name, TemplateBody=str(template))
    cf.delete_stack(StackName=stack_name)

    # Verify the stack-controlled S3 bucket has been deleted
    bucket_names = sorted([b["Name"] for b in s3.list_buckets()["Buckets"]])
    assert bucket_names == [cf_storage_bucket]

    # Verify both stacks are deleted
    stacks = cf.list_stacks()["StackSummaries"]
    assert len(stacks) == 2
    for stack in stacks:
        assert stack["StackStatus"] == "DELETE_COMPLETE"


def get_inner_template(bucket_created_by_cf):
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "bcbcf": {
                "Type": "AWS::S3::Bucket",
                "Properties": {"BucketName": bucket_created_by_cf},
            }
        },
        "Outputs": {"Bucket": {"Value": {"Ref": "bcbcf"}}},
    }


def get_inner_template_with_params():
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Parameters": {
            "BName": {"Description": "bucket name", "Type": "String"},
        },
        "Resources": {
            "bcbcf": {
                "Type": "AWS::S3::Bucket",
                "Properties": {"BucketName": {"Ref": "BName"}},
            }
        },
    }


def get_outer_template_with_params(cf_storage_bucket, first_bucket):
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "NestedStack": {
                "Type": "AWS::CloudFormation::Stack",
                "Properties": {
                    "TemplateURL": f"https://s3.amazonaws.com/{cf_storage_bucket}/stack.json",
                    "Parameters": {"BName": first_bucket},
                },
            },
        },
    }
