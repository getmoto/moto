import base64
import json
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests.test_stepfunctions.test_stepfunctions import _get_default_role


def _create_state_machine(client, role_arn=None):
    return client.create_state_machine(
        name=str(uuid4()),
        definition=json.dumps(
            {"StartAt": "Refresh", "States": {"Refresh": {"Type": "Pass", "End": True}}}
        ),
        roleArn=role_arn or _get_default_role(),
    )["stateMachineArn"]


def _secret_change_pattern(secret_arn):
    return {
        "source": ["aws.secretsmanager"],
        "detail-type": ["AWS API Call via CloudTrail"],
        "detail": {
            "eventSource": ["secretsmanager.amazonaws.com"],
            "eventName": ["PutSecretValue"],
            "responseElements": {"arn": [secret_arn]},
        },
    }


@pytest.mark.parametrize("mocked_sfn", [True, False], ids=["Mocked", "Parsed"])
@pytest.mark.parametrize(
    "rule_state", ["ENABLED", "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"]
)
@pytest.mark.parametrize(
    "region,value,stages",
    [
        ("us-east-1", {"SecretString": "new-secret-value"}, None),
        ("eu-west-1", {"SecretBinary": b"new-binary-value"}, ["AWSPENDING"]),
    ],
)
def test_put_secret_value_invokes_stepfunction(
    mocked_sfn, rule_state, region, value, stages
):
    with mock_aws(config={"stepfunctions": {"execute_state_machine": mocked_sfn}}):
        sfn = boto3.client("stepfunctions", region)
        events = boto3.client("events", region)
        secrets = boto3.client("secretsmanager", region)
        machine = _create_state_machine(sfn)
        secret = secrets.create_secret(Name=str(uuid4()), SecretString="old-value")
        rule_name = str(uuid4())
        events.put_rule(
            Name=rule_name,
            EventPattern=json.dumps(_secret_change_pattern(secret["ARN"])),
            State=rule_state,
        )
        events.put_targets(Rule=rule_name, Targets=[{"Id": "refresh", "Arn": machine}])
        token, rotation_token = str(uuid4()), str(uuid4())
        request = {
            "SecretId": secret["ARN"],
            "ClientRequestToken": token,
            "RotationToken": rotation_token,
            **value,
        }
        if stages is not None:
            request["VersionStages"] = stages
        response = secrets.put_secret_value(**request)
        stored = secrets.get_secret_value(SecretId=secret["ARN"], VersionId=token)
        for key, expected in value.items():
            assert stored[key] == expected
        assert stored["VersionId"] == response["VersionId"] == token
        if stages == ["AWSPENDING"]:
            assert (
                secrets.get_secret_value(SecretId=secret["ARN"])["SecretString"]
                == "old-value"
            )

        executions = sfn.list_executions(stateMachineArn=machine)["executions"]
        assert len(executions) == 1
        event = json.loads(
            sfn.describe_execution(executionArn=executions[0]["executionArn"])["input"]
        )
        assert event["source"] == "aws.secretsmanager"
        assert event["detail-type"] == "AWS API Call via CloudTrail"
        assert event["account"] == ACCOUNT_ID
        assert event["region"] == region
        assert event["resources"] == []
        detail = event["detail"]
        assert detail["eventName"] == "PutSecretValue"
        assert detail["eventSource"] == "secretsmanager.amazonaws.com"
        assert detail["awsRegion"] == region
        assert detail["recipientAccountId"] == ACCOUNT_ID
        assert detail["eventType"] == "AwsApiCall"
        assert detail["readOnly"] is False
        assert detail["managementEvent"] is True
        expected_request = {"secretId": secret["ARN"], "clientRequestToken": token}
        if stages is not None:
            expected_request["versionStages"] = stages
        assert detail["requestParameters"] == expected_request
        assert detail["responseElements"] == {
            "arn": secret["ARN"],
            "name": secret["Name"],
            "versionId": token,
            "versionStages": stages or ["AWSCURRENT"],
        }
        serialized = json.dumps(event)
        assert rotation_token not in serialized
        assert "new-secret-value" not in serialized
        assert "new-binary-value" not in serialized
        assert base64.b64encode(b"new-binary-value").decode() not in serialized


@mock_aws
def test_put_first_secret_value_preserves_requested_stages_in_event():
    region = "us-east-1"
    sfn = boto3.client("stepfunctions", region)
    events = boto3.client("events", region)
    secrets = boto3.client("secretsmanager", region)
    machine = _create_state_machine(sfn)
    secret = secrets.create_secret(Name=str(uuid4()))
    rule_name = str(uuid4())
    events.put_rule(
        Name=rule_name, EventPattern=json.dumps(_secret_change_pattern(secret["ARN"]))
    )
    events.put_targets(Rule=rule_name, Targets=[{"Id": "refresh", "Arn": machine}])
    response = secrets.put_secret_value(
        SecretId=secret["Name"],
        SecretString="first-value",
        VersionStages=["AWSPENDING"],
    )
    executions = sfn.list_executions(stateMachineArn=machine)["executions"]
    assert len(executions) == 1
    event = json.loads(
        sfn.describe_execution(executionArn=executions[0]["executionArn"])["input"]
    )
    assert event["detail"]["requestParameters"]["secretId"] == secret["Name"]
    assert event["detail"]["requestParameters"]["versionStages"] == ["AWSPENDING"]
    assert (
        event["detail"]["responseElements"]["versionStages"]
        == response["VersionStages"]
        == ["AWSPENDING", "AWSCURRENT"]
    )


