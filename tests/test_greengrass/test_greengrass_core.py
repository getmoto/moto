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
def test_list_core_definitions():

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
    client.create_core_definition(InitialVersion=initial_version, Name=core_name)
    res = client.list_core_definitions()
    res.should.have.key("Definitions")
    core_definition = res["Definitions"][0]

    core_definition.should.have.key("Name").equals(core_name)
    core_definition.should.have.key("Arn")
    core_definition.should.have.key("Id")
    core_definition.should.have.key("LatestVersion")
    core_definition.should.have.key("LatestVersionArn")
    if not TEST_SERVER_MODE:
        core_definition.should.have.key("CreationTimestamp").equal(
            "2022-06-01T12:00:00.000Z"
        )
        core_definition.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_core_definition():

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
    create_res = client.create_core_definition(
        InitialVersion=initial_version, Name=core_name
    )
    core_def_id = create_res["Id"]
    arn = create_res["Arn"]
    latest_version = create_res["LatestVersion"]
    latest_version_arn = create_res["LatestVersionArn"]

    get_res = client.get_core_definition(CoreDefinitionId=core_def_id)

    get_res.should.have.key("Name").equals(core_name)
    get_res.should.have.key("Arn").equals(arn)
    get_res.should.have.key("Id").equals(core_def_id)
    get_res.should.have.key("LatestVersion").equals(latest_version)
    get_res.should.have.key("LatestVersionArn").equals(latest_version_arn)

    if not TEST_SERVER_MODE:
        get_res.should.have.key("CreationTimestamp").equal("2022-06-01T12:00:00.000Z")
        get_res.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@mock_greengrass
def test_delete_core_definition():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123456789",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
        }
    ]

    initial_version = {"Cores": cores}

    create_res = client.create_core_definition(
        InitialVersion=initial_version, Name="TestCore"
    )
    core_def_id = create_res["Id"]

    client.get_core_definition(CoreDefinitionId=core_def_id)
    client.delete_core_definition(CoreDefinitionId=core_def_id)
    with pytest.raises(ClientError) as ex:
        client.delete_core_definition(CoreDefinitionId=core_def_id)
    ex.value.response["Error"]["Message"].should.equal(
        "That cores definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_update_core_definition():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123456789",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
        }
    ]

    initial_version = {"Cores": cores}
    create_res = client.create_core_definition(
        InitialVersion=initial_version, Name="TestCore"
    )
    core_def_id = create_res["Id"]
    updated_core_name = "UpdatedCore"
    client.update_core_definition(CoreDefinitionId=core_def_id, Name="UpdatedCore")
    get_res = client.get_core_definition(CoreDefinitionId=core_def_id)
    get_res.should.have.key("Name").equals(updated_core_name)


@mock_greengrass
def test_update_core_definition_with_empty_name():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123456789",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
        }
    ]

    initial_version = {"Cores": cores}
    create_res = client.create_core_definition(
        InitialVersion=initial_version, Name="TestCore"
    )
    core_def_id = create_res["Id"]

    with pytest.raises(ClientError) as ex:
        client.update_core_definition(CoreDefinitionId=core_def_id, Name="")
    ex.value.response["Error"]["Message"].should.equal(
        "Input does not contain any attributes to be updated"
    )
    ex.value.response["Error"]["Code"].should.equal(
        "InvalidContainerDefinitionException"
    )


@mock_greengrass
def test_update_core_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.update_core_definition(
            CoreDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="abc"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That cores definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


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
