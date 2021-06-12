from __future__ import unicode_literals
from datetime import datetime

from botocore.exceptions import ClientError
import boto3
import sure  # noqa
import json

from moto.core import ACCOUNT_ID
from moto.ec2 import utils as ec2_utils
from uuid import UUID

from moto import mock_ecs
from moto import mock_ec2
from moto.ecs.exceptions import (
    ClusterNotFoundException,
    ServiceNotFoundException,
    InvalidParameterException,
    TaskDefinitionNotFoundException,
    RevisionNotFoundException,
)
import pytest
from tests import EXAMPLE_AMI_ID


@mock_ecs
def test_create_cluster():
    client = boto3.client("ecs", region_name="us-east-1")
    response = client.create_cluster(clusterName="test_ecs_cluster")
    response["cluster"]["clusterName"].should.equal("test_ecs_cluster")
    response["cluster"]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    response["cluster"]["status"].should.equal("ACTIVE")
    response["cluster"]["registeredContainerInstancesCount"].should.equal(0)
    response["cluster"]["runningTasksCount"].should.equal(0)
    response["cluster"]["pendingTasksCount"].should.equal(0)
    response["cluster"]["activeServicesCount"].should.equal(0)


@mock_ecs
def test_list_clusters():
    client = boto3.client("ecs", region_name="us-east-2")
    _ = client.create_cluster(clusterName="test_cluster0")
    _ = client.create_cluster(clusterName="test_cluster1")
    response = client.list_clusters()
    response["clusterArns"].should.contain(
        "arn:aws:ecs:us-east-2:{}:cluster/test_cluster0".format(ACCOUNT_ID)
    )
    response["clusterArns"].should.contain(
        "arn:aws:ecs:us-east-2:{}:cluster/test_cluster1".format(ACCOUNT_ID)
    )


@mock_ecs
def test_describe_clusters():
    client = boto3.client("ecs", region_name="us-east-1")
    response = client.describe_clusters(clusters=["some-cluster"])
    response["failures"].should.contain(
        {
            "arn": "arn:aws:ecs:us-east-1:{}:cluster/some-cluster".format(ACCOUNT_ID),
            "reason": "MISSING",
        }
    )


@mock_ecs
def test_delete_cluster():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    response = client.delete_cluster(cluster="test_ecs_cluster")
    response["cluster"]["clusterName"].should.equal("test_ecs_cluster")
    response["cluster"]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    response["cluster"]["status"].should.equal("ACTIVE")
    response["cluster"]["registeredContainerInstancesCount"].should.equal(0)
    response["cluster"]["runningTasksCount"].should.equal(0)
    response["cluster"]["pendingTasksCount"].should.equal(0)
    response["cluster"]["activeServicesCount"].should.equal(0)

    response = client.list_clusters()
    len(response["clusterArns"]).should.equal(0)


@mock_ecs
def test_delete_cluster_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")
    client.delete_cluster.when.called_with(cluster="not_a_cluster").should.throw(
        ClientError, ClusterNotFoundException().message
    )


@mock_ecs
def test_register_task_definition():
    client = boto3.client("ecs", region_name="us-east-1")
    # Registering with minimal definition
    definition = dict(
        family="test_ecs_task",
        containerDefinitions=[
            {"name": "hello_world", "image": "hello-world:latest", "memory": 400,}
        ],
    )

    response = client.register_task_definition(**definition)

    response["taskDefinition"] = response["taskDefinition"]
    response["taskDefinition"]["family"].should.equal("test_ecs_task")
    response["taskDefinition"]["revision"].should.equal(1)
    response["taskDefinition"]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    response["taskDefinition"]["networkMode"].should.equal("bridge")
    response["taskDefinition"]["volumes"].should.equal([])
    response["taskDefinition"]["placementConstraints"].should.equal([])
    response["taskDefinition"]["compatibilities"].should.equal(["EC2"])
    response["taskDefinition"].shouldnt.have.key("requiresCompatibilities")
    response["taskDefinition"].shouldnt.have.key("cpu")
    response["taskDefinition"].shouldnt.have.key("memory")

    response["taskDefinition"]["containerDefinitions"][0]["name"].should.equal(
        "hello_world"
    )
    response["taskDefinition"]["containerDefinitions"][0]["image"].should.equal(
        "hello-world:latest"
    )
    response["taskDefinition"]["containerDefinitions"][0]["cpu"].should.equal(0)
    response["taskDefinition"]["containerDefinitions"][0]["portMappings"].should.equal(
        []
    )
    response["taskDefinition"]["containerDefinitions"][0]["essential"].should.equal(
        True
    )
    response["taskDefinition"]["containerDefinitions"][0]["environment"].should.equal(
        []
    )
    response["taskDefinition"]["containerDefinitions"][0]["mountPoints"].should.equal(
        []
    )
    response["taskDefinition"]["containerDefinitions"][0]["volumesFrom"].should.equal(
        []
    )

    # Registering again increments the revision
    response = client.register_task_definition(**definition)

    response["taskDefinition"]["revision"].should.equal(2)
    response["taskDefinition"]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:2".format(ACCOUNT_ID)
    )

    # Registering with optional top-level params
    definition["requiresCompatibilities"] = ["FARGATE"]
    definition["taskRoleArn"] = "my-custom-task-role-arn"
    definition["executionRoleArn"] = "my-custom-execution-role-arn"
    response = client.register_task_definition(**definition)
    response["taskDefinition"]["requiresCompatibilities"].should.equal(["FARGATE"])
    response["taskDefinition"]["compatibilities"].should.equal(["EC2", "FARGATE"])
    response["taskDefinition"]["networkMode"].should.equal("awsvpc")
    response["taskDefinition"]["taskRoleArn"].should.equal("my-custom-task-role-arn")
    response["taskDefinition"]["executionRoleArn"].should.equal(
        "my-custom-execution-role-arn"
    )

    definition["requiresCompatibilities"] = ["EC2", "FARGATE"]
    response = client.register_task_definition(**definition)
    response["taskDefinition"]["requiresCompatibilities"].should.equal(
        ["EC2", "FARGATE"]
    )
    response["taskDefinition"]["compatibilities"].should.equal(["EC2", "FARGATE"])
    response["taskDefinition"]["networkMode"].should.equal("awsvpc")

    definition["cpu"] = "512"
    response = client.register_task_definition(**definition)
    response["taskDefinition"]["cpu"].should.equal("512")

    definition.update({"memory": "512"})
    response = client.register_task_definition(**definition)
    response["taskDefinition"]["memory"].should.equal("512")

    # Registering with optional container params
    definition["containerDefinitions"][0]["cpu"] = 512
    response = client.register_task_definition(**definition)
    response["taskDefinition"]["containerDefinitions"][0]["cpu"].should.equal(512)

    definition["containerDefinitions"][0]["essential"] = False
    response = client.register_task_definition(**definition)
    response["taskDefinition"]["containerDefinitions"][0]["essential"].should.equal(
        False
    )

    definition["containerDefinitions"][0]["environment"] = [
        {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
    ]
    response = client.register_task_definition(**definition)
    response["taskDefinition"]["containerDefinitions"][0]["environment"][0][
        "name"
    ].should.equal("AWS_ACCESS_KEY_ID")
    response["taskDefinition"]["containerDefinitions"][0]["environment"][0][
        "value"
    ].should.equal("SOME_ACCESS_KEY")

    definition["containerDefinitions"][0]["logConfiguration"] = {
        "logDriver": "json-file"
    }
    response = client.register_task_definition(**definition)
    response["taskDefinition"]["containerDefinitions"][0]["logConfiguration"][
        "logDriver"
    ].should.equal("json-file")


@mock_ecs
def test_list_task_definitions():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world2",
                "image": "docker/hello-world2:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY2"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.list_task_definitions()
    len(response["taskDefinitionArns"]).should.equal(2)
    response["taskDefinitionArns"][0].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    response["taskDefinitionArns"][1].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:2".format(ACCOUNT_ID)
    )


