import uuid

import boto3
import pytest
from botocore.exceptions import ClientError
from datetime import datetime

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
def test_recipe_list_with_invalid_version():
    client = _create_databrew_client()

    recipe_version = "1.1"
    with pytest.raises(ClientError) as exc:
        client.list_recipes(RecipeVersion=recipe_version)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        f"Invalid version {recipe_version}. "
        "Valid versions are LATEST_PUBLISHED and LATEST_WORKING."
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")


@mock_databrew
def test_list_recipes_with_max_results():
    client = _create_databrew_client()

    _create_test_recipes(client, 4)
    response = client.list_recipes(MaxResults=2, RecipeVersion="LATEST_WORKING")
    response["Recipes"].should.have.length_of(2)
    response.should.have.key("NextToken")


@mock_databrew
def test_list_recipes_from_next_token():
    client = _create_databrew_client()
    _create_test_recipes(client, 10)
    first_response = client.list_recipes(MaxResults=3, RecipeVersion="LATEST_WORKING")
    response = client.list_recipes(
        NextToken=first_response["NextToken"], RecipeVersion="LATEST_WORKING"
    )
    response["Recipes"].should.have.length_of(7)


@mock_databrew
def test_list_recipes_with_max_results_greater_than_actual_results():
    client = _create_databrew_client()
    _create_test_recipes(client, 4)
    response = client.list_recipes(MaxResults=10, RecipeVersion="LATEST_WORKING")
    response["Recipes"].should.have.length_of(4)


@mock_databrew
def test_list_recipe_versions_no_recipe():
    client = _create_databrew_client()
    recipe_name = "NotExist"
    response = client.list_recipe_versions(Name=recipe_name)
    response["Recipes"].should.have.length_of(0)


@mock_databrew
def test_list_recipe_versions_none_published():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    response = client.list_recipe_versions(Name=recipe_name)
    response["Recipes"].should.have.length_of(0)


@mock_databrew
def test_list_recipe_versions_one_published():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    client.publish_recipe(Name=recipe_name)
    response = client.list_recipe_versions(Name=recipe_name)
    response["Recipes"].should.have.length_of(1)
    response["Recipes"][0]["RecipeVersion"].should.equal("1.0")


@mock_databrew
def test_list_recipe_versions_two_published():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    client.publish_recipe(Name=recipe_name)
    client.publish_recipe(Name=recipe_name)
    response = client.list_recipe_versions(Name=recipe_name)
    response["Recipes"].should.have.length_of(2)
    response["Recipes"][0]["RecipeVersion"].should.equal("1.0")
    response["Recipes"][1]["RecipeVersion"].should.equal("2.0")


@mock_databrew
def test_describe_recipe_latest_working():
    client = _create_databrew_client()
    response = _create_test_recipe(client)

    recipe = client.describe_recipe(
        Name=response["Name"], RecipeVersion="LATEST_WORKING"
    )

    recipe["Name"].should.equal(response["Name"])
    recipe["Steps"].should.have.length_of(1)
    recipe["RecipeVersion"].should.equal("0.1")


@mock_databrew
def test_describe_recipe_with_version():
    client = _create_databrew_client()
    response = _create_test_recipe(client)

    recipe = client.describe_recipe(Name=response["Name"], RecipeVersion="0.1")

    recipe["Name"].should.equal(response["Name"])
    recipe["Steps"].should.have.length_of(1)
    recipe["RecipeVersion"].should.equal("0.1")


@mock_databrew
def test_describe_recipe_latest_published():
    client = _create_databrew_client()
    response = _create_test_recipe(client)

    client.publish_recipe(Name=response["Name"])
    recipe = client.describe_recipe(
        Name=response["Name"], RecipeVersion="LATEST_PUBLISHED"
    )

    recipe["Name"].should.equal(response["Name"])
    recipe["Steps"].should.have.length_of(1)
    recipe["RecipeVersion"].should.equal("1.0")


