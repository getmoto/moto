import json
from uuid import uuid4

import boto3
import pytest

from moto import mock_aws
from tests.test_stepfunctions.test_stepfunctions import _get_default_role

state_machine_definition = {
    "StartAt": "HelloWorld",
    "States": {"HelloWorld": {"Type": "Pass", "Result": "Hello World!", "End": True}},
}


@pytest.mark.parametrize("mocked_sfn", [True, False], ids=["Mocked", "Parsed"])
def test_create_bucket_invokes_stepfunction(mocked_sfn):
    with mock_aws(config={"stepfunctions": {"execute_state_machine": mocked_sfn}}):
        create_bucket_invokes_stepfunction()


def create_bucket_invokes_stepfunction():
    sfn_client = boto3.client("stepfunctions", "us-east-1")
    response = sfn_client.create_state_machine(
        name=str(uuid4()),
        definition=json.dumps(state_machine_definition),
        roleArn=_get_default_role(),
    )
    state_machine_arn = response["stateMachineArn"]

    events_client = boto3.client("events", "us-east-1")
    s3_client = boto3.client("s3", "us-east-1")

    bucket_name = str(uuid4())

    events_client.put_rule(
        Name="rule_name",
        EventPattern="""{
                    "source": [
                        "aws.s3"
                    ],
                    "detail-type": [
                        "AWS API Call via CloudTrail"
                    ],
                    "detail": {
                        "eventSource": [
                            "s3.amazonaws.com"
                        ],
                        "eventName": [
                            "CreateBucket"
                        ]
                    }
                }""",
        State="ENABLED",
    )

    events_client.put_targets(
        Rule="rule_name",
        Targets=[{"Id": "n/a", "Arn": state_machine_arn}],
    )

    # Kick off Event
    s3_client.create_bucket(Bucket=bucket_name)

    # Verify SFN was invoked
    execs = sfn_client.list_executions(stateMachineArn=state_machine_arn)["executions"]
    assert len(execs) == 1

    # Verify the Execution Input is correct
    execution_arn = execs[0]["executionArn"]
    execution_details = sfn_client.describe_execution(executionArn=execution_arn)
    execution_input = json.loads(execution_details["input"])
    assert execution_input["source"] == "aws.s3"
    assert execution_input["detail-type"] == "Object Created"
    assert execution_input["resources"] == [f"arn:aws:s3:::{bucket_name}"]
