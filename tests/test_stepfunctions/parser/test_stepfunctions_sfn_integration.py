import json
from time import sleep
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest

from moto import settings

from . import allow_aws_request, aws_verified, sfn_role_policy

sfn_allow_start_execution = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "states:StartExecution",
                "states:DescribeExecution",
                "states:StopExecution",
                "events:PutTargets",
                "events:PutRule",
                "events:DescribeRule",
            ],
            "Resource": "*",
        }
    ],
}


@aws_verified
@pytest.mark.aws_verified
def test_state_machine_calling_child_state_machine():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Don't need to test this in ServerMode")

    # https://github.com/getmoto/moto/issues/10076
    # The states:startExecution.sync:2 integration used to fail with
    # KeyError: 'Input', because the PascalCase ASL parameters were not
    # converted to the casing of the boto operation members.
    iam = boto3.client("iam", region_name="us-east-1")
    role_name = f"sfn_role_{str(uuid4())[0:6]}"
    sfn_role = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(sfn_role_policy),
        Path="/",
    )["Role"]["Arn"]
    iam.put_role_policy(
        PolicyDocument=json.dumps(sfn_allow_start_execution),
        PolicyName="allowStartExecution",
        RoleName=role_name,
    )

    client = boto3.client("stepfunctions", region_name="us-east-1")
    child_name = f"sfn_child_{str(uuid4())[0:6]}"
    child_arn = client.create_state_machine(
        name=child_name,
        definition=json.dumps(
            {"StartAt": "P", "States": {"P": {"Type": "Pass", "End": True}}}
        ),
        roleArn=sfn_role,
    )["stateMachineArn"]

    parent_name = f"sfn_parent_{str(uuid4())[0:6]}"
    parent_arn = client.create_state_machine(
        name=parent_name,
        definition=json.dumps(
            {
                "StartAt": "CallChild",
                "States": {
                    "CallChild": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::states:startExecution.sync:2",
                        "Parameters": {
                            "Input": {"foo": "bar"},
                            "StateMachineArn": child_arn,
                        },
                        "End": True,
                    }
                },
            }
        ),
        roleArn=sfn_role,
    )["stateMachineArn"]

    try:
        execution_arn = client.start_execution(
            name="run1", stateMachineArn=parent_arn, input="{}"
        )["executionArn"]

        execution = None
        for _ in range(30):
            execution = client.describe_execution(executionArn=execution_arn)
            if execution["status"] != "RUNNING":
                break
            sleep(10 if allow_aws_request() else 0.2)
        assert execution["status"] == "SUCCEEDED"

        # The task result of a .sync:2 integration contains the (parsed)
        # output of the child execution
        output = json.loads(execution["output"])
        assert output["Output"] == {"foo": "bar"}
    finally:
        for arn in [parent_arn, child_arn]:
            for exc in client.list_executions(stateMachineArn=arn)["executions"]:
                if exc["status"] == "RUNNING":
                    client.stop_execution(executionArn=exc["executionArn"])
            client.delete_state_machine(stateMachineArn=arn)
        iam.delete_role_policy(RoleName=role_name, PolicyName="allowStartExecution")
        iam.delete_role(RoleName=role_name)
