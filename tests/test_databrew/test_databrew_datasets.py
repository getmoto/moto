import uuid

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_databrew


def _create_databrew_client():
    client = boto3.client("databrew", region_name="us-west-1")
    return client


def _create_test_dataset(
    client,
    tags=None,
    dataset_name=None,
    dataset_format="JSON",
    dataset_format_options=None,
):
    if dataset_name is None:
        dataset_name = str(uuid.uuid4())

    if not dataset_format_options:
        if dataset_format == "JSON":
            dataset_format_options = {"Json": {"MultiLine": True}}
        elif dataset_format == "CSV":
            dataset_format_options = {"Csv": {"Delimiter": ",", "HeaderRow": False}}
        elif dataset_format == "EXCEL":
            dataset_format_options = {
                "Excel": {
                    "SheetNames": [
                        "blaa",
                    ],
                    "SheetIndexes": [
                        123,
                    ],
                    "HeaderRow": True,
                }
            }

    return client.create_dataset(
        Name=dataset_name,
        Format=dataset_format,
        FormatOptions=dataset_format_options,
        Input={
            "S3InputDefinition": {
                "Bucket": "somerandombucketname",
            },
            "DataCatalogInputDefinition": {
                "DatabaseName": "somedbname",
                "TableName": "sometablename",
                "TempDirectory": {
                    "Bucket": "sometempbucketname",
                },
            },
            "DatabaseInputDefinition": {
                "GlueConnectionName": "someglueconnectionname",
                "TempDirectory": {
                    "Bucket": "sometempbucketname",
                },
            },
        },
        PathOptions={
            "LastModifiedDateCondition": {
                "Expression": "string",
                "ValuesMap": {"string": "string"},
            },
            "FilesLimit": {
                "MaxFiles": 123,
                "OrderedBy": "LAST_MODIFIED_DATE",
                "Order": "ASCENDING",
            },
            "Parameters": {
                "string": {
                    "Name": "string",
                    "Type": "string",
                    "CreateColumn": False,
                    "Filter": {
                        "Expression": "string",
                        "ValuesMap": {"string": "string"},
                    },
                }
            },
        },
        Tags=tags or {},
    )


def _create_test_datasets(client, count):
    for _ in range(count):
        _create_test_dataset(client)


@mock_databrew
def test_dataset_list_when_empty():
    client = _create_databrew_client()

    response = client.list_datasets()
    response.should.have.key("Datasets")
    response["Datasets"].should.have.length_of(0)


@mock_databrew
def test_list_datasets_with_max_results():
    client = _create_databrew_client()

    _create_test_datasets(client, 4)
    response = client.list_datasets(MaxResults=2)
    response["Datasets"].should.have.length_of(2)
    response.should.have.key("NextToken")


@mock_databrew
def test_list_datasets_from_next_token():
    client = _create_databrew_client()
    _create_test_datasets(client, 10)
    first_response = client.list_datasets(MaxResults=3)
    response = client.list_datasets(NextToken=first_response["NextToken"])
    response["Datasets"].should.have.length_of(7)


@mock_databrew
def test_list_datasets_with_max_results_greater_than_actual_results():
    client = _create_databrew_client()
    _create_test_datasets(client, 4)
    response = client.list_datasets(MaxResults=10)
    response["Datasets"].should.have.length_of(4)


@mock_databrew
def test_describe_dataset():
    client = _create_databrew_client()

    # region basic test
    response = _create_test_dataset(client)
    dataset = client.describe_dataset(Name=response["Name"])
    dataset["Name"].should.equal(response["Name"])
    # endregion

    # region JSON test
    response = _create_test_dataset(client, dataset_format="CSV")
    dataset = client.describe_dataset(Name=response["Name"])
    dataset["Format"].should.equal("CSV")
    # endregion


@mock_databrew
def test_describe_dataset_that_does_not_exist():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        client.describe_dataset(Name="DoseNotExist")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("One or more resources can't be found.")


@mock_databrew
def test_create_dataset_that_already_exists():
    client = _create_databrew_client()

    response = _create_test_dataset(client)

    with pytest.raises(ClientError) as exc:
        _create_test_dataset(client, dataset_name=response["Name"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("AlreadyExistsException")
    err["Message"].should.equal(f"{response['Name']} already exists.")


@mock_databrew
def test_delete_dataset():
    client = _create_databrew_client()
    response = _create_test_dataset(client)

    # Check dataset exists
    dataset = client.describe_dataset(Name=response["Name"])
    dataset["Name"].should.equal(response["Name"])

    # Delete the dataset
    client.delete_dataset(Name=response["Name"])

    # Check it does not exist anymore
    with pytest.raises(ClientError) as exc:
        client.describe_dataset(Name=response["Name"])

    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("One or more resources can't be found.")

    # Check that a dataset that does not exist errors
    with pytest.raises(ClientError) as exc:
        client.delete_dataset(Name=response["Name"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("One or more resources can't be found.")


@mock_databrew
def test_update_dataset():
    client = _create_databrew_client()
    response = _create_test_dataset(client)

    # Update the dataset and check response
    dataset = client.update_dataset(
        Name=response["Name"],
        Format="TEST",
        Input={
            "S3InputDefinition": {
                "Bucket": "somerandombucketname",
            },
            "DataCatalogInputDefinition": {
                "DatabaseName": "somedbname",
                "TableName": "sometablename",
                "TempDirectory": {
                    "Bucket": "sometempbucketname",
                },
            },
            "DatabaseInputDefinition": {
                "GlueConnectionName": "someglueconnectionname",
                "TempDirectory": {
                    "Bucket": "sometempbucketname",
                },
            },
        },
    )
    dataset["Name"].should.equal(response["Name"])

    # Describe the dataset and check the changes
    dataset = client.describe_dataset(Name=response["Name"])
    dataset["Name"].should.equal(response["Name"])
    dataset["Format"].should.equal("TEST")


@mock_databrew
def test_update_dataset_that_does_not_exist():
    client = _create_databrew_client()

    # Update the dataset and check response
    with pytest.raises(ClientError) as exc:
        client.update_dataset(
            Name="RANDOMNAME",
            Format="TEST",
            Input={
                "S3InputDefinition": {
                    "Bucket": "somerandombucketname",
                },
                "DataCatalogInputDefinition": {
                    "DatabaseName": "somedbname",
                    "TableName": "sometablename",
                    "TempDirectory": {
                        "Bucket": "sometempbucketname",
                    },
                },
                "DatabaseInputDefinition": {
                    "GlueConnectionName": "someglueconnectionname",
                    "TempDirectory": {
                        "Bucket": "sometempbucketname",
                    },
                },
            },
        )

    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("One or more resources can't be found.")
