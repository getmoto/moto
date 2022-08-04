from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

DESCRIPTION = "test_description"

TAGS = {"key1": "value1", "key2": "value2"}

AVAILABLE_STATUS = "AVAILABLE"

REGISTRY_NAME = "TestRegistry"

REGISTRY_ARN = f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:registry/{REGISTRY_NAME}"

SCHEMA_NAME = "TestSchema"

REGISTRY_ID = {"RegistryName": f"{REGISTRY_NAME}"}

SCHEMA_ID = {"RegistryName": f"{REGISTRY_NAME}", "SchemaName": f"{SCHEMA_NAME}"}

SCHEMA_ARN = f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:schema/{REGISTRY_NAME}/{SCHEMA_NAME}"

AVRO_DATA_FORMAT = "AVRO"

JSON_DATA_FORMAT = "JSON"

PROTOBUF_DATA_FORMAT = "PROTOBUF"

BACKWARD_COMPATIBILITY = "BACKWARD"

DISABLED_COMPATIBILITY = "DISABLED"

AVRO_SCHEMA_DEFINITION = """{
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

NEW_AVRO_SCHEMA_DEFINITION = """{
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

JSON_SCHEMA_DEFINITION = """{
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

NEW_JSON_SCHEMA_DEFINITION = """{
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

PROTOBUF_SCHEMA_DEFINITION = """syntax = "proto2";
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

NEW_PROTOBUF_SCHEMA_DEFINITION = """syntax = "proto2";

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
