import json

import boto3

from moto import mock_aws

template_fs_simple = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "FileSystemResource": {"Type": "AWS::EFS::FileSystem", "Properties": {}},
    },
}


template_complete = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "MountTargetVPC": {
            "Type": "AWS::EC2::VPC",
            "Properties": {"CidrBlock": "172.31.0.0/16"},
        },
        "MountTargetSubnetOne": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "CidrBlock": "172.31.1.0/24",
                "VpcId": {"Ref": "MountTargetVPC"},
                "AvailabilityZone": "us-east-1a",
            },
        },
        "MountTargetSubnetTwo": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "CidrBlock": "172.31.2.0/24",
                "VpcId": {"Ref": "MountTargetVPC"},
                "AvailabilityZone": "us-east-1b",
            },
        },
        "MountTargetSubnetThree": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "CidrBlock": "172.31.3.0/24",
                "VpcId": {"Ref": "MountTargetVPC"},
                "AvailabilityZone": "us-east-1c",
            },
        },
        "FileSystemResource": {
            "Type": "AWS::EFS::FileSystem",
            "Properties": {
                "PerformanceMode": "maxIO",
                "LifecyclePolicies": [
                    {"TransitionToIA": "AFTER_30_DAYS"},
                    {"TransitionToPrimaryStorageClass": "AFTER_1_ACCESS"},
                ],
                "Encrypted": True,
                "FileSystemTags": [{"Key": "Name", "Value": "TestFileSystem"}],
                "FileSystemPolicy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": ["elasticfilesystem:ClientMount"],
                            "Principal": {
                                "AWS": "arn:aws:iam::111122223333:role/EfsReadOnly"
                            },
                        }
                    ],
                },
                "BackupPolicy": {"Status": "ENABLED"},
                "KmsKeyId": {"Fn::GetAtt": ["key", "Arn"]},
            },
        },
        "key": {
            "Type": "AWS::KMS::Key",
            "Properties": {
                "KeyPolicy": {
                    "Version": "2012-10-17",
                    "Id": "key-default-1",
                    "Statement": [
                        {
                            "Sid": "Allow administration of the key",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:aws:iam::",
                                            {"Ref": "AWS::AccountId"},
                                            ":root",
                                        ],
                                    ]
                                }
                            },
                            "Action": ["kms:*"],
                            "Resource": "*",
                        }
                    ],
                }
            },
        },
        "MountTargetResource1": {
            "Type": "AWS::EFS::MountTarget",
            "Properties": {
                "FileSystemId": {"Ref": "FileSystemResource"},
                "SubnetId": {"Ref": "MountTargetSubnetOne"},
                "SecurityGroups": [
                    {"Fn::GetAtt": ["MountTargetVPC", "DefaultSecurityGroup"]}
                ],
            },
        },
        "MountTargetResource2": {
            "Type": "AWS::EFS::MountTarget",
            "Properties": {
                "FileSystemId": {"Ref": "FileSystemResource"},
                "SubnetId": {"Ref": "MountTargetSubnetTwo"},
                "SecurityGroups": [
                    {"Fn::GetAtt": ["MountTargetVPC", "DefaultSecurityGroup"]}
                ],
            },
        },
        "MountTargetResource3": {
            "Type": "AWS::EFS::MountTarget",
            "Properties": {
                "FileSystemId": {"Ref": "FileSystemResource"},
                "SubnetId": {"Ref": "MountTargetSubnetThree"},
                "SecurityGroups": [
                    {"Fn::GetAtt": ["MountTargetVPC", "DefaultSecurityGroup"]}
                ],
            },
        },
        "AccessPointResource": {
            "Type": "AWS::EFS::AccessPoint",
            "Properties": {
                "FileSystemId": {"Ref": "FileSystemResource"},
                "PosixUser": {
                    "Uid": "13234",
                    "Gid": "1322",
                    "SecondaryGids": ["1344", "1452"],
                },
                "RootDirectory": {
                    "CreationInfo": {
                        "OwnerGid": "708798",
                        "OwnerUid": "7987987",
                        "Permissions": "0755",
                    },
                    "Path": "/testcfn/abc",
                },
            },
        },
    },
}


@mock_aws
def test_simple_template():
    region = "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)
    cf.create_stack(StackName="teststack", TemplateBody=json.dumps(template_fs_simple))

    efs = boto3.client("efs", region)
    fs = efs.describe_file_systems()["FileSystems"][0]
    assert fs["PerformanceMode"] == "generalPurpose"
    assert fs["Encrypted"] is False
    assert fs["ThroughputMode"] == "bursting"


@mock_aws
def test_full_template():
    region = "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)
    cf.create_stack(StackName="teststack", TemplateBody=json.dumps(template_complete))

    efs = boto3.client("efs", region)
    fs = efs.describe_file_systems()["FileSystems"][0]
    fs_id = fs["FileSystemId"]
    assert fs["Name"] == "TestFileSystem"
    assert fs["KmsKeyId"]

    lc = efs.describe_lifecycle_configuration(FileSystemId=fs_id)["LifecyclePolicies"]
    assert {"TransitionToIA": "AFTER_30_DAYS"} in lc
    assert {"TransitionToPrimaryStorageClass": "AFTER_1_ACCESS"} in lc

    aps = efs.describe_access_points()["AccessPoints"][0]
    assert aps["FileSystemId"] == fs_id

    cf.delete_stack(StackName="teststack")

    assert efs.describe_file_systems()["FileSystems"] == []
    assert efs.describe_access_points()["AccessPoints"] == []
