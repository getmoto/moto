import re
from uuid import uuid4

import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws
from tests.test_s3 import s3_aws_verified


@mock_aws
def test_get_unknown_access_point():
    client = boto3.client("s3control", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_access_point(AccountId="111111111111", Name="ap_name")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchAccessPoint"
    assert err["Message"] == "The specified accesspoint does not exist"
    assert err["AccessPointName"] == "ap_name"


@mock_aws
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


@mock_aws
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


@mock_aws
def test_list_access_points():
    region = "us-east-1"
    account_id = "111111111111"
    client = boto3.client("s3control", region_name=region)
    s3_client = boto3.client("s3", region_name=region)

    resp = client.list_access_points(AccountId=account_id)
    assert not resp.get("AccessPointList")

    s3_client.create_bucket(Bucket="bucket-a")
    s3_client.create_bucket(Bucket="bucket-b")
    client.create_access_point(AccountId=account_id, Name="ap1-a", Bucket="bucket-a")
    client.create_access_point(AccountId=account_id, Name="ap2-a", Bucket="bucket-a")
    client.create_access_point(AccountId=account_id, Name="ap3-b", Bucket="bucket-b")

    resp = client.list_access_points(AccountId=account_id)
    assert len(resp["AccessPointList"]) == 3

    resp = client.list_access_points(AccountId=account_id, Bucket="bucket-a")
    aps = resp["AccessPointList"]
    assert len(aps) == 2
    assert {ap["Name"] for ap in aps} == {"ap1-a", "ap2-a"}

    resp = client.list_access_points(AccountId=account_id, MaxResults=2)
    assert len(resp["AccessPointList"]) == 2
    assert "NextToken" in resp

    next_token = resp["NextToken"]
    resp2 = client.list_access_points(AccountId=account_id, NextToken=next_token)
    assert len(resp2["AccessPointList"]) == 1
    assert "NextToken" not in resp2


@pytest.mark.aws_verified
@s3_aws_verified
def test_delete_access_point(bucket_name=None):
    sts = boto3.client("sts", "us-east-1")
    account_id = sts.get_caller_identity()["Account"]

    client = boto3.client("s3control", region_name="us-east-1")
    ap_name = "ap-" + str(uuid4())[0:6]
    expected_arn = f"arn:aws:s3:us-east-1:{account_id}:accesspoint/{ap_name}"

    create = client.create_access_point(
        AccountId=account_id, Name=ap_name, Bucket=bucket_name
    )
    assert create["Alias"].startswith(ap_name)
    assert create["Alias"].endswith("-s3alias")
    assert create["AccessPointArn"] == expected_arn

    get = client.get_access_point(AccountId=account_id, Name=ap_name)
    assert get["Alias"] == create["Alias"]
    assert get["AccessPointArn"] == expected_arn

    client.delete_access_point(AccountId=account_id, Name=ap_name)

    with pytest.raises(ClientError) as exc:
        client.get_access_point(AccountId=account_id, Name=ap_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchAccessPoint"
    assert err["Message"] == "The specified accesspoint does not exist"
