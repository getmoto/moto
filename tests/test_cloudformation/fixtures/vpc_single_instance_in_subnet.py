from __future__ import unicode_literals

from tests import EXAMPLE_AMI_ID

template = {
    "Description": "AWS CloudFormation Sample Template vpc_single_instance_in_subnet.template: Sample template showing how to create a VPC and add an EC2 instance with an Elastic IP address and a security group. **WARNING** This template creates an Amazon EC2 instance. You will be billed for the AWS resources used if you create a stack from this template.",
    "Parameters": {
        "SSHLocation": {
            "ConstraintDescription": "must be a valid IP CIDR range of the form x.x.x.x/x.",
            "Description": " The IP address range that can be used to SSH to the EC2 instances",
            "Default": "0.0.0.0/0",
            "MinLength": "9",
            "AllowedPattern": "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
            "MaxLength": "18",
            "Type": "String",
        },
        "KeyName": {
            "Type": "String",
            "Description": "Name of an existing EC2 KeyPair to enable SSH access to the instance",
            "MinLength": "1",
            "AllowedPattern": "[\\x20-\\x7E]*",
            "MaxLength": "255",
            "ConstraintDescription": "can contain only ASCII characters.",
        },
        "InstanceType": {
            "Default": "m1.small",
            "ConstraintDescription": "must be a valid EC2 instance type.",
            "Type": "String",
            "Description": "WebServer EC2 instance type",
            "AllowedValues": [
                "t1.micro",
                "m1.small",
                "m1.medium",
                "m1.large",
                "m1.xlarge",
                "m2.xlarge",
                "m2.2xlarge",
                "m2.4xlarge",
                "m3.xlarge",
                "m3.2xlarge",
                "c1.medium",
                "c1.xlarge",
                "cc1.4xlarge",
                "cc2.8xlarge",
                "cg1.4xlarge",
            ],
        },
    },
    "AWSTemplateFormatVersion": "2010-09-09",
    "Outputs": {
        "URL": {
            "Description": "Newly created application URL",
            "Value": {
                "Fn::Join": [
                    "",
                    ["http://", {"Fn::GetAtt": ["WebServerInstance", "PublicIp"]}],
                ]
            },
        }
    },
    "Resources": {
        "Subnet": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "CidrBlock": "10.0.0.0/24",
                "Tags": [{"Value": {"Ref": "AWS::StackId"}, "Key": "Application"}],
            },
        },
        "WebServerWaitHandle": {"Type": "AWS::CloudFormation::WaitConditionHandle"},
        "Route": {
            "Type": "AWS::EC2::Route",
            "Properties": {
                "GatewayId": {"Ref": "InternetGateway"},
                "DestinationCidrBlock": "0.0.0.0/0",
                "RouteTableId": {"Ref": "RouteTable"},
            },
            "DependsOn": "AttachGateway",
        },
        "SubnetRouteTableAssociation": {
            "Type": "AWS::EC2::SubnetRouteTableAssociation",
            "Properties": {
                "SubnetId": {"Ref": "Subnet"},
                "RouteTableId": {"Ref": "RouteTable"},
            },
        },
        "InternetGateway": {
            "Type": "AWS::EC2::InternetGateway",
            "Properties": {
                "Tags": [{"Value": {"Ref": "AWS::StackId"}, "Key": "Application"}]
            },
        },
        "RouteTable": {
            "Type": "AWS::EC2::RouteTable",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "Tags": [{"Value": {"Ref": "AWS::StackId"}, "Key": "Application"}],
            },
        },
        "WebServerWaitCondition": {
            "Type": "AWS::CloudFormation::WaitCondition",
            "Properties": {"Handle": {"Ref": "WebServerWaitHandle"}, "Timeout": "300"},
            "DependsOn": "WebServerInstance",
        },
        "VPC": {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": "10.0.0.0/16",
                "Tags": [{"Value": {"Ref": "AWS::StackId"}, "Key": "Application"}],
            },
        },
        "InstanceSecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "SecurityGroupIngress": [
                    {
                        "ToPort": "22",
                        "IpProtocol": "tcp",
                        "CidrIp": {"Ref": "SSHLocation"},
                        "FromPort": "22",
                    },
                    {
                        "ToPort": "80",
                        "IpProtocol": "tcp",
                        "CidrIp": "0.0.0.0/0",
                        "FromPort": "80",
                    },
                ],
                "VpcId": {"Ref": "VPC"},
                "GroupDescription": "Enable SSH access via port 22",
            },
        },
        "WebServerInstance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "UserData": {
                    "Fn::Base64": {
                        "Fn::Join": [
                            "",
                            [
                                "#!/bin/bash\n",
                                "yum update -y aws-cfn-bootstrap\n",
                                "# Helper function\n",
                                "function error_exit\n",
                                "{\n",
                                '  /opt/aws/bin/cfn-signal -e 1 -r "$1" \'',
                                {"Ref": "WebServerWaitHandle"},
                                "'\n",
                                "  exit 1\n",
                                "}\n",
                                "# Install the simple web page\n",
                                "/opt/aws/bin/cfn-init -s ",
                                {"Ref": "AWS::StackId"},
                                " -r WebServerInstance ",
                                "         --region ",
                                {"Ref": "AWS::Region"},
                                " || error_exit 'Failed to run cfn-init'\n",
                                "# Start up the cfn-hup daemon to listen for changes to the Web Server metadata\n",
                                "/opt/aws/bin/cfn-hup || error_exit 'Failed to start cfn-hup'\n",
                                "# All done so signal success\n",
                                '/opt/aws/bin/cfn-signal -e 0 -r "WebServer setup complete" \'',
                                {"Ref": "WebServerWaitHandle"},
                                "'\n",
                            ],
                        ]
                    }
                },
                "Tags": [
                    {"Value": {"Ref": "AWS::StackId"}, "Key": "Application"},
                    {"Value": "Bar", "Key": "Foo"},
                ],
                "SecurityGroupIds": [{"Ref": "InstanceSecurityGroup"}],
                "KeyName": {"Ref": "KeyName"},
                "SubnetId": {"Ref": "Subnet"},
                "ImageId": {
                    "Fn::FindInMap": ["RegionMap", {"Ref": "AWS::Region"}, "AMI"]
                },
                "InstanceType": {"Ref": "InstanceType"},
            },
            "Metadata": {
                "Comment": "Install a simple PHP application",
                "AWS::CloudFormation::Init": {
                    "config": {
                        "files": {
                            "/etc/cfn/cfn-hup.conf": {
                                "content": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "[main]\n",
                                            "stack=",
                                            {"Ref": "AWS::StackId"},
                                            "\n",
                                            "region=",
                                            {"Ref": "AWS::Region"},
                                            "\n",
                                        ],
                                    ]
                                },
                                "owner": "root",
                                "group": "root",
                                "mode": "000400",
                            },
                            "/etc/cfn/hooks.d/cfn-auto-reloader.conf": {
                                "content": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "[cfn-auto-reloader-hook]\n",
                                            "triggers=post.update\n",
                                            "path=Resources.WebServerInstance.Metadata.AWS::CloudFormation::Init\n",
                                            "action=/opt/aws/bin/cfn-init -s ",
                                            {"Ref": "AWS::StackId"},
                                            " -r WebServerInstance ",
                                            " --region     ",
                                            {"Ref": "AWS::Region"},
                                            "\n",
                                            "runas=root\n",
                                        ],
                                    ]
                                }
                            },
                            "/var/www/html/index.php": {
                                "content": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "<?php\n",
                                            "echo '<h1>AWS CloudFormation sample PHP application</h1>';\n",
                                            "?>\n",
                                        ],
                                    ]
                                },
                                "owner": "apache",
                                "group": "apache",
                                "mode": "000644",
                            },
                        },
                        "services": {
                            "sysvinit": {
                                "httpd": {"ensureRunning": "true", "enabled": "true"},
                                "sendmail": {
                                    "ensureRunning": "false",
                                    "enabled": "false",
                                },
                            }
                        },
                        "packages": {"yum": {"httpd": [], "php": []}},
                    }
                },
            },
        },
        "IPAddress": {
            "Type": "AWS::EC2::EIP",
            "Properties": {"InstanceId": {"Ref": "WebServerInstance"}, "Domain": "vpc"},
            "DependsOn": "AttachGateway",
        },
        "AttachGateway": {
            "Type": "AWS::EC2::VPCGatewayAttachment",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "InternetGatewayId": {"Ref": "InternetGateway"},
            },
        },
    },
    "Mappings": {
        "RegionMap": {
            "ap-southeast-1": {"AMI": EXAMPLE_AMI_ID},
            "ap-southeast-2": {"AMI": EXAMPLE_AMI_ID},
            "us-west-2": {"AMI": EXAMPLE_AMI_ID},
            "us-east-1": {"AMI": EXAMPLE_AMI_ID},
            "ap-northeast-1": {"AMI": EXAMPLE_AMI_ID},
            "us-west-1": {"AMI": EXAMPLE_AMI_ID},
            "eu-west-1": {"AMI": EXAMPLE_AMI_ID},
            "sa-east-1": {"AMI": EXAMPLE_AMI_ID},
        }
    },
}
