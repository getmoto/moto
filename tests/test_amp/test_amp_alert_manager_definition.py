from datetime import datetime, timezone

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

DEFINITION = b"alertmanager_config: |\n  route:\n    receiver: default\n  receivers:\n    - name: default\n"


@mock_aws
def test_create_alert_manager_definition():
    client = boto3.client("amp", region_name="us-east-2")
    workspace_id = client.create_workspace()["workspaceId"]

    response = client.create_alert_manager_definition(
        workspaceId=workspace_id, data=DEFINITION
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 202
    assert response["status"] == {"statusCode": "ACTIVE"}


@mock_aws
@pytest.mark.parametrize(
    "data", [DEFINITION, DEFINITION + "# definição de alertas\n".encode()]
)
def test_describe_alert_manager_definition(data):
    client = boto3.client("amp", region_name="eu-west-1")
    workspace_id = client.create_workspace()["workspaceId"]
    before = datetime.now(timezone.utc)
    client.create_alert_manager_definition(workspaceId=workspace_id, data=data)

    response = client.describe_alert_manager_definition(workspaceId=workspace_id)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    definition = response["alertManagerDefinition"]
    assert definition["data"] == data
    assert definition["status"] == {"statusCode": "ACTIVE"}
    assert before <= definition["createdAt"] <= datetime.now(timezone.utc)
    assert definition["modifiedAt"] == definition["createdAt"]


@mock_aws
def test_put_alert_manager_definition():
    client = boto3.client("amp", region_name="ap-southeast-1")
    workspace_id = client.create_workspace()["workspaceId"]
    client.create_alert_manager_definition(workspaceId=workspace_id, data=DEFINITION)
    original = client.describe_alert_manager_definition(workspaceId=workspace_id)[
        "alertManagerDefinition"
    ]
    updated_data = DEFINITION + b"# updated configuration\n"
    before_update = datetime.now(timezone.utc)

    response = client.put_alert_manager_definition(
        workspaceId=workspace_id, data=updated_data
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 202
    assert response["status"] == {"statusCode": "ACTIVE"}
    definition = client.describe_alert_manager_definition(workspaceId=workspace_id)[
        "alertManagerDefinition"
    ]
    assert definition["data"] == updated_data
    assert definition["createdAt"] == original["createdAt"]
    assert before_update <= definition["modifiedAt"] <= datetime.now(timezone.utc)


@mock_aws
def test_create_alert_manager_definition_already_exists():
    client = boto3.client("amp", region_name="us-east-2")
    workspace_id = client.create_workspace()["workspaceId"]
    client.create_alert_manager_definition(workspaceId=workspace_id, data=DEFINITION)

    with pytest.raises(ClientError) as exc:
        client.create_alert_manager_definition(
            workspaceId=workspace_id, data=DEFINITION + b"# replacement\n"
        )

    assert exc.value.response["Error"]["Code"] == "ConflictException"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 409
    definition = client.describe_alert_manager_definition(workspaceId=workspace_id)[
        "alertManagerDefinition"
    ]
    assert definition["data"] == DEFINITION


@mock_aws
@pytest.mark.parametrize(
    "operation",
    ["describe_alert_manager_definition", "put_alert_manager_definition"],
)
def test_alert_manager_definition_not_found(operation):
    client = boto3.client("amp", region_name="us-east-2")
    workspace_id = client.create_workspace()["workspaceId"]
    kwargs = {"workspaceId": workspace_id}
    if operation == "put_alert_manager_definition":
        kwargs["data"] = DEFINITION

    with pytest.raises(ClientError) as exc:
        getattr(client, operation)(**kwargs)

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_aws
@pytest.mark.parametrize(
    "operation",
    [
        "create_alert_manager_definition",
        "describe_alert_manager_definition",
        "put_alert_manager_definition",
        "delete_alert_manager_definition",
    ],
)
def test_alert_manager_definition_workspace_not_found(operation):
    client = boto3.client("amp", region_name="us-east-2")
    kwargs = {"workspaceId": "ws-12345678-1234-1234-1234-123456789012"}
    if operation in {"create_alert_manager_definition", "put_alert_manager_definition"}:
        kwargs["data"] = DEFINITION

    with pytest.raises(ClientError) as exc:
        getattr(client, operation)(**kwargs)

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Workspace not found"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_aws
def test_delete_alert_manager_definition():
    client = boto3.client("amp", region_name="us-east-2")
    workspace_id = client.create_workspace()["workspaceId"]
    client.create_alert_manager_definition(workspaceId=workspace_id, data=DEFINITION)

    response = client.delete_alert_manager_definition(workspaceId=workspace_id)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 202
    assert set(response) == {"ResponseMetadata"}
    with pytest.raises(ClientError) as exc:
        client.describe_alert_manager_definition(workspaceId=workspace_id)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_recreate_alert_manager_definition():
    client = boto3.client("amp", region_name="us-east-2")
    workspace_id = client.create_workspace()["workspaceId"]
    client.create_alert_manager_definition(workspaceId=workspace_id, data=DEFINITION)
    client.delete_alert_manager_definition(workspaceId=workspace_id)
    updated_data = DEFINITION + b"# recreated\n"

    client.create_alert_manager_definition(workspaceId=workspace_id, data=updated_data)

    definition = client.describe_alert_manager_definition(workspaceId=workspace_id)[
        "alertManagerDefinition"
    ]
    assert definition["data"] == updated_data


@mock_aws
def test_alert_manager_definitions_are_workspace_specific():
    client = boto3.client("amp", region_name="us-east-2")
    first_workspace = client.create_workspace()["workspaceId"]
    second_workspace = client.create_workspace()["workspaceId"]
    client.create_alert_manager_definition(workspaceId=first_workspace, data=DEFINITION)
    second_data = DEFINITION + b"# second workspace\n"
    client.create_alert_manager_definition(
        workspaceId=second_workspace, data=second_data
    )

    client.delete_alert_manager_definition(workspaceId=first_workspace)

    definition = client.describe_alert_manager_definition(workspaceId=second_workspace)[
        "alertManagerDefinition"
    ]
    assert definition["data"] == second_data
