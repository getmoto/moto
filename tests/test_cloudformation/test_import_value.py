from __future__ import absolute_import, division, print_function

# Standard library modules
import unittest

# Third-party modules
import boto3
from botocore.exceptions import ClientError

# Package modules
from moto import mock_cloudformation

AWS_REGION = "us-west-1"

SG_STACK_NAME = "simple-sg-stack"
SG_TEMPLATE = """
AWSTemplateFormatVersion: 2010-09-09
Description: Simple test CF template for moto_cloudformation


Resources:
  SimpleSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Description: "A simple security group"
    Properties:
      GroupName: simple-security-group
      GroupDescription: "A simple security group"
      SecurityGroupEgress:
        -
          Description: "Egress to remote HTTPS servers"
          CidrIp: 0.0.0.0/0
          IpProtocol: tcp
          FromPort: 443
          ToPort: 443

Outputs:
    SimpleSecurityGroupName:
        Value: !GetAtt SimpleSecurityGroup.GroupId
        Export:
            Name: "SimpleSecurityGroup"

"""

EC2_STACK_NAME = "simple-ec2-stack"
EC2_TEMPLATE = """
---
# The latest template format version is "2010-09-09" and as of 2018-04-09
# is currently the only valid value.
AWSTemplateFormatVersion: 2010-09-09
Description: Simple test CF template for moto_cloudformation


Resources:
  SimpleInstance:
    Type: AWS::EC2::Instance
    Properties:
        ImageId: ami-03cf127a
        InstanceType: t2.micro
        SecurityGroups: !Split [',', !ImportValue SimpleSecurityGroup]
"""


class TestSimpleInstance(unittest.TestCase):
    def test_simple_instance(self):
        """Test that we can create a simple CloudFormation stack that imports values from an existing CloudFormation stack"""
        with mock_cloudformation():
            client = boto3.client("cloudformation", region_name=AWS_REGION)
            client.create_stack(StackName=SG_STACK_NAME, TemplateBody=SG_TEMPLATE)
            response = client.create_stack(
                StackName=EC2_STACK_NAME, TemplateBody=EC2_TEMPLATE
            )
            self.assertIn("StackId", response)
            response = client.describe_stacks(StackName=response["StackId"])
            self.assertIn("Stacks", response)
            stack_info = response["Stacks"]
            self.assertEqual(1, len(stack_info))
            self.assertIn("StackName", stack_info[0])
            self.assertEqual(EC2_STACK_NAME, stack_info[0]["StackName"])

    def test_simple_instance_missing_export(self):
        """Test that we get an exception if a CloudFormation stack tries to imports a non-existent export value"""
        with mock_cloudformation():
            client = boto3.client("cloudformation", region_name=AWS_REGION)
            with self.assertRaises(ClientError) as e:
                client.create_stack(StackName=EC2_STACK_NAME, TemplateBody=EC2_TEMPLATE)
            self.assertIn("Error", e.exception.response)
            self.assertIn("Code", e.exception.response["Error"])
            self.assertEqual("ExportNotFound", e.exception.response["Error"]["Code"])
