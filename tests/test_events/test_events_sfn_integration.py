import json
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests.test_stepfunctions.test_stepfunctions import _get_default_role

state_machine_definition = {
    "StartAt": "HelloWorld",
    "States": {"HelloWorld": {"Type": "Pass", "Result": "Hello World!", "End": True}},
}


@pytest.mark.parametrize("mocked_sfn", [True, False], ids=["Mocked", "Parsed"])
def test_create_bucket_invokes_stepfunction(mocked_sfn):
    with mock_aws(config={"stepfunctions": {"execute_state_machine": mocked_sfn}}):
        create_bucket_invokes_stepfunction()


def create_bucket_invokes_stepfunction():
    sfn_client = boto3.client("stepfunctions", "us-east-1")
    response = sfn_client.create_state_machine(
        name=str(uuid4()),
        definition=json.dumps(state_machine_definition),
        roleArn=_get_default_role(),
    )
    state_machine_arn = response["stateMachineArn"]

    events_client = boto3.client("events", "us-east-1")
    s3_client = boto3.client("s3", "us-east-1")

    bucket_name = str(uuid4())

    events_client.put_rule(
        Name="rule_name",
        EventPattern="""{
                    "source": [
                        "aws.s3"
                    ],
                    "detail-type": [
                        "AWS API Call via CloudTrail"
                    ],
                    "detail": {
                        "eventSource": [
                            "s3.amazonaws.com"
                        ],
                        "eventName": [
                            "CreateBucket"
                        ]
                    }
                }""",
        State="ENABLED",
    )

    events_client.put_targets(
        Rule="rule_name",
        Targets=[{"Id": "n/a", "Arn": state_machine_arn}],
    )

    # Kick off Event
    s3_client.create_bucket(Bucket=bucket_name)

    # Verify SFN was invoked
    execs = sfn_client.list_executions(stateMachineArn=state_machine_arn)["executions"]
    assert len(execs) == 1

    # Verify the Execution Input is correct
    execution_arn = execs[0]["executionArn"]
    execution_details = sfn_client.describe_execution(executionArn=execution_arn)
    execution_input = json.loads(execution_details["input"])
    assert execution_input["source"] == "aws.s3"
    assert execution_input["detail-type"] == "Object Created"
    assert execution_input["resources"] == [f"arn:aws:s3:::{bucket_name}"]


@pytest.mark.parametrize("mocked_sfn", [True, False], ids=["Mocked", "Parsed"])
@pytest.mark.parametrize("region", ["us-east-1", "eu-west-1"])
@pytest.mark.parametrize(
    "rule_state", ["ENABLED", "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"]
)
def test_delete_bucket_invokes_stepfunction(mocked_sfn, region, rule_state):
    with mock_aws(config={"stepfunctions": {"execute_state_machine": mocked_sfn}}):
        sfn_client = boto3.client("stepfunctions", region)
        state_machine_arn = sfn_client.create_state_machine(
            name=str(uuid4()),
            definition=json.dumps(state_machine_definition),
            roleArn=_get_default_role(),
        )["stateMachineArn"]
        events_client = boto3.client("events", region)
        s3_client = boto3.client("s3", region)
        bucket_name = str(uuid4())
        bucket_config = {} if region == "us-east-1" else {"LocationConstraint": region}
        s3_client.create_bucket(
            Bucket=bucket_name, CreateBucketConfiguration=bucket_config
        )
        events_client.put_rule(
            Name="delete-bucket",
            EventPattern=json.dumps(
                {
                    "source": ["aws.s3"],
                    "detail-type": ["AWS API Call via CloudTrail"],
                    "detail": {
                        "eventSource": ["s3.amazonaws.com"],
                        "eventName": ["DeleteBucket"],
                        "requestParameters": {"bucketName": [bucket_name]},
                    },
                }
            ),
            State=rule_state,
        )
        events_client.put_targets(
            Rule="delete-bucket",
            Targets=[{"Id": "sfn", "Arn": state_machine_arn}],
        )

        s3_client.put_object(Bucket=bucket_name, Key="key", Body=b"content")
        with pytest.raises(ClientError) as exc:
            s3_client.delete_bucket(Bucket=bucket_name)
        assert exc.value.response["Error"]["Code"] == "BucketNotEmpty"
        assert not sfn_client.list_executions(stateMachineArn=state_machine_arn)[
            "executions"
        ]

        s3_client.delete_object(Bucket=bucket_name, Key="key")
        s3_client.delete_bucket(Bucket=bucket_name)

        executions = sfn_client.list_executions(stateMachineArn=state_machine_arn)[
            "executions"
        ]
        assert len(executions) == 1
        execution = sfn_client.describe_execution(
            executionArn=executions[0]["executionArn"]
        )
        event = json.loads(execution["input"])
        assert event["source"] == "aws.s3"
        assert event["detail-type"] == "AWS API Call via CloudTrail"
        assert event["account"] == ACCOUNT_ID
        assert event["region"] == region
        assert event["resources"] == []
        assert event["detail"]["eventName"] == "DeleteBucket"
        assert event["detail"]["eventSource"] == "s3.amazonaws.com"
        assert event["detail"]["eventType"] == "AwsApiCall"
        assert event["detail"]["awsRegion"] == region
        assert event["detail"]["recipientAccountId"] == ACCOUNT_ID
        assert event["detail"]["requestParameters"] == {"bucketName": bucket_name}
        assert event["detail"]["responseElements"] is None
        assert event["detail"]["readOnly"] is False
        assert event["detail"]["managementEvent"] is True

        with pytest.raises(ClientError) as exc:
            s3_client.delete_bucket(Bucket=bucket_name)
        assert exc.value.response["Error"]["Code"] == "NoSuchBucket"
        assert (
            len(
                sfn_client.list_executions(stateMachineArn=state_machine_arn)[
                    "executions"
                ]
            )
            == 1
        )


