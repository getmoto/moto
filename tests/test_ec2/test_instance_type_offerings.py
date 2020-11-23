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
    offerings = client.describe_instance_type_offerings(
        Filters=[{"Name": "instance-type", "Values": ["t2.nano"]}])

    offerings.should.have.key("InstanceTypeOfferings")
    offerings["InstanceTypeOfferings"].should_not.be.empty
    offerings["InstanceTypeOfferings"].should.have.length_of(2)
    offerings["InstanceTypeOfferings"][0]['InstanceType'].should.equal('t2.nano')
    offerings["InstanceTypeOfferings"][-1]['InstanceType'].should.equal('t2.nano')
    offerings["InstanceTypeOfferings"][0]['Location'].should.equal('us-east-1a')


@mock_ec2
def test_describe_instance_type_offering_filter_by_zone():
    client = boto3.client("ec2", "us-east-1")
    offerings = client.describe_instance_type_offerings(
        Filters=[{"Name": "location", "Values": ["us-east-1c"]}])

    offerings.should.have.key("InstanceTypeOfferings")
    offerings["InstanceTypeOfferings"].should_not.be.empty
    offerings["InstanceTypeOfferings"].should.have.length_of(1)
    offerings["InstanceTypeOfferings"][0]['InstanceType'].should.equal('a1.2xlarge')
    offerings["InstanceTypeOfferings"][0]['Location'].should.equal('us-east-1c')


@mock_ec2
def test_describe_instance_type_offering_filter_by_region():
    client = boto3.client("ec2", "us-east-1")
    offerings = client.describe_instance_type_offerings(
        LocationType="region", Filters=[{"Name": "location", "Values": ["us-west-1"]}])

    offerings.should.have.key("InstanceTypeOfferings")
    offerings["InstanceTypeOfferings"].should_not.be.empty
    offerings["InstanceTypeOfferings"].should.have.length_of(2)
    offerings["InstanceTypeOfferings"][0]['InstanceType'].should.equal('a1.4xlarge')
    offerings["InstanceTypeOfferings"][0]['Location'].should.equal('us-west-1a')
