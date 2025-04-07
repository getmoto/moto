from contextlib import nullcontext
from functools import wraps
from uuid import uuid4

import boto3

from moto import mock_aws
from tests import allow_aws_request


def ec2_aws_verified(
    create_vpc: bool = False,
    create_sg: bool = False,
):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.

    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper(**kwargs):
            context = nullcontext() if allow_aws_request() else mock_aws()

            with context:
                return _invoke_func(create_vpc, create_sg, func=func, kwargs=kwargs)

        return pagination_wrapper

    return inner


def _invoke_func(create_vpc: bool, create_sg: bool, func, kwargs):
    ec2_client = boto3.client("ec2", "us-east-1")
    kwargs["ec2_client"] = ec2_client

    vpc_id = sg_id = None
    if create_vpc:
        vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/24")
        vpc_id = vpc["Vpc"]["VpcId"]
        kwargs["vpc_id"] = vpc_id

    if create_sg:
        sg_name = f"test_{str(uuid4())[0:6]}"
        sg = ec2_client.create_security_group(
            Description="test", GroupName=sg_name, VpcId=vpc_id
        )
        sg_id = sg["GroupId"]
        kwargs["sg_id"] = sg_id

    try:
        func(**kwargs)
    finally:
        if sg_id:
            ec2_client.delete_security_group(GroupId=sg_id)
        if vpc_id:
            ec2_client.delete_vpc(VpcId=vpc_id)
