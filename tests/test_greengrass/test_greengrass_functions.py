import boto3
from botocore.client import ClientError
import freezegun
import pytest


from moto import mock_greengrass
from moto.settings import TEST_SERVER_MODE


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_function_definition():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Functions": [
            {
                "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
                "Id": "1234567890",
                "FunctionConfiguration": {
                    "MemorySize": 16384,
                    "EncodingType": "binary",
                    "Pinned": True,
                    "Timeout": 3,
                },
            }
        ]
    }
    func_name = "TestFunc"
    res = client.create_function_definition(InitialVersion=init_ver, Name=func_name)
    res.should.have.key("Arn")
    res.should.have.key("Id")
    res.should.have.key("LatestVersion")
    res.should.have.key("LatestVersionArn")
    res.should.have.key("Name").equals(func_name)
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)

    if not TEST_SERVER_MODE:
        res.should.have.key("CreationTimestamp").equals("2022-06-01T12:00:00.000Z")
        res.should.have.key("LastUpdatedTimestamp").equals("2022-06-01T12:00:00.000Z")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_function_definitions():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Functions": [
            {
                "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
                "Id": "1234567890",
                "FunctionConfiguration": {
                    "MemorySize": 16384,
                    "EncodingType": "binary",
                    "Pinned": True,
                    "Timeout": 3,
                },
            }
        ]
    }
    func_name = "TestFunc"
    client.create_function_definition(InitialVersion=init_ver, Name=func_name)

    res = client.list_function_definitions()
    func_def = res["Definitions"][0]

    func_def.should.have.key("Name").equals(func_name)
    func_def.should.have.key("Arn")
    func_def.should.have.key("Id")
    func_def.should.have.key("LatestVersion")
    func_def.should.have.key("LatestVersionArn")
    if not TEST_SERVER_MODE:
        func_def.should.have.key("CreationTimestamp").equal("2022-06-01T12:00:00.000Z")
        func_def.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_function_definition():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Functions": [
            {
                "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
                "Id": "1234567890",
                "FunctionConfiguration": {
                    "MemorySize": 16384,
                    "EncodingType": "binary",
                    "Pinned": True,
                    "Timeout": 3,
                },
            }
        ]
    }
    func_name = "TestFunc"
    create_res = client.create_function_definition(
        InitialVersion=init_ver, Name=func_name
    )

    func_def_id = create_res["Id"]
    arn = create_res["Arn"]
    latest_version = create_res["LatestVersion"]
    latest_version_arn = create_res["LatestVersionArn"]

    get_res = client.get_function_definition(FunctionDefinitionId=func_def_id)

    get_res.should.have.key("Name").equals(func_name)
    get_res.should.have.key("Arn").equals(arn)
    get_res.should.have.key("Id").equals(func_def_id)
    get_res.should.have.key("LatestVersion").equals(latest_version)
    get_res.should.have.key("LatestVersionArn").equals(latest_version_arn)
    get_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    if not TEST_SERVER_MODE:
        get_res.should.have.key("CreationTimestamp").equal("2022-06-01T12:00:00.000Z")
        get_res.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@mock_greengrass
def test_get_function_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_function_definition(
            FunctionDefinitionId="b552443b-1888-469b-81f8-0ebc5ca92949"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That Lambda List Definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_delete_function_definition():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Functions": [
            {
                "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
                "Id": "1234567890",
                "FunctionConfiguration": {
                    "MemorySize": 16384,
                    "EncodingType": "binary",
                    "Pinned": True,
                    "Timeout": 3,
                },
            }
        ]
    }
    create_res = client.create_function_definition(
        InitialVersion=init_ver, Name="TestFunc"
    )

    func_def_id = create_res["Id"]
    del_res = client.delete_function_definition(FunctionDefinitionId=func_def_id)
    del_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_greengrass
def test_delete_function_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.delete_function_definition(
            FunctionDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That lambdas definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_update_function_definition():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Functions": [
            {
                "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
                "Id": "1234567890",
                "FunctionConfiguration": {
                    "MemorySize": 16384,
                    "EncodingType": "binary",
                    "Pinned": True,
                    "Timeout": 3,
                },
            }
        ]
    }
    create_res = client.create_function_definition(
        InitialVersion=init_ver, Name="TestFunc"
    )

    func_def_id = create_res["Id"]
    updated_func_name = "UpdatedFunction"
    update_res = client.update_function_definition(
        FunctionDefinitionId=func_def_id, Name=updated_func_name
    )
    update_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    get_res = client.get_function_definition(FunctionDefinitionId=func_def_id)
    get_res.should.have.key("Name").equals(updated_func_name)


@mock_greengrass
def test_update_function_definition_with_empty_name():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Functions": [
            {
                "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
                "Id": "1234567890",
                "FunctionConfiguration": {
                    "MemorySize": 16384,
                    "EncodingType": "binary",
                    "Pinned": True,
                    "Timeout": 3,
                },
            }
        ]
    }
    create_res = client.create_function_definition(
        InitialVersion=init_ver, Name="TestFunc"
    )

    func_def_id = create_res["Id"]

    with pytest.raises(ClientError) as ex:
        client.update_function_definition(FunctionDefinitionId=func_def_id, Name="")
    ex.value.response["Error"]["Message"].should.equal(
        "Input does not contain any attributes to be updated"
    )
    ex.value.response["Error"]["Code"].should.equal(
        "InvalidContainerDefinitionException"
    )


