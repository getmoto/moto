import json
import os
from datetime import datetime
from unittest import SkipTest, mock
from uuid import UUID

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.ec2 import utils as ec2_utils
from moto.moto_api import state_manager
from tests import EXAMPLE_AMI_ID

ECS_REGION = "us-east-1"


@mock_aws
def test_create_cluster():
    client = boto3.client("ecs", region_name=ECS_REGION)
    response = client.create_cluster(clusterName="test_ecs_cluster")
    assert response["cluster"]["clusterName"] == "test_ecs_cluster"
    assert (
        response["cluster"]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert response["cluster"]["status"] == "ACTIVE"
    assert response["cluster"]["registeredContainerInstancesCount"] == 0
    assert response["cluster"]["runningTasksCount"] == 0
    assert response["cluster"]["pendingTasksCount"] == 0
    assert response["cluster"]["activeServicesCount"] == 0


@mock_aws
def test_create_cluster_with_setting():
    client = boto3.client("ecs", region_name=ECS_REGION)
    cluster = client.create_cluster(
        clusterName="test_ecs_cluster",
        settings=[{"name": "containerInsights", "value": "disabled"}],
        serviceConnectDefaults={"namespace": "ns"},
    )["cluster"]
    assert cluster["clusterName"] == "test_ecs_cluster"
    assert cluster["status"] == "ACTIVE"
    assert cluster["settings"] == [{"name": "containerInsights", "value": "disabled"}]
    assert cluster["serviceConnectDefaults"] == {"namespace": "ns"}


@mock_aws
def test_create_cluster_with_capacity_providers():
    client = boto3.client("ecs", region_name=ECS_REGION)
    cluster = client.create_cluster(
        clusterName="test_ecs_cluster",
        capacityProviders=["FARGATE", "FARGATE_SPOT"],
        defaultCapacityProviderStrategy=[
            {"base": 1, "capacityProvider": "FARGATE_SPOT", "weight": 1},
            {"base": 0, "capacityProvider": "FARGATE", "weight": 1},
        ],
    )["cluster"]
    assert cluster["capacityProviders"] == ["FARGATE", "FARGATE_SPOT"]
    assert cluster["defaultCapacityProviderStrategy"] == [
        {"base": 1, "capacityProvider": "FARGATE_SPOT", "weight": 1},
        {"base": 0, "capacityProvider": "FARGATE", "weight": 1},
    ]


@mock_aws
def test_put_capacity_providers():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")
    cluster = client.put_cluster_capacity_providers(
        cluster="test_ecs_cluster",
        capacityProviders=["FARGATE", "FARGATE_SPOT"],
        defaultCapacityProviderStrategy=[
            {"base": 1, "capacityProvider": "FARGATE_SPOT", "weight": 1},
            {"base": 0, "capacityProvider": "FARGATE", "weight": 1},
        ],
    )["cluster"]

    assert cluster["capacityProviders"] == ["FARGATE", "FARGATE_SPOT"]
    assert cluster["defaultCapacityProviderStrategy"] == [
        {"base": 1, "capacityProvider": "FARGATE_SPOT", "weight": 1},
        {"base": 0, "capacityProvider": "FARGATE", "weight": 1},
    ]


@mock_aws
def test_list_clusters():
    client = boto3.client("ecs", region_name="us-east-2")
    client.create_cluster(clusterName="test_cluster0")
    client.create_cluster(clusterName="test_cluster1")
    response = client.list_clusters()
    assert (
        f"arn:aws:ecs:us-east-2:{ACCOUNT_ID}:cluster/test_cluster0"
        in response["clusterArns"]
    )
    assert (
        f"arn:aws:ecs:us-east-2:{ACCOUNT_ID}:cluster/test_cluster1"
        in response["clusterArns"]
    )


@mock_aws
def test_create_cluster_with_tags():
    client = boto3.client("ecs", region_name=ECS_REGION)
    tag_list = [{"key": "tagName", "value": "TagValue"}]
    cluster = client.create_cluster(clusterName="c1")["cluster"]

    resp = client.list_tags_for_resource(resourceArn=cluster["clusterArn"])
    assert "tags" not in resp

    client.tag_resource(resourceArn=cluster["clusterArn"], tags=tag_list)
    tags = client.list_tags_for_resource(resourceArn=cluster["clusterArn"])["tags"]
    assert tags == [{"key": "tagName", "value": "TagValue"}]

    cluster = client.create_cluster(clusterName="c2", tags=tag_list)["cluster"]

    tags = client.list_tags_for_resource(resourceArn=cluster["clusterArn"])["tags"]
    assert tags == [{"key": "tagName", "value": "TagValue"}]


@mock_aws
def test_describe_clusters():
    client = boto3.client("ecs", region_name=ECS_REGION)
    tag_list = [{"key": "tagName", "value": "TagValue"}]
    client.create_cluster(clusterName="c_with_tags", tags=tag_list)
    client.create_cluster(clusterName="c_without")
    clusters = client.describe_clusters(clusters=["c_with_tags"], include=["TAGS"])[
        "clusters"
    ]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["clusterName"] == "c_with_tags"
    assert cluster["tags"] == tag_list

    clusters = client.describe_clusters(clusters=["c_without"], include=["TAGS"])[
        "clusters"
    ]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["clusterName"] == "c_without"
    assert "tags" not in cluster

    clusters = client.describe_clusters(clusters=["c_with_tags", "c_without"])[
        "clusters"
    ]
    assert len(clusters) == 2
    assert "tags" not in clusters[0]
    assert "tags" not in clusters[1]


@mock_aws
def test_describe_clusters_missing():
    client = boto3.client("ecs", region_name=ECS_REGION)
    response = client.describe_clusters(clusters=["some-cluster"])
    assert {
        "arn": f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/some-cluster",
        "reason": "MISSING",
    } in response["failures"]


@mock_aws
def test_delete_cluster():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")
    response = client.delete_cluster(cluster="test_ecs_cluster")
    assert response["cluster"]["clusterName"] == "test_ecs_cluster"
    assert (
        response["cluster"]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert response["cluster"]["status"] == "INACTIVE"
    assert response["cluster"]["registeredContainerInstancesCount"] == 0
    assert response["cluster"]["runningTasksCount"] == 0
    assert response["cluster"]["pendingTasksCount"] == 0
    assert response["cluster"]["activeServicesCount"] == 0

    response = client.list_clusters()
    assert len(response["clusterArns"]) == 1


@mock_aws
def test_delete_cluster_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)
    with pytest.raises(ClientError) as exc:
        client.delete_cluster(cluster="not_a_cluster")
    assert exc.value.response["Error"]["Code"] == "ClusterNotFoundException"


@mock_aws
def test_register_task_definition():
    client = boto3.client("ecs", region_name=ECS_REGION)
    # Registering with minimal definition
    definition = dict(
        family="test_ecs_task",
        containerDefinitions=[
            {"name": "hello_world", "image": "hello-world:latest", "memory": 400}
        ],
    )

    response = client.register_task_definition(**definition)

    response["taskDefinition"] = response["taskDefinition"]
    assert response["taskDefinition"]["family"] == "test_ecs_task"
    assert response["taskDefinition"]["revision"] == 1
    assert (
        response["taskDefinition"]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert response["taskDefinition"]["networkMode"] == "bridge"
    assert response["taskDefinition"]["volumes"] == []
    assert response["taskDefinition"]["placementConstraints"] == []
    assert response["taskDefinition"]["compatibilities"] == ["EC2"]
    assert "requiresCompatibilities" not in response["taskDefinition"]
    assert "cpu" not in response["taskDefinition"]
    assert "memory" not in response["taskDefinition"]

    cntr_def = response["taskDefinition"]["containerDefinitions"][0]
    assert cntr_def["name"] == "hello_world"
    assert cntr_def["image"] == "hello-world:latest"
    assert cntr_def["cpu"] == 0
    assert cntr_def["portMappings"] == []
    assert cntr_def["essential"] is True
    assert cntr_def["environment"] == []
    assert cntr_def["mountPoints"] == []
    assert cntr_def["volumesFrom"] == []

    # Registering again increments the revision
    response = client.register_task_definition(**definition)

    assert response["taskDefinition"]["revision"] == 2
    assert (
        response["taskDefinition"]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:2"
    )

    # Registering with optional top-level params
    definition["requiresCompatibilities"] = ["FARGATE"]
    definition["taskRoleArn"] = "my-custom-task-role-arn"
    definition["executionRoleArn"] = "my-custom-execution-role-arn"
    response = client.register_task_definition(**definition)
    assert response["taskDefinition"]["requiresCompatibilities"] == ["FARGATE"]
    assert response["taskDefinition"]["compatibilities"] == ["EC2", "FARGATE"]
    assert response["taskDefinition"]["networkMode"] == "awsvpc"
    assert response["taskDefinition"]["taskRoleArn"] == "my-custom-task-role-arn"
    assert (
        response["taskDefinition"]["executionRoleArn"] == "my-custom-execution-role-arn"
    )

    definition["requiresCompatibilities"] = ["EC2", "FARGATE"]
    response = client.register_task_definition(**definition)
    assert response["taskDefinition"]["requiresCompatibilities"] == ["EC2", "FARGATE"]
    assert response["taskDefinition"]["compatibilities"] == ["EC2", "FARGATE"]
    assert response["taskDefinition"]["networkMode"] == "awsvpc"

    definition["cpu"] = "512"
    response = client.register_task_definition(**definition)
    assert response["taskDefinition"]["cpu"] == "512"

    definition.update({"memory": "512"})
    response = client.register_task_definition(**definition)
    assert response["taskDefinition"]["memory"] == "512"

    # Registering with optional container params
    definition["containerDefinitions"][0]["cpu"] = 512
    response = client.register_task_definition(**definition)
    assert response["taskDefinition"]["containerDefinitions"][0]["cpu"] == 512

    definition["containerDefinitions"][0]["essential"] = False
    response = client.register_task_definition(**definition)
    assert response["taskDefinition"]["containerDefinitions"][0]["essential"] is False

    definition["containerDefinitions"][0]["environment"] = [
        {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
    ]
    response = client.register_task_definition(**definition)
    assert (
        response["taskDefinition"]["containerDefinitions"][0]["environment"][0]["name"]
        == "AWS_ACCESS_KEY_ID"
    )
    assert (
        response["taskDefinition"]["containerDefinitions"][0]["environment"][0]["value"]
        == "SOME_ACCESS_KEY"
    )

    definition["containerDefinitions"][0]["logConfiguration"] = {
        "logDriver": "json-file"
    }
    response = client.register_task_definition(**definition)
    assert (
        response["taskDefinition"]["containerDefinitions"][0]["logConfiguration"][
            "logDriver"
        ]
        == "json-file"
    )


@mock_aws
def test_register_task_definition_fargate_with_pid_mode():
    client = boto3.client("ecs", region_name=ECS_REGION)
    definition = dict(
        family="test_ecs_task",
        containerDefinitions=[
            {"name": "hello_world", "image": "hello-world:latest", "memory": 400}
        ],
        requiresCompatibilities=["FARGATE"],
        pidMode="host",
        networkMode="awsvpc",
        cpu="256",
        memory="512",
    )

    with pytest.raises(ClientError) as exc:
        client.register_task_definition(**definition)
    ex = exc.value
    assert ex.operation_name == "RegisterTaskDefinition"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ClientException"
    assert (
        ex.response["Error"]["Message"]
        == "Tasks using the Fargate launch type do not support pidMode 'host'. The supported value for pidMode is 'task'."
    )


@mock_aws
def test_register_task_definition_memory_validation_ec2():
    client = boto3.client("ecs", region_name=ECS_REGION)
    container_name = "hello_world"
    bad_definition1 = dict(
        family="test_ecs_task",
        containerDefinitions=[
            {"name": container_name, "image": "hello-world:latest"},
            {"name": f"{container_name}2", "image": "hello-world:latest"},
        ],
        requiresCompatibilities=["EC2"],
    )

    with pytest.raises(ClientError) as exc:
        client.register_task_definition(**bad_definition1)
    ex = exc.value
    assert ex.operation_name == "RegisterTaskDefinition"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ClientException"
    assert (
        ex.response["Error"]["Message"]
        == f"Invalid setting for container '{container_name}'. At least one of 'memory' or 'memoryReservation' must be specified."
    )


@mock_aws
def test_register_task_definition_memory_validation_fargate():
    client = boto3.client("ecs", region_name=ECS_REGION)
    container_name = "hello_world"
    good_definition1 = dict(
        family="test_ecs_task",
        memory="1024",
        containerDefinitions=[
            {"name": container_name, "image": "hello-world:latest"},
            {"name": f"{container_name}2", "image": "hello-world:latest"},
        ],
        requiresCompatibilities=["FARGATE"],
    )

    response = client.register_task_definition(**good_definition1)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
@pytest.mark.parametrize(
    "ecs_def,missing_prop",
    [({"image": "hello-world:latest"}, "name"), ({"name": "test-name"}, "image")],
)
def test_register_task_definition_container_definition_validation(
    ecs_def, missing_prop
):
    client = boto3.client("ecs", region_name=ECS_REGION)
    bad_definition1 = dict(
        family="test_ecs_task",
        memory="400",
        containerDefinitions=[ecs_def],
        requiresCompatibilities=["FARGATE"],
    )

    with pytest.raises(ClientError) as exc:
        client.register_task_definition(**bad_definition1)
    ex = exc.value
    assert ex.operation_name == "RegisterTaskDefinition"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ClientException"
    assert (
        ex.response["Error"]["Message"]
        == f"Container.{missing_prop} should not be null or empty."
    )


@mock_aws
def test_list_task_definitions():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
    assert len(response["taskDefinitionArns"]) == 2
    assert (
        response["taskDefinitionArns"][0]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert (
        response["taskDefinitionArns"][1]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:2"
    )


@mock_aws
def test_list_task_definitions_with_family_prefix():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.register_task_definition(
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
    client.register_task_definition(
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
    client.register_task_definition(
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
    assert len(empty_response["taskDefinitionArns"]) == 0
    filtered_response = client.list_task_definitions(familyPrefix="test_ecs_task_a")
    assert len(filtered_response["taskDefinitionArns"]) == 2
    assert (
        filtered_response["taskDefinitionArns"][0]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task_a:1"
    )
    assert (
        filtered_response["taskDefinitionArns"][1]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task_a:2"
    )


@mock_aws
def test_describe_task_definitions():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
    client.register_task_definition(
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
    assert (
        response["taskDefinition"]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:3"
    )

    response = client.describe_task_definition(taskDefinition="test_ecs_task:2")
    assert (
        response["taskDefinition"]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:2"
    )
    assert response["taskDefinition"]["taskRoleArn"] == "my-task-role-arn"
    assert response["taskDefinition"]["executionRoleArn"] == "my-execution-role-arn"


@mock_aws
def test_deregister_task_definition_1():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
    response = client.deregister_task_definition(taskDefinition="test_ecs_task:1")
    assert response["taskDefinition"]["status"] == "INACTIVE"
    assert (
        response["taskDefinition"]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert (
        response["taskDefinition"]["containerDefinitions"][0]["name"] == "hello_world"
    )
    assert (
        response["taskDefinition"]["containerDefinitions"][0]["image"]
        == "docker/hello-world:latest"
    )
    assert response["taskDefinition"]["containerDefinitions"][0]["cpu"] == 1024
    assert response["taskDefinition"]["containerDefinitions"][0]["memory"] == 400
    assert response["taskDefinition"]["containerDefinitions"][0]["essential"] is True
    assert (
        response["taskDefinition"]["containerDefinitions"][0]["environment"][0]["name"]
        == "AWS_ACCESS_KEY_ID"
    )
    assert (
        response["taskDefinition"]["containerDefinitions"][0]["environment"][0]["value"]
        == "SOME_ACCESS_KEY"
    )
    assert (
        response["taskDefinition"]["containerDefinitions"][0]["logConfiguration"][
            "logDriver"
        ]
        == "json-file"
    )


@mock_aws
def test_deregister_task_definition_2():
    client = boto3.client("ecs", region_name=ECS_REGION)
    with pytest.raises(ClientError) as exc:
        client.deregister_task_definition(taskDefinition="fake_task")
    assert exc.value.response["Error"]["Message"] == "Revision is missing."

    with pytest.raises(ClientError) as exc:
        client.deregister_task_definition(taskDefinition="fake_task:foo")
    assert (
        exc.value.response["Error"]["Message"] == "Invalid revision number. Number: foo"
    )

    with pytest.raises(ClientError) as exc:
        client.deregister_task_definition(taskDefinition="fake_task:1")
    assert (
        exc.value.response["Error"]["Message"] == "Unable to describe task definition."
    )


@mock_aws
def test_create_service():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
        platformVersion="2",
    )
    assert (
        response["service"]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert response["service"]["desiredCount"] == 2
    assert len(response["service"]["events"]) == 0
    assert len(response["service"]["loadBalancers"]) == 0
    assert response["service"]["pendingCount"] == 2
    assert response["service"]["runningCount"] == 0
    assert (
        response["service"]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service"
    )
    assert response["service"]["serviceName"] == "test_ecs_service"
    assert response["service"]["status"] == "ACTIVE"
    assert (
        response["service"]["taskDefinition"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert response["service"]["schedulingStrategy"] == "REPLICA"
    assert response["service"]["launchType"] == "EC2"
    assert response["service"]["platformVersion"] == "2"


@mock_aws
def test_create_running_service():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Can't set environment variables in server mode for a single test"
        )
    running_service_count = 3
    with mock.patch.dict(
        os.environ, {"MOTO_ECS_SERVICE_RUNNING": str(running_service_count)}
    ):
        client = boto3.client("ecs", region_name=ECS_REGION)
        ec2 = boto3.resource("ec2", region_name=ECS_REGION)
        setup_ecs(client, ec2)

        response = client.create_service(
            cluster="test_ecs_cluster",
            serviceName="test_ecs_service",
            taskDefinition="test_ecs_task",
            desiredCount=4,
            platformVersion="2",
        )

        assert response["service"]["runningCount"] == running_service_count
        assert response["service"]["pendingCount"] == 1


@mock_aws
def test_create_running_service_bad_env_var():
    running_service_count = "ALSDHLHA;''"
    with mock.patch.dict(
        os.environ, {"MOTO_ECS_SERVICE_RUNNING": str(running_service_count)}
    ):
        client = boto3.client("ecs", region_name=ECS_REGION)
        ec2 = boto3.resource("ec2", region_name=ECS_REGION)
        setup_ecs(client, ec2)

        response = client.create_service(
            cluster="test_ecs_cluster",
            serviceName="test_ecs_service",
            taskDefinition="test_ecs_task",
            desiredCount=2,
            platformVersion="2",
        )

        assert response["service"]["runningCount"] == 0


@mock_aws
def test_create_running_service_negative_env_var():
    running_service_count = "-20"
    with mock.patch.dict(
        os.environ, {"MOTO_ECS_SERVICE_RUNNING": str(running_service_count)}
    ):
        client = boto3.client("ecs", region_name=ECS_REGION)
        ec2 = boto3.resource("ec2", region_name=ECS_REGION)
        setup_ecs(client, ec2)

        response = client.create_service(
            cluster="test_ecs_cluster",
            serviceName="test_ecs_service",
            taskDefinition="test_ecs_task",
            desiredCount=2,
            platformVersion="2",
        )

        assert response["service"]["runningCount"] == 0


@mock_aws
def test_create_service_errors():
    # given
    client = boto3.client("ecs", region_name=ECS_REGION)
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
    assert ex.operation_name == "CreateService"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "ClientException" in ex.response["Error"]["Code"]
    assert (
        ex.response["Error"]["Message"] == "launch type should be one of [EC2,FARGATE]"
    )


@mock_aws
def test_create_service_scheduling_strategy():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
        schedulingStrategy="DAEMON",
    )
    assert (
        response["service"]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert response["service"]["desiredCount"] == 2
    assert len(response["service"]["events"]) == 0
    assert len(response["service"]["loadBalancers"]) == 0
    assert response["service"]["pendingCount"] == 2
    assert response["service"]["runningCount"] == 0
    assert (
        response["service"]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service"
    )
    assert response["service"]["serviceName"] == "test_ecs_service"
    assert response["service"]["status"] == "ACTIVE"
    assert (
        response["service"]["taskDefinition"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert response["service"]["schedulingStrategy"] == "DAEMON"


@mock_aws
def test_list_services():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster1")
    client.create_cluster(clusterName="test_ecs_cluster2")
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
    client.create_service(
        cluster="test_ecs_cluster1",
        serviceName="test_ecs_service1",
        taskDefinition="test_ecs_task",
        schedulingStrategy="REPLICA",
        launchType="EC2",
        desiredCount=2,
    )
    client.create_service(
        cluster="test_ecs_cluster1",
        serviceName="test_ecs_service2",
        taskDefinition="test_ecs_task",
        schedulingStrategy="DAEMON",
        launchType="FARGATE",
        desiredCount=2,
    )
    client.create_service(
        cluster="test_ecs_cluster2",
        serviceName="test_ecs_service3",
        taskDefinition="test_ecs_task",
        schedulingStrategy="REPLICA",
        launchType="FARGATE",
        desiredCount=2,
    )

    test_ecs_service1_arn = f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster1/test_ecs_service1"
    test_ecs_service2_arn = f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster1/test_ecs_service2"

    cluster1_services = client.list_services(cluster="test_ecs_cluster1")
    assert len(cluster1_services["serviceArns"]) == 2
    assert cluster1_services["serviceArns"][0] == test_ecs_service1_arn
    assert cluster1_services["serviceArns"][1] == test_ecs_service2_arn

    cluster1_replica_services = client.list_services(
        cluster="test_ecs_cluster1", schedulingStrategy="REPLICA"
    )
    assert len(cluster1_replica_services["serviceArns"]) == 1
    assert cluster1_replica_services["serviceArns"][0] == test_ecs_service1_arn

    cluster1_fargate_services = client.list_services(
        cluster="test_ecs_cluster1", launchType="FARGATE"
    )
    assert len(cluster1_fargate_services["serviceArns"]) == 1
    assert cluster1_fargate_services["serviceArns"][0] == test_ecs_service2_arn


@mock_aws
@pytest.mark.parametrize("args", [{}, {"cluster": "foo"}], ids=["no args", "unknown"])
def test_list_unknown_service(args):
    client = boto3.client("ecs", region_name=ECS_REGION)
    with pytest.raises(ClientError) as exc:
        client.list_services(**args)
    err = exc.value.response["Error"]
    assert err["Code"] == "ClusterNotFoundException"
    assert err["Message"] == "Cluster not found."


@mock_aws
def test_describe_services():
    client = boto3.client("ecs", region_name=ECS_REGION)
    cluster_arn = client.create_cluster(clusterName="test_ecs_cluster")["cluster"][
        "clusterArn"
    ]
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
    client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service1",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[{"key": "Name", "value": "test_ecs_service1"}],
    )
    client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service2",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service3",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )

    # Verify we can describe services using the cluster ARN
    resp = client.describe_services(cluster=cluster_arn, services=["test_ecs_service1"])
    assert len(resp["services"]) == 1

    # Verify we can describe services using both names and ARN's
    response = client.describe_services(
        cluster="test_ecs_cluster",
        services=[
            "test_ecs_service1",
            f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service2",
        ],
    )
    assert len(response["services"]) == 2
    assert (
        response["services"][0]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service1"
    )
    assert response["services"][0]["serviceName"] == "test_ecs_service1"
    assert (
        response["services"][1]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service2"
    )
    assert response["services"][1]["serviceName"] == "test_ecs_service2"

    deployment = response["services"][0]["deployments"][0]
    assert deployment["desiredCount"] == 2
    assert deployment["pendingCount"] == 2
    assert deployment["runningCount"] == 0
    assert deployment["status"] == "PRIMARY"
    assert deployment["launchType"] == "EC2"
    assert (datetime.now() - deployment["createdAt"].replace(tzinfo=None)).seconds < 10
    assert (datetime.now() - deployment["updatedAt"].replace(tzinfo=None)).seconds < 10
    response = client.describe_services(
        cluster="test_ecs_cluster",
        services=[
            "test_ecs_service1",
            f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service2",
        ],
        include=["TAGS"],
    )
    assert response["services"][0]["tags"] == [
        {"key": "Name", "value": "test_ecs_service1"}
    ]
    assert response["services"][1]["tags"] == []
    assert response["services"][0]["launchType"] == "EC2"
    assert response["services"][1]["launchType"] == "EC2"


@mock_aws
@mock.patch.dict(os.environ, {"MOTO_ECS_NEW_ARN": "TrUe"})
def test_describe_services_new_arn():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Can't set environment variables in server mode for a single test"
        )
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")
    client.register_task_definition(
        family="test_ecs_task",
        memory="400",
        containerDefinitions=[
            {"name": "hello_world", "image": "docker/hello-world:latest"}
        ],
    )
    client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service1",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[{"key": "Name", "value": "test_ecs_service1"}],
    )
    response = client.describe_services(
        cluster="test_ecs_cluster", services=["test_ecs_service1"]
    )
    assert (
        response["services"][0]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service1"
    )


@mock_aws
def test_describe_services_scheduling_strategy():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
    client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service1",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service2",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        schedulingStrategy="DAEMON",
    )
    client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service3",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    response = client.describe_services(
        cluster="test_ecs_cluster",
        services=[
            "test_ecs_service1",
            f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service2",
            "test_ecs_service3",
        ],
    )
    assert len(response["services"]) == 3
    assert (
        response["services"][0]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service1"
    )
    assert response["services"][0]["serviceName"] == "test_ecs_service1"
    assert (
        response["services"][1]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service2"
    )
    assert response["services"][1]["serviceName"] == "test_ecs_service2"

    assert response["services"][0]["deployments"][0]["desiredCount"] == 2
    assert response["services"][0]["deployments"][0]["pendingCount"] == 2
    assert response["services"][0]["deployments"][0]["runningCount"] == 0
    assert response["services"][0]["deployments"][0]["status"] == "PRIMARY"

    assert response["services"][0]["schedulingStrategy"] == "REPLICA"
    assert response["services"][1]["schedulingStrategy"] == "DAEMON"
    assert response["services"][2]["schedulingStrategy"] == "REPLICA"


@mock_aws
def test_describe_services_error_unknown_cluster():
    # given
    client = boto3.client("ecs", region_name="eu-central-1")
    cluster_name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.describe_services(cluster=cluster_name, services=["test"])

    # then
    ex = e.value
    assert ex.operation_name == "DescribeServices"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ClusterNotFoundException"
    assert ex.response["Error"]["Message"] == "Cluster not found."


@mock_aws
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
            f"arn:aws:ecs:eu-central-1:{ACCOUNT_ID}:service/unknown-2",
        ],
    )

    # then
    services = response["services"]
    assert [service["serviceArn"] for service in services] == [service_arn, service_arn]

    failures = response["failures"]
    assert sorted(failures, key=lambda item: item["arn"]) == [
        {
            "arn": f"arn:aws:ecs:eu-central-1:{ACCOUNT_ID}:service/unknown",
            "reason": "MISSING",
        },
        {
            "arn": f"arn:aws:ecs:eu-central-1:{ACCOUNT_ID}:service/unknown-2",
            "reason": "MISSING",
        },
    ]


@mock_aws
def test_update_service():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
    )
    assert response["service"]["desiredCount"] == 2

    response = client.update_service(
        cluster="test_ecs_cluster",
        service="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=0,
    )
    assert response["service"]["desiredCount"] == 0
    assert response["service"]["schedulingStrategy"] == "REPLICA"

    # Verify we can pass the ARNs of the cluster and service
    response = client.update_service(
        cluster=response["service"]["clusterArn"],
        service=response["service"]["serviceArn"],
        taskDefinition="test_ecs_task",
        desiredCount=1,
    )
    assert response["service"]["desiredCount"] == 1


@mock_aws
def test_update_missing_service():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")

    with pytest.raises(ClientError):
        client.update_service(
            cluster="test_ecs_cluster",
            service="test_ecs_service",
            taskDefinition="test_ecs_task",
            desiredCount=0,
        )


@mock_aws
def test_delete_service():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
    client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    client.update_service(
        cluster="test_ecs_cluster", service="test_ecs_service", desiredCount=0
    )
    response = client.delete_service(
        cluster="test_ecs_cluster", service="test_ecs_service"
    )
    assert (
        response["service"]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert response["service"]["desiredCount"] == 0
    assert len(response["service"]["events"]) == 0
    assert len(response["service"]["loadBalancers"]) == 0
    assert response["service"]["pendingCount"] == 0
    assert response["service"]["runningCount"] == 0
    assert (
        response["service"]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service"
    )
    assert response["service"]["serviceName"] == "test_ecs_service"
    assert response["service"]["status"] == "INACTIVE"
    assert response["service"]["schedulingStrategy"] == "REPLICA"
    assert (
        response["service"]["taskDefinition"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )

    # service should still exist, just in the INACTIVE state
    service = client.describe_services(
        cluster="test_ecs_cluster", services=["test_ecs_service"]
    )["services"][0]
    assert service["status"] == "INACTIVE"


@mock_aws
def test_delete_service__using_arns():
    client = boto3.client("ecs", region_name=ECS_REGION)
    cluster_arn = client.create_cluster(clusterName="test_ecs_cluster")["cluster"][
        "clusterArn"
    ]
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
    service_arn = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )["service"]["serviceArn"]
    client.update_service(
        cluster="test_ecs_cluster", service="test_ecs_service", desiredCount=0
    )
    response = client.delete_service(cluster=cluster_arn, service=service_arn)
    assert (
        response["service"]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )


@mock_aws
def test_delete_service_force():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
    client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )
    response = client.delete_service(
        cluster="test_ecs_cluster", service="test_ecs_service", force=True
    )
    assert (
        response["service"]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert len(response["service"]["events"]) == 0
    assert len(response["service"]["loadBalancers"]) == 0
    assert response["service"]["pendingCount"] == 0
    assert response["service"]["runningCount"] == 0
    assert (
        response["service"]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service"
    )
    assert response["service"]["serviceName"] == "test_ecs_service"
    assert response["service"]["status"] == "INACTIVE"
    assert response["service"]["schedulingStrategy"] == "REPLICA"
    assert (
        response["service"]["taskDefinition"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )


@mock_aws
def test_delete_service_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)

    # Raises ClusterNotFoundException because "default" is not a cluster
    with pytest.raises(ClientError) as exc:
        client.delete_service(service="not_as_service")
    assert exc.value.response["Error"]["Code"] == "ClusterNotFoundException"

    client.create_cluster()
    with pytest.raises(ClientError) as exc:
        client.delete_service(service="not_as_service")
    assert "ServiceNotFoundException" in exc.value.response["Error"]["Message"]

    client.register_task_definition(
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

    client.create_service(
        serviceName="test_ecs_service", taskDefinition="test_ecs_task", desiredCount=1
    )

    with pytest.raises(ClientError) as exc:
        client.delete_service(service="test_ecs_service")
    assert (
        exc.value.response["Error"]["Message"]
        == "The service cannot be stopped while it is scaled above 0."
    )


@mock_aws
def test_update_service_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)

    with pytest.raises(ClientError) as exc:
        client.update_service(service="not_a_service", desiredCount=0)
    assert exc.value.response["Error"]["Code"] == "ClusterNotFoundException"

    client.create_cluster()

    with pytest.raises(ClientError) as exc:
        client.update_service(service="not_a_service", desiredCount=0)
    assert "ServiceNotFoundException" in exc.value.response["Error"]["Message"]


@mock_aws
def test_register_container_instance():
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    ecs_client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    assert response["containerInstance"]["ec2InstanceId"] == test_instance.id
    full_arn = response["containerInstance"]["containerInstanceArn"]
    arn_part = full_arn.split("/")
    assert arn_part[0] == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance"
    assert arn_part[1] == "test_ecs_cluster"
    assert arn_part[2] == str(UUID(arn_part[2]))
    assert response["containerInstance"]["status"] == "ACTIVE"
    assert len(response["containerInstance"]["registeredResources"]) == 4
    assert len(response["containerInstance"]["remainingResources"]) == 4
    assert response["containerInstance"]["agentConnected"] is True
    assert response["containerInstance"]["versionInfo"]["agentVersion"] == "1.0.0"
    assert response["containerInstance"]["versionInfo"]["agentHash"] == "4023248"
    assert (
        response["containerInstance"]["versionInfo"]["dockerVersion"]
        == "DockerVersion: 1.5.0"
    )


@mock_aws
@mock.patch.dict(os.environ, {"MOTO_ECS_NEW_ARN": "TrUe"})
def test_register_container_instance_new_arn_format():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Can't set environment variables in server mode for a single test"
        )
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    ecs_client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    full_arn = response["containerInstance"]["containerInstanceArn"]
    assert full_arn.startswith(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance/{test_cluster_name}/"
    )


@mock_aws
def test_deregister_container_instance():
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    ecs_client.create_cluster(clusterName=test_cluster_name)

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
    ecs_client.deregister_container_instance(
        cluster=test_cluster_name, containerInstance=container_instance_id
    )
    container_instances_response = ecs_client.list_container_instances(
        cluster=test_cluster_name
    )
    assert len(container_instances_response["containerInstanceArns"]) == 0

    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )
    container_instance_id = response["containerInstance"]["containerInstanceArn"]
    ecs_client.register_task_definition(
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

    ecs_client.start_task(
        cluster="test_ecs_cluster",
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="moto",
    )
    with pytest.raises(ClientError) as exc:
        ecs_client.deregister_container_instance(
            cluster=test_cluster_name, containerInstance=container_instance_id
        )
    err = exc.value.response["Error"]
    assert err["Message"] == "Found running tasks on the instance."

    container_instances_response = ecs_client.list_container_instances(
        cluster=test_cluster_name
    )
    assert len(container_instances_response["containerInstanceArns"]) == 1
    ecs_client.deregister_container_instance(
        cluster=test_cluster_name, containerInstance=container_instance_id, force=True
    )
    container_instances_response = ecs_client.list_container_instances(
        cluster=test_cluster_name
    )
    assert len(container_instances_response["containerInstanceArns"]) == 0


@mock_aws
def test_list_container_instances():
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"
    ecs_client.create_cluster(clusterName=test_cluster_name)

    instance_to_create = 3
    test_instance_arns = []
    for _ in range(0, instance_to_create):
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

    assert len(response["containerInstanceArns"]) == instance_to_create
    for arn in test_instance_arns:
        assert arn in response["containerInstanceArns"]


@mock_aws
def test_describe_container_instances():
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"
    ecs_client.create_cluster(clusterName=test_cluster_name)

    instance_to_create = 3
    test_instance_arns = []
    for _ in range(0, instance_to_create):
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

    test_instance_ids = list(map((lambda x: x.split("/")[-1]), test_instance_arns))
    response = ecs_client.describe_container_instances(
        cluster=test_cluster_name, containerInstances=test_instance_ids
    )
    assert len(response["failures"]) == 0
    assert len(response["containerInstances"]) == instance_to_create
    response_arns = [
        ci["containerInstanceArn"] for ci in response["containerInstances"]
    ]
    for arn in test_instance_arns:
        assert arn in response_arns
    for instance in response["containerInstances"]:
        assert "runningTasksCount" in instance.keys()
        assert "pendingTasksCount" in instance.keys()
        assert isinstance(instance["registeredAt"], datetime)

    with pytest.raises(ClientError) as e:
        ecs_client.describe_container_instances(
            cluster=test_cluster_name, containerInstances=[]
        )
    err = e.value.response["Error"]
    assert err["Code"] == "ClientException"
    assert err["Message"] == "Container Instances cannot be empty."


@mock_aws
def test_describe_container_instances_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)

    with pytest.raises(ClientError) as exc:
        client.describe_container_instances(containerInstances=[])
    assert exc.value.response["Error"]["Code"] == "ClusterNotFoundException"

    client.create_cluster()
    with pytest.raises(ClientError) as exc:
        client.describe_container_instances(containerInstances=[])
    assert (
        exc.value.response["Error"]["Message"] == "Container Instances cannot be empty."
    )


@mock_aws
def test_update_container_instances_state():
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"
    ecs_client.create_cluster(clusterName=test_cluster_name)

    instance_to_create = 3
    test_instance_arns = []
    for _ in range(0, instance_to_create):
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

    test_instance_ids = list(map((lambda x: x.split("/")[-1]), test_instance_arns))
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name,
        containerInstances=test_instance_ids,
        status="DRAINING",
    )
    assert len(response["failures"]) == 0
    assert len(response["containerInstances"]) == instance_to_create
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        assert status == "DRAINING"
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name,
        containerInstances=test_instance_ids,
        status="DRAINING",
    )
    assert len(response["failures"]) == 0
    assert len(response["containerInstances"]) == instance_to_create
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        assert status == "DRAINING"
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name, containerInstances=test_instance_ids, status="ACTIVE"
    )
    assert len(response["failures"]) == 0
    assert len(response["containerInstances"]) == instance_to_create
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        assert status == "ACTIVE"
    with pytest.raises(ClientError):
        ecs_client.update_container_instances_state(
            cluster=test_cluster_name,
            containerInstances=test_instance_ids,
            status="test_status",
        )


