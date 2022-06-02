import boto3
import freezegun

from moto import mock_greengrass
from moto.core import get_account_id

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
    res.should.have.key("CreationTimestamp").equals("2022-06-01T12:00:00.000Z")
    res.should.have.key("Id")
    res.should.have.key("LastUpdatedTimestamp").equals("2022-06-01T12:00:00.000Z")
    res.should.have.key("LatestVersionArn")
    res.should.have.key("Name").equals(core_name)
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)
