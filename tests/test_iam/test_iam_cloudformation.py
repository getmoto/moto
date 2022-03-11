import boto3
import json
import yaml
import sure  # noqa # pylint: disable=unused-import

import pytest
from botocore.exceptions import ClientError

from moto.core import ACCOUNT_ID
from moto import mock_autoscaling, mock_iam, mock_cloudformation, mock_s3, mock_sts
from tests import EXAMPLE_AMI_ID


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
@mock_iam
@mock_cloudformation
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
    Type: AWS::IAM::User
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)
    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    user_name = provisioned_resource["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    user = iam_client.get_user(UserName=user_name)["User"]
    user["Path"].should.equal("/")

    path = "/MyPath/"
    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
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
    Type: AWS::IAM::User
""".strip()

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)
    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    original_user_name = provisioned_resource["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    user = iam_client.get_user(UserName=original_user_name)["User"]
    user["Path"].should.equal("/")

    new_user_name = "MyUser"
    template = """
Resources:
  TheUser:
    Type: AWS::IAM::User
    Properties:
      UserName: {0}
""".strip().format(
        new_user_name
    )

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    with pytest.raises(ClientError) as e:
        iam_client.get_user(UserName=original_user_name)
    e.value.response["Error"]["Code"].should.equal("NoSuchEntity")

    iam_client.get_user(UserName=new_user_name)


@mock_iam
@mock_cloudformation
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
    len(provisioned_resources).should.equal(1)
    second_provisioned_user = [
        resource
        for resource in provisioned_resources
        if resource["LogicalResourceId"] == "TheSecondUser"
    ][0]
    second_user_name.should.equal(second_provisioned_user["PhysicalResourceId"])

    iam_client.get_user(UserName=second_user_name)
    with pytest.raises(ClientError) as e:
        iam_client.get_user(UserName=first_user_name)
    e.value.response["Error"]["Code"].should.equal("NoSuchEntity")


@mock_iam
@mock_cloudformation
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
""".strip().format(
        user_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    iam_client = boto3.client("iam", region_name="us-east-1")
    iam_client.get_user(UserName=user_name)

    cf_client.delete_stack(StackName=stack_name)

    with pytest.raises(ClientError) as e:
        iam_client.get_user(UserName=user_name)
    e.value.response["Error"]["Code"].should.equal("NoSuchEntity")


@mock_iam
@mock_cloudformation
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
    provisioned_resource["LogicalResourceId"].should.equal("TheUser")
    user_name = provisioned_resource["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    iam_client.get_user(UserName=user_name)

    cf_client.delete_stack(StackName=stack_name)

    with pytest.raises(ClientError) as e:
        iam_client.get_user(UserName=user_name)
    e.value.response["Error"]["Code"].should.equal("NoSuchEntity")


@mock_iam
@mock_cloudformation
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

    iam_client = boto3.client("iam", region_name="us-east-1")
    user_description = iam_client.get_user(UserName=output_user_name)["User"]
    output_user_arn.should.equal(user_description["Arn"])


# AWS::IAM::ManagedPolicy Tests
@mock_iam
@mock_cloudformation
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
    logical_resource_id.should.equal("ThePolicy")

    policy_arn = provisioned_resource["PhysicalResourceId"]
    policy_arn.should.match(
        "arn:aws:iam::{}:policy/MyStack-ThePolicy-[A-Z0-9]+".format(ACCOUNT_ID)
    )
    expected_name = policy_arn.split("/")[1]

    response = iam_client.list_entities_for_policy(PolicyArn=policy_arn)
    response.should.have.key("PolicyGroups").equal([])
    response.should.have.key("PolicyUsers").equal([])
    response.should.have.key("PolicyRoles").equal([])

    policy = iam_client.get_policy(PolicyArn=policy_arn)["Policy"]
    policy.should.have.key("Arn").equal(policy_arn)
    policy.should.have.key("PolicyName").equal(expected_name)
    policy.should.have.key("Description").equal("")
    policy.should.have.key("Path").equal("/")


@mock_iam
@mock_cloudformation
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
""".strip().format(
        desc, name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    policy_arn = provisioned_resource["PhysicalResourceId"]
    policy_arn.should.equal("arn:aws:iam::{}:policy/{}".format(ACCOUNT_ID, name))

    policy = iam_client.get_policy(PolicyArn=policy_arn)["Policy"]
    policy.should.have.key("Arn").equal(policy_arn)
    policy.should.have.key("Path").equal("/")
    policy.should.have.key("Description").equal(desc)
    policy.should.have.key("PolicyName").equal(name)


@mock_iam
@mock_cloudformation
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
""".strip().format(
        desc, group_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    policy_arn = provisioned_resource["PhysicalResourceId"]
    policy_arn.should.match(
        "rn:aws:iam::{}:policy/MyStack-ThePolicy-[A-Z0-9]+".format(ACCOUNT_ID)
    )

    response = iam_client.list_entities_for_policy(PolicyArn=policy_arn)
    response.should.have.key("PolicyUsers").equal([])
    response.should.have.key("PolicyRoles").equal([])

    response["PolicyGroups"][0]["GroupName"].should.be.equal(group_name)
    response["PolicyGroups"][0].should.have.key("GroupId")


@mock_iam
@mock_cloudformation
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
""".strip().format(
        desc, user_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    policy_arn = provisioned_resource["PhysicalResourceId"]
    policy_arn.should.match(
        "rn:aws:iam::{}:policy/MyStack-ThePolicy-[A-Z0-9]+".format(ACCOUNT_ID)
    )

    response = iam_client.list_entities_for_policy(PolicyArn=policy_arn)
    response.should.have.key("PolicyGroups").equal([])
    response.should.have.key("PolicyRoles").equal([])

    response["PolicyUsers"][0]["UserName"].should.be.equal(user_name)
    response["PolicyUsers"][0].should.have.key("UserId")


@mock_iam
@mock_cloudformation
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
""".strip().format(
        desc, role_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    policy_arn = provisioned_resource["PhysicalResourceId"]
    policy_arn.should.match(
        "rn:aws:iam::{}:policy/MyStack-ThePolicy-[A-Z0-9]+".format(ACCOUNT_ID)
    )

    response = iam_client.list_entities_for_policy(PolicyArn=policy_arn)
    response.should.have.key("PolicyGroups").equal([])
    response.should.have.key("PolicyUsers").equal([])

    response["PolicyRoles"][0]["RoleName"].should.be.equal(role_name)
    response["PolicyRoles"][0].should.have.key("RoleId")


# AWS::IAM::Policy Tests
@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_create_user_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    user_name = "MyUser"
    iam_client.create_user(UserName=user_name)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)

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
""".strip().format(
        policy_name, bucket_arn, user_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_user_policy(UserName=user_name, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)


@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_update_user_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    user_name_1 = "MyUser1"
    iam_client.create_user(UserName=user_name_1)
    user_name_2 = "MyUser2"
    iam_client.create_user(UserName=user_name_2)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)

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
""".strip().format(
        policy_name, bucket_arn, user_name_1
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_user_policy(UserName=user_name_1, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)

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
""".strip().format(
        policy_name, bucket_arn, user_name_2
    )

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_user_policy(UserName=user_name_2, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)

    iam_client.get_user_policy.when.called_with(
        UserName=user_name_1, PolicyName=policy_name
    ).should.throw(iam_client.exceptions.NoSuchEntityException)


@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_delete_user_policy_having_generated_name():
    iam_client = boto3.client("iam", region_name="us-east-1")
    user_name = "MyUser"
    iam_client.create_user(UserName=user_name)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)

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
""".strip().format(
        bucket_arn, user_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_user_policy(UserName=user_name, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)

    cf_client.delete_stack(StackName=stack_name)
    iam_client.get_user_policy.when.called_with(
        UserName=user_name, PolicyName=policy_name
    ).should.throw(iam_client.exceptions.NoSuchEntityException)


@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_create_role_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    role_name = "MyRole"
    iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)

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
""".strip().format(
        policy_name, bucket_arn, role_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)


@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_update_role_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    role_name_1 = "MyRole1"
    iam_client.create_role(RoleName=role_name_1, AssumeRolePolicyDocument="{}")
    role_name_2 = "MyRole2"
    iam_client.create_role(RoleName=role_name_2, AssumeRolePolicyDocument="{}")

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)

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
""".strip().format(
        policy_name, bucket_arn, role_name_1
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_role_policy(RoleName=role_name_1, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)

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
""".strip().format(
        policy_name, bucket_arn, role_name_2
    )

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_role_policy(RoleName=role_name_2, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)

    iam_client.get_role_policy.when.called_with(
        RoleName=role_name_1, PolicyName=policy_name
    ).should.throw(iam_client.exceptions.NoSuchEntityException)


@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_delete_role_policy_having_generated_name():
    iam_client = boto3.client("iam", region_name="us-east-1")
    role_name = "MyRole"
    iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)

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
""".strip().format(
        bucket_arn, role_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)

    cf_client.delete_stack(StackName=stack_name)
    iam_client.get_role_policy.when.called_with(
        RoleName=role_name, PolicyName=policy_name
    ).should.throw(iam_client.exceptions.NoSuchEntityException)


@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_create_group_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    group_name = "MyGroup"
    iam_client.create_group(GroupName=group_name)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)

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
""".strip().format(
        policy_name, bucket_arn, group_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_group_policy(GroupName=group_name, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)


@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_update_group_policy():
    iam_client = boto3.client("iam", region_name="us-east-1")
    group_name_1 = "MyGroup1"
    iam_client.create_group(GroupName=group_name_1)
    group_name_2 = "MyGroup2"
    iam_client.create_group(GroupName=group_name_2)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)

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
""".strip().format(
        policy_name, bucket_arn, group_name_1
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_group_policy(GroupName=group_name_1, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)

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
""".strip().format(
        policy_name, bucket_arn, group_name_2
    )

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_group_policy(GroupName=group_name_2, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)

    iam_client.get_group_policy.when.called_with(
        GroupName=group_name_1, PolicyName=policy_name
    ).should.throw(iam_client.exceptions.NoSuchEntityException)


@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_delete_group_policy_having_generated_name():
    iam_client = boto3.client("iam", region_name="us-east-1")
    group_name = "MyGroup"
    iam_client.create_group(GroupName=group_name)

    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "my-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)

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
""".strip().format(
        bucket_arn, group_name
    )

    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    provisioned_resource = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    logical_resource_id = provisioned_resource["LogicalResourceId"]
    logical_resource_id.should.equal("ThePolicy")

    original_policy_document = yaml.load(template, Loader=yaml.FullLoader)["Resources"][
        logical_resource_id
    ]["Properties"]["PolicyDocument"]
    policy = iam_client.get_group_policy(GroupName=group_name, PolicyName=policy_name)
    policy["PolicyDocument"].should.equal(original_policy_document)

    cf_client.delete_stack(StackName=stack_name)
    iam_client.get_group_policy.when.called_with(
        GroupName=group_name, PolicyName=policy_name
    ).should.throw(iam_client.exceptions.NoSuchEntityException)


# AWS::IAM::User AccessKeys
@mock_iam
@mock_cloudformation
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
    len(provisioned_access_keys).should.equal(1)

    iam_client = boto3.client("iam", region_name="us-east-1")
    user = iam_client.get_user(UserName=user_name)["User"]
    user["UserName"].should.equal(user_name)
    access_keys = iam_client.list_access_keys(UserName=user_name)
    access_keys["AccessKeyMetadata"][0]["UserName"].should.equal(user_name)


@mock_sts
@mock_iam
@mock_cloudformation
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
    caller_identity["Arn"].split("/")[1].should.equal(user_name)
    pass


@mock_iam
@mock_cloudformation
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
    provisioned_access_keys.should.have.length_of(1)
    access_key_id = provisioned_access_keys[0]["PhysicalResourceId"]

    iam_client = boto3.client("iam", region_name="us-east-1")
    user = iam_client.get_user(UserName=user_name)["User"]
    user["UserName"].should.equal(user_name)
    access_keys = iam_client.list_access_keys(UserName=user_name)
    access_keys["AccessKeyMetadata"][0]["AccessKeyId"].should.equal(access_key_id)
    access_keys["AccessKeyMetadata"][0]["UserName"].should.equal(user_name)
    access_key_id.should.equal(access_keys["AccessKeyMetadata"][0]["AccessKeyId"])

    cf_client.delete_stack(StackName=stack_name)

    iam_client.get_user.when.called_with(UserName=user_name).should.throw(
        iam_client.exceptions.NoSuchEntityException
    )
    iam_client.list_access_keys.when.called_with(UserName=user_name).should.throw(
        iam_client.exceptions.NoSuchEntityException
    )


@mock_iam
@mock_cloudformation
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
    access_key_id.should.equal(access_keys["AccessKeyMetadata"][0]["AccessKeyId"])

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
    access_keys["AccessKeyMetadata"][0]["Status"].should.equal("Inactive")


@mock_iam
@mock_cloudformation
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
    access_key_id.should.equal(access_keys["AccessKeyMetadata"][0]["AccessKeyId"])

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
""".strip().format(
        other_user_name
    )

    cf_client.update_stack(StackName=stack_name, TemplateBody=template)

    access_keys = iam_client.list_access_keys(UserName=user_name)
    len(access_keys["AccessKeyMetadata"]).should.equal(0)

    access_keys = iam_client.list_access_keys(UserName=other_user_name)
    access_key_id.should_not.equal(access_keys["AccessKeyMetadata"][0]["AccessKeyId"])


@mock_iam
@mock_cloudformation
def test_iam_cloudformation_create_role():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyStack"

    template = TEMPLATE_MINIMAL_ROLE.strip()
    cf_client.create_stack(StackName=stack_name, TemplateBody=template)

    resources = cf_client.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]
    role = [res for res in resources if res["ResourceType"] == "AWS::IAM::Role"][0]
    role["LogicalResourceId"].should.equal("RootRole")

    iam_client = boto3.client("iam", region_name="us-east-1")
    iam_client.list_roles()["Roles"].should.have.length_of(1)

    cf_client.delete_stack(StackName=stack_name)

    iam_client.list_roles()["Roles"].should.have.length_of(0)


@mock_iam
@mock_cloudformation
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
    role["LogicalResourceId"].should.equal("RootRole")
    role["PhysicalResourceId"].should.equal(role_name)
    profile = [
        res for res in resources if res["ResourceType"] == "AWS::IAM::InstanceProfile"
    ][0]
    profile["LogicalResourceId"].should.equal("RootInstanceProfile")
    profile["PhysicalResourceId"].should.contain(
        stack_name
    )  # e.g. MyStack-RootInstanceProfile-73Y4H4ALFW3N
    profile["PhysicalResourceId"].should.contain("RootInstanceProfile")

    iam_client = boto3.client("iam", region_name="us-east-1")
    iam_client.list_roles()["Roles"].should.have.length_of(1)

    cf_client.delete_stack(StackName=stack_name)

    iam_client.list_roles()["Roles"].should.have.length_of(0)


@mock_autoscaling
@mock_iam
@mock_cloudformation
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
            role["Path"].should.equal("/my-path/")
        else:
            role_name_to_id["no-path"] = role["RoleId"]
            role["RoleName"].should.equal("my-role-no-path-name")
            role["Path"].should.equal("/")

    instance_profile_responses = iam.list_instance_profiles()["InstanceProfiles"]
    instance_profile_responses.should.have.length_of(2)
    instance_profile_names = []

    for instance_profile_response in instance_profile_responses:
        instance_profile = iam.get_instance_profile(
            InstanceProfileName=instance_profile_response["InstanceProfileName"]
        )["InstanceProfile"]
        instance_profile_names.append(instance_profile["InstanceProfileName"])
        instance_profile["InstanceProfileName"].should.contain("my-instance-profile")
        if "with-path" in instance_profile["InstanceProfileName"]:
            instance_profile["Path"].should.equal("my-path")
            instance_profile["Roles"][0]["RoleId"].should.equal(
                role_name_to_id["with-path"]
            )
        else:
            instance_profile["InstanceProfileName"].should.contain("no-path")
            instance_profile["Roles"][0]["RoleId"].should.equal(
                role_name_to_id["no-path"]
            )
            instance_profile["Path"].should.equal("/")

    autoscale = boto3.client("autoscaling", region_name="us-west-1")
    launch_config = autoscale.describe_launch_configurations()["LaunchConfigurations"][
        0
    ]
    launch_config.should.have.key("IamInstanceProfile").should.contain(
        "my-instance-profile-with-path"
    )

    resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]
    instance_profile_resources = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::IAM::InstanceProfile"
    ]
    {ip["PhysicalResourceId"] for ip in instance_profile_resources}.should.equal(
        set(instance_profile_names)
    )

    role_resources = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::IAM::Role"
    ]
    {r["PhysicalResourceId"] for r in role_resources}.should.equal(set(role_names))
