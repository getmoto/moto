from datetime import datetime
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import aws_verified
from tests.test_stepfunctions.test_stepfunctions import (
    _get_default_role,
    simple_definition,
)


@pytest.mark.parametrize("use_parser", [True, False], ids=["use_parser", "use_mock"])
def test_describe_state_machine_using_version_arn(use_parser):
    with mock_aws(config={"stepfunctions": {"execute_state_machine": use_parser}}):
        client = boto3.client("stepfunctions", region_name="us-east-1")

        name = f"sfn_name_{str(uuid4())[0:6]}"
        response = client.create_state_machine(
            name=name,
            definition=simple_definition,
            roleArn=_get_default_role(),
            publish=True,
        )
        arn = response["stateMachineArn"]
        version_arn1 = response["stateMachineVersionArn"]

        # Use the initial version to describe the state machine
        version1 = client.describe_state_machine(stateMachineArn=version_arn1)
        assert version1["loggingConfiguration"] == {"level": "OFF"}

        # Update the state machine
        update = client.update_state_machine(
            stateMachineArn=arn,
            loggingConfiguration={"level": "ALL"},
            publish=True,
        )
        version_arn2 = update["stateMachineVersionArn"]
        assert version_arn1 != version_arn2

        # Assert that we can retrieve the latest configuration, either by the regular ARN or by the version ARN
        latest = client.describe_state_machine(stateMachineArn=arn)
        assert latest["loggingConfiguration"] == {"level": "ALL"}
        version2 = client.describe_state_machine(stateMachineArn=version_arn2)
        assert version2["loggingConfiguration"] == {"level": "ALL"}

        # Assert that we can still describe the first version of the state machine
        version1 = client.describe_state_machine(stateMachineArn=version_arn1)
        assert version1["loggingConfiguration"] == {"level": "OFF"}


@aws_verified
@pytest.mark.aws_verified
def test_create_state_machine_with_version_description():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    try:
        name = f"sfn_name_{str(uuid4())[0:6]}"

        response = client.create_state_machine(
            name=name,
            definition=simple_definition,
            roleArn=_get_default_role(),
            versionDescription="first version",
            publish=True,
        )
        arn = response["stateMachineArn"]
        version_arn1 = response["stateMachineVersionArn"]

        # Use the initial version to describe the state machine
        sm = client.describe_state_machine(stateMachineArn=arn)
        assert "description" not in sm

        version = client.describe_state_machine(stateMachineArn=version_arn1)
        assert version["description"] == "first version"

        update = client.update_state_machine(
            stateMachineArn=arn,
            definition=simple_definition,
            versionDescription="second version",
            publish=True,
        )
        version_arn2 = update["stateMachineVersionArn"]

        version = client.describe_state_machine(stateMachineArn=version_arn2)
        assert version["description"] == "second version"
    finally:
        client.delete_state_machine(stateMachineArn=arn)


@aws_verified
@pytest.mark.aws_verified
def test_create_unpublished_state_machine_with_version_description():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    name = f"sfn_name_{str(uuid4())[0:6]}"

    with pytest.raises(ClientError) as exc:
        client.create_state_machine(
            name=name,
            definition=simple_definition,
            roleArn=_get_default_role(),
            versionDescription="first version of statemachine",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Version description can only be set when publish is true"


@mock_aws
def test_list_state_machine_versions_includes_published_versions_only():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    name = "versioned_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=simple_definition,
        roleArn=_get_default_role(),
        publish=True,
    )
    arn = response_create["stateMachineArn"]
    version_arn1 = response_create["stateMachineVersionArn"]

    updated_definition = simple_definition.replace("DefaultState", "DefaultStateV2")
    response_update = client.update_state_machine(
        stateMachineArn=arn,
        definition=updated_definition,
        publish=True,
    )
    version_arn2 = response_update["stateMachineVersionArn"]

    response = client.list_state_machine_versions(stateMachineArn=arn)

    assert [
        item["stateMachineVersionArn"] for item in response["stateMachineVersions"]
    ] == [version_arn2, version_arn1]


