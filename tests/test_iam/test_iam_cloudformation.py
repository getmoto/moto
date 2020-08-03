import boto3
import sure  # noqa

from nose.tools import assert_raises
from botocore.exceptions import ClientError

from moto import mock_iam, mock_cloudformation


@mock_iam
@mock_cloudformation
def test_iam_cloudformation_create_user():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"
    user_name = "MyUser"

    template = """
Resources:
  TheUser:
    Type: AWS::Iam::User
    Properties:
      UserName: {0}
""".strip().format(
        user_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    provisioned_resource["LogicalResourceId"].should.equal("TheUser")
    provisioned_resource["PhysicalResourceId"].should.equal(user_name)


@mock_iam
@mock_cloudformation
def test_iam_cloudformation_update_user_no_interruption():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheUser:
    Type: AWS::Iam::User
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)
    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    user_name = provisioned_resource["PhysicalResourceId"]

    iam_client = boto3.client("iam")
    user = iam_client.get_user(UserName=user_name)["User"]
    user["Path"].should.equal("/")

    path = "/MyPath/"
    template = """
Resources:
  TheUser:
    Type: AWS::Iam::User
    Properties:
      Path: {0}
""".strip().format(
        path
    )

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    user = iam_client.get_user(UserName=user_name)["User"]
    user["Path"].should.equal(path)


@mock_iam
@mock_cloudformation
def test_iam_cloudformation_update_user_replacement():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheUser:
    Type: AWS::Iam::User
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)
    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    original_user_name = provisioned_resource["PhysicalResourceId"]

    iam_client = boto3.client("iam")
    user = iam_client.get_user(UserName=original_user_name)["User"]
    user["Path"].should.equal("/")

    new_user_name = "MyUser"
    template = """
Resources:
  TheUser:
    Type: AWS::Iam::User
    Properties:
      UserName: {0}
""".strip().format(
        new_user_name
    )

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    with assert_raises(ClientError) as e:
        iam_client.get_user(UserName=original_user_name)
    e.exception.response["Error"]["Code"].should.equal("NoSuchEntity")

    iam_client.get_user(UserName=new_user_name)


@mock_iam
@mock_cloudformation
def test_iam_cloudformation_delete_user():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"
    user_name = "MyUser"

    template = """
Resources:
  TheUser:
    Type: AWS::Iam::User
    Properties:
      UserName: {}
""".strip().format(
        user_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    iam_client = boto3.client("iam")
    user = iam_client.get_user(UserName=user_name)

    cf_client.delete_stack(StackName=stack_name)

    with assert_raises(ClientError) as e:
        user = iam_client.get_user(UserName=user_name)
    e.exception.response["Error"]["Code"].should.equal("NoSuchEntity")


@mock_iam
@mock_cloudformation
def test_iam_cloudformation_get_attr():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"
    user_name = "MyUser"

    template = """
Resources:
  TheUser:
    Type: AWS::Iam::User
    Properties:
      UserName: {0}
Outputs:
  UserName:
    Value: !Ref TheUser
  UserArn:
    Value: !GetAtt TheUser.Arn
""".strip().format(
        user_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)
    stack_description = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    output_user_name = [
        output["OutputValue"]
        for output in stack_description["Outputs"]
        if output["OutputKey"] == "UserName"
    ][0]
    output_user_arn = [
        output["OutputValue"]
        for output in stack_description["Outputs"]
        if output["OutputKey"] == "UserArn"
    ][0]

    iam_client = boto3.client("iam")
    user_description = iam_client.get_user(UserName=output_user_name)["User"]
    output_user_arn.should.equal(user_description["Arn"])
