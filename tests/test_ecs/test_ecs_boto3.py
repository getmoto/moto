from __future__ import unicode_literals
from datetime import datetime

from copy import deepcopy

from botocore.exceptions import ClientError
import boto3
import sure  # noqa
import json
from moto.ec2 import utils as ec2_utils
from uuid import UUID

from moto import mock_cloudformation, mock_elbv2
from moto import mock_ecs
from moto import mock_ec2
from nose.tools import assert_raises


@mock_ecs
def test_create_cluster():
    client = boto3.client("ecs", region_name="us-east-1")
    response = client.create_cluster(clusterName="test_ecs_cluster")
    response["cluster"]["clusterName"].should.equal("test_ecs_cluster")
    response["cluster"]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster"
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
        "arn:aws:ecs:us-east-2:012345678910:cluster/test_cluster0"
    )
    response["clusterArns"].should.contain(
        "arn:aws:ecs:us-east-2:012345678910:cluster/test_cluster1"
    )


@mock_ecs
def test_describe_clusters():
    client = boto3.client("ecs", region_name="us-east-1")
    response = client.describe_clusters(clusters=["some-cluster"])
    response["failures"].should.contain(
        {
            "arn": "arn:aws:ecs:us-east-1:012345678910:cluster/some-cluster",
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
        "arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster"
    )
    response["cluster"]["status"].should.equal("ACTIVE")
    response["cluster"]["registeredContainerInstancesCount"].should.equal(0)
    response["cluster"]["runningTasksCount"].should.equal(0)
    response["cluster"]["pendingTasksCount"].should.equal(0)
    response["cluster"]["activeServicesCount"].should.equal(0)

    response = client.list_clusters()
    len(response["clusterArns"]).should.equal(0)


@mock_ecs
def test_register_task_definition():
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
    )
    type(response["taskDefinition"]).should.be(dict)
    response["taskDefinition"]["revision"].should.equal(1)
    response["taskDefinition"]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
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
    response["taskDefinition"]["networkMode"].should.equal("bridge")


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
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
    )
    response["taskDefinitionArns"][1].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:2"
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
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task_a:1"
    )
    filtered_response["taskDefinitionArns"][1].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task_a:2"
    )


@mock_ecs
def test_describe_task_definition():
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
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:3"
    )

    response = client.describe_task_definition(taskDefinition="test_ecs_task:2")
    response["taskDefinition"]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:2"
    )


