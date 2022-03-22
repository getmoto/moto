import json
import boto3

import sure  # noqa # pylint: disable=unused-import

from moto import mock_s3, mock_cloudformation


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_basic():
    s3 = boto3.client("s3", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"testInstance": {"Type": "AWS::S3::Bucket", "Properties": {}}},
        "Outputs": {"Bucket": {"Value": {"Ref": "testInstance"}}},
    }
    template_json = json.dumps(template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
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
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    cf.describe_stacks(StackName="test_stack")
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


@mock_s3
@mock_cloudformation
def test_s3_bucket_cloudformation_outputs():
    region_name = "us-east-1"
    s3 = boto3.client("s3", region_name=region_name)
    cf = boto3.resource("cloudformation", region_name=region_name)
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
    cf.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))
    outputs_list = cf.Stack(stack_name).outputs
    output = {item["OutputKey"]: item["OutputValue"] for item in outputs_list}
    s3.head_bucket(Bucket=output["BucketName"])
    output["BucketARN"].should.match("arn:aws:s3.+{bucket}".format(bucket=bucket_name))
    output["BucketDomainName"].should.equal(
        "{bucket}.s3.amazonaws.com".format(bucket=bucket_name)
    )
    output["BucketDualStackDomainName"].should.equal(
        "{bucket}.s3.dualstack.{region}.amazonaws.com".format(
            bucket=bucket_name, region=region_name
        )
    )
    output["BucketRegionalDomainName"].should.equal(
        "{bucket}.s3.{region}.amazonaws.com".format(
            bucket=bucket_name, region=region_name
        )
    )
    output["BucketWebsiteURL"].should.equal(
        "http://{bucket}.s3-website.{region}.amazonaws.com".format(
            bucket=bucket_name, region=region_name
        )
    )
    output["BucketName"].should.equal(bucket_name)
