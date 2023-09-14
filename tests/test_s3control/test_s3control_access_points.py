import re

import boto3
import pytest

from botocore.client import ClientError
from moto import mock_s3control


@mock_s3control
def test_create_access_point():
    client = boto3.client("s3control", region_name="eu-west-1")
    resp = client.create_access_point(
        AccountId="111111111111", Name="ap_name", Bucket="mybucket"
    )

    assert "AccessPointArn" in resp
    assert resp["Alias"] == "ap_name"


@mock_s3control
def test_get_unknown_access_point():
    client = boto3.client("s3control", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_access_point(AccountId="111111111111", Name="ap_name")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchAccessPoint"
    assert err["Message"] == "The specified accesspoint does not exist"
    assert err["AccessPointName"] == "ap_name"


@mock_s3control
def test_get_access_point_minimal():
    client = boto3.client("s3control", region_name="ap-southeast-1")
    client.create_access_point(
        AccountId="111111111111", Name="ap_name", Bucket="mybucket"
    )

    resp = client.get_access_point(AccountId="111111111111", Name="ap_name")

    assert resp["Name"] == "ap_name"
    assert resp["Bucket"] == "mybucket"
    assert resp["NetworkOrigin"] == "Internet"
    assert resp["PublicAccessBlockConfiguration"] == {
        "BlockPublicAcls": True,
        "IgnorePublicAcls": True,
        "BlockPublicPolicy": True,
        "RestrictPublicBuckets": True,
    }
    assert "CreationDate" in resp
    assert "Alias" in resp
    assert re.match("ap_name-[a-z0-9]+-s3alias", resp["Alias"])
    assert resp["AccessPointArn"] == (
        "arn:aws:s3:us-east-1:111111111111:accesspoint/ap_name"
    )
    assert "Endpoints" in resp

    assert resp["Endpoints"]["ipv4"] == "s3-accesspoint.us-east-1.amazonaws.com"
    assert resp["Endpoints"]["fips"] == "s3-accesspoint-fips.us-east-1.amazonaws.com"
    assert resp["Endpoints"]["fips_dualstack"] == (
        "s3-accesspoint-fips.dualstack.us-east-1.amazonaws.com"
    )
    assert resp["Endpoints"]["dualstack"] == (
        "s3-accesspoint.dualstack.us-east-1.amazonaws.com"
    )


@mock_s3control
def test_get_access_point_full():
    client = boto3.client("s3control", region_name="ap-southeast-1")
    client.create_access_point(
        AccountId="111111111111",
        Name="ap_name",
        Bucket="mybucket",
        VpcConfiguration={"VpcId": "sth"},
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )

    resp = client.get_access_point(AccountId="111111111111", Name="ap_name")

    assert resp["Name"] == "ap_name"
    assert resp["Bucket"] == "mybucket"
    assert resp["NetworkOrigin"] == "VPC"
    assert resp["VpcConfiguration"] == {"VpcId": "sth"}
    assert resp["PublicAccessBlockConfiguration"] == {
        "BlockPublicAcls": False,
        "IgnorePublicAcls": False,
        "BlockPublicPolicy": False,
        "RestrictPublicBuckets": False,
    }


@mock_s3control
def test_delete_access_point():
    client = boto3.client("s3control", region_name="ap-southeast-1")

    client.create_access_point(
        AccountId="111111111111", Name="ap_name", Bucket="mybucket"
    )

    client.delete_access_point(AccountId="111111111111", Name="ap_name")

    with pytest.raises(ClientError) as exc:
        client.get_access_point(AccountId="111111111111", Name="ap_name")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchAccessPoint"
