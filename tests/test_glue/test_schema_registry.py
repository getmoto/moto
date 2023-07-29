"""Unit tests for glue-schema-registry-supported APIs."""
import boto3
import pytest
from botocore.client import ClientError
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from moto import mock_glue

from . import helpers
from .fixtures.schema_registry import (
    TEST_REGISTRY_NAME,
    TEST_REGISTRY_ARN,
    TEST_DESCRIPTION,
    TEST_TAGS,
    TEST_SCHEMA_NAME,
    TEST_SCHEMA_ARN,
    TEST_AVRO_SCHEMA_DEFINITION,
    TEST_NEW_AVRO_SCHEMA_DEFINITION,
    TEST_JSON_SCHEMA_DEFINITION,
    TEST_NEW_JSON_SCHEMA_DEFINITION,
    TEST_PROTOBUF_SCHEMA_DEFINITION,
    TEST_NEW_PROTOBUF_SCHEMA_DEFINITION,
    TEST_AVRO_DATA_FORMAT,
    TEST_JSON_DATA_FORMAT,
    TEST_PROTOBUF_DATA_FORMAT,
    TEST_REGISTRY_ID,
    TEST_SCHEMA_ID,
    TEST_BACKWARD_COMPATIBILITY,
    TEST_DISABLED_COMPATIBILITY,
    TEST_AVAILABLE_STATUS,
    TEST_SCHEMA_VERSION_NUMBER,
    TEST_SCHEMA_VERSION_NUMBER_LATEST_VERSION,
    TEST_VERSION_ID,
    TEST_INVALID_SCHEMA_NAME_DOES_NOT_EXIST,
    TEST_INVALID_SCHEMA_ID_SCHEMA_DOES_NOT_EXIST,
    TEST_INVALID_SCHEMA_ID_REGISTRY_DOES_NOT_EXIST,
    TEST_METADATA_KEY_VALUE,
    TEST_METADATA_KEY,
    TEST_METADATA_VALUE,
    TEST_DELETING_STATUS,
)


@pytest.fixture(name="client")
def fixture_client():
    with mock_glue():
        yield boto3.client("glue", region_name="us-east-1")


# Test create_registry
def test_create_registry_valid_input(client):
    response = client.create_registry(
        RegistryName=TEST_REGISTRY_NAME, Description=TEST_DESCRIPTION, Tags=TEST_TAGS
    )
    assert response["RegistryName"] == TEST_REGISTRY_NAME
    assert response["Description"] == TEST_DESCRIPTION
    assert response["Tags"] == TEST_TAGS
    assert response["RegistryArn"] == TEST_REGISTRY_ARN


def test_create_registry_valid_partial_input(client):
    response = client.create_registry(RegistryName=TEST_REGISTRY_NAME)
    assert response["RegistryName"] == TEST_REGISTRY_NAME
    assert response["RegistryArn"] == TEST_REGISTRY_ARN


def test_create_registry_invalid_registry_name_too_long(client):
    registry_name = ""
    for _ in range(80):
        registry_name = registry_name + "toolong"

    with pytest.raises(ClientError) as exc:
        client.create_registry(RegistryName=registry_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "The resource name contains too many or too few characters. Parameter Name: registryName"
    )


def test_create_registry_more_than_allowed(client):
    for i in range(10):
        client.create_registry(RegistryName=TEST_REGISTRY_NAME + str(i))

    with pytest.raises(ClientError) as exc:
        client.create_registry(RegistryName=TEST_REGISTRY_NAME)

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNumberLimitExceededException"
    assert (
        err["Message"]
        == "More registries cannot be created. The maximum limit has been reached."
    )


def test_create_registry_invalid_registry_name(client):
    invalid_registry_name = "A,B,C"

    with pytest.raises(ClientError) as exc:
        client.create_registry(RegistryName=invalid_registry_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "The parameter value contains one or more characters that are not valid. Parameter Name: registryName"
    )


def test_create_registry_already_exists(client):
    client.create_registry(RegistryName=TEST_REGISTRY_NAME)

    with pytest.raises(ClientError) as exc:
        client.create_registry(RegistryName=TEST_REGISTRY_NAME)
    err = exc.value.response["Error"]
    assert err["Code"] == "AlreadyExistsException"
    assert (
        err["Message"] == "Registry already exists. RegistryName: " + TEST_REGISTRY_NAME
    )


def test_create_registry_invalid_description_too_long(client):
    description = ""
    for _ in range(350):
        description = description + "toolong"

    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName=TEST_REGISTRY_NAME,
            Description=description,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "The resource name contains too many or too few characters. Parameter Name: description"
    )


