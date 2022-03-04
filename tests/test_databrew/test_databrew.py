import uuid

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_databrew


def _create_databrew_client():
    client = boto3.client("databrew", region_name="us-west-1")
    return client


def _create_test_recipe(client, tags=None, recipe_name=None):
    if recipe_name is None:
        recipe_name = str(uuid.uuid4())

    return client.create_recipe(
        Name=recipe_name,
        Steps=[
            {
                "Action": {
                    "Operation": "REMOVE_COMBINED",
                    "Parameters": {
                        "collapseConsecutiveWhitespace": "false",
                        "removeAllPunctuation": "false",
                        "removeAllQuotes": "false",
                        "removeAllWhitespace": "false",
                        "removeCustomCharacters": "false",
                        "removeCustomValue": "false",
                        "removeLeadingAndTrailingPunctuation": "false",
                        "removeLeadingAndTrailingQuotes": "false",
                        "removeLeadingAndTrailingWhitespace": "false",
                        "removeLetters": "false",
                        "removeNumbers": "false",
                        "removeSpecialCharacters": "true",
                        "sourceColumn": "FakeColumn",
                    },
                }
            }
        ],
        Tags=tags or {},
    )


def _create_test_recipes(client, count):
    for _ in range(count):
        _create_test_recipe(client)


@mock_databrew
def test_recipe_list_when_empty():
    client = _create_databrew_client()

    response = client.list_recipes()
    response.should.have.key("Recipes")
    response["Recipes"].should.have.length_of(0)


@mock_databrew
def test_list_recipes_with_max_results():
    client = _create_databrew_client()

    _create_test_recipes(client, 4)
    response = client.list_recipes(MaxResults=2)
    response["Recipes"].should.have.length_of(2)
    response.should.have.key("NextToken")


@mock_databrew
def test_list_recipes_from_next_token():
    client = _create_databrew_client()
    _create_test_recipes(client, 10)
    first_response = client.list_recipes(MaxResults=3)
    response = client.list_recipes(NextToken=first_response["NextToken"])
    response["Recipes"].should.have.length_of(7)


@mock_databrew
def test_list_recipes_with_max_results_greater_than_actual_results():
    client = _create_databrew_client()
    _create_test_recipes(client, 4)
    response = client.list_recipes(MaxResults=10)
    response["Recipes"].should.have.length_of(4)


@mock_databrew
def test_describe_recipe():
    client = _create_databrew_client()
    response = _create_test_recipe(client)

    recipe = client.describe_recipe(Name=response["Name"])

    recipe["Name"].should.equal(response["Name"])
    recipe["Steps"].should.have.length_of(1)


@mock_databrew
def test_describe_recipe_that_does_not_exist():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        client.describe_recipe(Name="DoseNotExist")
    err = exc.value.response["Error"]
    err["Code"].should.equal("EntityNotFoundException")
    err["Message"].should.equal("Recipe DoseNotExist not found.")


@mock_databrew
def test_create_recipe_that_already_exists():
    client = _create_databrew_client()

    response = _create_test_recipe(client)

    with pytest.raises(ClientError) as exc:
        _create_test_recipe(client, recipe_name=response["Name"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("AlreadyExistsException")
    err["Message"].should.equal("Recipe already exists.")
