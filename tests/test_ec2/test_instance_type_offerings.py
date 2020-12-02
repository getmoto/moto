from __future__ import unicode_literals

import boto3
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_describe_instance_type_offerings():
    client = boto3.client("ec2", "us-east-1")
    offerings = client.describe_instance_type_offerings()

    offerings.should.have.key("InstanceTypeOfferings")
    offerings["InstanceTypeOfferings"].should_not.be.empty
    offerings["InstanceTypeOfferings"][0].should.have.key("InstanceType")
    offerings["InstanceTypeOfferings"][0].should.have.key("Location")
    offerings["InstanceTypeOfferings"][0].should.have.key("LocationType")


@mock_ec2
def test_describe_instance_type_offering_filter_by_type():
    client = boto3.client("ec2", "us-east-1")

    # Verify offerings of a specific instance type
    offerings = client.describe_instance_type_offerings(
        Filters=[{"Name": "instance-type", "Values": ["t2.nano"]}]
    )

    offerings.should.have.key("InstanceTypeOfferings")
    offerings["InstanceTypeOfferings"].should_not.be.empty
    offerings = offerings["InstanceTypeOfferings"]
    offerings.should.have.length_of(1)
    offerings[0]["InstanceType"].should.equal("t2.nano")
    offerings[0]["Location"].should.equal("us-east-1")

    # Verify offerings of that instance type per availibility zone
    offerings = client.describe_instance_type_offerings(
        LocationType="availability-zone",
        Filters=[{"Name": "instance-type", "Values": ["t2.nano"]}],
    )
    offerings.should.have.key("InstanceTypeOfferings")
    offerings = offerings["InstanceTypeOfferings"]
    offerings.should.have.length_of(6)
    for offering in offerings:
        offering["InstanceType"].should.equal("t2.nano")
        offering["LocationType"].should.equal("availability-zone")
        offering["Location"].should.match("us-east-1[a-f]")


@mock_ec2
def test_describe_instance_type_offering_filter_by_zone():
    client = boto3.client("ec2", "us-east-1")
    offerings = client.describe_instance_type_offerings(
        LocationType="availability-zone",
        Filters=[{"Name": "location", "Values": ["us-east-1c"]}],
    )

    offerings.should.have.key("InstanceTypeOfferings")
    offerings = offerings["InstanceTypeOfferings"]
    offerings.should_not.be.empty
    offerings.should.have.length_of(353)
    assert all([o["LocationType"] == "availability-zone" for o in offerings])
    assert all([o["Location"] == "us-east-1c" for o in offerings])
    assert any([o["InstanceType"] == "a1.2xlarge" for o in offerings])


@mock_ec2
def test_describe_instance_type_offering_filter_by_zone_id():
    client = boto3.client("ec2", "ca-central-1")
    offerings = client.describe_instance_type_offerings(
        LocationType="availability-zone-id",
        Filters=[
            {"Name": "location", "Values": ["cac1-az1"]},
            {"Name": "instance-type", "Values": ["c5.9xlarge"]},
        ],
    )

    offerings.should.have.key("InstanceTypeOfferings")
    offerings = offerings["InstanceTypeOfferings"]
    offerings.should_not.be.empty
    offerings.should.have.length_of(1)
    offerings[0]["LocationType"].should.equal("availability-zone-id")
    offerings[0]["InstanceType"].should.equal("c5.9xlarge")
    offerings[0]["Location"].should.equal("cac1-az1")