@mock_ecs
def test_list_task_definitions_with_family_prefix():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.register_task_definition(
        family="test_ecs_task_a",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.register_task_definition(
        family="test_ecs_task_a",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.register_task_definition(
        family="test_ecs_task_b",
        containerDefinitions=[
            {
                "name": "hello_world2",
                "image": "docker/hello-world2:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY2"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    empty_response = client.list_task_definitions(familyPrefix="test_ecs_task")
    len(empty_response["taskDefinitionArns"]).should.equal(0)
    filtered_response = client.list_task_definitions(familyPrefix="test_ecs_task_a")
    len(filtered_response["taskDefinitionArns"]).should.equal(2)
    filtered_response["taskDefinitionArns"][0].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task_a:1".format(ACCOUNT_ID)
    )
    filtered_response["taskDefinitionArns"][1].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task_a:2".format(ACCOUNT_ID)
    )


@mock_ecs
def test_describe_task_definitions():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
        tags=[{"key": "Name", "value": "test_ecs_task"}],
    )
    _ = client.register_task_definition(
        family="test_ecs_task",
        taskRoleArn="my-task-role-arn",
        executionRoleArn="my-execution-role-arn",
        containerDefinitions=[
            {
                "name": "hello_world2",
                "image": "docker/hello-world2:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY2"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world3",
                "image": "docker/hello-world3:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY3"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.describe_task_definition(taskDefinition="test_ecs_task")
    response["taskDefinition"]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:3".format(ACCOUNT_ID)
    )

    response = client.describe_task_definition(taskDefinition="test_ecs_task:2")
    response["taskDefinition"]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:2".format(ACCOUNT_ID)
    )
    response["taskDefinition"]["taskRoleArn"].should.equal("my-task-role-arn")
    response["taskDefinition"]["executionRoleArn"].should.equal("my-execution-role-arn")

    response = client.describe_task_definition(
        taskDefinition="test_ecs_task:1", include=["TAGS"]
    )
    response["tags"].should.equal([{"key": "Name", "value": "test_ecs_task"}])


@mock_ecs
def test_deregister_task_definition_1():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.deregister_task_definition(taskDefinition="test_ecs_task:1")
    type(response["taskDefinition"]).should.be(dict)
    response["taskDefinition"]["status"].should.equal("INACTIVE")
    response["taskDefinition"]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    response["taskDefinition"]["containerDefinitions"][0]["name"].should.equal(
        "hello_world"
    )
    response["taskDefinition"]["containerDefinitions"][0]["image"].should.equal(
        "docker/hello-world:latest"
    )
    response["taskDefinition"]["containerDefinitions"][0]["cpu"].should.equal(1024)
    response["taskDefinition"]["containerDefinitions"][0]["memory"].should.equal(400)
    response["taskDefinition"]["containerDefinitions"][0]["essential"].should.equal(
        True
    )
    response["taskDefinition"]["containerDefinitions"][0]["environment"][0][
        "name"
    ].should.equal("AWS_ACCESS_KEY_ID")
    response["taskDefinition"]["containerDefinitions"][0]["environment"][0][
        "value"
    ].should.equal("SOME_ACCESS_KEY")
    response["taskDefinition"]["containerDefinitions"][0]["logConfiguration"][
        "logDriver"
    ].should.equal("json-file")


@mock_ecs
def test_deregister_task_definition_2():
    client = boto3.client("ecs", region_name="us-east-1")
    client.deregister_task_definition.when.called_with(
        taskDefinition="fake_task"
    ).should.throw(ClientError, RevisionNotFoundException().message)
    client.deregister_task_definition.when.called_with(
        taskDefinition="fake_task:foo"
    ).should.throw(
        ClientError,
        InvalidParameterException("Invalid revision number. Number: foo").message,
    )
    client.deregister_task_definition.when.called_with(
        taskDefinition="fake_task:1"
    ).should.throw(ClientError, TaskDefinitionNotFoundException().message)


@mock_ecs
def test_create_service():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    response["service"]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    response["service"]["desiredCount"].should.equal(2)
    len(response["service"]["events"]).should.equal(0)
    len(response["service"]["loadBalancers"]).should.equal(0)
    response["service"]["pendingCount"].should.equal(0)
    response["service"]["runningCount"].should.equal(0)
    response["service"]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service".format(ACCOUNT_ID)
    )
    response["service"]["serviceName"].should.equal("test_ecs_service")
    response["service"]["status"].should.equal("ACTIVE")
    response["service"]["taskDefinition"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    response["service"]["schedulingStrategy"].should.equal("REPLICA")
    response["service"]["launchType"].should.equal("EC2")


@mock_ecs
def test_create_service_errors():
    # given
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )

    # not existing launch type
    # when
    with pytest.raises(ClientError) as e:
        client.create_service(
            cluster="test_ecs_cluster",
            serviceName="test_ecs_service",
            taskDefinition="test_ecs_task",
            desiredCount=2,
            launchType="SOMETHING",
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateService")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ClientException")
    ex.response["Error"]["Message"].should.equal(
        "launch type should be one of [EC2,FARGATE]"
    )


@mock_ecs
def test_create_service_scheduling_strategy():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        schedulingStrategy="DAEMON",
    )
    response["service"]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    response["service"]["desiredCount"].should.equal(2)
    len(response["service"]["events"]).should.equal(0)
    len(response["service"]["loadBalancers"]).should.equal(0)
    response["service"]["pendingCount"].should.equal(0)
    response["service"]["runningCount"].should.equal(0)
    response["service"]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service".format(ACCOUNT_ID)
    )
    response["service"]["serviceName"].should.equal("test_ecs_service")
    response["service"]["status"].should.equal("ACTIVE")
    response["service"]["taskDefinition"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    response["service"]["schedulingStrategy"].should.equal("DAEMON")


@mock_ecs
def test_list_services():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service1",
        taskDefinition="test_ecs_task",
        schedulingStrategy="REPLICA",
        desiredCount=2,
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service2",
        taskDefinition="test_ecs_task",
        schedulingStrategy="DAEMON",
        desiredCount=2,
    )
    unfiltered_response = client.list_services(cluster="test_ecs_cluster")
    len(unfiltered_response["serviceArns"]).should.equal(2)
    unfiltered_response["serviceArns"][0].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service1".format(ACCOUNT_ID)
    )
    unfiltered_response["serviceArns"][1].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service2".format(ACCOUNT_ID)
    )

    filtered_response = client.list_services(
        cluster="test_ecs_cluster", schedulingStrategy="REPLICA"
    )
    len(filtered_response["serviceArns"]).should.equal(1)
    filtered_response["serviceArns"][0].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service1".format(ACCOUNT_ID)
    )


@mock_ecs
def test_describe_services():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service1",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[{"key": "Name", "value": "test_ecs_service1"}],
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service2",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service3",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    response = client.describe_services(
        cluster="test_ecs_cluster",
        services=[
            "test_ecs_service1",
            "arn:aws:ecs:us-east-1:{}:service/test_ecs_service2".format(ACCOUNT_ID),
        ],
    )
    len(response["services"]).should.equal(2)
    response["services"][0]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service1".format(ACCOUNT_ID)
    )
    response["services"][0]["serviceName"].should.equal("test_ecs_service1")
    response["services"][1]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service2".format(ACCOUNT_ID)
    )
    response["services"][1]["serviceName"].should.equal("test_ecs_service2")

    response["services"][0]["deployments"][0]["desiredCount"].should.equal(2)
    response["services"][0]["deployments"][0]["pendingCount"].should.equal(2)
    response["services"][0]["deployments"][0]["runningCount"].should.equal(0)
    response["services"][0]["deployments"][0]["status"].should.equal("PRIMARY")
    response["services"][0]["deployments"][0]["launchType"].should.equal("EC2")
    (
        datetime.now()
        - response["services"][0]["deployments"][0]["createdAt"].replace(tzinfo=None)
    ).seconds.should.be.within(0, 10)
    (
        datetime.now()
        - response["services"][0]["deployments"][0]["updatedAt"].replace(tzinfo=None)
    ).seconds.should.be.within(0, 10)
    response = client.describe_services(
        cluster="test_ecs_cluster",
        services=[
            "test_ecs_service1",
            "arn:aws:ecs:us-east-1:{}:service/test_ecs_service2".format(ACCOUNT_ID),
        ],
        include=["TAGS"],
    )
    response["services"][0]["tags"].should.equal(
        [{"key": "Name", "value": "test_ecs_service1"}]
    )
    response["services"][1]["tags"].should.equal([])
    response["services"][0]["launchType"].should.equal("EC2")
    response["services"][1]["launchType"].should.equal("EC2")


