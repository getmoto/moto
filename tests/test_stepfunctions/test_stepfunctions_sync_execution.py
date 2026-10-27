import json
import os
from unittest import SkipTest, mock

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError

from moto import mock_aws, settings

REGION = "us-east-1"
PASS_DEFINITION = json.dumps(
    {
        "StartAt": "P",
        "States": {"P": {"Type": "Pass", "Result": {"ok": True}, "End": True}},
    }
)


def _client():
    # StartSyncExecution's endpoint has the host prefix "sync-"; in ServerMode
    # that would turn localhost into sync-localhost.
    kwargs = {}
    if settings.TEST_SERVER_MODE:
        kwargs["config"] = Config(inject_host_prefix=False)
    return boto3.client("stepfunctions", region_name=REGION, **kwargs)


def _role_arn():
    return "arn:aws:iam::123456789012:role/unknown_sf_role"


def _create(client, sm_type):
    return client.create_state_machine(
        name=f"sm-{sm_type.lower()}",
        definition=PASS_DEFINITION,
        roleArn=_role_arn(),
        type=sm_type,
    )["stateMachineArn"]


@mock_aws
def test_start_sync_execution_on_express_state_machine():
    client = _client()
    sm_arn = _create(client, "EXPRESS")

    resp = client.start_sync_execution(
        stateMachineArn=sm_arn, name="run-1", input='{"a": 1}'
    )

    assert resp["status"] == "SUCCEEDED"
    assert resp["stateMachineArn"] == sm_arn
    assert resp["name"] == "run-1"
    assert resp["executionArn"].startswith(
        "arn:aws:states:us-east-1:123456789012:express:sm-express:run-1:"
    )
    assert json.loads(resp["input"]) == {"a": 1}
    assert resp["stopDate"] >= resp["startDate"]


@mock_aws
def test_start_sync_execution_generates_a_name():
    client = _client()
    sm_arn = _create(client, "EXPRESS")

    resp = client.start_sync_execution(stateMachineArn=sm_arn)

    assert resp["name"]
    assert json.loads(resp["input"]) == {}


@mock_aws
def test_start_sync_execution_rejects_standard_state_machine():
    client = _client()
    sm_arn = _create(client, "STANDARD")

    with pytest.raises(ClientError) as exc:
        client.start_sync_execution(stateMachineArn=sm_arn)

    assert exc.value.response["Error"]["Code"] == "StateMachineTypeNotSupported"


@mock_aws
def test_start_sync_execution_on_unknown_state_machine():
    client = _client()
    unknown = "arn:aws:states:us-east-1:123456789012:stateMachine:does-not-exist"

    with pytest.raises(ClientError) as exc:
        client.start_sync_execution(stateMachineArn=unknown)

    assert exc.value.response["Error"]["Code"] == "StateMachineDoesNotExist"


@mock_aws
def test_start_sync_execution_follows_the_configured_failure_outcome():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    client = _client()
    sm_arn = _create(client, "EXPRESS")

    with mock.patch.dict(os.environ, {"SF_EXECUTION_HISTORY_TYPE": "FAILURE"}):
        resp = client.start_sync_execution(stateMachineArn=sm_arn)

    assert resp["status"] == "FAILED"
