"""Unit tests for glue-schema-registry-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.client import ClientError
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from moto import mock_glue

from . import helpers
from .fixtures.schema_registry import (
    REGISTRY_NAME,
    REGISTRY_ARN,
    DESCRIPTION,
    TAGS,
    SCHEMA_NAME,
    SCHEMA_ARN,
    AVRO_SCHEMA_DEFINITION,
    NEW_AVRO_SCHEMA_DEFINITION,
    JSON_SCHEMA_DEFINITION,
    NEW_JSON_SCHEMA_DEFINITION,
    PROTOBUF_SCHEMA_DEFINITION,
    NEW_PROTOBUF_SCHEMA_DEFINITION,
    AVRO_DATA_FORMAT,
    JSON_DATA_FORMAT,
    PROTOBUF_DATA_FORMAT,
    REGISTRY_ID,
    SCHEMA_ID,
    BACKWARD_COMPATIBILITY,
    DISABLED_COMPATIBILITY,
    AVAILABLE_STATUS,
)


def create_glue_client():
    return boto3.client("glue", region_name="us-east-1")


# Test create_registry
@mock_glue
def test_create_registry_valid_input():
    client = create_glue_client()
    response = client.create_registry(
        RegistryName=REGISTRY_NAME, Description=DESCRIPTION, Tags=TAGS
    )
    response.should.have.key("RegistryName").equals(REGISTRY_NAME)
    response.should.have.key("Description").equals(DESCRIPTION)
    response.should.have.key("Tags").equals(TAGS)
    response.should.have.key("RegistryArn").equals(REGISTRY_ARN)


@mock_glue
def test_create_registry_valid_partial_input():
    client = create_glue_client()
    response = client.create_registry(RegistryName=REGISTRY_NAME)
    response.should.have.key("RegistryName").equals(REGISTRY_NAME)
    response.should.have.key("RegistryArn").equals(REGISTRY_ARN)


@mock_glue
def test_create_registry_invalid_registry_name_too_long():
    client = create_glue_client()
    registry_name = ""
    for _ in range(80):
        registry_name = registry_name + "toolong"

    with pytest.raises(ClientError) as exc:
        client.create_registry(RegistryName=registry_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "The resource name contains too many or too few characters. Parameter Name: registryName"
    )


@mock_glue
def test_create_registry_more_than_allowed():
    client = create_glue_client()

    for i in range(10):
        client.create_registry(RegistryName=REGISTRY_NAME + str(i))

    with pytest.raises(ClientError) as exc:
        client.create_registry(RegistryName=REGISTRY_NAME)

    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNumberLimitExceededException")
    err["Message"].should.equal(
        "More registries cannot be created. The maximum limit has been reached."
    )


@mock_glue
def test_create_registry_invalid_registry_name():
    client = create_glue_client()
    invalid_registry_name = "A,B,C"

    with pytest.raises(ClientError) as exc:
        client.create_registry(RegistryName=invalid_registry_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "The parameter value contains one or more characters that are not valid. Parameter Name: registryName"
    )


@mock_glue
def test_create_registry_already_exists():
    client = create_glue_client()

    client.create_registry(RegistryName=REGISTRY_NAME)

    with pytest.raises(ClientError) as exc:
        client.create_registry(RegistryName=REGISTRY_NAME)
    err = exc.value.response["Error"]
    err["Code"].should.equal("AlreadyExistsException")
    err["Message"].should.equal(
        "Registry already exists. RegistryName: " + REGISTRY_NAME
    )


@mock_glue
def test_create_registry_invalid_description_too_long():
    client = create_glue_client()
    description = ""
    for _ in range(350):
        description = description + "toolong"

    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName=REGISTRY_NAME,
            Description=description,
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "The resource name contains too many or too few characters. Parameter Name: description"
    )


@mock_glue
def test_create_registry_invalid_number_of_tags():
    tags = {}
    for i in range(51):
        key = "k" + str(i)
        val = "v" + str(i)
        tags[key] = val

    client = create_glue_client()
    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName=REGISTRY_NAME,
            Tags=tags,
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal("New Tags cannot be empty or more than 50")


# Test create_schema
@mock_glue
def test_create_schema_valid_input_registry_name_avro():
    client = create_glue_client()
    helpers.create_registry(client)

    response = client.create_schema(
        RegistryId=REGISTRY_ID,
        SchemaName=SCHEMA_NAME,
        DataFormat=AVRO_DATA_FORMAT,
        Compatibility=BACKWARD_COMPATIBILITY,
        SchemaDefinition=AVRO_SCHEMA_DEFINITION,
        Description=DESCRIPTION,
        Tags=TAGS,
    )
    response.should.have.key("RegistryName").equals(REGISTRY_NAME)
    response.should.have.key("RegistryArn").equals(REGISTRY_ARN)
    response.should.have.key("SchemaName").equals(SCHEMA_NAME)
    response.should.have.key("SchemaArn").equals(SCHEMA_ARN)
    response.should.have.key("Description").equals(DESCRIPTION)
    response.should.have.key("DataFormat").equals(AVRO_DATA_FORMAT)
    response.should.have.key("Compatibility").equals(BACKWARD_COMPATIBILITY)
    response.should.have.key("SchemaCheckpoint").equals(1)
    response.should.have.key("LatestSchemaVersion").equals(1)
    response.should.have.key("NextSchemaVersion").equals(2)
    response.should.have.key("SchemaStatus").equals(AVAILABLE_STATUS)
    response.should.have.key("Tags").equals(TAGS)
    response.should.have.key("SchemaVersionId")
    response.should.have.key("SchemaVersionStatus").equals(AVAILABLE_STATUS)


@mock_glue
def test_create_schema_valid_input_registry_name_json():
    client = create_glue_client()
    helpers.create_registry(client)

    response = client.create_schema(
        RegistryId=REGISTRY_ID,
        SchemaName=SCHEMA_NAME,
        DataFormat=JSON_DATA_FORMAT,
        Compatibility=BACKWARD_COMPATIBILITY,
        SchemaDefinition=JSON_SCHEMA_DEFINITION,
        Description=DESCRIPTION,
        Tags=TAGS,
    )
    response.should.have.key("RegistryName").equals(REGISTRY_NAME)
    response.should.have.key("RegistryArn").equals(REGISTRY_ARN)
    response.should.have.key("SchemaName").equals(SCHEMA_NAME)
    response.should.have.key("SchemaArn").equals(SCHEMA_ARN)
    response.should.have.key("Description").equals(DESCRIPTION)
    response.should.have.key("DataFormat").equals(JSON_DATA_FORMAT)
    response.should.have.key("Compatibility").equals(BACKWARD_COMPATIBILITY)
    response.should.have.key("SchemaCheckpoint").equals(1)
    response.should.have.key("LatestSchemaVersion").equals(1)
    response.should.have.key("NextSchemaVersion").equals(2)
    response.should.have.key("SchemaStatus").equals(AVAILABLE_STATUS)
    response.should.have.key("Tags").equals(TAGS)
    response.should.have.key("SchemaVersionId")
    response.should.have.key("SchemaVersionStatus").equals(AVAILABLE_STATUS)


@mock_glue
def test_create_schema_valid_input_registry_name_protobuf():
    client = create_glue_client()
    helpers.create_registry(client)

    response = client.create_schema(
        RegistryId=REGISTRY_ID,
        SchemaName=SCHEMA_NAME,
        DataFormat=PROTOBUF_DATA_FORMAT,
        Compatibility=BACKWARD_COMPATIBILITY,
        SchemaDefinition=PROTOBUF_SCHEMA_DEFINITION,
        Description=DESCRIPTION,
        Tags=TAGS,
    )
    response.should.have.key("RegistryName").equals(REGISTRY_NAME)
    response.should.have.key("RegistryArn").equals(REGISTRY_ARN)
    response.should.have.key("SchemaName").equals(SCHEMA_NAME)
    response.should.have.key("SchemaArn").equals(SCHEMA_ARN)
    response.should.have.key("Description").equals(DESCRIPTION)
    response.should.have.key("DataFormat").equals(PROTOBUF_DATA_FORMAT)
    response.should.have.key("Compatibility").equals(BACKWARD_COMPATIBILITY)
    response.should.have.key("SchemaCheckpoint").equals(1)
    response.should.have.key("LatestSchemaVersion").equals(1)
    response.should.have.key("NextSchemaVersion").equals(2)
    response.should.have.key("SchemaStatus").equals(AVAILABLE_STATUS)
    response.should.have.key("Tags").equals(TAGS)
    response.should.have.key("SchemaVersionId")
    response.should.have.key("SchemaVersionStatus").equals(AVAILABLE_STATUS)


@mock_glue
def test_create_schema_valid_input_registry_arn():
    client = create_glue_client()
    helpers.create_registry(client)

    registry_id = {"RegistryArn": f"{REGISTRY_ARN}"}
    response = client.create_schema(
        RegistryId=registry_id,
        SchemaName=SCHEMA_NAME,
        DataFormat=AVRO_DATA_FORMAT,
        Compatibility=BACKWARD_COMPATIBILITY,
        SchemaDefinition=AVRO_SCHEMA_DEFINITION,
        Description=DESCRIPTION,
        Tags=TAGS,
    )
    response.should.have.key("RegistryName").equals(REGISTRY_NAME)
    response.should.have.key("RegistryArn").equals(REGISTRY_ARN)
    response.should.have.key("SchemaName").equals(SCHEMA_NAME)
    response.should.have.key("SchemaArn").equals(SCHEMA_ARN)
    response.should.have.key("Description").equals(DESCRIPTION)
    response.should.have.key("DataFormat").equals(AVRO_DATA_FORMAT)
    response.should.have.key("Compatibility").equals(BACKWARD_COMPATIBILITY)
    response.should.have.key("SchemaCheckpoint").equals(1)
    response.should.have.key("LatestSchemaVersion").equals(1)
    response.should.have.key("NextSchemaVersion").equals(2)
    response.should.have.key("SchemaStatus").equals(AVAILABLE_STATUS)
    response.should.have.key("Tags").equals(TAGS)
    response.should.have.key("SchemaVersionId")
    response.should.have.key("SchemaVersionStatus").equals(AVAILABLE_STATUS)


@mock_glue
def test_create_schema_valid_partial_input():
    client = create_glue_client()
    helpers.create_registry(client)

    response = helpers.create_schema(client, REGISTRY_ID)
    response.should.have.key("RegistryName").equals(REGISTRY_NAME)
    response.should.have.key("RegistryArn").equals(REGISTRY_ARN)
    response.should.have.key("SchemaName").equals(SCHEMA_NAME)
    response.should.have.key("SchemaArn").equals(SCHEMA_ARN)
    response.should.have.key("DataFormat").equals(AVRO_DATA_FORMAT)
    response.should.have.key("Compatibility").equals(BACKWARD_COMPATIBILITY)
    response.should.have.key("SchemaCheckpoint").equals(1)
    response.should.have.key("LatestSchemaVersion").equals(1)
    response.should.have.key("NextSchemaVersion").equals(2)
    response.should.have.key("SchemaStatus").equals(AVAILABLE_STATUS)
    response.should.have.key("SchemaStatus")
    response.should.have.key("SchemaVersionId")
    response.should.have.key("SchemaVersionStatus").equals(AVAILABLE_STATUS)


@mock_glue
def test_create_schema_valid_default_registry():
    client = create_glue_client()
    helpers.create_registry(client)

    empty_registry_id = {}

    response = helpers.create_schema(client, registry_id=empty_registry_id)
    default_registry_name = "default-registry"
    response.should.have.key("RegistryName").equals(default_registry_name)
    response.should.have.key("RegistryArn").equals(
        f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:registry/{default_registry_name}"
    )
    response.should.have.key("SchemaName").equals(SCHEMA_NAME)
    response.should.have.key("SchemaArn").equals(
        f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:schema/{default_registry_name}/{SCHEMA_NAME}"
    )
    response.should.have.key("DataFormat").equals(AVRO_DATA_FORMAT)
    response.should.have.key("Compatibility").equals(BACKWARD_COMPATIBILITY)
    response.should.have.key("SchemaCheckpoint").equals(1)
    response.should.have.key("LatestSchemaVersion").equals(1)
    response.should.have.key("NextSchemaVersion").equals(2)
    response.should.have.key("SchemaStatus").equals(AVAILABLE_STATUS)
    response.should.have.key("SchemaStatus")
    response.should.have.key("SchemaVersionId")
    response.should.have.key("SchemaVersionStatus").equals(AVAILABLE_STATUS)


@mock_glue
def test_create_schema_invalid_registry_arn():
    client = create_glue_client()
    helpers.create_registry(client)

    invalid_registry_arn = (
        f"invalid:arn:aws:glue:us-east-1:{ACCOUNT_ID}:registry/{REGISTRY_NAME}"
    )
    invalid_registry_id = {"RegistryArn": f"{invalid_registry_arn}"}

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(client, registry_id=invalid_registry_id)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "The parameter value contains one or more characters that are not valid. Parameter Name: registryArn"
    )


@mock_glue
def test_create_schema_invalid_registry_id_both_params_provided():
    client = create_glue_client()
    helpers.create_registry(client)

    invalid_registry_id = {
        "RegistryName": f"{REGISTRY_NAME}",
        "RegistryArn": f"{REGISTRY_ARN}",
    }

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(client, registry_id=invalid_registry_id)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "One of registryName or registryArn has to be provided, both cannot be provided."
    )


@mock_glue
def test_create_schema_invalid_schema_name():
    client = create_glue_client()
    helpers.create_registry(client)

    invalid_schema_name = "Invalid,Schema,Name"

    with pytest.raises(ClientError) as exc:
        client.create_schema(
            RegistryId=REGISTRY_ID,
            SchemaName=invalid_schema_name,
            DataFormat=AVRO_DATA_FORMAT,
            Compatibility=BACKWARD_COMPATIBILITY,
            SchemaDefinition=AVRO_SCHEMA_DEFINITION,
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "The parameter value contains one or more characters that are not valid. Parameter Name: schemaName"
    )


@mock_glue
def test_create_schema_invalid_schema_name_too_long():
    client = create_glue_client()
    helpers.create_registry(client)

    invalid_schema_name = ""
    for _ in range(80):
        invalid_schema_name = invalid_schema_name + "toolong"

    with pytest.raises(ClientError) as exc:
        client.create_schema(
            RegistryId=REGISTRY_ID,
            SchemaName=invalid_schema_name,
            DataFormat=AVRO_DATA_FORMAT,
            Compatibility=BACKWARD_COMPATIBILITY,
            SchemaDefinition=AVRO_SCHEMA_DEFINITION,
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "The resource name contains too many or too few characters. Parameter Name: schemaName"
    )


@mock_glue
def test_create_schema_invalid_data_format():
    client = create_glue_client()
    helpers.create_registry(client)

    invalid_data_format = "INVALID"

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(client, REGISTRY_ID, data_format=invalid_data_format)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal("Data format is not valid.")


@mock_glue
def test_create_schema_invalid_compatibility():
    client = create_glue_client()
    helpers.create_registry(client)

    invalid_compatibility = "INVALID"

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(client, REGISTRY_ID, compatibility=invalid_compatibility)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal("Compatibility is not valid.")


@mock_glue
def test_create_schema_invalid_schema_definition():
    client = create_glue_client()
    helpers.create_registry(client)

    invalid_schema_definition = """{
                            "type":: "record",
                        }"""

    with pytest.raises(ClientError) as exc:
        helpers.create_schema(
            client, REGISTRY_ID, schema_definition=invalid_schema_definition
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.have(
        f"Schema definition of {AVRO_DATA_FORMAT} data format is invalid"
    )


# test RegisterSchemaVersion
@mock_glue
def test_register_schema_version_valid_input_avro():
    client = create_glue_client()
    helpers.create_registry(client)

    helpers.create_schema(client, REGISTRY_ID)

    response = client.register_schema_version(
        SchemaId=SCHEMA_ID, SchemaDefinition=NEW_AVRO_SCHEMA_DEFINITION
    )

    response.should.have.key("SchemaVersionId")
    response.should.have.key("VersionNumber").equals(2)
    response.should.have.key("Status").equals(AVAILABLE_STATUS)


@mock_glue
def test_register_schema_version_valid_input_json():
    client = create_glue_client()
    helpers.create_registry(client)

    helpers.create_schema(
        client,
        REGISTRY_ID,
        data_format="JSON",
        schema_definition=JSON_SCHEMA_DEFINITION,
    )

    response = client.register_schema_version(
        SchemaId=SCHEMA_ID, SchemaDefinition=NEW_JSON_SCHEMA_DEFINITION
    )

    response.should.have.key("SchemaVersionId")
    response.should.have.key("VersionNumber").equals(2)
    response.should.have.key("Status").equals(AVAILABLE_STATUS)


@mock_glue
def test_register_schema_version_valid_input_protobuf():
    client = create_glue_client()
    helpers.create_registry(client)

    helpers.create_schema(
        client,
        REGISTRY_ID,
        data_format="PROTOBUF",
        schema_definition=PROTOBUF_SCHEMA_DEFINITION,
    )

    response = client.register_schema_version(
        SchemaId=SCHEMA_ID, SchemaDefinition=NEW_PROTOBUF_SCHEMA_DEFINITION
    )

    response.should.have.key("SchemaVersionId")
    response.should.have.key("VersionNumber").equals(2)
    response.should.have.key("Status").equals(AVAILABLE_STATUS)


@mock_glue
def test_register_schema_version_valid_input_schema_arn():
    client = create_glue_client()
    helpers.create_registry(client)

    helpers.create_schema(client, REGISTRY_ID)

    schema_id = {"SchemaArn": SCHEMA_ARN}
    response = client.register_schema_version(
        SchemaId=schema_id, SchemaDefinition=NEW_AVRO_SCHEMA_DEFINITION
    )

    response.should.have.key("SchemaVersionId")
    response.should.have.key("VersionNumber").equals(2)
    response.should.have.key("Status").equals(AVAILABLE_STATUS)


@mock_glue
def test_register_schema_version_identical_schema_version_avro():
    client = create_glue_client()
    helpers.create_registry(client)

    response = helpers.create_schema(client, REGISTRY_ID)

    version_id = response["SchemaVersionId"]

    response = client.register_schema_version(
        SchemaId=SCHEMA_ID, SchemaDefinition=AVRO_SCHEMA_DEFINITION
    )

    response.should.have.key("SchemaVersionId").equals(version_id)
    response.should.have.key("VersionNumber").equals(1)
    response.should.have.key("Status").equals(AVAILABLE_STATUS)


@mock_glue
def test_register_schema_version_identical_schema_version_json():
    client = create_glue_client()
    helpers.create_registry(client)

    response = helpers.create_schema(
        client,
        REGISTRY_ID,
        data_format=JSON_DATA_FORMAT,
        schema_definition=JSON_SCHEMA_DEFINITION,
    )

    version_id = response["SchemaVersionId"]

    response = client.register_schema_version(
        SchemaId=SCHEMA_ID, SchemaDefinition=JSON_SCHEMA_DEFINITION
    )

    response.should.have.key("SchemaVersionId").equals(version_id)
    response.should.have.key("VersionNumber").equals(1)
    response.should.have.key("Status").equals(AVAILABLE_STATUS)


@mock_glue
def test_register_schema_version_identical_schema_version_protobuf():
    client = create_glue_client()
    helpers.create_registry(client)

    response = helpers.create_schema(
        client,
        REGISTRY_ID,
        data_format=PROTOBUF_DATA_FORMAT,
        schema_definition=PROTOBUF_SCHEMA_DEFINITION,
    )

    version_id = response["SchemaVersionId"]

    response = client.register_schema_version(
        SchemaId=SCHEMA_ID, SchemaDefinition=PROTOBUF_SCHEMA_DEFINITION
    )

    response.should.have.key("SchemaVersionId").equals(version_id)
    response.should.have.key("VersionNumber").equals(1)
    response.should.have.key("Status").equals(AVAILABLE_STATUS)


@mock_glue
def test_register_schema_version_invalid_registry_schema_does_not_exist():
    client = create_glue_client()
    helpers.create_registry(client)

    helpers.create_schema(client, REGISTRY_ID)

    invalid_schema_id = {
        "RegistryName": "InvalidRegistryDoesNotExist",
        "SchemaName": f"{SCHEMA_NAME}",
    }

    with pytest.raises(ClientError) as exc:
        client.register_schema_version(
            SchemaId=invalid_schema_id, SchemaDefinition=AVRO_SCHEMA_DEFINITION
        )

    err = exc.value.response["Error"]
    err["Code"].should.equal("EntityNotFoundException")
    err["Message"].should.equal("Schema is not found.")


@mock_glue
def test_register_schema_version_invalid_schema_schema_does_not_exist():
    client = create_glue_client()
    helpers.create_registry(client)

    helpers.create_schema(client, REGISTRY_ID)

    invalid_schema_id = {
        "RegistryName": f"{REGISTRY_NAME}",
        "SchemaName": "InvalidSchemaDoesNotExist",
    }

    with pytest.raises(ClientError) as exc:
        client.register_schema_version(
            SchemaId=invalid_schema_id, SchemaDefinition=AVRO_SCHEMA_DEFINITION
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("EntityNotFoundException")
    err["Message"].should.equal("Schema is not found.")


@mock_glue
def test_register_schema_version_invalid_compatibility_disabled():
    client = create_glue_client()
    helpers.create_registry(client)

    helpers.create_schema(client, REGISTRY_ID, compatibility=DISABLED_COMPATIBILITY)

    with pytest.raises(ClientError) as exc:
        client.register_schema_version(
            SchemaId=SCHEMA_ID, SchemaDefinition=AVRO_SCHEMA_DEFINITION
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "Compatibility DISABLED does not allow versioning. SchemaId: SchemaId(schemaName="
        + SCHEMA_NAME
        + ", registryName="
        + REGISTRY_NAME
        + ")"
    )


@mock_glue
def test_register_schema_version_invalid_schema_definition():
    client = create_glue_client()
    helpers.create_registry(client)

    helpers.create_schema(client, REGISTRY_ID, compatibility=DISABLED_COMPATIBILITY)

    with pytest.raises(ClientError) as exc:
        client.register_schema_version(
            SchemaId=SCHEMA_ID, SchemaDefinition=AVRO_SCHEMA_DEFINITION
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.have("Schema definition of JSON data format is invalid:")
