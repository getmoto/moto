import boto3
import freezegun
import pytest
from botocore.client import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.settings import TEST_SERVER_MODE


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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
    assert "Arn" in res
    assert "Id" in res
    if not TEST_SERVER_MODE:
        assert res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert res["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"
    assert "LatestVersionArn" in res
    assert res["Name"] == core_name
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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
    assert "Definitions" in res
    core_definition = res["Definitions"][0]

    assert core_definition["Name"] == core_name
    assert "Arn" in core_definition
    assert "Id" in core_definition
    assert "LatestVersion" in core_definition
    assert "LatestVersionArn" in core_definition
    if not TEST_SERVER_MODE:
        assert core_definition["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert core_definition["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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

    assert get_res["Name"] == core_name
    assert get_res["Arn"] == arn
    assert get_res["Id"] == core_def_id
    assert get_res["LatestVersion"] == latest_version
    assert get_res["LatestVersionArn"] == latest_version_arn

    if not TEST_SERVER_MODE:
        assert get_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert get_res["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


@mock_aws
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
    err = ex.value.response["Error"]
    assert err["Message"] == "That cores definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@mock_aws
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
    assert get_res["Name"] == updated_core_name


@mock_aws
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
    err = ex.value.response["Error"]
    assert err["Message"] == "Input does not contain any attributes to be updated"
    assert err["Code"] == "InvalidContainerDefinitionException"


@mock_aws
def test_update_core_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.update_core_definition(
            CoreDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="abc"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That cores definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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
    assert "Arn" in core_def_ver_res
    assert "CreationTimestamp" in core_def_ver_res
    if not TEST_SERVER_MODE:
        assert core_def_ver_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
    assert core_def_ver_res["Id"] == core_def_id
    assert "Version" in core_def_ver_res


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
def test_get_core_definition_version():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    initial_version = {
        "Cores": [
            {
                "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                "Id": "123456789",
                "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
            }
        ]
    }

    core_def_res = client.create_core_definition(
        InitialVersion=initial_version, Name="TestCore"
    )
    core_def_id = core_def_res["Id"]
    core_def_ver_id = core_def_res["LatestVersion"]

    core_def_ver_res = client.get_core_definition_version(
        CoreDefinitionId=core_def_id, CoreDefinitionVersionId=core_def_ver_id
    )

    assert "Arn" in core_def_ver_res
    assert "CreationTimestamp" in core_def_ver_res
    assert core_def_ver_res["Definition"] == initial_version
    if not TEST_SERVER_MODE:
        assert core_def_ver_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
    assert core_def_ver_res["Id"] == core_def_id
    assert "Version" in core_def_ver_res


@mock_aws
def test_get_core_definition_version_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.get_core_definition_version(
            CoreDefinitionId="fe2392e9-e67f-4308-af1b-ff94a128b231",
            CoreDefinitionVersionId="cd2ea6dc-6634-4e89-8441-8003500435f9",
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That cores definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@mock_aws
def test_get_core_definition_version_with_invalid_version_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    core_def_res = client.create_core_definition(
        Name="TestCore",
        InitialVersion={
            "Cores": [
                {
                    "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                    "Id": "123456789",
                    "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
                }
            ]
        },
    )
    core_def_id = core_def_res["Id"]
    invalid_version_id = "cd2ea6dc-6634-4e89-8441-8003500435f9"
    with pytest.raises(ClientError) as ex:
        client.get_core_definition_version(
            CoreDefinitionId=core_def_id, CoreDefinitionVersionId=invalid_version_id
        )
    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == f"Version {invalid_version_id} of Core List Definition {core_def_id} does not exist."
    )
    assert err["Code"] == "VersionNotFoundException"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
def test_list_core_definition_version():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    initial_version = {
        "Cores": [
            {
                "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                "Id": "123456789",
                "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/v1Thing",
            }
        ]
    }

    core_def_res = client.create_core_definition(
        InitialVersion=initial_version, Name="TestCore"
    )
    core_def_id = core_def_res["Id"]
    core_def_vers_res = client.list_core_definition_versions(
        CoreDefinitionId=core_def_id
    )

    assert "Versions" in core_def_vers_res
    core_def_ver = core_def_vers_res["Versions"][0]
    assert "Arn" in core_def_ver
    assert "CreationTimestamp" in core_def_ver

    if not TEST_SERVER_MODE:
        assert core_def_ver["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
    assert core_def_ver["Id"] == core_def_id
    assert "Version" in core_def_ver


@mock_aws
def test_list_core_definition_version_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.list_core_definition_versions(
            CoreDefinitionId="cd2ea6dc-6634-4e89-8441-8003500435f9"
        )

    err = ex.value.response["Error"]
    assert err["Message"] == "That cores definition does not exist."
    assert err["Code"] == "IdNotFoundException"
