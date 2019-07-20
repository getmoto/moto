from __future__ import unicode_literals
import boto
import boto.ec2
import boto3
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated


@mock_ec2_deprecated
def test_describe_regions():
    conn = boto.connect_ec2('the_key', 'the_secret')
    regions = conn.get_all_regions()
    regions.should.have.length_of(16)
    for region in regions:
        region.endpoint.should.contain(region.name)


@mock_ec2_deprecated
def test_availability_zones():
    conn = boto.connect_ec2('the_key', 'the_secret')
    regions = conn.get_all_regions()
    for region in regions:
        conn = boto.ec2.connect_to_region(region.name)
        if conn is None:
            continue
        for zone in conn.get_all_zones():
            zone.name.should.contain(region.name)


@mock_ec2
def test_boto3_describe_regions():
    ec2 = boto3.client('ec2', 'us-east-1')
    resp = ec2.describe_regions()
    resp['Regions'].should.have.length_of(16)
    for rec in resp['Regions']:
        rec['Endpoint'].should.contain(rec['RegionName'])

    test_region = 'us-east-1' 
    resp = ec2.describe_regions(RegionNames=[test_region])
    resp['Regions'].should.have.length_of(1)
    resp['Regions'][0].should.have.key('RegionName').which.should.equal(test_region)


@mock_ec2
def test_boto3_availability_zones():
    ec2 = boto3.client('ec2', 'us-east-1')
    resp = ec2.describe_regions()
    regions = [r['RegionName'] for r in resp['Regions']]
    for region in regions:
        conn = boto3.client('ec2', region)
        resp = conn.describe_availability_zones()
        for rec in resp['AvailabilityZones']:
            rec['ZoneName'].should.contain(region)
