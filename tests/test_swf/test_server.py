import json

import pytest

from moto import mock_aws, server
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_0


@mock_aws
@pytest.mark.parametrize(
    "operation", ["DescribeWorkflowExecution", "GetWorkflowExecutionHistory"]
)
@pytest.mark.parametrize(
    "parameters",
    [
        pytest.param({}, id="missing-domain-and-execution"),
        pytest.param({"domain": "test-domain"}, id="missing-execution"),
        pytest.param(
            {"execution": {"runId": "run-id", "workflowId": "workflow-id"}},
            id="missing-domain",
        ),
        pytest.param(
            {
                "domain": None,
                "execution": {"runId": "run-id", "workflowId": "workflow-id"},
            },
            id="null-domain",
        ),
        pytest.param(
            {
                "domain": 123,
                "execution": {"runId": "run-id", "workflowId": "workflow-id"},
            },
            id="non-string-domain",
        ),
        *[
            pytest.param({"domain": "test-domain", "execution": execution}, id=name)
            for name, execution in [
                ("missing-run-id", {"workflowId": "workflow-id"}),
                ("missing-workflow-id", {"runId": "run-id"}),
                ("empty-execution", {}),
                ("null-execution", None),
                ("string-execution", "invalid"),
                ("list-execution", []),
                ("number-execution", 123),
                ("null-run-id", {"runId": None, "workflowId": "workflow-id"}),
                ("null-workflow-id", {"runId": "run-id", "workflowId": None}),
                ("non-string-run-id", {"runId": 123, "workflowId": "workflow-id"}),
                ("non-string-workflow-id", {"runId": "run-id", "workflowId": []}),
            ]
        ],
    ],
)
def test_workflow_execution_invalid_parameters(operation, parameters):
    # Send JSON directly so botocore cannot reject or transform malformed parameters.
    client = server.create_backend_app("swf").test_client()
    response = client.post(
        "/",
        headers={
            "X-Amz-Target": f"SimpleWorkflowService.{operation}",
            "Content-Type": APPLICATION_AMZ_JSON_1_0,
        },
        json=parameters,
    )

    assert response.status_code == 400
    assert json.loads(response.data)["__type"] == (
        "com.amazonaws.swf.base.model#SerializationException"
    )
