import json
import re

import boto3

from moto import mock_s3, mock_cloudformation


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_basic():
    s3_client = boto3.client("s3", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"testInstance": {"Type": "AWS::S3::Bucket", "Properties": {}}},
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    cf_client.create_stack(StackName="test_stack", TemplateBody=template_json)
    stack_description = cf_client.describe_stacks(StackName="test_stack")["Stacks"][0]

    s3_client.head_bucket(Bucket=stack_description["Outputs"][0]["OutputValue"])


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_with_properties():
    s3_client = boto3.client("s3", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

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
    cf_client.create_stack(StackName="test_stack", TemplateBody=template_json)
    cf_client.describe_stacks(StackName="test_stack")
    s3_client.head_bucket(Bucket=bucket_name)

    encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
    assert (
        encryption["ServerSideEncryptionConfiguration"]["Rules"][0][
            "ApplyServerSideEncryptionByDefault"
        ]["SSEAlgorithm"]
        == "AES256"
    )


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_update_no_interruption():
    s3_client = boto3.client("s3", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"testInstance": {"Type": "AWS::S3::Bucket"}},
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    cf_client.create_stack(StackName="test_stack", TemplateBody=template_json)
    stack_description = cf_client.describe_stacks(StackName="test_stack")["Stacks"][0]
    s3_client.head_bucket(Bucket=stack_description["Outputs"][0]["OutputValue"])

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
    cf_client.update_stack(StackName="test_stack", TemplateBody=template_json)
    encryption = s3_client.get_bucket_encryption(
        Bucket=stack_description["Outputs"][0]["OutputValue"]
    )
    assert (
        encryption["ServerSideEncryptionConfiguration"]["Rules"][0][
            "ApplyServerSideEncryptionByDefault"
        ]["SSEAlgorithm"]
        == "AES256"
    )


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_update_replacement():
    s3_client = boto3.client("s3", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"testInstance": {"Type": "AWS::S3::Bucket"}},
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    cf_client.create_stack(StackName="test_stack", TemplateBody=template_json)
    stack_description = cf_client.describe_stacks(StackName="test_stack")["Stacks"][0]
    s3_client.head_bucket(Bucket=stack_description["Outputs"][0]["OutputValue"])

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
    cf_client.update_stack(StackName="test_stack", TemplateBody=template_json)
    stack_description = cf_client.describe_stacks(StackName="test_stack")["Stacks"][0]
    s3_client.head_bucket(Bucket=stack_description["Outputs"][0]["OutputValue"])


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_outputs():
    region_name = "us-east-1"
    s3_client = boto3.client("s3", region_name=region_name)
    cf_client = boto3.resource("cloudformation", region_name=region_name)
    stack_name = "test-stack"
    bucket_name = "test-bucket"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "TestBucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {"BucketName": bucket_name},
            }
        },
        "Outputs": {
            "BucketARN": {
                "Value": {"Fn::GetAtt": ["TestBucket", "Arn"]},
                "Export": {"Name": {"Fn::Sub": "${AWS::StackName}:BucketARN"}},
            },
            "BucketDomainName": {
                "Value": {"Fn::GetAtt": ["TestBucket", "DomainName"]},
                "Export": {"Name": {"Fn::Sub": "${AWS::StackName}:BucketDomainName"}},
            },
            "BucketDualStackDomainName": {
                "Value": {"Fn::GetAtt": ["TestBucket", "DualStackDomainName"]},
                "Export": {
                    "Name": {"Fn::Sub": "${AWS::StackName}:BucketDualStackDomainName"}
                },
            },
            "BucketRegionalDomainName": {
                "Value": {"Fn::GetAtt": ["TestBucket", "RegionalDomainName"]},
                "Export": {
                    "Name": {"Fn::Sub": "${AWS::StackName}:BucketRegionalDomainName"}
                },
            },
            "BucketWebsiteURL": {
                "Value": {"Fn::GetAtt": ["TestBucket", "WebsiteURL"]},
                "Export": {"Name": {"Fn::Sub": "${AWS::StackName}:BucketWebsiteURL"}},
            },
            "BucketName": {
                "Value": {"Ref": "TestBucket"},
                "Export": {"Name": {"Fn::Sub": "${AWS::StackName}:BucketName"}},
            },
        },
    }
    cf_client.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))
    outputs_list = cf_client.Stack(stack_name).outputs
    output = {item["OutputKey"]: item["OutputValue"] for item in outputs_list}
    s3_client.head_bucket(Bucket=output["BucketName"])
    assert re.match(f"arn:aws:s3.+{bucket_name}", output["BucketARN"])
    assert output["BucketDomainName"] == f"{bucket_name}.s3.amazonaws.com"
    assert output["BucketDualStackDomainName"] == (
        f"{bucket_name}.s3.dualstack.{region_name}.amazonaws.com"
    )
    assert output["BucketRegionalDomainName"] == (
        f"{bucket_name}.s3.{region_name}.amazonaws.com"
    )
    assert output["BucketWebsiteURL"] == (
        f"http://{bucket_name}.s3-website.{region_name}.amazonaws.com"
    )
    assert output["BucketName"] == bucket_name
