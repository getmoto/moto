from __future__ import unicode_literals
import boto3
import sure  # noqa
from moto import mock_ec2


@mock_ec2
def test_describe_nat_gateways():
    conn = boto3.client('ec2', 'us-east-1')

    response = conn.describe_nat_gateways()

    response['NatGateways'].should.have.length_of(0)


@mock_ec2
def test_create_nat_gateway():
    conn = boto3.client('ec2', 'us-east-1')
    vpc = conn.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = conn.create_subnet(
        VpcId=vpc_id,
        CidrBlock='10.0.1.0/27',
        AvailabilityZone='us-east-1a',
    )
    allocation_id = conn.allocate_address(Domain='vpc')['AllocationId']
    subnet_id = subnet['Subnet']['SubnetId']

    response = conn.create_nat_gateway(
        SubnetId=subnet_id,
        AllocationId=allocation_id,
    )

    response['NatGateway']['VpcId'].should.equal(vpc_id)
    response['NatGateway']['SubnetId'].should.equal(subnet_id)
    response['NatGateway']['State'].should.equal('available')


@mock_ec2
def test_delete_nat_gateway():
    conn = boto3.client('ec2', 'us-east-1')
    vpc = conn.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = conn.create_subnet(
        VpcId=vpc_id,
        CidrBlock='10.0.1.0/27',
        AvailabilityZone='us-east-1a',
    )
    allocation_id = conn.allocate_address(Domain='vpc')['AllocationId']
    subnet_id = subnet['Subnet']['SubnetId']

    nat_gateway = conn.create_nat_gateway(
        SubnetId=subnet_id,
        AllocationId=allocation_id,
    )
    nat_gateway_id = nat_gateway['NatGateway']['NatGatewayId']
    response = conn.delete_nat_gateway(NatGatewayId=nat_gateway_id)

    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response.should.equal({
        'NatGatewayId': nat_gateway_id,
        'ResponseMetadata': {
            'HTTPStatusCode': 200,
            'RequestId': '741fc8ab-6ebe-452b-b92b-example'
        }
    })


@mock_ec2
def test_create_and_describe_nat_gateway():
    conn = boto3.client('ec2', 'us-east-1')
    vpc = conn.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    subnet = conn.create_subnet(
        VpcId=vpc_id,
        CidrBlock='10.0.1.0/27',
        AvailabilityZone='us-east-1a',
    )
    allocation_id = conn.allocate_address(Domain='vpc')['AllocationId']
    subnet_id = subnet['Subnet']['SubnetId']

    create_response = conn.create_nat_gateway(
        SubnetId=subnet_id,
        AllocationId=allocation_id,
    )
    nat_gateway_id = create_response['NatGateway']['NatGatewayId']
    describe_response = conn.describe_nat_gateways()

    enis = conn.describe_network_interfaces()['NetworkInterfaces']
    eni_id = enis[0]['NetworkInterfaceId']
    public_ip = conn.describe_addresses(AllocationIds=[allocation_id])[
        'Addresses'][0]['PublicIp']

    describe_response['NatGateways'].should.have.length_of(1)
    describe_response['NatGateways'][0][
        'NatGatewayId'].should.equal(nat_gateway_id)
    describe_response['NatGateways'][0]['State'].should.equal('available')
    describe_response['NatGateways'][0]['SubnetId'].should.equal(subnet_id)
    describe_response['NatGateways'][0]['VpcId'].should.equal(vpc_id)
    describe_response['NatGateways'][0]['NatGatewayAddresses'][
        0]['AllocationId'].should.equal(allocation_id)
    describe_response['NatGateways'][0]['NatGatewayAddresses'][
        0]['NetworkInterfaceId'].should.equal(eni_id)
    assert describe_response['NatGateways'][0][
        'NatGatewayAddresses'][0]['PrivateIp'].startswith('10.')
    describe_response['NatGateways'][0]['NatGatewayAddresses'][
        0]['PublicIp'].should.equal(public_ip)
