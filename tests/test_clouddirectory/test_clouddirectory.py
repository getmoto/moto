"""Unit tests for clouddirectory-supported APIs."""

import boto3

from moto import mock_aws
from tests import DEFAULT_ACCOUNT_ID


@mock_aws
def test_create_directory():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn = (
        f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-schema/1"
    )
    resp = client.create_directory(SchemaArn=schema_arn, Name="test-directory")
    assert (
        resp["DirectoryArn"]
        == f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-directory"
    )
    assert resp["Name"] == "test-directory"
    assert "ObjectIdentifier" in resp


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

    # Test resourcetaggingapi
    rtapi = boto3.client("resourcegroupstaggingapi", region_name=region)
    resp = rtapi.get_resources(ResourceTypeFilters=["clouddirectory"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == directory_arn
    assert resp["ResourceTagMappingList"][0]["Tags"][0]["Key"] == "key1"
    assert resp["ResourceTagMappingList"][0]["Tags"][0]["Value"] == "value1"


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