@mock_databrew
def test_describe_recipe_implicit_latest_published():
    client = _create_databrew_client()
    response = _create_test_recipe(client)

    client.publish_recipe(Name=response["Name"])
    recipe = client.describe_recipe(Name=response["Name"])

    recipe["Name"].should.equal(response["Name"])
    recipe["Steps"].should.have.length_of(1)
    recipe["RecipeVersion"].should.equal("1.0")


@mock_databrew
def test_describe_recipe_that_does_not_exist():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        client.describe_recipe(Name="DoseNotExist")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(
        "The recipe DoseNotExist for version LATEST_PUBLISHED wasn't found."
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)


@mock_databrew
def test_describe_recipe_with_long_name():
    client = _create_databrew_client()
    name = "a" * 256
    with pytest.raises(ClientError) as exc:
        client.describe_recipe(Name=name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        f"1 validation error detected: Value '{name}' at 'name' failed to satisfy constraint: "
        f"Member must have length less than or equal to 255"
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_describe_recipe_with_long_version():
    client = _create_databrew_client()
    version = "1" * 17
    with pytest.raises(ClientError) as exc:
        client.describe_recipe(Name="AnyName", RecipeVersion=version)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        f"1 validation error detected: Value '{version}' at 'recipeVersion' failed to satisfy constraint: "
        f"Member must have length less than or equal to 16"
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_describe_recipe_with_invalid_version():
    client = _create_databrew_client()
    name = "AnyName"
    version = "invalid"
    with pytest.raises(ClientError) as exc:
        client.describe_recipe(Name=name, RecipeVersion=version)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(f"Recipe {name} version {version} isn't valid.")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


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

    # Describe the recipe and check the changes
    recipe = client.describe_recipe(
        Name=response["Name"], RecipeVersion="LATEST_WORKING"
    )
    recipe["Name"].should.equal(response["Name"])
    recipe["Steps"].should.have.length_of(1)
    recipe["Steps"][0]["Action"]["Parameters"]["removeCustomValue"].should.equal("true")


@mock_databrew
def test_update_recipe_description():
    client = _create_databrew_client()
    response = _create_test_recipe(client)

    description = "NewDescription"
    recipe = client.update_recipe(
        Name=response["Name"], Steps=[], Description=description
    )

    recipe["Name"].should.equal(response["Name"])

    # Describe the recipe and check the changes
    recipe = client.describe_recipe(
        Name=response["Name"], RecipeVersion="LATEST_WORKING"
    )
    recipe["Name"].should.equal(response["Name"])
    recipe["Description"].should.equal(description)


@mock_databrew
def test_update_recipe_invalid():
    client = _create_databrew_client()

    recipe_name = "NotFound"
    with pytest.raises(ClientError) as exc:
        client.update_recipe(Name=recipe_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(f"The recipe {recipe_name} wasn't found")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)


@mock_databrew
def test_create_recipe_that_already_exists():
    client = _create_databrew_client()

    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    with pytest.raises(ClientError) as exc:
        _create_test_recipe(client, recipe_name=response["Name"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("ConflictException")
    err["Message"].should.equal(f"The recipe {recipe_name} already exists")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(409)


@mock_databrew
def test_publish_recipe():
    client = _create_databrew_client()

    response = _create_test_recipe(client)
    recipe_name = response["Name"]

    # Before a recipe is published, we should not be able to retrieve a published version
    with pytest.raises(ClientError) as exc:
        recipe = client.describe_recipe(Name=recipe_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")

    dt_before_publish = datetime.now().astimezone()

    # Publish the recipe
    publish_response = client.publish_recipe(Name=recipe_name, Description="1st desc")
    publish_response["Name"].should.equal(recipe_name)

    # Recipe is now published, so check we can retrieve the published version
    recipe = client.describe_recipe(Name=recipe_name)
    recipe["Description"].should.equal("1st desc")
    recipe["RecipeVersion"].should.equal("1.0")
    recipe["PublishedDate"].should.be.greater_than(dt_before_publish)
    first_published_date = recipe["PublishedDate"]

    # Publish the recipe a 2nd time
    publish_response = client.publish_recipe(Name=recipe_name, Description="2nd desc")
    publish_response["Name"].should.equal(recipe_name)

    recipe = client.describe_recipe(Name=recipe_name)
    recipe["Description"].should.equal("2nd desc")
    recipe["RecipeVersion"].should.equal("2.0")
    recipe["PublishedDate"].should.be.greater_than(first_published_date)


@mock_databrew
def test_publish_recipe_that_does_not_exist():
    client = _create_databrew_client()
    with pytest.raises(ClientError) as exc:
        client.publish_recipe(Name="DoesNotExist")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)


@mock_databrew
def test_publish_long_recipe_name():
    client = _create_databrew_client()
    name = "a" * 256
    with pytest.raises(ClientError) as exc:
        client.publish_recipe(Name=name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        f"1 validation error detected: Value '{name}' at 'name' failed to satisfy constraint: "
        f"Member must have length less than or equal to 255"
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")


@mock_databrew
def test_delete_recipe_version():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    client.delete_recipe_version(Name=recipe_name, RecipeVersion="LATEST_WORKING")
    with pytest.raises(ClientError) as exc:
        client.describe_recipe(Name=recipe_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)


@mock_databrew
def test_delete_recipe_version_published():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    client.publish_recipe(Name=recipe_name)
    client.delete_recipe_version(Name=recipe_name, RecipeVersion="1.0")
    with pytest.raises(ClientError) as exc:
        client.describe_recipe(Name=recipe_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)
    recipe = client.describe_recipe(Name=recipe_name, RecipeVersion="1.1")
    recipe["RecipeVersion"].should.equal("1.1")


@mock_databrew
def test_delete_recipe_version_latest_working_after_publish():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    client.publish_recipe(Name=recipe_name)
    with pytest.raises(ClientError) as exc:
        client.delete_recipe_version(Name=recipe_name, RecipeVersion="LATEST_WORKING")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Recipe version LATEST_WORKING is not allowed to be deleted"
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_delete_recipe_version_latest_working_numeric_after_publish():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    client.publish_recipe(Name=recipe_name)
    with pytest.raises(ClientError) as exc:
        client.delete_recipe_version(Name=recipe_name, RecipeVersion="1.1")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("Recipe version 1.1 is not allowed to be deleted")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_delete_recipe_version_invalid_version_string():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    recipe_version = "NotValid"
    client.publish_recipe(Name=recipe_name)
    with pytest.raises(ClientError) as exc:
        client.delete_recipe_version(Name=recipe_name, RecipeVersion=recipe_version)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        f"Recipe {recipe_name} version {recipe_version} is invalid."
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_delete_recipe_version_invalid_version_length():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    recipe_version = "1" * 17
    client.publish_recipe(Name=recipe_name)
    with pytest.raises(ClientError) as exc:
        client.delete_recipe_version(Name=recipe_name, RecipeVersion=recipe_version)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        f"Recipe {recipe_name} version {recipe_version} is invalid."
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_delete_recipe_version_unknown_recipe():
    client = _create_databrew_client()
    recipe_name = "Unknown"
    with pytest.raises(ClientError) as exc:
        client.delete_recipe_version(Name=recipe_name, RecipeVersion="1.1")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(f"The recipe {recipe_name} wasn't found")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)


@mock_databrew
def test_delete_recipe_version_unknown_version():
    client = _create_databrew_client()
    response = _create_test_recipe(client)
    recipe_name = response["Name"]
    recipe_version = "1.1"
    with pytest.raises(ClientError) as exc:
        client.delete_recipe_version(Name=recipe_name, RecipeVersion=recipe_version)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(
        f"The recipe {recipe_name} version {recipe_version} wasn't found."
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)
