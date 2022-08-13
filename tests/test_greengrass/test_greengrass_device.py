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
    res.should.have.key("Arn")
    res.should.have.key("Id")
    res.should.have.key("LatestVersion")
    res.should.have.key("LatestVersionArn")
    res.should.have.key("Name").equals(device_name)
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)

    if not TEST_SERVER_MODE:
        res.should.have.key("CreationTimestamp").equals("2022-06-01T12:00:00.000Z")
        res.should.have.key("LastUpdatedTimestamp").equals("2022-06-01T12:00:00.000Z")


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
    res.should.have.key("Definitions")
    device_definition = res["Definitions"][0]

    device_definition.should.have.key("Name").equals(device_name)
    device_definition.should.have.key("Arn")
    device_definition.should.have.key("Id")
    device_definition.should.have.key("LatestVersion")
    device_definition.should.have.key("LatestVersionArn")
    if not TEST_SERVER_MODE:
        device_definition.should.have.key("CreationTimestamp").equal(
            "2022-06-01T12:00:00.000Z"
        )
        device_definition.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


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

    get_res.should.have.key("Name").equals(device_name)
    get_res.should.have.key("Arn").equals(arn)
    get_res.should.have.key("Id").equals(device_def_id)
    get_res.should.have.key("LatestVersion").equals(latest_version)
    get_res.should.have.key("LatestVersionArn").equals(latest_version_arn)

    if not TEST_SERVER_MODE:
        get_res.should.have.key("CreationTimestamp").equal("2022-06-01T12:00:00.000Z")
        get_res.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@mock_greengrass
def test_get_device_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_device_definition(
            DeviceDefinitionId="b552443b-1888-469b-81f8-0ebc5ca92949"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That Device List Definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


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
    device_def_ver_res.should.have.key("Arn")
    device_def_ver_res.should.have.key("CreationTimestamp")
    device_def_ver_res.should.have.key("Id").equals(device_def_id)
    device_def_ver_res.should.have.key("Version")

    if not TEST_SERVER_MODE:
        device_def_ver_res["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")


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
    ex.value.response["Error"]["Message"].should.equal(
        "That devices definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


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
    del_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_greengrass
def test_delete_device_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.delete_device_definition(
            DeviceDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That devices definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


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
    update_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    get_res = client.get_device_definition(DeviceDefinitionId=device_def_id)
    get_res.should.have.key("Name").equals(updated_device_name)


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
    ex.value.response["Error"]["Message"].should.equal(
        "Input does not contain any attributes to be updated"
    )
    ex.value.response["Error"]["Code"].should.equal(
        "InvalidContainerDefinitionException"
    )


@mock_greengrass
def test_update_device_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.update_device_definition(
            DeviceDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="123"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That devices definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


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

    device_def_vers_res.should.have.key("Versions")
    device_def_ver = device_def_vers_res["Versions"][0]
    device_def_ver.should.have.key("Arn")
    device_def_ver.should.have.key("CreationTimestamp")

    if not TEST_SERVER_MODE:
        device_def_ver["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")
    device_def_ver.should.have.key("Id").equals(device_def_id)
    device_def_ver.should.have.key("Version")


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

    core_def_ver_res.should.have.key("Arn")
    core_def_ver_res.should.have.key("CreationTimestamp")
    core_def_ver_res.should.have.key("Definition").should.equal(initial_version)
    if not TEST_SERVER_MODE:
        core_def_ver_res["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")
    core_def_ver_res.should.have.key("Id").equals(device_def_id)
    core_def_ver_res.should.have.key("Version")


@mock_greengrass
def test_get_device_definition_version_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_device_definition_version(
            DeviceDefinitionId="fe2392e9-e67f-4308-af1b-ff94a128b231",
            DeviceDefinitionVersionId="cd2ea6dc-6634-4e89-8441-8003500435f9",
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That devices definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


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
    ex.value.response["Error"]["Message"].should.equal(
        f"Version {invalid_device_version_id} of Device List Definition {device_def_id} does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("VersionNotFoundException")