@mock_ecs
def test_deregister_task_definition():
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
    response["taskDefinition"]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
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
        "arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster"
    )
    response["service"]["desiredCount"].should.equal(2)
    len(response["service"]["events"]).should.equal(0)
    len(response["service"]["loadBalancers"]).should.equal(0)
    response["service"]["pendingCount"].should.equal(0)
    response["service"]["runningCount"].should.equal(0)
    response["service"]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service"
    )
    response["service"]["serviceName"].should.equal("test_ecs_service")
    response["service"]["status"].should.equal("ACTIVE")
    response["service"]["taskDefinition"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
    )
    response["service"]["schedulingStrategy"].should.equal("REPLICA")


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
        "arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster"
    )
    response["service"]["desiredCount"].should.equal(2)
    len(response["service"]["events"]).should.equal(0)
    len(response["service"]["loadBalancers"]).should.equal(0)
    response["service"]["pendingCount"].should.equal(0)
    response["service"]["runningCount"].should.equal(0)
    response["service"]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service"
    )
    response["service"]["serviceName"].should.equal("test_ecs_service")
    response["service"]["status"].should.equal("ACTIVE")
    response["service"]["taskDefinition"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
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
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service1"
    )
    unfiltered_response["serviceArns"][1].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service2"
    )

    filtered_response = client.list_services(
        cluster="test_ecs_cluster", schedulingStrategy="REPLICA"
    )
    len(filtered_response["serviceArns"]).should.equal(1)
    filtered_response["serviceArns"][0].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service1"
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
            "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service2",
        ],
    )
    len(response["services"]).should.equal(2)
    response["services"][0]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service1"
    )
    response["services"][0]["serviceName"].should.equal("test_ecs_service1")
    response["services"][1]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service2"
    )
    response["services"][1]["serviceName"].should.equal("test_ecs_service2")

    response["services"][0]["deployments"][0]["desiredCount"].should.equal(2)
    response["services"][0]["deployments"][0]["pendingCount"].should.equal(2)
    response["services"][0]["deployments"][0]["runningCount"].should.equal(0)
    response["services"][0]["deployments"][0]["status"].should.equal("PRIMARY")
    (
        datetime.now()
        - response["services"][0]["deployments"][0]["createdAt"].replace(tzinfo=None)
    ).seconds.should.be.within(0, 10)
    (
        datetime.now()
        - response["services"][0]["deployments"][0]["updatedAt"].replace(tzinfo=None)
    ).seconds.should.be.within(0, 10)


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
            "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service2",
            "test_ecs_service3",
        ],
    )
    len(response["services"]).should.equal(3)
    response["services"][0]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service1"
    )
    response["services"][0]["serviceName"].should.equal("test_ecs_service1")
    response["services"][1]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service2"
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
        "arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster"
    )
    response["service"]["desiredCount"].should.equal(0)
    len(response["service"]["events"]).should.equal(0)
    len(response["service"]["loadBalancers"]).should.equal(0)
    response["service"]["pendingCount"].should.equal(0)
    response["service"]["runningCount"].should.equal(0)
    response["service"]["serviceArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service"
    )
    response["service"]["serviceName"].should.equal("test_ecs_service")
    response["service"]["status"].should.equal("ACTIVE")
    response["service"]["schedulingStrategy"].should.equal("REPLICA")
    response["service"]["taskDefinition"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
    )


@mock_ecs
def test_update_non_existent_service():
    client = boto3.client("ecs", region_name="us-east-1")
    try:
        client.update_service(
            cluster="my-clustet", service="my-service", desiredCount=0
        )
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        error_code.should.equal("ServiceNotFoundException")
    else:
        raise Exception("Didn't raise ClientError")


@mock_ec2
@mock_ecs
def test_register_container_instance():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = ecs_client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
    arn_part[0].should.equal("arn:aws:ecs:us-east-1:012345678910:container-instance")
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
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
    with assert_raises(Exception) as e:
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
            ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
            ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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

    with assert_raises(ClientError) as e:
        ecs_client.describe_container_instances(
            cluster=test_cluster_name, containerInstances=[]
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
            ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
            ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
    )
    len(response["tasks"]).should.equal(2)
    response["tasks"][0]["taskArn"].should.contain(
        "arn:aws:ecs:us-east-1:012345678910:task/"
    )
    response["tasks"][0]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster"
    )
    response["tasks"][0]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
    )
    response["tasks"][0]["containerInstanceArn"].should.contain(
        "arn:aws:ecs:us-east-1:012345678910:container-instance/"
    )
    response["tasks"][0]["overrides"].should.equal({})
    response["tasks"][0]["lastStatus"].should.equal("RUNNING")
    response["tasks"][0]["desiredStatus"].should.equal("RUNNING")
    response["tasks"][0]["startedBy"].should.equal("moto")
    response["tasks"][0]["stoppedReason"].should.equal("")


@mock_ec2
@mock_ecs
def test_run_task_default_cluster():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "default"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        "arn:aws:ecs:us-east-1:012345678910:task/"
    )
    response["tasks"][0]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:cluster/default"
    )
    response["tasks"][0]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
    )
    response["tasks"][0]["containerInstanceArn"].should.contain(
        "arn:aws:ecs:us-east-1:012345678910:container-instance/"
    )
    response["tasks"][0]["overrides"].should.equal({})
    response["tasks"][0]["lastStatus"].should.equal("RUNNING")
    response["tasks"][0]["desiredStatus"].should.equal("RUNNING")
    response["tasks"][0]["startedBy"].should.equal("moto")
    response["tasks"][0]["stoppedReason"].should.equal("")


