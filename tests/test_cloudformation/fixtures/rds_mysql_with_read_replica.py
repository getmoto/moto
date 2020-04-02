from __future__ import unicode_literals

template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "AWS CloudFormation Sample Template RDS_MySQL_With_Read_Replica: Sample template showing how to create a highly-available, RDS DBInstance with a read replica. **WARNING** This template creates an Amazon Relational Database Service database instance and Amazon CloudWatch alarms. You will be billed for the AWS resources used if you create a stack from this template.",
    "Parameters": {
        "DBName": {
            "Default": "MyDatabase",
            "Description": "The database name",
            "Type": "String",
            "MinLength": "1",
            "MaxLength": "64",
            "AllowedPattern": "[a-zA-Z][a-zA-Z0-9]*",
            "ConstraintDescription": "must begin with a letter and contain only alphanumeric characters.",
        },
        "DBInstanceIdentifier": {"Type": "String"},
        "DBUser": {
            "NoEcho": "true",
            "Description": "The database admin account username",
            "Type": "String",
            "MinLength": "1",
            "MaxLength": "16",
            "AllowedPattern": "[a-zA-Z][a-zA-Z0-9]*",
            "ConstraintDescription": "must begin with a letter and contain only alphanumeric characters.",
        },
        "DBPassword": {
            "NoEcho": "true",
            "Description": "The database admin account password",
            "Type": "String",
            "MinLength": "1",
            "MaxLength": "41",
            "AllowedPattern": "[a-zA-Z0-9]+",
            "ConstraintDescription": "must contain only alphanumeric characters.",
        },
        "DBAllocatedStorage": {
            "Default": "5",
            "Description": "The size of the database (Gb)",
            "Type": "Number",
            "MinValue": "5",
            "MaxValue": "1024",
            "ConstraintDescription": "must be between 5 and 1024Gb.",
        },
        "DBInstanceClass": {
            "Description": "The database instance type",
            "Type": "String",
            "Default": "db.m1.small",
            "AllowedValues": [
                "db.t1.micro",
                "db.m1.small",
                "db.m1.medium",
                "db.m1.large",
                "db.m1.xlarge",
                "db.m2.xlarge",
                "db.m2.2xlarge",
                "db.m2.4xlarge",
                "db.m3.medium",
                "db.m3.large",
                "db.m3.xlarge",
                "db.m3.2xlarge",
                "db.r3.large",
                "db.r3.xlarge",
                "db.r3.2xlarge",
                "db.r3.4xlarge",
                "db.r3.8xlarge",
                "db.m2.xlarge",
                "db.m2.2xlarge",
                "db.m2.4xlarge",
                "db.cr1.8xlarge",
            ],
            "ConstraintDescription": "must select a valid database instance type.",
        },
        "EC2SecurityGroup": {
            "Description": "The EC2 security group that contains instances that need access to the database",
            "Default": "default",
            "Type": "String",
            "AllowedPattern": "[a-zA-Z0-9\\-]+",
            "ConstraintDescription": "must be a valid security group name.",
        },
        "MultiAZ": {
            "Description": "Multi-AZ master database",
            "Type": "String",
            "Default": "false",
            "AllowedValues": ["true", "false"],
            "ConstraintDescription": "must be true or false.",
        },
    },
    "Conditions": {
        "Is-EC2-VPC": {
            "Fn::Or": [
                {"Fn::Equals": [{"Ref": "AWS::Region"}, "eu-central-1"]},
                {"Fn::Equals": [{"Ref": "AWS::Region"}, "cn-north-1"]},
            ]
        },
        "Is-EC2-Classic": {"Fn::Not": [{"Condition": "Is-EC2-VPC"}]},
    },
    "Resources": {
        "DBEC2SecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Condition": "Is-EC2-VPC",
            "Properties": {
                "GroupDescription": "Open database for access",
                "SecurityGroupIngress": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": "3306",
                        "ToPort": "3306",
                        "SourceSecurityGroupName": {"Ref": "EC2SecurityGroup"},
                    }
                ],
            },
        },
        "DBSecurityGroup": {
            "Type": "AWS::RDS::DBSecurityGroup",
            "Condition": "Is-EC2-Classic",
            "Properties": {
                "DBSecurityGroupIngress": [
                    {"EC2SecurityGroupName": {"Ref": "EC2SecurityGroup"}}
                ],
                "GroupDescription": "database access",
            },
        },
        "my_vpc": {"Type": "AWS::EC2::VPC", "Properties": {"CidrBlock": "10.0.0.0/16"}},
        "EC2Subnet": {
            "Type": "AWS::EC2::Subnet",
            "Condition": "Is-EC2-VPC",
            "Properties": {
                "AvailabilityZone": "eu-central-1a",
                "CidrBlock": "10.0.1.0/24",
                "VpcId": {"Ref": "my_vpc"},
            },
        },
        "DBSubnet": {
            "Type": "AWS::RDS::DBSubnetGroup",
            "Condition": "Is-EC2-VPC",
            "Properties": {
                "DBSubnetGroupDescription": "my db subnet group",
                "SubnetIds": [{"Ref": "EC2Subnet"}],
            },
        },
        "MasterDB": {
            "Type": "AWS::RDS::DBInstance",
            "Properties": {
                "DBInstanceIdentifier": {"Ref": "DBInstanceIdentifier"},
                "DBName": {"Ref": "DBName"},
                "AllocatedStorage": {"Ref": "DBAllocatedStorage"},
                "DBInstanceClass": {"Ref": "DBInstanceClass"},
                "Engine": "MySQL",
                "DBSubnetGroupName": {
                    "Fn::If": [
                        "Is-EC2-VPC",
                        {"Ref": "DBSubnet"},
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "MasterUsername": {"Ref": "DBUser"},
                "MasterUserPassword": {"Ref": "DBPassword"},
                "MultiAZ": {"Ref": "MultiAZ"},
                "Tags": [{"Key": "Name", "Value": "Master Database"}],
                "VPCSecurityGroups": {
                    "Fn::If": [
                        "Is-EC2-VPC",
                        [{"Fn::GetAtt": ["DBEC2SecurityGroup", "GroupId"]}],
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "DBSecurityGroups": {
                    "Fn::If": [
                        "Is-EC2-Classic",
                        [{"Ref": "DBSecurityGroup"}],
                        {"Ref": "AWS::NoValue"},
                    ]
                },
            },
            "DeletionPolicy": "Snapshot",
        },
        "ReplicaDB": {
            "Type": "AWS::RDS::DBInstance",
            "Properties": {
                "SourceDBInstanceIdentifier": {"Ref": "MasterDB"},
                "DBInstanceClass": {"Ref": "DBInstanceClass"},
                "Tags": [{"Key": "Name", "Value": "Read Replica Database"}],
            },
        },
    },
    "Outputs": {
        "EC2Platform": {
            "Description": "Platform in which this stack is deployed",
            "Value": {"Fn::If": ["Is-EC2-VPC", "EC2-VPC", "EC2-Classic"]},
        },
        "MasterJDBCConnectionString": {
            "Description": "JDBC connection string for the master database",
            "Value": {
                "Fn::Join": [
                    "",
                    [
                        "jdbc:mysql://",
                        {"Fn::GetAtt": ["MasterDB", "Endpoint.Address"]},
                        ":",
                        {"Fn::GetAtt": ["MasterDB", "Endpoint.Port"]},
                        "/",
                        {"Ref": "DBName"},
                    ],
                ]
            },
        },
        "ReplicaJDBCConnectionString": {
            "Description": "JDBC connection string for the replica database",
            "Value": {
                "Fn::Join": [
                    "",
                    [
                        "jdbc:mysql://",
                        {"Fn::GetAtt": ["ReplicaDB", "Endpoint.Address"]},
                        ":",
                        {"Fn::GetAtt": ["ReplicaDB", "Endpoint.Port"]},
                        "/",
                        {"Ref": "DBName"},
                    ],
                ]
            },
        },
    },
}
