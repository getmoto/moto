import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_associate_resource_cloudformation():
    client = boto3.client("servicecatalog-appregistry", region_name="us-east-1")
    stack_name = "foo"
    stack_id = boto3.client("cloudformation", region_name="us-east-1").create_stack(
        StackName=stack_name,
        TemplateBody="""
---
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  S3:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: foo
""",
    )["StackId"]
    create = client.create_application(name="testapp", description="blah")
    resp = client.associate_resource(
        application=create["application"]["id"],
        resource=stack_id,
        resourceType="CFN_STACK",
        options=["APPLY_APPLICATION_TAG"],
    )

    assert "applicationArn" in resp
    assert "resourceArn" in resp
    assert "options" in resp
    assert resp["applicationArn"] == create["application"]["arn"]


@mock_aws
def test_associate_resource_cloudformation_validation_error():
    client = boto3.client("servicecatalog-appregistry", region_name="us-east-1")
    create = client.create_application(name="testapp", description="blah")
    stack_name = "foo"
    with pytest.raises(ClientError) as exc:
        client.associate_resource(
            application=create["application"]["id"],
            resource=stack_name,
            resourceType="CFN_STACK",
            options=["APPLY_APPLICATION_TAG"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"No CloudFormation stack called '{stack_name}' found"
