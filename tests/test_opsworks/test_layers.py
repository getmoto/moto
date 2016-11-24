from __future__ import unicode_literals
import boto3
import sure  # noqa
import re

from datetime import datetime

from freezegun import freeze_time

from moto import mock_opsworks


@mock_opsworks
def test_create_layer_response():
    client = boto3.client('opsworks', region_name='us-east-1')
    stack_id = client.create_stack(
        Name="test_stack_1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn"
    )['StackId']

    response = client.create_layer(
        StackId=stack_id,
        Type="custom",
        Name="TestLayer",
        Shortname="TestLayerShortName"
    )

    response.should.contain("LayerId")

    # ClientError
    client.create_layer.when.called_with(
        StackId=stack_id,
        Type="custom",
        Name="TestLayer",
        Shortname="_"
    ).should.throw(
        Exception, re.compile(r'already a layer named "TestLayer"')
    )
    # ClientError
    client.create_layer.when.called_with(
        StackId=stack_id,
        Type="custom",
        Name="_",
        Shortname="TestLayerShortName"
    ).should.throw(
        Exception, re.compile(r'already a layer with shortname "TestLayerShortName"')
    )


@freeze_time(datetime.now())
@mock_opsworks
def test_describe_layers():
    client = boto3.client('opsworks', region_name='us-east-1')
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

    rv1 = client.describe_layers(StackId=stack_id)
    rv2 = client.describe_layers(LayerIds=[layer_id])
    rv1.should.equal(rv2)

    rv1['Layers'][0]['Name'].should.equal("TestLayer")

