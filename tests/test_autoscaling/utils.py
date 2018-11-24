import boto
import boto3
from boto import vpc as boto_vpc
from moto import mock_ec2, mock_ec2_deprecated


@mock_ec2
def setup_networking():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    vpc = ec2.create_vpc(CidrBlock='10.11.0.0/16')
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id,
        CidrBlock='10.11.1.0/24',
        AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id,
        CidrBlock='10.11.2.0/24',
        AvailabilityZone='us-east-1b')
    return {'vpc': vpc.id, 'subnet1': subnet1.id, 'subnet2': subnet2.id}

@mock_ec2_deprecated
def setup_networking_deprecated():
    conn = boto_vpc.connect_to_region('us-east-1')
    vpc = conn.create_vpc("10.11.0.0/16")
    subnet1 = conn.create_subnet(
        vpc.id,
        "10.11.1.0/24",
        availability_zone='us-east-1a')
    subnet2 = conn.create_subnet(
        vpc.id,
        "10.11.2.0/24",
        availability_zone='us-east-1b')
    return {'vpc': vpc.id, 'subnet1': subnet1.id, 'subnet2': subnet2.id}
