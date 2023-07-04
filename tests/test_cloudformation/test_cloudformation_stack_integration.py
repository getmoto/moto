import boto3
import json
import io
import pytest
import zipfile

from botocore.exceptions import ClientError
from decimal import Decimal
from string import Template

from moto import (
    mock_autoscaling,
    mock_cloudformation,
    mock_dynamodb,
    mock_ec2,
    mock_events,
    mock_kms,
    mock_lambda,
    mock_logs,
    mock_s3,
    mock_sqs,
    mock_elbv2,
    mock_ssm,
)
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from tests import EXAMPLE_AMI_ID, EXAMPLE_AMI_ID2
from tests.markers import requires_docker
from tests.test_cloudformation.fixtures import fn_join, single_instance_with_ebs_volume


@mock_cloudformation
def test_create_template_without_required_param_boto3():
    template_json = json.dumps(single_instance_with_ebs_volume.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    with pytest.raises(ClientError) as ex:
        cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    err = ex.value.response["Error"]
    assert err["Code"] == "Missing Parameter"
    assert err["Message"] == "Missing parameter KeyName"


@mock_ec2
@mock_cloudformation
def test_fn_join_boto3():
    template_json = json.dumps(fn_join.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")
    eip = ec2.describe_addresses()["Addresses"][0]

    stack = cf.describe_stacks()["Stacks"][0]
    fn_join_output = stack["Outputs"][0]
    assert fn_join_output["OutputValue"] == f"test eip:{eip['PublicIp']}"


@mock_cloudformation
@mock_sqs
def test_conditional_resources_boto3():
    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Parameters": {
            "EnvType": {"Description": "Environment type.", "Type": "String"}
        },
        "Conditions": {"CreateQueue": {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]}},
        "Resources": {
            "QueueGroup": {
                "Condition": "CreateQueue",
                "Type": "AWS::SQS::Queue",
                "Properties": {"QueueName": "my-queue", "VisibilityTimeout": 60},
            }
        },
    }
    sqs_template_json = json.dumps(sqs_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(
        StackName="test_stack_without_queue",
        TemplateBody=sqs_template_json,
        Parameters=[{"ParameterKey": "EnvType", "ParameterValue": "staging"}],
    )
    sqs = boto3.client("sqs", region_name="us-west-1")
    assert "QueueUrls" not in sqs.list_queues()

    cf.create_stack(
        StackName="test_stack_with_queue",
        TemplateBody=sqs_template_json,
        Parameters=[{"ParameterKey": "EnvType", "ParameterValue": "prod"}],
    )
    assert len(sqs.list_queues()["QueueUrls"]) == 1


@mock_cloudformation
@mock_ec2
def test_conditional_if_handling_boto3():
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Conditions": {"EnvEqualsPrd": {"Fn::Equals": [{"Ref": "ENV"}, "prd"]}},
        "Parameters": {
            "ENV": {
                "Default": "dev",
                "Description": "Deployment environment for the stack (dev/prd)",
                "Type": "String",
            }
        },
        "Description": "Stack 1",
        "Resources": {
            "App1": {
                "Properties": {
                    "ImageId": {
                        "Fn::If": ["EnvEqualsPrd", EXAMPLE_AMI_ID, EXAMPLE_AMI_ID2]
                    }
                },
                "Type": "AWS::EC2::Instance",
            }
        },
    }
    dummy_template_json = json.dumps(dummy_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=dummy_template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2_instance = ec2.describe_instances()["Reservations"][0]["Instances"][0]
    assert ec2_instance["ImageId"] == EXAMPLE_AMI_ID2

    cf = boto3.client("cloudformation", region_name="us-west-2")
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
        Parameters=[{"ParameterKey": "ENV", "ParameterValue": "prd"}],
    )
    ec2 = boto3.client("ec2", region_name="us-west-2")
    ec2_instance = ec2.describe_instances()["Reservations"][0]["Instances"][0]
    assert ec2_instance["ImageId"] == EXAMPLE_AMI_ID


@mock_cloudformation
@mock_ec2
def test_cloudformation_mapping_boto3():
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Mappings": {
            "RegionMap": {
                "us-east-1": {"32": EXAMPLE_AMI_ID, "64": "n/a"},
                "us-west-1": {"32": EXAMPLE_AMI_ID2, "64": "n/a"},
                "eu-west-1": {"32": "n/a", "64": "n/a"},
                "ap-southeast-1": {"32": "n/a", "64": "n/a"},
                "ap-northeast-1": {"32": "n/a", "64": "n/a"},
            }
        },
        "Resources": {
            "WebServer": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": {
                        "Fn::FindInMap": ["RegionMap", {"Ref": "AWS::Region"}, "32"]
                    },
                    "InstanceType": "m1.small",
                },
            }
        },
    }

    dummy_template_json = json.dumps(dummy_template)

    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(StackName="test_stack1", TemplateBody=dummy_template_json)
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2_instance = ec2.describe_instances()["Reservations"][0]["Instances"][0]
    assert ec2_instance["ImageId"] == EXAMPLE_AMI_ID

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack1", TemplateBody=dummy_template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2_instance = ec2.describe_instances()["Reservations"][0]["Instances"][0]
    assert ec2_instance["ImageId"] == EXAMPLE_AMI_ID2


@mock_cloudformation
@mock_lambda
@requires_docker
def test_lambda_function():
    # switch this to python as backend lambda only supports python execution.
    lambda_code = """
def lambda_handler(event, context):
    return {"event": event}
"""
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "lambdaTest": {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "Code": {
                        # CloudFormation expects a string as ZipFile, not a ZIP file base64-encoded
                        "ZipFile": {"Fn::Join": ["\n", lambda_code.splitlines()]}
                    },
                    "Handler": "index.lambda_handler",
                    "Description": "Test function",
                    "MemorySize": 128,
                    "Role": {"Fn::GetAtt": ["MyRole", "Arn"]},
                    "Runtime": "python2.7",
                    "Environment": {"Variables": {"TEST_ENV_KEY": "test-env-val"}},
                    "ReservedConcurrentExecutions": 10,
                },
            },
            "MyRole": {
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
            },
        },
    }

    template_json = json.dumps(template)
    cf_conn = boto3.client("cloudformation", "us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=template_json)

    conn = boto3.client("lambda", "us-east-1")
    result = conn.list_functions()
    assert len(result["Functions"]) == 1
    assert result["Functions"][0]["Description"] == "Test function"
    assert result["Functions"][0]["Handler"] == "index.lambda_handler"
    assert result["Functions"][0]["MemorySize"] == 128
    assert result["Functions"][0]["Runtime"] == "python2.7"
    assert result["Functions"][0]["Environment"] == {
        "Variables": {"TEST_ENV_KEY": "test-env-val"}
    }

    function_name = result["Functions"][0]["FunctionName"]
    result = conn.get_function(FunctionName=function_name)

    assert result["Concurrency"]["ReservedConcurrentExecutions"] == 10

    response = conn.invoke(FunctionName=function_name)
    result = json.loads(response["Payload"].read())
    assert result == {"event": "{}"}


def _make_zipfile(func_str):
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", func_str)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


@mock_cloudformation
@mock_s3
@mock_lambda
def test_lambda_layer():
    # switch this to python as backend lambda only supports python execution.
    layer_code = """
def lambda_handler(event, context):
    return (event, context)
"""
    region = "us-east-1"
    bucket_name = "test_bucket"
    s3_conn = boto3.client("s3", region)
    s3_conn.create_bucket(Bucket=bucket_name)

    zip_content = _make_zipfile(layer_code)
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "lambdaTest": {
                "Type": "AWS::Lambda::LayerVersion",
                "Properties": {
                    "Content": {"S3Bucket": bucket_name, "S3Key": "test.zip"},
                    "LayerName": "testLayer",
                    "Description": "Test Layer",
                    "CompatibleRuntimes": ["python2.7", "python3.6"],
                    "LicenseInfo": "MIT",
                    "CompatibleArchitectures": [],
                },
            },
        },
    }

    template_json = json.dumps(template)
    cf_conn = boto3.client("cloudformation", region)
    cf_conn.create_stack(StackName="test_stack", TemplateBody=template_json)

    lambda_conn = boto3.client("lambda", region)
    result = lambda_conn.list_layers()
    layer_name = result["Layers"][0]["LayerName"]
    result = lambda_conn.list_layer_versions(LayerName=layer_name)
    result["LayerVersions"][0].pop("CreatedDate")
    assert result["LayerVersions"] == [
        {
            "Version": 1,
            "LayerVersionArn": f"arn:aws:lambda:{region}:{ACCOUNT_ID}:layer:{layer_name}:1",
            "CompatibleRuntimes": ["python2.7", "python3.6"],
            "Description": "Test Layer",
            "LicenseInfo": "MIT",
            "CompatibleArchitectures": [],
        }
    ]