@mock_aws
@pytest.mark.parametrize(
    "mismatch",
    ["bucket", "event-name", "detail-type", "disabled", "region", "bus", "account"],
)
def test_delete_bucket_does_not_invoke_nonmatching_rule(mismatch):
    region = "us-east-1"
    s3_client = boto3.client("s3", region)
    bucket_name = str(uuid4())
    s3_client.create_bucket(Bucket=bucket_name)
    rule_region = "eu-west-1" if mismatch == "region" else region
    client_kwargs = {}
    role_arn = _get_default_role()
    if mismatch == "account":
        credentials = boto3.client("sts", region).assume_role(
            RoleArn="arn:aws:iam::999999999999:role/other-account",
            RoleSessionName="other-account",
        )["Credentials"]
        client_kwargs = {
            "aws_access_key_id": credentials["AccessKeyId"],
            "aws_secret_access_key": credentials["SecretAccessKey"],
            "aws_session_token": credentials["SessionToken"],
        }
        iam_client = boto3.client("iam", region, **client_kwargs)
        role_arn = iam_client.create_role(
            RoleName="sfn-role", AssumeRolePolicyDocument="{}"
        )["Role"]["Arn"]
        assert role_arn.startswith("arn:aws:iam::999999999999:")
    sfn_client = boto3.client("stepfunctions", rule_region, **client_kwargs)
    state_machine_arn = sfn_client.create_state_machine(
        name=str(uuid4()),
        definition=json.dumps(state_machine_definition),
        roleArn=role_arn,
    )["stateMachineArn"]
    events_client = boto3.client("events", rule_region, **client_kwargs)
    event_bus = "custom" if mismatch == "bus" else "default"
    if mismatch == "bus":
        events_client.create_event_bus(Name=event_bus)
    events_client.put_rule(
        Name="nonmatching-rule",
        EventBusName=event_bus,
        EventPattern=json.dumps(
            {
                "source": ["aws.s3"],
                "detail-type": [
                    "Object Deleted"
                    if mismatch == "detail-type"
                    else "AWS API Call via CloudTrail"
                ],
                "detail": {
                    "eventSource": ["s3.amazonaws.com"],
                    "eventName": [
                        "CreateBucket" if mismatch == "event-name" else "DeleteBucket"
                    ],
                    "requestParameters": {
                        "bucketName": [
                            "another-bucket" if mismatch == "bucket" else bucket_name
                        ]
                    },
                },
            }
        ),
        State="DISABLED" if mismatch == "disabled" else "ENABLED",
    )
    events_client.put_targets(
        Rule="nonmatching-rule",
        EventBusName=event_bus,
        Targets=[{"Id": "sfn", "Arn": state_machine_arn}],
    )

    s3_client.delete_bucket(Bucket=bucket_name)

    assert not sfn_client.list_executions(stateMachineArn=state_machine_arn)[
        "executions"
    ]
