import copy
import json
from collections import OrderedDict
from datetime import datetime, timedelta
import os
import pytz

import boto3
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import

import pytest
from unittest import SkipTest

from moto import (
    mock_cloudformation,
    mock_dynamodb2,
    mock_s3,
    mock_sns,
    mock_sqs,
    mock_ec2,
    mock_iam,
    mock_lambda,
)
from moto import settings
from moto.core import ACCOUNT_ID
from moto.cloudformation import cloudformation_backends
from .test_cloudformation_stack_crud import dummy_template_json2, dummy_template_json4

from tests import EXAMPLE_AMI_ID

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {
        "EC2Instance1": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": EXAMPLE_AMI_ID,
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

dummy_template3 = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 3",
    "Resources": {
        "VPC": {"Properties": {"CidrBlock": "192.168.0.0/16"}, "Type": "AWS::EC2::VPC"}
    },
}


dummy_template_with_parameters = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "A simple CloudFormation template",
    "Resources": {
        "Bucket": {
            "Type": "AWS::S3::Bucket",
            "Properties": {"BucketName": {"Ref": "Name"}},
        }
    },
    "Parameters": {
        "Name": {"Type": "String", "Default": "SomeValue"},
        "Another": {
            "Type": "String",
            "Default": "A",
            "AllowedValues": ["A", "B"],
            "Description": "Chose A or B",
        },
    },
}


dummy_template_yaml = """---
AWSTemplateFormatVersion: 2010-09-09
Description: Stack1 with yaml template
Resources:
  EC2Instance1:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-03cf127a
      KeyName: dummy
      InstanceType: t2.micro
      Tags:
        - Key: Description
          Value: Test tag
        - Key: Name
          Value: Name tag for tests
    Parameters:
"""

dummy_template_yaml_with_short_form_func = """---
AWSTemplateFormatVersion: 2010-09-09
Description: Stack1 with yaml template
Resources:
  EC2Instance1:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-03cf127a
      KeyName: !Join [ ":", [ du, m, my ] ]
      InstanceType: t2.micro
      Tags:
        - Key: Description
          Value: Test tag
        - Key: Name
          Value: Name tag for tests
"""

dummy_yaml_template_with_equals = """---
AWSTemplateFormatVersion: 2010-09-09
Description: Stack with yaml template
Conditions:
  maybe:
    Fn::Equals: [!Ref enabled, true]
Parameters:
  enabled:
    Type: String
    AllowedValues:
     - true
     - false
Resources:
  VPC1:
    Type: AWS::EC2::VPC
    Condition: maybe
    Properties:
      CidrBlock: 192.168.0.0/16
"""

dummy_template_yaml_with_ref = """---
AWSTemplateFormatVersion: 2010-09-09
Description: Stack1 with yaml template
Parameters:
  TagDescription:
    Type: String
  TagName:
    Type: String

Resources:
  EC2Instance1:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-03cf127a
      KeyName: dummy
      InstanceType: t2.micro
      Tags:
        - Key: Description
          Value:
            Ref: TagDescription
        - Key: Name
          Value: !Ref TagName
"""

dummy_empty_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {},
    "Resources": {},
}

dummy_parametrized_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "KeyName": {"Description": "A template parameter", "Type": "String"}
    },
    "Resources": {},
}

dummy_update_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "KeyName": {
            "Description": "Name of an existing EC2 KeyPair",
            "Type": "AWS::EC2::KeyPair::KeyName",
            "ConstraintDescription": "must be the name of an existing EC2 KeyPair.",
        }
    },
    "Resources": {
        "Instance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {"ImageId": EXAMPLE_AMI_ID},
        }
    },
}

dummy_output_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {
        "Instance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {"ImageId": EXAMPLE_AMI_ID},
        }
    },
    "Outputs": {
        "StackVPC": {
            "Description": "The ID of the VPC",
            "Value": "VPCID",
            "Export": {"Name": "My VPC ID"},
        }
    },
}

dummy_import_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::ImportValue": "My VPC ID"},
                "VisibilityTimeout": 60,
            },
        }
    },
}

dummy_redrive_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "MainQueue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": "mainqueue.fifo",
                "FifoQueue": True,
                "ContentBasedDeduplication": False,
                "RedrivePolicy": {
                    "deadLetterTargetArn": {"Fn::GetAtt": ["DeadLetterQueue", "Arn"]},
                    "maxReceiveCount": 5,
                },
            },
        },
        "DeadLetterQueue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {"FifoQueue": True},
        },
    },
}

dummy_template_special_chars_in_description = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1 <env>",
    "Resources": {
        "EC2Instance1": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": EXAMPLE_AMI_ID,
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

dummy_unknown_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {
        "UnknownResource": {"Type": "AWS::Cloud9::EnvironmentEC2", "Properties": {}},
    },
}

dummy_template_json = json.dumps(dummy_template)
dummy_template_special_chars_in_description_json = json.dumps(
    dummy_template_special_chars_in_description
)
dummy_empty_template_json = json.dumps(dummy_empty_template)
dummy_parametrized_template_json = json.dumps(dummy_parametrized_template)
dummy_update_template_json = json.dumps(dummy_update_template)
dummy_output_template_json = json.dumps(dummy_output_template)
dummy_import_template_json = json.dumps(dummy_import_template)
dummy_redrive_template_json = json.dumps(dummy_redrive_template)
dummy_unknown_template_json = json.dumps(dummy_unknown_template)


@mock_cloudformation
@mock_ec2
def test_create_stack():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    stack = cf_conn.describe_stacks()["Stacks"][0]
    stack.should.have.key("StackName").equal("test_stack")

    template = cf_conn.get_template(StackName="test_stack")["TemplateBody"]
    template.should.equal(dummy_template)


@mock_cloudformation
@mock_ec2
def test_boto3_describe_stack_instances():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    cf_conn.create_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
    )
    usw2_instance = cf_conn.describe_stack_instance(
        StackSetName="test_stack_set",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-west-2",
    )
    use1_instance = cf_conn.describe_stack_instance(
        StackSetName="test_stack_set",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-east-1",
    )

    usw2_instance["StackInstance"].should.have.key("Region").which.should.equal(
        "us-west-2"
    )
    usw2_instance["StackInstance"].should.have.key("Account").which.should.equal(
        ACCOUNT_ID
    )
    use1_instance["StackInstance"].should.have.key("Region").which.should.equal(
        "us-east-1"
    )
    use1_instance["StackInstance"].should.have.key("Account").which.should.equal(
        ACCOUNT_ID
    )


@mock_cloudformation
def test_boto3_list_stacksets_length():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    cf_conn.create_stack_set(
        StackSetName="test_stack_set2", TemplateBody=dummy_template_yaml
    )
    stacksets = cf_conn.list_stack_sets()
    stacksets.should.have.length_of(2)


@mock_cloudformation
def test_boto3_filter_stacks():
    conn = boto3.client("cloudformation", region_name="us-east-1")
    conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)
    conn.create_stack(StackName="test_stack2", TemplateBody=dummy_template_json)
    conn.update_stack(StackName="test_stack", TemplateBody=dummy_template_json2)

    stacks = conn.list_stacks(StackStatusFilter=["CREATE_COMPLETE"])
    stacks.get("StackSummaries").should.have.length_of(1)
    stacks = conn.list_stacks(StackStatusFilter=["UPDATE_COMPLETE"])
    stacks.get("StackSummaries").should.have.length_of(1)


@mock_cloudformation
def test_boto3_list_stacksets_contents():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    stacksets = cf_conn.list_stack_sets()
    stacksets["Summaries"][0].should.have.key("StackSetName").which.should.equal(
        "test_stack_set"
    )
    stacksets["Summaries"][0].should.have.key("Status").which.should.equal("ACTIVE")


@mock_cloudformation
def test_boto3_stop_stack_set_operation():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    cf_conn.create_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-1", "us-west-2"],
    )
    operation_id = cf_conn.list_stack_set_operations(StackSetName="test_stack_set")[
        "Summaries"
    ][-1]["OperationId"]
    cf_conn.stop_stack_set_operation(
        StackSetName="test_stack_set", OperationId=operation_id
    )
    list_operation = cf_conn.list_stack_set_operations(StackSetName="test_stack_set")
    list_operation["Summaries"][-1]["Status"].should.equal("STOPPED")