@mock_cloudformation
@mock_ec2
def test_nat_gateway():
    ec2_conn = boto3.client("ec2", "us-east-1")
    vpc_id = ec2_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_id = ec2_conn.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc_id)["Subnet"][
        "SubnetId"
    ]
    route_table_id = ec2_conn.create_route_table(VpcId=vpc_id)["RouteTable"][
        "RouteTableId"
    ]

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "NAT": {
                "DependsOn": "vpcgatewayattachment",
                "Type": "AWS::EC2::NatGateway",
                "Properties": {
                    "AllocationId": {"Fn::GetAtt": ["EIP", "AllocationId"]},
                    "SubnetId": subnet_id,
                },
            },
            "EIP": {"Type": "AWS::EC2::EIP", "Properties": {"Domain": "vpc"}},
            "Route": {
                "Type": "AWS::EC2::Route",
                "Properties": {
                    "RouteTableId": route_table_id,
                    "DestinationCidrBlock": "0.0.0.0/0",
                    "NatGatewayId": {"Ref": "NAT"},
                },
            },
            "internetgateway": {"Type": "AWS::EC2::InternetGateway"},
            "vpcgatewayattachment": {
                "Type": "AWS::EC2::VPCGatewayAttachment",
                "Properties": {
                    "InternetGatewayId": {"Ref": "internetgateway"},
                    "VpcId": vpc_id,
                },
            },
        },
    }

    cf_conn = boto3.client("cloudformation", "us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=json.dumps(template))
    stack_resources = cf_conn.list_stack_resources(StackName="test_stack")
    nat_gateway_resource = stack_resources.get("StackResourceSummaries")[0]
    for resource in stack_resources["StackResourceSummaries"]:
        if resource["ResourceType"] == "AWS::EC2::NatGateway":
            nat_gateway_resource = resource
        elif resource["ResourceType"] == "AWS::EC2::Route":
            route_resource = resource

    result = ec2_conn.describe_nat_gateways()
    assert len(result["NatGateways"]) == 1
    assert result["NatGateways"][0]["VpcId"] == vpc_id
    assert result["NatGateways"][0]["SubnetId"] == subnet_id
    assert result["NatGateways"][0]["State"] == "available"
    physical_id = nat_gateway_resource.get("PhysicalResourceId")
    assert result["NatGateways"][0]["NatGatewayId"] == physical_id
    assert "rtb-" in route_resource["PhysicalResourceId"]


@mock_cloudformation()
@mock_kms()
def test_stack_kms():
    kms_key_template = {
        "Resources": {
            "kmskey": {
                "Properties": {
                    "Description": "A kms key",
                    "EnableKeyRotation": True,
                    "Enabled": True,
                    "KeyPolicy": "a policy",
                },
                "Type": "AWS::KMS::Key",
            }
        }
    }
    kms_key_template_json = json.dumps(kms_key_template)

    cf_conn = boto3.client("cloudformation", "us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=kms_key_template_json)

    kms_conn = boto3.client("kms", "us-east-1")
    keys = kms_conn.list_keys()["Keys"]
    assert len(keys) == 1
    result = kms_conn.describe_key(KeyId=keys[0]["KeyId"])

    assert result["KeyMetadata"]["Enabled"] is True
    assert result["KeyMetadata"]["KeyUsage"] == "ENCRYPT_DECRYPT"


@mock_cloudformation()
@mock_ec2()
def test_stack_spot_fleet():
    conn = boto3.client("ec2", "us-east-1")

    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = conn.create_subnet(
        VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/16", AvailabilityZone="us-east-1a"
    )["Subnet"]
    subnet_id = subnet["SubnetId"]

    spot_fleet_template = {
        "Resources": {
            "SpotFleet": {
                "Type": "AWS::EC2::SpotFleet",
                "Properties": {
                    "SpotFleetRequestConfigData": {
                        "IamFleetRole": f"arn:aws:iam::{ACCOUNT_ID}:role/fleet",
                        "SpotPrice": "0.12",
                        "TargetCapacity": 6,
                        "AllocationStrategy": "diversified",
                        "LaunchSpecifications": [
                            {
                                "EbsOptimized": "false",
                                "InstanceType": "t2.small",
                                "ImageId": EXAMPLE_AMI_ID,
                                "SubnetId": subnet_id,
                                "WeightedCapacity": "2",
                                "SpotPrice": "0.13",
                            },
                            {
                                "EbsOptimized": "true",
                                "InstanceType": "t2.large",
                                "ImageId": EXAMPLE_AMI_ID,
                                "Monitoring": {"Enabled": "true"},
                                "SecurityGroups": [{"GroupId": "sg-123"}],
                                "SubnetId": subnet_id,
                                "IamInstanceProfile": {
                                    "Arn": f"arn:aws:iam::{ACCOUNT_ID}:role/fleet"
                                },
                                "WeightedCapacity": "4",
                                "SpotPrice": "10.00",
                            },
                        ],
                    }
                },
            }
        }
    }
    spot_fleet_template_json = json.dumps(spot_fleet_template)

    cf_conn = boto3.client("cloudformation", "us-east-1")
    stack_id = cf_conn.create_stack(
        StackName="test_stack", TemplateBody=spot_fleet_template_json
    )["StackId"]

    stack_resources = cf_conn.list_stack_resources(StackName=stack_id)
    assert len(stack_resources["StackResourceSummaries"]) == 1
    spot_fleet_id = stack_resources["StackResourceSummaries"][0]["PhysicalResourceId"]

    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    assert len(spot_fleet_requests) == 1
    spot_fleet_request = spot_fleet_requests[0]
    assert spot_fleet_request["SpotFleetRequestState"] == "active"
    spot_fleet_config = spot_fleet_request["SpotFleetRequestConfig"]

    assert spot_fleet_config["SpotPrice"] == "0.12"
    assert spot_fleet_config["TargetCapacity"] == 6
    assert spot_fleet_config["IamFleetRole"] == f"arn:aws:iam::{ACCOUNT_ID}:role/fleet"
    assert spot_fleet_config["AllocationStrategy"] == "diversified"
    assert spot_fleet_config["FulfilledCapacity"] == 6.0

    assert len(spot_fleet_config["LaunchSpecifications"]) == 2
    launch_spec = spot_fleet_config["LaunchSpecifications"][0]

    assert launch_spec["EbsOptimized"] is False
    assert launch_spec["ImageId"] == EXAMPLE_AMI_ID
    assert launch_spec["InstanceType"] == "t2.small"
    assert launch_spec["SubnetId"] == subnet_id
    assert launch_spec["SpotPrice"] == "0.13"
    assert launch_spec["WeightedCapacity"] == 2.0


@mock_cloudformation()
@mock_ec2()
def test_stack_spot_fleet_should_figure_out_default_price():
    conn = boto3.client("ec2", "us-east-1")

    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = conn.create_subnet(
        VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/16", AvailabilityZone="us-east-1a"
    )["Subnet"]
    subnet_id = subnet["SubnetId"]

    spot_fleet_template = {
        "Resources": {
            "SpotFleet1": {
                "Type": "AWS::EC2::SpotFleet",
                "Properties": {
                    "SpotFleetRequestConfigData": {
                        "IamFleetRole": f"arn:aws:iam::{ACCOUNT_ID}:role/fleet",
                        "TargetCapacity": 6,
                        "AllocationStrategy": "diversified",
                        "LaunchSpecifications": [
                            {
                                "EbsOptimized": "false",
                                "InstanceType": "t2.small",
                                "ImageId": EXAMPLE_AMI_ID,
                                "SubnetId": subnet_id,
                                "WeightedCapacity": "2",
                            },
                            {
                                "EbsOptimized": "true",
                                "InstanceType": "t2.large",
                                "ImageId": EXAMPLE_AMI_ID,
                                "Monitoring": {"Enabled": "true"},
                                "SecurityGroups": [{"GroupId": "sg-123"}],
                                "SubnetId": subnet_id,
                                "IamInstanceProfile": {
                                    "Arn": f"arn:aws:iam::{ACCOUNT_ID}:role/fleet"
                                },
                                "WeightedCapacity": "4",
                            },
                        ],
                    }
                },
            }
        }
    }
    spot_fleet_template_json = json.dumps(spot_fleet_template)

    cf_conn = boto3.client("cloudformation", "us-east-1")
    stack_id = cf_conn.create_stack(
        StackName="test_stack", TemplateBody=spot_fleet_template_json
    )["StackId"]

    stack_resources = cf_conn.list_stack_resources(StackName=stack_id)
    assert len(stack_resources["StackResourceSummaries"]) == 1
    spot_fleet_id = stack_resources["StackResourceSummaries"][0]["PhysicalResourceId"]

    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    assert len(spot_fleet_requests) == 1
    spot_fleet_request = spot_fleet_requests[0]
    assert spot_fleet_request["SpotFleetRequestState"] == "active"
    spot_fleet_config = spot_fleet_request["SpotFleetRequestConfig"]

    assert "SpotPrice" not in spot_fleet_config
    assert len(spot_fleet_config["LaunchSpecifications"]) == 2
    launch_spec1 = spot_fleet_config["LaunchSpecifications"][0]
    launch_spec2 = spot_fleet_config["LaunchSpecifications"][1]

    assert "SpotPrice" not in launch_spec1
    assert "SpotPrice" not in launch_spec2


@mock_ec2
@mock_elbv2
@mock_cloudformation
def test_invalid_action_type_listener_rule():
    invalid_listener_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "alb": {
                "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
                "Properties": {
                    "Name": "myelbv2",
                    "Scheme": "internet-facing",
                    "Subnets": [{"Ref": "mysubnet"}],
                },
            },
            "mytargetgroup1": {
                "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                "Properties": {"Name": "mytargetgroup1"},
            },
            "mytargetgroup2": {
                "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                "Properties": {"Name": "mytargetgroup2"},
            },
            "listener": {
                "Type": "AWS::ElasticLoadBalancingV2::Listener",
                "Properties": {
                    "DefaultActions": [
                        {"Type": "forward", "TargetGroupArn": {"Ref": "mytargetgroup1"}}
                    ],
                    "LoadBalancerArn": {"Ref": "alb"},
                    "Port": "80",
                    "Protocol": "HTTP",
                },
            },
            "rule": {
                "Type": "AWS::ElasticLoadBalancingV2::ListenerRule",
                "Properties": {
                    "Actions": [
                        {
                            "Type": "forward2",
                            "TargetGroupArn": {"Ref": "mytargetgroup2"},
                        }
                    ],
                    "Conditions": [{"field": "path-pattern", "values": ["/*"]}],
                    "ListenerArn": {"Ref": "listener"},
                    "Priority": 2,
                },
            },
            "myvpc": {
                "Type": "AWS::EC2::VPC",
                "Properties": {"CidrBlock": "10.0.0.0/16"},
            },
            "mysubnet": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {"CidrBlock": "10.0.0.0/27", "VpcId": {"Ref": "myvpc"}},
            },
        },
    }

    listener_template_json = json.dumps(invalid_listener_template)

    cfn_conn = boto3.client("cloudformation", "us-west-1")
    with pytest.raises(ClientError) as exc:
        cfn_conn.create_stack(StackName="s", TemplateBody=listener_template_json)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"


