from botocore.exceptions import ClientError
import boto3
import sure  # noqa # pylint: disable=unused-import
import json

from moto.core import ACCOUNT_ID
from moto.ec2 import utils as ec2_utils

from moto import mock_ecs, mock_ec2
import pytest
from tests import EXAMPLE_AMI_ID


@mock_ecs
def test_list_account_settings_initial():
    client = boto3.client("ecs", region_name="eu-west-1")

    resp = client.list_account_settings()
    resp.should.have.key("settings").equal([])


@mock_ecs
@pytest.mark.parametrize(
    "name",
    ["containerInstanceLongArnFormat", "serviceLongArnFormat", "taskLongArnFormat"],
)
@pytest.mark.parametrize("value", ["enabled", "disabled"])
def test_put_account_setting(name, value):
    client = boto3.client("ecs", region_name="eu-west-1")

    resp = client.put_account_setting(name=name, value=value)
    resp.should.have.key("setting")
    resp["setting"].should.equal({"name": name, "value": value})


@mock_ecs
def test_list_account_setting():
    client = boto3.client("ecs", region_name="eu-west-1")

    client.put_account_setting(name="containerInstanceLongArnFormat", value="enabled")
    client.put_account_setting(name="serviceLongArnFormat", value="disabled")
    client.put_account_setting(name="taskLongArnFormat", value="enabled")

    resp = client.list_account_settings()
    resp.should.have.key("settings").length_of(3)
    resp["settings"].should.contain(
        {"name": "containerInstanceLongArnFormat", "value": "enabled"}
    )
    resp["settings"].should.contain(
        {"name": "serviceLongArnFormat", "value": "disabled"}
    )
    resp["settings"].should.contain({"name": "taskLongArnFormat", "value": "enabled"})

    resp = client.list_account_settings(name="serviceLongArnFormat")
    resp.should.have.key("settings").length_of(1)
    resp["settings"].should.contain(
        {"name": "serviceLongArnFormat", "value": "disabled"}
    )

    resp = client.list_account_settings(value="enabled")
    resp.should.have.key("settings").length_of(2)
    resp["settings"].should.contain(
        {"name": "containerInstanceLongArnFormat", "value": "enabled"}
    )
    resp["settings"].should.contain({"name": "taskLongArnFormat", "value": "enabled"})


@mock_ecs
def test_list_account_settings_wrong_name():
    client = boto3.client("ecs", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.list_account_settings(name="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterException")
    err["Message"].should.equal(
        "unknown should be one of [serviceLongArnFormat,taskLongArnFormat,containerInstanceLongArnFormat,containerLongArnFormat,awsvpcTrunking,containerInsights,dualStackIPv6]"
    )


@mock_ecs
def test_delete_account_setting():
    client = boto3.client("ecs", region_name="eu-west-1")

    client.put_account_setting(name="containerInstanceLongArnFormat", value="enabled")
    client.put_account_setting(name="serviceLongArnFormat", value="enabled")
    client.put_account_setting(name="taskLongArnFormat", value="enabled")

    resp = client.list_account_settings()
    resp.should.have.key("settings").length_of(3)

    client.delete_account_setting(name="serviceLongArnFormat")

    resp = client.list_account_settings()
    resp.should.have.key("settings").length_of(2)
    resp["settings"].should.contain(
        {"name": "containerInstanceLongArnFormat", "value": "enabled"}
    )
    resp["settings"].should.contain({"name": "taskLongArnFormat", "value": "enabled"})


@mock_ec2
@mock_ecs
def test_put_account_setting_changes_service_arn():
    client = boto3.client("ecs", region_name="eu-west-1")
    client.put_account_setting(name="serviceLongArnFormat", value="enabled")

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

    # Initial response is long
    response = client.list_services(cluster="dummy-cluster", launchType="FARGATE")
    service_arn = response["serviceArns"][0]
    service_arn.should.equal(
        "arn:aws:ecs:eu-west-1:{}:service/dummy-cluster/test-ecs-service".format(
            ACCOUNT_ID
        )
    )

    # Second invocation returns short ARN's, after deleting the longArn-preference
    client.delete_account_setting(name="serviceLongArnFormat")
    response = client.list_services(cluster="dummy-cluster", launchType="FARGATE")
    service_arn = response["serviceArns"][0]
    service_arn.should.equal(
        "arn:aws:ecs:eu-west-1:{}:service/test-ecs-service".format(ACCOUNT_ID)
    )


@mock_ec2
@mock_ecs
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

    # Initial ARN should be short
    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )
    full_arn = response["containerInstance"]["containerInstanceArn"]
    full_arn.should.match(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance/[a-z0-9-]+$"
    )

    # Now enable long-format
    ecs_client.put_account_setting(
        name="containerInstanceLongArnFormat", value="enabled"
    )
    response = ecs_client.register_container_instance(
        cluster=test_cluster_name, instanceIdentityDocument=instance_id_document
    )
    full_arn = response["containerInstance"]["containerInstanceArn"]
    full_arn.should.match(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:container-instance/{test_cluster_name}/[a-z0-9-]+$"
    )


@mock_ec2
@mock_ecs
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
    # Initial ARN is short-format
    client.put_account_setting(name="taskLongArnFormat", value="disabled")
    response = client.run_task(
        launchType="FARGATE",
        overrides={},
        taskDefinition="test_ecs_task",
        count=1,
        startedBy="moto",
    )
    response["tasks"][0]["taskArn"].should.match(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/[a-z0-9-]+$"
    )

    # Enable long-format for the next task
    client.put_account_setting(name="taskLongArnFormat", value="enabled")
    response = client.run_task(
        launchType="FARGATE",
        overrides={},
        taskDefinition="test_ecs_task",
        count=1,
        startedBy="moto",
    )
    response["tasks"][0]["taskArn"].should.match(
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task/{test_cluster_name}/[a-z0-9-]+$"
    )
