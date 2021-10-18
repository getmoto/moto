from __future__ import unicode_literals
import boto
import boto.ec2
import boto3
import pytest
import sure  # noqa

from botocore.exceptions import ClientError
from moto import mock_ec2, mock_ec2_deprecated


# Has boto3 equivalent
@mock_ec2_deprecated
def test_describe_regions():
    conn = boto.connect_ec2("the_key", "the_secret")
    regions = conn.get_all_regions()
    len(regions).should.be.greater_than(1)
    for region in regions:
        region.endpoint.should.contain(region.name)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_availability_zones():
    conn = boto.connect_ec2("the_key", "the_secret")
    regions = conn.get_all_regions()
    for region in regions:
        conn = boto.ec2.connect_to_region(region.name)
        if conn is None:
            continue
        for zone in conn.get_all_zones():
            zone.name.should.contain(region.name)


@mock_ec2
def test_boto3_describe_regions():
    ec2 = boto3.client("ec2", "us-east-1")
    resp = ec2.describe_regions()
    len(resp["Regions"]).should.be.greater_than(1)
    for rec in resp["Regions"]:
        rec["Endpoint"].should.contain(rec["RegionName"])

    test_region = "us-east-1"
    resp = ec2.describe_regions(RegionNames=[test_region])
    resp["Regions"].should.have.length_of(1)
    resp["Regions"][0].should.have.key("RegionName").which.should.equal(test_region)
    resp["Regions"][0].should.have.key("OptInStatus").which.should.equal(
        "opt-in-not-required"
    )

    test_region = "ap-east-1"
    resp = ec2.describe_regions(RegionNames=[test_region])
    resp["Regions"].should.have.length_of(1)
    resp["Regions"][0].should.have.key("RegionName").which.should.equal(test_region)
    resp["Regions"][0].should.have.key("OptInStatus").which.should.equal("not-opted-in")


@mock_ec2
def test_boto3_availability_zones():
    ec2 = boto3.client("ec2", "us-east-1")
    resp = ec2.describe_regions()
    regions = [r["RegionName"] for r in resp["Regions"]]
    for region in regions:
        conn = boto3.client("ec2", region)
        resp = conn.describe_availability_zones()
        for rec in resp["AvailabilityZones"]:
            rec["ZoneName"].should.contain(region)


@mock_ec2
def test_describe_availability_zones_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_availability_zones(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DescribeAvailabilityZones operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_boto3_zoneId_in_availability_zones():
    conn = boto3.client("ec2", "us-east-1")
    resp = conn.describe_availability_zones()
    for rec in resp["AvailabilityZones"]:
        rec.get("ZoneId").should.contain("use1")
    conn = boto3.client("ec2", "us-west-1")
    resp = conn.describe_availability_zones()
    for rec in resp["AvailabilityZones"]:
        rec.get("ZoneId").should.contain("usw1")