@mock_ecs
def test_describe_services_scheduling_strategy():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service1",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service2",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        schedulingStrategy="DAEMON",
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service3",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    response = client.describe_services(
        cluster="test_ecs_cluster",
        services=[
            "test_ecs_service1",
            "arn:aws:ecs:us-east-1:{}:service/test_ecs_service2".format(ACCOUNT_ID),
            "test_ecs_service3",
        ],
    )
    len(response["services"]).should.equal(3)
    response["services"][0]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service1".format(ACCOUNT_ID)
    )
    response["services"][0]["serviceName"].should.equal("test_ecs_service1")
    response["services"][1]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service2".format(ACCOUNT_ID)
    )
    response["services"][1]["serviceName"].should.equal("test_ecs_service2")

    response["services"][0]["deployments"][0]["desiredCount"].should.equal(2)
    response["services"][0]["deployments"][0]["pendingCount"].should.equal(2)
    response["services"][0]["deployments"][0]["runningCount"].should.equal(0)
    response["services"][0]["deployments"][0]["status"].should.equal("PRIMARY")

    response["services"][0]["schedulingStrategy"].should.equal("REPLICA")
    response["services"][1]["schedulingStrategy"].should.equal("DAEMON")
    response["services"][2]["schedulingStrategy"].should.equal("REPLICA")


@mock_ecs
def test_describe_services_error_unknown_cluster():
    # given
    client = boto3.client("ecs", region_name="eu-central-1")
    cluster_name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.describe_services(
            cluster=cluster_name, services=["test"],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("DescribeServices")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ClusterNotFoundException")
    ex.response["Error"]["Message"].should.equal("Cluster not found.")


@mock_ecs
def test_describe_services_with_known_unknown_services():
    # given
    client = boto3.client("ecs", region_name="eu-central-1")
    cluster_name = "test_cluster"
    task_name = "test_task"
    service_name = "test_service"
    client.create_cluster(clusterName=cluster_name)
    client.register_task_definition(
        family=task_name,
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 256,
                "memory": 512,
                "essential": True,
            }
        ],
    )
    service_arn = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=task_name,
        desiredCount=1,
    )["service"]["serviceArn"]

    # when
    response = client.describe_services(
        cluster=cluster_name,
        services=[
            service_name,
            "unknown",
            service_arn,
            "arn:aws:ecs:eu-central-1:{}:service/unknown-2".format(ACCOUNT_ID),
        ],
    )

    # then
    services = response["services"]
    services.should.have.length_of(2)
    [service["serviceArn"] for service in services].should.equal(
        [service_arn, service_arn]
    )

    failures = response["failures"]
    failures.should.have.length_of(2)
    sorted(failures, key=lambda item: item["arn"]).should.equal(
        [
            {
                "arn": "arn:aws:ecs:eu-central-1:{}:service/unknown".format(ACCOUNT_ID),
                "reason": "MISSING",
            },
            {
                "arn": "arn:aws:ecs:eu-central-1:{}:service/unknown-2".format(
                    ACCOUNT_ID
                ),
                "reason": "MISSING",
            },
        ]
    )


@mock_ecs
def test_update_service():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    response["service"]["desiredCount"].should.equal(2)

    response = client.update_service(
        cluster="test_ecs_cluster",
        service="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=0,
    )
    response["service"]["desiredCount"].should.equal(0)
    response["service"]["schedulingStrategy"].should.equal("REPLICA")

    # Verify we can pass the ARNs of the cluster and service
    response = client.update_service(
        cluster=response["service"]["clusterArn"],
        service=response["service"]["serviceArn"],
        taskDefinition="test_ecs_task",
        desiredCount=1,
    )
    response["service"]["desiredCount"].should.equal(1)


@mock_ecs
def test_update_missing_service():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")

    client.update_service.when.called_with(
        cluster="test_ecs_cluster",
        service="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=0,
    ).should.throw(ClientError)


@mock_ecs
def test_delete_service():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    _ = client.update_service(
        cluster="test_ecs_cluster", service="test_ecs_service", desiredCount=0
    )
    response = client.delete_service(
        cluster="test_ecs_cluster", service="test_ecs_service"
    )
    response["service"]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    response["service"]["desiredCount"].should.equal(0)
    len(response["service"]["events"]).should.equal(0)
    len(response["service"]["loadBalancers"]).should.equal(0)
    response["service"]["pendingCount"].should.equal(0)
    response["service"]["runningCount"].should.equal(0)
    response["service"]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service".format(ACCOUNT_ID)
    )
    response["service"]["serviceName"].should.equal("test_ecs_service")
    response["service"]["status"].should.equal("ACTIVE")
    response["service"]["schedulingStrategy"].should.equal("REPLICA")
    response["service"]["taskDefinition"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )


@mock_ecs
def test_delete_service_force():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    response = client.delete_service(
        cluster="test_ecs_cluster", service="test_ecs_service", force=True
    )
    response["service"]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    len(response["service"]["events"]).should.equal(0)
    len(response["service"]["loadBalancers"]).should.equal(0)
    response["service"]["pendingCount"].should.equal(0)
    response["service"]["runningCount"].should.equal(0)
    response["service"]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service".format(ACCOUNT_ID)
    )
    response["service"]["serviceName"].should.equal("test_ecs_service")
    response["service"]["status"].should.equal("ACTIVE")
    response["service"]["schedulingStrategy"].should.equal("REPLICA")
    response["service"]["taskDefinition"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )


@mock_ecs
def test_delete_service_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")

    # Raises ClusterNotFoundException because "default" is not a cluster
    client.delete_service.when.called_with(service="not_as_service").should.throw(
        ClientError, ClusterNotFoundException().message
    )

    _ = client.create_cluster()
    client.delete_service.when.called_with(service="not_as_service").should.throw(
        ClientError, ServiceNotFoundException().message
    )

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
            }
        ],
    )

    _ = client.create_service(
        serviceName="test_ecs_service", taskDefinition="test_ecs_task", desiredCount=1,
    )

    client.delete_service.when.called_with(service="test_ecs_service").should.throw(
        ClientError,
        InvalidParameterException(
            "The service cannot be stopped while it is scaled above 0."
        ).message,
    )


@mock_ecs
def test_update_service_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")

    client.update_service.when.called_with(
        service="not_a_service", desiredCount=0
    ).should.throw(ClientError, ClusterNotFoundException().message)

    _ = client.create_cluster()

    client.update_service.when.called_with(
        service="not_a_service", desiredCount=0
    ).should.throw(ClientError, ServiceNotFoundException().message)


@mock_ec2
@mock_ecs
def test_register_container_instance():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    response["containerInstance"]["ec2InstanceId"].should.equal(test_instance.id)
    full_arn = response["containerInstance"]["containerInstanceArn"]
    arn_part = full_arn.split("/")
    arn_part[0].should.equal(
        "arn:aws:ecs:us-east-1:{}:container-instance".format(ACCOUNT_ID)
    )
    arn_part[1].should.equal(str(UUID(arn_part[1])))
    response["containerInstance"]["status"].should.equal("ACTIVE")
    len(response["containerInstance"]["registeredResources"]).should.equal(4)
    len(response["containerInstance"]["remainingResources"]).should.equal(4)
    response["containerInstance"]["agentConnected"].should.equal(True)
    response["containerInstance"]["versionInfo"]["agentVersion"].should.equal("1.0.0")
    response["containerInstance"]["versionInfo"]["agentHash"].should.equal("4023248")
    response["containerInstance"]["versionInfo"]["dockerVersion"].should.equal(
        "DockerVersion: 1.5.0"
    )


@mock_ec2
@mock_ecs
def test_deregister_container_instance():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )
    container_instance_id = response["containerInstance"]["containerInstanceArn"]
    response = ecs_client.deregister_container_instance(
        cluster=test_cluster_name, containerInstance=container_instance_id
    )
    container_instances_response = ecs_client.list_container_instances(
        cluster=test_cluster_name
    )
    len(container_instances_response["containerInstanceArns"]).should.equal(0)

    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )
    container_instance_id = response["containerInstance"]["containerInstanceArn"]
    _ = ecs_client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )

    response = ecs_client.start_task(
        cluster="test_ecs_cluster",
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="moto",
    )
    with pytest.raises(Exception) as e:
        ecs_client.deregister_container_instance(
            cluster=test_cluster_name, containerInstance=container_instance_id
        ).should.have.raised(Exception)
    container_instances_response = ecs_client.list_container_instances(
        cluster=test_cluster_name
    )
    len(container_instances_response["containerInstanceArns"]).should.equal(1)
    ecs_client.deregister_container_instance(
        cluster=test_cluster_name, containerInstance=container_instance_id, force=True
    )
    container_instances_response = ecs_client.list_container_instances(
        cluster=test_cluster_name
    )
    len(container_instances_response["containerInstanceArns"]).should.equal(0)