@mock_ec2
@mock_elbv2
@mock_cloudformation
@mock_events
def test_update_stack_listener_and_rule():
    initial_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "alb": {
                "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
                "Properties": {
                    "Name": "myelbv2",
                    "Scheme": "internet-facing",
                    "Subnets": [{"Ref": "mysubnet"}],
                    "SecurityGroups": [{"Ref": "mysg"}],
                    "Type": "application",
                    "IpAddressType": "ipv4",
                },
            },
            "mytargetgroup1": {
                "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                "Properties": {"Name": "mytargetgroup1"},
            },
            "mytargetgroup2": {
                "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                "Properties": {"Name": "mytargetgroup2"},
            },
            "listener": {
                "Type": "AWS::ElasticLoadBalancingV2::Listener",
                "Properties": {
                    "DefaultActions": [
                        {"Type": "forward", "TargetGroupArn": {"Ref": "mytargetgroup1"}}
                    ],
                    "LoadBalancerArn": {"Ref": "alb"},
                    "Port": "80",
                    "Protocol": "HTTP",
                },
            },
            "rule": {
                "Type": "AWS::ElasticLoadBalancingV2::ListenerRule",
                "Properties": {
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": {"Ref": "mytargetgroup2"},
                        }
                    ],
                    "Conditions": [{"Field": "path-pattern", "Values": ["/*"]}],
                    "ListenerArn": {"Ref": "listener"},
                    "Priority": 2,
                },
            },
            "myvpc": {
                "Type": "AWS::EC2::VPC",
                "Properties": {"CidrBlock": "10.0.0.0/16"},
            },
            "mysubnet": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {"CidrBlock": "10.0.0.0/27", "VpcId": {"Ref": "myvpc"}},
            },
            "mysg": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupName": "mysg",
                    "GroupDescription": "test security group",
                    "VpcId": {"Ref": "myvpc"},
                },
            },
        },
    }

    initial_template_json = json.dumps(initial_template)

    cfn_conn = boto3.client("cloudformation", "us-west-1")
    cfn_conn.create_stack(StackName="initial_stack", TemplateBody=initial_template_json)

    elbv2_conn = boto3.client("elbv2", "us-west-1")

    initial_template["Resources"]["rule"]["Properties"]["Conditions"][0][
        "Field"
    ] = "host-header"
    initial_template["Resources"]["rule"]["Properties"]["Conditions"][0]["Values"] = "*"
    initial_template["Resources"]["listener"]["Properties"]["Port"] = 90

    initial_template_json = json.dumps(initial_template)
    cfn_conn.update_stack(StackName="initial_stack", TemplateBody=initial_template_json)

    load_balancers = elbv2_conn.describe_load_balancers()["LoadBalancers"]
    listeners = elbv2_conn.describe_listeners(
        LoadBalancerArn=load_balancers[0]["LoadBalancerArn"]
    )["Listeners"]
    assert listeners[0]["Port"] == 90

    l_rule = elbv2_conn.describe_rules(ListenerArn=listeners[0]["ListenerArn"])["Rules"]

    assert l_rule[0]["Conditions"] == [{"Field": "host-header", "Values": ["*"]}]


