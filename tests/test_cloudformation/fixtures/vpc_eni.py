from __future__ import unicode_literals

template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "VPC ENI Test CloudFormation",
    "Resources": {
        "ENI": {
            "Type": "AWS::EC2::NetworkInterface",
            "Properties": {
                "SubnetId": {"Ref": "Subnet"}
            }
        },
        "Subnet": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "AvailabilityZone": "us-east-1a",
                "VpcId": {"Ref": "VPC"},
                "CidrBlock": "10.0.0.0/24"
            }
        },
        "VPC": {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": "10.0.0.0/16"
            }
        }
    },
    "Outputs": {
        "NinjaENI": {
            "Description": "Elastic IP mapping to Auto-Scaling Group",
            "Value": {"Ref": "ENI"}
        }
    }
}
