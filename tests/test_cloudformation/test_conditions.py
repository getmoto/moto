from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from tests import aws_verified

conditional_output_conditional_value = """
Outputs:
  roleArn:
    Condition: RoleCondition
    Value: !GetAtt role.Arn

Parameters:
  roleName:
    Type: String
    Description: Predefined role name

Conditions:
  RoleCondition: !Equals [ !Ref roleName, "myrole" ]

Resources:
  role:
    Condition: RoleCondition
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


@pytest.mark.aws_verified
@aws_verified
def test_conditional_output_conditional_value():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    param = [{"ParameterKey": "roleName", "ParameterValue": "myrole"}]
    name = f"stack{str(uuid4())[0:6]}"
    cf.create_stack(
        StackName=name,
        TemplateBody=conditional_output_conditional_value,
        Parameters=param,
        Capabilities=["CAPABILITY_IAM"],
    )
    waiter = cf.get_waiter("stack_create_complete")
    waiter.wait(StackName=name)

    stack = cf.describe_stacks(StackName=name)["Stacks"][0]
    assert stack["Outputs"][0]["OutputKey"] == "roleArn"

    cf.delete_stack(StackName=name)

    # verify role does not exist with different name
    param = [{"ParameterKey": "roleName", "ParameterValue": "diffname"}]
    cf.create_stack(
        StackName=f"{name}2",
        TemplateBody=conditional_output_conditional_value,
        Parameters=param,
        Capabilities=["CAPABILITY_IAM"],
    )
    waiter = cf.get_waiter("stack_create_complete")
    waiter.wait(StackName=f"{name}2")
    stack = cf.describe_stacks()["Stacks"][0]
    assert "Outputs" not in stack

    cf.delete_stack(StackName=f"{name}2")


permanent_output_conditional_value = """
Outputs:
  roleArn:
    Value: !GetAtt role.Arn

Parameters:
  roleName:
    Type: String
    Description: Predefined role name

Conditions:
  RoleCondition: !Equals [ !Ref roleName, "myrole" ]

Resources:
  role:
    Condition: RoleCondition
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


@pytest.mark.aws_verified
@aws_verified
def test_permanent_output_conditional_value():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    param = [{"ParameterKey": "roleName", "ParameterValue": "myrole"}]

    name = f"stack{str(uuid4())[0:6]}"
    cf.create_stack(
        StackName=name,
        TemplateBody=permanent_output_conditional_value,
        Parameters=param,
        Capabilities=["CAPABILITY_IAM"],
    )
    waiter = cf.get_waiter("stack_create_complete")
    waiter.wait(StackName=name)

    # Works - because role exists
    stack = cf.describe_stacks(StackName=name)["Stacks"][0]
    assert stack["Outputs"][0]["OutputKey"] == "roleArn"

    cf.delete_stack(StackName=name)

    # Role does not exist with different name
    # So we can't get the Output either
    param = [{"ParameterKey": "roleName", "ParameterValue": "diffname"}]
    with pytest.raises(ClientError) as exc:
        cf.create_stack(
            StackName=f"{name}2",
            TemplateBody=permanent_output_conditional_value,
            Parameters=param,
            Capabilities=["CAPABILITY_IAM"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Unresolved resource dependencies [role] in the Outputs block of the template"
    )


conditional_output_of_permanent_value = """
Outputs:
  roleArn:
    Condition: RoleCondition
    Value: !GetAtt role.Arn

Parameters:
  roleName:
    Type: String
    Description: Predefined role name

Conditions:
  RoleCondition: !Equals [ !Ref roleName, "myrole" ]

Resources:
  role:
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


@pytest.mark.aws_verified
@aws_verified
def test_conditional_output_of_permanent_value():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    param = [{"ParameterKey": "roleName", "ParameterValue": "myrole"}]

    name = f"stack{str(uuid4())[0:6]}"
    cf.create_stack(
        StackName=name,
        TemplateBody=conditional_output_of_permanent_value,
        Parameters=param,
        Capabilities=["CAPABILITY_IAM"],
    )
    waiter = cf.get_waiter("stack_create_complete")
    waiter.wait(StackName=name)

    stack = cf.describe_stacks(StackName=name)["Stacks"][0]
    assert stack["Outputs"][0]["OutputKey"] == "roleArn"

    cf.delete_stack(StackName=name)

    # verify role does not exist with different name
    param = [{"ParameterKey": "roleName", "ParameterValue": "diffname"}]
    cf.create_stack(
        StackName=f"{name}2",
        TemplateBody=conditional_output_of_permanent_value,
        Parameters=param,
        Capabilities=["CAPABILITY_IAM"],
    )
    waiter = cf.get_waiter("stack_create_complete")
    waiter.wait(StackName=f"{name}2")
    stack = cf.describe_stacks(StackName=f"{name}2")["Stacks"][0]
    # The Role does exist
    # But Output is conditional, and just doesn't return anything
    assert "Outputs" not in stack

    cf.delete_stack(StackName=f"{name}2")