@mock_ec2
@mock_elbv2
@mock_cloudformation
def test_stack_elbv2_resources_integration():
    alb_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Outputs": {
            "albdns": {
                "Description": "Load balanacer DNS",
                "Value": {"Fn::GetAtt": ["alb", "DNSName"]},
            },
            "albname": {
                "Description": "Load balancer name",
                "Value": {"Fn::GetAtt": ["alb", "LoadBalancerName"]},
            },
            "canonicalhostedzoneid": {
                "Description": "Load balancer canonical hosted zone ID",
                "Value": {"Fn::GetAtt": ["alb", "CanonicalHostedZoneID"]},
            },
        },
        "Resources": {
            "alb": {
                "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
                "Properties": {
                    "Name": "myelbv2",
                    "Scheme": "internet-facing",
                    "Subnets": [{"Ref": "mysubnet"}],
                    "SecurityGroups": [{"Ref": "mysg"}],
                    "Type": "application",
                    "IpAddressType": "ipv4",
                },
            },
            "mytargetgroup1": {
                "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                "Properties": {
                    "HealthCheckIntervalSeconds": 30,
                    "HealthCheckPath": "/status",
                    "HealthCheckPort": 80,
                    "HealthCheckProtocol": "HTTP",
                    "HealthCheckTimeoutSeconds": 5,
                    "HealthyThresholdCount": 30,
                    "UnhealthyThresholdCount": 5,
                    "Matcher": {"HttpCode": "200,201"},
                    "Name": "mytargetgroup1",
                    "Port": 80,
                    "Protocol": "HTTP",
                    "TargetType": "instance",
                    "Targets": [{"Id": {"Ref": "ec2instance", "Port": 80}}],
                    "VpcId": {"Ref": "myvpc"},
                },
            },
            "mytargetgroup2": {
                "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                "Properties": {
                    "HealthCheckIntervalSeconds": 30,
                    "HealthCheckPath": "/status",
                    "HealthCheckPort": 8080,
                    "HealthCheckProtocol": "HTTP",
                    "HealthCheckTimeoutSeconds": 5,
                    "HealthyThresholdCount": 30,
                    "UnhealthyThresholdCount": 5,
                    "Name": "mytargetgroup2",
                    "Port": 8080,
                    "Protocol": "HTTP",
                    "TargetType": "instance",
                    "Targets": [{"Id": {"Ref": "ec2instance", "Port": 8080}}],
                    "VpcId": {"Ref": "myvpc"},
                },
            },
            "listener": {
                "Type": "AWS::ElasticLoadBalancingV2::Listener",
                "Properties": {
                    "DefaultActions": [
                        {"Type": "forward", "TargetGroupArn": {"Ref": "mytargetgroup1"}}
                    ],
                    "LoadBalancerArn": {"Ref": "alb"},
                    "Port": "80",
                    "Protocol": "HTTP",
                },
            },
            "rule": {
                "Type": "AWS::ElasticLoadBalancingV2::ListenerRule",
                "Properties": {
                    "Actions": [
                        {
                            "Type": "forward",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {
                                        "TargetGroupArn": {"Ref": "mytargetgroup2"},
                                        "Weight": 1,
                                    },
                                    {
                                        "TargetGroupArn": {"Ref": "mytargetgroup1"},
                                        "Weight": 2,
                                    },
                                ]
                            },
                        }
                    ],
                    "Conditions": [{"Field": "path-pattern", "Values": ["/*"]}],
                    "ListenerArn": {"Ref": "listener"},
                    "Priority": 2,
                },
            },
            "rule2": {
                "Type": "AWS::ElasticLoadBalancingV2::ListenerRule",
                "Properties": {
                    "Actions": [
                        {"Type": "forward", "TargetGroupArn": {"Ref": "mytargetgroup2"}}
                    ],
                    "Conditions": [{"Field": "host-header", "Values": ["example.com"]}],
                    "ListenerArn": {"Ref": "listener"},
                    "Priority": 30,
                },
            },
            "myvpc": {
                "Type": "AWS::EC2::VPC",
                "Properties": {"CidrBlock": "10.0.0.0/16"},
            },
            "mysubnet": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {"CidrBlock": "10.0.0.0/27", "VpcId": {"Ref": "myvpc"}},
            },
            "mysg": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupName": "mysg",
                    "GroupDescription": "test security group",
                    "VpcId": {"Ref": "myvpc"},
                },
            },
            "ec2instance": {
                "Type": "AWS::EC2::Instance",
                "Properties": {"ImageId": EXAMPLE_AMI_ID, "UserData": "some user data"},
            },
        },
    }
    alb_template_json = json.dumps(alb_template)

    cfn_conn = boto3.client("cloudformation", "us-west-1")
    cfn_conn.create_stack(StackName="elb_stack", TemplateBody=alb_template_json)

    elbv2_conn = boto3.client("elbv2", "us-west-1")

    lbs = elbv2_conn.describe_load_balancers()["LoadBalancers"]
    assert len(lbs) == 1
    assert lbs[0]["LoadBalancerName"] == "myelbv2"
    assert lbs[0]["Scheme"] == "internet-facing"
    assert lbs[0]["Type"] == "application"
    assert lbs[0]["IpAddressType"] == "ipv4"

    target_groups = elbv2_conn.describe_target_groups()["TargetGroups"]
    # sort to do comparison with indexes
    target_groups = sorted(target_groups, key=lambda tg: tg["TargetGroupName"])
    assert len(target_groups) == 2
    assert target_groups[0]["HealthCheckIntervalSeconds"] == 30
    assert target_groups[0]["HealthCheckPath"] == "/status"
    assert target_groups[0]["HealthCheckPort"] == "80"
    assert target_groups[0]["HealthCheckProtocol"] == "HTTP"
    assert target_groups[0]["HealthCheckTimeoutSeconds"] == 5
    assert target_groups[0]["HealthyThresholdCount"] == 30
    assert target_groups[0]["UnhealthyThresholdCount"] == 5
    assert target_groups[0]["Matcher"] == {"HttpCode": "200,201"}
    assert target_groups[0]["TargetGroupName"] == "mytargetgroup1"
    assert target_groups[0]["Port"] == 80
    assert target_groups[0]["Protocol"] == "HTTP"
    assert target_groups[0]["TargetType"] == "instance"

    assert target_groups[1]["HealthCheckIntervalSeconds"] == 30
    assert target_groups[1]["HealthCheckPath"] == "/status"
    assert target_groups[1]["HealthCheckPort"] == "8080"
    assert target_groups[1]["HealthCheckProtocol"] == "HTTP"
    assert target_groups[1]["HealthCheckTimeoutSeconds"] == 5
    assert target_groups[1]["HealthyThresholdCount"] == 30
    assert target_groups[1]["UnhealthyThresholdCount"] == 5
    assert target_groups[1]["Matcher"] == {"HttpCode": "200"}
    assert target_groups[1]["TargetGroupName"] == "mytargetgroup2"
    assert target_groups[1]["Port"] == 8080
    assert target_groups[1]["Protocol"] == "HTTP"
    assert target_groups[1]["TargetType"] == "instance"

    lstnrs = elbv2_conn.describe_listeners(LoadBalancerArn=lbs[0]["LoadBalancerArn"])[
        "Listeners"
    ]
    assert len(lstnrs) == 1
    assert lstnrs[0]["LoadBalancerArn"] == lbs[0]["LoadBalancerArn"]
    assert lstnrs[0]["Port"] == 80
    assert lstnrs[0]["Protocol"] == "HTTP"
    assert lstnrs[0]["DefaultActions"] == [
        {"Type": "forward", "TargetGroupArn": target_groups[0]["TargetGroupArn"]}
    ]

    rule = elbv2_conn.describe_rules(ListenerArn=lstnrs[0]["ListenerArn"])["Rules"]
    assert len(rule) == 3
    assert rule[0]["Priority"] == "2"
    assert rule[0]["Actions"] == [
        {
            "Type": "forward",
            "ForwardConfig": {
                "TargetGroups": [
                    {
                        "TargetGroupArn": target_groups[1]["TargetGroupArn"],
                        "Weight": 1,
                    },
                    {
                        "TargetGroupArn": target_groups[0]["TargetGroupArn"],
                        "Weight": 2,
                    },
                ],
                "TargetGroupStickinessConfig": {"Enabled": False},
            },
        }
    ]
    assert rule[0]["Conditions"] == [{"Field": "path-pattern", "Values": ["/*"]}]

    assert rule[1]["Priority"] == "30"
    assert rule[1]["Actions"] == [
        {"Type": "forward", "TargetGroupArn": target_groups[1]["TargetGroupArn"]}
    ]
    assert rule[1]["Conditions"] == [
        {"Field": "host-header", "Values": ["example.com"]}
    ]

    # test outputs
    stacks = cfn_conn.describe_stacks(StackName="elb_stack")["Stacks"]
    assert len(stacks) == 1

    dns = list(
        filter(lambda item: item["OutputKey"] == "albdns", stacks[0]["Outputs"])
    )[0]
    name = list(
        filter(lambda item: item["OutputKey"] == "albname", stacks[0]["Outputs"])
    )[0]

    assert dns["OutputValue"] == lbs[0]["DNSName"]
    assert name["OutputValue"] == lbs[0]["LoadBalancerName"]


