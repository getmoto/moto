from __future__ import unicode_literals
import boto3
import sure  # noqa
import re

from moto import mock_opsworks

@mock_opsworks
def test_create_instance_response():
    client = boto3.client('opsworks')
    stack_id = client.create_stack(
        Name="test_stack_1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn"
    )['StackId']

    layer_id = client.create_layer(
        StackId=stack_id,
        Type="custom",
        Name="TestLayer",
        Shortname="TestLayerShortName"
    )['LayerId']

    response = client.create_instance(
        StackId=stack_id, LayerIds=[layer_id], InstanceType="t2.micro"
    )

    response.should.contain("InstanceId")

