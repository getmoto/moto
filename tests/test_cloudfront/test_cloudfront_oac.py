import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_cloudfront


@mock_cloudfront
def test_create_origin_access_control():
    cf = boto3.client("cloudfront", "us-east-1")

    oac_list = cf.list_origin_access_controls()["OriginAccessControlList"]
    assert oac_list["Items"] == []

    oac_input = {
        "Name": "my_oac",
        "SigningProtocol": "sigv4",
        "SigningBehavior": "always",
        "OriginAccessControlOriginType": "s3",
    }
    resp = cf.create_origin_access_control(OriginAccessControlConfig=oac_input)[
        "OriginAccessControl"
    ]
    control_id = resp.pop("Id")

    assert control_id is not None
    assert resp["OriginAccessControlConfig"] == oac_input

    resp = cf.get_origin_access_control(Id=control_id)["OriginAccessControl"]
    assert resp.pop("Id") is not None
    assert resp["OriginAccessControlConfig"] == oac_input

    oac_list = cf.list_origin_access_controls()["OriginAccessControlList"]
    assert oac_list["Items"][0].pop("Id") == control_id
    assert oac_list["Items"][0] == oac_input

    cf.delete_origin_access_control(Id=control_id)

    oac_list = cf.list_origin_access_controls()["OriginAccessControlList"]
    assert oac_list["Items"] == []

    with pytest.raises(ClientError) as exc:
        cf.get_origin_access_control(Id=control_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchOriginAccessControl"
    assert err["Message"] == "The specified origin access control does not exist."


@mock_cloudfront
def test_update_origin_access_control():
    # http://localhost:5000/2020-05-31/origin-access-control/DE53MREVCPIFL/config
    cf = boto3.client("cloudfront", "us-east-1")
    oac_input = {
        "Name": "my_oac",
        "SigningProtocol": "sigv4",
        "SigningBehavior": "always",
        "OriginAccessControlOriginType": "s3",
    }
    resp = cf.create_origin_access_control(OriginAccessControlConfig=oac_input)[
        "OriginAccessControl"
    ]
    control_id = resp.pop("Id")

    oac_input["Description"] = "updated"
    control = cf.update_origin_access_control(
        Id=control_id, OriginAccessControlConfig=oac_input
    )["OriginAccessControl"]
    assert control["Id"] == control_id
    assert control["OriginAccessControlConfig"] == oac_input
