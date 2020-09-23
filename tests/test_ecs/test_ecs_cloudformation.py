import boto3
import json
from copy import deepcopy
from moto import mock_cloudformation, mock_ecs


@mock_ecs
@mock_cloudformation
def test_update_task_definition_family_through_cloudformation_should_trigger_a_replacement():
    template1 = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testTaskDefinition": {
                "Type": "AWS::ECS::TaskDefinition",
                "Properties": {
                    "Family": "testTaskDefinition1",
                    "ContainerDefinitions": [
                        {
                            "Name": "ecs-sample",
                            "Image": "amazon/amazon-ecs-sample",
                            "Cpu": "200",
                            "Memory": "500",
                            "Essential": "true",
                        }
                    ],
                    "Volumes": [],
                },
            }
        },
    }
    template1_json = json.dumps(template1)
    cfn_conn = boto3.client("cloudformation", region_name="us-west-1")
    cfn_conn.create_stack(StackName="test_stack", TemplateBody=template1_json)

    template2 = deepcopy(template1)
    template2["Resources"]["testTaskDefinition"]["Properties"][
        "Family"
    ] = "testTaskDefinition2"
    template2_json = json.dumps(template2)
    cfn_conn.update_stack(StackName="test_stack", TemplateBody=template2_json)

    ecs_conn = boto3.client("ecs", region_name="us-west-1")
    resp = ecs_conn.list_task_definitions(familyPrefix="testTaskDefinition2")
    len(resp["taskDefinitionArns"]).should.equal(1)
    resp["taskDefinitionArns"][0].endswith("testTaskDefinition2:1").should.be.true


@mock_ecs
@mock_cloudformation
def test_create_service_through_cloudformation():
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testCluster": {
                "Type": "AWS::ECS::Cluster",
                "Properties": {"ClusterName": "testcluster"},
            },
            "testTaskDefinition": {
                "Type": "AWS::ECS::TaskDefinition",
                "Properties": {
                    "ContainerDefinitions": [
                        {
                            "Name": "ecs-sample",
                            "Image": "amazon/amazon-ecs-sample",
                            "Cpu": "200",
                            "Memory": "500",
                            "Essential": "true",
                        }
                    ],
                    "Volumes": [],
                },
            },
            "testService": {
                "Type": "AWS::ECS::Service",
                "Properties": {
                    "Cluster": {"Ref": "testCluster"},
                    "DesiredCount": 10,
                    "TaskDefinition": {"Ref": "testTaskDefinition"},
                },
            },
        },
    }
    template_json = json.dumps(template)
    cfn_conn = boto3.client("cloudformation", region_name="us-west-1")
    cfn_conn.create_stack(StackName="test_stack", TemplateBody=template_json)

    ecs_conn = boto3.client("ecs", region_name="us-west-1")
    resp = ecs_conn.list_services(cluster="testcluster")
    len(resp["serviceArns"]).should.equal(1)


@mock_ecs
@mock_cloudformation
def test_update_service_through_cloudformation_should_trigger_replacement():
    template1 = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testCluster": {
                "Type": "AWS::ECS::Cluster",
                "Properties": {"ClusterName": "testcluster"},
            },
            "testTaskDefinition": {
                "Type": "AWS::ECS::TaskDefinition",
                "Properties": {
                    "ContainerDefinitions": [
                        {
                            "Name": "ecs-sample",
                            "Image": "amazon/amazon-ecs-sample",
                            "Cpu": "200",
                            "Memory": "500",
                            "Essential": "true",
                        }
                    ],
                    "Volumes": [],
                },
            },
            "testService": {
                "Type": "AWS::ECS::Service",
                "Properties": {
                    "Cluster": {"Ref": "testCluster"},
                    "TaskDefinition": {"Ref": "testTaskDefinition"},
                    "DesiredCount": 10,
                },
            },
        },
    }
    template_json1 = json.dumps(template1)
    cfn_conn = boto3.client("cloudformation", region_name="us-west-1")
    cfn_conn.create_stack(StackName="test_stack", TemplateBody=template_json1)
    template2 = deepcopy(template1)
    template2["Resources"]["testService"]["Properties"]["DesiredCount"] = 5
    template2_json = json.dumps(template2)
    cfn_conn.update_stack(StackName="test_stack", TemplateBody=template2_json)

    ecs_conn = boto3.client("ecs", region_name="us-west-1")
    resp = ecs_conn.list_services(cluster="testcluster")
    len(resp["serviceArns"]).should.equal(1)


