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
    response = client.list_recipes(MaxResults=2, RecipeVersion='LATEST_WORKING')
    response["Recipes"].should.have.length_of(2)
    response.should.have.key("NextToken")


@mock_databrew
def test_list_recipes_from_next_token():
    client = _create_databrew_client()
    _create_test_recipes(client, 10)
    first_response = client.list_recipes(MaxResults=3, RecipeVersion='LATEST_WORKING')
    response = client.list_recipes(NextToken=first_response["NextToken"], RecipeVersion='LATEST_WORKING')
    response["Recipes"].should.have.length_of(7)


@mock_databrew
def test_list_recipes_with_max_results_greater_than_actual_results():
    client = _create_databrew_client()
    _create_test_recipes(client, 4)
    response = client.list_recipes(MaxResults=10, RecipeVersion='LATEST_WORKING')
    response["Recipes"].should.have.length_of(4)


@mock_databrew
def test_describe_recipe():
    client = _create_databrew_client()
    response = _create_test_recipe(client)

    recipe = client.describe_recipe(Name=response["Name"], RecipeVersion='LATEST_WORKING')

    recipe["Name"].should.equal(response["Name"])
    recipe["Steps"].should.have.length_of(1)


@mock_databrew
def test_update_recipe():
    client = _create_databrew_client()
    response = _create_test_recipe(client)

    recipe = client.update_recipe(
        Name=response["Name"],
        Steps=[
            {
                "Action": {
                    "Operation": "REMOVE_COMBINED",
                    "Parameters": {
                        "collapseConsecutiveWhitespace": "false",
                        "removeAllPunctuation": "false",
                        "removeAllQuotes": "false",
                        "removeAllWhitespace": "false",
                        "removeCustomCharacters": "true",
                        "removeCustomValue": "true",
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
    )

    recipe["Name"].should.equal(response["Name"])

    # Describe the recipe and change the changes
    recipe = client.describe_recipe(Name=response["Name"], RecipeVersion='LATEST_WORKING')
    recipe["Name"].should.equal(response["Name"])
    recipe["Steps"].should.have.length_of(1)
    recipe["Steps"][0]["Action"]["Parameters"]["removeCustomValue"].should.equal("true")


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
    recipe_name = response['Name']
    with pytest.raises(ClientError) as exc:
        _create_test_recipe(client, recipe_name=response["Name"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("ConflictException")
    err["Message"].should.equal(f"The recipe {recipe_name} already exists")


@mock_databrew
def test_publish_recipe():
    client = _create_databrew_client()

    response = _create_test_recipe(client)
    recipe_name = response['Name']

    publish_response = client.publish_recipe(Name=recipe_name, Description="test desc")
    publish_response["Name"].should.equal(recipe_name)

    recipe = client.describe_recipe(Name=recipe_name)
    recipe['Description'].should.equal("test desc")
    recipe['RecipeVersion'].should.equal("1.0")

    publish_response = client.publish_recipe(Name=recipe_name, Description="test desc")
    publish_response["Name"].should.equal(recipe_name)

    recipe = client.describe_recipe(Name=recipe_name)
    recipe['Description'].should.equal("test desc")
    recipe['RecipeVersion'].should.equal("2.0")
