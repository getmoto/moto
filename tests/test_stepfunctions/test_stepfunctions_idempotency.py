import os
from unittest import SkipTest, mock

import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.stepfunctions.models import StepFunctionBackend, stepfunctions_backends
from tests import DEFAULT_ACCOUNT_ID

from .parser import (
    verify_execution_result,
)


@mock_aws
@mock.patch.dict(os.environ, {"SF_EXECUTION_HISTORY_TYPE": "FAILURE"})
def test_create_state_machine_twice_after_failure():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Don't need to test this in ServerMode")

    def _verify_result(client, execution, execution_arn):
        name = execution["name"]
        arn = execution["stateMachineArn"]
        execution_arn = execution["executionArn"]

        # Execution fails if we re-start it after failure
        with pytest.raises(ClientError) as exc:
            client.start_execution(name=name, stateMachineArn=arn)
        err = exc.value.response["Error"]
        assert err["Code"] == "ExecutionAlreadyExists"
        assert err["Message"] == f"Execution Already Exists: '{execution_arn}'"

    verify_execution_result(_verify_result, "FAILED", "failure")


@mock_aws
def test_create_state_machine_twice_after_success():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Don't need to test this in ServerMode")

    def _verify_result(client, execution, execution_arn):
        name = execution["name"]
        arn = execution["stateMachineArn"]
        execution_arn = execution["executionArn"]

        if execution["status"] == "RUNNING":
            # We can start the execution just fine
            idempotent = client.start_execution(name=name, stateMachineArn=arn)
            assert idempotent["executionArn"] == execution_arn

            # Manually mark our execution as finished
            # (Because we don't actually execute anything, the status is always 'RUNNING' if we don't do this manually)
            backend: StepFunctionBackend = stepfunctions_backends[DEFAULT_ACCOUNT_ID][
                "us-east-1"
            ]
            machine = backend.describe_state_machine(arn)
            execution = next(
                (x for x in machine.executions if x.execution_arn == execution_arn),
                None,
            )
            execution.status = "SUCCEEDED"

            # We're not done yet - we should check in on the progress later
            return False
        elif execution["status"] == "SUCCEEDED":
            # Execution fails if we re-start it after it finishes
            with pytest.raises(ClientError) as exc:
                client.start_execution(name=name, stateMachineArn=arn)
            err = exc.value.response["Error"]
            assert err["Code"] == "ExecutionAlreadyExists"
            assert err["Message"] == f"Execution Already Exists: '{execution_arn}'"

            # Execution finished, and we verified our error exception
            # Return True to indicate we can tear down our StateMachine
            return True

    verify_execution_result(_verify_result, None, tmpl_name="wait_1")