@mock_dynamodb
@mock_cloudformation
def test_stack_dynamodb_resources_integration():
    dynamodb_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "myDynamoDBTable": {
                "Type": "AWS::DynamoDB::Table",
                "Properties": {
                    "AttributeDefinitions": [
                        {"AttributeName": "Album", "AttributeType": "S"},
                        {"AttributeName": "Artist", "AttributeType": "S"},
                        {"AttributeName": "Sales", "AttributeType": "N"},
                        {"AttributeName": "NumberOfSongs", "AttributeType": "N"},
                    ],
                    "KeySchema": [
                        {"AttributeName": "Album", "KeyType": "HASH"},
                        {"AttributeName": "Artist", "KeyType": "RANGE"},
                    ],
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": "5",
                        "WriteCapacityUnits": "5",
                    },
                    "TableName": "myTableName",
                    "GlobalSecondaryIndexes": [
                        {
                            "IndexName": "myGSI",
                            "KeySchema": [
                                {"AttributeName": "Sales", "KeyType": "HASH"},
                                {"AttributeName": "Artist", "KeyType": "RANGE"},
                            ],
                            "Projection": {
                                "NonKeyAttributes": ["Album", "NumberOfSongs"],
                                "ProjectionType": "INCLUDE",
                            },
                            "ProvisionedThroughput": {
                                "ReadCapacityUnits": "5",
                                "WriteCapacityUnits": "5",
                            },
                        },
                        {
                            "IndexName": "myGSI2",
                            "KeySchema": [
                                {"AttributeName": "NumberOfSongs", "KeyType": "HASH"},
                                {"AttributeName": "Sales", "KeyType": "RANGE"},
                            ],
                            "Projection": {
                                "NonKeyAttributes": ["Album", "Artist"],
                                "ProjectionType": "INCLUDE",
                            },
                            "ProvisionedThroughput": {
                                "ReadCapacityUnits": "5",
                                "WriteCapacityUnits": "5",
                            },
                        },
                    ],
                    "LocalSecondaryIndexes": [
                        {
                            "IndexName": "myLSI",
                            "KeySchema": [
                                {"AttributeName": "Album", "KeyType": "HASH"},
                                {"AttributeName": "Sales", "KeyType": "RANGE"},
                            ],
                            "Projection": {
                                "NonKeyAttributes": ["Artist", "NumberOfSongs"],
                                "ProjectionType": "INCLUDE",
                            },
                        }
                    ],
                    "StreamSpecification": {"StreamViewType": "KEYS_ONLY"},
                },
            }
        },
    }

    dynamodb_template_json = json.dumps(dynamodb_template)

    cfn_conn = boto3.client("cloudformation", "us-east-1")
    cfn_conn.create_stack(
        StackName="dynamodb_stack", TemplateBody=dynamodb_template_json
    )

    dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
    table_desc = dynamodb_client.describe_table(TableName="myTableName")["Table"]
    assert table_desc["StreamSpecification"] == {
        "StreamEnabled": True,
        "StreamViewType": "KEYS_ONLY",
    }

    dynamodb_conn = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb_conn.Table("myTableName")
    assert table.name == "myTableName"

    table.put_item(
        Item={"Album": "myAlbum", "Artist": "myArtist", "Sales": 10, "NumberOfSongs": 5}
    )

    response = table.get_item(Key={"Album": "myAlbum", "Artist": "myArtist"})

    assert response["Item"]["Album"] == "myAlbum"
    assert response["Item"]["Sales"] == Decimal("10")
    assert response["Item"]["NumberOfSongs"] == Decimal("5")
    assert response["Item"]["Album"] == "myAlbum"


@mock_cloudformation
@mock_logs
@mock_s3
def test_create_log_group_using_fntransform():
    s3_resource = boto3.resource("s3")
    s3_resource.create_bucket(
        Bucket="owi-common-cf",
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    s3_resource.Object("owi-common-cf", "snippets/test.json").put(
        Body=json.dumps({"lgname": {"name": "some-log-group"}})
    )
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Mappings": {
            "EnvironmentMapping": {
                "Fn::Transform": {
                    "Name": "AWS::Include",
                    "Parameters": {"Location": "s3://owi-common-cf/snippets/test.json"},
                }
            }
        },
        "Resources": {
            "LogGroup": {
                "Properties": {
                    "LogGroupName": {
                        "Fn::FindInMap": ["EnvironmentMapping", "lgname", "name"]
                    },
                    "RetentionInDays": 90,
                },
                "Type": "AWS::Logs::LogGroup",
            }
        },
    }

    cf_conn = boto3.client("cloudformation", "us-west-2")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=json.dumps(template))

    logs_conn = boto3.client("logs", region_name="us-west-2")
    log_group = logs_conn.describe_log_groups()["logGroups"][0]
    assert log_group["logGroupName"] == "some-log-group"