@mock_aws
def test_put_secret_value_retry_and_errors():
    region = "us-east-1"
    sfn = boto3.client("stepfunctions", region)
    events = boto3.client("events", region)
    secrets = boto3.client("secretsmanager", region)
    machine = _create_state_machine(sfn)
    secret = secrets.create_secret(Name=str(uuid4()), SecretString="old-value")
    rule_name = str(uuid4())
    events.put_rule(
        Name=rule_name, EventPattern=json.dumps(_secret_change_pattern(secret["ARN"]))
    )
    events.put_targets(Rule=rule_name, Targets=[{"Id": "refresh", "Arn": machine}])
    token = str(uuid4())
    for _ in range(2):
        response = secrets.put_secret_value(
            SecretId=secret["ARN"], SecretString="new-value", ClientRequestToken=token
        )
        assert response["VersionId"] == token
    assert len(secrets.list_secret_version_ids(SecretId=secret["ARN"])["Versions"]) == 2
    assert len(sfn.list_executions(stateMachineArn=machine)["executions"]) == 2

    with pytest.raises(ClientError) as exc:
        secrets.put_secret_value(
            SecretId=secret["ARN"],
            SecretString="conflicting-value",
            ClientRequestToken=token,
        )
    assert exc.value.response["Error"]["Code"] == "ResourceExistsException"
    with pytest.raises(ClientError) as exc:
        secrets.put_secret_value(SecretId="missing-secret", SecretString="new-value")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert len(sfn.list_executions(stateMachineArn=machine)["executions"]) == 2
    assert (
        secrets.get_secret_value(SecretId=secret["ARN"])["SecretString"] == "new-value"
    )


@mock_aws
@pytest.mark.parametrize(
    "mismatch",
    [
        "secret",
        "stage",
        "event-name",
        "detail-type",
        "disabled",
        "region",
        "bus",
        "account",
    ],
)
def test_put_secret_value_does_not_invoke_nonmatching_rule(mismatch):
    region = "us-east-1"
    secrets = boto3.client("secretsmanager", region)
    secret = secrets.create_secret(Name=str(uuid4()), SecretString="old-value")
    rule_region = "eu-west-1" if mismatch == "region" else region
    client_kwargs = {}
    role_arn = None
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
        role_arn = boto3.client("iam", region, **client_kwargs).create_role(
            RoleName=str(uuid4()), AssumeRolePolicyDocument="{}"
        )["Role"]["Arn"]
    sfn = boto3.client("stepfunctions", rule_region, **client_kwargs)
    events = boto3.client("events", rule_region, **client_kwargs)
    machine = _create_state_machine(sfn, role_arn)
    pattern = _secret_change_pattern(secret["ARN"])
    if mismatch == "secret":
        pattern["detail"]["responseElements"]["arn"] = [secret["ARN"] + "other"]
    if mismatch == "stage":
        pattern["detail"]["responseElements"]["versionStages"] = ["AWSCURRENT"]
    if mismatch == "event-name":
        pattern["detail"]["eventName"] = ["UpdateSecret"]
    if mismatch == "detail-type":
        pattern["detail-type"] = ["Secret Label Updated"]
    bus = "custom" if mismatch == "bus" else "default"
    if bus == "custom":
        events.create_event_bus(Name=bus)
    rule_name = str(uuid4())
    events.put_rule(
        Name=rule_name,
        EventBusName=bus,
        EventPattern=json.dumps(pattern),
        State="DISABLED" if mismatch == "disabled" else "ENABLED",
    )
    events.put_targets(
        Rule=rule_name, EventBusName=bus, Targets=[{"Id": "refresh", "Arn": machine}]
    )
    secrets.put_secret_value(
        SecretId=secret["ARN"], SecretString="new-value", VersionStages=["AWSPENDING"]
    )
    assert sfn.list_executions(stateMachineArn=machine)["executions"] == []


@mock_aws
def test_put_secret_value_succeeds_when_notification_target_is_missing():
    region = "us-east-1"
    secrets = boto3.client("secretsmanager", region)
    events = boto3.client("events", region)
    secret = secrets.create_secret(Name=str(uuid4()), SecretString="old-value")
    rule_name = str(uuid4())
    events.put_rule(
        Name=rule_name, EventPattern=json.dumps(_secret_change_pattern(secret["ARN"]))
    )
    events.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "missing",
                "Arn": f"arn:aws:states:{region}:{ACCOUNT_ID}:stateMachine:missing",
            }
        ],
    )
    response = secrets.put_secret_value(
        SecretId=secret["ARN"], SecretString="new-value"
    )
    stored = secrets.get_secret_value(SecretId=secret["ARN"])
    assert stored["VersionId"] == response["VersionId"]
    assert stored["SecretString"] == "new-value"
