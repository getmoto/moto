from collections import OrderedDict
import json
import yaml
import os
import boto3
from nose.tools import raises
import botocore
import sure  # noqa


from moto.cloudformation.exceptions import ValidationError
from moto.cloudformation.models import FakeStack
from moto.cloudformation.parsing import (
    resource_class_from_type,
    parse_condition,
    Export,
)
from moto.sqs.models import Queue
from moto.s3.models import FakeBucket
from moto.cloudformation.utils import yaml_tag_constructor
from boto.cloudformation.stack import Output
from moto import mock_cloudformation, mock_s3, mock_sqs, mock_ec2

json_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {
        "EC2Instance1": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": "ami-d3adb33f",
                "KeyName": "dummy",
                "InstanceType": "t2.micro",
                "Tags": [
                    {"Key": "Description", "Value": "Test tag"},
                    {"Key": "Name", "Value": "Name tag for tests"},
                ],
            },
        }
    },
}

json_valid_template_with_tabs = """
{
\t"AWSTemplateFormatVersion": "2010-09-09",
\t"Description": "Stack 2",
\t"Resources": {
\t\t"Queue": {"Type": "AWS::SQS::Queue", "Properties": {"VisibilityTimeout": 60}}
\t}
}
"""

# One resource is required
json_bad_template = {"AWSTemplateFormatVersion": "2010-09-09", "Description": "Stack 1"}

dummy_template_json = json.dumps(json_template)
dummy_bad_template_json = json.dumps(json_bad_template)


@mock_cloudformation
def test_boto3_json_validate_successful():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    response = cf_conn.validate_template(TemplateBody=dummy_template_json)
    assert response["Description"] == "Stack 1"
    assert response["Parameters"] == []
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_cloudformation
def test_boto3_json_with_tabs_validate_successful():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    response = cf_conn.validate_template(TemplateBody=json_valid_template_with_tabs)
    assert response["Description"] == "Stack 2"
    assert response["Parameters"] == []
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_cloudformation
def test_boto3_json_invalid_missing_resource():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    try:
        cf_conn.validate_template(TemplateBody=dummy_bad_template_json)
        assert False
    except botocore.exceptions.ClientError as e:
        str(e).should.contain(
            "An error occurred (ValidationError) when calling the ValidateTemplate operation: Stack"
            " with id Missing top level"
        )
        assert True


yaml_template = """
    AWSTemplateFormatVersion: '2010-09-09'
    Description: Simple CloudFormation Test Template
    Resources:
      S3Bucket:
        Type: AWS::S3::Bucket
        Properties:
          AccessControl: PublicRead
          BucketName: cf-test-bucket-1
"""

yaml_bad_template = """
    AWSTemplateFormatVersion: '2010-09-09'
    Description: Simple CloudFormation Test Template
"""


@mock_cloudformation
def test_boto3_yaml_validate_successful():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    response = cf_conn.validate_template(TemplateBody=yaml_template)
    assert response["Description"] == "Simple CloudFormation Test Template"
    assert response["Parameters"] == []
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_cloudformation
@mock_s3
def test_boto3_yaml_validate_template_url_successful():
    s3 = boto3.client("s3")
    s3_conn = boto3.resource("s3", region_name="us-east-1")
    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=yaml_template)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )

    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    response = cf_conn.validate_template(TemplateURL=key_url)
    assert response["Description"] == "Simple CloudFormation Test Template"
    assert response["Parameters"] == []
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_cloudformation
def test_boto3_yaml_invalid_missing_resource():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    try:
        cf_conn.validate_template(TemplateBody=yaml_bad_template)
        assert False
    except botocore.exceptions.ClientError as e:
        str(e).should.contain(
            "An error occurred (ValidationError) when calling the ValidateTemplate operation: Stack"
            " with id Missing top level"
        )
        assert True
