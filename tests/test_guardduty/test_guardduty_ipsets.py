import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_ip_set():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    resp = client.create_ip_set(
        DetectorId=detector_id,
        Name="my first ipset",
        Format="TXT",
        Location="s3://bucket/threats.txt",
        Activate=True,
    )
    assert resp["IpSetId"]


@mock_aws
def test_get_ip_set():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    ip_set_id = client.create_ip_set(
        DetectorId=detector_id,
        Name="my first ipset",
        Format="TXT",
        Location="s3://bucket/threats.txt",
        Activate=True,
        Tags={"key": "value"},
    )["IpSetId"]

    resp = client.get_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
    assert resp["Name"] == "my first ipset"
    assert resp["Format"] == "TXT"
    assert resp["Location"] == "s3://bucket/threats.txt"
    assert resp["Status"] == "ACTIVE"
    assert resp["Tags"] == {"key": "value"}


@mock_aws
def test_get_ip_set__not_activated():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    ip_set_id = client.create_ip_set(
        DetectorId=detector_id,
        Name="my first ipset",
        Format="TXT",
        Location="s3://bucket/threats.txt",
        Activate=False,
    )["IpSetId"]

    resp = client.get_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
    assert resp["Status"] == "INACTIVE"
    assert resp["Tags"] == {}


@mock_aws
def test_get_ip_set__with_expected_bucket_owner():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    ip_set_id = client.create_ip_set(
        DetectorId=detector_id,
        Name="my first ipset",
        Format="TXT",
        Location="s3://bucket/threats.txt",
        Activate=True,
        ExpectedBucketOwner="123456789012",
    )["IpSetId"]

    resp = client.get_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
    assert resp["ExpectedBucketOwner"] == "123456789012"


@mock_aws
def test_list_ip_sets():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    assert client.list_ip_sets(DetectorId=detector_id)["IpSetIds"] == []

    first = client.create_ip_set(
        DetectorId=detector_id,
        Name="first",
        Format="TXT",
        Location="s3://bucket/first.txt",
        Activate=True,
    )["IpSetId"]
    second = client.create_ip_set(
        DetectorId=detector_id,
        Name="second",
        Format="STIX",
        Location="s3://bucket/second.xml",
        Activate=False,
    )["IpSetId"]

    ip_set_ids = client.list_ip_sets(DetectorId=detector_id)["IpSetIds"]
    assert sorted(ip_set_ids) == sorted([first, second])


@mock_aws
def test_update_ip_set():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    ip_set_id = client.create_ip_set(
        DetectorId=detector_id,
        Name="my first ipset",
        Format="TXT",
        Location="s3://bucket/threats.txt",
        Activate=True,
    )["IpSetId"]

    client.update_ip_set(
        DetectorId=detector_id,
        IpSetId=ip_set_id,
        Name="renamed",
        Location="s3://bucket/other.txt",
        Activate=False,
    )

    resp = client.get_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
    assert resp["Name"] == "renamed"
    assert resp["Location"] == "s3://bucket/other.txt"
    assert resp["Status"] == "INACTIVE"
    assert resp["Format"] == "TXT"


@mock_aws
def test_update_ip_set__only_one_field():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    ip_set_id = client.create_ip_set(
        DetectorId=detector_id,
        Name="my first ipset",
        Format="TXT",
        Location="s3://bucket/threats.txt",
        Activate=True,
    )["IpSetId"]

    client.update_ip_set(DetectorId=detector_id, IpSetId=ip_set_id, Name="renamed")

    resp = client.get_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
    assert resp["Name"] == "renamed"
    assert resp["Location"] == "s3://bucket/threats.txt"
    assert resp["Status"] == "ACTIVE"


@mock_aws
def test_delete_ip_set():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    ip_set_id = client.create_ip_set(
        DetectorId=detector_id,
        Name="my first ipset",
        Format="TXT",
        Location="s3://bucket/threats.txt",
        Activate=True,
    )["IpSetId"]

    client.delete_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)

    assert client.list_ip_sets(DetectorId=detector_id)["IpSetIds"] == []

    with pytest.raises(ClientError) as exc:
        client.get_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"


@mock_aws
def test_get_ip_set__unknown_id():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    with pytest.raises(ClientError) as exc:
        client.get_ip_set(DetectorId=detector_id, IpSetId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"


@mock_aws
def test_ip_set_operations__unknown_detector():
    client = boto3.client("guardduty", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.list_ip_sets(DetectorId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"
