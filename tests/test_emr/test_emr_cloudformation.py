import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from tests import EXAMPLE_AMI_ID

template = """{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Description": "The AWS CloudFormation template for this Serverless application",
  "Resources": {
    "Cluster1": {
        "Type" : "AWS::EMR::Cluster",
        "Properties" : {
          "Instances" : {
              "CoreInstanceGroup": {
                  "InstanceCount": 3,
                  "InstanceType": "m3g",
              }
          },
          "JobFlowRole" : "EMR_EC2_DefaultRole",
          "Name" : "my cluster",
          "ServiceRole" : "EMR_DefaultRole",
        }
    },
  },
  "Outputs": {
    "ClusterId": {
        "Description": "Cluster info",
        "Value": {
            "Fn::GetAtt": ["Cluster1", "Id"]
        },
    }
  }
}"""


@mock_aws
def test_create_simple_cluster__using_cloudformation():
    region = "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)
    emr = boto3.client("emr", region_name=region)
    cf.create_stack(StackName="teststack", TemplateBody=template)

    # Verify resources
    res = cf.describe_stack_resources(StackName="teststack")["StackResources"][0]
    cluster_id = res["PhysicalResourceId"]
    assert res["LogicalResourceId"] == "Cluster1"
    assert res["ResourceType"] == "AWS::EMR::Cluster"
    assert cluster_id.startswith("j-")

    # Verify outputs
    stack = cf.describe_stacks(StackName="teststack")["Stacks"][0]
    assert {
        "OutputKey": "ClusterId",
        "OutputValue": cluster_id,
        "Description": "Cluster info",
    } in stack["Outputs"]

    # Verify EMR Cluster
    cl = emr.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert cl["Name"] == "my cluster"
    assert cl["Ec2InstanceAttributes"]["IamInstanceProfile"] == "EMR_EC2_DefaultRole"
    assert cl["ServiceRole"] == "EMR_DefaultRole"
    assert cl["Tags"] == []


template_with_tags = {
    "Resources": {
        "Cluster1": {
            "Type": "AWS::EMR::Cluster",
            "Properties": {
                "Instances": {
                    "CoreInstanceGroup": {
                        "InstanceCount": 3,
                        "InstanceType": "m3g",
                    }
                },
                "JobFlowRole": "EMR_EC2_DefaultRole",
                "Name": "my cluster",
                "ServiceRole": "EMR_DefaultRole",
                "Tags": [
                    {"Key": "k1", "Value": "v1"},
                    {"Key": "k2", "Value": "v2"},
                ],
            },
        },
    },
}


@mock_aws
def test_create_simple_cluster_with_tags():
    region = "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)
    emr = boto3.client("emr", region_name=region)
    cf.create_stack(StackName="teststack", TemplateBody=json.dumps(template_with_tags))

    # Verify resources
    res = cf.describe_stack_resources(StackName="teststack")["StackResources"][0]
    cluster_id = res["PhysicalResourceId"]

    # Verify EMR Cluster
    cl = emr.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert cl["Tags"] == [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]