@mock_ec2
@mock_ecs
def test_list_container_instances():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"
    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    instance_to_create = 3
    test_instance_arns = []
    for i in range(0, instance_to_create):
        test_instance = ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
        )[0]

        instance_id_document = json.dumps(
            ec2_utils.generate_instance_identity_document(test_instance)
        )

        response = ecs_client.register_container_instance(
            cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
        )

        test_instance_arns.append(response["containerInstance"]["containerInstanceArn"])

    response = ecs_client.list_container_instances(cluster=test_cluster_name)

    len(response["containerInstanceArns"]).should.equal(instance_to_create)
    for arn in test_instance_arns:
        response["containerInstanceArns"].should.contain(arn)


@mock_ec2
@mock_ecs
def test_describe_container_instances():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"
    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    instance_to_create = 3
    test_instance_arns = []
    for i in range(0, instance_to_create):
        test_instance = ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
        )[0]

        instance_id_document = json.dumps(
            ec2_utils.generate_instance_identity_document(test_instance)
        )

        response = ecs_client.register_container_instance(
            cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
        )

        test_instance_arns.append(response["containerInstance"]["containerInstanceArn"])

    test_instance_ids = list(map((lambda x: x.split("/")[1]), test_instance_arns))
    response = ecs_client.describe_container_instances(
        cluster=test_cluster_name, containerInstances=test_instance_ids
    )
    len(response["failures"]).should.equal(0)
    len(response["containerInstances"]).should.equal(instance_to_create)
    response_arns = [
        ci["containerInstanceArn"] for ci in response["containerInstances"]
    ]
    for arn in test_instance_arns:
        response_arns.should.contain(arn)
    for instance in response["containerInstances"]:
        instance.keys().should.contain("runningTasksCount")
        instance.keys().should.contain("pendingTasksCount")
        instance["registeredAt"].should.be.a("datetime.datetime")

    with pytest.raises(ClientError) as e:
        ecs_client.describe_container_instances(
            cluster=test_cluster_name, containerInstances=[]
        )


@mock_ecs
def test_describe_container_instances_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")

    client.describe_container_instances.when.called_with(
        containerInstances=[]
    ).should.throw(ClientError, ClusterNotFoundException().message)

    _ = client.create_cluster()
    client.describe_container_instances.when.called_with(
        containerInstances=[]
    ).should.throw(
        ClientError,
        InvalidParameterException("Container Instances cannot be empty.").message,
    )


@mock_ec2
@mock_ecs
def test_update_container_instances_state():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"
    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    instance_to_create = 3
    test_instance_arns = []
    for i in range(0, instance_to_create):
        test_instance = ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
        )[0]

        instance_id_document = json.dumps(
            ec2_utils.generate_instance_identity_document(test_instance)
        )

        response = ecs_client.register_container_instance(
            cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
        )

        test_instance_arns.append(response["containerInstance"]["containerInstanceArn"])

    test_instance_ids = list(map((lambda x: x.split("/")[1]), test_instance_arns))
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name,
        containerInstances=test_instance_ids,
        status="DRAINING",
    )
    len(response["failures"]).should.equal(0)
    len(response["containerInstances"]).should.equal(instance_to_create)
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        status.should.equal("DRAINING")
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name,
        containerInstances=test_instance_ids,
        status="DRAINING",
    )
    len(response["failures"]).should.equal(0)
    len(response["containerInstances"]).should.equal(instance_to_create)
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        status.should.equal("DRAINING")
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name, containerInstances=test_instance_ids, status="ACTIVE"
    )
    len(response["failures"]).should.equal(0)
    len(response["containerInstances"]).should.equal(instance_to_create)
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        status.should.equal("ACTIVE")
    ecs_client.update_container_instances_state.when.called_with(
        cluster=test_cluster_name,
        containerInstances=test_instance_ids,
        status="test_status",
    ).should.throw(Exception)


@mock_ec2
@mock_ecs
def test_update_container_instances_state_by_arn():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"
    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    instance_to_create = 3
    test_instance_arns = []
    for i in range(0, instance_to_create):
        test_instance = ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
        )[0]

        instance_id_document = json.dumps(
            ec2_utils.generate_instance_identity_document(test_instance)
        )

        response = ecs_client.register_container_instance(
            cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
        )

        test_instance_arns.append(response["containerInstance"]["containerInstanceArn"])

    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name,
        containerInstances=test_instance_arns,
        status="DRAINING",
    )
    len(response["failures"]).should.equal(0)
    len(response["containerInstances"]).should.equal(instance_to_create)
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        status.should.equal("DRAINING")
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name,
        containerInstances=test_instance_arns,
        status="DRAINING",
    )
    len(response["failures"]).should.equal(0)
    len(response["containerInstances"]).should.equal(instance_to_create)
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        status.should.equal("DRAINING")
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name,
        containerInstances=test_instance_arns,
        status="ACTIVE",
    )
    len(response["failures"]).should.equal(0)
    len(response["containerInstances"]).should.equal(instance_to_create)
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        status.should.equal("ACTIVE")
    ecs_client.update_container_instances_state.when.called_with(
        cluster=test_cluster_name,
        containerInstances=test_instance_arns,
        status="test_status",
    ).should.throw(Exception)


@mock_ec2
@mock_ecs
def test_run_task():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        count=2,
        startedBy="moto",
        tags=[
            {"key": "tagKey0", "value": "tagValue0"},
            {"key": "tagKey1", "value": "tagValue1"},
        ],
    )
    len(response["tasks"]).should.equal(2)
    response["tasks"][0]["taskArn"].should.contain(
        "arn:aws:ecs:us-east-1:{}:task/".format(ACCOUNT_ID)
    )
    response["tasks"][0]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    response["tasks"][0]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    response["tasks"][0]["containerInstanceArn"].should.contain(
        "arn:aws:ecs:us-east-1:{}:container-instance/".format(ACCOUNT_ID)
    )
    response["tasks"][0]["overrides"].should.equal({})
    response["tasks"][0]["lastStatus"].should.equal("RUNNING")
    response["tasks"][0]["desiredStatus"].should.equal("RUNNING")
    response["tasks"][0]["startedBy"].should.equal("moto")
    response["tasks"][0]["stoppedReason"].should.equal("")
    response["tasks"][0]["tags"][0].get("value").should.equal("tagValue0")


@mock_ec2
@mock_ecs
def test_run_task_default_cluster():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "default"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.run_task(
        launchType="FARGATE",
        overrides={},
        taskDefinition="test_ecs_task",
        count=2,
        startedBy="moto",
    )
    len(response["tasks"]).should.equal(2)
    response["tasks"][0]["taskArn"].should.contain(
        "arn:aws:ecs:us-east-1:{}:task/".format(ACCOUNT_ID)
    )
    response["tasks"][0]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/default".format(ACCOUNT_ID)
    )
    response["tasks"][0]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    response["tasks"][0]["containerInstanceArn"].should.contain(
        "arn:aws:ecs:us-east-1:{}:container-instance/".format(ACCOUNT_ID)
    )
    response["tasks"][0]["overrides"].should.equal({})
    response["tasks"][0]["lastStatus"].should.equal("RUNNING")
    response["tasks"][0]["desiredStatus"].should.equal("RUNNING")
    response["tasks"][0]["startedBy"].should.equal("moto")
    response["tasks"][0]["stoppedReason"].should.equal("")


@mock_ecs
def test_run_task_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
            }
        ],
    )

    client.run_task.when.called_with(
        cluster="not_a_cluster", taskDefinition="test_ecs_task"
    ).should.throw(ClientError, ClusterNotFoundException().message)


@mock_ec2
@mock_ecs
def test_start_task():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    container_instances = client.list_container_instances(cluster=test_cluster_name)
    container_instance_id = container_instances["containerInstanceArns"][0].split("/")[
        -1
    ]

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )

    response = client.start_task(
        cluster="test_ecs_cluster",
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="moto",
    )

    len(response["tasks"]).should.equal(1)
    response["tasks"][0]["taskArn"].should.contain(
        "arn:aws:ecs:us-east-1:{}:task/".format(ACCOUNT_ID)
    )
    response["tasks"][0]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    response["tasks"][0]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    response["tasks"][0]["containerInstanceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{0}:container-instance/{1}".format(
            ACCOUNT_ID, container_instance_id
        )
    )
    response["tasks"][0]["overrides"].should.equal({})
    response["tasks"][0]["lastStatus"].should.equal("RUNNING")
    response["tasks"][0]["desiredStatus"].should.equal("RUNNING")
    response["tasks"][0]["startedBy"].should.equal("moto")
    response["tasks"][0]["stoppedReason"].should.equal("")