@mock_cloudformation
def test_boto3_describe_stack_set_operation():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    cf_conn.create_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-1", "us-west-2"],
    )
    operation_id = cf_conn.list_stack_set_operations(StackSetName="test_stack_set")[
        "Summaries"
    ][-1]["OperationId"]
    cf_conn.stop_stack_set_operation(
        StackSetName="test_stack_set", OperationId=operation_id
    )
    response = cf_conn.describe_stack_set_operation(
        StackSetName="test_stack_set", OperationId=operation_id
    )

    response["StackSetOperation"]["Status"].should.equal("STOPPED")
    response["StackSetOperation"]["Action"].should.equal("CREATE")
    with pytest.raises(ClientError) as exp:
        cf_conn.describe_stack_set_operation(
            StackSetName="test_stack_set", OperationId="non_existing_operation"
        )
    exp_err = exp.value.response.get("Error")
    exp_metadata = exp.value.response.get("ResponseMetadata")

    exp_err.get("Code").should.match(r"ValidationError")
    exp_err.get("Message").should.match(
        r"Stack with id non_existing_operation does not exist"
    )
    exp_metadata.get("HTTPStatusCode").should.equal(400)


@mock_cloudformation
def test_boto3_list_stack_set_operation_results():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    cf_conn.create_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-1", "us-west-2"],
    )
    operation_id = cf_conn.list_stack_set_operations(StackSetName="test_stack_set")[
        "Summaries"
    ][-1]["OperationId"]

    cf_conn.stop_stack_set_operation(
        StackSetName="test_stack_set", OperationId=operation_id
    )
    response = cf_conn.list_stack_set_operation_results(
        StackSetName="test_stack_set", OperationId=operation_id
    )

    response["Summaries"].should.have.length_of(3)
    response["Summaries"][0].should.have.key("Account").which.should.equal(ACCOUNT_ID)
    response["Summaries"][1].should.have.key("Status").which.should.equal("STOPPED")


@mock_cloudformation
def test_boto3_update_stack_instances():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    param = [
        {"ParameterKey": "SomeParam", "ParameterValue": "StackSetValue"},
        {"ParameterKey": "AnotherParam", "ParameterValue": "StackSetValue2"},
    ]
    param_overrides = [
        {"ParameterKey": "SomeParam", "ParameterValue": "OverrideValue"},
        {"ParameterKey": "AnotherParam", "ParameterValue": "OverrideValue2"},
    ]
    cf_conn.create_stack_set(
        StackSetName="test_stack_set",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param,
    )
    cf_conn.create_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-1", "us-west-2"],
    )
    cf_conn.update_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-west-1", "us-west-2"],
        ParameterOverrides=param_overrides,
    )
    usw2_instance = cf_conn.describe_stack_instance(
        StackSetName="test_stack_set",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-west-2",
    )
    usw1_instance = cf_conn.describe_stack_instance(
        StackSetName="test_stack_set",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-west-1",
    )
    use1_instance = cf_conn.describe_stack_instance(
        StackSetName="test_stack_set",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-east-1",
    )

    usw2_instance["StackInstance"]["ParameterOverrides"][0][
        "ParameterKey"
    ].should.equal(param_overrides[0]["ParameterKey"])
    usw2_instance["StackInstance"]["ParameterOverrides"][0][
        "ParameterValue"
    ].should.equal(param_overrides[0]["ParameterValue"])
    usw2_instance["StackInstance"]["ParameterOverrides"][1][
        "ParameterKey"
    ].should.equal(param_overrides[1]["ParameterKey"])
    usw2_instance["StackInstance"]["ParameterOverrides"][1][
        "ParameterValue"
    ].should.equal(param_overrides[1]["ParameterValue"])

    usw1_instance["StackInstance"]["ParameterOverrides"][0][
        "ParameterKey"
    ].should.equal(param_overrides[0]["ParameterKey"])
    usw1_instance["StackInstance"]["ParameterOverrides"][0][
        "ParameterValue"
    ].should.equal(param_overrides[0]["ParameterValue"])
    usw1_instance["StackInstance"]["ParameterOverrides"][1][
        "ParameterKey"
    ].should.equal(param_overrides[1]["ParameterKey"])
    usw1_instance["StackInstance"]["ParameterOverrides"][1][
        "ParameterValue"
    ].should.equal(param_overrides[1]["ParameterValue"])

    use1_instance["StackInstance"]["ParameterOverrides"].should.be.empty


@mock_cloudformation
def test_boto3_delete_stack_instances():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    cf_conn.create_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
    )

    cf_conn.delete_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1"],
        RetainStacks=False,
    )

    cf_conn.list_stack_instances(StackSetName="test_stack_set")[
        "Summaries"
    ].should.have.length_of(1)
    cf_conn.list_stack_instances(StackSetName="test_stack_set")["Summaries"][0][
        "Region"
    ].should.equal("us-west-2")


@mock_cloudformation
def test_boto3_create_stack_instances():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    cf_conn.create_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
    )

    cf_conn.list_stack_instances(StackSetName="test_stack_set")[
        "Summaries"
    ].should.have.length_of(2)
    cf_conn.list_stack_instances(StackSetName="test_stack_set")["Summaries"][0][
        "Account"
    ].should.equal(ACCOUNT_ID)


@mock_cloudformation
def test_boto3_create_stack_instances_with_param_overrides():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    param = [
        {"ParameterKey": "TagDescription", "ParameterValue": "StackSetValue"},
        {"ParameterKey": "TagName", "ParameterValue": "StackSetValue2"},
    ]
    param_overrides = [
        {"ParameterKey": "TagDescription", "ParameterValue": "OverrideValue"},
        {"ParameterKey": "TagName", "ParameterValue": "OverrideValue2"},
    ]
    cf_conn.create_stack_set(
        StackSetName="test_stack_set",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param,
    )
    cf_conn.create_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
        ParameterOverrides=param_overrides,
    )
    usw2_instance = cf_conn.describe_stack_instance(
        StackSetName="test_stack_set",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-west-2",
    )

    usw2_instance["StackInstance"]["ParameterOverrides"][0][
        "ParameterKey"
    ].should.equal(param_overrides[0]["ParameterKey"])
    usw2_instance["StackInstance"]["ParameterOverrides"][1][
        "ParameterKey"
    ].should.equal(param_overrides[1]["ParameterKey"])
    usw2_instance["StackInstance"]["ParameterOverrides"][0][
        "ParameterValue"
    ].should.equal(param_overrides[0]["ParameterValue"])
    usw2_instance["StackInstance"]["ParameterOverrides"][1][
        "ParameterValue"
    ].should.equal(param_overrides[1]["ParameterValue"])


@mock_cloudformation
def test_update_stack_set():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    param = [
        {"ParameterKey": "TagDescription", "ParameterValue": "StackSetValue"},
        {"ParameterKey": "TagName", "ParameterValue": "StackSetValue2"},
    ]
    param_overrides = [
        {"ParameterKey": "TagDescription", "ParameterValue": "OverrideValue"},
        {"ParameterKey": "TagName", "ParameterValue": "OverrideValue2"},
    ]
    cf_conn.create_stack_set(
        StackSetName="test_stack_set",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param,
    )
    cf_conn.update_stack_set(
        StackSetName="test_stack_set",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param_overrides,
    )
    stackset = cf_conn.describe_stack_set(StackSetName="test_stack_set")

    stackset["StackSet"]["Parameters"][0]["ParameterValue"].should.equal(
        param_overrides[0]["ParameterValue"]
    )
    stackset["StackSet"]["Parameters"][1]["ParameterValue"].should.equal(
        param_overrides[1]["ParameterValue"]
    )
    stackset["StackSet"]["Parameters"][0]["ParameterKey"].should.equal(
        param_overrides[0]["ParameterKey"]
    )
    stackset["StackSet"]["Parameters"][1]["ParameterKey"].should.equal(
        param_overrides[1]["ParameterKey"]
    )


