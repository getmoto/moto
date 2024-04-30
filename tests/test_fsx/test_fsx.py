"""Unit tests for fsx-supported APIs."""
import pytest
import boto3

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

def test_describe_file_systems(client):
    resp = client.describe_file_systems()
    assert resp == []

def test_create_filesystem(client):
    file_system = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS
    )

    assert file_system is None
    assert file_system["FileSystem"]["FileSystemId"].startswith("fs-moto")

