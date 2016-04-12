from __future__ import unicode_literals
import boto3
import sure  # noqa

from moto import mock_opsworks, mock_ec2, mock_elb


@mock_opsworks
def test_create_stack_response():
    client = boto3.client('opsworks')
    response = client.create_stack(
        Name="test_stack_1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn"
    )
    response.should.contain("StackId")


@mock_opsworks
def test_describe_stacks():
    client = boto3.client('opsworks')
    for i in xrange(1, 4):
        client.create_stack(
            Name="test_stack_{}".format(i),
            Region="us-east-1",
            ServiceRoleArn="service_arn",
            DefaultInstanceProfileArn="profile_arn"
        )

    response = client.describe_stacks()
    response['Stacks'].should.have.length_of(3)
    response['Stacks'][0]['ServiceRoleArn'].should.equal("service_arn")
    response['Stacks'][0]['DefaultInstanceProfileArn'].should.equal("profile_arn")

    _id = response['Stacks'][0]['StackId']
    response = client.describe_stacks(StackIds=[_id])
    response['Stacks'].should.have.length_of(1)
    response['Stacks'][0]['Arn'].should.contain(_id)


