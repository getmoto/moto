import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_boto3_describe_regions():
    ec2 = boto3.client("ec2", "us-east-1")
    resp = ec2.describe_regions()
    assert len(resp["Regions"]) > 1
    for rec in resp["Regions"]:
        assert rec["RegionName"] in rec["Endpoint"]

    test_region = "us-east-1"
    resp = ec2.describe_regions(RegionNames=[test_region])
    assert len(resp["Regions"]) == 1
    assert resp["Regions"][0]["RegionName"] == test_region
    assert resp["Regions"][0]["OptInStatus"] == "opt-in-not-required"

    test_region = "ap-east-1"
    resp = ec2.describe_regions(RegionNames=[test_region])
    assert len(resp["Regions"]) == 1
    assert resp["Regions"][0]["RegionName"] == test_region
    assert resp["Regions"][0]["OptInStatus"] == "not-opted-in"


@mock_aws
def test_boto3_availability_zones():
    ec2 = boto3.client("ec2", "us-east-1")
    resp = ec2.describe_regions()
    regions = [r["RegionName"] for r in resp["Regions"]]
    for region in regions:
        conn = boto3.client("ec2", region)
        resp = conn.describe_availability_zones()
        for rec in resp["AvailabilityZones"]:
            assert region in rec["ZoneName"]


@mock_aws
def test_availability_zones__parameters():
    us_east = boto3.client("ec2", "us-east-1")
    zones = us_east.describe_availability_zones(ZoneNames=["us-east-1b"])[
        "AvailabilityZones"
    ]
    assert len(zones) == 1
    assert zones[0]["ZoneId"] == "use1-az1"

    zones = us_east.describe_availability_zones(ZoneNames=["us-east-1a", "us-east-1b"])[
        "AvailabilityZones"
    ]
    assert len(zones) == 2
    assert set([zone["ZoneId"] for zone in zones]) == {"use1-az1", "use1-az6"}

    zones = us_east.describe_availability_zones(ZoneIds=["use1-az1"])[
        "AvailabilityZones"
    ]
    assert len(zones) == 1
    assert zones[0]["ZoneId"] == "use1-az1"

    zones = us_east.describe_availability_zones(
        Filters=[{"Name": "state", "Values": ["unavailable"]}]
    )["AvailabilityZones"]
    assert zones == []

    zones = us_east.describe_availability_zones(
        Filters=[{"Name": "zone-id", "Values": ["use1-az2"]}]
    )["AvailabilityZones"]
    assert len(zones) == 1
    assert zones[0]["ZoneId"] == "use1-az2"

    zones = us_east.describe_availability_zones(
        Filters=[{"Name": "zone-name", "Values": ["us-east-1b"]}]
    )["AvailabilityZones"]
    assert len(zones) == 1
    assert zones[0]["ZoneId"] == "use1-az1"


@mock_aws
def test_describe_availability_zones_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_availability_zones(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DescribeAvailabilityZones operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_aws
def test_boto3_zoneId_in_availability_zones():
    conn = boto3.client("ec2", "us-east-1")
    resp = conn.describe_availability_zones()
    for rec in resp["AvailabilityZones"]:
        assert "use1" in rec.get("ZoneId")
    conn = boto3.client("ec2", "us-west-1")
    resp = conn.describe_availability_zones()
    for rec in resp["AvailabilityZones"]:
        assert "usw1" in rec.get("ZoneId")
