import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

cluster_name = "test_ecs_cluster"
service_name = "test_ecs_service"
task_def_name = "test_ecs_task"


@mock_aws
def test_create_task_set():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    create_task_def(client)
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
    assert task_set["clusterArn"] == cluster_arn
    assert task_set["serviceArn"] == service_arn
    assert task_set["taskDefinition"].endswith(f"{task_def_name}:1")
    assert task_set["scale"] == {"value": 100.0, "unit": "PERCENT"}
    assert (
        task_set["loadBalancers"][0]["targetGroupArn"]
        == "arn:aws:elasticloadbalancing:us-east-1:01234567890:targetgroup/c26b93c1bc35466ba792d5b08fe6a5bc/ec39113f8831453a"
    )
    assert task_set["loadBalancers"][0]["containerPort"] == 8080
    assert task_set["loadBalancers"][0]["containerName"] == "hello_world"
    assert task_set["launchType"] == "EC2"
    assert task_set["platformVersion"] == "LATEST"


@mock_aws
def test_create_task_set_errors():
    # given
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    create_task_def(client)
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
    assert ex.operation_name == "CreateTaskSet"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ClientException"
    assert (
        ex.response["Error"]["Message"] == "launch type should be one of [EC2,FARGATE]"
    )


@mock_aws
def test_describe_task_sets():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    create_task_def(client)
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
        cluster=cluster_name, service=service_name, include=["TAGS"]
    )["taskSets"]

    cluster_arn = client.describe_clusters(clusters=[cluster_name])["clusters"][0][
        "clusterArn"
    ]

    service_arn = client.describe_services(
        cluster=cluster_name, services=[service_name]
    )["services"][0]["serviceArn"]

    assert len(task_sets) == 1
    assert "tags" in task_sets[0]
    assert task_sets[0]["taskDefinition"].endswith(f"{task_def_name}:1")
    assert task_sets[0]["clusterArn"] == cluster_arn
    assert task_sets[0]["serviceArn"] == service_arn
    assert task_sets[0]["serviceArn"].endswith(f"{service_name}")
    assert task_sets[0]["scale"] == {"value": 100.0, "unit": "PERCENT"}
    assert task_sets[0]["taskSetArn"].endswith(f"{task_sets[0]['id']}")
    assert (
        task_sets[0]["loadBalancers"][0]["targetGroupArn"]
        == "arn:aws:elasticloadbalancing:us-east-1:01234567890:targetgroup/c26b93c1bc35466ba792d5b08fe6a5bc/ec39113f8831453a"
    )
    assert task_sets[0]["loadBalancers"][0]["containerPort"] == 8080
    assert task_sets[0]["loadBalancers"][0]["containerName"] == "hello_world"
    assert task_sets[0]["launchType"] == "EC2"


@mock_aws
def test_delete_task_set():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    create_task_def(client)
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=task_def_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )

    task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name
    )["taskSet"]

    task_sets = client.describe_task_sets(
        cluster=cluster_name, service=service_name, taskSets=[task_set["taskSetArn"]]
    )["taskSets"]

    assert len(task_sets) == 1

    task_sets = client.describe_task_sets(
        cluster=cluster_name, service=service_name, taskSets=[task_set["taskSetArn"]]
    )["taskSets"]

    assert len(task_sets) == 1

    response = client.delete_task_set(
        cluster=cluster_name, service=service_name, taskSet=task_set["taskSetArn"]
    )
    assert response["taskSet"]["taskSetArn"] == task_set["taskSetArn"]

    task_sets = client.describe_task_sets(
        cluster=cluster_name, service=service_name, taskSets=[task_set["taskSetArn"]]
    )["taskSets"]

    assert len(task_sets) == 0

    with pytest.raises(ClientError):
        client.delete_task_set(
            cluster=cluster_name, service=service_name, taskSet=task_set["taskSetArn"]
        )