@mock_ecs
@mock_cloudformation
def test_create_cluster_through_cloudformation():
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testCluster": {
                "Type": "AWS::ECS::Cluster",
                "Properties": {"ClusterName": "testcluster"},
            }
        },
    }
    template_json = json.dumps(template)

    ecs_conn = boto3.client("ecs", region_name="us-west-1")
    resp = ecs_conn.list_clusters()
    len(resp["clusterArns"]).should.equal(0)

    cfn_conn = boto3.client("cloudformation", region_name="us-west-1")
    cfn_conn.create_stack(StackName="test_stack", TemplateBody=template_json)

    resp = ecs_conn.list_clusters()
    len(resp["clusterArns"]).should.equal(1)


@mock_ecs
@mock_cloudformation
def test_create_cluster_through_cloudformation_no_name():
    # cloudformation should create a cluster name for you if you do not provide it
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-cluster.html#cfn-ecs-cluster-clustername
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {"testCluster": {"Type": "AWS::ECS::Cluster"}},
    }
    template_json = json.dumps(template)
    cfn_conn = boto3.client("cloudformation", region_name="us-west-1")
    cfn_conn.create_stack(StackName="test_stack", TemplateBody=template_json)

    ecs_conn = boto3.client("ecs", region_name="us-west-1")
    resp = ecs_conn.list_clusters()
    len(resp["clusterArns"]).should.equal(1)


@mock_ecs
@mock_cloudformation
def test_update_cluster_name_through_cloudformation_should_trigger_a_replacement():
    template1 = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testCluster": {
                "Type": "AWS::ECS::Cluster",
                "Properties": {"ClusterName": "testcluster1"},
            }
        },
    }
    template2 = deepcopy(template1)
    template2["Resources"]["testCluster"]["Properties"]["ClusterName"] = "testcluster2"
    template1_json = json.dumps(template1)
    cfn_conn = boto3.client("cloudformation", region_name="us-west-1")
    stack_resp = cfn_conn.create_stack(
        StackName="test_stack", TemplateBody=template1_json
    )

    template2_json = json.dumps(template2)
    cfn_conn.update_stack(StackName=stack_resp["StackId"], TemplateBody=template2_json)
    ecs_conn = boto3.client("ecs", region_name="us-west-1")
    resp = ecs_conn.list_clusters()
    len(resp["clusterArns"]).should.equal(1)
    resp["clusterArns"][0].endswith("testcluster2").should.be.true


@mock_ecs
@mock_cloudformation
def test_create_task_definition_through_cloudformation():
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ECS Cluster Test CloudFormation",
        "Resources": {
            "testTaskDefinition": {
                "Type": "AWS::ECS::TaskDefinition",
                "Properties": {
                    "ContainerDefinitions": [
                        {
                            "Name": "ecs-sample",
                            "Image": "amazon/amazon-ecs-sample",
                            "Cpu": "200",
                            "Memory": "500",
                            "Essential": "true",
                        }
                    ],
                    "Volumes": [],
                },
            }
        },
    }
    template_json = json.dumps(template)
    cfn_conn = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = "test_stack"
    cfn_conn.create_stack(StackName=stack_name, TemplateBody=template_json)

    ecs_conn = boto3.client("ecs", region_name="us-west-1")
    resp = ecs_conn.list_task_definitions()
    len(resp["taskDefinitionArns"]).should.equal(1)
    task_definition_arn = resp["taskDefinitionArns"][0]

    task_definition_details = cfn_conn.describe_stack_resource(
        StackName=stack_name, LogicalResourceId="testTaskDefinition"
    )["StackResourceDetail"]
    task_definition_details["PhysicalResourceId"].should.equal(task_definition_arn)
