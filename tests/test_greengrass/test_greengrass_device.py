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
