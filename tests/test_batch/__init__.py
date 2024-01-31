from typing import Any, Tuple
from uuid import uuid4

import boto3

DEFAULT_REGION = "eu-central-1"


def _get_clients() -> Tuple[Any, Any, Any, Any, Any]:
    return (
        boto3.client("ec2", region_name=DEFAULT_REGION),
        boto3.client("iam", region_name=DEFAULT_REGION),
        boto3.client("ecs", region_name=DEFAULT_REGION),
        boto3.client("logs", region_name=DEFAULT_REGION),
        boto3.client("batch", region_name=DEFAULT_REGION),
    )


def _setup(ec2_client: Any, iam_client: Any) -> Tuple[str, str, str, str]:
    """
    Do prerequisite setup
    :return: VPC ID, Subnet ID, Security group ID, IAM Role ARN
    :rtype: tuple
    """
    resp = ec2_client.create_vpc(CidrBlock="172.30.0.0/24")
    vpc_id = resp["Vpc"]["VpcId"]
    resp = ec2_client.create_subnet(
        AvailabilityZone="eu-central-1a", CidrBlock="172.30.0.0/25", VpcId=vpc_id
    )
    subnet_id = resp["Subnet"]["SubnetId"]
    resp = ec2_client.create_security_group(
        Description="test_sg_desc", GroupName=str(uuid4())[0:6], VpcId=vpc_id
    )
    sg_id = resp["GroupId"]

    role_name = f"{str(uuid4())[0:6]}"
    resp = iam_client.create_role(
        RoleName=role_name, AssumeRolePolicyDocument="some_policy"
    )
    iam_arn = resp["Role"]["Arn"]
    iam_client.create_instance_profile(InstanceProfileName=role_name)
    iam_client.add_role_to_instance_profile(
        InstanceProfileName=role_name, RoleName=role_name
    )

    return vpc_id, subnet_id, sg_id, iam_arn