template_with_custom_ami = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "SubnetId": {"Type": "String"},
        "InstanceType": {"Type": "String"},
        "TerminationProtected": {"Type": "String", "Default": "false"},
        "ElasticMapReducePrincipal": {"Type": "String"},
        "Ec2Principal": {"Type": "String"},
    },
    "Resources": {
        "cluster": {
            "Type": "AWS::EMR::Cluster",
            "Properties": {
                "CustomAmiId": EXAMPLE_AMI_ID,
                "Instances": {
                    "MasterInstanceGroup": {
                        "InstanceCount": 1,
                        "InstanceType": {"Ref": "InstanceType"},
                        "Market": "ON_DEMAND",
                        "Name": "cfnMaster",
                    },
                    "CoreInstanceGroup": {
                        "InstanceCount": 1,
                        "InstanceType": {"Ref": "InstanceType"},
                        "Market": "ON_DEMAND",
                        "Name": "cfnCore",
                    },
                    "TaskInstanceGroups": [
                        {
                            "InstanceCount": 1,
                            "InstanceType": {"Ref": "InstanceType"},
                            "Market": "ON_DEMAND",
                            "Name": "cfnTask-1",
                        },
                        {
                            "InstanceCount": 1,
                            "InstanceType": {"Ref": "InstanceType"},
                            "Market": "ON_DEMAND",
                            "Name": "cfnTask-2",
                        },
                    ],
                    "TerminationProtected": {"Ref": "TerminationProtected"},
                    "Ec2SubnetId": {"Ref": "SubnetId"},
                },
                "Name": "CFNtest",
                "JobFlowRole": {"Ref": "emrEc2InstanceProfile"},
                "ServiceRole": {"Ref": "emrRole"},
                "ReleaseLabel": "release_2024",
                "VisibleToAllUsers": True,
                "Tags": [{"Key": "key1", "Value": "value1"}],
            },
        },
        "emrRole": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2008-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {
                                "Service": {"Ref": "ElasticMapReducePrincipal"}
                            },
                            "Action": "sts:AssumeRole",
                        }
                    ],
                },
                "Path": "/",
                "ManagedPolicyArns": [
                    "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
                ],
            },
        },
        "emrEc2Role": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2008-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {"Service": {"Ref": "Ec2Principal"}},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                },
                "Path": "/",
                "ManagedPolicyArns": [
                    "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
                ],
            },
        },
        "emrEc2InstanceProfile": {
            "Type": "AWS::IAM::InstanceProfile",
            "Properties": {"Path": "/", "Roles": [{"Ref": "emrEc2Role"}]},
        },
    },
}


@mock_aws
def test_create_cluster_with_custom_ami():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    params = [
        {"ParameterKey": "InstanceType", "ParameterValue": "i4s"},
        {"ParameterKey": "SubnetId", "ParameterValue": subnet.id},
        {
            "ParameterKey": "ElasticMapReducePrincipal",
            "ParameterValue": "emr_principal",
        },
        {"ParameterKey": "Ec2Principal", "ParameterValue": "ec2_principal"},
    ]

    region = "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)
    emr = boto3.client("emr", region_name=region)
    cf.create_stack(
        StackName="teststack",
        TemplateBody=json.dumps(template_with_custom_ami),
        Parameters=params,
    )

    # Verify resources
    res = cf.describe_stack_resources(StackName="teststack")["StackResources"]
    cluster = [r for r in res if r["ResourceType"] == "AWS::EMR::Cluster"][0]
    cluster_id = cluster["PhysicalResourceId"]

    instance_profile = [
        r for r in res if r["ResourceType"] == "AWS::IAM::InstanceProfile"
    ][0]
    instance_profile_id = instance_profile["PhysicalResourceId"]

    role = [r for r in res if r["ResourceType"] == "AWS::IAM::Role"][0]
    role_id = role["PhysicalResourceId"]

    # Verify EMR Cluster
    cl = emr.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert cl["Name"] == "CFNtest"
    assert cl["Ec2InstanceAttributes"]["Ec2SubnetId"] == subnet.id
    assert cl["Ec2InstanceAttributes"]["IamInstanceProfile"] == instance_profile_id
    assert cl["ServiceRole"] == role_id
    assert cl["ReleaseLabel"] == "release_2024"
    assert cl["CustomAmiId"] == EXAMPLE_AMI_ID


