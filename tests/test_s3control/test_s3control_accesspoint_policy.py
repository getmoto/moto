import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws


@mock_aws
def test_get_access_point_policy():
    client = boto3.client("s3control", region_name="us-west-2")
    client.create_access_point(
        AccountId="111111111111", Name="ap_name", Bucket="mybucket"
    )

    policy = """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": "s3:GetObjectTagging",
      "Resource": "arn:aws:s3:us-east-1:123456789012:accesspoint/mybucket/object/*",
      "Principal": {
        "AWS": "*"
      }
    }
  ]
}"""
    client.put_access_point_policy(
        AccountId="111111111111", Name="ap_name", Policy=policy
    )

    resp = client.get_access_point_policy(AccountId="111111111111", Name="ap_name")
    assert "Policy" in resp
    assert resp["Policy"] == policy


@mock_aws
def test_get_unknown_access_point_policy():
    client = boto3.client("s3control", region_name="ap-southeast-1")
    client.create_access_point(
        AccountId="111111111111", Name="ap_name", Bucket="mybucket"
    )

    with pytest.raises(ClientError) as exc:
        client.get_access_point_policy(AccountId="111111111111", Name="ap_name")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchAccessPointPolicy"
    assert err["Message"] == "The specified accesspoint policy does not exist"
    assert err["AccessPointName"] == "ap_name"


@mock_aws
def test_get_access_point_policy_status():
    client = boto3.client("s3control", region_name="us-west-2")
    client.create_access_point(
        AccountId="111111111111", Name="ap_name", Bucket="mybucket"
    )

    policy = """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": "s3:GetObjectTagging",
      "Resource": "arn:aws:s3:us-east-1:123456789012:accesspoint/mybucket/object/*",
      "Principal": {
        "AWS": "*"
      }
    }
  ]
}"""
    client.put_access_point_policy(
        AccountId="111111111111", Name="ap_name", Policy=policy
    )

    resp = client.get_access_point_policy_status(
        AccountId="111111111111", Name="ap_name"
    )
    assert "PolicyStatus" in resp
    assert resp["PolicyStatus"] == {"IsPublic": True}


@mock_aws
def test_delete_access_point_policy():
    client = boto3.client("s3control", region_name="us-west-2")
    client.create_access_point(
        AccountId="111111111111", Name="ap_name", Bucket="mybucket"
    )

    policy = """some json policy"""
    client.put_access_point_policy(
        AccountId="111111111111", Name="ap_name", Policy=policy
    )

    client.delete_access_point_policy(AccountId="111111111111", Name="ap_name")

    with pytest.raises(ClientError) as exc:
        client.get_access_point_policy(AccountId="111111111111", Name="ap_name")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchAccessPointPolicy"


@mock_aws
def test_get_unknown_access_point_policy_status():
    client = boto3.client("s3control", region_name="ap-southeast-1")
    client.create_access_point(
        AccountId="111111111111", Name="ap_name", Bucket="mybucket"
    )

    with pytest.raises(ClientError) as exc:
        client.get_access_point_policy_status(AccountId="111111111111", Name="ap_name")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchAccessPointPolicy"
    assert err["Message"] == "The specified accesspoint policy does not exist"
    assert err["AccessPointName"] == "ap_name"