@mock_cloudformation
def test_update_stack_set_with_previous_value():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    param = [
        {"ParameterKey": "TagDescription", "ParameterValue": "StackSetValue"},
        {"ParameterKey": "TagName", "ParameterValue": "StackSetValue2"},
    ]
    param_overrides = [
        {"ParameterKey": "TagDescription", "ParameterValue": "OverrideValue"},
        {"ParameterKey": "TagName", "UsePreviousValue": True},
    ]
    cf_conn.create_stack_set(
        StackSetName="test_stack_set",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param,
    )
    cf_conn.update_stack_set(
        StackSetName="test_stack_set",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param_overrides,
    )
    stackset = cf_conn.describe_stack_set(StackSetName="test_stack_set")

    stackset["StackSet"]["Parameters"][0]["ParameterValue"].should.equal(
        param_overrides[0]["ParameterValue"]
    )
    stackset["StackSet"]["Parameters"][1]["ParameterValue"].should.equal(
        param[1]["ParameterValue"]
    )
    stackset["StackSet"]["Parameters"][0]["ParameterKey"].should.equal(
        param_overrides[0]["ParameterKey"]
    )
    stackset["StackSet"]["Parameters"][1]["ParameterKey"].should.equal(
        param_overrides[1]["ParameterKey"]
    )


@mock_cloudformation
def test_boto3_list_stack_set_operations():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    cf_conn.create_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
    )
    cf_conn.update_stack_instances(
        StackSetName="test_stack_set",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
    )

    list_operation = cf_conn.list_stack_set_operations(StackSetName="test_stack_set")
    list_operation["Summaries"].should.have.length_of(2)
    list_operation["Summaries"][-1]["Action"].should.equal("UPDATE")


@mock_cloudformation
def test_boto3_bad_list_stack_resources():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    with pytest.raises(ClientError):
        cf_conn.list_stack_resources(StackName="test_stack_set")


@mock_cloudformation
def test_boto3_delete_stack_set_by_name():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    cf_conn.delete_stack_set(StackSetName="test_stack_set")

    cf_conn.describe_stack_set(StackSetName="test_stack_set")["StackSet"][
        "Status"
    ].should.equal("DELETED")


@mock_cloudformation
def test_boto3_delete_stack_set_by_id():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    response = cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )
    stack_set_id = response["StackSetId"]
    cf_conn.delete_stack_set(StackSetName=stack_set_id)

    cf_conn.describe_stack_set(StackSetName="test_stack_set")["StackSet"][
        "Status"
    ].should.equal("DELETED")


@mock_cloudformation
def test_boto3_create_stack_set():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    response = cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_json
    )

    cf_conn.describe_stack_set(StackSetName="test_stack_set")["StackSet"][
        "TemplateBody"
    ].should.equal(dummy_template_json)
    response["StackSetId"].should_not.be.empty


@mock_cloudformation
def test_boto3_create_stack_set_with_yaml():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack_set(
        StackSetName="test_stack_set", TemplateBody=dummy_template_yaml
    )

    cf_conn.describe_stack_set(StackSetName="test_stack_set")["StackSet"][
        "TemplateBody"
    ].should.equal(dummy_template_yaml)


@mock_cloudformation
@mock_s3
def test_create_stack_set_from_s3_url():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3_conn = boto3.resource("s3", region_name="us-east-1")
    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=dummy_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )

    cf_conn = boto3.client("cloudformation", region_name="us-west-1")
    cf_conn.create_stack_set(StackSetName="stack_from_url", TemplateURL=key_url)
    cf_conn.describe_stack_set(StackSetName="stack_from_url")["StackSet"][
        "TemplateBody"
    ].should.equal(dummy_template_json)


@mock_cloudformation
def test_boto3_create_stack_set_with_ref_yaml():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    params = [
        {"ParameterKey": "TagDescription", "ParameterValue": "desc_ref"},
        {"ParameterKey": "TagName", "ParameterValue": "name_ref"},
    ]
    cf_conn.create_stack_set(
        StackSetName="test_stack",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=params,
    )

    cf_conn.describe_stack_set(StackSetName="test_stack")["StackSet"][
        "TemplateBody"
    ].should.equal(dummy_template_yaml_with_ref)


@mock_cloudformation
def test_boto3_describe_stack_set_params():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    params = [
        {"ParameterKey": "TagDescription", "ParameterValue": "desc_ref"},
        {"ParameterKey": "TagName", "ParameterValue": "name_ref"},
    ]
    cf_conn.create_stack_set(
        StackSetName="test_stack",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=params,
    )

    cf_conn.describe_stack_set(StackSetName="test_stack")["StackSet"][
        "Parameters"
    ].should.equal(params)


@mock_cloudformation
def test_boto3_describe_stack_set_by_id():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    response = cf_conn.create_stack_set(
        StackSetName="test_stack", TemplateBody=dummy_template_json,
    )

    stack_set_id = response["StackSetId"]
    cf_conn.describe_stack_set(StackSetName=stack_set_id)["StackSet"][
        "TemplateBody"
    ].should.equal(dummy_template_json)


@mock_cloudformation
def test_boto3_create_stack():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    cf_conn.get_template(StackName="test_stack")["TemplateBody"].should.equal(
        json.loads(dummy_template_json, object_pairs_hook=OrderedDict)
    )


@mock_cloudformation
def test_boto3_create_stack_fail_missing_parameter():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    with pytest.raises(ClientError, match="Missing parameter KeyName"):

        cf_conn.create_stack(
            StackName="test_stack", TemplateBody=dummy_parametrized_template_json
        )


@mock_cloudformation
def test_boto3_create_stack_s3_long_name():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    stack_name = "MyLongStackName01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012"

    template = '{"Resources":{"HelloBucket":{"Type":"AWS::S3::Bucket"}}}'

    cf_conn.create_stack(StackName=stack_name, TemplateBody=template)

    cf_conn.get_template(StackName=stack_name)["TemplateBody"].should.equal(
        json.loads(template, object_pairs_hook=OrderedDict)
    )
    provisioned_resource = cf_conn.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    provisioned_bucket_name = provisioned_resource["PhysicalResourceId"]
    len(provisioned_bucket_name).should.be.lower_than(64)
    logical_name_lower_case = provisioned_resource["LogicalResourceId"].lower()
    bucket_name_stack_name_prefix = provisioned_bucket_name[
        : provisioned_bucket_name.index("-" + logical_name_lower_case)
    ]
    stack_name.lower().should.contain(bucket_name_stack_name_prefix)


@mock_cloudformation
def test_boto3_create_stack_with_yaml():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_yaml)

    cf_conn.get_template(StackName="test_stack")["TemplateBody"].should.equal(
        dummy_template_yaml
    )


@mock_cloudformation
def test_boto3_create_stack_with_short_form_func_yaml():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(
        StackName="test_stack", TemplateBody=dummy_template_yaml_with_short_form_func
    )

    cf_conn.get_template(StackName="test_stack")["TemplateBody"].should.equal(
        dummy_template_yaml_with_short_form_func
    )


@mock_s3
@mock_cloudformation
def test_get_template_summary():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3_conn = boto3.resource("s3", region_name="us-east-1")

    # json template
    conn = boto3.client("cloudformation", region_name="us-east-1")
    result = conn.get_template_summary(TemplateBody=json.dumps(dummy_template3))
    result["ResourceTypes"].should.equal(["AWS::EC2::VPC"])
    result["Version"].should.equal("2010-09-09")
    result["Description"].should.equal("Stack 3")
    result["Parameters"].should.equal([])

    # existing stack
    conn.create_stack(StackName="test_stack", TemplateBody=json.dumps(dummy_template3))
    result = conn.get_template_summary(StackName="test_stack")
    result["ResourceTypes"].should.equal(["AWS::EC2::VPC"])
    result["Version"].should.equal("2010-09-09")
    result["Description"].should.equal("Stack 3")
    result["Parameters"].should.equal([])

    # json template from s3
    s3_conn.create_bucket(Bucket="foobar")
    s3_conn.Object("foobar", "template-key").put(Body=json.dumps(dummy_template3))
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )
    conn.create_stack(StackName="stack_from_url", TemplateURL=key_url)
    result = conn.get_template_summary(TemplateURL=key_url)
    result["ResourceTypes"].should.equal(["AWS::EC2::VPC"])
    result["Version"].should.equal("2010-09-09")
    result["Description"].should.equal("Stack 3")

    # yaml template
    conn = boto3.client("cloudformation", region_name="us-east-1")
    result = conn.get_template_summary(TemplateBody=dummy_template_yaml)
    result["ResourceTypes"].should.equal(["AWS::EC2::Instance"])
    result["Version"].should.equal("2010-09-09")
    result["Description"].should.equal("Stack1 with yaml template")