template_with_root_volume = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "InstanceType": {"Type": "String"},
        "ReleaseLabel": {"Type": "String"},
        "SubnetId": {"Type": "String"},
        "TerminationProtected": {"Type": "String", "Default": "false"},
        "EbsRootVolumeSize": {"Type": "String"},
    },
    "Resources": {
        "cluster": {
            "Type": "AWS::EMR::Cluster",
            "Properties": {
                "EbsRootVolumeSize": {"Ref": "EbsRootVolumeSize"},
                "Instances": {
                    "MasterInstanceGroup": {
                        "InstanceCount": 1,
                        "InstanceType": {"Ref": "InstanceType"},
                        "Market": "ON_DEMAND",
                        "Name": "cfnMaster",
                    },
                    "CoreInstanceGroup": {
                        "InstanceCount": 1,
                        "InstanceType": {"Ref": "InstanceType"},
                        "Market": "ON_DEMAND",
                        "Name": "cfnCore",
                    },
                    "TaskInstanceGroups": [
                        {
                            "InstanceCount": 1,
                            "InstanceType": {"Ref": "InstanceType"},
                            "Market": "ON_DEMAND",
                            "Name": "cfnTask-1",
                        },
                        {
                            "InstanceCount": 1,
                            "InstanceType": {"Ref": "InstanceType"},
                            "Market": "ON_DEMAND",
                            "Name": "cfnTask-2",
                        },
                    ],
                    "TerminationProtected": {"Ref": "TerminationProtected"},
                    "Ec2SubnetId": {"Ref": "SubnetId"},
                },
                "Name": "CFNtest",
                "JobFlowRole": {"Ref": "emrEc2InstanceProfile"},
                "ServiceRole": {"Ref": "emrRole"},
                "ReleaseLabel": {"Ref": "ReleaseLabel"},
                "VisibleToAllUsers": True,
                "Tags": [{"Key": "key1", "Value": "value1"}],
            },
        },
        "emrRole": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2008-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {"Service": "elasticmapreduce.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                },
                "Path": "/",
                "ManagedPolicyArns": [
                    "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
                ],
            },
        },
        "emrEc2Role": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2008-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {"Service": "ec2.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                },
                "Path": "/",
                "ManagedPolicyArns": [
                    "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
                ],
            },
        },
        "emrEc2InstanceProfile": {
            "Type": "AWS::IAM::InstanceProfile",
            "Properties": {"Path": "/", "Roles": [{"Ref": "emrEc2Role"}]},
        },
    },
}


@mock_aws
def test_create_cluster_with_root_volume():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    params = [
        {"ParameterKey": "InstanceType", "ParameterValue": "i4s"},
        {"ParameterKey": "ReleaseLabel", "ParameterValue": "latest"},
        {"ParameterKey": "EbsRootVolumeSize", "ParameterValue": "15"},
        {"ParameterKey": "SubnetId", "ParameterValue": subnet.id},
        {
            "ParameterKey": "ElasticMapReducePrincipal",
            "ParameterValue": "emr_principal",
        },
        {"ParameterKey": "Ec2Principal", "ParameterValue": "ec2_principal"},
    ]

    region = "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)
    emr = boto3.client("emr", region_name=region)
    cf.create_stack(
        StackName="teststack",
        TemplateBody=json.dumps(template_with_root_volume),
        Parameters=params,
    )

    # Verify resources
    res = cf.describe_stack_resources(StackName="teststack")["StackResources"]
    cluster = [r for r in res if r["ResourceType"] == "AWS::EMR::Cluster"][0]
    cluster_id = cluster["PhysicalResourceId"]

    instance_profile = [
        r for r in res if r["ResourceType"] == "AWS::IAM::InstanceProfile"
    ][0]
    instance_profile_id = instance_profile["PhysicalResourceId"]

    role = [r for r in res if r["ResourceType"] == "AWS::IAM::Role"][0]
    role_id = role["PhysicalResourceId"]

    # Verify EMR Cluster
    cl = emr.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert cl["Name"] == "CFNtest"
    assert cl["Ec2InstanceAttributes"]["Ec2SubnetId"] == subnet.id
    assert cl["Ec2InstanceAttributes"]["IamInstanceProfile"] == instance_profile_id
    assert cl["ServiceRole"] == role_id