@mock_ecs
def test_start_task_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
            }
        ],
    )

    client.start_task.when.called_with(
        taskDefinition="test_ecs_task", containerInstances=["not_a_container_instance"]
    ).should.throw(ClientError, ClusterNotFoundException().message)

    _ = client.create_cluster()
    client.start_task.when.called_with(
        taskDefinition="test_ecs_task", containerInstances=[]
    ).should.throw(
        ClientError, InvalidParameterException("Container Instances cannot be empty.")
    )


@mock_ec2
@mock_ecs
def test_list_tasks():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    _ = client.create_cluster()

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    _ = client.register_container_instance(
        instanceIdentityDocument=instance_id_document
    )

    container_instances = client.list_container_instances()
    container_instance_id = container_instances["containerInstanceArns"][0].split("/")[
        -1
    ]

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )

    _ = client.start_task(
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="foo",
    )

    _ = client.start_task(
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="bar",
    )

    assert len(client.list_tasks()["taskArns"]).should.equal(2)
    assert len(client.list_tasks(startedBy="foo")["taskArns"]).should.equal(1)


@mock_ecs
def test_list_tasks_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")
    client.list_tasks.when.called_with(cluster="not_a_cluster").should.throw(
        ClientError, ClusterNotFoundException().message
    )


@mock_ec2
@mock_ecs
def test_describe_tasks():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    tasks_arns = [
        task["taskArn"]
        for task in client.run_task(
            cluster="test_ecs_cluster",
            overrides={},
            taskDefinition="test_ecs_task",
            count=2,
            startedBy="moto",
        )["tasks"]
    ]
    response = client.describe_tasks(cluster="test_ecs_cluster", tasks=tasks_arns)

    len(response["tasks"]).should.equal(2)
    set(
        [response["tasks"][0]["taskArn"], response["tasks"][1]["taskArn"]]
    ).should.equal(set(tasks_arns))

    # Test we can pass task ids instead of ARNs
    response = client.describe_tasks(
        cluster="test_ecs_cluster", tasks=[tasks_arns[0].split("/")[-1]]
    )
    len(response["tasks"]).should.equal(1)


@mock_ecs
def test_describe_tasks_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")

    client.describe_tasks.when.called_with(tasks=[]).should.throw(
        ClientError, ClusterNotFoundException().message
    )

    _ = client.create_cluster()
    client.describe_tasks.when.called_with(tasks=[]).should.throw(
        ClientError, InvalidParameterException("Tasks cannot be empty.").message
    )


@mock_ecs
def test_describe_task_definition_by_family():
    client = boto3.client("ecs", region_name="us-east-1")
    container_definition = {
        "name": "hello_world",
        "image": "docker/hello-world:latest",
        "cpu": 1024,
        "memory": 400,
        "essential": True,
        "environment": [{"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}],
        "logConfiguration": {"logDriver": "json-file"},
    }
    task_definition = client.register_task_definition(
        family="test_ecs_task", containerDefinitions=[container_definition]
    )
    family = task_definition["taskDefinition"]["family"]
    task = client.describe_task_definition(taskDefinition=family)["taskDefinition"]
    task["containerDefinitions"][0].should.equal(
        dict(
            container_definition,
            **{"mountPoints": [], "portMappings": [], "volumesFrom": []}
        )
    )
    task["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    task["volumes"].should.equal([])
    task["status"].should.equal("ACTIVE")


@mock_ec2
@mock_ecs
def test_stop_task():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    _ = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    run_response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        count=1,
        startedBy="moto",
    )
    stop_response = client.stop_task(
        cluster="test_ecs_cluster",
        task=run_response["tasks"][0].get("taskArn"),
        reason="moto testing",
    )

    stop_response["task"]["taskArn"].should.equal(
        run_response["tasks"][0].get("taskArn")
    )
    stop_response["task"]["lastStatus"].should.equal("STOPPED")
    stop_response["task"]["desiredStatus"].should.equal("STOPPED")
    stop_response["task"]["stoppedReason"].should.equal("moto testing")


@mock_ecs
def test_stop_task_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")

    client.stop_task.when.called_with(task="fake_task").should.throw(
        ClientError, ClusterNotFoundException().message
    )


@mock_ec2
@mock_ecs
def test_resource_reservation_and_release():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    _ = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
                "portMappings": [{"hostPort": 80, "containerPort": 8080}],
            }
        ],
    )
    run_response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        count=1,
        startedBy="moto",
    )
    container_instance_arn = run_response["tasks"][0].get("containerInstanceArn")
    container_instance_description = client.describe_container_instances(
        cluster="test_ecs_cluster", containerInstances=[container_instance_arn]
    )["containerInstances"][0]
    remaining_resources, registered_resources = _fetch_container_instance_resources(
        container_instance_description
    )
    remaining_resources["CPU"].should.equal(registered_resources["CPU"] - 1024)
    remaining_resources["MEMORY"].should.equal(registered_resources["MEMORY"] - 400)
    registered_resources["PORTS"].append("80")
    remaining_resources["PORTS"].should.equal(registered_resources["PORTS"])
    container_instance_description["runningTasksCount"].should.equal(1)
    client.stop_task(
        cluster="test_ecs_cluster",
        task=run_response["tasks"][0].get("taskArn"),
        reason="moto testing",
    )
    container_instance_description = client.describe_container_instances(
        cluster="test_ecs_cluster", containerInstances=[container_instance_arn]
    )["containerInstances"][0]
    remaining_resources, registered_resources = _fetch_container_instance_resources(
        container_instance_description
    )
    remaining_resources["CPU"].should.equal(registered_resources["CPU"])
    remaining_resources["MEMORY"].should.equal(registered_resources["MEMORY"])
    remaining_resources["PORTS"].should.equal(registered_resources["PORTS"])
    container_instance_description["runningTasksCount"].should.equal(0)


@mock_ec2
@mock_ecs
def test_resource_reservation_and_release_memory_reservation():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    _ = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "memoryReservation": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
                "portMappings": [{"containerPort": 8080}],
            }
        ],
    )
    run_response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        count=1,
        startedBy="moto",
    )
    container_instance_arn = run_response["tasks"][0].get("containerInstanceArn")
    container_instance_description = client.describe_container_instances(
        cluster="test_ecs_cluster", containerInstances=[container_instance_arn]
    )["containerInstances"][0]
    remaining_resources, registered_resources = _fetch_container_instance_resources(
        container_instance_description
    )
    remaining_resources["CPU"].should.equal(registered_resources["CPU"])
    remaining_resources["MEMORY"].should.equal(registered_resources["MEMORY"] - 400)
    remaining_resources["PORTS"].should.equal(registered_resources["PORTS"])
    container_instance_description["runningTasksCount"].should.equal(1)
    client.stop_task(
        cluster="test_ecs_cluster",
        task=run_response["tasks"][0].get("taskArn"),
        reason="moto testing",
    )
    container_instance_description = client.describe_container_instances(
        cluster="test_ecs_cluster", containerInstances=[container_instance_arn]
    )["containerInstances"][0]
    remaining_resources, registered_resources = _fetch_container_instance_resources(
        container_instance_description
    )
    remaining_resources["CPU"].should.equal(registered_resources["CPU"])
    remaining_resources["MEMORY"].should.equal(registered_resources["MEMORY"])
    remaining_resources["PORTS"].should.equal(registered_resources["PORTS"])
    container_instance_description["runningTasksCount"].should.equal(0)


@mock_ec2
@mock_ecs
def test_task_definitions_unable_to_be_placed():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 5000,
                "memory": 40000,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        count=2,
        startedBy="moto",
    )
    len(response["tasks"]).should.equal(0)


@mock_ec2
@mock_ecs
def test_task_definitions_with_port_clash():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 256,
                "memory": 512,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
                "portMappings": [{"hostPort": 80, "containerPort": 8080}],
            }
        ],
    )
    response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        count=2,
        startedBy="moto",
    )
    len(response["tasks"]).should.equal(1)
    response["tasks"][0]["taskArn"].should.contain(
        "arn:aws:ecs:us-east-1:{}:task/".format(ACCOUNT_ID)
    )
    response["tasks"][0]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    response["tasks"][0]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )
    response["tasks"][0]["containerInstanceArn"].should.contain(
        "arn:aws:ecs:us-east-1:{}:container-instance/".format(ACCOUNT_ID)
    )
    response["tasks"][0]["overrides"].should.equal({})
    response["tasks"][0]["lastStatus"].should.equal("RUNNING")
    response["tasks"][0]["desiredStatus"].should.equal("RUNNING")
    response["tasks"][0]["startedBy"].should.equal("moto")
    response["tasks"][0]["stoppedReason"].should.equal("")