@mock_cloudformation
def test_get_template_summary_for_stack_created_by_changeset_execution():
    conn = boto3.client("cloudformation", region_name="us-east-1")
    conn.create_change_set(
        StackName="stack_from_changeset",
        TemplateBody=json.dumps(dummy_template3),
        ChangeSetName="test_changeset",
        ChangeSetType="CREATE",
    )
    with pytest.raises(
        ClientError,
        match="GetTemplateSummary cannot be called on REVIEW_IN_PROGRESS stacks",
    ):
        conn.get_template_summary(StackName="stack_from_changeset")
    conn.execute_change_set(ChangeSetName="test_changeset")
    result = conn.get_template_summary(StackName="stack_from_changeset")
    result["ResourceTypes"].should.equal(["AWS::EC2::VPC"])
    result["Version"].should.equal("2010-09-09")
    result["Description"].should.equal("Stack 3")


@mock_s3
@mock_cloudformation
def test_get_template_summary_for_template_containing_parameters():
    conn = boto3.client("cloudformation", region_name="us-east-1")
    conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(dummy_template_with_parameters)
    )
    result = conn.get_template_summary(StackName="test_stack")
    result.should.match_dict(
        {
            "Parameters": [
                {
                    "ParameterKey": "Name",
                    "DefaultValue": "SomeValue",
                    "ParameterType": "String",
                    "NoEcho": False,
                    "Description": "",
                    "ParameterConstraints": {},
                },
                {
                    "ParameterKey": "Another",
                    "DefaultValue": "A",
                    "ParameterType": "String",
                    "NoEcho": False,
                    "Description": "Chose A or B",
                    "ParameterConstraints": {"AllowedValues": ["A", "B"]},
                },
            ],
            "Description": "A simple CloudFormation template",
            "ResourceTypes": ["AWS::S3::Bucket"],
            "Version": "2010-09-09",
            # TODO: get_template_summary should support ResourceIdentifierSummaries
            # "ResourceIdentifierSummaries": [
            #     {
            #         "ResourceType": "AWS::S3::Bucket",
            #         "LogicalResourceIds": ["Bucket"],
            #         "ResourceIdentifiers": ["BucketName"],
            #     }
            # ],
        }
    )


@mock_cloudformation
def test_boto3_create_stack_with_ref_yaml():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    params = [
        {"ParameterKey": "TagDescription", "ParameterValue": "desc_ref"},
        {"ParameterKey": "TagName", "ParameterValue": "name_ref"},
    ]
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=params,
    )

    cf_conn.get_template(StackName="test_stack")["TemplateBody"].should.equal(
        dummy_template_yaml_with_ref
    )


@mock_cloudformation
def test_creating_stacks_across_regions():
    west1_cf = boto3.resource("cloudformation", region_name="us-west-1")
    west2_cf = boto3.resource("cloudformation", region_name="us-west-2")
    west1_cf.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)
    west2_cf.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    list(west1_cf.stacks.all()).should.have.length_of(1)
    list(west2_cf.stacks.all()).should.have.length_of(1)

    list(west1_cf.stacks.all())[0].stack_id.should.contain(
        "arn:aws:cloudformation:us-west-1:123456789:stack/test_stack/"
    )
    list(west2_cf.stacks.all())[0].stack_id.should.contain(
        "arn:aws:cloudformation:us-west-2:123456789:stack/test_stack/"
    )


@mock_cloudformation
@mock_sns
@mock_sqs
def test_create_stack_with_notification_arn():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="fake-queue")
    queue_arn = queue.attributes["QueueArn"]

    sns = boto3.client("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="fake-topic")
    topic_arn = topic["TopicArn"]

    sns.subscribe(TopicArn=topic_arn, Protocol="sqs", Endpoint=queue_arn)

    cf = boto3.resource("cloudformation", region_name="us-east-1")
    cf.create_stack(
        StackName="test_stack_with_notifications",
        TemplateBody=dummy_template_json,
        NotificationARNs=[topic_arn],
    )

    stack = list(cf.stacks.all())[0]
    stack.notification_arns.should.contain(topic_arn)

    messages = queue.receive_messages()
    messages.should.have.length_of(1)
    msg = json.loads(messages[0].body)
    msg["Subject"].should.equal("AWS CloudFormation Notification")
    msg["Message"].should.contain("StackId='{}'\n".format(stack.stack_id))
    msg["Message"].should.contain("LogicalResourceId='test_stack_with_notifications'\n")
    msg["Message"].should.contain("ResourceStatus='CREATE_IN_PROGRESS'\n")
    msg["Message"].should.contain("ResourceStatusReason='User Initiated'\n")
    msg["Message"].should.contain("ResourceType='AWS::CloudFormation::Stack'\n")
    msg["Message"].should.contain("StackName='test_stack_with_notifications'\n")
    msg.should.have.key("MessageId")
    msg.should.have.key("Signature")
    msg.should.have.key("SignatureVersion")
    msg.should.have.key("Subject")
    msg.should.have.key("Timestamp")
    msg["TopicArn"].should.equal(topic_arn)
    msg.should.have.key("Type")
    msg.should.have.key("UnsubscribeURL")

    messages = queue.receive_messages()
    messages.should.have.length_of(1)
    msg = json.loads(messages[0].body)
    msg["Message"].should.contain("StackId='{}'\n".format(stack.stack_id))
    msg["Message"].should.contain("LogicalResourceId='test_stack_with_notifications'\n")
    msg["Message"].should.contain("ResourceStatus='CREATE_COMPLETE'\n")
    msg["Message"].should.contain("ResourceStatusReason='None'\n")
    msg["Message"].should.contain("ResourceType='AWS::CloudFormation::Stack'\n")
    msg["Message"].should.contain("StackName='test_stack_with_notifications'\n")
    msg.should.have.key("MessageId")
    msg.should.have.key("Signature")
    msg.should.have.key("SignatureVersion")
    msg.should.have.key("Subject")
    msg.should.have.key("Timestamp")
    msg["TopicArn"].should.equal(topic_arn)
    msg.should.have.key("Type")
    msg.should.have.key("UnsubscribeURL")


@mock_cloudformation
def test_create_stack_with_role_arn():
    cf = boto3.resource("cloudformation", region_name="us-east-1")
    cf.create_stack(
        StackName="test_stack_with_notifications",
        TemplateBody=dummy_template_json,
        RoleARN="arn:aws:iam::{}:role/moto".format(ACCOUNT_ID),
    )
    stack = list(cf.stacks.all())[0]
    stack.role_arn.should.equal("arn:aws:iam::{}:role/moto".format(ACCOUNT_ID))


@mock_cloudformation
@mock_s3
def test_create_stack_from_s3_url():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3_conn = boto3.resource("s3", region_name="us-east-1")
    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=dummy_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )

    cf_conn = boto3.client("cloudformation", region_name="us-west-1")
    cf_conn.create_stack(StackName="stack_from_url", TemplateURL=key_url)
    cf_conn.get_template(StackName="stack_from_url")["TemplateBody"].should.equal(
        json.loads(dummy_template_json, object_pairs_hook=OrderedDict)
    )


@mock_cloudformation
def test_boto3_update_stack_fail_missing_new_parameter():

    name = "update_stack_fail_missing_new_parameter"

    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    cf_conn.create_stack(StackName=name, TemplateBody=dummy_empty_template_json)

    with pytest.raises(ClientError, match="Missing parameter KeyName"):

        cf_conn.update_stack(
            StackName=name, TemplateBody=dummy_parametrized_template_json
        )