def test_create_registry_invalid_number_of_tags(client):
    tags = {}
    for i in range(51):
        key = "k" + str(i)
        val = "v" + str(i)
        tags[key] = val

    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName=TEST_REGISTRY_NAME,
            Tags=tags,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert err["Message"] == "New Tags cannot be empty or more than 50"


# Test create_schema
def test_create_schema_valid_input_registry_name_avro(client):
    helpers.create_registry(client)

    response = client.create_schema(
        RegistryId=TEST_REGISTRY_ID,
        SchemaName=TEST_SCHEMA_NAME,
        DataFormat=TEST_AVRO_DATA_FORMAT,
        Compatibility=TEST_BACKWARD_COMPATIBILITY,
        SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION,
        Description=TEST_DESCRIPTION,
        Tags=TEST_TAGS,
    )
    assert response["RegistryName"] == TEST_REGISTRY_NAME
    assert response["RegistryArn"] == TEST_REGISTRY_ARN
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["Description"] == TEST_DESCRIPTION
    assert response["DataFormat"] == TEST_AVRO_DATA_FORMAT
    assert response["Compatibility"] == TEST_BACKWARD_COMPATIBILITY
    assert response["SchemaCheckpoint"] == 1
    assert response["LatestSchemaVersion"] == 1
    assert response["NextSchemaVersion"] == 2
    assert response["SchemaStatus"] == TEST_AVAILABLE_STATUS
    assert response["Tags"] == TEST_TAGS
    assert "SchemaVersionId" in response
    assert response["SchemaVersionStatus"] == TEST_AVAILABLE_STATUS


def test_create_schema_valid_input_registry_name_json(client):
    helpers.create_registry(client)

    response = client.create_schema(
        RegistryId=TEST_REGISTRY_ID,
        SchemaName=TEST_SCHEMA_NAME,
        DataFormat=TEST_JSON_DATA_FORMAT,
        Compatibility=TEST_BACKWARD_COMPATIBILITY,
        SchemaDefinition=TEST_JSON_SCHEMA_DEFINITION,
        Description=TEST_DESCRIPTION,
        Tags=TEST_TAGS,
    )
    assert response["RegistryName"] == TEST_REGISTRY_NAME
    assert response["RegistryArn"] == TEST_REGISTRY_ARN
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["Description"] == TEST_DESCRIPTION
    assert response["DataFormat"] == TEST_JSON_DATA_FORMAT
    assert response["Compatibility"] == TEST_BACKWARD_COMPATIBILITY
    assert response["SchemaCheckpoint"] == 1
    assert response["LatestSchemaVersion"] == 1
    assert response["NextSchemaVersion"] == 2
    assert response["SchemaStatus"] == TEST_AVAILABLE_STATUS
    assert response["Tags"] == TEST_TAGS
    assert "SchemaVersionId" in response
    assert response["SchemaVersionStatus"] == TEST_AVAILABLE_STATUS


def test_create_schema_valid_input_registry_name_protobuf(client):
    helpers.create_registry(client)

    response = client.create_schema(
        RegistryId=TEST_REGISTRY_ID,
        SchemaName=TEST_SCHEMA_NAME,
        DataFormat=TEST_PROTOBUF_DATA_FORMAT,
        Compatibility=TEST_BACKWARD_COMPATIBILITY,
        SchemaDefinition=TEST_PROTOBUF_SCHEMA_DEFINITION,
        Description=TEST_DESCRIPTION,
        Tags=TEST_TAGS,
    )
    assert response["RegistryName"] == TEST_REGISTRY_NAME
    assert response["RegistryArn"] == TEST_REGISTRY_ARN
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["Description"] == TEST_DESCRIPTION
    assert response["DataFormat"] == TEST_PROTOBUF_DATA_FORMAT
    assert response["Compatibility"] == TEST_BACKWARD_COMPATIBILITY
    assert response["SchemaCheckpoint"] == 1
    assert response["LatestSchemaVersion"] == 1
    assert response["NextSchemaVersion"] == 2
    assert response["SchemaStatus"] == TEST_AVAILABLE_STATUS
    assert response["Tags"] == TEST_TAGS
    assert "SchemaVersionId" in response
    assert response["SchemaVersionStatus"] == TEST_AVAILABLE_STATUS


