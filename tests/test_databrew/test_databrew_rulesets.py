import uuid

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_databrew


def _create_databrew_client():
    client = boto3.client("databrew", region_name="us-west-1")
    return client


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


@mock_databrew
def test_ruleset_list_when_empty():
    client = _create_databrew_client()

    response = client.list_rulesets()
    response.should.have.key("Rulesets")
    response["Rulesets"].should.have.length_of(0)


@mock_databrew
def test_list_ruleset_with_max_results():
    client = _create_databrew_client()

    _create_test_rulesets(client, 4)
    response = client.list_rulesets(MaxResults=2)
    response["Rulesets"].should.have.length_of(2)
    response.should.have.key("NextToken")


@mock_databrew
def test_list_rulesets_from_next_token():
    client = _create_databrew_client()
    _create_test_rulesets(client, 10)
    first_response = client.list_rulesets(MaxResults=3)
    response = client.list_rulesets(NextToken=first_response["NextToken"])
    response["Rulesets"].should.have.length_of(7)


@mock_databrew
def test_list_rulesets_with_max_results_greater_than_actual_results():
    client = _create_databrew_client()
    _create_test_rulesets(client, 4)
    response = client.list_rulesets(MaxResults=10)
    response["Rulesets"].should.have.length_of(4)


@mock_databrew
def test_describe_ruleset():
    client = _create_databrew_client()
    response = _create_test_ruleset(client)

    ruleset = client.describe_ruleset(Name=response["Name"])

    ruleset["Name"].should.equal(response["Name"])
    ruleset["Rules"].should.have.length_of(1)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_databrew
def test_describe_ruleset_that_does_not_exist():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        client.describe_ruleset(Name="DoseNotExist")
    err = exc.value.response["Error"]
    err["Code"].should.equal("EntityNotFoundException")
    err["Message"].should.equal("Ruleset DoseNotExist not found.")


@mock_databrew
def test_create_ruleset_that_already_exists():
    client = _create_databrew_client()

    response = _create_test_ruleset(client)

    with pytest.raises(ClientError) as exc:
        _create_test_ruleset(client, ruleset_name=response["Name"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("AlreadyExistsException")
    err["Message"].should.equal("Ruleset already exists.")


@mock_databrew
def test_delete_ruleset():
    client = _create_databrew_client()
    response = _create_test_ruleset(client)
    ruleset_name = response["Name"]

    # Check ruleset exists
    ruleset = client.describe_ruleset(Name=ruleset_name)
    ruleset["Name"].should.equal(response["Name"])

    # Delete the ruleset
    response = client.delete_ruleset(Name=ruleset_name)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Name"].should.equal(ruleset_name)

    # Check it does not exist anymore
    with pytest.raises(ClientError) as exc:
        client.describe_ruleset(Name=ruleset_name)

    err = exc.value.response["Error"]
    err["Code"].should.equal("EntityNotFoundException")
    err["Message"].should.equal(f"Ruleset {ruleset_name} not found.")

    # Check that a ruleset that does not exist errors
    with pytest.raises(ClientError) as exc:
        client.delete_ruleset(Name=ruleset_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("EntityNotFoundException")
    err["Message"].should.equal(f"Ruleset {ruleset_name} not found.")


@mock_databrew
def test_update_ruleset():
    client = _create_databrew_client()
    response = _create_test_ruleset(client)

    # Update the ruleset and check response
    ruleset = client.update_ruleset(
        Name=response["Name"],
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
    ruleset["Name"].should.equal(response["Name"])

    # Describe the ruleset and check the changes
    ruleset = client.describe_ruleset(Name=response["Name"])
    ruleset["Name"].should.equal(response["Name"])
    ruleset["Rules"].should.have.length_of(1)
    ruleset["Rules"][0]["SubstitutionMap"][":val1"].should.equal("10")