@mock_cloudformation
@mock_logs
def test_create_cloudwatch_logs_resource_policy():
    policy_document = json.dumps(
        {
            "Statement": [
                {
                    "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                    "Effect": "Allow",
                    "Principal": {"Service": "es.amazonaws.com"},
                    "Resource": "*",
                }
            ]
        }
    )
    template1 = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "LogGroupPolicy1": {
                "Type": "AWS::Logs::ResourcePolicy",
                "Properties": {
                    "PolicyDocument": policy_document,
                    "PolicyName": "TestPolicyA",
                },
            }
        },
    }
    template2 = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "LogGroupPolicy1": {
                "Type": "AWS::Logs::ResourcePolicy",
                "Properties": {
                    "PolicyDocument": policy_document,
                    "PolicyName": "TestPolicyB",
                },
            },
            "LogGroupPolicy2": {
                "Type": "AWS::Logs::ResourcePolicy",
                "Properties": {
                    "PolicyDocument": policy_document,
                    "PolicyName": "TestPolicyC",
                },
            },
        },
    }

    cf_conn = boto3.client("cloudformation", "us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=json.dumps(template1))

    logs_conn = boto3.client("logs", region_name="us-east-1")
    policies = logs_conn.describe_resource_policies()["resourcePolicies"]
    assert len(policies) == 1

    assert policies[0]["policyName"] == "TestPolicyA"
    assert policies[0]["policyDocument"] == policy_document

    cf_conn.update_stack(StackName="test_stack", TemplateBody=json.dumps(template2))
    policies = logs_conn.describe_resource_policies()["resourcePolicies"]
    assert len(policies) == 2

    policy_b = [pol for pol in policies if pol["policyName"] == "TestPolicyB"][0][
        "policyDocument"
    ]
    assert policy_b == policy_document

    policy_c = [pol for pol in policies if pol["policyName"] == "TestPolicyC"][0][
        "policyDocument"
    ]
    assert policy_c == policy_document

    cf_conn.update_stack(StackName="test_stack", TemplateBody=json.dumps(template1))
    policies = logs_conn.describe_resource_policies()["resourcePolicies"]
    assert len(policies) == 1
    assert policies[0]["policyName"] == "TestPolicyA"
    assert policies[0]["policyDocument"] == policy_document


@mock_cloudformation
@mock_logs
def test_delete_stack_containing_cloudwatch_logs_resource_policy():
    template1 = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "LogGroupPolicy1": {
                "Type": "AWS::Logs::ResourcePolicy",
                "Properties": {
                    "PolicyDocument": '{"Statement":[{"Action":"logs:*","Effect":"Allow","Principal":"*","Resource":"*"}]}',
                    "PolicyName": "TestPolicyA",
                },
            }
        },
    }

    cf_conn = boto3.client("cloudformation", "us-east-1")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=json.dumps(template1))

    logs_conn = boto3.client("logs", region_name="us-east-1")
    policies = logs_conn.describe_resource_policies()["resourcePolicies"]
    assert len(policies) == 1

    cf_conn.delete_stack(StackName="test_stack")
    policies = logs_conn.describe_resource_policies()["resourcePolicies"]
    assert len(policies) == 0


@mock_cloudformation
@mock_sqs
def test_delete_stack_with_deletion_policy_boto3():
    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "QueueGroup": {
                "DeletionPolicy": "Retain",
                "Type": "AWS::SQS::Queue",
                "Properties": {"QueueName": "my-queue", "VisibilityTimeout": 60},
            }
        },
    }

    sqs_template_json = json.dumps(sqs_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=sqs_template_json,
    )
    sqs = boto3.client("sqs", region_name="us-west-1")
    assert len(sqs.list_queues()["QueueUrls"]) == 1

    cf.delete_stack(StackName="test_stack")
    assert len(sqs.list_queues()["QueueUrls"]) == 1


@mock_cloudformation
@mock_events
def test_stack_events_create_rule_integration():
    events_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "Event": {
                "Type": "AWS::Events::Rule",
                "Properties": {
                    "Name": "quick-fox",
                    "State": "ENABLED",
                    "ScheduleExpression": "rate(5 minutes)",
                },
            }
        },
    }
    cf_conn = boto3.client("cloudformation", "us-west-2")
    cf_conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(events_template)
    )

    rules = boto3.client("events", "us-west-2").list_rules()
    assert len(rules["Rules"]) == 1
    assert rules["Rules"][0]["Name"] == "quick-fox"
    assert rules["Rules"][0]["State"] == "ENABLED"
    assert rules["Rules"][0]["ScheduleExpression"] == "rate(5 minutes)"


@mock_cloudformation
@mock_events
def test_stack_events_delete_rule_integration():
    events_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "Event": {
                "Type": "AWS::Events::Rule",
                "Properties": {
                    "Name": "quick-fox",
                    "State": "ENABLED",
                    "ScheduleExpression": "rate(5 minutes)",
                },
            }
        },
    }
    cf_conn = boto3.client("cloudformation", "us-west-2")
    cf_conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(events_template)
    )

    rules = boto3.client("events", "us-west-2").list_rules()
    assert len(rules["Rules"]) == 1

    cf_conn.delete_stack(StackName="test_stack")

    rules = boto3.client("events", "us-west-2").list_rules()
    assert len(rules["Rules"]) == 0


@mock_cloudformation
@mock_events
def test_stack_events_create_rule_without_name_integration():
    events_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "Event": {
                "Type": "AWS::Events::Rule",
                "Properties": {
                    "State": "ENABLED",
                    "ScheduleExpression": "rate(5 minutes)",
                },
            }
        },
    }
    cf_conn = boto3.client("cloudformation", "us-west-2")
    cf_conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(events_template)
    )

    rules = boto3.client("events", "us-west-2").list_rules()
    assert "test_stack-Event-" in rules["Rules"][0]["Name"]


@mock_cloudformation
@mock_events
@mock_logs
def test_stack_events_create_rule_as_target():
    events_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "SecurityGroup": {
                "Type": "AWS::Logs::LogGroup",
                "Properties": {
                    "LogGroupName": {"Fn::GetAtt": ["Event", "Arn"]},
                    "RetentionInDays": 3,
                },
            },
            "Event": {
                "Type": "AWS::Events::Rule",
                "Properties": {
                    "State": "ENABLED",
                    "ScheduleExpression": "rate(5 minutes)",
                },
            },
        },
    }
    cf_conn = boto3.client("cloudformation", "us-west-2")
    cf_conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(events_template)
    )

    rules = boto3.client("events", "us-west-2").list_rules()
    log_groups = boto3.client("logs", "us-west-2").describe_log_groups()

    assert "test_stack-Event-" in rules["Rules"][0]["Name"]

    assert log_groups["logGroups"][0]["logGroupName"] == rules["Rules"][0]["Arn"]
    assert log_groups["logGroups"][0]["retentionInDays"] == 3