@mock_greengrass
def test_update_function_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.update_function_definition(
            FunctionDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="123"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That lambdas definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_function_definition_version():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    v1_functions = [
        {
            "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
            "Id": "1234567890",
            "FunctionConfiguration": {
                "MemorySize": 16384,
                "EncodingType": "binary",
                "Pinned": True,
                "Timeout": 3,
            },
        }
    ]

    initial_version = {"Functions": v1_functions}
    func_def_res = client.create_function_definition(
        InitialVersion=initial_version, Name="TestFunction"
    )
    func_def_id = func_def_res["Id"]

    v2_functions = [
        {
            "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:2",
            "Id": "987654321",
            "FunctionConfiguration": {
                "MemorySize": 128,
                "EncodingType": "binary",
                "Pinned": False,
                "Timeout": 5,
            },
        }
    ]

    func_def_ver_res = client.create_function_definition_version(
        FunctionDefinitionId=func_def_id, Functions=v2_functions
    )
    func_def_ver_res.should.have.key("Arn")
    func_def_ver_res.should.have.key("CreationTimestamp")
    func_def_ver_res.should.have.key("Id").equals(func_def_id)
    func_def_ver_res.should.have.key("Version")

    if not TEST_SERVER_MODE:
        func_def_ver_res["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_create_function_definition_version_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    functions = [
        {
            "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
            "Id": "1234567890",
            "FunctionConfiguration": {
                "MemorySize": 16384,
                "EncodingType": "binary",
                "Pinned": True,
                "Timeout": 3,
            },
        }
    ]
    with pytest.raises(ClientError) as ex:
        client.create_function_definition_version(
            FunctionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
            Functions=functions,
        )
    ex.value.response["Error"]["Message"].should.equal("That lambdas does not exist.")
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_function_definition_versions():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    functions = [
        {
            "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
            "Id": "1234567890",
            "FunctionConfiguration": {
                "MemorySize": 16384,
                "EncodingType": "binary",
                "Pinned": True,
                "Timeout": 3,
            },
        }
    ]

    initial_version = {"Functions": functions}
    create_res = client.create_function_definition(
        InitialVersion=initial_version, Name="TestFunction"
    )
    func_def_id = create_res["Id"]

    func_def_vers_res = client.list_function_definition_versions(
        FunctionDefinitionId=func_def_id
    )

    func_def_vers_res.should.have.key("Versions")
    device_def_ver = func_def_vers_res["Versions"][0]
    device_def_ver.should.have.key("Arn")
    device_def_ver.should.have.key("CreationTimestamp")

    if not TEST_SERVER_MODE:
        device_def_ver["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")
    device_def_ver.should.have.key("Id").equals(func_def_id)
    device_def_ver.should.have.key("Version")


@mock_greengrass
def test_list_function_definition_versions_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.list_function_definition_versions(
            FunctionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That lambdas definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_function_definition_version():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    functions = [
        {
            "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
            "Id": "1234567890",
            "FunctionConfiguration": {
                "MemorySize": 16384,
                "EncodingType": "binary",
                "Pinned": True,
                "Timeout": 3,
            },
        }
    ]

    initial_version = {"Functions": functions}
    create_res = client.create_function_definition(
        InitialVersion=initial_version, Name="TestFunction"
    )

    func_def_id = create_res["Id"]
    func_def_ver_id = create_res["LatestVersion"]

    func_def_ver_res = client.get_function_definition_version(
        FunctionDefinitionId=func_def_id, FunctionDefinitionVersionId=func_def_ver_id
    )

    func_def_ver_res.should.have.key("Arn")
    func_def_ver_res.should.have.key("CreationTimestamp")
    func_def_ver_res.should.have.key("Definition").should.equal(initial_version)
    func_def_ver_res.should.have.key("Id").equals(func_def_id)
    func_def_ver_res.should.have.key("Version")

    if not TEST_SERVER_MODE:
        func_def_ver_res["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_get_function_definition_version_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.get_function_definition_version(
            FunctionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
            FunctionDefinitionVersionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That lambdas definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_get_function_definition_version_with_invalid_version_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    functions = [
        {
            "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
            "Id": "1234567890",
            "FunctionConfiguration": {
                "MemorySize": 16384,
                "EncodingType": "binary",
                "Pinned": True,
                "Timeout": 3,
            },
        }
    ]

    initial_version = {"Functions": functions}
    create_res = client.create_function_definition(
        InitialVersion=initial_version, Name="TestFunction"
    )

    func_def_id = create_res["Id"]
    invalid_func_def_ver_id = "7b0bdeae-54c7-47cf-9f93-561e672efd9c"

    with pytest.raises(ClientError) as ex:
        client.get_function_definition_version(
            FunctionDefinitionId=func_def_id,
            FunctionDefinitionVersionId=invalid_func_def_ver_id,
        )
    ex.value.response["Error"]["Message"].should.equal(
        f"Version {invalid_func_def_ver_id} of Lambda List Definition {func_def_id} does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")
