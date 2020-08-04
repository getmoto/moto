import boto3
import yaml
import sure  # noqa

from nose.tools import assert_raises
from botocore.exceptions import ClientError

from moto import mock_iam, mock_cloudformation, mock_s3

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

    iam_client = boto3.client("iam")
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

    iam_client = boto3.client("iam")
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
    Type: AWS::IAM::User
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

    iam_client = boto3.client("iam")
    user = iam_client.get_user(UserName=user_name)

    cf_client.delete_stack(StackName=stack_name)

    with assert_raises(ClientError) as e:
        user = iam_client.get_user(UserName=user_name)
    e.exception.response["Error"]["Code"].should.equal("NoSuchEntity")


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

    iam_client = boto3.client("iam")
    user_description = iam_client.get_user(UserName=output_user_name)["User"]
    output_user_arn.should.equal(user_description["Arn"])


# AWS::IAM::Policy Tests
@mock_s3
@mock_iam
@mock_cloudformation
def test_iam_cloudformation_create_user_policy():
    iam_client = boto3.client("iam")
    user_name = "MyUser"
    iam_client.create_user(UserName=user_name)

    s3_client = boto3.client("s3")
    bucket_name = "my-bucket"
    bucket = s3_client.create_bucket(Bucket=bucket_name)
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
    iam_client = boto3.client("iam")
    user_name_1 = "MyUser1"
    iam_client.create_user(UserName=user_name_1)
    user_name_2 = "MyUser2"
    iam_client.create_user(UserName=user_name_2)

    s3_client = boto3.client("s3")
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
    iam_client = boto3.client("iam")
    user_name = "MyUser"
    iam_client.create_user(UserName=user_name)

    s3_client = boto3.client("s3")
    bucket_name = "my-bucket"
    bucket = s3_client.create_bucket(Bucket=bucket_name)
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
    iam_client = boto3.client("iam")
    role_name = "MyRole"
    iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

    s3_client = boto3.client("s3")
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
    iam_client = boto3.client("iam")
    role_name_1 = "MyRole1"
    iam_client.create_role(RoleName=role_name_1, AssumeRolePolicyDocument="{}")
    role_name_2 = "MyRole2"
    iam_client.create_role(RoleName=role_name_2, AssumeRolePolicyDocument="{}")

    s3_client = boto3.client("s3")
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
    iam_client = boto3.client("iam")
    role_name = "MyRole"
    iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

    s3_client = boto3.client("s3")
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
    iam_client = boto3.client("iam")
    group_name = "MyGroup"
    iam_client.create_group(GroupName=group_name)

    s3_client = boto3.client("s3")
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
    iam_client = boto3.client("iam")
    group_name_1 = "MyGroup1"
    iam_client.create_group(GroupName=group_name_1)
    group_name_2 = "MyGroup2"
    iam_client.create_group(GroupName=group_name_2)

    s3_client = boto3.client("s3")
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
    iam_client = boto3.client("iam")
    group_name = "MyGroup"
    iam_client.create_group(GroupName=group_name)

    s3_client = boto3.client("s3")
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
