import boto3
from botocore.client import ClientError
import freezegun
import pytest

from moto import mock_greengrass
from moto.settings import TEST_SERVER_MODE


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


@mock_greengrass
def test_create_resource_definition_with_invalid_volume_resource():

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
                        "SourcePath": "/sys/foo",
                    }
                },
            }
        ]
    }

    with pytest.raises(ClientError) as ex:
        client.create_resource_definition(InitialVersion=init_ver)
    ex.value.response["Error"]["Message"].should.equal(
        "The resources definition is invalid. (ErrorDetails: [Accessing /sys is prohibited])"
    )
    ex.value.response["Error"]["Code"].should.equal("400")


@mock_greengrass
def test_create_resource_definition_with_invalid_local_device_resource():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    source_path = "/foo/bar"
    init_ver = {
        "Resources": [
            {
                "Id": "123",
                "Name": "test_directory",
                "ResourceDataContainer": {
                    "LocalDeviceResourceData": {
                        "SourcePath": source_path,
                    }
                },
            }
        ]
    }

    with pytest.raises(ClientError) as ex:
        client.create_resource_definition(InitialVersion=init_ver)
    ex.value.response["Error"]["Message"].should.equal(
        f"The resources definition is invalid. (ErrorDetails: [Device resource path should begin with "
        "/dev"
        f", but got: {source_path}])"
    )
    ex.value.response["Error"]["Code"].should.equal("400")


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


@mock_greengrass
def test_create_resources_definition_version_with_volume_resource():

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
            "Id": "123",
            "Name": "test_directory",
            "ResourceDataContainer": {
                "LocalVolumeResourceData": {
                    "DestinationPath": "/test_dir",
                    "GroupOwnerSetting": {"AutoAddGroupOwner": True},
                    "SourcePath": "/sys/block/sda",
                }
            },
        }
    ]
    with pytest.raises(ClientError) as ex:
        client.create_resource_definition_version(
            ResourceDefinitionId=resource_def_id, Resources=v2_resources
        )
    ex.value.response["Error"]["Message"].should.equal(
        "The resources definition is invalid. (ErrorDetails: [Accessing /sys is prohibited])"
    )
    ex.value.response["Error"]["Code"].should.equal("400")


