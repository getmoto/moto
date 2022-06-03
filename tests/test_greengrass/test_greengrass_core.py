import boto3
import freezegun

from moto import mock_greengrass
from moto.core import get_account_id
from moto.settings import TEST_SERVER_MODE

ACCOUNT_ID = get_account_id()


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_core_definition():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123456789",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
        }
    ]

    initial_version = {"Cores": cores}

    core_name = "TestCore"
    res = client.create_core_definition(InitialVersion=initial_version, Name=core_name)
    res.should.have.key("Arn")
    res.should.have.key("Id")
    if not TEST_SERVER_MODE:
        res.should.have.key("CreationTimestamp").equals("2022-06-01T12:00:00.000Z")
        res.should.have.key("LastUpdatedTimestamp").equals("2022-06-01T12:00:00.000Z")
    res.should.have.key("LatestVersionArn")
    res.should.have.key("Name").equals(core_name)
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_core_definition_version():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    v1_cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123456789",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
        }
    ]

    initial_version = {"Cores": v1_cores}

    core_def_res = client.create_core_definition(
        InitialVersion=initial_version, Name="TestCore"
    )
    core_def_id = core_def_res["Id"]

    v2_cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/277a6a15293c1ed5fa1aa74bae890b1827f80959537bfdcf10f63e661d54ebe1",
            "Id": "987654321",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v2Thing",
        }
    ]

    core_def_ver_res = client.create_core_definition_version(
        CoreDefinitionId=core_def_id, Cores=v2_cores
    )
    core_def_ver_res.should.have.key("Arn")
    core_def_ver_res.should.have.key("CreationTimestamp")
    if not TEST_SERVER_MODE:
        core_def_ver_res["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")
    core_def_ver_res.should.have.key("Id").equals(core_def_id)
    core_def_ver_res.should.have.key("Version")
