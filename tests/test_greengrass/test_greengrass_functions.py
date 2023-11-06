import boto3
import freezegun
import pytest
from botocore.client import ClientError

from moto import mock_aws
from moto.settings import TEST_SERVER_MODE


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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
    assert "Arn" in res
    assert "Id" in res
    assert "LatestVersion" in res
    assert "LatestVersionArn" in res
    assert res["Name"] == func_name
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201

    if not TEST_SERVER_MODE:
        assert res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert res["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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

    assert func_def["Name"] == func_name
    assert "Arn" in func_def
    assert "Id" in func_def
    assert "LatestVersion" in func_def
    assert "LatestVersionArn" in func_def
    if not TEST_SERVER_MODE:
        assert func_def["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert func_def["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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

    assert get_res["Name"] == func_name
    assert get_res["Arn"] == arn
    assert get_res["Id"] == func_def_id
    assert get_res["LatestVersion"] == latest_version
    assert get_res["LatestVersionArn"] == latest_version_arn
    assert get_res["ResponseMetadata"]["HTTPStatusCode"] == 200

    if not TEST_SERVER_MODE:
        assert get_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert get_res["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


@mock_aws
def test_get_function_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_function_definition(
            FunctionDefinitionId="b552443b-1888-469b-81f8-0ebc5ca92949"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That Lambda List Definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@mock_aws
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
    assert del_res["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_delete_function_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.delete_function_definition(
            FunctionDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That lambdas definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@mock_aws
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
    assert update_res["ResponseMetadata"]["HTTPStatusCode"] == 200

    get_res = client.get_function_definition(FunctionDefinitionId=func_def_id)
    assert get_res["Name"] == updated_func_name


@mock_aws
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
    err = ex.value.response["Error"]
    assert err["Message"] == "Input does not contain any attributes to be updated"
    assert err["Code"] == "InvalidContainerDefinitionException"


@mock_aws
def test_update_function_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.update_function_definition(
            FunctionDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="123"
        )
    rr = ex.value.response["Error"]
    assert rr["Message"] == "That lambdas definition does not exist."
    assert rr["Code"] == "IdNotFoundException"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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
    assert "Arn" in func_def_ver_res
    assert "CreationTimestamp" in func_def_ver_res
    assert func_def_ver_res["Id"] == func_def_id
    assert "Version" in func_def_ver_res

    if not TEST_SERVER_MODE:
        assert func_def_ver_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"


@mock_aws
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
    err = ex.value.response["Error"]
    assert err["Message"] == "That lambdas does not exist."
    assert err["Code"] == "IdNotFoundException"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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

    assert "Versions" in func_def_vers_res
    device_def_ver = func_def_vers_res["Versions"][0]
    assert "Arn" in device_def_ver
    assert "CreationTimestamp" in device_def_ver

    if not TEST_SERVER_MODE:
        assert device_def_ver["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
    assert device_def_ver["Id"] == func_def_id
    assert "Version" in device_def_ver


@mock_aws
def test_list_function_definition_versions_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.list_function_definition_versions(
            FunctionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That lambdas definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_aws
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

    assert "Arn" in func_def_ver_res
    assert "CreationTimestamp" in func_def_ver_res
    assert func_def_ver_res["Definition"] == initial_version
    assert func_def_ver_res["Id"] == func_def_id
    assert "Version" in func_def_ver_res

    if not TEST_SERVER_MODE:
        assert func_def_ver_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"


@mock_aws
def test_get_function_definition_version_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.get_function_definition_version(
            FunctionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
            FunctionDefinitionVersionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That lambdas definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@mock_aws
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
    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == f"Version {invalid_func_def_ver_id} of Lambda List Definition {func_def_id} does not exist."
    )
    assert err["Code"] == "IdNotFoundException"