@mock_cloudformation
def test_boto3_update_stack_fail_update_same_template_body():

    name = "update_stack_with_previous_value"
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    params = [
        {"ParameterKey": "TagName", "ParameterValue": "foo"},
        {"ParameterKey": "TagDescription", "ParameterValue": "bar"},
    ]

    cf_conn.create_stack(
        StackName=name, TemplateBody=dummy_template_yaml_with_ref, Parameters=params,
    )

    with pytest.raises(ClientError) as exp:
        cf_conn.update_stack(
            StackName=name,
            TemplateBody=dummy_template_yaml_with_ref,
            Parameters=params,
        )
    exp_err = exp.value.response.get("Error")
    exp_metadata = exp.value.response.get("ResponseMetadata")

    exp_err.get("Code").should.equal("ValidationError")
    exp_err.get("Message").should.equal(f"Stack [{name}] already exists")
    exp_metadata.get("HTTPStatusCode").should.equal(400)

    cf_conn.update_stack(
        StackName=name,
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=[
            {"ParameterKey": "TagName", "ParameterValue": "new_foo"},
            {"ParameterKey": "TagDescription", "ParameterValue": "new_bar"},
        ],
    )


@mock_cloudformation
def test_boto3_update_stack_deleted_resources_can_reference_deleted_parameters():

    name = "update_stack_deleted_resources_can_reference_deleted_parameters"

    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    template_json = json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Parameters": {"TimeoutParameter": {"Default": 61, "Type": "String"}},
            "Resources": {
                "Queue": {
                    "Type": "AWS::SQS::Queue",
                    "Properties": {"VisibilityTimeout": {"Ref": "TimeoutParameter"}},
                }
            },
        }
    )

    cf_conn.create_stack(StackName=name, TemplateBody=template_json)

    response = cf_conn.describe_stack_resources(StackName=name)
    len(response["StackResources"]).should.equal(1)

    cf_conn.update_stack(StackName=name, TemplateBody=dummy_empty_template_json)

    response = cf_conn.describe_stack_resources(StackName=name)
    len(response["StackResources"]).should.equal(0)


@mock_cloudformation
def test_boto3_update_stack_deleted_resources_can_reference_deleted_resources():

    name = "update_stack_deleted_resources_can_reference_deleted_resources"

    cf_conn = boto3.client("cloudformation", region_name="us-east-1")

    template_json = json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Parameters": {"TimeoutParameter": {"Default": 61, "Type": "String"}},
            "Resources": {
                "VPC": {
                    "Type": "AWS::EC2::VPC",
                    "Properties": {"CidrBlock": "10.0.0.0/16"},
                },
                "Subnet": {
                    "Type": "AWS::EC2::Subnet",
                    "Properties": {"VpcId": {"Ref": "VPC"}, "CidrBlock": "10.0.0.0/24"},
                },
            },
        }
    )

    cf_conn.create_stack(StackName=name, TemplateBody=template_json)

    response = cf_conn.describe_stack_resources(StackName=name)
    len(response["StackResources"]).should.equal(2)

    cf_conn.update_stack(StackName=name, TemplateBody=dummy_empty_template_json)

    response = cf_conn.describe_stack_resources(StackName=name)
    len(response["StackResources"]).should.equal(0)


@mock_cloudformation
def test_update_stack_with_previous_value():
    name = "update_stack_with_previous_value"
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(
        StackName=name,
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=[
            {"ParameterKey": "TagName", "ParameterValue": "foo"},
            {"ParameterKey": "TagDescription", "ParameterValue": "bar"},
        ],
    )
    cf_conn.update_stack(
        StackName=name,
        UsePreviousTemplate=True,
        Parameters=[
            {"ParameterKey": "TagName", "UsePreviousValue": True},
            {"ParameterKey": "TagDescription", "ParameterValue": "not bar"},
        ],
    )
    stack = cf_conn.describe_stacks(StackName=name)["Stacks"][0]
    tag_name = [
        x["ParameterValue"]
        for x in stack["Parameters"]
        if x["ParameterKey"] == "TagName"
    ][0]
    tag_desc = [
        x["ParameterValue"]
        for x in stack["Parameters"]
        if x["ParameterKey"] == "TagDescription"
    ][0]
    assert tag_name == "foo"
    assert tag_desc == "not bar"


@mock_cloudformation
@mock_s3
@mock_ec2
def test_update_stack_from_s3_url():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3_conn = boto3.resource("s3", region_name="us-east-1")

    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(
        StackName="update_stack_from_url",
        TemplateBody=dummy_template_json,
        Tags=[{"Key": "foo", "Value": "bar"}],
    )

    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=dummy_update_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )

    cf_conn.update_stack(
        StackName="update_stack_from_url",
        TemplateURL=key_url,
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "value"}],
    )

    cf_conn.get_template(StackName="update_stack_from_url")[
        "TemplateBody"
    ].should.equal(
        json.loads(dummy_update_template_json, object_pairs_hook=OrderedDict)
    )


@mock_cloudformation
@mock_s3
def test_create_change_set_from_s3_url():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3_conn = boto3.resource("s3", region_name="us-east-1")
    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=dummy_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )
    cf_conn = boto3.client("cloudformation", region_name="us-west-1")
    response = cf_conn.create_change_set(
        StackName="NewStack",
        TemplateURL=key_url,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
        Tags=[{"Key": "tag-key", "Value": "tag-value"}],
    )
    assert (
        "arn:aws:cloudformation:us-west-1:123456789:changeSet/NewChangeSet/"
        in response["Id"]
    )
    assert (
        "arn:aws:cloudformation:us-west-1:123456789:stack/NewStack"
        in response["StackId"]
    )


@mock_cloudformation
@mock_ec2
def test_describe_change_set():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
    )

    stack = cf_conn.describe_change_set(ChangeSetName="NewChangeSet")

    stack["ChangeSetName"].should.equal("NewChangeSet")
    stack["StackName"].should.equal("NewStack")
    stack["Status"].should.equal("CREATE_COMPLETE")
    stack["ExecutionStatus"].should.equal("AVAILABLE")
    two_secs_ago = datetime.now(tz=pytz.UTC) - timedelta(seconds=2)
    assert (
        two_secs_ago < stack["CreationTime"] < datetime.now(tz=pytz.UTC)
    ), "Change set should have been created recently"
    stack["Changes"].should.have.length_of(1)
    stack["Changes"][0].should.equal(
        dict(
            {
                "Type": "Resource",
                "ResourceChange": {
                    "Action": "Add",
                    "LogicalResourceId": "EC2Instance1",
                    "ResourceType": "AWS::EC2::Instance",
                },
            }
        )
    )

    # Execute change set
    cf_conn.execute_change_set(ChangeSetName="NewChangeSet")

    # Verify that the changes have been applied
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.describe_instances()["Reservations"].should.have.length_of(1)

    change_set = cf_conn.describe_change_set(ChangeSetName="NewChangeSet")
    change_set["Changes"].should.have.length_of(1)
    change_set["ExecutionStatus"].should.equal("EXECUTE_COMPLETE")

    stack = cf_conn.describe_stacks(StackName="NewStack")["Stacks"][0]
    stack["StackStatus"].should.equal("CREATE_COMPLETE")

    # create another change set to update the stack
    cf_conn.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_update_template_json,
        ChangeSetName="NewChangeSet2",
        ChangeSetType="UPDATE",
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "value"}],
    )

    stack = cf_conn.describe_change_set(ChangeSetName="NewChangeSet2")
    stack["ChangeSetName"].should.equal("NewChangeSet2")
    stack["StackName"].should.equal("NewStack")
    stack["Changes"].should.have.length_of(2)

    # Execute change set
    cf_conn.execute_change_set(ChangeSetName="NewChangeSet2")

    # Verify that the changes have been applied
    stack = cf_conn.describe_stacks(StackName="NewStack")["Stacks"][0]
    stack["StackStatus"].should.equal("UPDATE_COMPLETE")


@mock_cloudformation
@mock_ec2
def test_execute_change_set_w_arn():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    # Verify no instances exist at the moment
    ec2.describe_instances()["Reservations"].should.have.length_of(0)
    # Create a Change set, and verify no resources have been created yet
    change_set = cf_conn.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
    )
    ec2.describe_instances()["Reservations"].should.have.length_of(0)
    cf_conn.describe_change_set(ChangeSetName="NewChangeSet")["Status"].should.equal(
        "CREATE_COMPLETE"
    )
    # Execute change set
    cf_conn.execute_change_set(ChangeSetName=change_set["Id"])
    # Verify that the status has changed, and the appropriate resources have been created
    cf_conn.describe_change_set(ChangeSetName="NewChangeSet")["Status"].should.equal(
        "CREATE_COMPLETE"
    )
    ec2.describe_instances()["Reservations"].should.have.length_of(1)