@mock_aws
def test_delete_state_machine_version_removes_version():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    name = "versioned_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=simple_definition,
        roleArn=_get_default_role(),
        publish=True,
    )
    arn = response_create["stateMachineArn"]
    version_arn1 = response_create["stateMachineVersionArn"]

    updated_definition = simple_definition.replace("DefaultState", "DefaultStateV2")
    response_update = client.update_state_machine(
        stateMachineArn=arn,
        definition=updated_definition,
        publish=True,
    )
    version_arn2 = response_update["stateMachineVersionArn"]

    client.delete_state_machine_version(stateMachineVersionArn=version_arn1)

    response = client.list_state_machine_versions(stateMachineArn=arn)
    assert [
        item["stateMachineVersionArn"] for item in response["stateMachineVersions"]
    ] == [version_arn2]


@mock_aws
def test_delete_state_machine_version_fails_if_alias_references_it():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    name = "versioned_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=simple_definition,
        roleArn=_get_default_role(),
        publish=True,
    )

    client.create_state_machine_alias(
        name="stable",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create["stateMachineVersionArn"],
                "weight": 100,
            }
        ],
    )

    with pytest.raises(ClientError) as exc:
        client.delete_state_machine_version(
            stateMachineVersionArn=response_create["stateMachineVersionArn"]
        )

    assert exc.value.response["Error"]["Code"] == "ConflictException"


@mock_aws
def test_publish_state_machine_version_creates_new_version():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    response_create = client.create_state_machine(
        name="versioned_step_function",
        definition=simple_definition,
        roleArn=_get_default_role(),
    )
    arn = response_create["stateMachineArn"]

    response = client.publish_state_machine_version(
        stateMachineArn=arn,
        description="first published version",
    )

    assert response["stateMachineVersionArn"] == f"{arn}:1"

    version = client.describe_state_machine(
        stateMachineArn=response["stateMachineVersionArn"]
    )
    assert version["description"] == "first published version"


@mock_aws
def test_list_state_machine_versions_fails_for_unknown_state_machine():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    nonexistent_arn = f"arn:aws:states:us-east-1:{ACCOUNT_ID}:stateMachine:nonexistent"

    with pytest.raises(ClientError) as exc:
        client.list_state_machine_versions(stateMachineArn=nonexistent_arn)

    assert exc.value.response["Error"]["Code"] == "StateMachineDoesNotExist"


@mock_aws
def test_publish_state_machine_version_returns_creation_date():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    response_create = client.create_state_machine(
        name="versioned_step_function",
        definition=simple_definition,
        roleArn=_get_default_role(),
    )
    arn = response_create["stateMachineArn"]

    response = client.publish_state_machine_version(stateMachineArn=arn)

    assert isinstance(response["creationDate"], datetime)


@mock_aws
def test_delete_state_machine_version_is_noop_when_version_missing():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    response_create = client.create_state_machine(
        name="versioned_step_function",
        definition=simple_definition,
        roleArn=_get_default_role(),
        publish=True,
    )
    arn = response_create["stateMachineArn"]
    version_arn1 = response_create["stateMachineVersionArn"]

    missing_version_arn = f"{arn}:99"
    client.delete_state_machine_version(stateMachineVersionArn=missing_version_arn)

    response = client.list_state_machine_versions(stateMachineArn=arn)
    assert [
        item["stateMachineVersionArn"] for item in response["stateMachineVersions"]
    ] == [version_arn1]


@mock_aws
def test_publish_state_machine_version_fails_for_unknown_state_machine():
    client = boto3.client("stepfunctions", region_name="us-east-1")

    nonexistent_arn = f"arn:aws:states:us-east-1:{ACCOUNT_ID}:stateMachine:nonexistent"

    with pytest.raises(ClientError) as exc:
        client.publish_state_machine_version(stateMachineArn=nonexistent_arn)

    assert exc.value.response["Error"]["Code"] == "StateMachineDoesNotExist"
