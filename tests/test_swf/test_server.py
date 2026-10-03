import json

import pytest

from moto import mock_aws, server
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_0

MISSING_DOMAIN = "1 validation error detected: Value null at 'domain' failed to satisfy constraint: Member must not be null"
MISSING_EXECUTION = "1 validation error detected: Value null at 'execution' failed to satisfy constraint: Member must not be null"
MISSING_RUN_ID = "1 validation error detected: Value null at 'execution.runId' failed to satisfy constraint: Member must not be null"
MISSING_WORKFLOW_ID = "1 validation error detected: Value null at 'execution.workflowId' failed to satisfy constraint: Member must not be null"


def workflow_execution_request(operation, parameters):
    # Send JSON directly so botocore cannot reject or transform malformed parameters.
    client = server.create_backend_app("swf").test_client()
    return client.post(
        "/",
        headers={
            "X-Amz-Target": f"SimpleWorkflowService.{operation}",
            "Content-Type": APPLICATION_AMZ_JSON_1_0,
        },
        json=parameters,
    )


@mock_aws
@pytest.mark.parametrize(
    "operation", ["DescribeWorkflowExecution", "GetWorkflowExecutionHistory"]
)
@pytest.mark.parametrize(
    "parameters,message",
    [
        pytest.param(
            {},
            "2 validation errors detected: Value null at 'execution' failed to satisfy constraint: Member must not be null; Value null at 'domain' failed to satisfy constraint: Member must not be null",
            id="missing-domain-and-execution",
        ),
        pytest.param(
            {"domain": "test-domain"}, MISSING_EXECUTION, id="missing-execution"
        ),
        pytest.param(
            {"execution": {"runId": "run-id", "workflowId": "workflow-id"}},
            MISSING_DOMAIN,
            id="missing-domain",
        ),
        pytest.param(
            {
                "domain": None,
                "execution": {"runId": "run-id", "workflowId": "workflow-id"},
            },
            MISSING_DOMAIN,
            id="null-domain",
        ),
        *[
            pytest.param(
                {"domain": "test-domain", "execution": execution}, message, id=name
            )
            for name, execution, message in [
                ("missing-run-id", {"workflowId": "workflow-id"}, MISSING_RUN_ID),
                ("missing-workflow-id", {"runId": "run-id"}, MISSING_WORKFLOW_ID),
                (
                    "empty-execution",
                    {},
                    "2 validation errors detected: Value null at 'execution.runId' failed to satisfy constraint: Member must not be null; Value null at 'execution.workflowId' failed to satisfy constraint: Member must not be null",
                ),
                ("null-execution", None, MISSING_EXECUTION),
                (
                    "null-run-id",
                    {"runId": None, "workflowId": "workflow-id"},
                    MISSING_RUN_ID,
                ),
                (
                    "null-workflow-id",
                    {"runId": "run-id", "workflowId": None},
                    MISSING_WORKFLOW_ID,
                ),
            ]
        ],
    ],
)
def test_workflow_execution_missing_parameters(operation, parameters, message):
    # Status, error type, and messages verified against AWS SWF on 2026-09-17.
    response = workflow_execution_request(operation, parameters)

    assert response.status_code == 400
    assert json.loads(response.data) == {
        "__type": "com.amazon.coral.validate#ValidationException",
        "message": message,
    }


@mock_aws
@pytest.mark.parametrize(
    "operation", ["DescribeWorkflowExecution", "GetWorkflowExecutionHistory"]
)
@pytest.mark.parametrize(
    "domain,execution",
    [
        pytest.param(
            123,
            {"runId": "run-id", "workflowId": "workflow-id"},
            id="non-string-domain",
        ),
        pytest.param("test-domain", "invalid", id="string-execution"),
        pytest.param("test-domain", [], id="list-execution"),
        pytest.param("test-domain", 123, id="number-execution"),
        pytest.param(
            "test-domain",
            {"runId": 123, "workflowId": "workflow-id"},
            id="non-string-run-id",
        ),
        pytest.param(
            "test-domain",
            {"runId": "run-id", "workflowId": []},
            id="non-string-workflow-id",
        ),
    ],
)
def test_workflow_execution_invalid_parameter_types(operation, domain, execution):
    response = workflow_execution_request(
        operation, {"domain": domain, "execution": execution}
    )

    assert response.status_code == 400
    assert json.loads(response.data)["__type"] == (
        "com.amazonaws.swf.base.model#SerializationException"
    )
