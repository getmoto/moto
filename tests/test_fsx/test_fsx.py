"""Unit tests for fsx-supported APIs."""

import re

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

TEST_REGION_NAME = "us-east-1"
FAKE_SUBNET_ID = "subnet-012345678"
FAKE_SECURITY_GROUP_IDS = ["sg-0123456789abcdef0", "sg-0123456789abcdef1"]


@pytest.fixture(name="client")
def fixture_fsx_client():
    with mock_aws():
        yield boto3.client("fsx", region_name=TEST_REGION_NAME)


def test_create_filesystem(client):
    resp = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
    )

    file_system = resp["FileSystem"]

    assert re.match(r"^fs-[0-9a-f]{8,}$", file_system["FileSystemId"])
    assert file_system["FileSystemType"] == "LUSTRE"


@mock_aws
def test_describe_filesystems():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    # Create a LUSTRE file system
    client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
    )

    # Create another WINDOWS file system
    client.create_file_system(
        FileSystemType="WINDOWS",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
    )

    resp = client.describe_file_systems()
    file_systems = resp["FileSystems"]

    assert len(file_systems) == 2
    assert file_systems[0]["FileSystemType"] == "LUSTRE"
    assert file_systems[1]["FileSystemType"] == "WINDOWS"


@mock_aws
def test_describe_filesystems_does_not_exist():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    resp = client.describe_file_systems(FileSystemIds=["fs-1234567890"])
    file_systems = resp["FileSystems"]

    assert len(file_systems) == 0


@mock_aws
def test_delete_file_system():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    # Create a LUSTRE file system
    fs = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
    )

    file_system_id = fs["FileSystem"]["FileSystemId"]
    resp = client.delete_file_system(FileSystemId=file_system_id)
    assert resp["FileSystemId"] == file_system_id
    assert resp["Lifecycle"] == "DELETING"
    assert resp["LustreResponse"] is not None


@mock_aws
def test_create_backup():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    tags = [
        {"Key": "Moto", "Value": "Hello"},
        {"Key": "Environment", "Value": "Dev"},
    ]
    fs = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
    )
    resp = client.create_backup(
        FileSystemId=fs["FileSystem"]["FileSystemId"], Tags=tags
    )

    backup = resp["Backup"]
    assert backup["BackupId"].startswith("backup-")
    assert backup["ResourceARN"].startswith("arn:aws:fsx:")
    assert backup["Tags"] == tags


@mock_aws
def test_nonexistent_file_system():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)

    with pytest.raises(ClientError) as exc:
        client.create_backup(
            FileSystemId="NONEXISTENTFILESYSTEMID",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "FSx resource, NONEXISTENTFILESYSTEMID does not exist"


@mock_aws
def test_delete_backup():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    fs = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
    )
    resp = client.create_backup(FileSystemId=fs["FileSystem"]["FileSystemId"])

    backup = resp["Backup"]
    assert backup["BackupId"].startswith("backup-")
    assert backup["ResourceARN"].startswith("arn:aws:fsx:")

    resp = client.delete_backup(BackupId=backup["BackupId"])
    assert resp["BackupId"] == backup["BackupId"]
    assert resp["Lifecycle"] == "DELETED"


@mock_aws
def test_backup_not_found():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        client.delete_backup(BackupId="NONEXISTENTBACKUPID")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "FSx resource, NONEXISTENTBACKUPID does not exist"


@mock_aws
def test_tag_resource():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    fs = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
    )
    file_system_id = fs["FileSystem"]["FileSystemId"]

    resp = client.describe_file_systems(FileSystemIds=[file_system_id])
    resource_arn = resp["FileSystems"][0]["ResourceARN"]
    tags = [
        {"Key": "Moto", "Value": "Hello"},
        {"Key": "Environment", "Value": "Dev"},
    ]

    client.tag_resource(ResourceARN=resource_arn, Tags=tags)

    resp = client.describe_file_systems(FileSystemIds=[file_system_id])
    assert resp["FileSystems"][0]["Tags"] == tags


@mock_aws
def test_untag_resource():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    fs = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
        Tags=[
            {"Key": "Moto", "Value": "Hello"},
            {"Key": "Environment", "Value": "Dev"},
        ],
    )
    file_system_id = fs["FileSystem"]["FileSystemId"]

    resp = client.describe_file_systems(FileSystemIds=[file_system_id])
    resource_arn = resp["FileSystems"][0]["ResourceARN"]

    tag_keys = ["Moto"]

    client.untag_resource(ResourceARN=resource_arn, TagKeys=tag_keys)

    resp = client.describe_file_systems(FileSystemIds=[file_system_id])
    assert len(resp["FileSystems"][0]["Tags"]) == 1
    assert resp["FileSystems"][0]["Tags"] == [{"Key": "Environment", "Value": "Dev"}]


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    fs = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
    )

    tags = [
        {"Key": "Moto", "Value": "Hello"},
        {"Key": "Environment", "Value": "Dev"},
    ]
    resource_arn = fs["FileSystem"]["ResourceARN"]
    client.tag_resource(ResourceARN=resource_arn, Tags=tags)
    resp = client.list_tags_for_resource(ResourceARN=resource_arn)
    assert len(resp["Tags"]) == 2
    assert resp["Tags"] == tags
