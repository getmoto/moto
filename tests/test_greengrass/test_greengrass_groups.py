import boto3
import freezegun

from moto import mock_greengrass
from moto.core import get_account_id
from moto.settings import TEST_SERVER_MODE

ACCOUNT_ID = get_account_id()


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_group():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_core_ver = {
        "Cores": [
            {
                "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                "Id": "123456789",
                "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
            }
        ]
    }

    create_core_def_res = client.create_core_definition(
        InitialVersion=init_core_ver, Name="TestCore"
    )
    core_def_ver_arn = create_core_def_res["LatestVersionArn"]

    init_grp = {"CoreDefinitionVersionArn": core_def_ver_arn}

    grp_name = "TestGroup"
    create_grp_res = client.create_group(Name=grp_name, InitialVersion=init_grp)
    create_grp_res.should.have.key("Arn")
    create_grp_res.should.have.key("Id")
    create_grp_res.should.have.key("LastUpdatedTimestamp")
    create_grp_res.should.have.key("LatestVersion")
    create_grp_res.should.have.key("LatestVersionArn")
    create_grp_res.should.have.key("Name").equals(grp_name)
    create_grp_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)

    if not TEST_SERVER_MODE:
        create_grp_res.should.have.key("CreationTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )
        create_grp_res.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )
