import json
from unittest import SkipTest

import boto3

from moto import mock_aws, settings

REGION = "us-east-1"
ROLE_ARN = "arn:aws:iam::123456789012:role/unknown_sf_role"


def _express(client, definition):
    return client.create_state_machine(
        name="sync-sm",
        definition=json.dumps(definition),
        roleArn=ROLE_ARN,
        type="EXPRESS",
    )["stateMachineArn"]


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_start_sync_execution_returns_the_state_machine_output():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this in ServerMode")
    client = boto3.client("stepfunctions", region_name=REGION)
    sm_arn = _express(
        client,
        {
            "StartAt": "Greet",
            "States": {
                "Greet": {
                    "Type": "Pass",
                    "Parameters": {"greeting.$": "States.Format('Hello, {}', $.name)"},
                    "End": True,
                }
            },
        },
    )

    resp = client.start_sync_execution(stateMachineArn=sm_arn, input='{"name": "Hien"}')

    assert resp["status"] == "SUCCEEDED"
    assert json.loads(resp["output"]) == {"greeting": "Hello, Hien"}
    assert json.loads(resp["input"]) == {"name": "Hien"}


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_start_sync_execution_reports_a_failed_state():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this in ServerMode")
    client = boto3.client("stepfunctions", region_name=REGION)
    sm_arn = _express(
        client,
        {
            "StartAt": "F",
            "States": {"F": {"Type": "Fail", "Error": "Boom", "Cause": "always fails"}},
        },
    )

    resp = client.start_sync_execution(stateMachineArn=sm_arn)

    assert resp["status"] == "FAILED"
    assert resp["error"] == "Boom"
    assert resp["cause"] == "always fails"
    assert "output" not in resp
