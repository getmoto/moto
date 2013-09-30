import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_vpcs():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    vpc.cidr_block.should.equal('10.0.0.0/16')

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(1)

    vpc.delete()

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(0)

    conn.delete_vpc.when.called_with(
        "vpc-1234abcd").should.throw(EC2ResponseError)
