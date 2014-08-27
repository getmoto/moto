from __future__ import unicode_literals

template = {
    "Description": "AWS CloudFormation Sample Template Gollum_Single_Instance_With_EBS_Volume: Gollum is a simple wiki system built on top of Git that powers GitHub Wikis. This template installs a Gollum Wiki stack on a single EC2 instance with an EBS volume for storage and demonstrates using the AWS CloudFormation bootstrap scripts to install the packages and files necessary at instance launch time. **WARNING** This template creates an Amazon EC2 instance and an EBS volume. You will be billed for the AWS resources used if you create a stack from this template.",
    "Parameters": {
        "SSHLocation": {
            "ConstraintDescription": "must be a valid IP CIDR range of the form x.x.x.x/x.",
            "Description": "The IP address range that can be used to SSH to the EC2 instances",
            "Default": "0.0.0.0/0",
            "MinLength": "9",
            "AllowedPattern": "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
            "MaxLength": "18",
            "Type": "String"
        },
        "KeyName": {
            "Type": "String",
            "Description": "Name of an existing EC2 KeyPair to enable SSH access to the instances",
            "MinLength": "1",
            "AllowedPattern": "[\\x20-\\x7E]*",
            "MaxLength": "255",
            "ConstraintDescription": "can contain only ASCII characters."
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
                "cg1.4xlarge"
            ]
        },
        "VolumeSize": {
            "Description": "WebServer EC2 instance type",
            "Default": "5",
            "Type": "Number",
            "MaxValue": "1024",
            "MinValue": "5",
            "ConstraintDescription": "must be between 5 and 1024 Gb."
        }
    },
    "AWSTemplateFormatVersion": "2010-09-09",
    "Outputs": {
        "WebsiteURL": {
            "Description": "URL for Gollum wiki",
            "Value": {
                "Fn::Join": [
                    "",
                    [
                        "http://",
                        {
                            "Fn::GetAtt": [
                                "WebServer",
                                "PublicDnsName"
                            ]
                        }
                    ]
                ]
            }
        }
    },
    "Resources": {
        "WebServerSecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "SecurityGroupIngress": [
                    {
                        "ToPort": "80",
                        "IpProtocol": "tcp",
                        "CidrIp": "0.0.0.0/0",
                        "FromPort": "80"
                    },
                    {
                        "ToPort": "22",
                        "IpProtocol": "tcp",
                        "CidrIp": {
                            "Ref": "SSHLocation"
                        },
                        "FromPort": "22"
                    }
                ],
                "GroupDescription": "Enable SSH access and HTTP access on the inbound port"
            }
        },
        "WebServer": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "UserData": {
                    "Fn::Base64": {
                        "Fn::Join": [
                            "",
                            [
                                "#!/bin/bash -v\n",
                                "yum update -y aws-cfn-bootstrap\n",
                                "# Helper function\n",
                                "function error_exit\n",
                                "{\n",
                                "  /opt/aws/bin/cfn-signal -e 1 -r \"$1\" '",
                                {
                                    "Ref": "WaitHandle"
                                },
                                "'\n",
                                "  exit 1\n",
                                "}\n",
                                "# Install Rails packages\n",
                                "/opt/aws/bin/cfn-init -s ",
                                {
                                    "Ref": "AWS::StackId"
                                },
                                " -r WebServer ",
                                "    --region ",
                                {
                                    "Ref": "AWS::Region"
                                },
                                " || error_exit 'Failed to run cfn-init'\n",
                                "# Wait for the EBS volume to show up\n",
                                "while [ ! -e /dev/sdh ]; do echo Waiting for EBS volume to attach; sleep 5; done\n",
                                "# Format the EBS volume and mount it\n",
                                "mkdir /var/wikidata\n",
                                "/sbin/mkfs -t ext3 /dev/sdh1\n",
                                "mount /dev/sdh1 /var/wikidata\n",
                                "# Initialize the wiki and fire up the server\n",
                                "cd /var/wikidata\n",
                                "git init\n",
                                "gollum --port 80 --host 0.0.0.0 &\n",
                                "# If all is well so signal success\n",
                                "/opt/aws/bin/cfn-signal -e $? -r \"Rails application setup complete\" '",
                                {
                                    "Ref": "WaitHandle"
                                },
                                "'\n"
                            ]
                        ]
                    }
                },
                "KeyName": {
                    "Ref": "KeyName"
                },
                "SecurityGroups": [
                    {
                        "Ref": "WebServerSecurityGroup"
                    }
                ],
                "InstanceType": {
                    "Ref": "InstanceType"
                },
                "ImageId": {
                    "Fn::FindInMap": [
                        "AWSRegionArch2AMI",
                        {
                            "Ref": "AWS::Region"
                        },
                        {
                            "Fn::FindInMap": [
                                "AWSInstanceType2Arch",
                                {
                                    "Ref": "InstanceType"
                                },
                                "Arch"
                            ]
                        }
                    ]
                }
            },
            "Metadata": {
                "AWS::CloudFormation::Init": {
                    "config": {
                        "packages": {
                            "rubygems": {
                                "nokogiri": [
                                    "1.5.10"
                                ],
                                "rdiscount": [],
                                "gollum": [
                                    "1.1.1"
                                ]
                            },
                            "yum": {
                                "libxslt-devel": [],
                                "gcc": [],
                                "git": [],
                                "rubygems": [],
                                "ruby-devel": [],
                                "ruby-rdoc": [],
                                "make": [],
                                "libxml2-devel": []
                            }
                        }
                    }
                }
            }
        },
        "DataVolume": {
            "Type": "AWS::EC2::Volume",
            "Properties": {
                "Tags": [
                    {
                        "Value": "Gollum Data Volume",
                        "Key": "Usage"
                    }
                ],
                "AvailabilityZone": {
                    "Fn::GetAtt": [
                        "WebServer",
                        "AvailabilityZone"
                    ]
                },
                "Size": "100",
            }
        },
        "MountPoint": {
            "Type": "AWS::EC2::VolumeAttachment",
            "Properties": {
                "InstanceId": {
                    "Ref": "WebServer"
                },
                "Device": "/dev/sdh",
                "VolumeId": {
                    "Ref": "DataVolume"
                }
            }
        },
        "WaitCondition": {
            "DependsOn": "MountPoint",
            "Type": "AWS::CloudFormation::WaitCondition",
            "Properties": {
                "Handle": {
                    "Ref": "WaitHandle"
                },
                "Timeout": "300"
            },
            "Metadata": {
                "Comment1": "Note that the WaitCondition is dependent on the volume mount point allowing the volume to be created and attached to the EC2 instance",
                "Comment2": "The instance bootstrap script waits for the volume to be attached to the instance prior to installing Gollum and signalling completion"
            }
        },
        "WaitHandle": {
            "Type": "AWS::CloudFormation::WaitConditionHandle"
        }
    },
    "Mappings": {
        "AWSInstanceType2Arch": {
            "m3.2xlarge": {
                "Arch": "64"
            },
            "m2.2xlarge": {
                "Arch": "64"
            },
            "m1.small": {
                "Arch": "64"
            },
            "c1.medium": {
                "Arch": "64"
            },
            "cg1.4xlarge": {
                "Arch": "64HVM"
            },
            "m2.xlarge": {
                "Arch": "64"
            },
            "t1.micro": {
                "Arch": "64"
            },
            "cc1.4xlarge": {
                "Arch": "64HVM"
            },
            "m1.medium": {
                "Arch": "64"
            },
            "cc2.8xlarge": {
                "Arch": "64HVM"
            },
            "m1.large": {
                "Arch": "64"
            },
            "m1.xlarge": {
                "Arch": "64"
            },
            "m2.4xlarge": {
                "Arch": "64"
            },
            "c1.xlarge": {
                "Arch": "64"
            },
            "m3.xlarge": {
                "Arch": "64"
            }
        },
        "AWSRegionArch2AMI": {
            "ap-southeast-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-b4b0cae6",
                "64": "ami-beb0caec"
            },
            "ap-southeast-2": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-b3990e89",
                "64": "ami-bd990e87"
            },
            "us-west-2": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-38fe7308",
                "64": "ami-30fe7300"
            },
            "us-east-1": {
                "64HVM": "ami-0da96764",
                "32": "ami-31814f58",
                "64": "ami-1b814f72"
            },
            "ap-northeast-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-0644f007",
                "64": "ami-0a44f00b"
            },
            "us-west-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-11d68a54",
                "64": "ami-1bd68a5e"
            },
            "eu-west-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-973b06e3",
                "64": "ami-953b06e1"
            },
            "sa-east-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-3e3be423",
                "64": "ami-3c3be421"
            }
        }
    }
}
