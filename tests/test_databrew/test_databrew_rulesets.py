import uuid

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


def _create_databrew_client():
    return boto3.client("databrew", region_name="us-west-1")


def _create_test_ruleset(client, tags=None, ruleset_name=None):
    if ruleset_name is None:
        ruleset_name = str(uuid.uuid4())

    return client.create_ruleset(
        Name=ruleset_name,
        TargetArn="arn:aws:databrew:eu-west-1:000000000000:dataset/fake-dataset",
        Rules=[
            {
                "Name": "Assert values > 0",
                "Disabled": False,
                "CheckExpression": ":col1 > :val1",
                "SubstitutionMap": {":col1": "`Value`", ":val1": "0"},
                "Threshold": {
                    "Value": 100,
                    "Type": "GREATER_THAN_OR_EQUAL",
                    "Unit": "PERCENTAGE",
                },
            }
        ],
        Tags=tags or {},
    )


def _create_test_rulesets(client, count):
    for _ in range(count):
        _create_test_ruleset(client)


@mock_aws
def test_ruleset_list_when_empty():
    client = _create_databrew_client()

    response = client.list_rulesets()
    assert "Rulesets" in response
    assert len(response["Rulesets"]) == 0


@mock_aws
def test_list_ruleset_with_max_results():
    client = _create_databrew_client()

    _create_test_rulesets(client, 4)
    response = client.list_rulesets(MaxResults=2)
    assert len(response["Rulesets"]) == 2
    assert "NextToken" in response


@mock_aws
def test_list_rulesets_from_next_token():
    client = _create_databrew_client()
    _create_test_rulesets(client, 10)
    first_response = client.list_rulesets(MaxResults=3)
    response = client.list_rulesets(NextToken=first_response["NextToken"])
    assert len(response["Rulesets"]) == 7


@mock_aws
def test_list_rulesets_with_max_results_greater_than_actual_results():
    client = _create_databrew_client()
    _create_test_rulesets(client, 4)
    response = client.list_rulesets(MaxResults=10)
    assert len(response["Rulesets"]) == 4


@mock_aws
def test_describe_ruleset():
    client = _create_databrew_client()
    response = _create_test_ruleset(client)

    ruleset = client.describe_ruleset(Name=response["Name"])

    assert ruleset["Name"] == response["Name"]
    assert len(ruleset["Rules"]) == 1
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_describe_ruleset_that_does_not_exist():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        client.describe_ruleset(Name="DoseNotExist")
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert err["Message"] == "Ruleset DoseNotExist not found."


@mock_aws
def test_create_ruleset_that_already_exists():
    client = _create_databrew_client()

    response = _create_test_ruleset(client)

    with pytest.raises(ClientError) as exc:
        _create_test_ruleset(client, ruleset_name=response["Name"])
    err = exc.value.response["Error"]
    assert err["Code"] == "AlreadyExistsException"
    assert err["Message"] == "Ruleset already exists."


@mock_aws
def test_delete_ruleset():
    client = _create_databrew_client()
    response = _create_test_ruleset(client)
    ruleset_name = response["Name"]

    # Check ruleset exists
    ruleset = client.describe_ruleset(Name=ruleset_name)
    assert ruleset["Name"] == response["Name"]

    # Delete the ruleset
    response = client.delete_ruleset(Name=ruleset_name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["Name"] == ruleset_name

    # Check it does not exist anymore
    with pytest.raises(ClientError) as exc:
        client.describe_ruleset(Name=ruleset_name)

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert err["Message"] == f"Ruleset {ruleset_name} not found."

    # Check that a ruleset that does not exist errors
    with pytest.raises(ClientError) as exc:
        client.delete_ruleset(Name=ruleset_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert err["Message"] == f"Ruleset {ruleset_name} not found."


@mock_aws
@pytest.mark.parametrize("name", ["name", "name with space"])
def test_update_ruleset(name):
    client = _create_databrew_client()
    _create_test_ruleset(client, ruleset_name=name)

    # Update the ruleset and check response
    ruleset = client.update_ruleset(
        Name=name,
        Rules=[
            {
                "Name": "Assert values > 0",
                "Disabled": False,
                "CheckExpression": ":col1 > :val1",
                "SubstitutionMap": {":col1": "`Value`", ":val1": "10"},
                "Threshold": {
                    "Value": 100,
                    "Type": "GREATER_THAN_OR_EQUAL",
                    "Unit": "PERCENTAGE",
                },
            }
        ],
    )
    assert ruleset["Name"] == name

    # Describe the ruleset and check the changes
    ruleset = client.describe_ruleset(Name=name)
    assert ruleset["Name"] == name
    assert len(ruleset["Rules"]) == 1
    assert ruleset["Rules"][0]["SubstitutionMap"][":val1"] == "10"
