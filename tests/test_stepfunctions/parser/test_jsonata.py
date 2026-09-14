import json
from time import sleep
from uuid import uuid4

import boto3

from moto import mock_aws


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_jsonata_pass_state():
    sfn = boto3.client("stepfunctions", region_name="us-east-1")
    definition = {
        "QueryLanguage": "JSONata",
        "StartAt": "Add",
        "States": {
            "Add": {
                "Type": "Pass",
                "Output": {"sum": "{% 1 + 1 %}"},
                "End": True,
            }
        },
    }
    arn = sfn.create_state_machine(
        name=f"jsonata-test-{str(uuid4())[:6]}",
        definition=json.dumps(definition),
        roleArn="arn:aws:iam::123456789012:role/sf",
    )["stateMachineArn"]

    execution_arn = sfn.start_execution(stateMachineArn=arn)["executionArn"]

    for _ in range(30):
        execution = sfn.describe_execution(executionArn=execution_arn)
        if execution["status"] != "RUNNING":
            break
        sleep(0.1)

    assert execution["status"] == "SUCCEEDED"
    assert json.loads(execution["output"]) == {"sum": 2}