template_with_kerberos_attrs = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "CrossRealmTrustPrincipalPassword": {"Type": "String"},
        "KdcAdminPassword": {"Type": "String"},
        "InstanceType": {"Type": "String"},
        "ReleaseLabel": {"Type": "String"},
        "SubnetId": {"Type": "String"},
    },
    "Resources": {
        "cluster": {
            "Type": "AWS::EMR::Cluster",
            "Properties": {
                "Instances": {
                    "MasterInstanceGroup": {
                        "InstanceCount": 1,
                        "InstanceType": {"Ref": "InstanceType"},
                        "Market": "ON_DEMAND",
                        "Name": "cfnMaster",
                    },
                    "CoreInstanceGroup": {
                        "InstanceCount": 1,
                        "InstanceType": {"Ref": "InstanceType"},
                        "Market": "ON_DEMAND",
                        "Name": "cfnCore",
                    },
                    "TaskInstanceGroups": [
                        {
                            "InstanceCount": 1,
                            "InstanceType": {"Ref": "InstanceType"},
                            "Market": "ON_DEMAND",
                            "Name": "cfnTask-1",
                        },
                        {
                            "InstanceCount": 1,
                            "InstanceType": {"Ref": "InstanceType"},
                            "Market": "ON_DEMAND",
                            "Name": "cfnTask-2",
                        },
                    ],
                    "Ec2SubnetId": {"Ref": "SubnetId"},
                },
                "Name": "CFNtest",
                "JobFlowRole": {"Ref": "emrEc2InstanceProfile"},
                "KerberosAttributes": {
                    "CrossRealmTrustPrincipalPassword": {
                        "Ref": "CrossRealmTrustPrincipalPassword"
                    },
                    "KdcAdminPassword": {"Ref": "KdcAdminPassword"},
                    "Realm": "EC2.INTERNAL",
                },
                "ServiceRole": {"Ref": "emrRole"},
                "ReleaseLabel": {"Ref": "ReleaseLabel"},
                "SecurityConfiguration": {"Ref": "securityConfiguration"},
                "VisibleToAllUsers": True,
                "Tags": [{"Key": "key1", "Value": "value1"}],
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
                            "Sid": "Enable IAM User Permissions",
                            "Effect": "Allow",
                            "Principal": {"AWS": {"Fn::GetAtt": ["emrEc2Role", "Arn"]}},
                            "Action": "kms:*",
                            "Resource": "*",
                        },
                        {
                            "Sid": "Enable IAM User Permissions",
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
                            "Action": "kms:*",
                            "Resource": "*",
                        },
                    ],
                }
            },
        },
        "securityConfiguration": {
            "Type": "AWS::EMR::SecurityConfiguration",
            "Properties": {
                "Name": "mysecconfig",
                "SecurityConfiguration": {
                    "AuthenticationConfiguration": {
                        "KerberosConfiguration": {
                            "Provider": "ClusterDedicatedKdc",
                            "ClusterDedicatedKdcConfiguration": {
                                "TicketLifetimeInHours": 24,
                                "CrossRealmTrustConfiguration": {
                                    "Realm": "AD.DOMAIN.COM",
                                    "Domain": "ad.domain.com",
                                    "AdminServer": "ad.domain.com",
                                    "KdcServer": "ad.domain.com",
                                },
                            },
                        }
                    }
                },
            },
        },
        "emrRole": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2008-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {"Service": "elasticmapreduce.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                },
                "Path": "/",
                "ManagedPolicyArns": [
                    "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
                ],
            },
        },
        "emrEc2Role": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2008-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {"Service": "ec2.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                },
                "Path": "/",
                "ManagedPolicyArns": [
                    "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
                ],
            },
        },
        "emrEc2InstanceProfile": {
            "Type": "AWS::IAM::InstanceProfile",
            "Properties": {"Path": "/", "Roles": [{"Ref": "emrEc2Role"}]},
        },
    },
    "Outputs": {"keyArn": {"Value": {"Fn::GetAtt": ["key", "Arn"]}}},
}