@mock_aws
def test_update_container_instances_state_by_arn():
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"
    ecs_client.create_cluster(clusterName=test_cluster_name)

    instance_to_create = 3
    test_instance_arns = []
    for _ in range(0, instance_to_create):
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
    assert len(response["failures"]) == 0
    assert len(response["containerInstances"]) == instance_to_create
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        assert status == "DRAINING"
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name,
        containerInstances=test_instance_arns,
        status="DRAINING",
    )
    assert len(response["failures"]) == 0
    assert len(response["containerInstances"]) == instance_to_create
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        assert status == "DRAINING"
    response = ecs_client.update_container_instances_state(
        cluster=test_cluster_name,
        containerInstances=test_instance_arns,
        status="ACTIVE",
    )
    assert len(response["failures"]) == 0
    assert len(response["containerInstances"]) == instance_to_create
    response_statuses = [ci["status"] for ci in response["containerInstances"]]
    for status in response_statuses:
        assert status == "ACTIVE"
    with pytest.raises(ClientError):
        ecs_client.update_container_instances_state(
            cluster=test_cluster_name,
            containerInstances=test_instance_arns,
            status="test_status",
        )


@mock_aws
def test_run_task():
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

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
    response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        startedBy="moto",
    )
    assert len(response["tasks"]) == 1
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
    assert len(response["tasks"]) == 2
    task = response["tasks"][0]
    assert f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/" in task["taskArn"]
    assert (
        task["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert (
        task["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert (
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance/"
        in task["containerInstanceArn"]
    )
    assert task["overrides"] == {}
    assert task["lastStatus"] == "RUNNING"
    assert task["desiredStatus"] == "RUNNING"
    assert task["startedBy"] == "moto"
    assert task["stoppedReason"] == ""
    assert task["tags"][0].get("value") == "tagValue0"


@mock_aws
def test_wait_tasks_stopped():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set transition directly in ServerMode")

    state_manager.set_transition(
        model_name="ecs::task",
        transition={"progression": "immediate"},
    )

    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name,
        instanceIdentityDocument=instance_id_document,
    )

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
    response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        startedBy="moto",
    )
    task_arn = response["tasks"][0]["taskArn"]

    assert len(response["tasks"]) == 1
    client.get_waiter("tasks_stopped").wait(
        cluster="test_ecs_cluster",
        tasks=[task_arn],
    )

    response = client.describe_tasks(cluster="test_ecs_cluster", tasks=[task_arn])
    assert response["tasks"][0]["lastStatus"] == "STOPPED"

    state_manager.unset_transition("ecs::task")


