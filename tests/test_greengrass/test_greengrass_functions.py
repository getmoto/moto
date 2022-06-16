import boto3
import freezegun

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
