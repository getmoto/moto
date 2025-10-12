"""Unit tests for clouddirectory-supported APIs."""

import boto3
import pytest

from moto import mock_aws
from tests import DEFAULT_ACCOUNT_ID


@mock_aws
def test_create_directory():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema = client.create_schema(Name="test-schema")
    schema_arn = schema["SchemaArn"]
    resp = client.create_directory(SchemaArn=schema_arn, Name="test-directory")
    assert (
        resp["DirectoryArn"]
        == f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-directory"
    )
    assert resp["Name"] == "test-directory"
    assert "ObjectIdentifier" in resp
    assert resp["AppliedSchemaArn"] == schema_arn


@mock_aws
def test_create_schema():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    resp = client.create_schema(Name="test-schema")
    assert (
        resp["SchemaArn"]
        == f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:schema/development/test-schema"
    )


@mock_aws
def test_apply_schema():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema = client.create_schema(Name="test-schema")
    schema_arn = schema["SchemaArn"]
    pub_schema = client.publish_schema(
        DevelopmentSchemaArn=schema_arn,
        Name="test-schema",
        Version="1",
        MinorVersion="0",
    )
    pub_schema_arn = pub_schema["PublishedSchemaArn"]
    directory = client.create_directory(SchemaArn=pub_schema_arn, Name="test-directory")
    directory_arn = directory["DirectoryArn"]
    resp = client.apply_schema(
        PublishedSchemaArn=pub_schema_arn, DirectoryArn=directory_arn
    )
    assert resp["AppliedSchemaArn"] == pub_schema_arn
    assert resp["DirectoryArn"] == directory_arn


@mock_aws
def test_publish_schema():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema = client.create_schema(Name="test-schema")
    schema_arn = schema["SchemaArn"]
    resp = client.publish_schema(
        DevelopmentSchemaArn=schema_arn,
        Name="test-schema",
        Version="1",
        MinorVersion="0",
    )
    assert (
        resp["PublishedSchemaArn"]
        == f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:schema/published/test-schema/1/0"
    )


@mock_aws
def test_list_development_schema_arns():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn1 = client.create_schema(Name="test-schema1")["SchemaArn"]
    schema_arn2 = client.create_schema(Name="test-schema2")["SchemaArn"]

    resp = client.list_development_schema_arns()
    assert len(resp["SchemaArns"]) == 2
    assert schema_arn1 in resp["SchemaArns"]
    assert schema_arn2 in resp["SchemaArns"]


@mock_aws
def test_list_published_schema_arns():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn1 = client.create_schema(Name="test-schema1")["SchemaArn"]
    schema_arn2 = client.create_schema(Name="test-schema2")["SchemaArn"]

    published_arn1 = client.publish_schema(
        DevelopmentSchemaArn=schema_arn1,
        Name="test-schema1",
        Version="1",
        MinorVersion="0",
    )["PublishedSchemaArn"]

    published_arn2 = client.publish_schema(
        DevelopmentSchemaArn=schema_arn2,
        Name="test-schema2",
        Version="1",
        MinorVersion="0",
    )["PublishedSchemaArn"]

    resp = client.list_published_schema_arns()
    assert len(resp["SchemaArns"]) == 2
    assert published_arn1 in resp["SchemaArns"]
    assert published_arn2 in resp["SchemaArns"]


@mock_aws
def test_delete_schema():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn = client.create_schema(Name="test-schema")["SchemaArn"]
    client.create_directory(SchemaArn=schema_arn, Name="test-directory")
    client.delete_schema(SchemaArn=schema_arn)
    resp = client.list_development_schema_arns()
    assert len(resp["SchemaArns"]) == 0


@mock_aws
def test_list_directories():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn = (
        f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-schema/1"
    )
    for i in range(3):
        client.create_directory(SchemaArn=schema_arn, Name=f"test-directory-{i}")

    resp = client.list_directories()
    assert len(resp["Directories"]) == 3

    directory = resp["Directories"][0]
    assert "Name" in directory
    assert "DirectoryArn" in directory
    assert "State" in directory
    assert "CreationDateTime" in directory

    # Test pagination
    resp = client.list_directories(MaxResults=1)
    assert len(resp["Directories"]) == 1
    assert "NextToken" in resp
    resp = client.list_directories(NextToken=resp["NextToken"])
    assert len(resp["Directories"]) == 2

    # Test filtering by state
    resp = client.list_directories(state="ENABLED")
    assert len(resp["Directories"]) == 3
    assert resp["Directories"][0]["State"] == "ENABLED"


@mock_aws
def test_tag_resource():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn = (
        f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-schema/1"
    )
    directory_arn = client.create_directory(
        SchemaArn=schema_arn, Name="test-directory"
    )["DirectoryArn"]
    client.tag_resource(
        ResourceArn=directory_arn, Tags=[{"Key": "key1", "Value": "value1"}]
    )

    # Test that the tag was added
    resp = client.list_tags_for_resource(ResourceArn=directory_arn)
    assert len(resp["Tags"]) == 1
    assert resp["Tags"][0]["Key"] == "key1"
    assert resp["Tags"][0]["Value"] == "value1"