@mock_ec2
@mock_ecs
def test_attributes():
    # Combined put, list delete attributes into the same test due to the amount of setup
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    instances = []
    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]
    instances.append(test_instance)

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    response["containerInstance"]["ec2InstanceId"].should.equal(test_instance.id)
    full_arn1 = response["containerInstance"]["containerInstanceArn"]

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]
    instances.append(test_instance)

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    response["containerInstance"]["ec2InstanceId"].should.equal(test_instance.id)
    full_arn2 = response["containerInstance"]["containerInstanceArn"]
    partial_arn2 = full_arn2.rsplit("/", 1)[-1]

    full_arn2.should_not.equal(
        full_arn1
    )  # uuid1 isnt unique enough when the pc is fast ;-)

    # Ok set instance 1 with 1 attribute, instance 2 with another, and all of them with a 3rd.
    ecs_client.put_attributes(
        cluster=test_cluster_name,
        attributes=[
            {"name": "env", "value": "prod"},
            {"name": "attr1", "value": "instance1", "targetId": full_arn1},
            {
                "name": "attr1",
                "value": "instance2",
                "targetId": partial_arn2,
                "targetType": "container-instance",
            },
        ],
    )

    resp = ecs_client.list_attributes(
        cluster=test_cluster_name, targetType="container-instance"
    )
    attrs = resp["attributes"]

    NUM_CUSTOM_ATTRIBUTES = 4  # 2 specific to individual machines and 1 global, going to both machines (2 + 1*2)
    NUM_DEFAULT_ATTRIBUTES = 4
    len(attrs).should.equal(
        NUM_CUSTOM_ATTRIBUTES + (NUM_DEFAULT_ATTRIBUTES * len(instances))
    )

    # Tests that the attrs have been set properly
    len(list(filter(lambda item: item["name"] == "env", attrs))).should.equal(2)
    len(
        list(
            filter(
                lambda item: item["name"] == "attr1" and item["value"] == "instance1",
                attrs,
            )
        )
    ).should.equal(1)

    ecs_client.delete_attributes(
        cluster=test_cluster_name,
        attributes=[
            {
                "name": "attr1",
                "value": "instance2",
                "targetId": partial_arn2,
                "targetType": "container-instance",
            }
        ],
    )
    NUM_CUSTOM_ATTRIBUTES -= 1

    resp = ecs_client.list_attributes(
        cluster=test_cluster_name, targetType="container-instance"
    )
    attrs = resp["attributes"]
    len(attrs).should.equal(
        NUM_CUSTOM_ATTRIBUTES + (NUM_DEFAULT_ATTRIBUTES * len(instances))
    )


@mock_ecs
def test_poll_endpoint():
    # Combined put, list delete attributes into the same test due to the amount of setup
    ecs_client = boto3.client("ecs", region_name="us-east-1")

    # Just a placeholder until someone actually wants useless data, just testing it doesnt raise an exception
    resp = ecs_client.discover_poll_endpoint(cluster="blah", containerInstance="blah")
    resp.should.contain("endpoint")
    resp.should.contain("telemetryEndpoint")


@mock_ecs
def test_list_task_definition_families():
    client = boto3.client("ecs", region_name="us-east-1")
    client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    client.register_task_definition(
        family="alt_test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )

    resp1 = client.list_task_definition_families()
    resp2 = client.list_task_definition_families(familyPrefix="alt")

    len(resp1["families"]).should.equal(2)
    len(resp2["families"]).should.equal(1)


@mock_ec2
@mock_ecs
def test_default_container_instance_attributes():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    # Create cluster and EC2 instance
    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    # Register container instance
    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    response["containerInstance"]["ec2InstanceId"].should.equal(test_instance.id)
    full_arn = response["containerInstance"]["containerInstanceArn"]
    container_instance_id = full_arn.rsplit("/", 1)[-1]

    default_attributes = response["containerInstance"]["attributes"]
    assert len(default_attributes) == 4
    expected_result = [
        {
            "name": "ecs.availability-zone",
            "value": test_instance.placement["AvailabilityZone"],
        },
        {"name": "ecs.ami-id", "value": test_instance.image_id},
        {"name": "ecs.instance-type", "value": test_instance.instance_type},
        {"name": "ecs.os-type", "value": test_instance.platform or "linux"},
    ]
    assert sorted(default_attributes, key=lambda item: item["name"]) == sorted(
        expected_result, key=lambda item: item["name"]
    )


@mock_ec2
@mock_ecs
def test_describe_container_instances_with_attributes():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    # Create cluster and EC2 instance
    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    # Register container instance
    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    response["containerInstance"]["ec2InstanceId"].should.equal(test_instance.id)
    full_arn = response["containerInstance"]["containerInstanceArn"]
    container_instance_id = full_arn.rsplit("/", 1)[-1]
    default_attributes = response["containerInstance"]["attributes"]

    # Set attributes on container instance, one without a value
    attributes = [
        {"name": "env", "value": "prod"},
        {
            "name": "attr1",
            "value": "instance1",
            "targetId": container_instance_id,
            "targetType": "container-instance",
        },
        {"name": "attr_without_value"},
    ]
    ecs_client.put_attributes(cluster=test_cluster_name, attributes=attributes)

    # Describe container instance, should have attributes previously set
    described_instance = ecs_client.describe_container_instances(
        cluster=test_cluster_name, containerInstances=[container_instance_id]
    )

    assert len(described_instance["containerInstances"]) == 1
    assert isinstance(described_instance["containerInstances"][0]["attributes"], list)

    # Remove additional info passed to put_attributes
    cleaned_attributes = []
    for attribute in attributes:
        attribute.pop("targetId", None)
        attribute.pop("targetType", None)
        cleaned_attributes.append(attribute)
    described_attributes = sorted(
        described_instance["containerInstances"][0]["attributes"],
        key=lambda item: item["name"],
    )
    expected_attributes = sorted(
        default_attributes + cleaned_attributes, key=lambda item: item["name"]
    )
    assert described_attributes == expected_attributes


def _fetch_container_instance_resources(container_instance_description):
    remaining_resources = {}
    registered_resources = {}
    remaining_resources_list = container_instance_description["remainingResources"]
    registered_resources_list = container_instance_description["registeredResources"]
    remaining_resources["CPU"] = [
        x["integerValue"] for x in remaining_resources_list if x["name"] == "CPU"
    ][0]
    remaining_resources["MEMORY"] = [
        x["integerValue"] for x in remaining_resources_list if x["name"] == "MEMORY"
    ][0]
    remaining_resources["PORTS"] = [
        x["stringSetValue"] for x in remaining_resources_list if x["name"] == "PORTS"
    ][0]
    registered_resources["CPU"] = [
        x["integerValue"] for x in registered_resources_list if x["name"] == "CPU"
    ][0]
    registered_resources["MEMORY"] = [
        x["integerValue"] for x in registered_resources_list if x["name"] == "MEMORY"
    ][0]
    registered_resources["PORTS"] = [
        x["stringSetValue"] for x in registered_resources_list if x["name"] == "PORTS"
    ][0]
    return remaining_resources, registered_resources


@mock_ecs
def test_create_service_load_balancing():
    client = boto3.client("ecs", region_name="us-east-1")
    client.create_cluster(clusterName="test_ecs_cluster")
    client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        loadBalancers=[
            {
                "targetGroupArn": "test_target_group_arn",
                "loadBalancerName": "test_load_balancer_name",
                "containerName": "test_container_name",
                "containerPort": 123,
            }
        ],
    )
    response["service"]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:cluster/test_ecs_cluster".format(ACCOUNT_ID)
    )
    response["service"]["desiredCount"].should.equal(2)
    len(response["service"]["events"]).should.equal(0)
    len(response["service"]["loadBalancers"]).should.equal(1)
    response["service"]["loadBalancers"][0]["targetGroupArn"].should.equal(
        "test_target_group_arn"
    )
    response["service"]["loadBalancers"][0]["loadBalancerName"].should.equal(
        "test_load_balancer_name"
    )
    response["service"]["loadBalancers"][0]["containerName"].should.equal(
        "test_container_name"
    )
    response["service"]["loadBalancers"][0]["containerPort"].should.equal(123)
    response["service"]["pendingCount"].should.equal(0)
    response["service"]["runningCount"].should.equal(0)
    response["service"]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:service/test_ecs_service".format(ACCOUNT_ID)
    )
    response["service"]["serviceName"].should.equal("test_ecs_service")
    response["service"]["status"].should.equal("ACTIVE")
    response["service"]["taskDefinition"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )


@mock_ecs
def test_list_tags_for_resource():
    client = boto3.client("ecs", region_name="us-east-1")
    response = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
        tags=[
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "foo", "value": "bar"},
        ],
    )
    type(response["taskDefinition"]).should.be(dict)
    response["taskDefinition"]["revision"].should.equal(1)
    response["taskDefinition"]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:{}:task-definition/test_ecs_task:1".format(ACCOUNT_ID)
    )

    task_definition_arn = response["taskDefinition"]["taskDefinitionArn"]
    response = client.list_tags_for_resource(resourceArn=task_definition_arn)

    type(response["tags"]).should.be(list)
    response["tags"].should.equal(
        [{"key": "createdBy", "value": "moto-unittest"}, {"key": "foo", "value": "bar"}]
    )


@mock_ecs
def test_list_tags_exceptions():
    client = boto3.client("ecs", region_name="us-east-1")
    client.list_tags_for_resource.when.called_with(
        resourceArn="arn:aws:ecs:us-east-1:012345678910:service/fake_service:1"
    ).should.throw(ClientError, ServiceNotFoundException().message)
    client.list_tags_for_resource.when.called_with(
        resourceArn="arn:aws:ecs:us-east-1:012345678910:task-definition/fake_task:1"
    ).should.throw(ClientError, TaskDefinitionNotFoundException().message)


@mock_ecs
def test_list_tags_for_resource_ecs_service():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "foo", "value": "bar"},
        ],
    )
    response = client.list_tags_for_resource(
        resourceArn=response["service"]["serviceArn"]
    )
    type(response["tags"]).should.be(list)
    response["tags"].should.equal(
        [{"key": "createdBy", "value": "moto-unittest"}, {"key": "foo", "value": "bar"}]
    )


@mock_ecs
def test_ecs_service_tag_resource():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    client.tag_resource(
        resourceArn=response["service"]["serviceArn"],
        tags=[
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "foo", "value": "bar"},
        ],
    )
    response = client.list_tags_for_resource(
        resourceArn=response["service"]["serviceArn"]
    )
    type(response["tags"]).should.be(list)
    response["tags"].should.equal(
        [{"key": "createdBy", "value": "moto-unittest"}, {"key": "foo", "value": "bar"}]
    )


@mock_ecs
def test_ecs_service_tag_resource_overwrites_tag():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[{"key": "foo", "value": "bar"}],
    )
    client.tag_resource(
        resourceArn=response["service"]["serviceArn"],
        tags=[
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "foo", "value": "hello world"},
        ],
    )
    response = client.list_tags_for_resource(
        resourceArn=response["service"]["serviceArn"]
    )
    type(response["tags"]).should.be(list)
    response["tags"].should.equal(
        [
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "foo", "value": "hello world"},
        ]
    )


@mock_ecs
def test_ecs_service_untag_resource():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[{"key": "foo", "value": "bar"}],
    )
    client.untag_resource(
        resourceArn=response["service"]["serviceArn"], tagKeys=["foo"]
    )
    response = client.list_tags_for_resource(
        resourceArn=response["service"]["serviceArn"]
    )
    response["tags"].should.equal([])


@mock_ecs
def test_ecs_service_untag_resource_multiple_tags():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName="test_ecs_cluster")
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    response = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[
            {"key": "foo", "value": "bar"},
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "hello", "value": "world"},
        ],
    )
    client.untag_resource(
        resourceArn=response["service"]["serviceArn"], tagKeys=["foo", "createdBy"]
    )
    response = client.list_tags_for_resource(
        resourceArn=response["service"]["serviceArn"]
    )
    response["tags"].should.equal([{"key": "hello", "value": "world"}])


@mock_ecs
def test_ecs_task_definition_placement_constraints():
    client = boto3.client("ecs", region_name="us-east-1")
    response = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
        networkMode="bridge",
        tags=[
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "foo", "value": "bar"},
        ],
        placementConstraints=[
            {"type": "memberOf", "expression": "attribute:ecs.instance-type =~ t2.*"}
        ],
    )
    type(response["taskDefinition"]["placementConstraints"]).should.be(list)
    response["taskDefinition"]["placementConstraints"].should.equal(
        [{"type": "memberOf", "expression": "attribute:ecs.instance-type =~ t2.*"}]
    )


@mock_ecs
def test_create_task_set():
    cluster_name = "test_ecs_cluster"
    service_name = "test_ecs_service"
    task_def_name = "test_ecs_task"

    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=task_def_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )
    load_balancers = [
        {
            "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:01234567890:targetgroup/c26b93c1bc35466ba792d5b08fe6a5bc/ec39113f8831453a",
            "containerName": "hello_world",
            "containerPort": 8080,
        },
    ]

    task_set = client.create_task_set(
        cluster=cluster_name,
        service=service_name,
        taskDefinition=task_def_name,
        loadBalancers=load_balancers,
    )["taskSet"]

    cluster_arn = client.describe_clusters(clusters=[cluster_name])["clusters"][0][
        "clusterArn"
    ]
    service_arn = client.describe_services(
        cluster=cluster_name, services=[service_name]
    )["services"][0]["serviceArn"]
    task_set["clusterArn"].should.equal(cluster_arn)
    task_set["serviceArn"].should.equal(service_arn)
    task_set["taskDefinition"].should.match("{0}:1$".format(task_def_name))
    task_set["scale"].should.equal({"value": 100.0, "unit": "PERCENT"})
    task_set["loadBalancers"][0]["targetGroupArn"].should.equal(
        "arn:aws:elasticloadbalancing:us-east-1:01234567890:targetgroup/"
        "c26b93c1bc35466ba792d5b08fe6a5bc/ec39113f8831453a"
    )
    task_set["loadBalancers"][0]["containerPort"].should.equal(8080)
    task_set["loadBalancers"][0]["containerName"].should.equal("hello_world")
    task_set["launchType"].should.equal("EC2")


@mock_ecs
def test_create_task_set_errors():
    # given
    cluster_name = "test_ecs_cluster"
    service_name = "test_ecs_service"
    task_def_name = "test_ecs_task"

    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=task_def_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )

    # not existing launch type
    # when
    with pytest.raises(ClientError) as e:
        client.create_task_set(
            cluster=cluster_name,
            service=service_name,
            taskDefinition=task_def_name,
            launchType="SOMETHING",
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateTaskSet")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ClientException")
    ex.response["Error"]["Message"].should.equal(
        "launch type should be one of [EC2,FARGATE]"
    )


@mock_ecs
def test_describe_task_sets():
    cluster_name = "test_ecs_cluster"
    service_name = "test_ecs_service"
    task_def_name = "test_ecs_task"

    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    _ = client.register_task_definition(
        family=task_def_name,
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=task_def_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )

    load_balancers = [
        {
            "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:01234567890:targetgroup/c26b93c1bc35466ba792d5b08fe6a5bc/ec39113f8831453a",
            "containerName": "hello_world",
            "containerPort": 8080,
        }
    ]

    _ = client.create_task_set(
        cluster=cluster_name,
        service=service_name,
        taskDefinition=task_def_name,
        loadBalancers=load_balancers,
    )
    task_sets = client.describe_task_sets(cluster=cluster_name, service=service_name)[
        "taskSets"
    ]
    assert "tags" not in task_sets[0]

    task_sets = client.describe_task_sets(
        cluster=cluster_name, service=service_name, include=["TAGS"],
    )["taskSets"]

    cluster_arn = client.describe_clusters(clusters=[cluster_name])["clusters"][0][
        "clusterArn"
    ]

    service_arn = client.describe_services(
        cluster=cluster_name, services=[service_name]
    )["services"][0]["serviceArn"]

    task_sets[0].should.have.key("tags")
    task_sets.should.have.length_of(1)
    task_sets[0]["taskDefinition"].should.match("{0}:1$".format(task_def_name))
    task_sets[0]["clusterArn"].should.equal(cluster_arn)
    task_sets[0]["serviceArn"].should.equal(service_arn)
    task_sets[0]["serviceArn"].should.match("{0}$".format(service_name))
    task_sets[0]["scale"].should.equal({"value": 100.0, "unit": "PERCENT"})
    task_sets[0]["taskSetArn"].should.match("{0}$".format(task_sets[0]["id"]))
    task_sets[0]["loadBalancers"][0]["targetGroupArn"].should.equal(
        "arn:aws:elasticloadbalancing:us-east-1:01234567890:targetgroup/"
        "c26b93c1bc35466ba792d5b08fe6a5bc/ec39113f8831453a"
    )
    task_sets[0]["loadBalancers"][0]["containerPort"].should.equal(8080)
    task_sets[0]["loadBalancers"][0]["containerName"].should.equal("hello_world")
    task_sets[0]["launchType"].should.equal("EC2")