@mock_cloudformation
def test_execute_change_set_w_name():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
    )
    cf_conn.execute_change_set(ChangeSetName="NewChangeSet", StackName="NewStack")


@mock_cloudformation
def test_describe_stack_pagination():
    conn = boto3.client("cloudformation", region_name="us-east-1")
    for i in range(100):
        conn.create_stack(
            StackName="test_stack_{}".format(i), TemplateBody=dummy_template_json
        )

    resp = conn.describe_stacks()
    stacks = resp["Stacks"]
    stacks.should.have.length_of(50)
    next_token = resp["NextToken"]
    next_token.should_not.be.none
    resp2 = conn.describe_stacks(NextToken=next_token)
    stacks.extend(resp2["Stacks"])
    stacks.should.have.length_of(100)
    assert "NextToken" not in resp2.keys()


@mock_cloudformation
def test_describe_stack_resource():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    stack = cf_conn.describe_stacks(StackName="test_stack")["Stacks"][0]

    response = cf_conn.describe_stack_resource(
        StackName=stack["StackName"], LogicalResourceId="EC2Instance1"
    )

    resource = response["StackResourceDetail"]
    resource["LogicalResourceId"].should.equal("EC2Instance1")
    resource["ResourceStatus"].should.equal("CREATE_COMPLETE")
    resource["ResourceType"].should.equal("AWS::EC2::Instance")
    resource["StackId"].should.equal(stack["StackId"])


@mock_cloudformation
def test_describe_stack_resource_when_resource_does_not_exist():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    stack = cf_conn.describe_stacks(StackName="test_stack")["Stacks"][0]

    with pytest.raises(ClientError, match="does not exist for stack"):
        cf_conn.describe_stack_resource(
            StackName=stack["StackName"], LogicalResourceId="DoesNotExist"
        )


@mock_cloudformation
def test_describe_stack_resources():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    stack = cf_conn.describe_stacks(StackName="test_stack")["Stacks"][0]

    response = cf_conn.describe_stack_resources(StackName=stack["StackName"])
    resource = response["StackResources"][0]
    resource["LogicalResourceId"].should.equal("EC2Instance1")
    resource["ResourceStatus"].should.equal("CREATE_COMPLETE")
    resource["ResourceType"].should.equal("AWS::EC2::Instance")
    resource["StackId"].should.equal(stack["StackId"])


@mock_cloudformation
def test_describe_stack_by_name():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    stack = cf_conn.describe_stacks(StackName="test_stack")["Stacks"][0]
    stack["StackName"].should.equal("test_stack")
    two_secs_ago = datetime.now(tz=pytz.UTC) - timedelta(seconds=2)
    assert (
        two_secs_ago < stack["CreationTime"] < datetime.now(tz=pytz.UTC)
    ), "Stack should have been created recently"


@mock_cloudformation
def test_describe_stack_by_stack_id():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    stack = cf_conn.describe_stacks(StackName="test_stack")["Stacks"][0]
    stack_by_id = cf_conn.describe_stacks(StackName=stack["StackId"])["Stacks"][0]

    stack_by_id["StackId"].should.equal(stack["StackId"])
    stack_by_id["StackName"].should.equal("test_stack")


@mock_cloudformation
def test_list_change_sets():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_change_set(
        StackName="NewStack2",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet2",
        ChangeSetType="CREATE",
    )
    change_set = cf_conn.list_change_sets(StackName="NewStack2")["Summaries"][0]
    change_set["StackName"].should.equal("NewStack2")
    change_set["ChangeSetName"].should.equal("NewChangeSet2")


@mock_cloudformation
def test_list_stacks():
    cf = boto3.resource("cloudformation", region_name="us-east-1")
    cf.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)
    cf.create_stack(StackName="test_stack2", TemplateBody=dummy_template_json)

    stacks = list(cf.stacks.all())
    stacks.should.have.length_of(2)
    stack_names = [stack.stack_name for stack in stacks]
    stack_names.should.contain("test_stack")
    stack_names.should.contain("test_stack2")


@mock_cloudformation
def test_delete_stack_from_resource():
    cf = boto3.resource("cloudformation", region_name="us-east-1")
    stack = cf.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    list(cf.stacks.all()).should.have.length_of(1)
    stack.delete()
    list(cf.stacks.all()).should.have.length_of(0)


@mock_cloudformation
@mock_ec2
def test_delete_change_set():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
    )

    cf_conn.list_change_sets(StackName="NewStack")["Summaries"].should.have.length_of(1)
    cf_conn.delete_change_set(ChangeSetName="NewChangeSet", StackName="NewStack")
    cf_conn.list_change_sets(StackName="NewStack")["Summaries"].should.have.length_of(0)

    # Testing deletion by arn
    result = cf_conn.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet1",
        ChangeSetType="CREATE",
    )
    cf_conn.delete_change_set(ChangeSetName=result.get("Id"), StackName="NewStack")
    cf_conn.list_change_sets(StackName="NewStack")["Summaries"].should.have.length_of(0)


@mock_cloudformation
@mock_ec2
def test_delete_stack_by_name():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    cf_conn.describe_stacks()["Stacks"].should.have.length_of(1)
    cf_conn.delete_stack(StackName="test_stack")
    cf_conn.describe_stacks()["Stacks"].should.have.length_of(0)


@mock_cloudformation
def test_delete_stack():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    cf.delete_stack(StackName="test_stack")
    stacks = cf.list_stacks()
    assert stacks["StackSummaries"][0]["StackStatus"] == "DELETE_COMPLETE"


@mock_cloudformation
def test_describe_deleted_stack():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    stack = cf_conn.describe_stacks(StackName="test_stack")["Stacks"][0]
    stack_id = stack["StackId"]
    cf_conn.delete_stack(StackName=stack["StackId"])
    stack_by_id = cf_conn.describe_stacks(StackName=stack_id)["Stacks"][0]
    stack_by_id["StackId"].should.equal(stack["StackId"])
    stack_by_id["StackName"].should.equal("test_stack")
    stack_by_id["StackStatus"].should.equal("DELETE_COMPLETE")


@mock_cloudformation
def test_describe_stack_with_special_chars():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(
        StackName="test_stack_spl",
        TemplateBody=dummy_template_special_chars_in_description_json,
    )

    stack = cf_conn.describe_stacks(StackName="test_stack_spl")["Stacks"][0]
    assert stack.get("StackName") == "test_stack_spl"
    assert stack.get("Description") == "Stack 1 <env>"


@mock_cloudformation
@mock_ec2
def test_describe_updated_stack():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
        Tags=[{"Key": "foo", "Value": "bar"}],
    )

    cf_conn.update_stack(
        StackName="test_stack",
        RoleARN="arn:aws:iam::{}:role/moto".format(ACCOUNT_ID),
        TemplateBody=dummy_update_template_json,
        Tags=[{"Key": "foo", "Value": "baz"}],
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "value"}],
    )

    stack = cf_conn.describe_stacks(StackName="test_stack")["Stacks"][0]
    stack_id = stack["StackId"]
    stack_by_id = cf_conn.describe_stacks(StackName=stack_id)["Stacks"][0]
    stack_by_id["StackId"].should.equal(stack["StackId"])
    stack_by_id["StackName"].should.equal("test_stack")
    stack_by_id["StackStatus"].should.equal("UPDATE_COMPLETE")
    stack_by_id["RoleARN"].should.equal("arn:aws:iam::{}:role/moto".format(ACCOUNT_ID))
    stack_by_id["Tags"].should.equal([{"Key": "foo", "Value": "baz"}])

    # Verify the updated template is persisted
    template = cf_conn.get_template(StackName="test_stack")["TemplateBody"]
    template.should.equal(dummy_update_template)


@mock_cloudformation
def test_update_stack_with_previous_template():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)
    cf_conn.update_stack(StackName="test_stack", UsePreviousTemplate=True)

    stack = cf_conn.describe_stacks(StackName="test_stack")["Stacks"][0]
    stack["StackName"].should.equal("test_stack")
    stack["StackStatus"].should.equal("UPDATE_COMPLETE")

    # Verify the original template is persisted
    template = cf_conn.get_template(StackName="test_stack")["TemplateBody"]
    template.should.equal(dummy_template)


