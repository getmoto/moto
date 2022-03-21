import json
import io
import zipfile

from decimal import Decimal

from botocore.exceptions import ClientError
import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest
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
)
from moto.core import ACCOUNT_ID

from tests import EXAMPLE_AMI_ID, EXAMPLE_AMI_ID2
from tests.test_cloudformation.fixtures import fn_join, single_instance_with_ebs_volume


@mock_cloudformation
def test_create_template_without_required_param_boto3():
    template_json = json.dumps(single_instance_with_ebs_volume.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    with pytest.raises(ClientError) as ex:
        cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    err = ex.value.response["Error"]
    err.should.have.key("Code").equal("Missing Parameter")
    err.should.have.key("Message").equal("Missing parameter KeyName")


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
    fn_join_output["OutputValue"].should.equal("test eip:{0}".format(eip["PublicIp"]))


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
    sqs.list_queues().shouldnt.have.key("QueueUrls")

    cf.create_stack(
        StackName="test_stack_with_queue",
        TemplateBody=sqs_template_json,
        Parameters=[{"ParameterKey": "EnvType", "ParameterValue": "prod"}],
    )
    sqs.list_queues()["QueueUrls"].should.have.length_of(1)


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
    ec2_instance["ImageId"].should.equal(EXAMPLE_AMI_ID2)

    cf = boto3.client("cloudformation", region_name="us-west-2")
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=dummy_template_json,
        Parameters=[{"ParameterKey": "ENV", "ParameterValue": "prd"}],
    )
    ec2 = boto3.client("ec2", region_name="us-west-2")
    ec2_instance = ec2.describe_instances()["Reservations"][0]["Instances"][0]
    ec2_instance["ImageId"].should.equal(EXAMPLE_AMI_ID)


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
    ec2_instance["ImageId"].should.equal(EXAMPLE_AMI_ID)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack1", TemplateBody=dummy_template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2_instance = ec2.describe_instances()["Reservations"][0]["Instances"][0]
    ec2_instance["ImageId"].should.equal(EXAMPLE_AMI_ID2)


