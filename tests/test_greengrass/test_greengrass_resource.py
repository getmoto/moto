import boto3
from botocore.client import ClientError
import freezegun
import pytest

from moto import mock_greengrass
from moto.core import get_account_id
from moto.settings import TEST_SERVER_MODE

ACCOUNT_ID = get_account_id()


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_resource_definition():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Resources": [
            {
                "Id": "123",
                "Name": "test_directory",
                "ResourceDataContainer": {
                    "LocalVolumeResourceData": {
                        "DestinationPath": "/test_dir",
                        "GroupOwnerSetting": {"AutoAddGroupOwner": True},
                        "SourcePath": "/home/ggc_user/test_dir",
                    }
                },
            }
        ]
    }

    resource_name = "TestResource"
    res = client.create_resource_definition(InitialVersion=init_ver, Name=resource_name)
    res.should.have.key("Arn")
    res.should.have.key("Id")
    res.should.have.key("LatestVersion")
    res.should.have.key("LatestVersionArn")
    res.should.have.key("Name").equals(resource_name)
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)

    if not TEST_SERVER_MODE:
        res.should.have.key("CreationTimestamp").equals("2022-06-01T12:00:00.000Z")
        res.should.have.key("LastUpdatedTimestamp").equals("2022-06-01T12:00:00.000Z")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_resource_definition_version():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    v1_resources = [
        {
            "Id": "123",
            "Name": "test_directory",
            "ResourceDataContainer": {
                "LocalVolumeResourceData": {
                    "DestinationPath": "/test_dir",
                    "GroupOwnerSetting": {"AutoAddGroupOwner": True},
                    "SourcePath": "/home/ggc_user/test_dir",
                }
            },
        }
    ]

    initial_version = {"Resources": v1_resources}
    resource_def_res = client.create_resource_definition(
        InitialVersion=initial_version, Name="TestResource"
    )
    resource_def_id = resource_def_res["Id"]

    v2_resources = [
        {
            "Id": "234",
            "Name": "test_directory2",
            "ResourceDataContainer": {
                "LocalVolumeResourceData": {
                    "DestinationPath": "/test_dir2",
                    "GroupOwnerSetting": {"AutoAddGroupOwner": True},
                    "SourcePath": "/home/ggc_user/test_dir2",
                }
            },
        }
    ]

    device_def_ver_res = client.create_resource_definition_version(
        ResourceDefinitionId=resource_def_id, Resources=v2_resources
    )
    device_def_ver_res.should.have.key("Arn")
    device_def_ver_res.should.have.key("CreationTimestamp")
    device_def_ver_res.should.have.key("Id").equals(resource_def_id)
    device_def_ver_res.should.have.key("Version")

    if not TEST_SERVER_MODE:
        device_def_ver_res["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_create_resources_definition_version_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    resources = [
        {
            "Id": "123",
            "Name": "test_directory",
            "ResourceDataContainer": {
                "LocalVolumeResourceData": {
                    "DestinationPath": "/test_dir",
                    "GroupOwnerSetting": {"AutoAddGroupOwner": True},
                    "SourcePath": "/home/ggc_user/test_dir",
                }
            },
        }
    ]
    with pytest.raises(ClientError) as ex:
        client.create_resource_definition_version(
            ResourceDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
            Resources=resources,
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That resource definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")