@mock_ecs
def test_delete_task_set():
    cluster_name = "test_ecs_cluster"
    service_name = "test_ecs_service"
    task_def_name = "test_ecs_task"

    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    _ = client.register_task_definition(
        family=task_def_name,
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=task_def_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )

    task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name,
    )["taskSet"]

    task_sets = client.describe_task_sets(
        cluster=cluster_name, service=service_name, taskSets=[task_set["taskSetArn"]],
    )["taskSets"]

    assert len(task_sets) == 1

    response = client.delete_task_set(
        cluster=cluster_name, service=service_name, taskSet=task_set["taskSetArn"],
    )
    assert response["taskSet"]["taskSetArn"] == task_set["taskSetArn"]

    task_sets = client.describe_task_sets(
        cluster=cluster_name, service=service_name, taskSets=[task_set["taskSetArn"]],
    )["taskSets"]

    assert len(task_sets) == 0

    with pytest.raises(ClientError):
        _ = client.delete_task_set(
            cluster=cluster_name, service=service_name, taskSet=task_set["taskSetArn"],
        )


@mock_ecs
def test_update_service_primary_task_set():
    cluster_name = "test_ecs_cluster"
    service_name = "test_ecs_service"
    task_def_name = "test_ecs_task"

    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    _ = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )

    task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name,
    )["taskSet"]

    service = client.describe_services(cluster=cluster_name, services=[service_name],)[
        "services"
    ][0]

    _ = client.update_service_primary_task_set(
        cluster=cluster_name,
        service=service_name,
        primaryTaskSet=task_set["taskSetArn"],
    )

    service = client.describe_services(cluster=cluster_name, services=[service_name],)[
        "services"
    ][0]
    assert service["taskSets"][0]["status"] == "PRIMARY"
    assert service["taskDefinition"] == service["taskSets"][0]["taskDefinition"]

    another_task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name,
    )["taskSet"]
    service = client.describe_services(cluster=cluster_name, services=[service_name],)[
        "services"
    ][0]
    assert service["taskSets"][1]["status"] == "ACTIVE"

    _ = client.update_service_primary_task_set(
        cluster=cluster_name,
        service=service_name,
        primaryTaskSet=another_task_set["taskSetArn"],
    )
    service = client.describe_services(cluster=cluster_name, services=[service_name],)[
        "services"
    ][0]
    assert service["taskSets"][0]["status"] == "ACTIVE"
    assert service["taskSets"][1]["status"] == "PRIMARY"
    assert service["taskDefinition"] == service["taskSets"][1]["taskDefinition"]


@mock_ecs
def test_update_task_set():
    cluster_name = "test_ecs_cluster"
    service_name = "test_ecs_service"
    task_def_name = "test_ecs_task"

    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    _ = client.register_task_definition(
        family=task_def_name,
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )

    task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name,
    )["taskSet"]

    another_task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name,
    )["taskSet"]
    assert another_task_set["scale"]["unit"] == "PERCENT"
    assert another_task_set["scale"]["value"] == 100.0

    client.update_task_set(
        cluster=cluster_name,
        service=service_name,
        taskSet=task_set["taskSetArn"],
        scale={"value": 25.0, "unit": "PERCENT"},
    )

    updated_task_set = client.describe_task_sets(
        cluster=cluster_name, service=service_name, taskSets=[task_set["taskSetArn"]],
    )["taskSets"][0]
    assert updated_task_set["scale"]["value"] == 25.0
    assert updated_task_set["scale"]["unit"] == "PERCENT"


@mock_ec2
@mock_ecs
def test_list_tasks_with_filters():
    ecs = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    _ = ecs.create_cluster(clusterName="test_cluster_1")
    _ = ecs.create_cluster(clusterName="test_cluster_2")

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    _ = ecs.register_container_instance(
        cluster="test_cluster_1", instanceIdentityDocument=instance_id_document
    )
    _ = ecs.register_container_instance(
        cluster="test_cluster_2", instanceIdentityDocument=instance_id_document
    )

    container_instances = ecs.list_container_instances(cluster="test_cluster_1")
    container_id_1 = container_instances["containerInstanceArns"][0].split("/")[-1]
    container_instances = ecs.list_container_instances(cluster="test_cluster_2")
    container_id_2 = container_instances["containerInstanceArns"][0].split("/")[-1]

    test_container_def = {
        "name": "hello_world",
        "image": "docker/hello-world:latest",
        "cpu": 1024,
        "memory": 400,
        "essential": True,
        "environment": [{"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}],
        "logConfiguration": {"logDriver": "json-file"},
    }

    _ = ecs.register_task_definition(
        family="test_task_def_1", containerDefinitions=[test_container_def],
    )

    _ = ecs.register_task_definition(
        family="test_task_def_2", containerDefinitions=[test_container_def],
    )

    _ = ecs.start_task(
        cluster="test_cluster_1",
        taskDefinition="test_task_def_1",
        overrides={},
        containerInstances=[container_id_1],
        startedBy="foo",
    )

    resp = ecs.start_task(
        cluster="test_cluster_2",
        taskDefinition="test_task_def_2",
        overrides={},
        containerInstances=[container_id_2],
        startedBy="foo",
    )
    task_to_stop = resp["tasks"][0]["taskArn"]

    _ = ecs.start_task(
        cluster="test_cluster_1",
        taskDefinition="test_task_def_1",
        overrides={},
        containerInstances=[container_id_1],
        startedBy="bar",
    )

    len(ecs.list_tasks(cluster="test_cluster_1")["taskArns"]).should.equal(2)
    len(ecs.list_tasks(cluster="test_cluster_2")["taskArns"]).should.equal(1)

    len(
        ecs.list_tasks(cluster="test_cluster_1", containerInstance="bad-id")["taskArns"]
    ).should.equal(0)
    len(
        ecs.list_tasks(cluster="test_cluster_1", containerInstance=container_id_1)[
            "taskArns"
        ]
    ).should.equal(2)
    len(
        ecs.list_tasks(cluster="test_cluster_2", containerInstance=container_id_2)[
            "taskArns"
        ]
    ).should.equal(1)

    len(
        ecs.list_tasks(cluster="test_cluster_1", family="non-existent-family")[
            "taskArns"
        ]
    ).should.equal(0)
    len(
        ecs.list_tasks(cluster="test_cluster_1", family="test_task_def_1")["taskArns"]
    ).should.equal(2)
    len(
        ecs.list_tasks(cluster="test_cluster_2", family="test_task_def_2")["taskArns"]
    ).should.equal(1)

    len(
        ecs.list_tasks(cluster="test_cluster_1", startedBy="non-existent-entity")[
            "taskArns"
        ]
    ).should.equal(0)
    len(
        ecs.list_tasks(cluster="test_cluster_1", startedBy="foo")["taskArns"]
    ).should.equal(1)
    len(
        ecs.list_tasks(cluster="test_cluster_1", startedBy="bar")["taskArns"]
    ).should.equal(1)
    len(
        ecs.list_tasks(cluster="test_cluster_2", startedBy="foo")["taskArns"]
    ).should.equal(1)

    len(
        ecs.list_tasks(cluster="test_cluster_1", desiredStatus="RUNNING")["taskArns"]
    ).should.equal(2)
    len(
        ecs.list_tasks(cluster="test_cluster_2", desiredStatus="RUNNING")["taskArns"]
    ).should.equal(1)
    _ = ecs.stop_task(cluster="test_cluster_2", task=task_to_stop, reason="for testing")
    len(
        ecs.list_tasks(cluster="test_cluster_1", desiredStatus="RUNNING")["taskArns"]
    ).should.equal(2)
    len(
        ecs.list_tasks(cluster="test_cluster_2", desiredStatus="STOPPED")["taskArns"]
    ).should.equal(1)

    resp = ecs.list_tasks(cluster="test_cluster_1", startedBy="foo")
    len(resp["taskArns"]).should.equal(1)

    resp = ecs.list_tasks(
        cluster="test_cluster_1", containerInstance=container_id_1, startedBy="bar"
    )
    len(resp["taskArns"]).should.equal(1)