@mock_aws
def test_delete_task_set__using_partial_arn():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    create_task_def(client)
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=task_def_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )

    task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name
    )["taskSet"]

    # Partial ARN match
    # arn:aws:ecs:us-east-1:123456789012:task-set/test_ecs_cluster/test_ecs_service/ecs-svc/386233676373827416
    # --> ecs-svc/386233676373827416
    partial_arn = "/".join(task_set["taskSetArn"].split("/")[-2:])
    task_sets = client.describe_task_sets(
        cluster=cluster_name, service=service_name, taskSets=[partial_arn]
    )["taskSets"]

    assert len(task_sets) == 1

    response = client.delete_task_set(
        cluster=cluster_name, service=service_name, taskSet=partial_arn
    )
    assert response["taskSet"]["taskSetArn"] == task_set["taskSetArn"]


@mock_aws
def test_update_service_primary_task_set():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    create_task_def(client)
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )

    task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name
    )["taskSet"]

    service = client.describe_services(cluster=cluster_name, services=[service_name])[
        "services"
    ][0]

    _ = client.update_service_primary_task_set(
        cluster=cluster_name,
        service=service_name,
        primaryTaskSet=task_set["taskSetArn"],
    )

    service = client.describe_services(cluster=cluster_name, services=[service_name])[
        "services"
    ][0]
    assert service["taskSets"][0]["status"] == "PRIMARY"
    assert service["taskDefinition"] == service["taskSets"][0]["taskDefinition"]

    another_task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name
    )["taskSet"]
    service = client.describe_services(cluster=cluster_name, services=[service_name])[
        "services"
    ][0]
    assert service["taskSets"][1]["status"] == "ACTIVE"

    _ = client.update_service_primary_task_set(
        cluster=cluster_name,
        service=service_name,
        primaryTaskSet=another_task_set["taskSetArn"],
    )
    service = client.describe_services(cluster=cluster_name, services=[service_name])[
        "services"
    ][0]
    assert service["taskSets"][0]["status"] == "ACTIVE"
    assert service["taskSets"][1]["status"] == "PRIMARY"
    assert service["taskDefinition"] == service["taskSets"][1]["taskDefinition"]


@mock_aws
def test_update_task_set():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    create_task_def(client)
    _ = client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        desiredCount=2,
        deploymentController={"type": "EXTERNAL"},
    )

    task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name
    )["taskSet"]

    another_task_set = client.create_task_set(
        cluster=cluster_name, service=service_name, taskDefinition=task_def_name
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
        cluster=cluster_name, service=service_name, taskSets=[task_set["taskSetArn"]]
    )["taskSets"][0]
    assert updated_task_set["scale"]["value"] == 25.0
    assert updated_task_set["scale"]["unit"] == "PERCENT"


@mock_aws
def test_create_task_sets_with_tags():
    client = boto3.client("ecs", region_name="us-east-1")
    _ = client.create_cluster(clusterName=cluster_name)
    create_task_def(client)
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
        tags=[{"key": "k1", "value": "v1"}, {"key": "k2", "value": "v2"}],
    )

    task_set = client.describe_task_sets(
        cluster=cluster_name, service=service_name, include=["TAGS"]
    )["taskSets"][0]
    assert task_set["tags"] == [
        {"key": "k1", "value": "v1"},
        {"key": "k2", "value": "v2"},
    ]

    client.tag_resource(
        resourceArn=task_set["taskSetArn"], tags=[{"key": "k3", "value": "v3"}]
    )

    task_set = client.describe_task_sets(
        cluster=cluster_name, service=service_name, include=["TAGS"]
    )["taskSets"][0]
    assert len(task_set["tags"]) == 3
    assert {"key": "k1", "value": "v1"} in task_set["tags"]
    assert {"key": "k2", "value": "v2"} in task_set["tags"]
    assert {"key": "k3", "value": "v3"} in task_set["tags"]

    client.untag_resource(resourceArn=task_set["taskSetArn"], tagKeys=["k2"])

    resp = client.list_tags_for_resource(resourceArn=task_set["taskSetArn"])
    assert len(resp["tags"]) == 2
    assert {"key": "k1", "value": "v1"} in resp["tags"]
    assert {"key": "k3", "value": "v3"} in resp["tags"]


def create_task_def(client):
    client.register_task_definition(
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
