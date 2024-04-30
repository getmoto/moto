"""Unit tests for fsx-supported APIs."""
import time

import boto3
import pytest

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
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS
    )

    file_system = resp["FileSystem"]

    assert file_system["FileSystemId"].startswith("fs-moto")
    assert file_system["FileSystemType"] == "LUSTRE"
    #assert len(file_system["SecurityGroupIds"]) == len(FAKE_SECURITY_GROUP_IDS)


@mock_aws
def test_describe_filesystems():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    # Create a LUSTRE file system
    client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS
    )

    time.sleep(1)

    # Create another WINDOWS file system
    client.create_file_system(
        FileSystemType="WINDOWS",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS
    )

    time.sleep(1)

    resp = client.describe_file_systems()
    file_systems = resp["FileSystems"]

    assert len(file_systems) == 2
    assert file_systems[0]["FileSystemType"] == "LUSTRE"
    assert file_systems[1]["FileSystemType"] == "WINDOWS"

@mock_aws
def test_delete_file_system():
    client = boto3.client("fsx", region_name=TEST_REGION_NAME)
    # Create a LUSTRE file system
    fs = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS
    )

    assert fs["FileSystem"]["FileSystemId"].startswith("fs-moto")
    file_system_id = fs["FileSystem"]["FileSystemId"]
    resp = client.delete_file_system(FileSystemId=file_system_id)
    assert resp["FileSystemId"] == file_system_id
    assert resp["Lifecycle"] == "DELETING"
    assert resp["LustreResponse"] is not None

    
@pytest.mark.skip("NotYetImplemented")
def test_tag_resource():
    client = boto3.client("fsx", region_name="us-east-2")
    resp = client.tag_resource()

    raise Exception("NotYetImplemented")