@mock_cloudformation
def test_bad_describe_stack():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        cf_conn.describe_stacks(StackName="non_existent_stack")
    err = exc.value.response["Error"]
    err.should.have.key("Code").being.equal("ValidationError")
    err.should.have.key("Message").being.equal(
        "Stack with id non_existent_stack does not exist"
    )


@mock_cloudformation
def test_cloudformation_params():
    dummy_template_with_params = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Stack 1",
        "Resources": {},
        "Parameters": {
            "APPNAME": {
                "Default": "app-name",
                "Description": "The name of the app",
                "Type": "String",
            }
        },
    }
    dummy_template_with_params_json = json.dumps(dummy_template_with_params)

    cf = boto3.resource("cloudformation", region_name="us-east-1")
    stack = cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_with_params_json,
        Parameters=[{"ParameterKey": "APPNAME", "ParameterValue": "testing123"}],
    )

    stack.parameters.should.have.length_of(1)
    param = stack.parameters[0]
    param["ParameterKey"].should.equal("APPNAME")
    param["ParameterValue"].should.equal("testing123")


@mock_cloudformation
@mock_ec2
def test_update_stack_with_parameters():
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Stack",
        "Resources": {
            "VPC": {
                "Properties": {"CidrBlock": {"Ref": "Bar"}},
                "Type": "AWS::EC2::VPC",
            }
        },
        "Parameters": {"Bar": {"Type": "String"}},
    }
    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
        Parameters=[{"ParameterKey": "Bar", "ParameterValue": "192.168.0.0/16"}],
    )
    cf.update_stack(
        StackName="test_stack",
        TemplateBody=template_json,
        Parameters=[{"ParameterKey": "Bar", "ParameterValue": "192.168.0.1/16"}],
    )

    stack = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    stack["Parameters"].should.have.length_of(1)
    stack["Parameters"][0].should.equal(
        {"ParameterKey": "Bar", "ParameterValue": "192.168.0.1/16"}
    )


@mock_cloudformation
@mock_ec2
def test_update_stack_replace_tags():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
        Tags=[{"Key": "foo", "Value": "bar"}],
    )
    cf.update_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
        Tags=[{"Key": "foo", "Value": "baz"}],
    )

    stack = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    stack["StackStatus"].should.equal("UPDATE_COMPLETE")
    stack["Tags"].should.equal([{"Key": "foo", "Value": "baz"}])


@mock_cloudformation
def test_update_stack_when_rolled_back():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate backend in server mode")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    stack = cf.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)
    stack_id = stack["StackId"]

    cloudformation_backends["us-east-1"].stacks[stack_id].status = "ROLLBACK_COMPLETE"

    with pytest.raises(ClientError) as ex:
        cf.update_stack(StackName="test_stack", TemplateBody=dummy_template_json)

    err = ex.value.response["Error"]
    err.should.have.key("Code").being.equal("ValidationError")
    err.should.have.key("Message").match(
        r"Stack:arn:aws:cloudformation:us-east-1:123456789:stack/test_stack/[a-z0-9-]+ is in ROLLBACK_COMPLETE state and can not be updated."
    )


@mock_cloudformation
@mock_ec2
def test_cloudformation_params_conditions_and_resources_are_distinct():
    template_with_conditions = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Stack 1",
        "Conditions": {
            "FooEnabled": {"Fn::Equals": [{"Ref": "FooEnabled"}, "true"]},
            "FooDisabled": {
                "Fn::Not": [{"Fn::Equals": [{"Ref": "FooEnabled"}, "true"]}]
            },
        },
        "Parameters": {
            "FooEnabled": {"Type": "String", "AllowedValues": ["true", "false"]}
        },
        "Resources": {
            "Bar": {
                "Properties": {"CidrBlock": "192.168.0.0/16"},
                "Condition": "FooDisabled",
                "Type": "AWS::EC2::VPC",
            }
        },
    }
    template_with_conditions = json.dumps(template_with_conditions)
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(
        StackName="test_stack1",
        TemplateBody=template_with_conditions,
        Parameters=[{"ParameterKey": "FooEnabled", "ParameterValue": "true"}],
    )
    resources = cf.list_stack_resources(StackName="test_stack1")[
        "StackResourceSummaries"
    ]
    assert not [
        resource for resource in resources if resource["LogicalResourceId"] == "Bar"
    ]


@mock_cloudformation
@mock_ec2
def test_cloudformation_conditions_yaml_equals():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(
        StackName="teststack2",
        TemplateBody=dummy_yaml_template_with_equals,
        Parameters=[{"ParameterKey": "enabled", "ParameterValue": "true"}],
    )
    resources = cf.list_stack_resources(StackName="teststack2")[
        "StackResourceSummaries"
    ]
    assert [
        resource for resource in resources if resource["LogicalResourceId"] == "VPC1"
    ]


@mock_cloudformation
@mock_ec2
def test_cloudformation_conditions_yaml_equals_shortform():
    _template = dummy_yaml_template_with_equals
    _template = _template.replace("Fn::Equals:", "!Equals")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(
        StackName="teststack2",
        TemplateBody=_template,
        Parameters=[{"ParameterKey": "enabled", "ParameterValue": "true"}],
    )
    resources = cf.list_stack_resources(StackName="teststack2")[
        "StackResourceSummaries"
    ]
    assert [
        resource for resource in resources if resource["LogicalResourceId"] == "VPC1"
    ]


@mock_cloudformation
def test_stack_tags():
    tags = [{"Key": "foo", "Value": "bar"}, {"Key": "baz", "Value": "bleh"}]
    cf = boto3.resource("cloudformation", region_name="us-east-1")
    stack = cf.create_stack(
        StackName="test_stack", TemplateBody=dummy_template_json, Tags=tags
    )
    observed_tag_items = set(
        item for items in [tag.items() for tag in stack.tags] for item in items
    )
    expected_tag_items = set(
        item for items in [tag.items() for tag in tags] for item in items
    )
    observed_tag_items.should.equal(expected_tag_items)


@mock_cloudformation
@mock_ec2
def test_stack_events():
    cf = boto3.resource("cloudformation", region_name="us-east-1")
    stack = cf.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)
    stack.update(
        TemplateBody=dummy_update_template_json,
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "value"}],
    )
    stack = cf.Stack(stack.stack_id)
    stack.delete()

    # assert begins and ends with stack events
    events = list(stack.events.all())
    events[0].resource_type.should.equal("AWS::CloudFormation::Stack")
    events[-1].resource_type.should.equal("AWS::CloudFormation::Stack")

    # testing ordering of stack events without assuming resource events will not exist
    # the AWS API returns events in reverse chronological order
    stack_events_to_look_for = iter(
        [
            ("DELETE_COMPLETE", None),
            ("DELETE_IN_PROGRESS", "User Initiated"),
            ("UPDATE_COMPLETE", None),
            ("UPDATE_IN_PROGRESS", "User Initiated"),
            ("CREATE_COMPLETE", None),
            ("CREATE_IN_PROGRESS", "User Initiated"),
        ]
    )
    try:
        for event in events:
            event.stack_id.should.equal(stack.stack_id)
            event.stack_name.should.equal("test_stack")
            event.event_id.should.match(r"[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}")

            if event.resource_type == "AWS::CloudFormation::Stack":
                event.logical_resource_id.should.equal("test_stack")
                event.physical_resource_id.should.equal(stack.stack_id)

                status_to_look_for, reason_to_look_for = next(stack_events_to_look_for)
                event.resource_status.should.equal(status_to_look_for)
                if reason_to_look_for is not None:
                    event.resource_status_reason.should.equal(reason_to_look_for)
    except StopIteration:
        assert False, "Too many stack events"

    list(stack_events_to_look_for).should.be.empty

    with pytest.raises(ClientError) as exp:
        stack = cf.Stack("non_existing_stack")
        events = list(stack.events.all())

    exp_err = exp.value.response.get("Error")
    exp_metadata = exp.value.response.get("ResponseMetadata")

    exp_err.get("Code").should.match(r"ValidationError")
    exp_err.get("Message").should.match(
        r"Stack with id non_existing_stack does not exist"
    )
    exp_metadata.get("HTTPStatusCode").should.equal(400)


