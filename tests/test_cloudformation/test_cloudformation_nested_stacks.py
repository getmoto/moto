import json
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

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


@mock_aws
def test_get_nested_stack_output_with_getatt():
    cf = boto3.client("cloudformation", "us-east-1")
    ssm = boto3.client("ssm", "us-east-1")
    bucket_created_by_cf = str(uuid4())
    template_url = upload_inner_template(get_inner_template(bucket_created_by_cf))

    stack_name = "a" + str(uuid4())[0:6]
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "NestedStack": {
                "Type": "AWS::CloudFormation::Stack",
                "Properties": {"TemplateURL": template_url},
            },
            "Param": {
                "Type": "AWS::SSM::Parameter",
                "Properties": {
                    "Name": "nested-bucket",
                    "Type": "String",
                    "Value": {"Fn::GetAtt": ["NestedStack", "Outputs.Bucket"]},
                },
            },
        },
        "Outputs": {
            "NestedBucket": {
                "Value": {"Fn::GetAtt": ["NestedStack", "Outputs.Bucket"]}
            },
            "NestedBucketSub": {"Value": {"Fn::Sub": "${NestedStack.Outputs.Bucket}"}},
        },
    }
    cf.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    outputs = get_stack_outputs(cf, stack_name)
    assert outputs["NestedBucket"] == bucket_created_by_cf
    assert outputs["NestedBucketSub"] == bucket_created_by_cf

    param = ssm.get_parameter(Name="nested-bucket")["Parameter"]
    assert param["Value"] == bucket_created_by_cf


@mock_aws
def test_get_nested_stack_output_with_yaml_getatt():
    cf = boto3.client("cloudformation", "us-east-1")
    bucket_created_by_cf = str(uuid4())
    template_url = upload_inner_template(get_inner_template(bucket_created_by_cf))

    stack_name = "a" + str(uuid4())[0:6]
    template = f"""
AWSTemplateFormatVersion: "2010-09-09"
Resources:
  NestedStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: {template_url}
Outputs:
  NestedBucket:
    Value: !GetAtt NestedStack.Outputs.Bucket
  NestedBucketSub:
    Value: !Sub "${{NestedStack.Outputs.Bucket}}-suffix"
"""
    cf.create_stack(StackName=stack_name, TemplateBody=template)

    outputs = get_stack_outputs(cf, stack_name)
    assert outputs["NestedBucket"] == bucket_created_by_cf
    assert outputs["NestedBucketSub"] == f"{bucket_created_by_cf}-suffix"


@mock_aws
def test_get_unknown_nested_stack_output():
    cf = boto3.client("cloudformation", "us-east-1")
    template_url = upload_inner_template(get_inner_template(str(uuid4())))

    stack_name = "a" + str(uuid4())[0:6]
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "NestedStack": {
                "Type": "AWS::CloudFormation::Stack",
                "Properties": {"TemplateURL": template_url},
            },
            "Param": {
                "Type": "AWS::SSM::Parameter",
                "Properties": {
                    "Type": "String",
                    "Value": {"Fn::GetAtt": ["NestedStack", "Outputs.Unknown"]},
                },
            },
        },
    }
    with pytest.raises(ClientError) as exc:
        cf.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Template error: resource NestedStack does not support attribute type Outputs.Unknown in Fn::GetAtt"
    )


def upload_inner_template(template):
    s3 = boto3.client("s3", "us-east-1")
    cf_storage_bucket = str(uuid4())
    s3.create_bucket(Bucket=cf_storage_bucket)
    s3.put_object(Bucket=cf_storage_bucket, Key="stack.json", Body=json.dumps(template))
    return f"https://s3.amazonaws.com/{cf_storage_bucket}/stack.json"


def get_stack_outputs(cf, stack_name):
    stack = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    return {o["OutputKey"]: o["OutputValue"] for o in stack["Outputs"]}


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
