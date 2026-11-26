"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_ec2 import EC2Client, EC2Config
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-ec2 is not installed", allow_module_level=True)

from tests import EXAMPLE_AMI_ID


@mock_aws
def test_launch_web_server_in_new_vpc():
    """Create a VPC with a subnet and security group, and launch a web server in it."""
    app = f"web-{uuid4().hex[:8]}"

    with EC2Client(config=EC2Config.resolve(region="us-east-1")) as client:
        vpc = client.create_vpc(
            cidr_block="10.0.0.0/16",
            tag_specifications=[
                {"resource_type": "vpc", "tags": [{"key": "app", "value": app}]}
            ],
        ).vpc
        assert vpc.vpc_id.startswith("vpc-")
        assert vpc.cidr_block == "10.0.0.0/16"

        subnet = client.create_subnet(
            vpc_id=vpc.vpc_id, cidr_block="10.0.1.0/24", availability_zone="us-east-1a"
        ).subnet
        assert subnet.vpc_id == vpc.vpc_id
        assert subnet.availability_zone == "us-east-1a"

        group_id = client.create_security_group(
            group_name=f"{app}-sg", description="Allow HTTPS", vpc_id=vpc.vpc_id
        ).group_id
        client.authorize_security_group_ingress(
            group_id=group_id,
            ip_permissions=[
                {
                    "ip_protocol": "tcp",
                    "from_port": 443,
                    "to_port": 443,
                    "ip_ranges": [{"cidr_ip": "0.0.0.0/0", "description": "HTTPS"}],
                }
            ],
        )
        group = client.describe_security_groups(group_ids=[group_id]).security_groups[0]
        assert [(p.from_port, p.to_port) for p in group.ip_permissions] == [(443, 443)]
        assert group.ip_permissions[0].ip_ranges[0].cidr_ip == "0.0.0.0/0"

        key_pair = client.create_key_pair(key_name=f"{app}-key")
        assert key_pair.key_material.startswith("-----BEGIN RSA PRIVATE KEY-----")

        reservation = client.run_instances(
            image_id=EXAMPLE_AMI_ID,
            instance_type="t3.micro",
            min_count=2,
            max_count=2,
            key_name=key_pair.key_name,
            subnet_id=subnet.subnet_id,
            security_group_ids=[group_id],
            tag_specifications=[
                {"resource_type": "instance", "tags": [{"key": "app", "value": app}]}
            ],
        )
        instance_ids = sorted(i.instance_id for i in reservation.instances)
        assert len(instance_ids) == 2

        # Find the instances again by their tag
        described = client.describe_instances(
            filters=[{"name": "tag:app", "values": [app]}]
        )
        instances = [i for r in described.reservations for i in r.instances]
        assert sorted(i.instance_id for i in instances) == instance_ids
        for instance in instances:
            assert instance.state.name == "running"
            assert instance.instance_type == "t3.micro"
            assert instance.vpc_id == vpc.vpc_id
            assert instance.subnet_id == subnet.subnet_id
            assert instance.private_ip_address.startswith("10.0.1.")
            assert [g.group_id for g in instance.security_groups] == [group_id]

        stopped = client.stop_instances(instance_ids=instance_ids[:1])
        assert stopped.stopping_instances[0].current_state.name == "stopping"

        terminated = client.terminate_instances(instance_ids=instance_ids)
        assert {i.current_state.name for i in terminated.terminating_instances} == {
            "shutting-down"
        }