@mock_cloudformation
@mock_events
def test_stack_events_update_rule_integration():
    events_template = Template(
        """{
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "Event": {
                "Type": "AWS::Events::Rule",
                "Properties": {
                    "Name": "$Name",
                    "State": "$State",
                    "ScheduleExpression": "rate(5 minutes)",
                },
            }
        },
    } """
    )

    cf_conn = boto3.client("cloudformation", "us-west-2")

    original_template = events_template.substitute(Name="Foo", State="ENABLED")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=original_template)

    rules = boto3.client("events", "us-west-2").list_rules()
    assert len(rules["Rules"]) == 1
    assert rules["Rules"][0]["Name"] == "Foo"
    assert rules["Rules"][0]["State"] == "ENABLED"

    update_template = events_template.substitute(Name="Bar", State="DISABLED")
    cf_conn.update_stack(StackName="test_stack", TemplateBody=update_template)

    rules = boto3.client("events", "us-west-2").list_rules()

    assert len(rules["Rules"]) == 1
    assert rules["Rules"][0]["Name"] == "Bar"
    assert rules["Rules"][0]["State"] == "DISABLED"


@mock_cloudformation
@mock_autoscaling
def test_autoscaling_propagate_tags():
    autoscaling_group_with_tags = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "AutoScalingGroup": {
                "Type": "AWS::AutoScaling::AutoScalingGroup",
                "Properties": {
                    "AutoScalingGroupName": "test-scaling-group",
                    "DesiredCapacity": 1,
                    "MinSize": 1,
                    "MaxSize": 50,
                    "LaunchConfigurationName": "test-launch-config",
                    "AvailabilityZones": ["us-east-1a"],
                    "Tags": [
                        {
                            "Key": "test-key-propagate",
                            "Value": "test",
                            "PropagateAtLaunch": True,
                        },
                        {
                            "Key": "test-key-no-propagate",
                            "Value": "test",
                            "PropagateAtLaunch": False,
                        },
                    ],
                },
                "DependsOn": "LaunchConfig",
            },
            "LaunchConfig": {
                "Type": "AWS::AutoScaling::LaunchConfiguration",
                "Properties": {
                    "LaunchConfigurationName": "test-launch-config",
                    "ImageId": EXAMPLE_AMI_ID,
                    "InstanceType": "t2.medium",
                },
            },
            "ScheduledAction": {
                "Type": "AWS::AutoScaling::ScheduledAction",
                "Properties": {
                    "AutoScalingGroupName": "test-scaling-group",
                    "DesiredCapacity": 10,
                    "EndTime": "2022-08-01T00:00:00Z",
                    "MaxSize": 15,
                    "MinSize": 5,
                    "Recurrence": "* * * * *",
                    "StartTime": "2022-07-01T00:00:00Z",
                },
            },
        },
    }
    boto3.client("cloudformation", "us-east-1").create_stack(
        StackName="propagate_tags_test",
        TemplateBody=json.dumps(autoscaling_group_with_tags),
    )

    autoscaling = boto3.client("autoscaling", "us-east-1")

    autoscaling_group_tags = autoscaling.describe_auto_scaling_groups()[
        "AutoScalingGroups"
    ][0]["Tags"]
    propagation_dict = {
        tag["Key"]: tag["PropagateAtLaunch"] for tag in autoscaling_group_tags
    }

    assert propagation_dict["test-key-propagate"]
    assert not propagation_dict["test-key-no-propagate"]


@mock_cloudformation
@mock_events
def test_stack_eventbus_create_from_cfn_integration():
    eventbus_template = """{
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "EventBus": {
                "Type": "AWS::Events::EventBus",
                "Properties": {
                    "Name": "MyCustomEventBus"
                },
            }
        },
    }"""

    cf_conn = boto3.client("cloudformation", "us-west-2")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=eventbus_template)

    event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="MyCustom"
    )

    assert len(event_buses["EventBuses"]) == 1
    assert event_buses["EventBuses"][0]["Name"] == "MyCustomEventBus"


@mock_cloudformation
@mock_events
def test_stack_events_delete_eventbus_integration():
    eventbus_template = """{
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "EventBus": {
                "Type": "AWS::Events::EventBus",
                "Properties": {
                    "Name": "MyCustomEventBus"
                },
            }
        },
    }"""
    cf_conn = boto3.client("cloudformation", "us-west-2")
    cf_conn.create_stack(StackName="test_stack", TemplateBody=eventbus_template)

    event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="MyCustom"
    )
    assert len(event_buses["EventBuses"]) == 1

    cf_conn.delete_stack(StackName="test_stack")

    event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="MyCustom"
    )
    assert len(event_buses["EventBuses"]) == 0


@mock_cloudformation
@mock_events
def test_stack_events_delete_from_cfn_integration():
    eventbus_template = Template(
        """{
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "$resource_name": {
                "Type": "AWS::Events::EventBus",
                "Properties": {
                    "Name": "$name"
                },
            }
        },
    }"""
    )

    cf_conn = boto3.client("cloudformation", "us-west-2")

    original_template = eventbus_template.substitute(
        {"resource_name": "original", "name": "MyCustomEventBus"}
    )
    cf_conn.create_stack(StackName="test_stack", TemplateBody=original_template)

    original_event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="MyCustom"
    )
    assert len(original_event_buses["EventBuses"]) == 1

    original_eventbus = original_event_buses["EventBuses"][0]

    updated_template = eventbus_template.substitute(
        {"resource_name": "updated", "name": "AnotherEventBus"}
    )
    cf_conn.update_stack(StackName="test_stack", TemplateBody=updated_template)

    update_event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="AnotherEventBus"
    )
    assert len(update_event_buses["EventBuses"]) == 1
    assert update_event_buses["EventBuses"][0]["Arn"] != original_eventbus["Arn"]


@mock_cloudformation
@mock_events
def test_stack_events_update_from_cfn_integration():
    eventbus_template = Template(
        """{
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "EventBus": {
                "Type": "AWS::Events::EventBus",
                "Properties": {
                    "Name": "$name"
                },
            }
        },
    }"""
    )

    cf_conn = boto3.client("cloudformation", "us-west-2")

    original_template = eventbus_template.substitute({"name": "MyCustomEventBus"})
    cf_conn.create_stack(StackName="test_stack", TemplateBody=original_template)

    original_event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="MyCustom"
    )
    assert len(original_event_buses["EventBuses"]) == 1

    original_eventbus = original_event_buses["EventBuses"][0]

    updated_template = eventbus_template.substitute({"name": "NewEventBus"})
    cf_conn.update_stack(StackName="test_stack", TemplateBody=updated_template)

    update_event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="NewEventBus"
    )
    assert len(update_event_buses["EventBuses"]) == 1
    assert update_event_buses["EventBuses"][0]["Name"] == "NewEventBus"
    assert update_event_buses["EventBuses"][0]["Arn"] != original_eventbus["Arn"]


@mock_cloudformation
@mock_events
def test_stack_events_get_attribute_integration():
    eventbus_template = """{
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "EventBus": {
                "Type": "AWS::Events::EventBus",
                "Properties": {
                    "Name": "MyEventBus"
                },
            }
        },
        "Outputs": {
            "bus_arn": {"Value": {"Fn::GetAtt": ["EventBus", "Arn"]}},
            "bus_name": {"Value": {"Fn::GetAtt": ["EventBus", "Name"]}},
        }
    }"""

    cf = boto3.client("cloudformation", "us-west-2")
    events = boto3.client("events", "us-west-2")

    cf.create_stack(StackName="test_stack", TemplateBody=eventbus_template)

    stack = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    outputs = stack["Outputs"]

    output_arn = list(filter(lambda item: item["OutputKey"] == "bus_arn", outputs))[0]
    output_name = list(filter(lambda item: item["OutputKey"] == "bus_name", outputs))[0]

    event_bus = events.list_event_buses(NamePrefix="MyEventBus")["EventBuses"][0]

    assert output_arn["OutputValue"] == event_bus["Arn"]
    assert output_name["OutputValue"] == event_bus["Name"]


