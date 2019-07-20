from __future__ import unicode_literals
import boto3
from freezegun import freeze_time
import sure  # noqa
import re

from moto import mock_opsworks


@freeze_time("2015-01-01")
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

    second_stack_id = client.create_stack(
        Name="test_stack_2",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn"
    )['StackId']

    response = client.create_layer(
        StackId=second_stack_id,
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
        Exception, re.compile(
            r'already a layer with shortname "TestLayerShortName"')
    )
    # ClientError
    client.create_layer.when.called_with(
        StackId="nothere",
        Type="custom",
        Name="TestLayer",
        Shortname="_"
    ).should.throw(
        Exception, "nothere"
    )


@freeze_time("2015-01-01")
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
    rv1['Layers'].should.equal(rv2['Layers'])

    rv1['Layers'][0]['Name'].should.equal("TestLayer")

    # ClientError
    client.describe_layers.when.called_with(
        StackId=stack_id,
        LayerIds=[layer_id]
    ).should.throw(
        Exception, "Please provide one or more layer IDs or a stack ID"
    )
    # ClientError
    client.describe_layers.when.called_with(
        StackId="nothere"
    ).should.throw(
        Exception, "Unable to find stack with ID nothere"
    )
    # ClientError
    client.describe_layers.when.called_with(
        LayerIds=["nothere"]
    ).should.throw(
        Exception, "nothere"
    )