@mock_aws
def test_task_state_transitions():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set transition directly in ServerMode")

    state_manager.set_transition(
        model_name="ecs::task",
        transition={"progression": "manual", "times": 1},
    )

    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name,
        instanceIdentityDocument=instance_id_document,
    )

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

    response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        startedBy="moto",
    )
    task_arn = response["tasks"][0]["taskArn"]
    assert len(response["tasks"]) == 1

    task_status = response["tasks"][0]["lastStatus"]
    assert task_status == "RUNNING"

    for status in ("DEACTIVATING", "STOPPING", "DEPROVISIONING", "STOPPED"):
        response = client.describe_tasks(cluster="test_ecs_cluster", tasks=[task_arn])
        assert response["tasks"][0]["lastStatus"] == status

    state_manager.unset_transition("ecs::task")


@mock_aws
def test_run_task_awsvpc_network():
    # Setup
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2_client = boto3.client("ec2", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    # ECS setup
    setup_resources = setup_ecs(client, ec2)

    # Execute
    response = client.run_task(
        cluster="test_ecs_cluster",
        overrides={},
        taskDefinition="test_ecs_task",
        startedBy="moto",
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [setup_resources[0].id],
                "securityGroups": [setup_resources[1].id],
            }
        },
    )

    # Verify
    assert len(response["tasks"]) == 1
    assert response["tasks"][0]["lastStatus"] == "RUNNING"
    assert response["tasks"][0]["desiredStatus"] == "RUNNING"
    assert response["tasks"][0]["startedBy"] == "moto"
    assert response["tasks"][0]["stoppedReason"] == ""

    eni = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "description", "Values": ["moto ECS"]}]
    )["NetworkInterfaces"][0]
    # should be UUID
    UUID(response["tasks"][0]["attachments"][0]["id"])
    assert response["tasks"][0]["attachments"][0]["status"] == "ATTACHED"
    assert response["tasks"][0]["attachments"][0]["type"] == "ElasticNetworkInterface"

    details = response["tasks"][0]["attachments"][0]["details"]
    assert {"name": "subnetId", "value": setup_resources[0].id} in details
    assert {"name": "privateDnsName", "value": eni["PrivateDnsName"]} in details
    assert {"name": "privateIPv4Address", "value": eni["PrivateIpAddress"]} in details
    assert {"name": "networkInterfaceId", "value": eni["NetworkInterfaceId"]} in details
    assert {"name": "macAddress", "value": eni["MacAddress"]} in details


