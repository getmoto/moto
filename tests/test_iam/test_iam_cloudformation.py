import json
from uuid import uuid4

import boto3
import pytest
import yaml
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID
from tests.test_iam import iam_aws_verified
from tests.test_iam.test_iam import MOCK_STS_EC2_POLICY_DOCUMENT

TEMPLATE_MINIMAL_ROLE = """
AWSTemplateFormatVersion: 2010-09-09
Resources:
  RootRole:
    Type: 'AWS::IAM::Role'
    Properties:
      AssumeRolePolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Principal:
              Service:
              - ec2.amazonaws.com
            Action:
              - 'sts:AssumeRole'
Outputs:
  RootRole:
    Value: !Ref RootRole
  RoleARN:
    Value: {"Fn::GetAtt": ["RootRole", "Arn"]}
  RoleID:
    Value: {"Fn::GetAtt": ["RootRole", "RoleId"]}
"""


TEMPLATE_ROLE_INSTANCE_PROFILE = """
AWSTemplateFormatVersion: 2010-09-09
Resources:
  RootRole:
    Type: 'AWS::IAM::Role'
    Properties:
      RoleName: {0}
      AssumeRolePolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Principal:
              Service:
              - ec2.amazonaws.com
            Action:
              - 'sts:AssumeRole'
      Path: /
      Policies:
        - PolicyName: root
          PolicyDocument:
            Version: 2012-10-17
            Statement:
              - Effect: Allow
                Action: '*'
                Resource: '*'
  RootInstanceProfile:
    Type: 'AWS::IAM::InstanceProfile'
    Properties:
      Path: /
      Roles:
        - !Ref RootRole
"""


# AWS::IAM::User Tests
@mock_aws
def test_iam_cloudformation_create_user():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"
    user_name = "MyUser"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
    Properties:
      UserName: {0}
""".strip().format(user_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    assert provisioned_resource["LogicalResourceId"] == "TheUser"
    assert provisioned_resource["PhysicalResourceId"] == user_name


@mock_aws
def test_iam_cloudformation_update_user_no_interruption():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)
    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    user_name = provisioned_resource["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    user = iam_client.get_user(UserName=user_name)["User"]
    assert user["Path"] == "/"

    path = "/MyPath/"
    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
    Properties:
      Path: {0}
""".strip().format(path)

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    user = iam_client.get_user(UserName=user_name)["User"]
    assert user["Path"] == path


