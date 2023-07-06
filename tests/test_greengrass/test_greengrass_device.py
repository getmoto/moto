import boto3
from botocore.client import ClientError
import freezegun
import pytest

from moto import mock_greengrass
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.settings import TEST_SERVER_MODE


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_device_definition():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Devices": [
            {
                "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                "Id": "123",
                "SyncShadow": True,
                "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
            }
        ]
    }

    device_name = "TestDevice"
    res = client.create_device_definition(InitialVersion=init_ver, Name=device_name)
    assert "Arn" in res
    assert "Id" in res
    assert "LatestVersion" in res
    assert "LatestVersionArn" in res
    assert res["Name"] == device_name
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201

    if not TEST_SERVER_MODE:
        assert res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert res["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_device_definitions():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Devices": [
            {
                "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                "Id": "123",
                "SyncShadow": True,
                "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
            }
        ]
    }

    device_name = "TestDevice"
    client.create_device_definition(InitialVersion=init_ver, Name=device_name)

    res = client.list_device_definitions()
    assert "Definitions" in res
    device_definition = res["Definitions"][0]

    assert device_definition["Name"] == device_name
    assert "Arn" in device_definition
    assert "Id" in device_definition
    assert "LatestVersion" in device_definition
    assert "LatestVersionArn" in device_definition
    if not TEST_SERVER_MODE:
        assert device_definition["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert device_definition["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_device_definition():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Devices": [
            {
                "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                "Id": "123",
                "SyncShadow": True,
                "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
            }
        ]
    }

    device_name = "TestDevice"
    create_res = client.create_device_definition(
        InitialVersion=init_ver, Name=device_name
    )
    device_def_id = create_res["Id"]
    arn = create_res["Arn"]
    latest_version = create_res["LatestVersion"]
    latest_version_arn = create_res["LatestVersionArn"]

    get_res = client.get_device_definition(DeviceDefinitionId=device_def_id)

    assert get_res["Name"] == device_name
    assert get_res["Arn"] == arn
    assert get_res["Id"] == device_def_id
    assert get_res["LatestVersion"] == latest_version
    assert get_res["LatestVersionArn"] == latest_version_arn

    if not TEST_SERVER_MODE:
        assert get_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert get_res["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


@mock_greengrass
def test_get_device_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_device_definition(
            DeviceDefinitionId="b552443b-1888-469b-81f8-0ebc5ca92949"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That Device List Definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_device_definition_version():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    v1_devices = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123",
            "SyncShadow": True,
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
        }
    ]

    initial_version = {"Devices": v1_devices}
    device_def_res = client.create_device_definition(
        InitialVersion=initial_version, Name="TestDevice"
    )
    device_def_id = device_def_res["Id"]

    v2_devices = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/277a6a15293c1ed5fa1aa74bae890b1827f80959537bfdcf10f63e661d54ebe1",
            "Id": "987654321",
            "SyncShadow": False,
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v2Thing",
        }
    ]

    device_def_ver_res = client.create_device_definition_version(
        DeviceDefinitionId=device_def_id, Devices=v2_devices
    )
    assert "Arn" in device_def_ver_res
    assert "CreationTimestamp" in device_def_ver_res
    assert device_def_ver_res["Id"] == device_def_id
    assert "Version" in device_def_ver_res

    if not TEST_SERVER_MODE:
        assert device_def_ver_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_device_definition_version_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    devices = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123",
            "SyncShadow": True,
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
        }
    ]

    client.create_device_definition(
        InitialVersion={"Devices": devices}, Name="TestDevice"
    )

    with pytest.raises(ClientError) as ex:
        client.create_device_definition_version(
            DeviceDefinitionId="123", Devices=devices
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That devices definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@mock_greengrass
def test_delete_device_definition():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    devices = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123",
            "SyncShadow": True,
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
        }
    ]

    create_res = client.create_device_definition(
        InitialVersion={"Devices": devices}, Name="TestDevice"
    )

    device_def_id = create_res["Id"]
    del_res = client.delete_device_definition(DeviceDefinitionId=device_def_id)
    assert del_res["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_greengrass
def test_delete_device_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.delete_device_definition(
            DeviceDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That devices definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@mock_greengrass
def test_update_device_definition():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    devices = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123",
            "SyncShadow": True,
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
        }
    ]

    initial_version = {"Devices": devices}
    create_res = client.create_device_definition(
        InitialVersion=initial_version, Name="TestDevice"
    )
    device_def_id = create_res["Id"]
    updated_device_name = "UpdatedDevice"
    update_res = client.update_device_definition(
        DeviceDefinitionId=device_def_id, Name=updated_device_name
    )
    assert update_res["ResponseMetadata"]["HTTPStatusCode"] == 200

    get_res = client.get_device_definition(DeviceDefinitionId=device_def_id)
    assert get_res["Name"] == updated_device_name


