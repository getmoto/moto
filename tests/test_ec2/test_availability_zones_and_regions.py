from __future__ import unicode_literals
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_describe_regions():
    conn = boto.connect_ec2('the_key', 'the_secret')
    regions = conn.get_all_regions()
    regions.should.have.length_of(8)
    regions[0].name.should.equal('eu-west-1')
    regions[0].endpoint.should.equal('ec2.eu-west-1.amazonaws.com')


@mock_ec2
def test_availability_zones():
    # Just testing us-east-1 for now
    conn = boto.connect_ec2('the_key', 'the_secret')
    zones = conn.get_all_zones()
    zones.should.have.length_of(5)
    zones[0].name.should.equal('us-east-1a')
    zones[0].region_name.should.equal('us-east-1')