@mock_aws
def test_iam_cloudformation_update_user_replacement():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)
    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    original_user_name = provisioned_resource["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    user = iam_client.get_user(UserName=original_user_name)["User"]
    assert user["Path"] == "/"

    new_user_name = "MyUser"
    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
    Properties:
      UserName: {0}
""".strip().format(new_user_name)

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    with pytest.raises(ClientError) as e:
        iam_client.get_user(UserName=original_user_name)
    assert e.value.response["Error"]["Code"] == "NoSuchEntity"

    iam_client.get_user(UserName=new_user_name)


@mock_aws
def test_iam_cloudformation_update_drop_user():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheFirstUser:
    Type: AWS::IAM::User
  TheSecondUser:
    Type: AWS::IAM::User
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]
    first_provisioned_user = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheFirstUser"
    ][0]
    second_provisioned_user = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheSecondUser"
    ][0]
    first_user_name = first_provisioned_user["PhysicalResourceId"]
    second_user_name = second_provisioned_user["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    iam_client.get_user(UserName=first_user_name)
    iam_client.get_user(UserName=second_user_name)

    template = """
Resources:
  TheSecondUser:
    Type: AWS::IAM::User
""".strip()

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]
    assert len(provisioned_resources) == 1
    second_provisioned_user = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheSecondUser"
    ][0]
    assert second_user_name == second_provisioned_user["PhysicalResourceId"]

    iam_client.get_user(UserName=second_user_name)
    with pytest.raises(ClientError) as e:
        iam_client.get_user(UserName=first_user_name)
    assert e.value.response["Error"]["Code"] == "NoSuchEntity"


@mock_aws
def test_iam_cloudformation_delete_user():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"
    user_name = "MyUser"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
    Properties:
      UserName: {}
""".strip().format(user_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    iam_client = boto3.client("iam", region_name="us-east-1")
    iam_client.get_user(UserName=user_name)

    cf_client.delete_stack(StackName=stack_name)

    with pytest.raises(ClientError) as e:
        iam_client.get_user(UserName=user_name)
    assert e.value.response["Error"]["Code"] == "NoSuchEntity"


@mock_aws
def test_iam_cloudformation_delete_user_having_generated_name():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)
    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    assert provisioned_resource["LogicalResourceId"] == "TheUser"
    user_name = provisioned_resource["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    iam_client.get_user(UserName=user_name)

    cf_client.delete_stack(StackName=stack_name)

    with pytest.raises(ClientError) as e:
        iam_client.get_user(UserName=user_name)
    assert e.value.response["Error"]["Code"] == "NoSuchEntity"


@mock_aws
def test_iam_cloudformation_user_get_attr():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"
    user_name = "MyUser"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
    Properties:
      UserName: {0}
Outputs:
  UserName:
    Value: !Ref TheUser
  UserArn:
    Value: !GetAtt TheUser.Arn
""".strip().format(user_name)

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

    iam_client = boto3.client("iam", region_name="us-east-1")
    user_description = iam_client.get_user(UserName=output_user_name)["User"]
    assert output_user_arn == user_description["Arn"]


# AWS::IAM::ManagedPolicy Tests
@mock_aws
def test_iam_cloudformation_create_managed_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: '*'
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    policy_arn = provisioned_resource["PhysicalResourceId"]
    assert policy_arn.startswith(f"arn:aws:iam::{ACCOUNT_ID}:policy/MyStack-ThePolicy-")
    expected_name = policy_arn.split("/")[1]

    response = iam_client.list_entities_for_policy(PolicyArn=policy_arn)
    assert response["PolicyGroups"] == []
    assert response["PolicyUsers"] == []
    assert response["PolicyRoles"] == []

    policy = iam_client.get_policy(PolicyArn=policy_arn)["Policy"]
    assert policy["Arn"] == policy_arn
    assert policy["PolicyName"] == expected_name
    assert policy["Description"] == ""
    assert policy["Path"] == "/"


@mock_aws
def test_iam_cloudformation_create_managed_policy_with_additional_properties():
    iam_client = boto3.client("iam", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    name = "FancyManagedPolicy"
    desc = "Custom managed policy with name"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      Description: {0}
      Path: /
      ManagedPolicyName: {1}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: '*'
""".strip().format(desc, name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    policy_arn = provisioned_resource["PhysicalResourceId"]
    assert policy_arn == f"arn:aws:iam::{ACCOUNT_ID}:policy/{name}"

    policy = iam_client.get_policy(PolicyArn=policy_arn)["Policy"]
    assert policy["Arn"] == policy_arn
    assert policy["Path"] == "/"
    assert policy["Description"] == desc
    assert policy["PolicyName"] == name


@mock_aws
def test_iam_cloudformation_create_managed_policy_attached_to_a_group():
    iam_client = boto3.client("iam", region_name="us-east-1")
    group_name = "MyGroup"
    iam_client.create_group(GroupName=group_name)

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    desc = "Custom managed policy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      Description: {0}
      Path: /
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: '*'
      Groups:
        - {1}
""".strip().format(desc, group_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    policy_arn = provisioned_resource["PhysicalResourceId"]
    assert policy_arn.startswith(f"arn:aws:iam::{ACCOUNT_ID}:policy/MyStack-ThePolicy-")

    response = iam_client.list_entities_for_policy(PolicyArn=policy_arn)
    assert response["PolicyUsers"] == []
    assert response["PolicyRoles"] == []

    assert response["PolicyGroups"][0]["GroupName"] == group_name
    assert "GroupId" in response["PolicyGroups"][0]


@mock_aws
def test_iam_cloudformation_create_managed_policy_attached_to_a_user():
    iam_client = boto3.client("iam", region_name="us-east-1")
    user_name = "MyUser"
    iam_client.create_user(UserName=user_name)

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    desc = "Custom managed policy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      Description: {0}
      Path: /
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: '*'
      Users:
        - {1}
""".strip().format(desc, user_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    policy_arn = provisioned_resource["PhysicalResourceId"]
    assert policy_arn.startswith(f"arn:aws:iam::{ACCOUNT_ID}:policy/MyStack-ThePolicy-")

    response = iam_client.list_entities_for_policy(PolicyArn=policy_arn)
    assert response["PolicyGroups"] == []
    assert response["PolicyRoles"] == []

    assert response["PolicyUsers"][0]["UserName"] == user_name
    assert "UserId" in response["PolicyUsers"][0]


@mock_aws
def test_iam_cloudformation_create_managed_policy_attached_to_a_role():
    iam_client = boto3.client("iam", region_name="us-east-1")
    role_name = "MyRole"
    iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument="some policy")

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    desc = "Custom managed policy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      Description: {0}
      Path: /
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: '*'
      Roles:
        - {1}
""".strip().format(desc, role_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    policy_arn = provisioned_resource["PhysicalResourceId"]
    assert policy_arn.startswith(f"arn:aws:iam::{ACCOUNT_ID}:policy/MyStack-ThePolicy-")

    response = iam_client.list_entities_for_policy(PolicyArn=policy_arn)
    assert response["PolicyGroups"] == []
    assert response["PolicyUsers"] == []

    assert response["PolicyRoles"][0]["RoleName"] == role_name
    assert "RoleId" in response["PolicyRoles"][0]


# AWS::IAM::Policy Tests
@mock_aws
def test_iam_cloudformation_create_user_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    user_name = "MyUser"
    iam_client.create_user(UserName=user_name)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    policy_name = "MyPolicy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: {0}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: {1}
      Users:
        - {2}
""".strip().format(policy_name, bucket_arn, user_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_user_policy(UserName=user_name, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document


@mock_aws
def test_iam_cloudformation_update_user_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    user_name_1 = "MyUser1"
    iam_client.create_user(UserName=user_name_1)
    user_name_2 = "MyUser2"
    iam_client.create_user(UserName=user_name_2)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    policy_name = "MyPolicy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: {0}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: {1}
      Users:
        - {2}
""".strip().format(policy_name, bucket_arn, user_name_1)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_user_policy(UserName=user_name_1, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document

    # Change template and user
    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: {0}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:ListBuckets
          Resource: {1}
      Users:
        - {2}
""".strip().format(policy_name, bucket_arn, user_name_2)

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_user_policy(UserName=user_name_2, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document

    with pytest.raises(ClientError):
        iam_client.get_user_policy(UserName=user_name_1, PolicyName=policy_name)


@mock_aws
def test_iam_cloudformation_delete_user_policy_having_generated_name():
    iam_client = boto3.client("iam", region_name="us-east-1")
    user_name = "MyUser"
    iam_client.create_user(UserName=user_name)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    policy_name = "MyPolicy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: MyPolicy
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: {0}
      Users:
        - {1}
""".strip().format(bucket_arn, user_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_user_policy(UserName=user_name, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document

    cf_client.delete_stack(StackName=stack_name)
    with pytest.raises(ClientError):
        iam_client.get_user_policy(UserName=user_name, PolicyName=policy_name)


@mock_aws
def test_iam_cloudformation_create_role_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    role_name = "MyRole"
    iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    policy_name = "MyPolicy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: {0}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: {1}
      Roles:
        - {2}
""".strip().format(policy_name, bucket_arn, role_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document


@mock_aws
def test_iam_cloudformation_update_role_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    role_name_1 = "MyRole1"
    iam_client.create_role(RoleName=role_name_1, AssumeRolePolicyDocument="{}")
    role_name_2 = "MyRole2"
    iam_client.create_role(RoleName=role_name_2, AssumeRolePolicyDocument="{}")

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    policy_name = "MyPolicy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: {0}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: {1}
      Roles:
        - {2}
""".strip().format(policy_name, bucket_arn, role_name_1)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_role_policy(RoleName=role_name_1, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document

    # Change template and user
    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: {0}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:ListBuckets
          Resource: {1}
      Roles:
        - {2}
""".strip().format(policy_name, bucket_arn, role_name_2)

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_role_policy(RoleName=role_name_2, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document

    with pytest.raises(ClientError):
        iam_client.get_role_policy(RoleName=role_name_1, PolicyName=policy_name)


@mock_aws
def test_iam_cloudformation_delete_role_policy_having_generated_name():
    iam_client = boto3.client("iam", region_name="us-east-1")
    role_name = "MyRole"
    iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    policy_name = "MyPolicy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: MyPolicy
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: {0}
      Roles:
        - {1}
""".strip().format(bucket_arn, role_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document

    cf_client.delete_stack(StackName=stack_name)
    with pytest.raises(ClientError) as exc:
        iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
    assert exc.value.response["Error"]["Code"] == "NoSuchEntity"


@mock_aws
def test_iam_cloudformation_create_group_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    group_name = "MyGroup"
    iam_client.create_group(GroupName=group_name)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    policy_name = "MyPolicy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: {0}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: {1}
      Groups:
        - {2}
""".strip().format(policy_name, bucket_arn, group_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_group_policy(GroupName=group_name, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document


@mock_aws
def test_iam_cloudformation_update_group_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    group_name_1 = "MyGroup1"
    iam_client.create_group(GroupName=group_name_1)
    group_name_2 = "MyGroup2"
    iam_client.create_group(GroupName=group_name_2)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    policy_name = "MyPolicy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: {0}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: {1}
      Groups:
        - {2}
""".strip().format(policy_name, bucket_arn, group_name_1)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_group_policy(GroupName=group_name_1, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document

    # Change template and user
    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: {0}
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:ListBuckets
          Resource: {1}
      Groups:
        - {2}
""".strip().format(policy_name, bucket_arn, group_name_2)

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_group_policy(GroupName=group_name_2, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document

    with pytest.raises(ClientError) as exc:
        iam_client.get_group_policy(GroupName=group_name_1, PolicyName=policy_name)
    assert exc.value.response["Error"]["Code"] == "NoSuchEntity"


@mock_aws
def test_iam_cloudformation_delete_group_policy_having_generated_name():
    iam_client = boto3.client("iam", region_name="us-east-1")
    group_name = "MyGroup"
    iam_client.create_group(GroupName=group_name)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    stack_name = "MyStack"
    policy_name = "MyPolicy"

    template = """
Resources:
  ThePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: MyPolicy
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Action: s3:*
          Resource: {0}
      Groups:
        - {1}
""".strip().format(bucket_arn, group_name)

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    assert logical_resource_id == "ThePolicy"

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_group_policy(GroupName=group_name, PolicyName=policy_name)
    assert policy["PolicyDocument"] == original_policy_document

    cf_client.delete_stack(StackName=stack_name)
    with pytest.raises(ClientError) as exc:
        iam_client.get_group_policy(GroupName=group_name, PolicyName=policy_name)
    assert exc.value.response["Error"]["Code"] == "NoSuchEntity"


# AWS::IAM::User AccessKeys
@mock_aws
def test_iam_cloudformation_create_user_with_access_key():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
  TheAccessKey:
    Type: AWS::IAM::AccessKey
    Properties:
      UserName: !Ref TheUser
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]

    provisioned_user = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheUser"
    ][0]
    user_name = provisioned_user["PhysicalResourceId"]

    provisioned_access_keys = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheAccessKey"
    ]
    assert len(provisioned_access_keys) == 1

    iam_client = boto3.client("iam", region_name="us-east-1")
    user = iam_client.get_user(UserName=user_name)["User"]
    assert user["UserName"] == user_name
    access_keys = iam_client.list_access_keys(UserName=user_name)
    assert access_keys["AccessKeyMetadata"][0]["UserName"] == user_name


@mock_aws
def test_iam_cloudformation_access_key_get_attr():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
  TheAccessKey:
    Type: AWS::IAM::AccessKey
    Properties:
      UserName: !Ref TheUser
Outputs:
  AccessKeyId:
    Value: !Ref TheAccessKey
  SecretKey:
    Value: !GetAtt TheAccessKey.SecretAccessKey
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]
    provisioned_user = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheUser"
    ][0]
    user_name = provisioned_user["PhysicalResourceId"]

    stack_description = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    output_access_key_id = [
        output["OutputValue"]
        for output in stack_description["Outputs"]
        if output["OutputKey"] == "AccessKeyId"
    ][0]
    output_secret_key = [
        output["OutputValue"]
        for output in stack_description["Outputs"]
        if output["OutputKey"] == "SecretKey"
    ][0]

    sts_client = boto3.client(
        "sts",
        aws_access_key_id=output_access_key_id,
        aws_secret_access_key=output_secret_key,
        region_name="us-east-1",
    )
    caller_identity = sts_client.get_caller_identity()
    assert caller_identity["Arn"].split("/")[1] == user_name
    pass


@mock_aws
def test_iam_cloudformation_delete_users_access_key():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
    Resources:
      TheUser:
        Type: AWS::IAM::User
      TheAccessKey:
        Type: AWS::IAM::AccessKey
        Properties:
          UserName: !Ref TheUser
    """.strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]

    provisioned_user = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheUser"
    ][0]
    user_name = provisioned_user["PhysicalResourceId"]

    provisioned_access_keys = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheAccessKey"
    ]
    assert len(provisioned_access_keys) == 1
    access_key_id = provisioned_access_keys[0]["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    user = iam_client.get_user(UserName=user_name)["User"]
    assert user["UserName"] == user_name
    access_keys = iam_client.list_access_keys(UserName=user_name)
    assert access_keys["AccessKeyMetadata"][0]["AccessKeyId"] == access_key_id
    assert access_keys["AccessKeyMetadata"][0]["UserName"] == user_name
    assert access_key_id == access_keys["AccessKeyMetadata"][0]["AccessKeyId"]

    cf_client.delete_stack(StackName=stack_name)

    with pytest.raises(ClientError) as exc:
        iam_client.get_user(UserName=user_name)
    assert exc.value.response["Error"]["Code"] == "NoSuchEntity"

    with pytest.raises(ClientError) as exc:
        iam_client.list_access_keys(UserName=user_name)
    assert exc.value.response["Error"]["Code"] == "NoSuchEntity"


@mock_aws
def test_iam_cloudformation_update_users_access_key_no_interruption():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
  TheAccessKey:
    Type: AWS::IAM::AccessKey
    Properties:
      UserName: !Ref TheUser
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]

    provisioned_user = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheUser"
    ][0]
    user_name = provisioned_user["PhysicalResourceId"]

    provisioned_access_key = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheAccessKey"
    ][0]
    access_key_id = provisioned_access_key["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    iam_client.get_user(UserName=user_name)
    access_keys = iam_client.list_access_keys(UserName=user_name)
    assert access_key_id == access_keys["AccessKeyMetadata"][0]["AccessKeyId"]

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
  TheAccessKey:
    Type: AWS::IAM::AccessKey
    Properties:
      Status: Inactive
""".strip()

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)
    access_keys = iam_client.list_access_keys(UserName=user_name)
    assert access_keys["AccessKeyMetadata"][0]["Status"] == "Inactive"


@mock_aws
def test_iam_cloudformation_update_users_access_key_replacement():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
  TheAccessKey:
    Type: AWS::IAM::AccessKey
    Properties:
      UserName: !Ref TheUser
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]

    provisioned_user = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheUser"
    ][0]
    user_name = provisioned_user["PhysicalResourceId"]

    provisioned_access_key = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheAccessKey"
    ][0]
    access_key_id = provisioned_access_key["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    iam_client.get_user(UserName=user_name)
    access_keys = iam_client.list_access_keys(UserName=user_name)
    assert access_key_id == access_keys["AccessKeyMetadata"][0]["AccessKeyId"]

    other_user_name = "MyUser"
    iam_client.create_user(UserName=other_user_name)

    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
  TheAccessKey:
    Type: AWS::IAM::AccessKey
    Properties:
      UserName: {0}
""".strip().format(other_user_name)

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    access_keys = iam_client.list_access_keys(UserName=user_name)
    assert len(access_keys["AccessKeyMetadata"]) == 0

    access_keys = iam_client.list_access_keys(UserName=other_user_name)
    assert access_key_id != access_keys["AccessKeyMetadata"][0]["AccessKeyId"]


@mock_aws
def test_iam_cloudformation_create_role():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = TEMPLATE_MINIMAL_ROLE.strip()
    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]
    role = [res for res in resources if res["ResourceType"] == "AWS::IAM::Role"][0]
    assert role["LogicalResourceId"] == "RootRole"

    outputs = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]["Outputs"]
    outputs = {o["OutputKey"]: o["OutputValue"] for o in outputs}

    iam_client = boto3.client("iam", region_name="us-east-1")
    roles = iam_client.list_roles()["Roles"]
    assert len(roles) == 1

    assert roles[0]["RoleName"] == [v for k, v in outputs.items() if k == "RootRole"][0]
    assert roles[0]["Arn"] == [v for k, v in outputs.items() if k == "RoleARN"][0]
    assert roles[0]["RoleId"] == [v for k, v in outputs.items() if k == "RoleID"][0]

    cf_client.delete_stack(StackName=stack_name)

    assert len(iam_client.list_roles()["Roles"]) == 0


@mock_aws
def test_iam_cloudformation_create_role_and_instance_profile():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"
    role_name = "MyUser"

    template = TEMPLATE_ROLE_INSTANCE_PROFILE.strip().format(role_name)
    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]
    role = [res for res in resources if res["ResourceType"] == "AWS::IAM::Role"][0]
    assert role["LogicalResourceId"] == "RootRole"
    assert role["PhysicalResourceId"] == role_name
    profile = [
        res for res in resources if res["ResourceType"] == "AWS::IAM::InstanceProfile"
    ][0]
    assert profile["LogicalResourceId"] == "RootInstanceProfile"
    assert (
        stack_name in profile["PhysicalResourceId"]
    )  # e.g. MyStack-RootInstanceProfile-73Y4H4ALFW3N
    assert "RootInstanceProfile" in profile["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    assert len(iam_client.list_roles()["Roles"]) == 1

    cf_client.delete_stack(StackName=stack_name)

    assert len(iam_client.list_roles()["Roles"]) == 0


@mock_aws
def test_iam_roles():
    iam_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "my-launch-config": {
                "Properties": {
                    "IamInstanceProfile": {"Ref": "my-instance-profile-with-path"},
                    "ImageId": EXAMPLE_AMI_ID,
                    "InstanceType": "t2.medium",
                },
                "Type": "AWS::AutoScaling::LaunchConfiguration",
            },
            "my-instance-profile-with-path": {
                "Properties": {
                    "Path": "my-path",
                    "Roles": [{"Ref": "my-role-with-path"}],
                },
                "Type": "AWS::IAM::InstanceProfile",
            },
            "my-instance-profile-no-path": {
                "Properties": {"Roles": [{"Ref": "my-role-no-path"}]},
                "Type": "AWS::IAM::InstanceProfile",
            },
            "my-role-with-path": {
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Statement": [
                            {
                                "Action": ["sts:AssumeRole"],
                                "Effect": "Allow",
                                "Principal": {"Service": ["ec2.amazonaws.com"]},
                            }
                        ]
                    },
                    "Path": "/my-path/",
                    "Policies": [
                        {
                            "PolicyDocument": {
                                "Statement": [
                                    {
                                        "Action": [
                                            "ec2:CreateTags",
                                            "ec2:DescribeInstances",
                                            "ec2:DescribeTags",
                                        ],
                                        "Effect": "Allow",
                                        "Resource": ["*"],
                                    }
                                ],
                                "Version": "2012-10-17",
                            },
                            "PolicyName": "EC2_Tags",
                        },
                        {
                            "PolicyDocument": {
                                "Statement": [
                                    {
                                        "Action": ["sqs:*"],
                                        "Effect": "Allow",
                                        "Resource": ["*"],
                                    }
                                ],
                                "Version": "2012-10-17",
                            },
                            "PolicyName": "SQS",
                        },
                    ],
                },
                "Type": "AWS::IAM::Role",
            },
            "my-role-no-path": {
                "Properties": {
                    "RoleName": "my-role-no-path-name",
                    "AssumeRolePolicyDocument": {
                        "Statement": [
                            {
                                "Action": ["sts:AssumeRole"],
                                "Effect": "Allow",
                                "Principal": {"Service": ["ec2.amazonaws.com"]},
                            }
                        ]
                    },
                },
                "Type": "AWS::IAM::Role",
            },
        },
    }

    iam_template_json = json.dumps(iam_template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=iam_template_json)

    iam = boto3.client("iam", region_name="us-west-1")

    role_results = iam.list_roles()["Roles"]
    role_name_to_id = {}
    role_names = []
    for role_result in role_results:
        role = iam.get_role(RoleName=role_result["RoleName"])["Role"]
        role_names.append(role["RoleName"])
        # Role name is not specified, so randomly generated - can't check exact name
        if "with-path" in role["RoleName"]:
            role_name_to_id["with-path"] = role["RoleId"]
            assert role["Path"] == "/my-path/"
        else:
            role_name_to_id["no-path"] = role["RoleId"]
            assert role["RoleName"] == "my-role-no-path-name"
            assert role["Path"] == "/"

    instance_profile_responses = iam.list_instance_profiles()["InstanceProfiles"]
    assert len(instance_profile_responses) == 2
    instance_profile_names = []

    for instance_profile_response in instance_profile_responses:
        instance_profile = iam.get_instance_profile(
            InstanceProfileName=instance_profile_response["InstanceProfileName"]
        )["InstanceProfile"]
        instance_profile_names.append(instance_profile["InstanceProfileName"])
        assert "my-instance-profile" in instance_profile["InstanceProfileName"]
        if "with-path" in instance_profile["InstanceProfileName"]:
            assert instance_profile["Path"] == "my-path"
            assert (
                instance_profile["Roles"][0]["RoleId"] == role_name_to_id["with-path"]
            )
        else:
            assert "no-path" in instance_profile["InstanceProfileName"]
            assert instance_profile["Roles"][0]["RoleId"] == role_name_to_id["no-path"]
            assert instance_profile["Path"] == "/"

    autoscale = boto3.client("autoscaling", region_name="us-west-1")
    launch_config = autoscale.describe_launch_configurations()["LaunchConfigurations"][
        0
    ]
    assert "my-instance-profile-with-path" in launch_config["IamInstanceProfile"]

    resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]
    instance_profile_resources = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::IAM::InstanceProfile"
    ]
    assert {ip["PhysicalResourceId"] for ip in instance_profile_resources} == set(
        instance_profile_names
    )

    role_resources = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::IAM::Role"
    ]
    assert {r["PhysicalResourceId"] for r in role_resources} == set(role_names)


template_with_instance_profile = """
Parameters:
    InputRole:
        Type: String
        Default: "test-emr-role"

Resources:
    emrEc2InstanceProfile:
        Type: 'AWS::IAM::InstanceProfile'
        Properties:
            Path: /
            Roles:
              - !Ref InputRole
"""


@pytest.mark.aws_verified
@iam_aws_verified()
def test_delete_instance_profile_with_existing_role(user_name=None):
    region = "us-east-1"
    iam = boto3.client("iam", region_name=region)
    iam_role_name = f"moto_{str(uuid4())[0:6]}"
    iam.create_role(
        RoleName=iam_role_name, AssumeRolePolicyDocument=MOCK_STS_EC2_POLICY_DOCUMENT
    )

    try:
        cf = boto3.client("cloudformation", region_name=region)
        cf.create_stack(
            StackName="teststack",
            TemplateBody=template_with_instance_profile,
            Parameters=[{"ParameterKey": "InputRole", "ParameterValue": iam_role_name}],
            Capabilities=["CAPABILITY_NAMED_IAM"],
        )

        # Just verify that we can delete the InstanceProfile
        cf.delete_stack(StackName="teststack")

        # The role still exists at this point
        iam.get_role(RoleName=iam_role_name)
    finally:
        iam.delete_role(RoleName=iam_role_name)
