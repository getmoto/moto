import json
from uuid import uuid4

import boto3

from moto import mock_aws
from tests import EXAMPLE_AMI_ID
from tests.test_stepfunctions.test_stepfunctions import _get_default_role

state_machine_definition = {
    "StartAt": "HelloWorld",
    "States": {"HelloWorld": {"Type": "Pass", "Result": "Hello World!", "End": True}},
}


def _create_state_machine_rule(sfn_client, events_client, state):
    response = sfn_client.create_state_machine(
        name=str(uuid4()),
        definition=json.dumps(state_machine_definition),
        roleArn=_get_default_role(),
    )
    state_machine_arn = response["stateMachineArn"]

    rule_name = str(uuid4())
    events_client.put_rule(
        Name=rule_name,
        EventPattern=json.dumps(
            {
                "source": ["aws.ec2"],
                "detail-type": ["EC2 Instance State-change Notification"],
                "detail": {"state": [state]},
            }
        ),
        State="ENABLED",
    )
    events_client.put_targets(
        Rule=rule_name,
        Targets=[{"Id": "n/a", "Arn": state_machine_arn}],
    )
    return state_machine_arn


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_run_instances_invokes_stepfunction_for_running_state():
    sfn_client = boto3.client("stepfunctions", "us-east-1")
    events_client = boto3.client("events", "us-east-1")
    ec2_client = boto3.client("ec2", "us-east-1")

    state_machine_arn = _create_state_machine_rule(sfn_client, events_client, "running")

    resp = ec2_client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance_id = resp["Instances"][0]["InstanceId"]

    execs = sfn_client.list_executions(stateMachineArn=state_machine_arn)["executions"]
    assert len(execs) == 1

    execution_details = sfn_client.describe_execution(
        executionArn=execs[0]["executionArn"]
    )
    execution_input = json.loads(execution_details["input"])
    assert execution_input["source"] == "aws.ec2"
    assert execution_input["detail-type"] == "EC2 Instance State-change Notification"
    assert execution_input["detail"]["instance-id"] == instance_id
    assert execution_input["detail"]["state"] == "running"


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_stop_instances_invokes_stepfunction_for_stopped_state():
    sfn_client = boto3.client("stepfunctions", "us-east-1")
    events_client = boto3.client("events", "us-east-1")
    ec2_client = boto3.client("ec2", "us-east-1")

    resp = ec2_client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance_id = resp["Instances"][0]["InstanceId"]

    state_machine_arn = _create_state_machine_rule(sfn_client, events_client, "stopped")

    ec2_client.stop_instances(InstanceIds=[instance_id])

    execs = sfn_client.list_executions(stateMachineArn=state_machine_arn)["executions"]
    assert len(execs) == 1
    execution_input = json.loads(
        sfn_client.describe_execution(executionArn=execs[0]["executionArn"])["input"]
    )
    assert execution_input["detail"]["state"] == "stopped"


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_terminate_instances_invokes_stepfunction_for_terminated_state():
    sfn_client = boto3.client("stepfunctions", "us-east-1")
    events_client = boto3.client("events", "us-east-1")
    ec2_client = boto3.client("ec2", "us-east-1")

    resp = ec2_client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance_id = resp["Instances"][0]["InstanceId"]

    state_machine_arn = _create_state_machine_rule(
        sfn_client, events_client, "terminated"
    )

    ec2_client.terminate_instances(InstanceIds=[instance_id])

    execs = sfn_client.list_executions(stateMachineArn=state_machine_arn)["executions"]
    assert len(execs) == 1
    execution_input = json.loads(
        sfn_client.describe_execution(executionArn=execs[0]["executionArn"])["input"]
    )
    assert execution_input["detail"]["state"] == "terminated"


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_rule_does_not_fire_for_a_different_state():
    sfn_client = boto3.client("stepfunctions", "us-east-1")
    events_client = boto3.client("events", "us-east-1")
    ec2_client = boto3.client("ec2", "us-east-1")

    # Rule only matches "stopped" - starting/running an instance shouldn't fire it
    state_machine_arn = _create_state_machine_rule(sfn_client, events_client, "stopped")

    ec2_client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    execs = sfn_client.list_executions(stateMachineArn=state_machine_arn)["executions"]
    assert len(execs) == 0
