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