def test_create_schema_valid_input_registry_arn(client):
    helpers.create_registry(client)

    registry_id = {"RegistryArn": f"{TEST_REGISTRY_ARN}"}
    response = client.create_schema(
        RegistryId=registry_id,
        SchemaName=TEST_SCHEMA_NAME,
        DataFormat=TEST_AVRO_DATA_FORMAT,
        Compatibility=TEST_BACKWARD_COMPATIBILITY,
        SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION,
        Description=TEST_DESCRIPTION,
        Tags=TEST_TAGS,
    )
    assert response["RegistryName"] == TEST_REGISTRY_NAME
    assert response["RegistryArn"] == TEST_REGISTRY_ARN
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["Description"] == TEST_DESCRIPTION
    assert response["DataFormat"] == TEST_AVRO_DATA_FORMAT
    assert response["Compatibility"] == TEST_BACKWARD_COMPATIBILITY
    assert response["SchemaCheckpoint"] == 1
    assert response["LatestSchemaVersion"] == 1
    assert response["NextSchemaVersion"] == 2
    assert response["SchemaStatus"] == TEST_AVAILABLE_STATUS
    assert response["Tags"] == TEST_TAGS
    assert "SchemaVersionId" in response
    assert response["SchemaVersionStatus"] == TEST_AVAILABLE_STATUS


