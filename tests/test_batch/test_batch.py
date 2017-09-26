from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_batch, mock_iam, mock_ec2


DEFAULT_REGION = 'eu-central-1'


def _get_clients():
    return boto3.client('ec2', region_name=DEFAULT_REGION), \
           boto3.client('iam', region_name=DEFAULT_REGION), \
           boto3.client('batch', region_name=DEFAULT_REGION)


def _setup(ec2_client, iam_client):
    """
    Do prerequisite setup
    :return: VPC ID, Subnet ID, Security group ID, IAM Role ARN
    :rtype: tuple
    """
    resp = ec2_client.create_vpc(CidrBlock='172.30.0.0/24')
    vpc_id = resp['Vpc']['VpcId']
    resp = ec2_client.create_subnet(
        AvailabilityZone='eu-central-1a',
        CidrBlock='172.30.0.0/25',
        VpcId=vpc_id
    )
    subnet_id = resp['Subnet']['SubnetId']
    resp = ec2_client.create_security_group(
        Description='test_sg_desc',
        GroupName='test_sg',
        VpcId=vpc_id
    )
    sg_id = resp['GroupId']

    resp = iam_client.create_role(
        RoleName='TestRole',
        AssumeRolePolicyDocument='some_policy'
    )
    iam_arn = resp['Role']['Arn']

    return vpc_id, subnet_id, sg_id, iam_arn


# Yes, yes it talks to all the things
@mock_ec2
@mock_iam
@mock_batch
def test_create_compute_environment():
    ec2_client, iam_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='MANAGED',
        state='ENABLED',
        computeResources={
            'type': 'EC2',
            'minvCpus': 123,
            'maxvCpus': 123,
            'desiredvCpus': 123,
            'instanceTypes': [
                'some_instance_type',
            ],
            'imageId': 'some_image_id',
            'subnets': [
                subnet_id,
            ],
            'securityGroupIds': [
                sg_id,
            ],
            'ec2KeyPair': 'string',
            'instanceRole': iam_arn,
            'tags': {
                'string': 'string'
            },
            'bidPercentage': 123,
            'spotIamFleetRole': 'string'
        },
        serviceRole=iam_arn
    )
    resp.should.contain('computeEnvironmentArn')
    resp['computeEnvironmentName'].should.equal(compute_name)

# TODO create 1000s of tests to test complex option combinations of create environment
