from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

region = "us-east-1"
simple_definition = (
    '{"Comment": "An example of the Amazon States Language using a choice state.",'
    '"StartAt": "DefaultState",'
    '"States": '
    '{"DefaultState": {"Type": "Fail","Error": "DefaultStateError","Cause": "No Matches!"}}}'
)
account_id = None


def _get_default_role():
    return "arn:aws:iam::" + ACCOUNT_ID + ":role/unknown_sf_role"


@mock_aws
def test_state_machine_alias_succeeds():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )
    response = client.create_state_machine_alias(
        name="my-alias",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create["stateMachineVersionArn"],
                "weight": 100,
            }
        ],
    )
    assert (
        response["stateMachineAliasArn"]
        == response_create["stateMachineArn"] + ":" + "my-alias"
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert isinstance(response["creationDate"], datetime)


@mock_aws
@pytest.mark.parametrize(
    "routing_configuration,expected_error_msg",
    [
        pytest.param(
            [
                {
                    "stateMachineVersionArn": "arn:aws:states:us-east-1:123456789012:stateMachine:test:1",
                    "weight": 50,
                },
                {
                    "stateMachineVersionArn": "arn:aws:states:us-east-1:123456789012:stateMachine:test:1",
                    "weight": 25,
                },
                {
                    "stateMachineVersionArn": "arn:aws:states:us-east-1:123456789012:stateMachine:test:1",
                    "weight": 25,
                },
            ],
            "Routing configuration must contain 1 or 2",
            id="too_many_versions",
        ),
        pytest.param(
            [
                {
                    "stateMachineVersionArn": "arn:aws:states:us-east-1:123456789012:stateMachine:test:1",
                    "weight": 50,
                },
            ],
            "sum of the weights in the routing configuration must be equal to 100",
            id="invalid_weight_single",
        ),
        pytest.param(
            [
                {
                    "stateMachineVersionArn": "arn:aws:states:us-east-1:123456789012:stateMachine:test:1",
                    "weight": 60,
                },
                {
                    "stateMachineVersionArn": "arn:aws:states:us-east-1:123456789012:stateMachine:test:1",
                    "weight": 30,
                },
            ],
            "sum of the weights in the routing configuration must be equal to 100",
            id="invalid_weight_sum",
        ),
    ],
)
def test_state_machine_alias_fails_with_invalid_routing_config(
    routing_configuration, expected_error_msg
):
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    _ = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    with pytest.raises(ClientError) as exc:
        client.create_state_machine_alias(
            name="my-alias",
            routingConfiguration=routing_configuration,
        )
    assert exc.value.response["Error"]["Code"] == "ValidationException"
    assert expected_error_msg in exc.value.response["Error"]["Message"]


@mock_aws
def test_state_machine_alias_fails_with_different_state_machines():
    client = boto3.client("stepfunctions", region_name=region)
    name1 = "example_step_function_1"
    response_create_1 = client.create_state_machine(
        name=name1,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )
    name2 = "example_step_function_2"
    response_create_2 = client.create_state_machine(
        name=name2,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )
    with pytest.raises(ClientError) as exc:
        client.create_state_machine_alias(
            name="my-alias",
            routingConfiguration=[
                {
                    "stateMachineVersionArn": response_create_1[
                        "stateMachineVersionArn"
                    ],
                    "weight": 50,
                },
                {
                    "stateMachineVersionArn": response_create_2[
                        "stateMachineVersionArn"
                    ],
                    "weight": 50,
                },
            ],
        )
    assert exc.value.response["Error"]["Code"] == "ValidationException"
    assert (
        "Both stateMachineVersionArn values must belong to the same state machine"
        in exc.value.response["Error"]["Message"]
    )


@mock_aws
def test_state_machine_two_alias():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create_v1 = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    updated_definition = str(simple_definition).replace(
        "DefaultState", "DefaultStateV2"
    )
    response_update_v2 = client.update_state_machine(
        stateMachineArn=response_create_v1["stateMachineArn"],
        definition=updated_definition,
        publish=True,
    )

    response = client.create_state_machine_alias(
        name="my-alias",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create_v1["stateMachineVersionArn"],
                "weight": 70,
            },
            {
                "stateMachineVersionArn": response_update_v2["stateMachineVersionArn"],
                "weight": 30,
            },
        ],
    )
    assert (
        response["stateMachineAliasArn"]
        == response_create_v1["stateMachineArn"] + ":" + "my-alias"
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert isinstance(response["creationDate"], datetime)


@mock_aws
def test_state_machine_describe_alias_succeeds():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    response_create_alias = client.create_state_machine_alias(
        name="my-alias",
        description="Test alias",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create["stateMachineVersionArn"],
                "weight": 100,
            }
        ],
    )

    response = client.describe_state_machine_alias(
        stateMachineAliasArn=response_create_alias["stateMachineAliasArn"]
    )

    assert (
        response["stateMachineAliasArn"]
        == response_create_alias["stateMachineAliasArn"]
    )
    assert response["name"] == "my-alias"
    assert response["description"] == "Test alias"
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert isinstance(response["creationDate"], datetime)
    assert isinstance(response["updateDate"], datetime)
    assert len(response["routingConfiguration"]) == 1
    assert (
        response["routingConfiguration"][0]["stateMachineVersionArn"]
        == response_create["stateMachineVersionArn"]
    )
    assert response["routingConfiguration"][0]["weight"] == 100