@mock_aws
def test_untag_resource():
    region = "us-east-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn = (
        f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-schema/1"
    )
    directory_arn = client.create_directory(
        SchemaArn=schema_arn, Name="test-directory"
    )["DirectoryArn"]
    client.tag_resource(
        ResourceArn=directory_arn, Tags=[{"Key": "key1", "Value": "value1"}]
    )
    client.tag_resource(
        ResourceArn=directory_arn, Tags=[{"Key": "key2", "Value": "value2"}]
    )
    client.tag_resource(
        ResourceArn=directory_arn, Tags=[{"Key": "key3", "Value": "value3"}]
    )
    resp = client.list_tags_for_resource(ResourceArn=directory_arn)
    assert len(resp["Tags"]) == 3

    client.untag_resource(ResourceArn=directory_arn, TagKeys=["key2", "key3"])
    resp = client.list_tags_for_resource(ResourceArn=directory_arn)
    assert len(resp["Tags"]) == 1
    assert resp["Tags"][0]["Key"] == "key1"


@mock_aws
def test_delete_directory():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn = (
        f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-schema/1"
    )
    directory_arns = []
    for i in range(3):
        resp = client.create_directory(SchemaArn=schema_arn, Name=f"test-directory-{i}")
        directory_arns.append(resp["DirectoryArn"])

    directories = client.list_directories()["Directories"]
    assert len(directories) == 3

    resp = client.delete_directory(DirectoryArn=directory_arns[1])
    assert resp["DirectoryArn"] == directory_arns[1]

    directories = client.list_directories()["Directories"]
    assert len(directories) == 2
    for directory in directories:
        assert directory["DirectoryArn"] != directory_arns[1]


@mock_aws
def test_get_directory():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn = (
        f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-schema/1"
    )
    directory_arns = []
    for i in range(3):
        resp = client.create_directory(SchemaArn=schema_arn, Name=f"test-directory-{i}")
        directory_arns.append(resp["DirectoryArn"])

    directory = client.get_directory(DirectoryArn=directory_arns[0])["Directory"]
    assert "Name" in resp
    assert directory["DirectoryArn"] == directory_arns[0]
    assert directory["State"] == "ENABLED"
    assert "CreationDateTime" in directory


@mock_aws
def test_apply_schema_with_nonexistent_schema():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)

    schema = client.create_schema(Name="test-schema")
    schema_arn = schema["SchemaArn"]
    pub_schema = client.publish_schema(
        DevelopmentSchemaArn=schema_arn,
        Name="test-schema",
        Version="1",
        MinorVersion="0",
    )
    pub_schema_arn = pub_schema["PublishedSchemaArn"]
    directory = client.create_directory(SchemaArn=pub_schema_arn, Name="test-directory")
    directory_arn = directory["DirectoryArn"]

    non_existent_schema_arn = (
        f"arn:aws:clouddirectory:{region}:123456789012:schema/published/nonexistent/1/0"
    )

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.apply_schema(
            PublishedSchemaArn=non_existent_schema_arn, DirectoryArn=directory_arn
        )


@mock_aws
def test_apply_schema_updates_directory_schema():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)

    schema1 = client.create_schema(Name="test-schema1")
    schema1_arn = schema1["SchemaArn"]
    pub_schema1 = client.publish_schema(
        DevelopmentSchemaArn=schema1_arn,
        Name="test-schema1",
        Version="1",
        MinorVersion="0",
    )
    pub_schema1_arn = pub_schema1["PublishedSchemaArn"]

    directory = client.create_directory(
        SchemaArn=pub_schema1_arn, Name="test-directory"
    )
    directory_arn = directory["DirectoryArn"]

    schema2 = client.create_schema(Name="test-schema2")
    schema2_arn = schema2["SchemaArn"]
    pub_schema2 = client.publish_schema(
        DevelopmentSchemaArn=schema2_arn,
        Name="test-schema2",
        Version="1",
        MinorVersion="0",
    )
    pub_schema2_arn = pub_schema2["PublishedSchemaArn"]

    # Apply second schema to directory
    resp = client.apply_schema(
        PublishedSchemaArn=pub_schema2_arn, DirectoryArn=directory_arn
    )

    # Verify schema was updated
    assert resp["AppliedSchemaArn"] == pub_schema2_arn


@mock_aws
def test_publish_nonexistent_schema():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)

    non_existent_schema_arn = f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:schema/development/nonexistent"

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.publish_schema(
            DevelopmentSchemaArn=non_existent_schema_arn,
            Name="nonexistent",
            Version="1",
            MinorVersion="0",
        )


@mock_aws
def test_publish_schema_state_transition():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)

    dev_schema = client.create_schema(Name="test-schema")
    dev_schema_arn = dev_schema["SchemaArn"]

    dev_schemas = client.list_development_schema_arns()
    assert dev_schema_arn in dev_schemas["SchemaArns"]

    published = client.publish_schema(
        DevelopmentSchemaArn=dev_schema_arn,
        Name="test-schema",
        Version="1",
        MinorVersion="0",
    )
    published_schema_arn = published["PublishedSchemaArn"]

    dev_schemas = client.list_development_schema_arns()
    pub_schemas = client.list_published_schema_arns()

    assert dev_schema_arn not in dev_schemas["SchemaArns"]
    assert published_schema_arn in pub_schemas["SchemaArns"]
    assert (
        published_schema_arn
        == f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:schema/published/test-schema/1/0"
    )


@mock_aws
def test_publish_already_published_schema():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)

    schema = client.create_schema(Name="test-schema")
    schema_arn = schema["SchemaArn"]
    new_schema_arn = client.publish_schema(
        DevelopmentSchemaArn=schema_arn,
        Name="test-schema",
        Version="1",
        MinorVersion="0",
    )

    # Try to publish again with same development schema
    with pytest.raises(client.exceptions.SchemaAlreadyPublishedException):
        client.publish_schema(
            DevelopmentSchemaArn=new_schema_arn["PublishedSchemaArn"],
            Name="test-schema",
            Version="1",
            MinorVersion="0",
        )