@mock_cloudformation
@mock_lambda
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
    result["Functions"].should.have.length_of(1)
    result["Functions"][0]["Description"].should.equal("Test function")
    result["Functions"][0]["Handler"].should.equal("index.lambda_handler")
    result["Functions"][0]["MemorySize"].should.equal(128)
    result["Functions"][0]["Runtime"].should.equal("python2.7")
    result["Functions"][0]["Environment"].should.equal(
        {"Variables": {"TEST_ENV_KEY": "test-env-val"}}
    )

    function_name = result["Functions"][0]["FunctionName"]
    result = conn.get_function(FunctionName=function_name)

    result["Concurrency"]["ReservedConcurrentExecutions"].should.equal(10)

    response = conn.invoke(FunctionName=function_name)
    result = json.loads(response["Payload"].read())
    result.should.equal({"event": "{}"})


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
    result["LayerVersions"].should.equal(
        [
            {
                "Version": 1,
                "LayerVersionArn": "arn:aws:lambda:{}:{}:layer:{}:1".format(
                    region, ACCOUNT_ID, layer_name
                ),
                "CompatibleRuntimes": ["python2.7", "python3.6"],
                "Description": "Test Layer",
                "LicenseInfo": "MIT",
            }
        ]
    )


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
    result["NatGateways"].should.have.length_of(1)
    result["NatGateways"][0]["VpcId"].should.equal(vpc_id)
    result["NatGateways"][0]["SubnetId"].should.equal(subnet_id)
    result["NatGateways"][0]["State"].should.equal("available")
    result["NatGateways"][0]["NatGatewayId"].should.equal(
        nat_gateway_resource.get("PhysicalResourceId")
    )
    route_resource.get("PhysicalResourceId").should.contain("rtb-")


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
    len(keys).should.equal(1)
    result = kms_conn.describe_key(KeyId=keys[0]["KeyId"])

    result["KeyMetadata"]["Enabled"].should.equal(True)
    result["KeyMetadata"]["KeyUsage"].should.equal("ENCRYPT_DECRYPT")


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
                        "IamFleetRole": "arn:aws:iam::{}:role/fleet".format(ACCOUNT_ID),
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
                                    "Arn": "arn:aws:iam::{}:role/fleet".format(
                                        ACCOUNT_ID
                                    )
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
    stack_resources["StackResourceSummaries"].should.have.length_of(1)
    spot_fleet_id = stack_resources["StackResourceSummaries"][0]["PhysicalResourceId"]

    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    len(spot_fleet_requests).should.equal(1)
    spot_fleet_request = spot_fleet_requests[0]
    spot_fleet_request["SpotFleetRequestState"].should.equal("active")
    spot_fleet_config = spot_fleet_request["SpotFleetRequestConfig"]

    spot_fleet_config["SpotPrice"].should.equal("0.12")
    spot_fleet_config["TargetCapacity"].should.equal(6)
    spot_fleet_config["IamFleetRole"].should.equal(
        "arn:aws:iam::{}:role/fleet".format(ACCOUNT_ID)
    )
    spot_fleet_config["AllocationStrategy"].should.equal("diversified")
    spot_fleet_config["FulfilledCapacity"].should.equal(6.0)

    len(spot_fleet_config["LaunchSpecifications"]).should.equal(2)
    launch_spec = spot_fleet_config["LaunchSpecifications"][0]

    launch_spec["EbsOptimized"].should.equal(False)
    launch_spec["ImageId"].should.equal(EXAMPLE_AMI_ID)
    launch_spec["InstanceType"].should.equal("t2.small")
    launch_spec["SubnetId"].should.equal(subnet_id)
    launch_spec["SpotPrice"].should.equal("0.13")
    launch_spec["WeightedCapacity"].should.equal(2.0)


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
                        "IamFleetRole": "arn:aws:iam::{}:role/fleet".format(ACCOUNT_ID),
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
                                    "Arn": "arn:aws:iam::{}:role/fleet".format(
                                        ACCOUNT_ID
                                    )
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
    stack_resources["StackResourceSummaries"].should.have.length_of(1)
    spot_fleet_id = stack_resources["StackResourceSummaries"][0]["PhysicalResourceId"]

    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    len(spot_fleet_requests).should.equal(1)
    spot_fleet_request = spot_fleet_requests[0]
    spot_fleet_request["SpotFleetRequestState"].should.equal("active")
    spot_fleet_config = spot_fleet_request["SpotFleetRequestConfig"]

    assert "SpotPrice" not in spot_fleet_config
    len(spot_fleet_config["LaunchSpecifications"]).should.equal(2)
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
    cfn_conn.create_stack.when.called_with(
        StackName="listener_stack", TemplateBody=listener_template_json
    ).should.throw(ClientError)


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
    listeners[0]["Port"].should.equal(90)

    listener_rule = elbv2_conn.describe_rules(ListenerArn=listeners[0]["ListenerArn"])[
        "Rules"
    ]

    listener_rule[0]["Conditions"].should.equal(
        [{"Field": "host-header", "Values": ["*"]}]
    )


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

    load_balancers = elbv2_conn.describe_load_balancers()["LoadBalancers"]
    len(load_balancers).should.equal(1)
    load_balancers[0]["LoadBalancerName"].should.equal("myelbv2")
    load_balancers[0]["Scheme"].should.equal("internet-facing")
    load_balancers[0]["Type"].should.equal("application")
    load_balancers[0]["IpAddressType"].should.equal("ipv4")

    target_groups = sorted(
        elbv2_conn.describe_target_groups()["TargetGroups"],
        key=lambda tg: tg["TargetGroupName"],
    )  # sort to do comparison with indexes
    len(target_groups).should.equal(2)
    target_groups[0]["HealthCheckIntervalSeconds"].should.equal(30)
    target_groups[0]["HealthCheckPath"].should.equal("/status")
    target_groups[0]["HealthCheckPort"].should.equal("80")
    target_groups[0]["HealthCheckProtocol"].should.equal("HTTP")
    target_groups[0]["HealthCheckTimeoutSeconds"].should.equal(5)
    target_groups[0]["HealthyThresholdCount"].should.equal(30)
    target_groups[0]["UnhealthyThresholdCount"].should.equal(5)
    target_groups[0]["Matcher"].should.equal({"HttpCode": "200,201"})
    target_groups[0]["TargetGroupName"].should.equal("mytargetgroup1")
    target_groups[0]["Port"].should.equal(80)
    target_groups[0]["Protocol"].should.equal("HTTP")
    target_groups[0]["TargetType"].should.equal("instance")

    target_groups[1]["HealthCheckIntervalSeconds"].should.equal(30)
    target_groups[1]["HealthCheckPath"].should.equal("/status")
    target_groups[1]["HealthCheckPort"].should.equal("8080")
    target_groups[1]["HealthCheckProtocol"].should.equal("HTTP")
    target_groups[1]["HealthCheckTimeoutSeconds"].should.equal(5)
    target_groups[1]["HealthyThresholdCount"].should.equal(30)
    target_groups[1]["UnhealthyThresholdCount"].should.equal(5)
    target_groups[1]["Matcher"].should.equal({"HttpCode": "200"})
    target_groups[1]["TargetGroupName"].should.equal("mytargetgroup2")
    target_groups[1]["Port"].should.equal(8080)
    target_groups[1]["Protocol"].should.equal("HTTP")
    target_groups[1]["TargetType"].should.equal("instance")

    listeners = elbv2_conn.describe_listeners(
        LoadBalancerArn=load_balancers[0]["LoadBalancerArn"]
    )["Listeners"]
    len(listeners).should.equal(1)
    listeners[0]["LoadBalancerArn"].should.equal(load_balancers[0]["LoadBalancerArn"])
    listeners[0]["Port"].should.equal(80)
    listeners[0]["Protocol"].should.equal("HTTP")
    listeners[0]["DefaultActions"].should.equal(
        [{"Type": "forward", "TargetGroupArn": target_groups[0]["TargetGroupArn"]}]
    )

    listener_rule = elbv2_conn.describe_rules(ListenerArn=listeners[0]["ListenerArn"])[
        "Rules"
    ]
    len(listener_rule).should.equal(3)
    listener_rule[0]["Priority"].should.equal("2")
    listener_rule[0]["Actions"].should.equal(
        [
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
        ],
        [{"Type": "forward", "TargetGroupArn": target_groups[1]["TargetGroupArn"]}],
    )
    listener_rule[0]["Conditions"].should.equal(
        [{"Field": "path-pattern", "Values": ["/*"]}]
    )

    listener_rule[1]["Priority"].should.equal("30")
    listener_rule[1]["Actions"].should.equal(
        [{"Type": "forward", "TargetGroupArn": target_groups[1]["TargetGroupArn"]}]
    )
    listener_rule[1]["Conditions"].should.equal(
        [{"Field": "host-header", "Values": ["example.com"]}]
    )

    # test outputs
    stacks = cfn_conn.describe_stacks(StackName="elb_stack")["Stacks"]
    len(stacks).should.equal(1)

    dns = list(
        filter(lambda item: item["OutputKey"] == "albdns", stacks[0]["Outputs"])
    )[0]
    name = list(
        filter(lambda item: item["OutputKey"] == "albname", stacks[0]["Outputs"])
    )[0]

    dns["OutputValue"].should.equal(load_balancers[0]["DNSName"])
    name["OutputValue"].should.equal(load_balancers[0]["LoadBalancerName"])


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
    table_desc["StreamSpecification"].should.equal(
        {"StreamEnabled": True, "StreamViewType": "KEYS_ONLY"}
    )

    dynamodb_conn = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb_conn.Table("myTableName")
    table.name.should.equal("myTableName")

    table.put_item(
        Item={"Album": "myAlbum", "Artist": "myArtist", "Sales": 10, "NumberOfSongs": 5}
    )

    response = table.get_item(Key={"Album": "myAlbum", "Artist": "myArtist"})

    response["Item"]["Album"].should.equal("myAlbum")
    response["Item"]["Sales"].should.equal(Decimal("10"))
    response["Item"]["NumberOfSongs"].should.equal(Decimal("5"))
    response["Item"]["Album"].should.equal("myAlbum")


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
    log_group["logGroupName"].should.equal("some-log-group")


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
    policies.should.have.length_of(1)
    policies.should.be.containing_item_with_attributes(
        policyName="TestPolicyA", policyDocument=policy_document
    )

    cf_conn.update_stack(StackName="test_stack", TemplateBody=json.dumps(template2))
    policies = logs_conn.describe_resource_policies()["resourcePolicies"]
    policies.should.have.length_of(2)
    policies.should.be.containing_item_with_attributes(
        policyName="TestPolicyB", policyDocument=policy_document
    )
    policies.should.be.containing_item_with_attributes(
        policyName="TestPolicyC", policyDocument=policy_document
    )

    cf_conn.update_stack(StackName="test_stack", TemplateBody=json.dumps(template1))
    policies = logs_conn.describe_resource_policies()["resourcePolicies"]
    policies.should.have.length_of(1)
    policies.should.be.containing_item_with_attributes(
        policyName="TestPolicyA", policyDocument=policy_document
    )


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
    policies.should.have.length_of(1)

    cf_conn.delete_stack(StackName="test_stack")
    policies = logs_conn.describe_resource_policies()["resourcePolicies"]
    policies.should.have.length_of(0)


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
    rules["Rules"].should.have.length_of(1)
    rules["Rules"][0]["Name"].should.equal("quick-fox")
    rules["Rules"][0]["State"].should.equal("ENABLED")
    rules["Rules"][0]["ScheduleExpression"].should.equal("rate(5 minutes)")


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
    rules["Rules"].should.have.length_of(1)

    cf_conn.delete_stack(StackName="test_stack")

    rules = boto3.client("events", "us-west-2").list_rules()
    rules["Rules"].should.have.length_of(0)


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
    rules["Rules"][0]["Name"].should.contain("test_stack-Event-")


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

    rules["Rules"][0]["Name"].should.contain("test_stack-Event-")

    log_groups["logGroups"][0]["logGroupName"].should.equal(rules["Rules"][0]["Arn"])
    log_groups["logGroups"][0]["retentionInDays"].should.equal(3)


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
    rules["Rules"].should.have.length_of(1)
    rules["Rules"][0]["Name"].should.equal("Foo")
    rules["Rules"][0]["State"].should.equal("ENABLED")

    update_template = events_template.substitute(Name="Bar", State="DISABLED")
    cf_conn.update_stack(StackName="test_stack", TemplateBody=update_template)

    rules = boto3.client("events", "us-west-2").list_rules()

    rules["Rules"].should.have.length_of(1)
    rules["Rules"][0]["Name"].should.equal("Bar")
    rules["Rules"][0]["State"].should.equal("DISABLED")


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

    event_buses["EventBuses"].should.have.length_of(1)
    event_buses["EventBuses"][0]["Name"].should.equal("MyCustomEventBus")


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
    event_buses["EventBuses"].should.have.length_of(1)

    cf_conn.delete_stack(StackName="test_stack")

    event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="MyCustom"
    )
    event_buses["EventBuses"].should.have.length_of(0)


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
    original_event_buses["EventBuses"].should.have.length_of(1)

    original_eventbus = original_event_buses["EventBuses"][0]

    updated_template = eventbus_template.substitute(
        {"resource_name": "updated", "name": "AnotherEventBus"}
    )
    cf_conn.update_stack(StackName="test_stack", TemplateBody=updated_template)

    update_event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="AnotherEventBus"
    )
    update_event_buses["EventBuses"].should.have.length_of(1)
    update_event_buses["EventBuses"][0]["Arn"].shouldnt.equal(original_eventbus["Arn"])


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
    original_event_buses["EventBuses"].should.have.length_of(1)

    original_eventbus = original_event_buses["EventBuses"][0]

    updated_template = eventbus_template.substitute({"name": "NewEventBus"})
    cf_conn.update_stack(StackName="test_stack", TemplateBody=updated_template)

    update_event_buses = boto3.client("events", "us-west-2").list_event_buses(
        NamePrefix="NewEventBus"
    )
    update_event_buses["EventBuses"].should.have.length_of(1)
    update_event_buses["EventBuses"][0]["Name"].should.equal("NewEventBus")
    update_event_buses["EventBuses"][0]["Arn"].shouldnt.equal(original_eventbus["Arn"])


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

    output_arn["OutputValue"].should.equal(event_bus["Arn"])
    output_name["OutputValue"].should.equal(event_bus["Name"])


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
    outputs.should.have.length_of(1)
    outputs[0]["OutputKey"].should.equal("MyTableName")
    outputs[0]["OutputValue"].should.contain("foobar")
    # Assert the table is created
    ddb = boto3.client("dynamodb", "us-west-2")
    table_names = ddb.list_tables()["TableNames"]
    table_names.should.equal([outputs[0]["OutputValue"]])
