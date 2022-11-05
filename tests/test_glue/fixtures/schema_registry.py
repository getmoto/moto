from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

TEST_DESCRIPTION = "test_description"

TEST_TAGS = {"key1": "value1", "key2": "value2"}

TEST_AVAILABLE_STATUS = "AVAILABLE"
TEST_DELETING_STATUS = "DELETING"

TEST_REGISTRY_NAME = "TestRegistry"
TEST_INVALID_REGISTRY_NAME_DOES_NOT_EXIST = "InvalidRegistryDoesNotExist"
TEST_REGISTRY_ARN = f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:registry/{TEST_REGISTRY_NAME}"
TEST_REGISTRY_ID = {"RegistryName": f"{TEST_REGISTRY_NAME}"}

TEST_SCHEMA_NAME = "TestSchema"
TEST_INVALID_SCHEMA_NAME_DOES_NOT_EXIST = "InvalidSchemaDoesNotExist"
TEST_SCHEMA_ARN = f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:schema/{TEST_REGISTRY_NAME}/{TEST_SCHEMA_NAME}"
TEST_SCHEMA_ID = {
    "RegistryName": f"{TEST_REGISTRY_NAME}",
    "SchemaName": f"{TEST_SCHEMA_NAME}",
}
TEST_INVALID_SCHEMA_ID_SCHEMA_DOES_NOT_EXIST = {
    "RegistryName": TEST_REGISTRY_NAME,
    "SchemaName": TEST_INVALID_SCHEMA_NAME_DOES_NOT_EXIST,
}
TEST_INVALID_SCHEMA_ID_REGISTRY_DOES_NOT_EXIST = {
    "RegistryName": TEST_INVALID_REGISTRY_NAME_DOES_NOT_EXIST,
    "SchemaName": TEST_SCHEMA_NAME,
}

TEST_AVRO_DATA_FORMAT = "AVRO"
TEST_JSON_DATA_FORMAT = "JSON"
TEST_PROTOBUF_DATA_FORMAT = "PROTOBUF"

TEST_BACKWARD_COMPATIBILITY = "BACKWARD"
TEST_DISABLED_COMPATIBILITY = "DISABLED"

TEST_SCHEMA_VERSION_NUMBER = {"VersionNumber": 1, "LatestVersion": False}
TEST_SCHEMA_VERSION_NUMBER_LATEST_VERSION = {"LatestVersion": True}
TEST_VERSION_ID = "00000000-0000-0000-0000-000000000000"


TEST_METADATA_KEY = "test_metadata_key"
TEST_METADATA_VALUE = "test_metadata_value"
TEST_METADATA_KEY_VALUE = {
    "MetadataKey": TEST_METADATA_KEY,
    "MetadataValue": TEST_METADATA_VALUE,
}

TEST_AVRO_SCHEMA_DEFINITION = """{
        "type": "record",
        "namespace": "Moto_Test",
        "name": "Person",
        "fields": [
            {
                "name": "Name",
                "type": "string"
            },
            {
                "name": "Age",
                "type": "int"
            }
        ]
    }"""

TEST_NEW_AVRO_SCHEMA_DEFINITION = """{
        "type": "record",
        "namespace": "Moto_Test",
        "name": "Person",
        "fields": [
            {
                "name": "Name",
                "type": "string"
            },
            {
                "name": "Age",
                "type": "int"
            },
            {
                "name": "address",
                "type": "string",
                "default": ""
            }
        ]
    }"""

TEST_JSON_SCHEMA_DEFINITION = """{
        "$id": "https://example.com/person.schema.json",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Person",
        "type": "object",
        "properties": {
            "firstName": {
                "type": "string",
                "description": "The person's first name."
            },
            "lastName": {
                "type": "string",
                "description": "The person's last name."
            }
        }
    }"""

TEST_NEW_JSON_SCHEMA_DEFINITION = """{
        "$id": "https://example.com/person.schema.json",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Person",
        "type": "object",
        "properties": {
            "firstName": {
                "type": "string",
                "description": "The person's first name."
            },
            "lastName": {
                "type": "string",
                "description": "The person's last name."
            },
            "age": {
                "description": "Age in years which must be equal to or greater than zero.",
                "type": "integer",
                "minimum": 0
            }
        }
    }"""

TEST_PROTOBUF_SCHEMA_DEFINITION = """syntax = "proto2";
    package tutorial;

    option java_multiple_files = true;
    option java_package = "com.example.tutorial.protos";
    option java_outer_classname = "AddressBookProtos";

    message Person {
      optional string name = 1;
      optional int32 id = 2;
      optional string email = 3;

      enum PhoneType {
        MOBILE = 0;
        HOME = 1;
        WORK = 2;
      }

      message PhoneNumber {
        optional string number = 1;
        optional PhoneType type = 2 [default = HOME];
      }

      repeated PhoneNumber phones = 4;
    }"""

TEST_NEW_PROTOBUF_SCHEMA_DEFINITION = """syntax = "proto2";

    package tutorial;

    option java_multiple_files = true;
    option java_package = "com.example.tutorial.protos";
    option java_outer_classname = "AddressBookProtos";

    message Person {
      optional string name = 1;
      optional int32 id = 2;
      optional string email = 3;

      enum PhoneType {
        MOBILE = 0;
        HOME = 1;
        WORK = 2;
      }

      message PhoneNumber {
        optional string number = 1;
        optional PhoneType type = 2 [default = HOME];
      }

      repeated PhoneNumber phones = 4;
    }

    message AddressBook {
      repeated Person people = 1;
    }"""