@mock_aws
def test_create_cluster_with_kerberos_attrs():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    params = [
        {"ParameterKey": "CrossRealmTrustPrincipalPassword", "ParameterValue": "p2ss"},
        {"ParameterKey": "KdcAdminPassword", "ParameterValue": "adminp2ss"},
        {"ParameterKey": "InstanceType", "ParameterValue": "i4s"},
        {"ParameterKey": "ReleaseLabel", "ParameterValue": "latest"},
        {"ParameterKey": "EbsRootVolumeSize", "ParameterValue": "15"},
        {"ParameterKey": "SubnetId", "ParameterValue": subnet.id},
        {
            "ParameterKey": "ElasticMapReducePrincipal",
            "ParameterValue": "emr_principal",
        },
        {"ParameterKey": "Ec2Principal", "ParameterValue": "ec2_principal"},
    ]

    region = "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)
    emr = boto3.client("emr", region_name=region)
    cf.create_stack(
        StackName="teststack",
        TemplateBody=json.dumps(template_with_kerberos_attrs),
        Parameters=params,
    )

    # Verify resources
    res = cf.describe_stack_resources(StackName="teststack")["StackResources"]
    cluster = [r for r in res if r["ResourceType"] == "AWS::EMR::Cluster"][0]
    cluster_id = cluster["PhysicalResourceId"]

    instance_profile = [
        r for r in res if r["ResourceType"] == "AWS::IAM::InstanceProfile"
    ][0]
    instance_profile_id = instance_profile["PhysicalResourceId"]

    role = [r for r in res if r["ResourceType"] == "AWS::IAM::Role"][0]
    role_id = role["PhysicalResourceId"]

    # Verify EMR Cluster
    cl = emr.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert cl["Name"] == "CFNtest"
    assert cl["Ec2InstanceAttributes"]["Ec2SubnetId"] == subnet.id
    assert cl["Ec2InstanceAttributes"]["IamInstanceProfile"] == instance_profile_id
    assert cl["ServiceRole"] == role_id

    kerberos = cl["KerberosAttributes"]
    assert kerberos == {
        "Realm": "EC2.INTERNAL",
        "KdcAdminPassword": "adminp2ss",
        "CrossRealmTrustPrincipalPassword": "p2ss",
    }

    # Verify everything can be deleted
    cf.delete_stack(StackName="teststack")

    cl = emr.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert cl["Status"]["State"] == "TERMINATED"

    with pytest.raises(ClientError) as exc:
        emr.describe_security_configuration(Name="mysecconfig")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"


template_with_simple_instance_group_config = {
    "Resources": {
        "Cluster1": {
            "Type": "AWS::EMR::Cluster",
            "Properties": {
                "Instances": {
                    "CoreInstanceGroup": {
                        "InstanceCount": 3,
                        "InstanceType": "m3g",
                    }
                },
                "JobFlowRole": "EMR_EC2_DefaultRole",
                "Name": "my cluster",
                "ServiceRole": "EMR_DefaultRole",
            },
        },
        "TestInstanceGroupConfig": {
            "Type": "AWS::EMR::InstanceGroupConfig",
            "Properties": {
                "InstanceCount": 2,
                "InstanceType": "m3.xlarge",
                "InstanceRole": "TASK",
                "Market": "ON_DEMAND",
                "Name": "cfnTask2",
                "JobFlowId": {"Ref": "Cluster1"},
            },
        },
    },
}


@mock_aws
def test_create_simple_instance_group():
    region = "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)
    emr = boto3.client("emr", region_name=region)
    cf.create_stack(
        StackName="teststack",
        TemplateBody=json.dumps(template_with_simple_instance_group_config),
    )

    # Verify resources
    res = cf.describe_stack_resources(StackName="teststack")["StackResources"][0]
    cluster_id = res["PhysicalResourceId"]

    ig = emr.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"][0]
    assert ig["Name"] == "cfnTask2"
    assert ig["Market"] == "ON_DEMAND"
    assert ig["InstanceGroupType"] == "TASK"
    assert ig["InstanceType"] == "m3.xlarge"


