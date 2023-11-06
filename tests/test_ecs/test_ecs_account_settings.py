import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.ec2 import utils as ec2_utils
from tests import EXAMPLE_AMI_ID


@mock_aws
def test_list_account_settings_initial():
    client = boto3.client("ecs", region_name="eu-west-1")

    resp = client.list_account_settings()
    assert resp["settings"] == []


@mock_aws
@pytest.mark.parametrize(
    "name",
    ["containerInstanceLongArnFormat", "serviceLongArnFormat", "taskLongArnFormat"],
)
@pytest.mark.parametrize("value", ["enabled", "disabled"])
def test_put_account_setting(name, value):
    client = boto3.client("ecs", region_name="eu-west-1")

    resp = client.put_account_setting(name=name, value=value)
    assert resp["setting"] == {"name": name, "value": value}


@mock_aws
def test_list_account_setting():
    client = boto3.client("ecs", region_name="eu-west-1")

    client.put_account_setting(name="containerInstanceLongArnFormat", value="enabled")
    client.put_account_setting(name="serviceLongArnFormat", value="disabled")
    client.put_account_setting(name="taskLongArnFormat", value="enabled")

    resp = client.list_account_settings()
    assert len(resp["settings"]) == 3
    assert {"name": "containerInstanceLongArnFormat", "value": "enabled"} in resp[
        "settings"
    ]
    assert {"name": "serviceLongArnFormat", "value": "disabled"} in resp["settings"]
    assert {"name": "taskLongArnFormat", "value": "enabled"} in resp["settings"]

    resp = client.list_account_settings(name="serviceLongArnFormat")
    assert len(resp["settings"]) == 1
    assert {"name": "serviceLongArnFormat", "value": "disabled"} in resp["settings"]

    resp = client.list_account_settings(value="enabled")
    assert len(resp["settings"]) == 2
    assert {"name": "containerInstanceLongArnFormat", "value": "enabled"} in resp[
        "settings"
    ]
    assert {"name": "taskLongArnFormat", "value": "enabled"} in resp["settings"]


@mock_aws
def test_list_account_settings_wrong_name():
    client = boto3.client("ecs", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.list_account_settings(name="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "unknown should be one of [serviceLongArnFormat,taskLongArnFormat,containerInstanceLongArnFormat,containerLongArnFormat,awsvpcTrunking,containerInsights,dualStackIPv6]"
    )


@mock_aws
def test_delete_account_setting():
    client = boto3.client("ecs", region_name="eu-west-1")

    client.put_account_setting(name="containerInstanceLongArnFormat", value="enabled")
    client.put_account_setting(name="serviceLongArnFormat", value="enabled")
    client.put_account_setting(name="taskLongArnFormat", value="enabled")

    resp = client.list_account_settings()
    assert len(resp["settings"]) == 3

    client.delete_account_setting(name="serviceLongArnFormat")

    resp = client.list_account_settings()
    assert len(resp["settings"]) == 2
    assert {"name": "containerInstanceLongArnFormat", "value": "enabled"} in resp[
        "settings"
    ]
    assert {"name": "taskLongArnFormat", "value": "enabled"} in resp["settings"]


@mock_aws
def test_put_account_setting_changes_service_arn():
    client = boto3.client("ecs", region_name="eu-west-1")
    client.put_account_setting(name="serviceLongArnFormat", value="disabled")

    _ = client.create_cluster(clusterName="dummy-cluster")
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
    client.create_service(
        cluster="dummy-cluster",
        serviceName="test-ecs-service",
        taskDefinition="test_ecs_task",
        desiredCount=2,
        launchType="FARGATE",
        tags=[{"key": "ResourceOwner", "value": "Dummy"}],
    )

    # Initial response is short (setting serviceLongArnFormat=disabled)
    response = client.list_services(cluster="dummy-cluster", launchType="FARGATE")
    service_arn = response["serviceArns"][0]
    assert service_arn == f"arn:aws:ecs:eu-west-1:{ACCOUNT_ID}:service/test-ecs-service"

    # Second invocation returns long ARN's by default, after deleting the preference
    client.delete_account_setting(name="serviceLongArnFormat")
    response = client.list_services(cluster="dummy-cluster", launchType="FARGATE")
    service_arn = response["serviceArns"][0]
    assert (
        service_arn
        == f"arn:aws:ecs:eu-west-1:{ACCOUNT_ID}:service/dummy-cluster/test-ecs-service"
    )


@mock_aws
def test_put_account_setting_changes_containerinstance_arn():
    ecs_client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    test_cluster_name = "test_ecs_cluster"

    ecs_client.create_cluster(clusterName=test_cluster_name)

    test_instance = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    # Initial ARN should be long
    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )
    full_arn = response["containerInstance"]["containerInstanceArn"]
    assert full_arn.startswith(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance/{test_cluster_name}/"
    )

    # Now disable long-format
    ecs_client.put_account_setting(
        name="containerInstanceLongArnFormat", value="disabled"
    )
    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )
    full_arn = response["containerInstance"]["containerInstanceArn"]
    assert full_arn.startswith(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance/"
    )


@mock_aws
def test_run_task_default_cluster_new_arn_format():
    client = boto3.client("ecs", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

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
    # Initial ARN is long-format
    client.put_account_setting(name="taskLongArnFormat", value="enabled")
    response = client.run_task(
        launchType="FARGATE",
        overrides={},
        taskDefinition="test_ecs_task",
        count=1,
        startedBy="moto",
    )
    assert response["tasks"][0]["taskArn"].startswith(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/{test_cluster_name}/"
    )

    # Enable short-format for the next task
    client.put_account_setting(name="taskLongArnFormat", value="disabled")
    response = client.run_task(
        launchType="FARGATE",
        overrides={},
        taskDefinition="test_ecs_task",
        count=1,
        startedBy="moto",
    )
    assert response["tasks"][0]["taskArn"].startswith(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/"
    )
