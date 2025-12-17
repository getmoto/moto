"""Unit tests for ecs-supported APIs."""

import boto3

from moto import mock_aws


@mock_aws
def test_delete_task_definitions():
    client = boto3.client("ecs", region_name="us-east-2")
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

    client.deregister_task_definition(taskDefinition="test_ecs_task:1")
    resp = client.delete_task_definitions(taskDefinitions=["test_ecs_task:1"])

    assert resp["taskDefinitions"] == [
        {
            "family": "test_ecs_task",
            "revision": 1,
            "volumes": [],
            "compatibilities": ["EC2"],
            "status": "DELETE_IN_PROGRESS",
            "containerDefinitions": [
                {
                    "cpu": 1024,
                    "portMappings": [],
                    "essential": True,
                    "environment": [
                        {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                    ],
                    "mountPoints": [],
                    "volumesFrom": [],
                    "name": "hello_world",
                    "image": "docker/hello-world:latest",
                    "memory": 400,
                    "logConfiguration": {"logDriver": "json-file"},
                }
            ],
            "networkMode": "bridge",
            "placementConstraints": [],
            "taskDefinitionArn": "arn:aws:ecs:us-east-2:123456789012:task-definition/test_ecs_task:1",
        }
    ]
    assert resp["failures"] == []


@mock_aws
def test_delete_task_definitions_cannot_delete_active():
    client = boto3.client("ecs", region_name="us-east-2")
    task_def_1 = client.register_task_definition(
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

    resp = client.delete_task_definitions(
        taskDefinitions=[
            task_def_1["taskDefinition"]["taskDefinitionArn"],
        ]
    )

    assert resp["taskDefinitions"] == []
    assert resp["failures"] == [
        {
            "arn": task_def_1["taskDefinition"]["taskDefinitionArn"],
            "reason": "The specified task definition is still in ACTIVE status. Please deregister the target and try again.",
        }
    ]


@mock_aws
def test_delete_task_definitions_invalid_identifier():
    client = boto3.client("ecs", region_name="us-east-2")
    resp = client.delete_task_definitions(
        taskDefinitions=[
            "invalid-task-definition-name",
        ]
    )

    assert resp["taskDefinitions"] == []
    assert resp["failures"] == [
        {
            "arn": "invalid-task-definition-name",
            "reason": "The specified task definition identifier is invalid. Specify a valid name or ARN and try again.",
        }
    ]


@mock_aws
def test_delete_task_definitions_nonexistent():
    client = boto3.client("ecs", region_name="us-east-2")
    resp = client.delete_task_definitions(
        taskDefinitions=[
            "nonexistent-task-definition:1",
        ]
    )

    assert resp["taskDefinitions"] == []
    assert resp["failures"] == [
        {
            "arn": "nonexistent-task-definition:1",
            "reason": "The specified task definition does not exist. Specify a valid account, family, revision and try again.",
        }
    ]