@mock_cloudformation
@mock_dynamodb
def test_dynamodb_table_creation():
    CFN_TEMPLATE = {
        "Outputs": {"MyTableName": {"Value": {"Ref": "MyTable"}}},
        "Resources": {
            "MyTable": {
                "Type": "AWS::DynamoDB::Table",
                "Properties": {
                    "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
                    "AttributeDefinitions": [
                        {"AttributeName": "id", "AttributeType": "S"}
                    ],
                    "BillingMode": "PAY_PER_REQUEST",
                },
            },
        },
    }
    stack_name = "foobar"
    cfn = boto3.client("cloudformation", "us-west-2")
    cfn.create_stack(StackName=stack_name, TemplateBody=json.dumps(CFN_TEMPLATE))
    # Wait until moto creates the stack
    waiter = cfn.get_waiter("stack_create_complete")
    waiter.wait(StackName=stack_name)
    # Verify the TableName is part of the outputs
    stack = cfn.describe_stacks(StackName=stack_name)["Stacks"][0]
    outputs = stack["Outputs"]
    assert len(outputs) == 1
    assert outputs[0]["OutputKey"] == "MyTableName"
    assert "foobar" in outputs[0]["OutputValue"]
    # Assert the table is created
    ddb = boto3.client("dynamodb", "us-west-2")
    table_names = ddb.list_tables()["TableNames"]
    assert table_names == [outputs[0]["OutputValue"]]


@mock_cloudformation
@mock_ssm
def test_ssm_parameter():
    parameter_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "BasicParameter": {
                "Type": "AWS::SSM::Parameter",
                "Properties": {
                    "Name": "test_ssm",
                    "Type": "String",
                    "Value": "Test SSM Parameter",
                    "Description": "Test SSM Description",
                    "AllowedPattern": "^[a-zA-Z]{1,10}$",
                },
            }
        },
    }
    stack_name = "test_stack"
    cfn = boto3.client("cloudformation", "us-west-2")
    cfn.create_stack(StackName=stack_name, TemplateBody=json.dumps(parameter_template))
    # Wait until moto creates the stack
    waiter = cfn.get_waiter("stack_create_complete")
    waiter.wait(StackName=stack_name)

    stack_resources = cfn.list_stack_resources(StackName=stack_name)
    ssm_resource = stack_resources.get("StackResourceSummaries")[0]
    assert ssm_resource.get("PhysicalResourceId") == "test_ssm"

    ssm_client = boto3.client("ssm", region_name="us-west-2")
    parameters = ssm_client.get_parameters(Names=["test_ssm"], WithDecryption=False)[
        "Parameters"
    ]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "test_ssm"
    assert parameters[0]["Value"] == "Test SSM Parameter"


@mock_cloudformation
@mock_ssm
def test_ssm_parameter_update_stack():
    parameter_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "BasicParameter": {
                "Type": "AWS::SSM::Parameter",
                "Properties": {
                    "Name": "test_ssm",
                    "Type": "String",
                    "Value": "Test SSM Parameter",
                    "Description": "Test SSM Description",
                    "AllowedPattern": "^[a-zA-Z]{1,10}$",
                },
            }
        },
    }
    stack_name = "test_stack"
    cfn = boto3.client("cloudformation", "us-west-2")
    cfn.create_stack(StackName=stack_name, TemplateBody=json.dumps(parameter_template))
    # Wait until moto creates the stack
    waiter = cfn.get_waiter("stack_create_complete")
    waiter.wait(StackName=stack_name)

    ssm_client = boto3.client("ssm", region_name="us-west-2")
    parameters = ssm_client.get_parameters(Names=["test_ssm"], WithDecryption=False)[
        "Parameters"
    ]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "test_ssm"
    assert parameters[0]["Value"] == "Test SSM Parameter"

    parameter_template["Resources"]["BasicParameter"]["Properties"][
        "Value"
    ] = "Test SSM Parameter Updated"
    cfn.update_stack(StackName=stack_name, TemplateBody=json.dumps(parameter_template))

    ssm_client = boto3.client("ssm", region_name="us-west-2")
    parameters = ssm_client.get_parameters(Names=["test_ssm"], WithDecryption=False)[
        "Parameters"
    ]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "test_ssm"
    assert parameters[0]["Value"] == "Test SSM Parameter Updated"


@mock_cloudformation
@mock_ssm
def test_ssm_parameter_update_stack_and_remove_resource():
    parameter_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "BasicParameter": {
                "Type": "AWS::SSM::Parameter",
                "Properties": {
                    "Name": "test_ssm",
                    "Type": "String",
                    "Value": "Test SSM Parameter",
                    "Description": "Test SSM Description",
                    "AllowedPattern": "^[a-zA-Z]{1,10}$",
                },
            }
        },
    }
    stack_name = "test_stack"
    cfn = boto3.client("cloudformation", "us-west-2")
    cfn.create_stack(StackName=stack_name, TemplateBody=json.dumps(parameter_template))
    # Wait until moto creates the stack
    waiter = cfn.get_waiter("stack_create_complete")
    waiter.wait(StackName=stack_name)

    ssm_client = boto3.client("ssm", region_name="us-west-2")
    parameters = ssm_client.get_parameters(Names=["test_ssm"], WithDecryption=False)[
        "Parameters"
    ]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "test_ssm"
    assert parameters[0]["Value"] == "Test SSM Parameter"

    parameter_template["Resources"].pop("BasicParameter")
    cfn.update_stack(StackName=stack_name, TemplateBody=json.dumps(parameter_template))

    ssm_client = boto3.client("ssm", region_name="us-west-1")
    parameters = ssm_client.get_parameters(Names=["test_ssm"], WithDecryption=False)[
        "Parameters"
    ]
    assert len(parameters) == 0


@mock_cloudformation
@mock_ssm
def test_ssm_parameter_update_stack_and_add_resource():
    parameter_template = {"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}
    stack_name = "test_stack"
    cfn = boto3.client("cloudformation", "us-west-2")
    cfn.create_stack(StackName=stack_name, TemplateBody=json.dumps(parameter_template))
    # Wait until moto creates the stack
    waiter = cfn.get_waiter("stack_create_complete")
    waiter.wait(StackName=stack_name)

    ssm_client = boto3.client("ssm", region_name="us-west-2")
    parameters = ssm_client.get_parameters(Names=["test_ssm"], WithDecryption=False)[
        "Parameters"
    ]
    assert len(parameters) == 0

    parameter_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "BasicParameter": {
                "Type": "AWS::SSM::Parameter",
                "Properties": {
                    "Name": "test_ssm",
                    "Type": "String",
                    "Value": "Test SSM Parameter",
                    "Description": "Test SSM Description",
                    "AllowedPattern": "^[a-zA-Z]{1,10}$",
                },
            }
        },
    }
    cfn.update_stack(StackName=stack_name, TemplateBody=json.dumps(parameter_template))

    ssm_client = boto3.client("ssm", region_name="us-west-2")
    parameters = ssm_client.get_parameters(Names=["test_ssm"], WithDecryption=False)[
        "Parameters"
    ]
    assert len(parameters) == 1
    assert parameters[0]["Name"] == "test_ssm"
    assert parameters[0]["Value"] == "Test SSM Parameter"
