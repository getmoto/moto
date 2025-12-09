from unittest import SkipTest

import pytest
from botocore.exceptions import ClientError

from moto import settings

from . import (
    allow_aws_request,
    aws_verified,
    verify_execution_result,
)


@aws_verified
@pytest.mark.aws_verified
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


@aws_verified
@pytest.mark.aws_verified
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

    # AWS is a little slower, so we need to wait longer
    # If we only wait 1 second, our execution might finish before we can retry it
    tmpl_name = "wait_15" if allow_aws_request() else "wait_1"
    verify_execution_result(_verify_result, None, tmpl_name)