@mock_aws
def test_run_task_awsvpc_network_error():
    # Setup
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    # ECS setup
    setup_ecs(client, ec2)

    # Execute
    with pytest.raises(ClientError) as exc:
        client.run_task(
            cluster="test_ecs_cluster",
            overrides={},
            taskDefinition="test_ecs_task",
            startedBy="moto",
            launchType="FARGATE",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Network Configuration must be provided when networkMode 'awsvpc' is specified."
    )


@mock_aws
def test_run_task_default_cluster():
    client = boto3.client("ecs", region_name=ECS_REGION)

    test_cluster_name = "default"

    client.create_cluster(clusterName=test_cluster_name)

    client.register_task_definition(
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
    response = client.run_task(
        launchType="FARGATE",
        overrides={},
        taskDefinition="test_ecs_task",
        count=2,
        startedBy="moto",
    )
    assert len(response["tasks"]) == 2
    assert response["tasks"][0]["launchType"] == "FARGATE"
    assert response["tasks"][0]["taskArn"].startswith(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/default/"
    )
    assert (
        response["tasks"][0]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/default"
    )
    assert (
        response["tasks"][0]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert response["tasks"][0]["overrides"] == {}
    assert response["tasks"][0]["lastStatus"] == "RUNNING"
    assert response["tasks"][0]["desiredStatus"] == "RUNNING"
    assert response["tasks"][0]["startedBy"] == "moto"
    assert response["tasks"][0]["stoppedReason"] == ""


@mock_aws
@mock.patch.dict(os.environ, {"MOTO_ECS_NEW_ARN": "TrUe"})
def test_run_task_default_cluster_new_arn_format():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Can't set environment variables in server mode for a single test"
        )
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "default"

    client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    client.register_task_definition(
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
    task = client.run_task(
        launchType="FARGATE",
        overrides={},
        taskDefinition="test_ecs_task",
        count=1,
        startedBy="moto",
    )["tasks"][0]
    assert task["taskArn"].startswith(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/{test_cluster_name}/"
    )


@mock_aws
def test_run_task_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.register_task_definition(
        family="test_ecs_task",
        memory="400",
        containerDefinitions=[{"name": "irrelevant", "image": "irrelevant"}],
    )

    with pytest.raises(ClientError) as exc:
        client.run_task(cluster="not_a_cluster", taskDefinition="test_ecs_task")
    err = exc.value.response["Error"]
    assert err["Code"] == "ClusterNotFoundException"
    assert err["Message"] == "Cluster not found."

    with pytest.raises(ClientError) as exc:
        client.run_task(
            cluster="not_a_cluster",
            taskDefinition="test_ecs_task",
            launchType="Fargate",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert err["Message"] == "launch type should be one of [EC2,FARGATE,EXTERNAL]"


@mock_aws
def test_start_task():
    client = boto3.client("ecs", region_name=ECS_REGION)
    test_cluster_name = "test_ecs_cluster"
    setup_ecs_cluster_with_ec2_instance(client, test_cluster_name)

    container_instances = client.list_container_instances(cluster=test_cluster_name)
    container_instance_id = container_instances["containerInstanceArns"][0].split("/")[
        -1
    ]

    response = client.start_task(
        cluster="test_ecs_cluster",
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="moto",
    )

    assert len(response["tasks"]) == 1
    assert (
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/" in response["tasks"][0]["taskArn"]
    )
    assert (
        response["tasks"][0]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert (
        response["tasks"][0]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert (
        response["tasks"][0]["containerInstanceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance/test_ecs_cluster/{container_instance_id}"
    )
    assert response["tasks"][0]["tags"] == []
    assert response["tasks"][0]["overrides"] == {}
    assert response["tasks"][0]["lastStatus"] == "RUNNING"
    assert response["tasks"][0]["desiredStatus"] == "RUNNING"
    assert response["tasks"][0]["startedBy"] == "moto"
    assert response["tasks"][0]["stoppedReason"] == ""


@mock_aws
def test_start_task_with_tags():
    client = boto3.client("ecs", region_name=ECS_REGION)
    test_cluster_name = "test_ecs_cluster"
    setup_ecs_cluster_with_ec2_instance(client, test_cluster_name)

    container_instances = client.list_container_instances(cluster=test_cluster_name)
    container_instance_id = container_instances["containerInstanceArns"][0].split("/")[
        -1
    ]

    task_tags = [{"key": "Name", "value": "test_ecs_start_task"}]
    response = client.start_task(
        cluster="test_ecs_cluster",
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="moto",
        tags=task_tags,
    )

    assert len(response["tasks"]) == 1
    assert (
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/" in response["tasks"][0]["taskArn"]
    )
    assert (
        response["tasks"][0]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert (
        response["tasks"][0]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert (
        response["tasks"][0]["containerInstanceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance/test_ecs_cluster/{container_instance_id}"
    )
    assert response["tasks"][0]["tags"] == task_tags
    assert response["tasks"][0]["overrides"] == {}
    assert response["tasks"][0]["lastStatus"] == "RUNNING"
    assert response["tasks"][0]["desiredStatus"] == "RUNNING"
    assert response["tasks"][0]["startedBy"] == "moto"
    assert response["tasks"][0]["stoppedReason"] == ""


@mock_aws
def test_start_task_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.register_task_definition(
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

    with pytest.raises(ClientError):
        client.start_task(
            taskDefinition="test_ecs_task",
            containerInstances=["not_a_container_instance"],
        )

    client.create_cluster()
    with pytest.raises(ClientError):
        client.start_task(taskDefinition="test_ecs_task", containerInstances=[])


@mock_aws
def test_list_tasks():
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    client.create_cluster()

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    client.register_container_instance(instanceIdentityDocument=instance_id_document)

    container_instances = client.list_container_instances()
    container_instance_id = container_instances["containerInstanceArns"][0].split("/")[
        -1
    ]

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

    client.start_task(
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="foo",
    )

    client.start_task(
        taskDefinition="test_ecs_task",
        overrides={},
        containerInstances=[container_instance_id],
        startedBy="bar",
    )

    assert len(client.list_tasks()["taskArns"]) == 2
    assert len(client.list_tasks(startedBy="foo")["taskArns"]) == 1


@mock_aws
def test_list_tasks_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)
    with pytest.raises(ClientError) as exc:
        client.list_tasks(cluster="not_a_cluster")
    assert exc.value.response["Error"]["Code"] == "ClusterNotFoundException"


@mock_aws
def test_describe_tasks():
    client = boto3.client("ecs", region_name=ECS_REGION)
    test_cluster_name = "test_ecs_cluster"
    setup_ecs_cluster_with_ec2_instance(client, test_cluster_name)

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

    assert len(response["tasks"]) == 2
    assert set(
        [response["tasks"][0]["taskArn"], response["tasks"][1]["taskArn"]]
    ) == set(tasks_arns)

    # Test we can pass task ids instead of ARNs
    response = client.describe_tasks(
        cluster="test_ecs_cluster", tasks=[tasks_arns[0].split("/")[-1]]
    )
    assert len(response["tasks"]) == 1


@mock_aws
def test_describe_tasks_empty_tags():
    client = boto3.client("ecs", region_name=ECS_REGION)
    test_cluster_name = "test_ecs_cluster"
    setup_ecs_cluster_with_ec2_instance(client, test_cluster_name)

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
    response = client.describe_tasks(
        cluster="test_ecs_cluster", tasks=tasks_arns, include=["TAGS"]
    )

    assert len(response["tasks"]) == 2
    assert set(
        [response["tasks"][0]["taskArn"], response["tasks"][1]["taskArn"]]
    ) == set(tasks_arns)
    assert response["tasks"][0]["tags"] == []

    # Test we can pass task ids instead of ARNs
    response = client.describe_tasks(
        cluster="test_ecs_cluster", tasks=[tasks_arns[0].split("/")[-1]]
    )
    assert len(response["tasks"]) == 1


@mock_aws
def test_describe_tasks_include_tags():
    client = boto3.client("ecs", region_name=ECS_REGION)
    test_cluster_name = "test_ecs_cluster"
    setup_ecs_cluster_with_ec2_instance(client, test_cluster_name)

    task_tags = [{"key": "Name", "value": "test_ecs_task"}]
    tasks_arns = [
        task["taskArn"]
        for task in client.run_task(
            cluster="test_ecs_cluster",
            overrides={},
            taskDefinition="test_ecs_task",
            count=2,
            startedBy="moto",
            tags=task_tags,
        )["tasks"]
    ]
    response = client.describe_tasks(
        cluster="test_ecs_cluster", tasks=tasks_arns, include=["TAGS"]
    )

    assert len(response["tasks"]) == 2
    assert set(
        [response["tasks"][0]["taskArn"], response["tasks"][1]["taskArn"]]
    ) == set(tasks_arns)
    assert response["tasks"][0]["tags"] == task_tags

    # Test we can pass task ids instead of ARNs
    response = client.describe_tasks(
        cluster="test_ecs_cluster", tasks=[tasks_arns[0].split("/")[-1]]
    )
    assert len(response["tasks"]) == 1


@mock_aws
def test_describe_tasks_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)

    with pytest.raises(ClientError) as exc:
        client.describe_tasks(tasks=[])
    assert exc.value.response["Error"]["Code"] == "ClusterNotFoundException"

    client.create_cluster()
    with pytest.raises(ClientError) as exc:
        client.describe_tasks(tasks=[])
    assert exc.value.response["Error"]["Code"] == "InvalidParameterException"


@mock_aws
def test_describe_task_definition_by_family():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
        family="test_ecs_task",
        containerDefinitions=[container_definition],
        proxyConfiguration={"type": "APPMESH", "containerName": "a"},
        inferenceAccelerators=[{"deviceName": "dn", "deviceType": "dt"}],
        runtimePlatform={"cpuArchitecture": "X86_64", "operatingSystemFamily": "LINUX"},
        ipcMode="host",
        pidMode="host",
        ephemeralStorage={"sizeInGiB": 123},
    )
    family = task_definition["taskDefinition"]["family"]
    task = client.describe_task_definition(taskDefinition=family)["taskDefinition"]
    assert task["containerDefinitions"][0] == dict(
        container_definition,
        **{"mountPoints": [], "portMappings": [], "volumesFrom": []},
    )
    assert (
        task["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert task["volumes"] == []
    assert task["status"] == "ACTIVE"
    assert task["proxyConfiguration"] == {"type": "APPMESH", "containerName": "a"}
    assert task["inferenceAccelerators"] == [{"deviceName": "dn", "deviceType": "dt"}]
    assert task["runtimePlatform"] == {
        "cpuArchitecture": "X86_64",
        "operatingSystemFamily": "LINUX",
    }
    assert task["ipcMode"] == "host"
    assert task["pidMode"] == "host"
    assert task["ephemeralStorage"] == {"sizeInGiB": 123}


@mock_aws
def test_stop_task():
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

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

    assert stop_response["task"]["taskArn"] == run_response["tasks"][0].get("taskArn")
    assert stop_response["task"]["lastStatus"] == "STOPPED"
    assert stop_response["task"]["desiredStatus"] == "STOPPED"
    assert stop_response["task"]["stoppedReason"] == "moto testing"


@mock_aws
def test_stop_task_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)

    with pytest.raises(ClientError) as exc:
        client.stop_task(task="fake_task")
    assert exc.value.response["Error"]["Code"] == "ClusterNotFoundException"


@mock_aws
def test_resource_reservation_and_release():
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

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
    assert remaining_resources["CPU"] == registered_resources["CPU"] - 1024
    assert remaining_resources["MEMORY"] == registered_resources["MEMORY"] - 400
    registered_resources["PORTS"].append("80")
    assert remaining_resources["PORTS"] == registered_resources["PORTS"]
    assert container_instance_description["runningTasksCount"] == 1
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
    assert remaining_resources["CPU"] == registered_resources["CPU"]
    assert remaining_resources["MEMORY"] == registered_resources["MEMORY"]
    assert remaining_resources["PORTS"] == registered_resources["PORTS"]
    assert container_instance_description["runningTasksCount"] == 0


@mock_aws
def test_resource_reservation_and_release_memory_reservation():
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    client.register_task_definition(
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
    assert remaining_resources["CPU"] == registered_resources["CPU"]
    assert remaining_resources["MEMORY"] == registered_resources["MEMORY"] - 400
    assert remaining_resources["PORTS"] == registered_resources["PORTS"]
    assert container_instance_description["runningTasksCount"] == 1
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
    assert remaining_resources["CPU"] == registered_resources["CPU"]
    assert remaining_resources["MEMORY"] == registered_resources["MEMORY"]
    assert remaining_resources["PORTS"] == registered_resources["PORTS"]
    assert container_instance_description["runningTasksCount"] == 0


@mock_aws
def test_task_definitions_unable_to_be_placed():
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 5000,
                "memory": 40000,
            }
        ],
    )
    response = client.run_task(
        cluster="test_ecs_cluster",
        taskDefinition="test_ecs_task",
        count=2,
    )
    assert len(response["tasks"]) == 0


@mock_aws
def test_task_definitions_with_port_clash():
    client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    client.register_task_definition(
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
    assert len(response["tasks"]) == 1
    assert (
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/" in response["tasks"][0]["taskArn"]
    )
    assert (
        response["tasks"][0]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert (
        response["tasks"][0]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )
    assert (
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance/"
        in response["tasks"][0]["containerInstanceArn"]
    )
    assert response["tasks"][0]["overrides"] == {}
    assert response["tasks"][0]["lastStatus"] == "RUNNING"
    assert response["tasks"][0]["desiredStatus"] == "RUNNING"
    assert response["tasks"][0]["startedBy"] == "moto"
    assert response["tasks"][0]["stoppedReason"] == ""


@mock_aws
def test_attributes():
    # Combined put, list delete attributes into the same test due to the amount of setup
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    ecs_client.create_cluster(clusterName=test_cluster_name)

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

    assert response["containerInstance"]["ec2InstanceId"] == test_instance.id
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

    assert response["containerInstance"]["ec2InstanceId"] == test_instance.id
    full_arn2 = response["containerInstance"]["containerInstanceArn"]
    partial_arn2 = full_arn2.rsplit("/", 1)[-1]

    # uuid1 isn't unique enough when the pc is fast ;-)
    assert full_arn2 != full_arn1

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
    assert len(attrs) == NUM_CUSTOM_ATTRIBUTES + (
        NUM_DEFAULT_ATTRIBUTES * len(instances)
    )

    # Tests that the attrs have been set properly
    assert len(list(filter(lambda item: item["name"] == "env", attrs))) == 2
    assert (
        len(
            list(
                filter(
                    lambda item: item["name"] == "attr1"
                    and item["value"] == "instance1",
                    attrs,
                )
            )
        )
        == 1
    )

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
    assert len(attrs) == NUM_CUSTOM_ATTRIBUTES + (
        NUM_DEFAULT_ATTRIBUTES * len(instances)
    )


@mock_aws
def test_poll_endpoint():
    # Combined put, list delete attributes into the same test due to the amount of setup
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)

    # Just a placeholder until someone actually wants useless data, just testing it doesnt raise an exception
    resp = ecs_client.discover_poll_endpoint(cluster="blah", containerInstance="blah")
    assert "endpoint" in resp
    assert "telemetryEndpoint" in resp


@mock_aws
def test_list_task_definition_families():
    client = boto3.client("ecs", region_name=ECS_REGION)
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

    assert len(resp1["families"]) == 2
    assert len(resp2["families"]) == 1


@mock_aws
def test_default_container_instance_attributes():
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    # Create cluster and EC2 instance
    ecs_client.create_cluster(clusterName=test_cluster_name)

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

    assert response["containerInstance"]["ec2InstanceId"] == test_instance.id

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


@mock_aws
def test_describe_container_instances_with_attributes():
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    test_cluster_name = "test_ecs_cluster"

    # Create cluster and EC2 instance
    ecs_client.create_cluster(clusterName=test_cluster_name)

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

    assert response["containerInstance"]["ec2InstanceId"] == test_instance.id
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


@mock_aws
def test_create_service_load_balancing():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")
    client.register_task_definition(
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
    assert (
        response["service"]["clusterArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test_ecs_cluster"
    )
    assert response["service"]["desiredCount"] == 2
    assert len(response["service"]["events"]) == 0
    assert len(response["service"]["loadBalancers"]) == 1
    assert (
        response["service"]["loadBalancers"][0]["targetGroupArn"]
        == "test_target_group_arn"
    )
    assert (
        response["service"]["loadBalancers"][0]["loadBalancerName"]
        == "test_load_balancer_name"
    )
    assert (
        response["service"]["loadBalancers"][0]["containerName"]
        == "test_container_name"
    )
    assert response["service"]["loadBalancers"][0]["containerPort"] == 123
    assert response["service"]["pendingCount"] == 2
    assert response["service"]["runningCount"] == 0
    assert (
        response["service"]["serviceArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:service/test_ecs_cluster/test_ecs_service"
    )
    assert response["service"]["serviceName"] == "test_ecs_service"
    assert response["service"]["status"] == "ACTIVE"
    assert (
        response["service"]["taskDefinition"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("ecs", region_name=ECS_REGION)
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
    assert response["taskDefinition"]["revision"] == 1
    assert (
        response["taskDefinition"]["taskDefinitionArn"]
        == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/test_ecs_task:1"
    )

    task_definition_arn = response["taskDefinition"]["taskDefinitionArn"]
    response = client.list_tags_for_resource(resourceArn=task_definition_arn)

    assert response["tags"] == [
        {"key": "createdBy", "value": "moto-unittest"},
        {"key": "foo", "value": "bar"},
    ]


@mock_aws
def test_list_tags_exceptions():
    client = boto3.client("ecs", region_name=ECS_REGION)
    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(
            resourceArn="arn:aws:ecs:us-east-1:012345678910:service/fake_service:1"
        )
    assert "ServiceNotFoundException" in exc.value.response["Error"]["Message"]

    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(
            resourceArn="arn:aws:ecs:us-east-1:012345678910:task-definition/fake_task:1"
        )
    assert (
        exc.value.response["Error"]["Message"] == "Unable to describe task definition."
    )


@mock_aws
def test_list_tags_for_resource_ecs_service():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")
    client.register_task_definition(
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
    assert response["tags"] == [
        {"key": "createdBy", "value": "moto-unittest"},
        {"key": "foo", "value": "bar"},
    ]


@mock_aws
@pytest.mark.parametrize("long_arn", ["disabled", "enabled"])
def test_ecs_service_tag_resource(long_arn):
    """
    Tagging does some weird ARN parsing - ensure it works with both long and short formats
    """
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.put_account_setting(name="serviceLongArnFormat", value=long_arn)

    client.create_cluster(clusterName="test_ecs_cluster")
    client.register_task_definition(
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
    service_arn2 = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service_2",
        taskDefinition="test_ecs_task",
        desiredCount=1,
    )["service"]["serviceArn"]
    service_arn1 = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
    )["service"]["serviceArn"]

    client.tag_resource(
        resourceArn=service_arn1,
        tags=[
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "foo", "value": "bar"},
        ],
    )
    client.tag_resource(
        resourceArn=service_arn2,
        tags=[
            {"key": "createdBy-2", "value": "moto-unittest-2"},
            {"key": "foo-2", "value": "bar-2"},
        ],
    )
    tags = client.list_tags_for_resource(resourceArn=service_arn1)["tags"]
    assert tags == [
        {"key": "createdBy", "value": "moto-unittest"},
        {"key": "foo", "value": "bar"},
    ]

    tags = client.list_tags_for_resource(resourceArn=service_arn2)["tags"]
    assert tags == [
        {"key": "createdBy-2", "value": "moto-unittest-2"},
        {"key": "foo-2", "value": "bar-2"},
    ]


@mock_aws
def test_ecs_service_tag_resource_overwrites_tag():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")
    client.register_task_definition(
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
    service_arn = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[{"key": "foo", "value": "bar"}],
    )["service"]["serviceArn"]
    client.tag_resource(
        resourceArn=service_arn,
        tags=[
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "foo", "value": "hello world"},
        ],
    )
    tags = client.list_tags_for_resource(resourceArn=service_arn)["tags"]
    assert tags == [
        {"key": "createdBy", "value": "moto-unittest"},
        {"key": "foo", "value": "hello world"},
    ]


@mock_aws
def test_ecs_service_untag_resource():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")
    client.register_task_definition(
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
    service_arn = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[{"key": "foo", "value": "bar"}],
    )["service"]["serviceArn"]
    client.untag_resource(resourceArn=service_arn, tagKeys=["foo"])
    response = client.list_tags_for_resource(resourceArn=service_arn)
    assert response["tags"] == []


@mock_aws
def test_ecs_service_untag_resource_multiple_tags():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")
    client.register_task_definition(
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
    service_arn = client.create_service(
        cluster="test_ecs_cluster",
        serviceName="test_ecs_service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        tags=[
            {"key": "foo", "value": "bar"},
            {"key": "createdBy", "value": "moto-unittest"},
            {"key": "hello", "value": "world"},
        ],
    )["service"]["serviceArn"]
    client.untag_resource(resourceArn=service_arn, tagKeys=["foo", "createdBy"])
    response = client.list_tags_for_resource(resourceArn=service_arn)
    assert response["tags"] == [{"key": "hello", "value": "world"}]


@mock_aws
def test_update_cluster():
    client = boto3.client("ecs", region_name=ECS_REGION)
    client.create_cluster(clusterName="test_ecs_cluster")

    resp = client.update_cluster(
        cluster="test_ecs_cluster",
        settings=[{"name": "containerInsights", "value": "v"}],
        configuration={"executeCommandConfiguration": {"kmsKeyId": "arn:kms:stuff"}},
    )["cluster"]
    assert resp["settings"] == [{"name": "containerInsights", "value": "v"}]
    assert resp["configuration"] == {
        "executeCommandConfiguration": {"kmsKeyId": "arn:kms:stuff"}
    }


@mock_aws
def test_ecs_task_definition_placement_constraints():
    client = boto3.client("ecs", region_name=ECS_REGION)
    task_def = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
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
    )["taskDefinition"]

    assert task_def["placementConstraints"] == [
        {"type": "memberOf", "expression": "attribute:ecs.instance-type =~ t2.*"}
    ]


@mock_aws
def test_list_tasks_with_filters():
    ecs = boto3.client("ecs", region_name=ECS_REGION)
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    clstr1 = "test_cluster_1"
    clstr2 = "test_cluster_2"
    ecs.create_cluster(clusterName=clstr1)
    ecs.create_cluster(clusterName=clstr2)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    ecs.register_container_instance(
        cluster=clstr1, instanceIdentityDocument=instance_id_document
    )
    ecs.register_container_instance(
        cluster=clstr2, instanceIdentityDocument=instance_id_document
    )

    container_instances = ecs.list_container_instances(cluster=clstr1)
    _id1 = container_instances["containerInstanceArns"][0].split("/")[-1]
    container_instances = ecs.list_container_instances(cluster=clstr2)
    _id2 = container_instances["containerInstanceArns"][0].split("/")[-1]

    test_container_def = {
        "name": "hello_world",
        "image": "docker/hello-world:latest",
        "cpu": 1024,
        "memory": 400,
    }

    ecs.register_task_definition(
        family="test_task_def_1", containerDefinitions=[test_container_def]
    )

    ecs.register_task_definition(
        family="test_task_def_2", containerDefinitions=[test_container_def]
    )

    ecs.start_task(
        cluster=clstr1,
        taskDefinition="test_task_def_1",
        overrides={},
        containerInstances=[_id1],
        startedBy="foo",
    )

    resp = ecs.start_task(
        cluster=clstr2,
        taskDefinition="test_task_def_2",
        overrides={},
        containerInstances=[_id2],
        startedBy="foo",
    )
    task_to_stop = resp["tasks"][0]["taskArn"]

    ecs.start_task(
        cluster=clstr1,
        taskDefinition="test_task_def_1",
        overrides={},
        containerInstances=[_id1],
        startedBy="bar",
    )

    assert len(ecs.list_tasks(cluster=clstr1)["taskArns"]) == 2
    assert len(ecs.list_tasks(cluster=clstr2)["taskArns"]) == 1

    assert (
        len(ecs.list_tasks(cluster=clstr1, containerInstance="bad-id")["taskArns"]) == 0
    )
    assert len(ecs.list_tasks(cluster=clstr1, containerInstance=_id1)["taskArns"]) == 2
    assert len(ecs.list_tasks(cluster=clstr2, containerInstance=_id2)["taskArns"]) == 1

    assert (
        len(ecs.list_tasks(cluster=clstr1, family="non-existent-family")["taskArns"])
        == 0
    )
    assert (
        len(ecs.list_tasks(cluster=clstr1, family="test_task_def_1")["taskArns"]) == 2
    )
    assert (
        len(ecs.list_tasks(cluster=clstr2, family="test_task_def_2")["taskArns"]) == 1
    )

    assert (
        len(ecs.list_tasks(cluster=clstr1, startedBy="non-existent-entity")["taskArns"])
        == 0
    )
    assert len(ecs.list_tasks(cluster=clstr1, startedBy="foo")["taskArns"]) == 1
    assert len(ecs.list_tasks(cluster=clstr1, startedBy="bar")["taskArns"]) == 1
    assert len(ecs.list_tasks(cluster=clstr2, startedBy="foo")["taskArns"]) == 1

    assert len(ecs.list_tasks(cluster=clstr1, desiredStatus="RUNNING")["taskArns"]) == 2
    assert len(ecs.list_tasks(cluster=clstr2, desiredStatus="RUNNING")["taskArns"]) == 1
    ecs.stop_task(cluster=clstr2, task=task_to_stop, reason="for testing")
    assert len(ecs.list_tasks(cluster=clstr1, desiredStatus="RUNNING")["taskArns"]) == 2
    assert len(ecs.list_tasks(cluster=clstr2, desiredStatus="STOPPED")["taskArns"]) == 1

    resp = ecs.list_tasks(cluster=clstr1, startedBy="foo")
    assert len(resp["taskArns"]) == 1

    resp = ecs.list_tasks(cluster=clstr1, containerInstance=_id1, startedBy="bar")
    assert len(resp["taskArns"]) == 1


@pytest.mark.parametrize(
    "update_params",
    [
        {
            "loadBalancers": [
                {
                    "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/mock-service-http",
                    "loadBalancerName": "mock-service1",
                    "containerName": "mock-container1",
                    "containerPort": 80,
                }
            ]
        },
        {
            "serviceRegistries": [
                {
                    "registryArn": "string",
                    "port": 123,
                    "containerName": "string",
                    "containerPort": 123,
                },
                {
                    "registryArn": "string2",
                    "port": 1234,
                    "containerName": "string2",
                    "containerPort": 1234,
                },
            ],
        },
        {
            "placementStrategy": [
                {"type": "random", "field": "string"},
            ],
        },
        {
            "deploymentConfiguration": {
                "deploymentCircuitBreaker": {"enable": True, "rollback": True},
                "maximumPercent": 10,
                "minimumHealthyPercent": 1,
                "alarms": {
                    "alarmNames": [
                        "string",
                    ],
                    "enable": True,
                    "rollback": True,
                },
            },
        },
    ],
)
@mock_aws
def test_remove_tg(update_params):
    # Setup
    ecs_client = boto3.client("ecs", region_name=ECS_REGION)
    cluster = "mock-cluster"
    service = "mock-service"
    ecs_client.create_cluster(clusterName=cluster)
    ecs_client.create_service(
        cluster=cluster,
        serviceName=service,
    )

    # Execute
    ecs_client.update_service(
        cluster="arn:aws:ecs:us-east-1:123456789012:cluster/" + cluster,
        service=service,
        **update_params,
    )
    response = ecs_client.describe_services(cluster=cluster, services=[service])
    response_svc = response["services"][0]
    property_key = next(iter(update_params))
    property_val = next(iter(update_params.values()))

    # Verify
    assert len(response_svc[property_key]) == len(property_val)
    assert response_svc[property_key] == update_params[property_key]


def setup_ecs(client, ec2):
    """test helper"""
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    sg = ec2.create_security_group(
        VpcId=vpc.id, GroupName="test-ecs", Description="moto ecs"
    )
    test_cluster_name = "test_ecs_cluster"
    client.create_cluster(clusterName=test_cluster_name)
    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]
    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )
    client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )
    client.register_task_definition(
        family="test_ecs_task",
        networkMode="awsvpc",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
            }
        ],
    )

    return subnet, sg


def setup_ecs_cluster_with_ec2_instance(client, test_cluster_name):
    ec2 = boto3.resource("ec2", region_name=ECS_REGION)

    client.create_cluster(clusterName=test_cluster_name)
    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]
    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )
    client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )

    client.register_task_definition(
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
