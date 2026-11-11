import json

import boto3
import pytest

from moto import mock_aws
from tests.test_stepfunctions.test_stepfunctions import simple_definition


@pytest.mark.parametrize("use_parser", [True, False], ids=["use_parser", "use_mock"])
@pytest.mark.parametrize("sm_type", ["STANDARD", "EXPRESS"])
def test_validate_state_machine_definition_ok(use_parser, sm_type):
    with mock_aws(config={"stepfunctions": {"execute_state_machine": use_parser}}):
        client = boto3.client("stepfunctions", region_name="us-east-1")

        response = client.validate_state_machine_definition(
            definition=simple_definition, type=sm_type
        )

        assert response["result"] == "OK"
        assert response["diagnostics"] == []
        assert response["truncated"] is False


@pytest.mark.parametrize("use_parser", [True, False], ids=["use_parser", "use_mock"])
@pytest.mark.parametrize(
    "definition",
    [
        "{not json",
        json.dumps({"States": {"Done": {"Type": "Succeed"}}}),
        json.dumps({"StartAt": "Done", "States": {"Done": {"Type": "Unknown"}}}),
    ],
    ids=["invalid_json", "missing_start_at", "unknown_state_type"],
)
def test_validate_state_machine_definition_fail(use_parser, definition):
    with mock_aws(config={"stepfunctions": {"execute_state_machine": use_parser}}):
        client = boto3.client("stepfunctions", region_name="us-east-1")

        response = client.validate_state_machine_definition(definition=definition)

        assert response["result"] == "FAIL"
        assert len(response["diagnostics"]) == 1
        diagnostic = response["diagnostics"][0]
        assert diagnostic["severity"] == "ERROR"
        assert diagnostic["code"] == "SCHEMA_VALIDATION_FAILED"
        assert diagnostic["message"]
        assert response["truncated"] is False


@mock_aws
def test_validate_state_machine_definition_express_rejects_activities():
    client = boto3.client("stepfunctions", region_name="us-east-1")
    definition = json.dumps(
        {
            "StartAt": "Task",
            "States": {
                "Task": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:us-east-1:123456789012:activity:act",
                    "End": True,
                }
            },
        }
    )

    standard = client.validate_state_machine_definition(
        definition=definition, type="STANDARD"
    )
    assert standard["result"] == "OK"

    # Express workflows do not support activities
    express = client.validate_state_machine_definition(
        definition=definition, type="EXPRESS"
    )
    assert express["result"] == "FAIL"
    assert express["diagnostics"][0]["code"] == "SCHEMA_VALIDATION_FAILED"


@mock_aws
def test_validate_state_machine_definition_max_results():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    response = client.validate_state_machine_definition(
        definition="{not json", maxResults=1
    )

    assert response["result"] == "FAIL"
    assert len(response["diagnostics"]) == 1
    assert response["truncated"] is False
