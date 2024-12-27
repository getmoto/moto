import json
from uuid import uuid4

import boto3
import pytest

from moto import mock_aws
from tests.test_stepfunctions.parser import sfn_role_policy
from tests.test_stepfunctions.test_stepfunctions import simple_definition


@pytest.mark.parametrize("use_parser", [True, False], ids=["use_parser", "use_mock"])
def test_describe_state_machine_using_version_arn(use_parser):
    with mock_aws(config={"stepfunctions": {"execute_state_machine": use_parser}}):
        iam = boto3.client("iam", region_name="us-east-1")
        role_name = f"sfn_role_{str(uuid4())[0:6]}"
        sfn_role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(sfn_role_policy),
            Path="/",
        )["Role"]["Arn"]

        client = boto3.client("stepfunctions", region_name="us-east-1")

        name1 = f"sfn_name_{str(uuid4())[0:6]}"
        response = client.create_state_machine(
            name=name1, definition=simple_definition, roleArn=sfn_role, publish=True
        )
        arn = response["stateMachineArn"]
        version_arn1 = response["stateMachineVersionArn"]

        # Use the initial version to describe the state machine
        version1 = client.describe_state_machine(stateMachineArn=version_arn1)
        assert version1["loggingConfiguration"] == {"level": "OFF"}

        # Update the state machine
        update = client.update_state_machine(
            stateMachineArn=arn,
            loggingConfiguration={"level": "ALL"},
            publish=True,
        )
        version_arn2 = update["stateMachineVersionArn"]
        assert version_arn1 != version_arn2

        # Assert that we can retrieve the latest configuration, either by the regular ARN or by the version ARN
        latest = client.describe_state_machine(stateMachineArn=arn)
        assert latest["loggingConfiguration"] == {"level": "ALL"}
        version2 = client.describe_state_machine(stateMachineArn=version_arn2)
        assert version2["loggingConfiguration"] == {"level": "ALL"}

        # Assert that we can still describe the first version of the state machine
        version1 = client.describe_state_machine(stateMachineArn=version_arn1)
        assert version1["loggingConfiguration"] == {"level": "OFF"}
