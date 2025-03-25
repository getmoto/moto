"""Unit tests for clouddirectory-supported APIs."""
import boto3

from moto import mock_aws
from tests import DEFAULT_ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_create_directory():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn = f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-schema/1"
    resp = client.create_directory(SchemaArn=schema_arn, Name="test-directory")
    assert resp["DirectoryArn"] == f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-directory"
    assert resp["Name"] == "test-directory"
    assert "ObjectIdentifier" in resp




@mock_aws
def test_list_directories():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    schema_arn = f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-schema/1"
    for i in range(3):
        client.create_directory(SchemaArn=schema_arn, Name=f"test-directory-{i}")
    
    resp = client.list_directories()
    assert len(resp["Directories"]) == 3
    
    directory = resp["Directories"][0]
    assert "Name" in directory
    assert "DirectoryArn" in directory
    assert "State" in directory
    assert "CreationDateTime" in directory


@mock_aws
def test_tag_resource():
    client = boto3.client("clouddirectory", region_name="us-east-2")
    resp = client.tag_resource()

    raise Exception("NotYetImplemented")


@mock_aws
def test_untag_resource():
    client = boto3.client("clouddirectory", region_name="us-east-2")
    resp = client.untag_resource()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_directory():
    client = boto3.client("clouddirectory", region_name="eu-west-1")
    resp = client.delete_directory()

    raise Exception("NotYetImplemented")


@mock_aws
def test_get_directory():
    client = boto3.client("clouddirectory", region_name="ap-southeast-1")
    resp = client.get_directory()

    raise Exception("NotYetImplemented")