template_with_advanced_instance_group_config = {
    "Resources": {
        "Cluster1": {
            "Type": "AWS::EMR::Cluster",
            "Properties": {
                "Instances": {
                    "CoreInstanceGroup": {
                        "InstanceCount": 3,
                        "InstanceType": "m3g",
                    }
                },
                "JobFlowRole": "EMR_EC2_DefaultRole",
                "Name": "my cluster",
                "ServiceRole": "EMR_DefaultRole",
            },
        },
        "TestInstanceGroupConfig": {
            "Type": "AWS::EMR::InstanceGroupConfig",
            "Properties": {
                "InstanceCount": 1,
                "InstanceType": "m4.large",
                "InstanceRole": "TASK",
                "Market": "ON_DEMAND",
                "Name": "cfnTask3",
                "JobFlowId": {"Ref": "Cluster1"},
                "EbsConfiguration": {
                    "EbsOptimized": True,
                    "EbsBlockDeviceConfigs": [
                        {
                            "VolumesPerInstance": 2,
                            "VolumeSpecification": {
                                "Iops": 10,
                                "SizeInGB": 50,
                                "Throughput": 100,
                                "VolumeType": "gp3",
                            },
                        }
                    ],
                },
                "AutoScalingPolicy": {
                    "Constraints": {"MinCapacity": 1, "MaxCapacity": 4},
                    "Rules": [
                        {
                            "Name": "Scale-out",
                            "Description": "Scale-out policy",
                            "Action": {
                                "SimpleScalingPolicyConfiguration": {
                                    "AdjustmentType": "CHANGE_IN_CAPACITY",
                                    "ScalingAdjustment": 1,
                                    "CoolDown": 300,
                                }
                            },
                            "Trigger": {
                                "CloudWatchAlarmDefinition": {
                                    "Dimensions": [
                                        {
                                            "Key": "JobFlowId",
                                            "Value": "${emr.clusterId}",
                                        }
                                    ],
                                    "EvaluationPeriods": 1,
                                    "Namespace": "AWS/ElasticMapReduce",
                                    "Period": 300,
                                    "ComparisonOperator": "LESS_THAN",
                                    "Statistic": "AVERAGE",
                                    "Threshold": 15,
                                    "Unit": "PERCENT",
                                    "MetricName": "YARNMemoryAvailablePercentage",
                                }
                            },
                        },
                        {
                            "Name": "Scale-in",
                            "Description": "Scale-in policy",
                            "Action": {
                                "SimpleScalingPolicyConfiguration": {
                                    "AdjustmentType": "CHANGE_IN_CAPACITY",
                                    "ScalingAdjustment": -1,
                                    "CoolDown": 300,
                                }
                            },
                            "Trigger": {
                                "CloudWatchAlarmDefinition": {
                                    "Dimensions": [
                                        {
                                            "Key": "JobFlowId",
                                            "Value": "${emr.clusterId}",
                                        }
                                    ],
                                    "EvaluationPeriods": 1,
                                    "Namespace": "AWS/ElasticMapReduce",
                                    "Period": 300,
                                    "ComparisonOperator": "GREATER_THAN",
                                    "Statistic": "AVERAGE",
                                    "Threshold": 75,
                                    "Unit": "PERCENT",
                                    "MetricName": "YARNMemoryAvailablePercentage",
                                }
                            },
                        },
                    ],
                },
            },
        },
    },
}


@mock_aws
def test_create_advanced_instance_group():
    region = "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)
    emr = boto3.client("emr", region_name=region)
    cf.create_stack(
        StackName="teststack",
        TemplateBody=json.dumps(template_with_advanced_instance_group_config),
    )

    # Verify resources
    res = cf.describe_stack_resources(StackName="teststack")["StackResources"][0]
    cluster_id = res["PhysicalResourceId"]

    ig = emr.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"][0]
    assert ig["Name"] == "cfnTask3"
    assert ig["Market"] == "ON_DEMAND"
    assert ig["InstanceGroupType"] == "TASK"
    assert ig["InstanceType"] == "m4.large"

    as_policy = ig["AutoScalingPolicy"]
    assert as_policy["Status"] == {"State": "ATTACHED"}
    assert as_policy["Constraints"] == {"MinCapacity": 1, "MaxCapacity": 4}

    ebs = ig["EbsBlockDevices"]
    assert ebs[0]["VolumeSpecification"] == {
        "VolumeType": "gp3",
        "Iops": 10,
        "SizeInGB": 50,
    }
