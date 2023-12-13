import json
from uuid import uuid4

import boto3

from moto import mock_autoscaling, mock_cloudformation, mock_ec2
from tests import EXAMPLE_AMI_ID, EXAMPLE_AMI_ID2


@mock_autoscaling
@mock_cloudformation
@mock_ec2
def test_asg_with_latest_launch_template_version():
    cf_client = boto3.client("cloudformation", region_name="us-west-1")
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    autoscaling_client = boto3.client("autoscaling", region_name="us-west-1")

    subnet1 = ec2.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc.id, AvailabilityZone="us-west-1a")

    subnet2 = ec2.create_subnet(CidrBlock="10.0.2.0/24", VpcId=vpc.id, AvailabilityZone="us-west-1b")

    autoscaling_group_name = str(uuid4())

    stack_name = str(uuid4())

    version_attribute = "LatestVersionNumber"

    template_json = json.dumps({
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "AWS CloudFormation Template to create an ASG group with LaunchTemplate",
        "Resources": {
            "LaunchTemplate": {
                "Type": "AWS::EC2::LaunchTemplate",
                "Properties": {
                    "LaunchTemplateName": "launch-template-test",
                    "LaunchTemplateData": {
                        "ImageId": EXAMPLE_AMI_ID,
                        "InstanceType": "t3.small",
                        "UserData": ""
                    }
                }
            },
            "AutoScalingGroup": {
                "Type": "AWS::AutoScaling::AutoScalingGroup",
                "Properties": {
                    "AutoScalingGroupName": autoscaling_group_name,
                    "VPCZoneIdentifier": [subnet1.id],
                    "LaunchTemplate": {
                        "LaunchTemplateId": {
                            "Ref": "LaunchTemplate"
                        },
                        "Version": {
                            "Fn::GetAtt": [
                                "LaunchTemplate",
                                version_attribute
                            ]
                        }
                    },
                    "MinSize": 1,
                    "MaxSize": 1
                }
            }
        }
    })

    cf_client.create_stack(
        StackName=stack_name,
        TemplateBody=template_json,
        Capabilities=["CAPABILITY_NAMED_IAM"],
        OnFailure="DELETE",
    )

    template_json = json.dumps({
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "AWS CloudFormation Template to create an ASG group with LaunchTemplate",
        "Resources": {
            "LaunchTemplate": {
                "Type": "AWS::EC2::LaunchTemplate",
                "Properties": {
                    "LaunchTemplateName": "launch-template-test",
                    "LaunchTemplateData": {
                        "ImageId": EXAMPLE_AMI_ID2,
                        "InstanceType": "t3.medium",
                        "UserData": ""
                    }
                }
            },
            "AutoScalingGroup": {
                "Type": "AWS::AutoScaling::AutoScalingGroup",
                "Properties": {
                    "AutoScalingGroupName": autoscaling_group_name,
                    "VPCZoneIdentifier": [subnet2.id],
                    "LaunchTemplate": {
                        "LaunchTemplateId": {
                            "Ref": "LaunchTemplate"
                        },
                        "Version": {
                            "Fn::GetAtt": [
                                "LaunchTemplate",
                                version_attribute
                            ]
                        }
                    },
                    "MinSize": 1,
                    "MaxSize": 2
                }
            }
        }
    })

    cf_client.update_stack(
        StackName=stack_name,
        TemplateBody=template_json,
        Capabilities=["CAPABILITY_NAMED_IAM"],
    )

    autoscaling_group = autoscaling_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[
            autoscaling_group_name,
        ]
    )["AutoScalingGroups"][0]

    assert autoscaling_group["LaunchTemplate"]["LaunchTemplateName"] == "launch-template-test"
    assert autoscaling_group["LaunchTemplate"]["Version"] == "2"


@mock_autoscaling
@mock_cloudformation
@mock_ec2
def test_asg_with_default_launch_template_version():
    cf_client = boto3.client("cloudformation", region_name="us-west-1")
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    autoscaling_client = boto3.client("autoscaling", region_name="us-west-1")

    subnet1 = ec2.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc.id, AvailabilityZone="us-west-1a")

    subnet2 = ec2.create_subnet(CidrBlock="10.0.2.0/24", VpcId=vpc.id, AvailabilityZone="us-west-1b")

    autoscaling_group_name = str(uuid4())

    stack_name = str(uuid4())

    version_attribute = "DefaultVersionNumber"

    template_json = json.dumps({
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "AWS CloudFormation Template to create an ASG group with LaunchTemplate",
        "Resources": {
            "LaunchTemplate": {
                "Type": "AWS::EC2::LaunchTemplate",
                "Properties": {
                    "LaunchTemplateName": "launch-template-test",
                    "LaunchTemplateData": {
                        "ImageId": EXAMPLE_AMI_ID,
                        "InstanceType": "t3.small",
                        "UserData": ""
                    }
                }
            },
            "AutoScalingGroup": {
                "Type": "AWS::AutoScaling::AutoScalingGroup",
                "Properties": {
                    "AutoScalingGroupName": autoscaling_group_name,
                    "VPCZoneIdentifier": [subnet1.id],
                    "LaunchTemplate": {
                        "LaunchTemplateId": {
                            "Ref": "LaunchTemplate"
                        },
                        "Version": {
                            "Fn::GetAtt": [
                                "LaunchTemplate",
                                version_attribute
                            ]
                        }
                    },
                    "MinSize": 1,
                    "MaxSize": 1
                }
            }
        }
    })

    cf_client.create_stack(
        StackName=stack_name,
        TemplateBody=template_json,
        Capabilities=["CAPABILITY_NAMED_IAM"],
        OnFailure="DELETE",
    )

    template_json = json.dumps({
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "AWS CloudFormation Template to create an ASG group with LaunchTemplate",
        "Resources": {
            "LaunchTemplate": {
                "Type": "AWS::EC2::LaunchTemplate",
                "Properties": {
                    "LaunchTemplateName": "launch-template-test",
                    "LaunchTemplateData": {
                        "ImageId": EXAMPLE_AMI_ID2,
                        "InstanceType": "t3.medium",
                        "UserData": ""
                    }
                }
            },
            "AutoScalingGroup": {
                "Type": "AWS::AutoScaling::AutoScalingGroup",
                "Properties": {
                    "AutoScalingGroupName": autoscaling_group_name,
                    "VPCZoneIdentifier": [subnet2.id],
                    "LaunchTemplate": {
                        "LaunchTemplateId": {
                            "Ref": "LaunchTemplate"
                        },
                        "Version": {
                            "Fn::GetAtt": [
                                "LaunchTemplate",
                                version_attribute
                            ]
                        }
                    },
                    "MinSize": 1,
                    "MaxSize": 2
                }
            }
        }
    })

    cf_client.update_stack(
        StackName=stack_name,
        TemplateBody=template_json,
        Capabilities=["CAPABILITY_NAMED_IAM"],
    )

    autoscaling_group = autoscaling_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[
            autoscaling_group_name,
        ]
    )["AutoScalingGroups"][0]

    assert autoscaling_group["LaunchTemplate"]["LaunchTemplateName"] == "launch-template-test"
    assert autoscaling_group["LaunchTemplate"]["Version"] == "1"