@mock_cloudformation
def test_list_exports():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    cf_resource = boto3.resource("cloudformation", region_name="us-east-1")
    stack = cf_resource.create_stack(
        StackName="test_stack", TemplateBody=dummy_output_template_json
    )
    output_value = "VPCID"
    exports = cf_client.list_exports()["Exports"]

    stack.outputs.should.have.length_of(1)
    stack.outputs[0]["OutputValue"].should.equal(output_value)

    exports.should.have.length_of(1)
    exports[0]["ExportingStackId"].should.equal(stack.stack_id)
    exports[0]["Name"].should.equal("My VPC ID")
    exports[0]["Value"].should.equal(output_value)


@mock_cloudformation
def test_list_exports_with_token():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    for i in range(101):
        # Add index to ensure name is unique
        dummy_output_template["Outputs"]["StackVPC"]["Export"]["Name"] += str(i)
        cf.create_stack(
            StackName="test_stack_{}".format(i),
            TemplateBody=json.dumps(dummy_output_template),
        )
    exports = cf.list_exports()
    exports["Exports"].should.have.length_of(100)
    exports.get("NextToken").should_not.be.none

    more_exports = cf.list_exports(NextToken=exports["NextToken"])
    more_exports["Exports"].should.have.length_of(1)
    more_exports.get("NextToken").should.be.none


@mock_cloudformation
def test_delete_stack_with_export():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    stack = cf.create_stack(
        StackName="test_stack", TemplateBody=dummy_output_template_json
    )

    stack_id = stack["StackId"]
    exports = cf.list_exports()["Exports"]
    exports.should.have.length_of(1)

    cf.delete_stack(StackName=stack_id)
    cf.list_exports()["Exports"].should.have.length_of(0)


@mock_cloudformation
def test_export_names_must_be_unique():
    cf = boto3.resource("cloudformation", region_name="us-east-1")
    cf.create_stack(StackName="test_stack", TemplateBody=dummy_output_template_json)
    with pytest.raises(ClientError):
        cf.create_stack(StackName="test_stack", TemplateBody=dummy_output_template_json)


@mock_sqs
@mock_cloudformation
def test_stack_with_imports():
    cf = boto3.resource("cloudformation", region_name="us-east-1")
    ec2_resource = boto3.resource("sqs", region_name="us-east-1")

    output_stack = cf.create_stack(
        StackName="test_stack1", TemplateBody=dummy_output_template_json
    )
    cf.create_stack(StackName="test_stack2", TemplateBody=dummy_import_template_json)

    output_stack.outputs.should.have.length_of(1)
    output = output_stack.outputs[0]["OutputValue"]
    queue = ec2_resource.get_queue_by_name(QueueName=output)
    queue.should_not.be.none


@mock_sqs
@mock_cloudformation
def test_non_json_redrive_policy():
    cf = boto3.resource("cloudformation", region_name="us-east-1")

    stack = cf.create_stack(
        StackName="test_stack1", TemplateBody=dummy_redrive_template_json
    )

    stack.Resource("MainQueue").resource_status.should.equal("CREATE_COMPLETE")
    stack.Resource("DeadLetterQueue").resource_status.should.equal("CREATE_COMPLETE")


@mock_cloudformation
def test_boto3_create_duplicate_stack():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    cf_conn.create_stack(
        StackName="test_stack", TemplateBody=dummy_template_json,
    )

    with pytest.raises(ClientError):
        cf_conn.create_stack(
            StackName="test_stack", TemplateBody=dummy_template_json,
        )


@mock_dynamodb2
@mock_cloudformation
def test_delete_stack_dynamo_template():
    conn = boto3.client("cloudformation", region_name="us-east-1")
    dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
    conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json4)
    table_desc = dynamodb_client.list_tables()
    len(table_desc.get("TableNames")).should.equal(1)
    conn.delete_stack(StackName="test_stack")
    table_desc = dynamodb_client.list_tables()
    len(table_desc.get("TableNames")).should.equal(0)
    conn.create_stack(StackName="test_stack", TemplateBody=dummy_template_json4)


@mock_dynamodb2
@mock_cloudformation
@mock_lambda
def test_create_stack_lambda_and_dynamodb():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant set environment variables in server mode")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Stack Lambda Test 1",
        "Parameters": {},
        "Resources": {
            "func1": {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "Code": {"S3Bucket": "bucket_123", "S3Key": "key_123"},
                    "FunctionName": "func1",
                    "Handler": "handler.handler",
                    "Role": get_role_name(),
                    "Runtime": "python2.7",
                    "Description": "descr",
                    "MemorySize": 12345,
                },
            },
            "func1version": {
                "Type": "AWS::Lambda::Version",
                "Properties": {"FunctionName": {"Ref": "func1"}},
            },
            "tab1": {
                "Type": "AWS::DynamoDB::Table",
                "Properties": {
                    "TableName": "tab1",
                    "KeySchema": [{"AttributeName": "attr1", "KeyType": "HASH"}],
                    "AttributeDefinitions": [
                        {"AttributeName": "attr1", "AttributeType": "string"}
                    ],
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 10,
                        "WriteCapacityUnits": 10,
                    },
                    "StreamSpecification": {"StreamViewType": "KEYS_ONLY"},
                },
            },
            "func1mapping": {
                "Type": "AWS::Lambda::EventSourceMapping",
                "Properties": {
                    "FunctionName": {"Ref": "func1"},
                    "EventSourceArn": {"Fn::GetAtt": ["tab1", "StreamArn"]},
                    "StartingPosition": "0",
                    "BatchSize": 100,
                    "Enabled": True,
                },
            },
        },
    }
    validate_s3_before = os.environ.get("VALIDATE_LAMBDA_S3", "")
    try:
        os.environ["VALIDATE_LAMBDA_S3"] = "false"
        cf.create_stack(
            StackName="test_stack_lambda", TemplateBody=json.dumps(template),
        )
    finally:
        os.environ["VALIDATE_LAMBDA_S3"] = validate_s3_before

    resources = cf.list_stack_resources(StackName="test_stack_lambda")[
        "StackResourceSummaries"
    ]
    resources.should.have.length_of(4)
    resource_types = [r["ResourceType"] for r in resources]
    resource_types.should.contain("AWS::Lambda::Function")
    resource_types.should.contain("AWS::Lambda::Version")
    resource_types.should.contain("AWS::DynamoDB::Table")
    resource_types.should.contain("AWS::Lambda::EventSourceMapping")


@mock_cloudformation
@mock_ec2
def test_create_and_update_stack_with_unknown_resource():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    # Creating a stack with an unknown resource should throw a warning
    expected_err = "Tried to parse AWS::Cloud9::EnvironmentEC2 but it's not supported by moto's CloudFormation implementation"
    if settings.TEST_SERVER_MODE:
        # Can't verify warnings in ServerMode though
        cf_conn.create_stack(
            StackName="test_stack", TemplateBody=dummy_unknown_template_json
        )
    else:
        with pytest.warns(UserWarning, match=expected_err):
            cf_conn.create_stack(
                StackName="test_stack", TemplateBody=dummy_unknown_template_json
            )

    # The stack should exist though
    stacks = cf_conn.describe_stacks()["Stacks"]
    stacks.should.have.length_of(1)
    stacks[0].should.have.key("StackName").equal("test_stack")

    # Updating an unknown resource should throw a warning, but not fail
    new_template = copy.deepcopy(dummy_unknown_template)
    new_template["Resources"]["UnknownResource"]["Properties"]["Sth"] = "other"
    if settings.TEST_SERVER_MODE:
        cf_conn.update_stack(
            StackName="test_stack", TemplateBody=json.dumps(new_template)
        )
    else:
        with pytest.warns(UserWarning, match=expected_err):
            cf_conn.update_stack(
                StackName="test_stack", TemplateBody=json.dumps(new_template)
            )


def get_role_name():
    with mock_iam():
        iam = boto3.client("iam", region_name="us-east-1")
        try:
            return iam.get_role(RoleName="my-role")["Role"]["Arn"]
        except ClientError:
            return iam.create_role(
                RoleName="my-role",
                AssumeRolePolicyDocument="some policy",
                Path="/my-path/",
            )["Role"]["Arn"]