@mock_greengrass
def test_update_device_definition_with_empty_name():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    devices = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123",
            "SyncShadow": True,
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
        }
    ]

    initial_version = {"Devices": devices}
    create_res = client.create_device_definition(
        InitialVersion=initial_version, Name="TestDevice"
    )
    device_def_id = create_res["Id"]

    with pytest.raises(ClientError) as ex:
        client.update_device_definition(DeviceDefinitionId=device_def_id, Name="")
    err = ex.value.response["Error"]
    assert err["Message"] == "Input does not contain any attributes to be updated"
    assert err["Code"] == "InvalidContainerDefinitionException"


@mock_greengrass
def test_update_device_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.update_device_definition(
            DeviceDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="123"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That devices definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_device_definition_versions():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    devices = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123",
            "SyncShadow": True,
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
        }
    ]

    initial_version = {"Devices": devices}
    create_res = client.create_device_definition(
        InitialVersion=initial_version, Name="TestDevice"
    )
    device_def_id = create_res["Id"]

    device_def_vers_res = client.list_device_definition_versions(
        DeviceDefinitionId=device_def_id
    )

    assert "Versions" in device_def_vers_res
    device_def_ver = device_def_vers_res["Versions"][0]
    assert "Arn" in device_def_ver
    assert "CreationTimestamp" in device_def_ver

    if not TEST_SERVER_MODE:
        assert device_def_ver["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
    assert device_def_ver["Id"] == device_def_id
    assert "Version" in device_def_ver


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_device_definition_version():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    devices = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123",
            "SyncShadow": True,
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
        }
    ]

    initial_version = {"Devices": devices}
    create_res = client.create_device_definition(
        InitialVersion=initial_version, Name="TestDevice"
    )

    device_def_id = create_res["Id"]
    device_def_ver_id = create_res["LatestVersion"]

    core_def_ver_res = client.get_device_definition_version(
        DeviceDefinitionId=device_def_id, DeviceDefinitionVersionId=device_def_ver_id
    )

    assert "Arn" in core_def_ver_res
    assert "CreationTimestamp" in core_def_ver_res
    assert core_def_ver_res["Definition"] == initial_version
    if not TEST_SERVER_MODE:
        assert core_def_ver_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
    assert core_def_ver_res["Id"] == device_def_id
    assert "Version" in core_def_ver_res


@mock_greengrass
def test_get_device_definition_version_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_device_definition_version(
            DeviceDefinitionId="fe2392e9-e67f-4308-af1b-ff94a128b231",
            DeviceDefinitionVersionId="cd2ea6dc-6634-4e89-8441-8003500435f9",
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That devices definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@mock_greengrass
def test_get_device_definition_version_with_invalid_version_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    devices = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123",
            "SyncShadow": True,
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
        }
    ]

    initial_version = {"Devices": devices}
    create_res = client.create_device_definition(
        InitialVersion=initial_version, Name="TestDevice"
    )

    device_def_id = create_res["Id"]
    invalid_device_version_id = "6fbffc21-989e-4d29-a793-a42f450a78c6"
    with pytest.raises(ClientError) as ex:
        client.get_device_definition_version(
            DeviceDefinitionId=device_def_id,
            DeviceDefinitionVersionId=invalid_device_version_id,
        )
    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == f"Version {invalid_device_version_id} of Device List Definition {device_def_id} does not exist."
    )
    assert err["Code"] == "VersionNotFoundException"
