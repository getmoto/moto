"""Unit tests for personalize-supported APIs."""

import json
import re

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_schema():
    client = boto3.client("personalize", region_name="ap-southeast-1")
    schema = {
        "type": "record",
        "name": "Interactions",
        "namespace": "com.amazonaws.personalize.schema",
        "fields": [
            {"name": "USER_ID", "type": "string"},
            {"name": "ITEM_ID", "type": "string"},
            {"name": "TIMESTAMP", "type": "long"},
        ],
        "version": "1.0",
    }

    create_schema_response = client.create_schema(
        name="personalize-demo-schema", schema=json.dumps(schema)
    )
    assert create_schema_response["schemaArn"] == (
        f"arn:aws:personalize:ap-southeast-1:{DEFAULT_ACCOUNT_ID}"
        ":schema/personalize-demo-schema"
    )


@mock_aws
def test_delete_schema():
    client = boto3.client("personalize", region_name="us-east-1")
    schema_arn = client.create_schema(name="myname", schema=json.dumps("sth"))[
        "schemaArn"
    ]
    client.delete_schema(schemaArn=schema_arn)

    assert client.list_schemas()["schemas"] == []


@mock_aws
def test_delete_schema__unknown():
    arn = f"arn:aws:personalize:ap-southeast-1:{DEFAULT_ACCOUNT_ID}:schema/personalize-demo-schema"
    client = boto3.client("personalize", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.delete_schema(schemaArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Resource Arn {arn} does not exist."


@mock_aws
def test_describe_schema():
    client = boto3.client("personalize", region_name="us-east-2")
    schema_arn = client.create_schema(name="myname", schema="sth")["schemaArn"]
    resp = client.describe_schema(schemaArn=schema_arn)
    assert "schema" in resp
    schema = resp["schema"]

    assert schema["name"] == "myname"
    assert re.search("schema/myname", schema["schemaArn"])
    assert schema["schema"] == "sth"
    assert "creationDateTime" in schema
    assert "lastUpdatedDateTime" in schema


@mock_aws
def test_describe_schema__with_domain():
    client = boto3.client("personalize", region_name="us-east-2")
    schema_arn = client.create_schema(name="myname", schema="sth", domain="ECOMMERCE")[
        "schemaArn"
    ]
    resp = client.describe_schema(schemaArn=schema_arn)
    assert "schema" in resp
    schema = resp["schema"]

    assert schema["domain"] == "ECOMMERCE"


@mock_aws
def test_describe_schema__unknown():
    arn = (
        "arn:aws:personalize:ap-southeast-1:486285699788:schema/personalize-demo-schema"
    )
    client = boto3.client("personalize", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.describe_schema(schemaArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Resource Arn {arn} does not exist."


@mock_aws
def test_list_schemas__initial():
    client = boto3.client("personalize", region_name="us-east-2")
    resp = client.list_schemas()

    assert resp["schemas"] == []


@mock_aws
def test_list_schema():
    client = boto3.client("personalize", region_name="us-east-2")
    schema_arn = client.create_schema(name="myname", schema="sth")["schemaArn"]

    resp = client.list_schemas()
    assert len(resp["schemas"]) == 1
    schema = resp["schemas"][0]

    assert schema["name"] == "myname"
    assert schema["schemaArn"] == schema_arn
    assert "schema" not in schema
    assert "creationDateTime" in schema
    assert "lastUpdatedDateTime" in schema