def test_create_schema_valid_partial_input(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    assert response["RegistryName"] == TEST_REGISTRY_NAME
    assert response["RegistryArn"] == TEST_REGISTRY_ARN
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["DataFormat"] == TEST_AVRO_DATA_FORMAT
    assert response["Compatibility"] == TEST_BACKWARD_COMPATIBILITY
    assert response["SchemaCheckpoint"] == 1
    assert response["LatestSchemaVersion"] == 1
    assert response["NextSchemaVersion"] == 2
    assert response["SchemaStatus"] == TEST_AVAILABLE_STATUS
    assert "SchemaStatus" in response
    assert "SchemaVersionId" in response
    assert response["SchemaVersionStatus"] == TEST_AVAILABLE_STATUS


def test_create_schema_valid_default_registry(client):
    helpers.create_registry(client)

    empty_registry_id = {}

    response = helpers.create_schema(client, registry_id=empty_registry_id)
    default_registry_name = "default-registry"
    assert response["RegistryName"] == default_registry_name
    assert (
        response["RegistryArn"]
        == f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:registry/{default_registry_name}"
    )
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert (
        response["SchemaArn"]
        == f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:schema/{default_registry_name}/{TEST_SCHEMA_NAME}"
    )
    assert response["DataFormat"] == TEST_AVRO_DATA_FORMAT
    assert response["Compatibility"] == TEST_BACKWARD_COMPATIBILITY
    assert response["SchemaCheckpoint"] == 1
    assert response["LatestSchemaVersion"] == 1
    assert response["NextSchemaVersion"] == 2
    assert response["SchemaStatus"] == TEST_AVAILABLE_STATUS
    assert "SchemaStatus" in response
    assert "SchemaVersionId" in response
    assert response["SchemaVersionStatus"] == TEST_AVAILABLE_STATUS


def test_create_schema_valid_default_registry_in_registry_id(client):
    helpers.create_registry(client)

    default_registry_name = "default-registry"
    registry_id_default_registry = {"RegistryName": f"{default_registry_name}"}

    response = helpers.create_schema(client, registry_id=registry_id_default_registry)

    assert response["RegistryName"] == default_registry_name
    assert (
        response["RegistryArn"]
        == f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:registry/{default_registry_name}"
    )
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert (
        response["SchemaArn"]
        == f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:schema/{default_registry_name}/{TEST_SCHEMA_NAME}"
    )
    assert response["DataFormat"] == TEST_AVRO_DATA_FORMAT
    assert response["Compatibility"] == TEST_BACKWARD_COMPATIBILITY
    assert response["SchemaCheckpoint"] == 1
    assert response["LatestSchemaVersion"] == 1
    assert response["NextSchemaVersion"] == 2
    assert response["SchemaStatus"] == TEST_AVAILABLE_STATUS
    assert "SchemaStatus" in response
    assert "SchemaVersionId" in response
    assert response["SchemaVersionStatus"] == TEST_AVAILABLE_STATUS


def test_create_schema_invalid_registry_arn(client):
    helpers.create_registry(client)

    invalid_registry_arn = (
        f"invalid:arn:aws:glue:us-east-1:{ACCOUNT_ID}:registry/{TEST_REGISTRY_NAME}"
    )
    invalid_registry_id = {"RegistryArn": f"{invalid_registry_arn}"}

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(client, registry_id=invalid_registry_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "The parameter value contains one or more characters that are not valid. Parameter Name: registryArn"
    )


def test_create_schema_invalid_registry_id_both_params_provided(client):
    helpers.create_registry(client)

    invalid_registry_id = {
        "RegistryName": f"{TEST_REGISTRY_NAME}",
        "RegistryArn": f"{TEST_REGISTRY_ARN}",
    }

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(client, registry_id=invalid_registry_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "One of registryName or registryArn has to be provided, both cannot be provided."
    )


def test_create_schema_invalid_schema_name(client):
    helpers.create_registry(client)

    invalid_schema_name = "Invalid,Schema,Name"

    with pytest.raises(ClientError) as exc:
        client.create_schema(
            RegistryId=TEST_REGISTRY_ID,
            SchemaName=invalid_schema_name,
            DataFormat=TEST_AVRO_DATA_FORMAT,
            Compatibility=TEST_BACKWARD_COMPATIBILITY,
            SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "The parameter value contains one or more characters that are not valid. Parameter Name: schemaName"
    )


def test_create_schema_invalid_schema_name_too_long(client):
    helpers.create_registry(client)

    invalid_schema_name = ""
    for _ in range(80):
        invalid_schema_name = invalid_schema_name + "toolong"

    with pytest.raises(ClientError) as exc:
        client.create_schema(
            RegistryId=TEST_REGISTRY_ID,
            SchemaName=invalid_schema_name,
            DataFormat=TEST_AVRO_DATA_FORMAT,
            Compatibility=TEST_BACKWARD_COMPATIBILITY,
            SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "The resource name contains too many or too few characters. Parameter Name: schemaName"
    )


def test_create_schema_invalid_data_format(client):
    helpers.create_registry(client)

    invalid_data_format = "INVALID"

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(client, TEST_REGISTRY_ID, data_format=invalid_data_format)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert err["Message"] == "Data format is not valid."


def test_create_schema_invalid_compatibility(client):
    helpers.create_registry(client)

    invalid_compatibility = "INVALID"

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(
            client, TEST_REGISTRY_ID, compatibility=invalid_compatibility
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert err["Message"] == "Compatibility is not valid."


def test_create_schema_invalid_schema_definition(client):
    helpers.create_registry(client)

    invalid_schema_definition = """{
                            "type":: "record",
                        }"""

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(
            client, TEST_REGISTRY_ID, schema_definition=invalid_schema_definition
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        f"Schema definition of {TEST_AVRO_DATA_FORMAT} data format is invalid"
        in err["Message"]
    )


# test register_schema_version
def test_register_schema_version_valid_input_avro(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    response = client.register_schema_version(
        SchemaId=TEST_SCHEMA_ID, SchemaDefinition=TEST_NEW_AVRO_SCHEMA_DEFINITION
    )

    assert "SchemaVersionId" in response
    assert response["VersionNumber"] == 2
    assert response["Status"] == TEST_AVAILABLE_STATUS


def test_register_schema_version_valid_input_json(client):
    helpers.create_registry(client)

    helpers.create_schema(
        client,
        TEST_REGISTRY_ID,
        data_format="JSON",
        schema_definition=TEST_JSON_SCHEMA_DEFINITION,
    )

    response = client.register_schema_version(
        SchemaId=TEST_SCHEMA_ID, SchemaDefinition=TEST_NEW_JSON_SCHEMA_DEFINITION
    )

    assert "SchemaVersionId" in response
    assert response["VersionNumber"] == 2
    assert response["Status"] == TEST_AVAILABLE_STATUS


def test_register_schema_version_valid_input_protobuf(client):
    helpers.create_registry(client)

    helpers.create_schema(
        client,
        TEST_REGISTRY_ID,
        data_format="PROTOBUF",
        schema_definition=TEST_PROTOBUF_SCHEMA_DEFINITION,
    )

    response = client.register_schema_version(
        SchemaId=TEST_SCHEMA_ID, SchemaDefinition=TEST_NEW_PROTOBUF_SCHEMA_DEFINITION
    )

    assert "SchemaVersionId" in response
    assert response["VersionNumber"] == 2
    assert response["Status"] == TEST_AVAILABLE_STATUS


def test_register_schema_version_valid_input_schema_arn(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    schema_id = {"SchemaArn": TEST_SCHEMA_ARN}
    response = client.register_schema_version(
        SchemaId=schema_id, SchemaDefinition=TEST_NEW_AVRO_SCHEMA_DEFINITION
    )

    assert "SchemaVersionId" in response
    assert response["VersionNumber"] == 2
    assert response["Status"] == TEST_AVAILABLE_STATUS


def test_register_schema_version_identical_schema_version_avro(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)

    version_id = response["SchemaVersionId"]

    response = client.register_schema_version(
        SchemaId=TEST_SCHEMA_ID, SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION
    )

    assert response["SchemaVersionId"] == version_id
    assert response["VersionNumber"] == 1
    assert response["Status"] == TEST_AVAILABLE_STATUS


def test_register_schema_version_identical_schema_version_json(client):
    helpers.create_registry(client)

    response = helpers.create_schema(
        client,
        TEST_REGISTRY_ID,
        data_format=TEST_JSON_DATA_FORMAT,
        schema_definition=TEST_JSON_SCHEMA_DEFINITION,
    )

    version_id = response["SchemaVersionId"]

    response = client.register_schema_version(
        SchemaId=TEST_SCHEMA_ID, SchemaDefinition=TEST_JSON_SCHEMA_DEFINITION
    )

    assert response["SchemaVersionId"] == version_id
    assert response["VersionNumber"] == 1
    assert response["Status"] == TEST_AVAILABLE_STATUS


def test_register_schema_version_identical_schema_version_protobuf(client):
    helpers.create_registry(client)

    response = helpers.create_schema(
        client,
        TEST_REGISTRY_ID,
        data_format=TEST_PROTOBUF_DATA_FORMAT,
        schema_definition=TEST_PROTOBUF_SCHEMA_DEFINITION,
    )

    version_id = response["SchemaVersionId"]

    response = client.register_schema_version(
        SchemaId=TEST_SCHEMA_ID, SchemaDefinition=TEST_PROTOBUF_SCHEMA_DEFINITION
    )

    assert response["SchemaVersionId"] == version_id
    assert response["VersionNumber"] == 1
    assert response["Status"] == TEST_AVAILABLE_STATUS


def test_register_schema_version_invalid_registry_schema_does_not_exist(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    with pytest.raises(ClientError) as exc:
        client.register_schema_version(
            SchemaId=TEST_INVALID_SCHEMA_ID_REGISTRY_DOES_NOT_EXIST,
            SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert "Schema is not found." in err["Message"]


def test_register_schema_version_invalid_schema_schema_does_not_exist(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    with pytest.raises(ClientError) as exc:
        client.register_schema_version(
            SchemaId=TEST_INVALID_SCHEMA_ID_SCHEMA_DOES_NOT_EXIST,
            SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert "Schema is not found." in err["Message"]


def test_register_schema_version_invalid_compatibility_disabled(client):
    helpers.create_registry(client)

    helpers.create_schema(
        client, TEST_REGISTRY_ID, compatibility=TEST_DISABLED_COMPATIBILITY
    )

    with pytest.raises(ClientError) as exc:
        client.register_schema_version(
            SchemaId=TEST_SCHEMA_ID, SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == f"Compatibility DISABLED does not allow versioning. SchemaId: SchemaId(schemaArn=null, schemaName={TEST_SCHEMA_NAME}, registryName={TEST_REGISTRY_NAME})"
    )


def test_register_schema_version_invalid_schema_definition(client):
    helpers.create_registry(client)

    helpers.create_schema(
        client, TEST_REGISTRY_ID, compatibility=TEST_DISABLED_COMPATIBILITY
    )

    with pytest.raises(ClientError) as exc:
        client.register_schema_version(
            SchemaId=TEST_SCHEMA_ID, SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert "Compatibility DISABLED does not allow versioning." in err["Message"]


def test_register_schema_version_invalid_schema_id(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)
    invalid_schema_id = {
        "SchemaArn": TEST_SCHEMA_ARN,
        "RegistryName": TEST_REGISTRY_NAME,
        "SchemaName": TEST_INVALID_SCHEMA_NAME_DOES_NOT_EXIST,
    }

    with pytest.raises(ClientError) as exc:
        client.register_schema_version(
            SchemaId=invalid_schema_id, SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "One of (registryName and schemaName) or schemaArn has to be provided, both cannot be provided."
    )


# test get_schema_version
def test_get_schema_version_valid_input_schema_version_id(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    response = client.get_schema_version(
        SchemaVersionId=version_id,
    )

    assert response["SchemaVersionId"] == version_id
    assert response["SchemaDefinition"] == TEST_AVRO_SCHEMA_DEFINITION
    assert response["DataFormat"] == TEST_AVRO_DATA_FORMAT
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["VersionNumber"] == 1
    assert response["Status"] == TEST_AVAILABLE_STATUS
    assert "CreatedTime" in response


def test_get_schema_version_valid_input_version_number(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    response = client.get_schema_version(
        SchemaId=TEST_SCHEMA_ID,
        SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
    )

    assert response["SchemaVersionId"] == version_id
    assert response["SchemaDefinition"] == TEST_AVRO_SCHEMA_DEFINITION
    assert response["DataFormat"] == TEST_AVRO_DATA_FORMAT
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["VersionNumber"] == 1
    assert response["Status"] == TEST_AVAILABLE_STATUS
    assert "CreatedTime" in response


def test_get_schema_version_valid_input_version_number_latest_version(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    response = helpers.register_schema_version(client)
    version_id = response["SchemaVersionId"]

    response = client.get_schema_version(
        SchemaId=TEST_SCHEMA_ID,
        SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER_LATEST_VERSION,
    )

    assert response["SchemaVersionId"] == version_id
    assert response["SchemaDefinition"] == TEST_NEW_AVRO_SCHEMA_DEFINITION
    assert response["DataFormat"] == TEST_AVRO_DATA_FORMAT
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["VersionNumber"] == 2
    assert response["Status"] == TEST_AVAILABLE_STATUS
    assert "CreatedTime" in response


def test_get_schema_version_empty_input(client):

    with pytest.raises(ClientError) as exc:
        client.get_schema_version()

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "At least one of (registryName and schemaName) or schemaArn has to be provided."
    )


def test_get_schema_version_invalid_schema_id_schema_version_number_both_provided(
    client,
):

    with pytest.raises(ClientError) as exc:
        client.get_schema_version(
            SchemaId=TEST_SCHEMA_ID,
            SchemaVersionId=TEST_VERSION_ID,
            SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER_LATEST_VERSION,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "No other input parameters can be specified when fetching by SchemaVersionId."
    )


def test_get_schema_version_insufficient_params_provided(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    with pytest.raises(ClientError) as exc:
        client.get_schema_version(SchemaId=TEST_SCHEMA_ID)

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert err["Message"] == "One of version number (or) latest version is required."


def test_get_schema_version_invalid_schema_version_number(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    invalid_schema_version_number = {"VersionNumber": 1, "LatestVersion": True}
    with pytest.raises(ClientError) as exc:
        client.get_schema_version(
            SchemaId=TEST_SCHEMA_ID,
            SchemaVersionNumber=invalid_schema_version_number,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert err["Message"] == "Only one of VersionNumber or LatestVersion is required."


def test_get_schema_version_invalid_version_number(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    invalid_schema_version_number = {"VersionNumber": 2}
    with pytest.raises(ClientError) as exc:
        client.get_schema_version(
            SchemaId=TEST_SCHEMA_ID,
            SchemaVersionNumber=invalid_schema_version_number,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert "Schema version is not found." in err["Message"]


def test_get_schema_version_invalid_schema_id_schema_name(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    with pytest.raises(ClientError) as exc:
        client.get_schema_version(
            SchemaId=TEST_INVALID_SCHEMA_ID_SCHEMA_DOES_NOT_EXIST,
            SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert (
        err["Message"]
        == f"Schema is not found. RegistryName: {TEST_REGISTRY_NAME}, SchemaName: {TEST_INVALID_SCHEMA_NAME_DOES_NOT_EXIST}, SchemaArn: null"
    )


def test_get_schema_version_invalid_schema_id_registry_name(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    with pytest.raises(ClientError) as exc:
        client.get_schema_version(
            SchemaId=TEST_INVALID_SCHEMA_ID_REGISTRY_DOES_NOT_EXIST,
            SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert "Schema is not found." in err["Message"]


def test_get_schema_version_invalid_schema_version(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)
    invalid_schema_version_id = "00000000-0000-0000-0000-00000000000p"
    with pytest.raises(ClientError) as exc:
        client.get_schema_version(SchemaVersionId=invalid_schema_version_id)

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "The parameter value contains one or more characters that are not valid. Parameter Name: SchemaVersionId"
    )


# Test get_schema_by_definition
def test_get_schema_by_definition_valid_input(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    response = client.get_schema_by_definition(
        SchemaId=TEST_SCHEMA_ID,
        SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION,
    )

    assert response["SchemaVersionId"] == version_id
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["DataFormat"] == TEST_AVRO_DATA_FORMAT
    assert response["Status"] == TEST_AVAILABLE_STATUS
    assert "CreatedTime" in response


def test_get_schema_by_definition_invalid_schema_id_schema_does_not_exist(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    with pytest.raises(ClientError) as exc:
        client.get_schema_by_definition(
            SchemaId=TEST_INVALID_SCHEMA_ID_SCHEMA_DOES_NOT_EXIST,
            SchemaDefinition=TEST_AVRO_SCHEMA_DEFINITION,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert "Schema is not found." in err["Message"]


def test_get_schema_by_definition_invalid_schema_definition_does_not_exist(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    with pytest.raises(ClientError) as exc:
        client.get_schema_by_definition(
            SchemaId=TEST_SCHEMA_ID,
            SchemaDefinition=TEST_NEW_AVRO_SCHEMA_DEFINITION,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert "Schema is not found." in err["Message"]


# test put_schema_version_metadata
def test_put_schema_version_metadata_valid_input_schema_version_number(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    response = client.put_schema_version_metadata(
        SchemaId=TEST_SCHEMA_ID,
        SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
        MetadataKeyValue=TEST_METADATA_KEY_VALUE,
    )

    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert response["RegistryName"] == TEST_REGISTRY_NAME
    assert response["LatestVersion"] is False
    assert response["VersionNumber"] == 1
    assert response["MetadataKey"] == TEST_METADATA_KEY_VALUE["MetadataKey"]
    assert response["MetadataValue"] == TEST_METADATA_KEY_VALUE["MetadataValue"]


def test_put_schema_version_metadata_valid_input_schema_version_id(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    response = client.put_schema_version_metadata(
        SchemaVersionId=version_id,
        MetadataKeyValue=TEST_METADATA_KEY_VALUE,
    )

    assert response["SchemaVersionId"] == version_id
    assert response["LatestVersion"] is False
    assert response["VersionNumber"] == 0
    assert response["MetadataKey"] == TEST_METADATA_KEY
    assert response["MetadataValue"] == TEST_METADATA_VALUE


def test_put_schema_version_metadata_more_than_allowed_schema_version_id(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    for i in range(10):
        client.put_schema_version_metadata(
            SchemaVersionId=version_id,
            MetadataKeyValue={
                "MetadataKey": f"test_metadata_key{i}",
                "MetadataValue": f"test_metadata_value{i}",
            },
        )

    with pytest.raises(ClientError) as exc:
        client.put_schema_version_metadata(
            SchemaVersionId=version_id,
            MetadataKeyValue=TEST_METADATA_KEY_VALUE,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNumberLimitExceededException"
    assert (
        err["Message"]
        == "Your resource limits for Schema Version Metadata have been exceeded."
    )


def test_put_schema_version_metadata_more_than_allowed_schema_version_id_same_key(
    client,
):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    for i in range(10):
        client.put_schema_version_metadata(
            SchemaVersionId=version_id,
            MetadataKeyValue={
                "MetadataKey": "test_metadata_key",
                "MetadataValue": f"test_metadata_value{i}",
            },
        )

    with pytest.raises(ClientError) as exc:
        client.put_schema_version_metadata(
            SchemaVersionId=version_id,
            MetadataKeyValue=TEST_METADATA_KEY_VALUE,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNumberLimitExceededException"
    assert (
        err["Message"]
        == "Your resource limits for Schema Version Metadata have been exceeded."
    )


def test_put_schema_version_metadata_already_exists_schema_version_id(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    client.put_schema_version_metadata(
        SchemaVersionId=version_id,
        MetadataKeyValue=TEST_METADATA_KEY_VALUE,
    )

    with pytest.raises(ClientError) as exc:
        client.put_schema_version_metadata(
            SchemaVersionId=version_id,
            MetadataKeyValue=TEST_METADATA_KEY_VALUE,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "AlreadyExistsException"
    assert (
        err["Message"]
        == f"Resource already exist for schema version id: {version_id}, metadata key: {TEST_METADATA_KEY}, metadata value: {TEST_METADATA_VALUE}"
    )


def test_put_schema_version_metadata_invalid_characters_metadata_key_schema_version_id(
    client,
):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    invalid_metadata_key = {
        "MetadataKey": "invalid~metadata~key",
        "MetadataValue": TEST_METADATA_VALUE,
    }

    with pytest.raises(ClientError) as exc:
        client.put_schema_version_metadata(
            SchemaVersionId=version_id,
            MetadataKeyValue=invalid_metadata_key,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "The parameter value contains one or more characters that are not valid. Parameter Name: key"
    )


def test_put_schema_version_metadata_invalid_characters_metadata_value_schema_version_id(
    client,
):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    invalid_metadata_value = {
        "MetadataKey": TEST_METADATA_KEY,
        "MetadataValue": "invalid~metadata~value",
    }

    with pytest.raises(ClientError) as exc:
        client.put_schema_version_metadata(
            SchemaVersionId=version_id,
            MetadataKeyValue=invalid_metadata_value,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert "value contains one or more characters that are not valid." in err["Message"]


def test_put_schema_version_metadata_more_than_allowed_schema_version_number(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    for i in range(10):
        client.put_schema_version_metadata(
            SchemaId=TEST_SCHEMA_ID,
            SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
            MetadataKeyValue={
                "MetadataKey": f"test_metadata_key{i}",
                "MetadataValue": f"test_metadata_value{i}",
            },
        )

    with pytest.raises(ClientError) as exc:
        client.put_schema_version_metadata(
            SchemaId=TEST_SCHEMA_ID,
            SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
            MetadataKeyValue=TEST_METADATA_KEY_VALUE,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNumberLimitExceededException"
    assert (
        err["Message"]
        == "Your resource limits for Schema Version Metadata have been exceeded."
    )


def test_put_schema_version_metadata_already_exists_schema_version_number(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    client.put_schema_version_metadata(
        SchemaId=TEST_SCHEMA_ID,
        SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
        MetadataKeyValue=TEST_METADATA_KEY_VALUE,
    )

    with pytest.raises(ClientError) as exc:
        client.put_schema_version_metadata(
            SchemaId=TEST_SCHEMA_ID,
            SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
            MetadataKeyValue=TEST_METADATA_KEY_VALUE,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "AlreadyExistsException"
    assert (
        err["Message"]
        == f"Resource already exist for schema version id: {version_id}, metadata key: {TEST_METADATA_KEY}, metadata value: {TEST_METADATA_VALUE}"
    )


def test_put_schema_version_metadata_invalid_characters_metadata_key_schema_version_number(
    client,
):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    invalid_metadata_key = {
        "MetadataKey": "invalid~metadata~key",
        "MetadataValue": TEST_METADATA_VALUE,
    }

    with pytest.raises(ClientError) as exc:
        client.put_schema_version_metadata(
            SchemaId=TEST_SCHEMA_ID,
            SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
            MetadataKeyValue=invalid_metadata_key,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        "The parameter value contains one or more characters that are not valid."
        in err["Message"]
    )


def test_put_schema_version_metadata_invalid_characters_metadata_value_schema_version_number(
    client,
):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    invalid_metadata_value = {
        "MetadataKey": TEST_METADATA_KEY,
        "MetadataValue": "invalid~metadata~value",
    }

    with pytest.raises(ClientError) as exc:
        client.put_schema_version_metadata(
            SchemaId=TEST_SCHEMA_ID,
            SchemaVersionNumber=TEST_SCHEMA_VERSION_NUMBER,
            MetadataKeyValue=invalid_metadata_value,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert "value contains one or more characters that are not valid." in err["Message"]


def test_get_schema(client):
    helpers.create_registry(client)
    helpers.create_schema(client, TEST_REGISTRY_ID)

    response = client.get_schema(
        SchemaId={"RegistryName": TEST_REGISTRY_NAME, "SchemaName": TEST_SCHEMA_NAME}
    )
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["SchemaName"] == TEST_SCHEMA_NAME


def test_update_schema(client):
    helpers.create_registry(client)
    helpers.create_schema(client, TEST_REGISTRY_ID)

    client.update_schema(
        SchemaId={"RegistryName": TEST_REGISTRY_NAME, "SchemaName": TEST_SCHEMA_NAME},
        Compatibility="FORWARD",
        Description="updated schema",
    )

    response = client.get_schema(
        SchemaId={"RegistryName": TEST_REGISTRY_NAME, "SchemaName": TEST_SCHEMA_NAME}
    )
    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert response["Description"] == "updated schema"
    assert response["Compatibility"] == "FORWARD"


# test delete_schema
def test_delete_schema_valid_input(client):
    helpers.create_registry(client)

    helpers.create_schema(client, TEST_REGISTRY_ID)

    response = client.delete_schema(SchemaId=TEST_SCHEMA_ID)

    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert response["Status"] == TEST_DELETING_STATUS


def test_delete_schema_valid_input_schema_arn(client):
    helpers.create_registry(client)

    response = helpers.create_schema(client, TEST_REGISTRY_ID)
    version_id = response["SchemaVersionId"]

    schema_id = {"SchemaArn": f"{TEST_SCHEMA_ARN}"}
    response = client.delete_schema(SchemaId=schema_id)

    assert response["SchemaArn"] == TEST_SCHEMA_ARN
    assert response["SchemaName"] == TEST_SCHEMA_NAME
    assert response["Status"] == TEST_DELETING_STATUS

    with pytest.raises(ClientError) as exc:
        client.get_schema_version(SchemaVersionId=version_id)

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert "Schema version is not found." in err["Message"]


def test_delete_schema_schema_not_found(client):
    helpers.create_registry(client)

    with pytest.raises(ClientError) as exc:
        client.delete_schema(SchemaId=TEST_SCHEMA_ID)

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert (
        err["Message"]
        == f"Schema is not found. RegistryName: {TEST_REGISTRY_NAME}, SchemaName: {TEST_SCHEMA_NAME}, SchemaArn: null"
    )


def test_list_registries(client):
    helpers.create_registry(client)
    helpers.create_registry(client, registry_name="registry2")

    registries = client.list_registries()["Registries"]
    assert len(registries) == 2


@pytest.mark.parametrize("name_or_arn", ["RegistryArn", "RegistryName"])
def test_get_registry(client, name_or_arn):
    x = helpers.create_registry(client)

    r = client.get_registry(RegistryId={name_or_arn: x[name_or_arn]})
    assert r["RegistryName"] == x["RegistryName"]
    assert r["RegistryArn"] == x["RegistryArn"]


@pytest.mark.parametrize("name_or_arn", ["RegistryArn", "RegistryName"])
def test_delete_registry(client, name_or_arn):
    x = helpers.create_registry(client)

    client.delete_registry(RegistryId={name_or_arn: x[name_or_arn]})
    assert len(client.list_registries()["Registries"]) == 0