@mock_ec2
@mock_ecs
def test_start_task():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        "arn:aws:ecs:us-east-1:012345678910:task/"
    )
    response["tasks"][0]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster"
    )
    response["tasks"][0]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
    )
    response["tasks"][0]["containerInstanceArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:container-instance/{0}".format(
            container_instance_id
        )
    )
    response["tasks"][0]["overrides"].should.equal({})
    response["tasks"][0]["lastStatus"].should.equal("RUNNING")
    response["tasks"][0]["desiredStatus"].should.equal("RUNNING")
    response["tasks"][0]["startedBy"].should.equal("moto")
    response["tasks"][0]["stoppedReason"].should.equal("")


@mock_ec2
@mock_ecs
def test_list_tasks():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    _ = client.register_container_instance(
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

    _ = client.start_task(
        cluster="test_ecs_cluster",
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="foo",
    )

    _ = client.start_task(
        cluster="test_ecs_cluster",
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="bar",
    )

    assert len(client.list_tasks()["taskArns"]).should.equal(2)
    assert len(client.list_tasks(cluster="test_ecs_cluster")["taskArns"]).should.equal(
        2
    )
    assert len(client.list_tasks(startedBy="foo")["taskArns"]).should.equal(1)


@mock_ec2
@mock_ecs
def test_describe_tasks():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
def describe_task_definition():
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
    family = task_definition["family"]
    task = client.describe_task_definition(taskDefinition=family)
    task["containerDefinitions"][0].should.equal(container_definition)
    task["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task2:1"
    )
    task["volumes"].should.equal([])


@mock_ec2
@mock_ecs
def test_stop_task():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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


@mock_ec2
@mock_ecs
def test_resource_reservation_and_release():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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


@mock_ec2
@mock_ecs
def test_task_definitions_unable_to_be_placed():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    _ = client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        "arn:aws:ecs:us-east-1:012345678910:task/"
    )
    response["tasks"][0]["clusterArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster"
    )
    response["tasks"][0]["taskDefinitionArn"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
    )
    response["tasks"][0]["containerInstanceArn"].should.contain(
        "arn:aws:ecs:us-east-1:012345678910:container-instance/"
    )
    response["tasks"][0]["overrides"].should.equal({})
    response["tasks"][0]["lastStatus"].should.equal("RUNNING")
    response["tasks"][0]["desiredStatus"].should.equal("RUNNING")
    response["tasks"][0]["startedBy"].should.equal("moto")
    response["tasks"][0]["stoppedReason"].should.equal("")


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
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
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
        "arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster"
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
        "arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service"
    )
    response["service"]["serviceName"].should.equal("test_ecs_service")
    response["service"]["status"].should.equal("ACTIVE")
    response["service"]["taskDefinition"].should.equal(
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
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
        "arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1"
    )

    task_definition_arn = response["taskDefinition"]["taskDefinitionArn"]
    response = client.list_tags_for_resource(resourceArn=task_definition_arn)

    type(response["tags"]).should.be(list)
    response["tags"].should.equal(
        [{"key": "createdBy", "value": "moto-unittest"}, {"key": "foo", "value": "bar"}]
    )


@mock_ecs
def test_list_tags_for_resource_unknown():
    client = boto3.client("ecs", region_name="us-east-1")
    task_definition_arn = "arn:aws:ecs:us-east-1:012345678910:task-definition/unknown:1"
    try:
        client.list_tags_for_resource(resourceArn=task_definition_arn)
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ClientException")


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
def test_list_tags_for_resource_unknown_service():
    client = boto3.client("ecs", region_name="us-east-1")
    service_arn = "arn:aws:ecs:us-east-1:012345678910:service/unknown:1"
    try:
        client.list_tags_for_resource(resourceArn=service_arn)
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ServiceNotFoundException")


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
