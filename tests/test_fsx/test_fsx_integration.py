import boto3
import pytest

from moto import mock_aws

TEST_REGION_NAME = "us-east-1"
FAKE_SUBNET_ID = "subnet-012345678"
FAKE_SECURITY_GROUP_IDS = ["sg-0123456789abcdef0", "sg-0123456789abcdef1"]


@pytest.fixture(name="client")
@mock_aws
def get_client():
    return boto3.client("fsx", region_name=TEST_REGION_NAME)


@pytest.fixture(name="resource_groups_client")
@mock_aws
def get_resource_groups_client():
    return boto3.client("resourcegroupstaggingapi", region_name=TEST_REGION_NAME)


@mock_aws
def test_fsx_file_system_service_tagging_api(client, resource_groups_client):
    tags = [
        {"Key": "Moto", "Value": "Hello"},
        {"Key": "Environment", "Value": "Dev"},
    ]
    resp = client.create_file_system(
        FileSystemType="LUSTRE",
        StorageCapacity=1200,
        StorageType="SSD",
        SubnetIds=[FAKE_SUBNET_ID],
        SecurityGroupIds=FAKE_SECURITY_GROUP_IDS,
        Tags=tags,
    )

    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    file_system = resp["FileSystem"]
    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[file_system["ResourceARN"]],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert resource_group_tags[0]["ResourceARN"] == file_system["ResourceARN"]
    assert resource_group_tags[0]["Tags"] == tags


@mock_aws
def test_fsx_backup_service_tagging_api(client, resource_groups_client):
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

    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    file_system = resp["Backup"]
    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[file_system["ResourceARN"]],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert resource_group_tags[0]["ResourceARN"] == file_system["ResourceARN"]
    assert resource_group_tags[0]["Tags"] == tags
