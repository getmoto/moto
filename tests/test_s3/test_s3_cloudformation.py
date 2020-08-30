import json
import boto3

import sure  # noqa

from moto import mock_s3, mock_cloudformation


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_basic():
    s3 = boto3.client("s3", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"testInstance": {"Type": "AWS::S3::Bucket", "Properties": {},}},
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    stack_id = cf.create_stack(StackName="test_stack", TemplateBody=template_json)[
        "StackId"
    ]
    stack_description = cf.describe_stacks(StackName="test_stack")["Stacks"][0]

    s3.head_bucket(Bucket=stack_description["Outputs"][0]["OutputValue"])


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_with_properties():
    s3 = boto3.client("s3", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")

    bucket_name = "MyBucket"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testInstance": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": bucket_name,
                    "BucketEncryption": {
                        "ServerSideEncryptionConfiguration": [
                            {
                                "ServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": "AES256"
                                }
                            }
                        ]
                    },
                },
            }
        },
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    stack_id = cf.create_stack(StackName="test_stack", TemplateBody=template_json)[
        "StackId"
    ]
    stack_description = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    s3.head_bucket(Bucket=bucket_name)

    encryption = s3.get_bucket_encryption(Bucket=bucket_name)
    encryption["ServerSideEncryptionConfiguration"]["Rules"][0][
        "ApplyServerSideEncryptionByDefault"
    ]["SSEAlgorithm"].should.equal("AES256")


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_update_no_interruption():
    s3 = boto3.client("s3", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"testInstance": {"Type": "AWS::S3::Bucket"}},
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    stack_description = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    s3.head_bucket(Bucket=stack_description["Outputs"][0]["OutputValue"])

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testInstance": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketEncryption": {
                        "ServerSideEncryptionConfiguration": [
                            {
                                "ServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": "AES256"
                                }
                            }
                        ]
                    }
                },
            }
        },
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    cf.update_stack(StackName="test_stack", TemplateBody=template_json)
    encryption = s3.get_bucket_encryption(
        Bucket=stack_description["Outputs"][0]["OutputValue"]
    )
    encryption["ServerSideEncryptionConfiguration"]["Rules"][0][
        "ApplyServerSideEncryptionByDefault"
    ]["SSEAlgorithm"].should.equal("AES256")


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_update_replacement():
    s3 = boto3.client("s3", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"testInstance": {"Type": "AWS::S3::Bucket"}},
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    stack_description = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    s3.head_bucket(Bucket=stack_description["Outputs"][0]["OutputValue"])

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testInstance": {
                "Type": "AWS::S3::Bucket",
                "Properties": {"BucketName": "MyNewBucketName"},
            }
        },
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    cf.update_stack(StackName="test_stack", TemplateBody=template_json)
    stack_description = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    s3.head_bucket(Bucket=stack_description["Outputs"][0]["OutputValue"])
