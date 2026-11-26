"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import json
from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_cloudformation import CloudFormationClient, CloudFormationConfig
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-cloudformation is not installed", allow_module_level=True)


def notifications_template(with_dead_letter_queue: bool) -> str:
    resources = {
        "Topic": {
            "Type": "AWS::SNS::Topic",
            "Properties": {"TopicName": {"Fn::Sub": "notifications-${Environment}"}},
        },
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {"QueueName": {"Fn::Sub": "notifications-${Environment}"}},
        },
    }
    if with_dead_letter_queue:
        resources["DeadLetterQueue"] = {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::Sub": "notifications-dlq-${Environment}"}
            },
        }
    return json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Parameters": {"Environment": {"Type": "String"}},
            "Resources": resources,
            "Outputs": {
                "TopicArn": {"Value": {"Ref": "Topic"}},
                "QueueArn": {"Value": {"Fn::GetAtt": ["Queue", "Arn"]}},
            },
        }
    )


@pytest.mark.skip(
    reason="Moto's CreateChangeSet defaults ChangeSetType to CREATE instead of UPDATE, "
    "so a change set for an existing stack lists every resource as 'Add'"
)
@mock_aws
def test_deploy_and_update_stack():
    """Deploy a stack, update it through a change set, and delete it again."""
    environment = f"test{uuid4().hex[:8]}"
    stack_name = f"notifications-{environment}"
    parameters = [{"parameter_key": "Environment", "parameter_value": environment}]

    config = CloudFormationConfig.resolve(region="us-east-1")
    with CloudFormationClient(config=config) as client:
        stack_id = client.create_stack(
            stack_name=stack_name,
            template_body=notifications_template(with_dead_letter_queue=False),
            parameters=parameters,
            tags=[{"key": "environment", "value": environment}],
        ).stack_id

        stack = client.describe_stacks(stack_name=stack_name).stacks[0]
        assert stack.stack_id == stack_id
        assert stack.stack_status == "CREATE_COMPLETE"
        assert [(p.parameter_key, p.parameter_value) for p in stack.parameters] == [
            ("Environment", environment)
        ]
        outputs = {o.output_key: o.output_value for o in stack.outputs}
        assert outputs["TopicArn"].endswith(f":notifications-{environment}")
        assert outputs["QueueArn"].endswith(f":notifications-{environment}")

        resources = client.list_stack_resources(
            stack_name=stack_name
        ).stack_resource_summaries
        assert sorted((r.logical_resource_id, r.resource_type) for r in resources) == [
            ("Queue", "AWS::SQS::Queue"),
            ("Topic", "AWS::SNS::Topic"),
        ]

        # Review the update before applying it
        client.create_change_set(
            stack_name=stack_name,
            change_set_name="add-dead-letter-queue",
            template_body=notifications_template(with_dead_letter_queue=True),
            parameters=parameters,
        )
        change_set = client.describe_change_set(
            stack_name=stack_name, change_set_name="add-dead-letter-queue"
        )
        assert change_set.status == "CREATE_COMPLETE"
        assert [
            (c.resource_change.action, c.resource_change.logical_resource_id)
            for c in change_set.changes
        ] == [("Add", "DeadLetterQueue")]

        client.execute_change_set(
            stack_name=stack_name, change_set_name="add-dead-letter-queue"
        )
        stack = client.describe_stacks(stack_name=stack_name).stacks[0]
        assert stack.stack_status == "UPDATE_COMPLETE"
        resources = client.list_stack_resources(
            stack_name=stack_name
        ).stack_resource_summaries
        assert sorted(r.logical_resource_id for r in resources) == [
            "DeadLetterQueue",
            "Queue",
            "Topic",
        ]

        client.delete_stack(stack_name=stack_name)
        stack = client.describe_stacks(stack_name=stack_id).stacks[0]
        assert stack.stack_status == "DELETE_COMPLETE"
