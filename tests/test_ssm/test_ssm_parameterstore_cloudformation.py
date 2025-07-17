import json

import boto3
import botocore.exceptions
import pytest

from moto import mock_aws


@mock_aws
def test_cloudformation_lifecycle():
    ssm_param_name = "test"
    ssm_param_value = "initial value"
    stack_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Test Stack",
        "Resources": {
            "SSMParameter": {
                "Type": "AWS::SSM::Parameter",
                "Properties": {
                    "Name": ssm_param_name,
                    "Type": "String",
                    "Value": ssm_param_value,
                },
            }
        },
    }

    cloudformation_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_template_str = json.dumps(stack_template)

    cloudformation_client.create_stack(
        StackName="test_stack",
        TemplateBody=stack_template_str,
        Capabilities=("CAPABILITY_IAM",),
    )

    client = boto3.client("ssm", region_name="us-east-1")
    resp = client.get_parameter(Name=ssm_param_name)["Parameter"]
    resp_param_name = resp["Name"]
    resp_param_value = resp["Value"]

    assert resp_param_name == ssm_param_name
    assert resp_param_value == ssm_param_value

    # Update the stack template with new value

    new_ssm_param_value = "updated value"

    stack_template["Resources"]["SSMParameter"]["Properties"]["Value"] = (
        new_ssm_param_value
    )
    stack_template_str = json.dumps(stack_template)
    cloudformation_client.update_stack(
        StackName="test_stack",
        TemplateBody=stack_template_str,
        Capabilities=("CAPABILITY_IAM",),
    )

    resp = client.get_parameter(Name=ssm_param_name)["Parameter"]
    resp_param_name = resp["Name"]
    resp_param_value = resp["Value"]

    assert resp_param_name == ssm_param_name
    assert resp_param_value == new_ssm_param_value

    # Stack deletion

    cloudformation_client.delete_stack(StackName="test_stack")
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        resp = client.get_parameter(Name=ssm_param_name)["Parameter"]
    err = exc.value.response["Error"]
    assert err["Code"] == "ParameterNotFound"
    assert err["Message"] == f"Parameter {ssm_param_name} not found."


@mock_aws
def test_cloudformation_lifecycle_with_parsing():
    ssm_param_name = "test"
    ssm_param_value = "initial value"
    stack_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Test Stack",
        "Parameters": {
            "Name": {"Type": "String", "Default": ssm_param_name},
            "Value": {"Type": "String", "Default": ssm_param_value},
        },
        "Resources": {
            "SSMParameter": {
                "Type": "AWS::SSM::Parameter",
                "Properties": {
                    "Name": {"Fn::Sub": "${Name}"},
                    "Type": "String",
                    "Value": {"Ref": "Value"},
                },
            }
        },
    }

    cloudformation_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_template_str = json.dumps(stack_template)

    cloudformation_client.create_stack(
        StackName="test_stack",
        TemplateBody=stack_template_str,
        Capabilities=("CAPABILITY_IAM",),
    )

    cloudformation_client.describe_stack_resources(StackName="test_stack")

    client = boto3.client("ssm", region_name="us-east-1")
    resp = client.get_parameter(Name=ssm_param_name)
    resp_param = resp.get("Parameter")
    resp_param_name = resp_param["Name"]
    resp_param_value = resp_param["Value"]

    assert resp_param_name == ssm_param_name
    assert resp_param_value == ssm_param_value

    # Update the stack with new value

    new_ssm_param_value = "updated value"

    stack_template_str = json.dumps(stack_template)
    cloudformation_client.update_stack(
        StackName="test_stack",
        TemplateBody=stack_template_str,
        Capabilities=("CAPABILITY_IAM",),
        Parameters=[{"ParameterKey": "Value", "ParameterValue": new_ssm_param_value}],
    )

    resp = client.get_parameter(Name=ssm_param_name)["Parameter"]
    resp_param_name = resp["Name"]
    resp_param_value = resp["Value"]

    assert resp_param_name == ssm_param_name
    assert resp_param_value == new_ssm_param_value

    # Stack deletion

    cloudformation_client.delete_stack(StackName="test_stack")
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        resp = client.get_parameter(Name=ssm_param_name)["Parameter"]
    err = exc.value.response["Error"]
    assert err["Code"] == "ParameterNotFound"
    assert err["Message"] == f"Parameter {ssm_param_name} not found."
