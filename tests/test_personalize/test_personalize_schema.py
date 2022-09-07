"""Unit tests for personalize-supported APIs."""
import boto3
import json
import sure  # noqa # pylint: disable=unused-import
import pytest
from botocore.exceptions import ClientError
from moto import mock_personalize
from moto.core import DEFAULT_ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_personalize
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
    create_schema_response.should.have.key("schemaArn").equals(
        f"arn:aws:personalize:ap-southeast-1:{DEFAULT_ACCOUNT_ID}:schema/personalize-demo-schema"
    )


@mock_personalize
def test_delete_schema():
    client = boto3.client("personalize", region_name="us-east-1")
    schema_arn = client.create_schema(name="myname", schema=json.dumps("sth"))[
        "schemaArn"
    ]
    client.delete_schema(schemaArn=schema_arn)

    client.list_schemas().should.have.key("schemas").equals([])


@mock_personalize
def test_delete_schema__unknown():
    arn = f"arn:aws:personalize:ap-southeast-1:{DEFAULT_ACCOUNT_ID}:schema/personalize-demo-schema"
    client = boto3.client("personalize", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.delete_schema(schemaArn=arn)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(f"Resource Arn {arn} does not exist.")


@mock_personalize
def test_describe_schema():
    client = boto3.client("personalize", region_name="us-east-2")
    schema_arn = client.create_schema(name="myname", schema="sth")["schemaArn"]
    resp = client.describe_schema(schemaArn=schema_arn)
    resp.should.have.key("schema")
    schema = resp["schema"]

    schema.should.have.key("name").equals("myname")
    schema.should.have.key("schemaArn").match("schema/myname")
    schema.should.have.key("schema").equals("sth")
    schema.should.have.key("creationDateTime")
    schema.should.have.key("lastUpdatedDateTime")


@mock_personalize
def test_describe_schema__with_domain():
    client = boto3.client("personalize", region_name="us-east-2")
    schema_arn = client.create_schema(name="myname", schema="sth", domain="ECOMMERCE")[
        "schemaArn"
    ]
    resp = client.describe_schema(schemaArn=schema_arn)
    resp.should.have.key("schema")
    schema = resp["schema"]

    schema.should.have.key("domain").equals("ECOMMERCE")


@mock_personalize
def test_describe_schema__unknown():
    arn = (
        "arn:aws:personalize:ap-southeast-1:486285699788:schema/personalize-demo-schema"
    )
    client = boto3.client("personalize", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.describe_schema(schemaArn=arn)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(f"Resource Arn {arn} does not exist.")


@mock_personalize
def test_list_schemas__initial():
    client = boto3.client("personalize", region_name="us-east-2")
    resp = client.list_schemas()

    resp.should.have.key("schemas").equals([])


@mock_personalize
def test_list_schema():
    client = boto3.client("personalize", region_name="us-east-2")
    schema_arn = client.create_schema(name="myname", schema="sth")["schemaArn"]

    resp = client.list_schemas()
    resp.should.have.key("schemas").length_of(1)
    schema = resp["schemas"][0]

    schema.should.have.key("name").equals("myname")
    schema.should.have.key("schemaArn").equals(schema_arn)
    schema.shouldnt.have.key("schema")
    schema.should.have.key("creationDateTime")
    schema.should.have.key("lastUpdatedDateTime")