@mock_aws
def test_state_machine_describe_alias_fails_nonexistent():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    nonexistent_alias_arn = response_create["stateMachineArn"] + ":nonexistent"

    with pytest.raises(ClientError) as exc:
        client.describe_state_machine_alias(stateMachineAliasArn=nonexistent_alias_arn)

    assert exc.value.response["Error"]["Code"] == "ResourceNotFound"


@mock_aws
def test_state_machine_delete_alias_succeeds():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    response_create_alias = client.create_state_machine_alias(
        name="my-alias",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create["stateMachineVersionArn"],
                "weight": 100,
            }
        ],
    )

    delete_response = client.delete_state_machine_alias(
        stateMachineAliasArn=response_create_alias["stateMachineAliasArn"]
    )
    assert delete_response["ResponseMetadata"]["HTTPStatusCode"] == 200

    with pytest.raises(ClientError) as exc:
        client.describe_state_machine_alias(
            stateMachineAliasArn=response_create_alias["stateMachineAliasArn"]
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFound"


@mock_aws
def test_state_machine_delete_alias_fails_nonexistent():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    nonexistent_alias_arn = response_create["stateMachineArn"] + ":nonexistent"

    with pytest.raises(ClientError) as exc:
        client.delete_state_machine_alias(stateMachineAliasArn=nonexistent_alias_arn)

    assert exc.value.response["Error"]["Code"] == "ResourceNotFound"


@mock_aws
def test_list_state_machine_aliases_succeeds():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create_v1 = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    updated_definition = str(simple_definition).replace(
        "DefaultState", "DefaultStateV2"
    )
    response_update_v2 = client.update_state_machine(
        stateMachineArn=response_create_v1["stateMachineArn"],
        definition=updated_definition,
        publish=True,
    )

    response_alias_1 = client.create_state_machine_alias(
        name="alias-1",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create_v1["stateMachineVersionArn"],
                "weight": 100,
            }
        ],
    )

    response_alias_2 = client.create_state_machine_alias(
        name="alias-2",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create_v1["stateMachineVersionArn"],
                "weight": 50,
            },
            {
                "stateMachineVersionArn": response_update_v2["stateMachineVersionArn"],
                "weight": 50,
            },
        ],
    )

    response = client.list_state_machine_aliases(
        stateMachineArn=response_create_v1["stateMachineArn"]
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["stateMachineAliases"]) == 2
    alias_arns = [
        alias["stateMachineAliasArn"] for alias in response["stateMachineAliases"]
    ]
    assert response_alias_1["stateMachineAliasArn"] in alias_arns
    assert response_alias_2["stateMachineAliasArn"] in alias_arns


@mock_aws
def test_list_state_machine_aliases_empty():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    response = client.list_state_machine_aliases(
        stateMachineArn=response_create["stateMachineArn"]
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["stateMachineAliases"]) == 0
    assert "nextToken" not in response or response["nextToken"] is None


@mock_aws
def test_list_state_machine_aliases_nonexistent_state_machine():
    client = boto3.client("stepfunctions", region_name=region)
    nonexistent_arn = f"arn:aws:states:{region}:{ACCOUNT_ID}:stateMachine:nonexistent"

    with pytest.raises(ClientError) as exc:
        client.list_state_machine_aliases(stateMachineArn=nonexistent_arn)

    assert exc.value.response["Error"]["Code"] == "StateMachineDoesNotExist"


@mock_aws
def test_update_state_machine_alias_succeeds():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create_v1 = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    updated_definition = str(simple_definition).replace(
        "DefaultState", "DefaultStateV2"
    )
    response_update_v2 = client.update_state_machine(
        stateMachineArn=response_create_v1["stateMachineArn"],
        definition=updated_definition,
        publish=True,
    )

    response_create_alias = client.create_state_machine_alias(
        name="my-alias",
        description="test-description",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create_v1["stateMachineVersionArn"],
                "weight": 100,
            }
        ],
    )

    update_response = client.update_state_machine_alias(
        stateMachineAliasArn=response_create_alias["stateMachineAliasArn"],
        description="new-test-description",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create_v1["stateMachineVersionArn"],
                "weight": 50,
            },
            {
                "stateMachineVersionArn": response_update_v2["stateMachineVersionArn"],
                "weight": 50,
            },
        ],
    )

    assert update_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert isinstance(update_response["updateDate"], datetime)

    describe_response = client.describe_state_machine_alias(
        stateMachineAliasArn=response_create_alias["stateMachineAliasArn"]
    )
    assert len(describe_response["routingConfiguration"]) == 2
    assert describe_response["routingConfiguration"][0]["weight"] == 50
    assert describe_response["routingConfiguration"][1]["weight"] == 50
    assert describe_response["description"] == "new-test-description"


@mock_aws
def test_update_state_machine_alias_fails_without_params():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    response_create_alias = client.create_state_machine_alias(
        name="my-alias",
        routingConfiguration=[
            {
                "stateMachineVersionArn": response_create["stateMachineVersionArn"],
                "weight": 100,
            }
        ],
    )

    with pytest.raises(ClientError) as exc:
        client.update_state_machine_alias(
            stateMachineAliasArn=response_create_alias["stateMachineAliasArn"]
        )
    assert exc.value.response["Error"]["Code"] == "ValidationException"
    assert "at least one of" in exc.value.response["Error"]["Message"]


@mock_aws
def test_update_state_machine_alias_fails_nonexistent():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    response_create = client.create_state_machine(
        name=name,
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        publish=True,
    )

    nonexistent_alias_arn = response_create["stateMachineArn"] + ":nonexistent"

    with pytest.raises(ClientError) as exc:
        client.update_state_machine_alias(
            stateMachineAliasArn=nonexistent_alias_arn,
            description="New description",
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFound"
