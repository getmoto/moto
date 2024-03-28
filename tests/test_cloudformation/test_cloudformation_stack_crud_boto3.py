import copy
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.cloudformation import cloudformation_backends
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.utilities.distutils_version import LooseVersion
from tests import EXAMPLE_AMI_ID

TEST_STACK_NAME = "test_stack"
REGION_NAME = "us-east-1"

boto3_version = sys.modules["botocore"].__version__

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

dummy_template2 = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 2",
    "Resources": {},
}

dummy_template3 = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 3",
    "Resources": {
        "VPC": {"Properties": {"CidrBlock": "192.168.0.0/16"}, "Type": "AWS::EC2::VPC"}
    },
}

dummy_template4 = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "myDynamoDBTable": {
            "Type": "AWS::DynamoDB::Table",
            "Properties": {
                "AttributeDefinitions": [
                    {"AttributeName": "Name", "AttributeType": "S"},
                    {"AttributeName": "Age", "AttributeType": "S"},
                ],
                "KeySchema": [
                    {"AttributeName": "Name", "KeyType": "HASH"},
                    {"AttributeName": "Age", "KeyType": "RANGE"},
                ],
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
                "TableName": "Person",
            },
        }
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

dummy_update_template_yaml = """---
AWSTemplateFormatVersion: '2010-09-09'
Parameters:
  KeyName:
    Description: Name of an existing EC2 KeyPair
    Type: AWS::EC2::KeyPair::KeyName
    ConstraintDescription: must be the name of an existing EC2 KeyPair.
Resources:
  Instance:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-12c6146b

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
            "Properties": {"QueueName": "deadletterqueue.fifo", "FifoQueue": True},
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

dummy_template_launch_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Trying to create ec2 with auto scaling group",
    "Parameters": {
        "Subnets": {
            "Description": "Pass in the created subnet ids",
            "Type": "List<AWS::EC2::Subnet::Id>",
        },
        "StackName": {"Type": "String", "Description": "Unique stack name"},
    },
    "Resources": {
        "TestLaunchTemplate": {
            "Type": "AWS::EC2::LaunchTemplate",
            "Properties": {
                "LaunchTemplateName": {"Fn::Sub": "${AWS::StackName}-launch-template"},
                "LaunchTemplateData": {
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/xvda",
                            "Ebs": {
                                "VolumeType": "gp3",
                                "VolumeSize": "30",
                                "DeleteOnTermination": "true",
                                "Encrypted": "true",
                            },
                        }
                    ],
                    "ImageId": "ami-12c6146b",
                    "InstanceType": "t3.micro",
                },
                "VersionDescription": "Initial Version",
            },
        },
        "ECSAutoScalingGroup": {
            "Type": "AWS::AutoScaling::AutoScalingGroup",
            "Properties": {
                "VPCZoneIdentifier": {"Ref": "Subnets"},
                "MixedInstancesPolicy": {
                    "InstancesDistribution": {
                        "OnDemandAllocationStrategy": "string",
                        "OnDemandBaseCapacity": 123,
                        "OnDemandPercentageAboveBaseCapacity": 123,
                        "SpotAllocationStrategy": "string",
                        "SpotInstancePools": 123,
                        "SpotMaxPrice": "string",
                    },
                    "LaunchTemplate": {
                        "LaunchTemplateSpecification": {
                            "LaunchTemplateId": {"Ref": "TestLaunchTemplate"},
                            "Version": "$DEFAULT",
                        }
                    },
                },
                "CapacityRebalance": True,
                "MinSize": "1",
                "MaxSize": "10",
                "DesiredCapacity": "5",
            },
        },
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
dummy_template_json2 = json.dumps(dummy_template2)
dummy_template_json4 = json.dumps(dummy_template4)
dummy_unknown_template_json = json.dumps(dummy_unknown_template)


@mock_aws
def test_create_stack():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)
    stack = cf.describe_stacks()["Stacks"][0]
    assert stack["StackName"] == TEST_STACK_NAME
    assert stack["EnableTerminationProtection"] is False

    template = cf.get_template(StackName=TEST_STACK_NAME)["TemplateBody"]
    assert template == dummy_template


@mock_aws
def test_create_stack_with_additional_properties():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=dummy_template_json,
        EnableTerminationProtection=True,
        TimeoutInMinutes=25,
    )
    stack = cf.describe_stacks()["Stacks"][0]
    assert stack["StackName"] == TEST_STACK_NAME
    assert stack["EnableTerminationProtection"] is True
    assert stack["TimeoutInMinutes"] == 25


@mock_aws
def test_describe_stack_instances():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="teststackset", TemplateBody=dummy_template_json)
    cf.create_stack_instances(
        StackSetName="teststackset",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
    )
    usw2_instance = cf.describe_stack_instance(
        StackSetName="teststackset",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-west-2",
    )["StackInstance"]
    use1_instance = cf.describe_stack_instance(
        StackSetName="teststackset",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-east-1",
    )["StackInstance"]

    assert use1_instance["Region"] == "us-east-1"
    assert usw2_instance["Region"] == "us-west-2"
    for instance in [use1_instance, usw2_instance]:
        assert instance["Account"] == ACCOUNT_ID
        assert instance["Status"] == "CURRENT"
        if LooseVersion(boto3_version) > LooseVersion("1.29.0"):
            # "Parameters only available in newer versions"
            assert instance["StackInstanceStatus"] == {"DetailedStatus": "SUCCEEDED"}


@mock_aws
def test_list_stacksets_length():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="teststackset", TemplateBody=dummy_template_json)
    cf.create_stack_set(StackSetName="teststackset2", TemplateBody=dummy_template_yaml)
    stacksets = cf.list_stack_sets()
    assert len(stacksets) == 2


@mock_aws
def test_filter_stacks():
    conn = boto3.client("cloudformation", region_name=REGION_NAME)
    conn.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)
    conn.create_stack(StackName="test_stack2", TemplateBody=dummy_template_json)
    conn.update_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json2)

    stacks = conn.list_stacks(StackStatusFilter=["CREATE_COMPLETE"])
    assert len(stacks.get("StackSummaries")) == 1
    stacks = conn.list_stacks(StackStatusFilter=["UPDATE_COMPLETE"])
    assert len(stacks.get("StackSummaries")) == 1


@mock_aws
def test_list_stacksets_contents():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="teststackset", TemplateBody=dummy_template_json)
    stacksets = cf.list_stack_sets()
    assert stacksets["Summaries"][0]["StackSetName"] == "teststackset"
    assert stacksets["Summaries"][0]["Status"] == "ACTIVE"


@mock_aws
def test_stop_stack_set_operation():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="teststackset", TemplateBody=dummy_template_json)
    cf.create_stack_instances(
        StackSetName="teststackset",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-1", "us-west-2"],
    )
    operation_id = cf.list_stack_set_operations(StackSetName="teststackset")[
        "Summaries"
    ][-1]["OperationId"]
    cf.stop_stack_set_operation(StackSetName="teststackset", OperationId=operation_id)
    list_operation = cf.list_stack_set_operations(StackSetName="teststackset")
    assert list_operation["Summaries"][-1]["Status"] == "STOPPED"


@mock_aws
def test_describe_stack_set_operation():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="name", TemplateBody=dummy_template_json)
    operation_id = cf.create_stack_instances(
        StackSetName="name",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-1", "us-west-2"],
    )["OperationId"]

    cf.stop_stack_set_operation(StackSetName="name", OperationId=operation_id)
    response = cf.describe_stack_set_operation(
        StackSetName="name", OperationId=operation_id
    )

    assert response["StackSetOperation"]["Status"] == "STOPPED"
    assert response["StackSetOperation"]["Action"] == "CREATE"
    with pytest.raises(ClientError) as exp:
        cf.describe_stack_set_operation(
            StackSetName="name", OperationId="non_existing_operation"
        )
    exp_err = exp.value.response.get("Error")
    exp_metadata = exp.value.response.get("ResponseMetadata")

    assert exp_err["Code"] == "ValidationError"
    assert exp_err["Message"] == "Stack with id non_existing_operation does not exist"
    assert exp_metadata.get("HTTPStatusCode") == 400


@mock_aws
def test_list_stack_set_operation_results():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="teststackset", TemplateBody=dummy_template_json)
    cf.create_stack_instances(
        StackSetName="teststackset",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-1", "us-west-2"],
    )
    operation_id = cf.list_stack_set_operations(StackSetName="teststackset")[
        "Summaries"
    ][-1]["OperationId"]

    cf.stop_stack_set_operation(StackSetName="teststackset", OperationId=operation_id)
    response = cf.list_stack_set_operation_results(
        StackSetName="teststackset", OperationId=operation_id
    )

    assert len(response["Summaries"]) == 3
    assert response["Summaries"][0]["Account"] == ACCOUNT_ID
    assert response["Summaries"][1]["Status"] == "STOPPED"


@mock_aws
def test_update_stack_instances():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    param = [
        {"ParameterKey": "TagDescription", "ParameterValue": "StackSetValue"},
        {"ParameterKey": "TagName", "ParameterValue": "StackSetValue2"},
    ]
    param_overrides = [
        {"ParameterKey": "TagDescription", "ParameterValue": "OverrideValue"},
        {"ParameterKey": "TagName", "ParameterValue": "OverrideValue2"},
    ]
    cf.create_stack_set(
        StackSetName="teststackset",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param,
    )
    cf.create_stack_instances(
        StackSetName="teststackset",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-1", "us-west-2"],
    )
    cf.update_stack_instances(
        StackSetName="teststackset",
        Accounts=[ACCOUNT_ID],
        Regions=["us-west-1", "us-west-2"],
        ParameterOverrides=param_overrides,
    )
    usw2_instance = cf.describe_stack_instance(
        StackSetName="teststackset",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-west-2",
    )
    usw1_instance = cf.describe_stack_instance(
        StackSetName="teststackset",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-west-1",
    )
    use1_instance = cf.describe_stack_instance(
        StackSetName="teststackset",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-east-1",
    )

    usw2_overrides = usw2_instance["StackInstance"]["ParameterOverrides"]
    assert usw2_overrides[0]["ParameterKey"] == param_overrides[0]["ParameterKey"]
    assert usw2_overrides[0]["ParameterValue"] == param_overrides[0]["ParameterValue"]
    assert usw2_overrides[1]["ParameterKey"] == param_overrides[1]["ParameterKey"]
    assert usw2_overrides[1]["ParameterValue"] == param_overrides[1]["ParameterValue"]

    usw1_overrides = usw1_instance["StackInstance"]["ParameterOverrides"]
    assert usw1_overrides[0]["ParameterKey"] == param_overrides[0]["ParameterKey"]
    assert usw1_overrides[0]["ParameterValue"] == param_overrides[0]["ParameterValue"]
    assert usw1_overrides[1]["ParameterKey"] == param_overrides[1]["ParameterKey"]
    assert usw1_overrides[1]["ParameterValue"] == param_overrides[1]["ParameterValue"]

    assert use1_instance["StackInstance"]["ParameterOverrides"] == []


@mock_aws
def test_delete_stack_instances():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    tss = "teststackset"
    cf.create_stack_set(StackSetName=tss, TemplateBody=dummy_template_json)
    cf.create_stack_instances(
        StackSetName=tss,
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2", "eu-north-1"],
    )

    # Delete just one
    cf.delete_stack_instances(
        StackSetName=tss,
        Accounts=[ACCOUNT_ID],
        # Also delete unknown region for good measure - that should be a no-op
        Regions=["us-east-1", "us-east-2"],
        RetainStacks=False,
    )

    # Some should remain
    remaining_stacks = cf.list_stack_instances(StackSetName=tss)["Summaries"]
    assert len(remaining_stacks) == 2
    assert [stack["Region"] for stack in remaining_stacks] == [
        "us-west-2",
        "eu-north-1",
    ]

    # Delete all
    cf.delete_stack_instances(
        StackSetName=tss,
        Accounts=[ACCOUNT_ID],
        # Also delete unknown region for good measure - that should be a no-op
        Regions=["us-west-2", "eu-north-1"],
        RetainStacks=False,
    )

    remaining_stacks = cf.list_stack_instances(StackSetName=tss)["Summaries"]
    assert len(remaining_stacks) == 0


@mock_aws
def test_create_stack_instances():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="teststackset", TemplateBody=dummy_template_json)
    cf.create_stack_instances(
        StackSetName="teststackset",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
    )

    summaries = cf.list_stack_instances(StackSetName="teststackset")["Summaries"]
    assert len(summaries) == 2
    assert summaries[0]["Account"] == ACCOUNT_ID


@mock_aws
def test_create_stack_instances_with_param_overrides():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    param = [
        {"ParameterKey": "TagDescription", "ParameterValue": "StackSetValue"},
        {"ParameterKey": "TagName", "ParameterValue": "StackSetValue2"},
    ]
    param_overrides = [
        {"ParameterKey": "TagDescription", "ParameterValue": "OverrideValue"},
        {"ParameterKey": "TagName", "ParameterValue": "OverrideValue2"},
    ]
    cf.create_stack_set(
        StackSetName="teststackset",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param,
    )
    cf.create_stack_instances(
        StackSetName="teststackset",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
        ParameterOverrides=param_overrides,
    )
    usw2_instance = cf.describe_stack_instance(
        StackSetName="teststackset",
        StackInstanceAccount=ACCOUNT_ID,
        StackInstanceRegion="us-west-2",
    )

    usw2_overrides = usw2_instance["StackInstance"]["ParameterOverrides"]
    assert usw2_overrides[0]["ParameterKey"] == param_overrides[0]["ParameterKey"]
    assert usw2_overrides[1]["ParameterKey"] == param_overrides[1]["ParameterKey"]
    assert usw2_overrides[0]["ParameterValue"] == param_overrides[0]["ParameterValue"]
    assert usw2_overrides[1]["ParameterValue"] == param_overrides[1]["ParameterValue"]


@mock_aws
def test_update_stack_set():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    param = [
        {"ParameterKey": "TagDescription", "ParameterValue": "StackSetValue"},
        {"ParameterKey": "TagName", "ParameterValue": "StackSetValue2"},
    ]
    param_overrides = [
        {"ParameterKey": "TagDescription", "ParameterValue": "OverrideValue"},
        {"ParameterKey": "TagName", "ParameterValue": "OverrideValue2"},
    ]
    cf.create_stack_set(
        StackSetName="teststackset",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param,
    )
    cf.update_stack_set(
        StackSetName="teststackset",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param_overrides,
    )
    stackset = cf.describe_stack_set(StackSetName="teststackset")

    stack_params = stackset["StackSet"]["Parameters"]
    assert stack_params[0]["ParameterValue"] == param_overrides[0]["ParameterValue"]
    assert stack_params[1]["ParameterValue"] == param_overrides[1]["ParameterValue"]
    assert stack_params[0]["ParameterKey"] == param_overrides[0]["ParameterKey"]
    assert stack_params[1]["ParameterKey"] == param_overrides[1]["ParameterKey"]


@mock_aws
def test_update_stack_set_with_previous_value():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    param = [
        {"ParameterKey": "TagDescription", "ParameterValue": "StackSetValue"},
        {"ParameterKey": "TagName", "ParameterValue": "StackSetValue2"},
    ]
    param_overrides = [
        {"ParameterKey": "TagDescription", "ParameterValue": "OverrideValue"},
        {"ParameterKey": "TagName", "UsePreviousValue": True},
    ]
    cf.create_stack_set(
        StackSetName="teststackset",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param,
    )
    cf.update_stack_set(
        StackSetName="teststackset",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=param_overrides,
    )
    stackset = cf.describe_stack_set(StackSetName="teststackset")

    stack_params = stackset["StackSet"]["Parameters"]
    assert stack_params[0]["ParameterValue"] == param_overrides[0]["ParameterValue"]
    assert stack_params[1]["ParameterValue"] == param[1]["ParameterValue"]
    assert stack_params[0]["ParameterKey"] == param_overrides[0]["ParameterKey"]
    assert stack_params[1]["ParameterKey"] == param_overrides[1]["ParameterKey"]


@mock_aws
def test_list_stack_set_operations():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="teststackset", TemplateBody=dummy_template_json)
    cf.create_stack_instances(
        StackSetName="teststackset",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
    )
    cf.update_stack_instances(
        StackSetName="teststackset",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1", "us-west-2"],
    )

    list_operation = cf.list_stack_set_operations(StackSetName="teststackset")
    assert len(list_operation["Summaries"]) == 2
    assert list_operation["Summaries"][-1]["Action"] == "UPDATE"


@mock_aws
def test_bad_list_stack_resources():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)

    with pytest.raises(ClientError):
        cf.list_stack_resources(StackName="teststackset")


@mock_aws
def test_delete_stack_set_by_name():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="teststackset", TemplateBody=dummy_template_json)
    cf.delete_stack_set(StackSetName="teststackset")

    stacks = cf.list_stack_sets()["Summaries"]
    assert len(stacks) == 1
    assert stacks[0]["StackSetName"] == "teststackset"
    assert stacks[0]["Status"] == "DELETED"

    with pytest.raises(ClientError) as exc:
        cf.describe_stack_set(StackSetName="teststackset")
    err = exc.value.response["Error"]
    assert err["Code"] == "StackSetNotFoundException"
    assert err["Message"] == "StackSet teststackset not found"


@mock_aws
def test_delete_stack_set_by_id():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    response = cf.create_stack_set(
        StackSetName="teststackset", TemplateBody=dummy_template_json
    )
    stack_set_id = response["StackSetId"]
    cf.delete_stack_set(StackSetName=stack_set_id)

    stacks = cf.list_stack_sets()["Summaries"]
    assert len(stacks) == 1
    assert stacks[0]["StackSetName"] == "teststackset"
    assert stacks[0]["Status"] == "DELETED"


@mock_aws
def test_delete_stack_set__while_instances_are_running():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="a", TemplateBody=json.dumps(dummy_template3))
    cf.create_stack_instances(
        StackSetName="a",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1"],
    )
    with pytest.raises(ClientError) as exc:
        cf.delete_stack_set(StackSetName="a")
    err = exc.value.response["Error"]
    assert err["Code"] == "StackSetNotEmptyException"
    assert err["Message"] == "StackSet is not empty"

    cf.delete_stack_instances(
        StackSetName="a",
        Accounts=[ACCOUNT_ID],
        Regions=["us-east-1"],
        RetainStacks=False,
    )

    # This will succeed when no StackInstances are left
    cf.delete_stack_set(StackSetName="a")


@mock_aws
def test_create_stack_set():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    response = cf.create_stack_set(
        StackSetName="teststackset",
        TemplateBody=dummy_template_json,
        Description="desc",
        AdministrationRoleARN="admin/role/arn:asdfasdfadsf",
    )
    assert response["StackSetId"] is not None

    stack_set = cf.describe_stack_set(StackSetName="teststackset")["StackSet"]
    assert stack_set["TemplateBody"] == dummy_template_json
    assert stack_set["AdministrationRoleARN"] == "admin/role/arn:asdfasdfadsf"
    assert stack_set["Description"] == "desc"


@mock_aws
@pytest.mark.parametrize("name", ["1234", "stack_set", "-set"])
def test_create_stack_set__invalid_name(name):
    client = boto3.client("cloudformation", region_name=REGION_NAME)
    with pytest.raises(ClientError) as exc:
        client.create_stack_set(StackSetName=name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == f"1 validation error detected: Value '{name}' at 'stackSetName' failed to satisfy constraint: Member must satisfy regular expression pattern: [a-zA-Z][-a-zA-Z0-9]*"
    )


@mock_aws
def test_create_stack_set_with_yaml():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack_set(StackSetName="tss", TemplateBody=dummy_template_yaml)

    tmplt = cf.describe_stack_set(StackSetName="tss")["StackSet"]["TemplateBody"]
    assert tmplt == dummy_template_yaml


@mock_aws
def test_create_stack_set_from_s3_url():
    s3 = boto3.client("s3", region_name=REGION_NAME)
    s3_conn = boto3.resource("s3", region_name=REGION_NAME)
    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=dummy_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack_set(StackSetName="urlStack", TemplateURL=key_url)
    tmplt = cf.describe_stack_set(StackSetName="urlStack")["StackSet"]["TemplateBody"]
    assert tmplt == dummy_template_json


@mock_aws
def test_create_stack_set_with_ref_yaml():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    params = [
        {"ParameterKey": "TagDescription", "ParameterValue": "desc_ref"},
        {"ParameterKey": "TagName", "ParameterValue": "name_ref"},
    ]
    cf.create_stack_set(
        StackSetName="teststack",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=params,
    )

    tmplt = cf.describe_stack_set(StackSetName="teststack")["StackSet"]["TemplateBody"]
    assert tmplt == dummy_template_yaml_with_ref


@mock_aws
def test_describe_stack_set_params():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    params = [
        {"ParameterKey": "TagDescription", "ParameterValue": "desc_ref"},
        {"ParameterKey": "TagName", "ParameterValue": "name_ref"},
    ]
    cf.create_stack_set(
        StackSetName="teststack",
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=params,
    )

    stack_set = cf.describe_stack_set(StackSetName="teststack")["StackSet"]
    assert stack_set["Parameters"] == params


@mock_aws
def test_describe_stack_set_by_id():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    ss_id = cf.create_stack_set(StackSetName="s", TemplateBody=dummy_template_json)[
        "StackSetId"
    ]

    stack_set = cf.describe_stack_set(StackSetName=ss_id)["StackSet"]
    assert stack_set["TemplateBody"] == dummy_template_json


@mock_aws
def test_create_stack_fail_missing_parameter():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)

    with pytest.raises(ClientError, match="Missing parameter KeyName"):
        cf.create_stack(StackName="ts", TemplateBody=dummy_parametrized_template_json)


@mock_aws
def test_create_stack_s3_long_name():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)

    stack_name = "MyLongStackName01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012"

    template = '{"Resources":{"HelloBucket":{"Type":"AWS::S3::Bucket"}}}'

    cf.create_stack(StackName=stack_name, TemplateBody=template)

    tmplt = cf.get_template(StackName=stack_name)["TemplateBody"]
    assert tmplt == json.loads(template, object_pairs_hook=OrderedDict)
    provisioned_resource = cf.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ][0]
    provisioned_bucket_name = provisioned_resource["PhysicalResourceId"]
    assert len(provisioned_bucket_name) < 64
    logical_name_lower_case = provisioned_resource["LogicalResourceId"].lower()
    bucket_name_stack_name_prefix = provisioned_bucket_name[
        : provisioned_bucket_name.index("-" + logical_name_lower_case)
    ]
    assert bucket_name_stack_name_prefix in stack_name.lower()


@mock_aws
def test_create_stack_with_yaml():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName="ts", TemplateBody=dummy_template_yaml)

    assert cf.get_template(StackName="ts")["TemplateBody"] == dummy_template_yaml


@mock_aws
def test_create_stack_with_short_form_func_yaml():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName="ts", TemplateBody=dummy_template_yaml_with_short_form_func
    )

    template_body = cf.get_template(StackName="ts")["TemplateBody"]
    assert template_body == dummy_template_yaml_with_short_form_func


@mock_aws
def test_get_template_summary():
    s3 = boto3.client("s3", region_name=REGION_NAME)
    s3_conn = boto3.resource("s3", region_name=REGION_NAME)

    # json template
    conn = boto3.client("cloudformation", region_name=REGION_NAME)
    result = conn.get_template_summary(TemplateBody=json.dumps(dummy_template3))
    assert result["ResourceTypes"] == ["AWS::EC2::VPC"]
    assert result["Version"] == "2010-09-09"
    assert result["Description"] == "Stack 3"
    assert result["Parameters"] == []

    # existing stack
    conn.create_stack(
        StackName=TEST_STACK_NAME, TemplateBody=json.dumps(dummy_template3)
    )
    result = conn.get_template_summary(StackName=TEST_STACK_NAME)
    assert result["ResourceTypes"] == ["AWS::EC2::VPC"]
    assert result["Version"] == "2010-09-09"
    assert result["Description"] == "Stack 3"
    assert result["Parameters"] == []

    # json template from s3
    s3_conn.create_bucket(Bucket="foobar")
    s3_conn.Object("foobar", "template-key").put(Body=json.dumps(dummy_template3))
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )
    conn.create_stack(StackName="stackfromurl", TemplateURL=key_url)
    result = conn.get_template_summary(TemplateURL=key_url)
    assert result["ResourceTypes"] == ["AWS::EC2::VPC"]
    assert result["Version"] == "2010-09-09"
    assert result["Description"] == "Stack 3"

    # yaml template
    conn = boto3.client("cloudformation", region_name=REGION_NAME)
    result = conn.get_template_summary(TemplateBody=dummy_template_yaml)
    assert result["ResourceTypes"] == ["AWS::EC2::Instance"]
    assert result["Version"] == "2010-09-09"
    assert result["Description"] == "Stack1 with yaml template"


@mock_aws
def test_get_template_summary_for_stack_created_by_changeset_execution():
    conn = boto3.client("cloudformation", region_name=REGION_NAME)
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
    assert result["ResourceTypes"] == ["AWS::EC2::VPC"]
    assert result["Version"] == "2010-09-09"
    assert result["Description"] == "Stack 3"


@mock_aws
def test_get_template_summary_for_template_containing_parameters():
    conn = boto3.client("cloudformation", region_name=REGION_NAME)
    conn.create_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=json.dumps(dummy_template_with_parameters),
    )
    result = conn.get_template_summary(StackName=TEST_STACK_NAME)
    del result["ResponseMetadata"]
    assert result == {
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


@mock_aws
def test_create_stack_with_ref_yaml():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    params = [
        {"ParameterKey": "TagDescription", "ParameterValue": "desc_ref"},
        {"ParameterKey": "TagName", "ParameterValue": "name_ref"},
    ]
    cf.create_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=params,
    )

    template_body = cf.get_template(StackName=TEST_STACK_NAME)["TemplateBody"]
    assert template_body == dummy_template_yaml_with_ref


@mock_aws
def test_creating_stacks_across_regions():
    west1_cf = boto3.resource("cloudformation", region_name="us-west-1")
    west2_cf = boto3.resource("cloudformation", region_name="us-west-2")
    west1_cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)
    west2_cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    west1_stacks = list(west1_cf.stacks.all())
    west2_stacks = list(west2_cf.stacks.all())
    assert len(west1_stacks) == 1
    assert len(west2_stacks) == 1

    assert west1_stacks[0].stack_id.startswith(
        f"arn:aws:cloudformation:us-west-1:{ACCOUNT_ID}:stack/test_stack/"
    )
    assert west2_stacks[0].stack_id.startswith(
        f"arn:aws:cloudformation:us-west-2:{ACCOUNT_ID}:stack/test_stack/"
    )


@mock_aws
def test_create_stack_with_notification_arn():
    sqs = boto3.resource("sqs", region_name=REGION_NAME)
    queue = sqs.create_queue(QueueName="fake-queue")
    queue_arn = queue.attributes["QueueArn"]

    sns = boto3.client("sns", region_name=REGION_NAME)
    topic = sns.create_topic(Name="fake-topic")
    topic_arn = topic["TopicArn"]

    sns.subscribe(TopicArn=topic_arn, Protocol="sqs", Endpoint=queue_arn)

    cf = boto3.resource("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName="test_stack_with_notifications",
        TemplateBody=dummy_template_json,
        NotificationARNs=[topic_arn],
    )

    stack = list(cf.stacks.all())[0]
    assert topic_arn in stack.notification_arns

    messages = queue.receive_messages()
    assert len(messages) == 1
    msg = json.loads(messages[0].body)
    assert msg["Subject"] == "AWS CloudFormation Notification"
    assert f"StackId='{stack.stack_id}'\n" in msg["Message"]
    assert "LogicalResourceId='test_stack_with_notifications'\n" in msg["Message"]
    assert "ResourceStatus='CREATE_IN_PROGRESS'\n" in msg["Message"]
    assert "ResourceStatusReason='User Initiated'\n" in msg["Message"]
    assert "ResourceType='AWS::CloudFormation::Stack'\n" in msg["Message"]
    assert "StackName='test_stack_with_notifications'\n" in msg["Message"]
    assert "MessageId" in msg
    assert "Signature" in msg
    assert "SignatureVersion" in msg
    assert "Subject" in msg
    assert "Timestamp" in msg
    assert msg["TopicArn"] == topic_arn
    assert "Type" in msg
    assert "UnsubscribeURL" in msg

    messages = queue.receive_messages()
    assert len(messages) == 1
    msg = json.loads(messages[0].body)
    assert f"StackId='{stack.stack_id}'\n" in msg["Message"]
    assert "LogicalResourceId='test_stack_with_notifications'\n" in msg["Message"]
    assert "ResourceStatus='CREATE_COMPLETE'\n" in msg["Message"]
    assert "ResourceStatusReason='None'\n" in msg["Message"]
    assert "ResourceType='AWS::CloudFormation::Stack'\n" in msg["Message"]
    assert "StackName='test_stack_with_notifications'\n" in msg["Message"]
    assert "MessageId" in msg
    assert "Signature" in msg
    assert "SignatureVersion" in msg
    assert "Subject" in msg
    assert "Timestamp" in msg
    assert msg["TopicArn"] == topic_arn
    assert "Type" in msg
    assert "UnsubscribeURL" in msg


@mock_aws
def test_create_stack_with_role_arn():
    cf = boto3.resource("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName="test_stack_with_notifications",
        TemplateBody=dummy_template_json,
        RoleARN=f"arn:aws:iam::{ACCOUNT_ID}:role/moto",
    )
    stack = list(cf.stacks.all())[0]
    assert stack.role_arn == f"arn:aws:iam::{ACCOUNT_ID}:role/moto"


@mock_aws
def test_create_stack_from_s3_url():
    s3 = boto3.client("s3", region_name=REGION_NAME)
    s3_conn = boto3.resource("s3", region_name=REGION_NAME)
    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=dummy_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="stackfromurl", TemplateURL=key_url)
    tmplt = cf.get_template(StackName="stackfromurl")["TemplateBody"]
    assert tmplt == json.loads(dummy_template_json, object_pairs_hook=OrderedDict)


@mock_aws
def test_update_stack_fail_missing_new_parameter():
    name = "update_stack_fail_missing_new_parameter"

    cf = boto3.client("cloudformation", region_name=REGION_NAME)

    cf.create_stack(StackName=name, TemplateBody=dummy_empty_template_json)

    with pytest.raises(ClientError, match="Missing parameter KeyName"):
        cf.update_stack(StackName=name, TemplateBody=dummy_parametrized_template_json)


@mock_aws
def test_update_stack_fail_update_same_template_body():
    name = "update_stack_with_previous_value"
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    params = [
        {"ParameterKey": "TagName", "ParameterValue": "foo"},
        {"ParameterKey": "TagDescription", "ParameterValue": "bar"},
    ]

    cf.create_stack(
        StackName=name, TemplateBody=dummy_template_yaml_with_ref, Parameters=params
    )

    with pytest.raises(ClientError) as exp:
        cf.update_stack(
            StackName=name, TemplateBody=dummy_template_yaml_with_ref, Parameters=params
        )
    exp_err = exp.value.response.get("Error")
    exp_metadata = exp.value.response.get("ResponseMetadata")

    assert exp_err.get("Code") == "ValidationError"
    assert exp_err.get("Message") == "No updates are to be performed."
    assert exp_metadata.get("HTTPStatusCode") == 400

    cf.update_stack(
        StackName=name,
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=[
            {"ParameterKey": "TagName", "ParameterValue": "new_foo"},
            {"ParameterKey": "TagDescription", "ParameterValue": "new_bar"},
        ],
    )


@mock_aws
def test_update_stack_deleted_resources_can_reference_deleted_parameters():
    name = "update_stack_deleted_resources_can_reference_deleted_parameters"

    cf = boto3.client("cloudformation", region_name=REGION_NAME)

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

    cf.create_stack(StackName=name, TemplateBody=template_json)

    response = cf.describe_stack_resources(StackName=name)
    assert len(response["StackResources"]) == 1

    cf.update_stack(StackName=name, TemplateBody=dummy_empty_template_json)

    response = cf.describe_stack_resources(StackName=name)
    assert len(response["StackResources"]) == 0


@mock_aws
def test_update_stack_deleted_resources_can_reference_deleted_resources():
    name = "update_stack_deleted_resources_can_reference_deleted_resources"

    cf = boto3.client("cloudformation", region_name=REGION_NAME)

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

    cf.create_stack(StackName=name, TemplateBody=template_json)

    response = cf.describe_stack_resources(StackName=name)
    assert len(response["StackResources"]) == 2

    cf.update_stack(StackName=name, TemplateBody=dummy_empty_template_json)

    response = cf.describe_stack_resources(StackName=name)
    assert len(response["StackResources"]) == 0


@mock_aws
def test_update_stack_with_previous_value():
    name = "update_stack_with_previous_value"
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName=name,
        TemplateBody=dummy_template_yaml_with_ref,
        Parameters=[
            {"ParameterKey": "TagName", "ParameterValue": "foo"},
            {"ParameterKey": "TagDescription", "ParameterValue": "bar"},
        ],
    )
    cf.update_stack(
        StackName=name,
        UsePreviousTemplate=True,
        Parameters=[
            {"ParameterKey": "TagName", "UsePreviousValue": True},
            {"ParameterKey": "TagDescription", "ParameterValue": "not bar"},
        ],
    )
    stack = cf.describe_stacks(StackName=name)["Stacks"][0]
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


@mock_aws
def test_update_stack_from_s3_url():
    s3 = boto3.client("s3", region_name=REGION_NAME)
    s3_conn = boto3.resource("s3", region_name=REGION_NAME)

    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName="update_stack_from_url",
        TemplateBody=dummy_template_json,
        Tags=[{"Key": "foo", "Value": "bar"}],
    )

    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=dummy_update_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )

    cf.update_stack(
        StackName="update_stack_from_url",
        TemplateURL=key_url,
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "value"}],
    )

    tmplt = cf.get_template(StackName="update_stack_from_url")["TemplateBody"]
    assert tmplt == json.loads(
        dummy_update_template_json, object_pairs_hook=OrderedDict
    )


@mock_aws
def test_create_change_set_from_s3_url():
    s3 = boto3.client("s3", region_name=REGION_NAME)
    s3_conn = boto3.resource("s3", region_name=REGION_NAME)
    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=dummy_template_json)
    key_url = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )
    cf = boto3.client("cloudformation", region_name="us-west-1")
    response = cf.create_change_set(
        StackName="NewStack",
        TemplateURL=key_url,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
        Tags=[{"Key": "tag-key", "Value": "tag-value"}],
    )
    assert (
        f"arn:aws:cloudformation:us-west-1:{ACCOUNT_ID}:changeSet/NewChangeSet/"
        in response["Id"]
    )
    assert (
        f"arn:aws:cloudformation:us-west-1:{ACCOUNT_ID}:stack/NewStack"
        in response["StackId"]
    )


@pytest.mark.parametrize(
    "stack_template,change_template",
    [
        pytest.param(dummy_template_yaml, dummy_update_template_json),
        pytest.param(dummy_template_json, dummy_update_template_json),
        pytest.param(dummy_template_yaml, dummy_update_template_yaml),
    ],
)
@mock_aws
def test_describe_change_set(stack_template, change_template):
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_change_set(
        StackName="NewStack",
        TemplateBody=stack_template,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
    )

    stack = cf.describe_change_set(ChangeSetName="NewChangeSet")

    assert stack["ChangeSetName"] == "NewChangeSet"
    assert stack["StackName"] == "NewStack"
    assert stack["Status"] == "CREATE_COMPLETE"
    assert stack["ExecutionStatus"] == "AVAILABLE"
    two_secs_ago = datetime.now(tz=timezone.utc) - timedelta(seconds=2)
    assert (
        two_secs_ago < stack["CreationTime"] < datetime.now(tz=timezone.utc)
    ), "Change set should have been created recently"
    assert len(stack["Changes"]) == 1
    assert stack["Changes"][0] == {
        "Type": "Resource",
        "ResourceChange": {
            "Action": "Add",
            "LogicalResourceId": "EC2Instance1",
            "ResourceType": "AWS::EC2::Instance",
        },
    }

    # Execute change set
    cf.execute_change_set(ChangeSetName="NewChangeSet")

    # Verify that the changes have been applied
    ec2 = boto3.client("ec2", region_name=REGION_NAME)
    assert len(ec2.describe_instances()["Reservations"]) == 1

    change_set = cf.describe_change_set(ChangeSetName="NewChangeSet")
    assert len(change_set["Changes"]) == 1
    assert change_set["ExecutionStatus"] == "EXECUTE_COMPLETE"

    stack = cf.describe_stacks(StackName="NewStack")["Stacks"][0]
    assert stack["StackStatus"] == "CREATE_COMPLETE"

    # create another change set to update the stack
    cf.create_change_set(
        StackName="NewStack",
        TemplateBody=change_template,
        ChangeSetName="NewChangeSet2",
        ChangeSetType="UPDATE",
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "value"}],
    )

    stack = cf.describe_change_set(ChangeSetName="NewChangeSet2")
    assert stack["ChangeSetName"] == "NewChangeSet2"
    assert stack["StackName"] == "NewStack"
    assert len(stack["Changes"]) == 2

    # Execute change set
    cf.execute_change_set(ChangeSetName="NewChangeSet2")

    # Verify that the changes have been applied
    stack = cf.describe_stacks(StackName="NewStack")["Stacks"][0]
    assert stack["StackStatus"] == "UPDATE_COMPLETE"


@mock_aws
def test_execute_change_set_w_arn():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    ec2 = boto3.client("ec2", region_name=REGION_NAME)
    # Verify no instances exist at the moment
    assert len(ec2.describe_instances()["Reservations"]) == 0
    # Create a Change set, and verify no resources have been created yet
    change_set = cf.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewCS",
        ChangeSetType="CREATE",
    )
    assert len(ec2.describe_instances()["Reservations"]) == 0
    assert cf.describe_change_set(ChangeSetName="NewCS")["Status"] == "CREATE_COMPLETE"
    # Execute change set
    cf.execute_change_set(ChangeSetName=change_set["Id"])
    # Verify that the status has changed, and the appropriate resources have been created
    assert cf.describe_change_set(ChangeSetName="NewCS")["Status"] == "CREATE_COMPLETE"
    assert len(ec2.describe_instances()["Reservations"]) == 1


@mock_aws
def test_execute_change_set_w_name():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
    )
    cf.execute_change_set(ChangeSetName="NewChangeSet", StackName="NewStack")


@mock_aws
def test_describe_stack_pagination():
    conn = boto3.client("cloudformation", region_name=REGION_NAME)
    for i in range(100):
        conn.create_stack(StackName=f"test_stack_{i}", TemplateBody=dummy_template_json)

    resp = conn.describe_stacks()
    stacks = resp["Stacks"]
    assert len(stacks) == 50
    next_token = resp["NextToken"]
    assert next_token is not None
    resp2 = conn.describe_stacks(NextToken=next_token)
    stacks.extend(resp2["Stacks"])
    assert len(stacks) == 100
    assert "NextToken" not in resp2.keys()


@mock_aws
def test_describe_stack_resource():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]

    response = cf.describe_stack_resource(
        StackName=stack["StackName"], LogicalResourceId="EC2Instance1"
    )

    resource = response["StackResourceDetail"]
    assert resource["LogicalResourceId"] == "EC2Instance1"
    assert resource["ResourceStatus"] == "CREATE_COMPLETE"
    assert resource["ResourceType"] == "AWS::EC2::Instance"
    assert resource["StackId"] == stack["StackId"]


@mock_aws
def test_describe_stack_resource_when_resource_does_not_exist():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]

    with pytest.raises(ClientError, match="does not exist for stack"):
        cf.describe_stack_resource(
            StackName=stack["StackName"], LogicalResourceId="DoesNotExist"
        )


@mock_aws
def test_describe_stack_resources():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]

    response = cf.describe_stack_resources(StackName=stack["StackName"])
    resource = response["StackResources"][0]
    assert resource["LogicalResourceId"] == "EC2Instance1"
    assert resource["ResourceStatus"] == "CREATE_COMPLETE"
    assert resource["ResourceType"] == "AWS::EC2::Instance"
    assert resource["StackId"] == stack["StackId"]


@mock_aws
def test_describe_stack_by_name():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]
    assert stack["StackName"] == TEST_STACK_NAME
    two_secs_ago = datetime.now(tz=timezone.utc) - timedelta(seconds=2)
    assert (
        two_secs_ago < stack["CreationTime"] < datetime.now(tz=timezone.utc)
    ), "Stack should have been created recently"


@mock_aws
def test_describe_stack_by_stack_id():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]
    stack_by_id = cf.describe_stacks(StackName=stack["StackId"])["Stacks"][0]

    assert stack_by_id["StackId"] == stack["StackId"]
    assert stack_by_id["StackName"] == TEST_STACK_NAME


@mock_aws
def test_list_change_sets():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_change_set(
        StackName="NewStack2",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet2",
        ChangeSetType="CREATE",
    )
    change_set = cf.list_change_sets(StackName="NewStack2")["Summaries"][0]
    assert change_set["StackName"] == "NewStack2"
    assert change_set["ChangeSetName"] == "NewChangeSet2"


@mock_aws
def test_list_stacks():
    cf = boto3.resource("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)
    cf.create_stack(StackName="test_stack2", TemplateBody=dummy_template_json)

    stacks = list(cf.stacks.all())
    assert len(stacks) == 2
    stack_names = [stack.stack_name for stack in stacks]
    assert TEST_STACK_NAME in stack_names
    assert "test_stack2" in stack_names


@mock_aws
def test_delete_stack_from_resource():
    cf = boto3.resource("cloudformation", region_name=REGION_NAME)
    stack = cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    assert len(list(cf.stacks.all())) == 1
    stack.delete()
    assert len(list(cf.stacks.all())) == 0

    ec2 = boto3.resource("ec2", region_name=REGION_NAME)
    vpc = ec2.create_vpc(CidrBlock="10.11.0.0/16")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.11.1.0/24", AvailabilityZone=f"{REGION_NAME}a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.11.2.0/24", AvailabilityZone=f"{REGION_NAME}b"
    )

    new_stack = cf.create_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=json.dumps(dummy_template_launch_template),
        Parameters=[
            {
                "ParameterKey": "Subnets",
                "ParameterValue": f"{subnet1.id},{subnet2.id}",
                "ResolvedValue": "string",
            },
            {
                "ParameterKey": "StackName",
                "ParameterValue": TEST_STACK_NAME,
                "ResolvedValue": "string",
            },
        ],
    )
    new_stack.delete()
    assert len(list(cf.stacks.all())) == 0


@mock_aws
def test_delete_change_set():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
    )

    assert len(cf.list_change_sets(StackName="NewStack")["Summaries"]) == 1
    cf.delete_change_set(ChangeSetName="NewChangeSet", StackName="NewStack")
    assert len(cf.list_change_sets(StackName="NewStack")["Summaries"]) == 0

    # Testing deletion by arn
    result = cf.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet1",
        ChangeSetType="CREATE",
    )
    cf.delete_change_set(ChangeSetName=result.get("Id"), StackName="NewStack")
    assert len(cf.list_change_sets(StackName="NewStack")["Summaries"]) == 0


@mock_aws
def test_create_change_set_twice__no_changes():
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Parameters only available in newer versions")
    cf_client = boto3.client("cloudformation", region_name=REGION_NAME)

    # Execute once
    change_set_id = cf_client.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
    )["Id"]
    cf_client.execute_change_set(ChangeSetName=change_set_id, DisableRollback=False)

    # Execute twice
    change_set_id = cf_client.create_change_set(
        StackName="NewStack",
        TemplateBody=dummy_template_json,
        ChangeSetName="NewChangeSet",
        ChangeSetType="UPDATE",
    )["Id"]
    execution = cf_client.describe_change_set(ChangeSetName=change_set_id)

    # Assert
    assert execution["ExecutionStatus"] == "UNAVAILABLE"
    assert execution["Status"] == "FAILED"
    assert (
        execution["StatusReason"]
        == "The submitted information didn't contain changes. Submit different information to create a change set."
    )


@mock_aws
def test_create_change_set_twice__using_s3__no_changes():
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Parameters only available in newer versions")
    cf_client = boto3.client("cloudformation", region_name=REGION_NAME)
    s3 = boto3.client("s3", region_name=REGION_NAME)
    s3_conn = boto3.resource("s3", region_name=REGION_NAME)
    s3_conn.create_bucket(Bucket="foobar")

    s3_conn.Object("foobar", "template-key").put(Body=dummy_template_json)
    key_url_1 = s3.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": "foobar", "Key": "template-key"}
    )

    s3_conn.Object("foobar", "template-key-unchanged").put(Body=dummy_template_json)
    key_url_2 = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": "foobar", "Key": "template-key-unchanged"},
    )

    # Execute once
    change_set_id = cf_client.create_change_set(
        StackName="NewStack",
        TemplateURL=key_url_1,
        ChangeSetName="NewChangeSet",
        ChangeSetType="CREATE",
    )["Id"]
    cf_client.execute_change_set(ChangeSetName=change_set_id, DisableRollback=False)

    # Execute twice
    change_set_id = cf_client.create_change_set(
        StackName="NewStack",
        TemplateURL=key_url_2,
        ChangeSetName="NewChangeSet",
        ChangeSetType="UPDATE",
    )["Id"]
    execution = cf_client.describe_change_set(ChangeSetName=change_set_id)

    # Assert
    assert execution["ExecutionStatus"] == "UNAVAILABLE"
    assert execution["Status"] == "FAILED"
    assert (
        execution["StatusReason"]
        == "The submitted information didn't contain changes. Submit different information to create a change set."
    )


@mock_aws
def test_delete_stack_by_name():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    assert len(cf.describe_stacks()["Stacks"]) == 1
    cf.delete_stack(StackName=TEST_STACK_NAME)
    assert len(cf.describe_stacks()["Stacks"]) == 0


@mock_aws
def test_delete_stack():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    ec2 = boto3.client("ec2", region_name=REGION_NAME)

    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)
    state = ec2.describe_instances()["Reservations"][0]["Instances"][0]["State"]

    cf.delete_stack(StackName=TEST_STACK_NAME)
    stacks = cf.list_stacks()
    assert stacks["StackSummaries"][0]["StackStatus"] == "DELETE_COMPLETE"
    assert ec2.describe_instances()["Reservations"][0]["Instances"][0]["State"] != state


@mock_aws
@pytest.mark.parametrize("nr_of_resources", [1, 3, 5])
def test_delete_stack_with_nested_resources(nr_of_resources):
    """
    Resources can be dependent on eachother
    Verify that we'll keep deleting resources from a stack until there are none left
    """
    nested_template = {"Resources": {}}
    for idx in range(nr_of_resources):
        role_refs = []
        for idy in range(nr_of_resources):
            role = {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Statement": [
                            {
                                "Action": ["sts:AssumeRole"],
                                "Effect": "Allow",
                                "Principal": {"Service": ["ec2.amazonaws.com"]},
                            }
                        ]
                    }
                },
            }
            nested_template["Resources"].update({f"role{idx}_{idy}": role})
            role_refs.append({"Ref": f"role{idx}_{idy}"})

        instance_profile = {
            "Type": "AWS::IAM::InstanceProfile",
            "Properties": {"Path": "/", "Roles": role_refs},
        }
        nested_template["Resources"].update({f"ip{idx}": instance_profile})
    cf = boto3.client("cloudformation", region_name=REGION_NAME)

    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=json.dumps(nested_template))
    cf.delete_stack(StackName=TEST_STACK_NAME)

    iam = boto3.client("iam", REGION_NAME)
    assert not iam.list_roles()["Roles"]
    assert not iam.list_instance_profiles()["InstanceProfiles"]


@mock_aws
@pytest.mark.skipif(
    settings.TEST_SERVER_MODE,
    reason="Can't patch model delete attributes in server mode.",
)
def test_delete_stack_delete_not_implemented(monkeypatch):
    monkeypatch.delattr(
        "moto.ec2.models.instances.Instance.delete_from_cloudformation_json"
    )
    monkeypatch.delattr("moto.ec2.models.instances.Instance.delete")

    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    ec2 = boto3.client("ec2", region_name=REGION_NAME)

    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)
    state = ec2.describe_instances()["Reservations"][0]["Instances"][0]["State"]

    # Mock stack deletion succeeds
    cf.delete_stack(StackName=TEST_STACK_NAME)
    stacks = cf.list_stacks()
    assert stacks["StackSummaries"][0]["StackStatus"] == "DELETE_COMPLETE"
    # But the underlying resource is untouched
    assert ec2.describe_instances()["Reservations"][0]["Instances"][0]["State"] == state


@mock_aws
def test_describe_deleted_stack():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]
    stack_id = stack["StackId"]
    cf.delete_stack(StackName=stack["StackId"])
    stack_by_id = cf.describe_stacks(StackName=stack_id)["Stacks"][0]
    assert stack_by_id["StackId"] == stack["StackId"]
    assert stack_by_id["StackName"] == TEST_STACK_NAME
    assert stack_by_id["StackStatus"] == "DELETE_COMPLETE"


@mock_aws
def test_describe_stack_with_special_chars():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName="test_stack_spl",
        TemplateBody=dummy_template_special_chars_in_description_json,
    )

    stack = cf.describe_stacks(StackName="test_stack_spl")["Stacks"][0]
    assert stack.get("StackName") == "test_stack_spl"
    assert stack.get("Description") == "Stack 1 <env>"


@mock_aws
def test_describe_updated_stack():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=dummy_template_json,
        Tags=[{"Key": "foo", "Value": "bar"}],
    )

    cf.update_stack(
        StackName=TEST_STACK_NAME,
        RoleARN=f"arn:aws:iam::{ACCOUNT_ID}:role/moto",
        TemplateBody=dummy_update_template_json,
        Tags=[{"Key": "foo", "Value": "baz"}],
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "value"}],
    )

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]
    stack_id = stack["StackId"]
    stack_by_id = cf.describe_stacks(StackName=stack_id)["Stacks"][0]
    assert stack_by_id["StackId"] == stack["StackId"]
    assert stack_by_id["StackName"] == TEST_STACK_NAME
    assert stack_by_id["StackStatus"] == "UPDATE_COMPLETE"
    assert stack_by_id["RoleARN"] == f"arn:aws:iam::{ACCOUNT_ID}:role/moto"
    assert stack_by_id["Tags"] == [{"Key": "foo", "Value": "baz"}]

    # Verify the updated template is persisted
    template = cf.get_template(StackName=TEST_STACK_NAME)["TemplateBody"]
    assert template == dummy_update_template


@mock_aws
def test_update_stack_with_previous_template():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)
    cf.update_stack(StackName=TEST_STACK_NAME, UsePreviousTemplate=True)

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]
    assert stack["StackName"] == TEST_STACK_NAME
    assert stack["StackStatus"] == "UPDATE_COMPLETE"

    # Verify the original template is persisted
    template = cf.get_template(StackName=TEST_STACK_NAME)["TemplateBody"]
    assert template == dummy_template


@mock_aws
def test_bad_describe_stack():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    with pytest.raises(ClientError) as exc:
        cf.describe_stacks(StackName="non_existent_stack")
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert err["Message"] == "Stack with id non_existent_stack does not exist"


@mock_aws
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

    cf = boto3.resource("cloudformation", region_name=REGION_NAME)
    stack = cf.create_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=dummy_template_with_params_json,
        Parameters=[{"ParameterKey": "APPNAME", "ParameterValue": "testing123"}],
    )

    assert len(stack.parameters) == 1
    param = stack.parameters[0]
    assert param["ParameterKey"] == "APPNAME"
    assert param["ParameterValue"] == "testing123"


@mock_aws
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
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=template_json,
        Parameters=[{"ParameterKey": "Bar", "ParameterValue": "192.168.0.0/16"}],
    )
    cf.update_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=template_json,
        Parameters=[{"ParameterKey": "Bar", "ParameterValue": "192.168.0.1/16"}],
    )

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]
    assert len(stack["Parameters"]) == 1
    assert stack["Parameters"][0] == {
        "ParameterKey": "Bar",
        "ParameterValue": "192.168.0.1/16",
    }


@mock_aws
def test_update_stack_replace_tags():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=dummy_template_json,
        Tags=[{"Key": "foo", "Value": "bar"}],
    )
    cf.update_stack(
        StackName=TEST_STACK_NAME,
        TemplateBody=dummy_template_json,
        Tags=[{"Key": "foo", "Value": "baz"}],
    )

    stack = cf.describe_stacks(StackName=TEST_STACK_NAME)["Stacks"][0]
    assert stack["StackStatus"] == "UPDATE_COMPLETE"
    assert stack["Tags"] == [{"Key": "foo", "Value": "baz"}]


@mock_aws
def test_update_stack_when_rolled_back():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate backend in server mode")
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    stack = cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)
    stack_id = stack["StackId"]

    cloudformation_backends[ACCOUNT_ID]["us-east-1"].stacks[
        stack_id
    ].status = "ROLLBACK_COMPLETE"

    with pytest.raises(ClientError) as ex:
        cf.update_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert "is in ROLLBACK_COMPLETE state and can not be updated." in err["Message"]


@mock_aws
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
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
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


@mock_aws
def test_cloudformation_conditions_yaml_equals():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
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


@mock_aws
def test_cloudformation_conditions_yaml_equals_shortform():
    _template = dummy_yaml_template_with_equals
    _template = _template.replace("Fn::Equals:", "!Equals")
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
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


@mock_aws
def test_stack_tags():
    tags = [{"Key": "foo", "Value": "bar"}, {"Key": "baz", "Value": "bleh"}]
    cf = boto3.resource("cloudformation", region_name=REGION_NAME)
    stack = cf.create_stack(
        StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json, Tags=tags
    )
    observed_tag_items = set(
        item for items in [tag.items() for tag in stack.tags] for item in items
    )
    expected_tag_items = set(
        item for items in [tag.items() for tag in tags] for item in items
    )
    assert observed_tag_items == expected_tag_items


@mock_aws
def test_stack_events():
    cf = boto3.resource("cloudformation", region_name=REGION_NAME)
    stack = cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)
    stack.update(
        TemplateBody=dummy_update_template_json,
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "value"}],
    )
    stack = cf.Stack(stack.stack_id)
    stack.delete()

    # assert begins and ends with stack events
    events = list(stack.events.all())
    assert events[0].resource_type == "AWS::CloudFormation::Stack"
    assert events[-1].resource_type == "AWS::CloudFormation::Stack"

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
            assert event.stack_id == stack.stack_id
            assert event.stack_name == TEST_STACK_NAME

            if event.resource_type == "AWS::CloudFormation::Stack":
                assert event.logical_resource_id == TEST_STACK_NAME
                assert event.physical_resource_id == stack.stack_id

                status_to_look_for, reason_to_look_for = next(stack_events_to_look_for)
                assert event.resource_status == status_to_look_for
                if reason_to_look_for is not None:
                    assert event.resource_status_reason == reason_to_look_for
    except StopIteration:
        assert False, "Too many stack events"

    assert list(stack_events_to_look_for) == []

    with pytest.raises(ClientError) as exp:
        stack = cf.Stack("non_existing_stack")
        events = list(stack.events.all())

    exp_err = exp.value.response.get("Error")
    exp_metadata = exp.value.response.get("ResponseMetadata")

    assert exp_err["Code"] == "ValidationError"
    assert exp_err["Message"] == "Stack with id non_existing_stack does not exist"
    assert exp_metadata.get("HTTPStatusCode") == 400


@mock_aws
def test_list_exports():
    cf_client = boto3.client("cloudformation", region_name=REGION_NAME)
    cf_resource = boto3.resource("cloudformation", region_name=REGION_NAME)
    stack = cf_resource.create_stack(
        StackName=TEST_STACK_NAME, TemplateBody=dummy_output_template_json
    )
    output_value = "VPCID"
    exports = cf_client.list_exports()["Exports"]

    assert len(stack.outputs) == 1
    assert stack.outputs[0]["OutputValue"] == output_value

    assert len(exports) == 1
    assert exports[0]["ExportingStackId"] == stack.stack_id
    assert exports[0]["Name"] == "My VPC ID"
    assert exports[0]["Value"] == output_value


@mock_aws
def test_list_exports_with_token():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    for i in range(101):
        # Add index to ensure name is unique
        dummy_output_template["Outputs"]["StackVPC"]["Export"]["Name"] += str(i)
        cf.create_stack(
            StackName=f"test_stack_{i}",
            TemplateBody=json.dumps(dummy_output_template),
        )
    exports = cf.list_exports()
    assert len(exports["Exports"]) == 100
    assert exports.get("NextToken") is not None

    more_exports = cf.list_exports(NextToken=exports["NextToken"])
    assert len(more_exports["Exports"]) == 1
    assert more_exports.get("NextToken") is None


@mock_aws
def test_delete_stack_with_export():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    stack = cf.create_stack(
        StackName=TEST_STACK_NAME, TemplateBody=dummy_output_template_json
    )

    stack_id = stack["StackId"]
    exports = cf.list_exports()["Exports"]
    assert len(exports) == 1

    cf.delete_stack(StackName=stack_id)
    assert len(cf.list_exports()["Exports"]) == 0


@mock_aws
def test_export_names_must_be_unique():
    cf = boto3.resource("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_output_template_json)
    with pytest.raises(ClientError):
        cf.create_stack(
            StackName=TEST_STACK_NAME, TemplateBody=dummy_output_template_json
        )


@mock_aws
def test_stack_with_imports():
    cf = boto3.resource("cloudformation", region_name=REGION_NAME)
    ec2_resource = boto3.resource("sqs", region_name=REGION_NAME)

    output_stack = cf.create_stack(
        StackName="test_stack1", TemplateBody=dummy_output_template_json
    )
    cf.create_stack(StackName="test_stack2", TemplateBody=dummy_import_template_json)

    assert len(output_stack.outputs) == 1
    output = output_stack.outputs[0]["OutputValue"]
    assert ec2_resource.get_queue_by_name(QueueName=output)


@mock_aws
def test_non_json_redrive_policy():
    cf = boto3.resource("cloudformation", region_name=REGION_NAME)

    stack = cf.create_stack(
        StackName="test_stack1", TemplateBody=dummy_redrive_template_json
    )

    assert stack.Resource("MainQueue").resource_status == "CREATE_COMPLETE"
    assert stack.Resource("DeadLetterQueue").resource_status == "CREATE_COMPLETE"


@mock_aws
def test_create_duplicate_stack():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)

    with pytest.raises(ClientError):
        cf.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json)


@mock_aws
def test_delete_stack_dynamo_template():
    conn = boto3.client("cloudformation", region_name=REGION_NAME)
    dynamodb_client = boto3.client("dynamodb", region_name=REGION_NAME)
    conn.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json4)
    table_desc = dynamodb_client.list_tables()
    assert len(table_desc.get("TableNames")) == 1
    conn.delete_stack(StackName=TEST_STACK_NAME)
    table_desc = dynamodb_client.list_tables()
    assert len(table_desc.get("TableNames")) == 0
    conn.create_stack(StackName=TEST_STACK_NAME, TemplateBody=dummy_template_json4)


@mock_aws
def test_create_stack_lambda_and_dynamodb():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant set environment variables in server mode")
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
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
                    "Runtime": "python3.11",
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
            StackName="test_stack_lambda", TemplateBody=json.dumps(template)
        )
    finally:
        os.environ["VALIDATE_LAMBDA_S3"] = validate_s3_before

    resources = cf.list_stack_resources(StackName="test_stack_lambda")[
        "StackResourceSummaries"
    ]
    assert len(resources) == 4
    resource_types = [r["ResourceType"] for r in resources]
    assert "AWS::Lambda::Function" in resource_types
    assert "AWS::Lambda::Version" in resource_types
    assert "AWS::DynamoDB::Table" in resource_types
    assert "AWS::Lambda::EventSourceMapping" in resource_types


@mock_aws
def test_create_and_update_stack_with_unknown_resource():
    cf = boto3.client("cloudformation", region_name=REGION_NAME)
    # Creating a stack with an unknown resource should throw a warning
    expected_err = "Tried to parse AWS::Cloud9::EnvironmentEC2 but it's not supported by moto's CloudFormation implementation"
    if settings.TEST_SERVER_MODE:
        # Can't verify warnings in ServerMode though
        cf.create_stack(
            StackName=TEST_STACK_NAME, TemplateBody=dummy_unknown_template_json
        )
    else:
        with pytest.warns(UserWarning, match=expected_err):
            cf.create_stack(
                StackName=TEST_STACK_NAME, TemplateBody=dummy_unknown_template_json
            )

    # The stack should exist though
    stacks = cf.describe_stacks()["Stacks"]
    assert len(stacks) == 1
    assert stacks[0]["StackName"] == TEST_STACK_NAME

    # Updating an unknown resource should throw a warning, but not fail
    new_template = copy.deepcopy(dummy_unknown_template)
    new_template["Resources"]["UnknownResource"]["Properties"]["Sth"] = "other"
    if settings.TEST_SERVER_MODE:
        cf.update_stack(
            StackName=TEST_STACK_NAME, TemplateBody=json.dumps(new_template)
        )
    else:
        with pytest.warns(UserWarning, match=expected_err):
            cf.update_stack(
                StackName=TEST_STACK_NAME, TemplateBody=json.dumps(new_template)
            )


def get_role_name():
    with mock_aws():
        iam = boto3.client("iam", region_name=REGION_NAME)
        try:
            return iam.get_role(RoleName="my-role")["Role"]["Arn"]
        except ClientError:
            return iam.create_role(
                RoleName="my-role",
                AssumeRolePolicyDocument="some policy",
                Path="/my-path/",
            )["Role"]["Arn"]
