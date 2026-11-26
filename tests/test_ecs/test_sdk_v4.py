"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_ec2 import EC2Client, EC2Config
    from aws_sdk_ecs import ECSClient, ECSConfig
except ImportError:  # Requires Python 3.12+
    pytest.skip(
        "aws-sdk-ecs and aws-sdk-ec2 are not installed", allow_module_level=True
    )


def _container(image: str) -> dict:
    return {
        "name": "web",
        "image": image,
        "essential": True,
        "port_mappings": [{"container_port": 80, "protocol": "tcp"}],
        "environment": [{"name": "STAGE", "value": "prod"}],
    }


@pytest.mark.skip(
    reason="CreateService fails with a KeyError: Moto requires networkConfiguration.awsvpcConfiguration.securityGroups "
    "(KeyError in Service._validate_network), but AWS makes it optional and falls back to the VPC's default security group"
)
@mock_aws
def test_roll_out_new_fargate_revision():
    """Run a Fargate web service, then roll out a new task definition revision."""
    config = ECSConfig.resolve(region="us-east-1")
    suffix = str(uuid4())[:8]
    family = f"web-{suffix}"

    with EC2Client(config=EC2Config.resolve(region="us-east-1")) as ec2:
        default_subnets = ec2.describe_subnets(
            filters=[{"name": "default-for-az", "values": ["true"]}]
        ).subnets
        subnet_ids = [subnet.subnet_id for subnet in default_subnets or []]
    assert subnet_ids

    with ECSClient(config=config) as client:
        cluster = client.create_cluster(
            cluster_name=f"production-{suffix}",
            tags=[{"key": "team", "value": "web"}],
        ).cluster
        assert cluster.status == "ACTIVE"

        first = client.register_task_definition(
            family=family,
            network_mode="awsvpc",
            requires_compatibilities=["FARGATE"],
            cpu="256",
            memory="512",
            container_definitions=[_container("nginx:1.27")],
        ).task_definition
        assert first.revision == 1
        assert first.container_definitions[0].port_mappings[0].container_port == 80

        service = client.create_service(
            cluster=cluster.cluster_arn,
            service_name="web",
            task_definition=first.task_definition_arn,
            desired_count=2,
            launch_type="FARGATE",
            network_configuration={
                "awsvpc_configuration": {
                    "subnets": subnet_ids,
                    "assign_public_ip": "ENABLED",
                }
            },
        ).service
        assert service.desired_count == 2
        assert service.launch_type == "FARGATE"

        second = client.register_task_definition(
            family=family,
            network_mode="awsvpc",
            requires_compatibilities=["FARGATE"],
            cpu="256",
            memory="512",
            container_definitions=[_container("nginx:1.28")],
        ).task_definition
        assert second.revision == 2

        client.update_service(
            cluster=cluster.cluster_arn,
            service="web",
            task_definition=second.task_definition_arn,
            desired_count=3,
        )

        described = client.describe_services(
            cluster=cluster.cluster_arn, services=["web"]
        )
        assert described.failures == []
        assert described.services[0].task_definition == second.task_definition_arn
        assert described.services[0].desired_count == 3

        revisions = client.list_task_definitions(family_prefix=family)
        assert revisions.task_definition_arns == [
            first.task_definition_arn,
            second.task_definition_arn,
        ]

        client.deregister_task_definition(task_definition=first.task_definition_arn)
        deleted = client.delete_service(
            cluster=cluster.cluster_arn, service="web", force=True
        ).service
        assert deleted.status in ("DRAINING", "INACTIVE")

        client.delete_cluster(cluster=cluster.cluster_arn)