@mock_greengrass
def test_create_resources_definition_version_with_invalid_local_device_resource():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    v1_resources = [
        {
            "Id": "123",
            "Name": "test_directory",
            "ResourceDataContainer": {
                "LocalDeviceResourceData": {
                    "SourcePath": "/dev/null",
                }
            },
        }
    ]

    initial_version = {"Resources": v1_resources}
    resource_def_res = client.create_resource_definition(
        InitialVersion=initial_version, Name="TestResource"
    )
    resource_def_id = resource_def_res["Id"]

    source_path = "/foo/bar"
    v2_resources = [
        {
            "Id": "123",
            "Name": "test_directory",
            "ResourceDataContainer": {
                "LocalDeviceResourceData": {"SourcePath": source_path}
            },
        }
    ]
    with pytest.raises(ClientError) as ex:
        client.create_resource_definition_version(
            ResourceDefinitionId=resource_def_id, Resources=v2_resources
        )
    ex.value.response["Error"]["Message"].should.equal(
        f"The resources definition is invalid. (ErrorDetails: [Device resource path should begin with "
        "/dev"
        f", but got: {source_path}])"
    )
    ex.value.response["Error"]["Code"].should.equal("400")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_resources():
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
    resource_name = "MotoTestResource"
    create_res = client.create_resource_definition(
        InitialVersion=init_ver, Name=resource_name
    )

    res_def_id = create_res["Id"]
    res_def_arn = create_res["Arn"]
    res_ver = create_res["LatestVersion"]
    res_ver_arn = create_res["LatestVersionArn"]

    res = client.list_resource_definitions()
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    res.should.have.key("Definitions")
    res["Definitions"].should.have.length_of(1)
    definition = res["Definitions"][0]
    definition.should.have.key("Id").equals(res_def_id)
    definition.should.have.key("Arn").equals(res_def_arn)
    definition.should.have.key("LatestVersion").equals(res_ver)
    definition.should.have.key("LatestVersionArn").equals(res_ver_arn)

    if not TEST_SERVER_MODE:
        definition.should.have.key("CreationTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )
        definition.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_resource_definition():

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
    resource_name = "MotoTestResource"
    create_res = client.create_resource_definition(
        InitialVersion=init_ver, Name=resource_name
    )

    resource_def_id = create_res["Id"]
    arn = create_res["Arn"]
    latest_version = create_res["LatestVersion"]
    latest_version_arn = create_res["LatestVersionArn"]

    get_res = client.get_resource_definition(ResourceDefinitionId=resource_def_id)

    get_res.should.have.key("Name").equals(resource_name)
    get_res.should.have.key("Arn").equals(arn)
    get_res.should.have.key("Id").equals(resource_def_id)
    get_res.should.have.key("LatestVersion").equals(latest_version)
    get_res.should.have.key("LatestVersionArn").equals(latest_version_arn)

    if not TEST_SERVER_MODE:
        get_res.should.have.key("CreationTimestamp").equal("2022-06-01T12:00:00.000Z")
        get_res.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@mock_greengrass
def test_get_resource_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_resource_definition(
            ResourceDefinitionId="76f22a66-176a-4474-b450-04099dc4b069"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That Resource List Definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_delete_resource_definition():

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
    create_res = client.create_resource_definition(
        InitialVersion=init_ver, Name="TestResource"
    )

    resource_def_id = create_res["Id"]
    del_res = client.delete_resource_definition(ResourceDefinitionId=resource_def_id)
    del_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_greengrass
def test_delete_resource_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.delete_resource_definition(
            ResourceDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That resources definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_update_resource_definition():

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
    create_res = client.create_resource_definition(
        InitialVersion=init_ver, Name="TestResource"
    )
    resource_def_id = create_res["Id"]
    updated_resource_name = "UpdatedResource"
    update_res = client.update_resource_definition(
        ResourceDefinitionId=resource_def_id, Name=updated_resource_name
    )
    update_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    get_res = client.get_resource_definition(ResourceDefinitionId=resource_def_id)
    get_res.should.have.key("Name").equals(updated_resource_name)


@mock_greengrass
def test_update_device_definition_with_empty_name():

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
    create_res = client.create_resource_definition(
        InitialVersion=init_ver, Name="TestResource"
    )
    resource_def_id = create_res["Id"]

    with pytest.raises(ClientError) as ex:
        client.update_resource_definition(ResourceDefinitionId=resource_def_id, Name="")
    ex.value.response["Error"]["Message"].should.equal("Invalid resource name.")
    ex.value.response["Error"]["Code"].should.equal("InvalidInputException")


@mock_greengrass
def test_update_resource_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.update_resource_definition(
            ResourceDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="123"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That resources definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_resource_definition_versions():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    resources = [
        {
            "Id": "123",
            "Name": "test_directory",
            "ResourceDataContainer": {
                "LocalDeviceResourceData": {
                    "SourcePath": "/dev/null",
                }
            },
        }
    ]

    initial_version = {"Resources": resources}
    create_res = client.create_resource_definition(
        InitialVersion=initial_version, Name="TestResource"
    )
    resource_def_id = create_res["Id"]

    resource_def_vers_res = client.list_resource_definition_versions(
        ResourceDefinitionId=resource_def_id
    )

    resource_def_vers_res.should.have.key("Versions")
    resource_def_vers_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    device_def_ver = resource_def_vers_res["Versions"][0]
    device_def_ver.should.have.key("Arn")
    device_def_ver.should.have.key("CreationTimestamp")
    device_def_ver.should.have.key("Id").equals(resource_def_id)
    device_def_ver.should.have.key("Version")

    if not TEST_SERVER_MODE:
        device_def_ver["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_list_resource_definition_versions_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.list_resource_definition_versions(
            ResourceDefinitionId="fe2392e9-e67f-4308-af1b-ff94a128b231"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That resources definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_resource_definition_version():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    resources = [
        {
            "Id": "123",
            "Name": "test_directory",
            "ResourceDataContainer": {
                "LocalDeviceResourceData": {
                    "SourcePath": "/dev/null",
                }
            },
        }
    ]

    initial_version = {"Resources": resources}
    create_res = client.create_resource_definition(
        InitialVersion=initial_version, Name="TestResource"
    )
    resource_def_id = create_res["Id"]
    resource_def_ver_id = create_res["LatestVersion"]

    resource_def_ver_res = client.get_resource_definition_version(
        ResourceDefinitionId=resource_def_id,
        ResourceDefinitionVersionId=resource_def_ver_id,
    )

    resource_def_ver_res.should.have.key("Arn")
    resource_def_ver_res.should.have.key("CreationTimestamp")
    resource_def_ver_res.should.have.key("Definition").should.equal(initial_version)
    resource_def_ver_res.should.have.key("Id").equals(resource_def_id)
    resource_def_ver_res.should.have.key("Version")
    resource_def_ver_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    if not TEST_SERVER_MODE:
        resource_def_ver_res["CreationTimestamp"].should.equal(
            "2022-06-01T12:00:00.000Z"
        )


@mock_greengrass
def test_get_resource_definition_version_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_resource_definition_version(
            ResourceDefinitionId="fe2392e9-e67f-4308-af1b-ff94a128b231",
            ResourceDefinitionVersionId="cd2ea6dc-6634-4e89-8441-8003500435f9",
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That resources definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_get_resource_definition_version_with_invalid_version_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    resources = [
        {
            "Id": "123",
            "Name": "test_directory",
            "ResourceDataContainer": {
                "LocalDeviceResourceData": {
                    "SourcePath": "/dev/null",
                }
            },
        }
    ]

    initial_version = {"Resources": resources}
    create_res = client.create_resource_definition(
        InitialVersion=initial_version, Name="TestResource"
    )

    resource_def_id = create_res["Id"]
    invalid_resource_version_id = "6fbffc21-989e-4d29-a793-a42f450a78c6"
    with pytest.raises(ClientError) as ex:
        client.get_resource_definition_version(
            ResourceDefinitionId=resource_def_id,
            ResourceDefinitionVersionId=invalid_resource_version_id,
        )
    ex.value.response["Error"]["Message"].should.equal(
        f"Version {invalid_resource_version_id} of Resource List Definition {resource_def_id} does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("VersionNotFoundException")
