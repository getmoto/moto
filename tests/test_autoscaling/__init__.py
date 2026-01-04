from contextlib import nullcontext
from functools import wraps
from uuid import uuid4

import boto3
import pytest

from moto import mock_aws
from tests import allow_aws_request

pytest.register_assert_rewrite("tests.test_ec2.helpers")


def autoscaling_aws_verified(
    create_auto_scaling_group: bool = False,
    get_group_name: bool = False,
    wait_for_instance_termination: bool = True,
):
    def inner(func):
        @wraps(func)
        def pagination_wrapper(**kwargs):
            context = nullcontext() if allow_aws_request() else mock_aws()

            with context:
                return _invoke_func(
                    create_auto_scaling_group=create_auto_scaling_group,
                    get_group_name=get_group_name,
                    wait_for_instance_termination=wait_for_instance_termination,
                    func=func,
                    kwargs=kwargs,
                )

        return pagination_wrapper

    return inner


def _invoke_func(
    create_auto_scaling_group: bool,
    get_group_name: bool,
    wait_for_instance_termination: bool,
    func,
    kwargs,
):
    autoscaling_client = boto3.client("autoscaling", "us-east-1")
    kwargs["autoscaling_client"] = autoscaling_client

    autoscaling_group_name = None
    if create_auto_scaling_group:
        # TODO - actually create one
        autoscaling_group_name = str(uuid4())
        kwargs["autoscaling_group_name"] = autoscaling_group_name
    elif get_group_name:
        # User will create it - let's still create a name, so we can delete it for them
        autoscaling_group_name = str(uuid4())
        kwargs["autoscaling_group_name"] = autoscaling_group_name

    try:
        func(**kwargs)
    finally:
        if autoscaling_group_name:
            groups = autoscaling_client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[autoscaling_group_name]
            )["AutoScalingGroups"]

            if not groups:
                # group was never created in the first place
                pass
            else:
                group = groups[0]
                autoscaling_client.delete_auto_scaling_group(
                    AutoScalingGroupName=autoscaling_group_name,
                    # Delete underlying instances as well
                    ForceDelete=True,
                )

                if wait_for_instance_termination:
                    ec2_client = boto3.client("ec2", "us-east-1")
                    waiter = ec2_client.get_waiter("instance_terminated")
                    waiter.wait(
                        # Delay to get around https://github.com/boto/boto3/issues/176
                        WaiterConfig={"Delay": 10},
                        InstanceIds=[inst["InstanceId"] for inst in group["Instances"]],
                    )
