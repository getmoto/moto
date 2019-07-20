from __future__ import unicode_literals
import boto3
import sure  # noqa

from moto import mock_opsworks
from moto import mock_ec2


@mock_opsworks
def test_create_instance():
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

    second_stack_id = client.create_stack(
        Name="test_stack_2",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn"
    )['StackId']

    second_layer_id = client.create_layer(
        StackId=second_stack_id,
        Type="custom",
        Name="SecondTestLayer",
        Shortname="SecondTestLayerShortName"
    )['LayerId']

    response = client.create_instance(
        StackId=stack_id, LayerIds=[layer_id], InstanceType="t2.micro"
    )

    response.should.contain("InstanceId")

    client.create_instance.when.called_with(
        StackId="nothere", LayerIds=[layer_id], InstanceType="t2.micro"
    ).should.throw(Exception, "Unable to find stack with ID nothere")

    client.create_instance.when.called_with(
        StackId=stack_id, LayerIds=["nothere"], InstanceType="t2.micro"
    ).should.throw(Exception, "nothere")
    # ClientError
    client.create_instance.when.called_with(
        StackId=stack_id, LayerIds=[second_layer_id], InstanceType="t2.micro"
    ).should.throw(Exception, "Please only provide layer IDs from the same stack")
    # ClientError
    client.start_instance.when.called_with(
        InstanceId="nothere"
    ).should.throw(Exception, "Unable to find instance with ID nothere")


@mock_opsworks
def test_describe_instances():
    """
    create two stacks, with 1 layer and 2 layers (S1L1, S2L1, S2L2)

    populate S1L1 with 2 instances (S1L1_i1, S1L1_i2)
    populate S2L1 with 1 instance (S2L1_i1)
    populate S2L2 with 3 instances (S2L2_i1..2)
    """

    client = boto3.client('opsworks', region_name='us-east-1')
    S1 = client.create_stack(
        Name="S1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn"
    )['StackId']
    S1L1 = client.create_layer(
        StackId=S1,
        Type="custom",
        Name="S1L1",
        Shortname="S1L1"
    )['LayerId']
    S2 = client.create_stack(
        Name="S2",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn"
    )['StackId']
    S2L1 = client.create_layer(
        StackId=S2,
        Type="custom",
        Name="S2L1",
        Shortname="S2L1"
    )['LayerId']
    S2L2 = client.create_layer(
        StackId=S2,
        Type="custom",
        Name="S2L2",
        Shortname="S2L2"
    )['LayerId']

    S1L1_i1 = client.create_instance(
        StackId=S1, LayerIds=[S1L1], InstanceType="t2.micro"
    )['InstanceId']
    S1L1_i2 = client.create_instance(
        StackId=S1, LayerIds=[S1L1], InstanceType="t2.micro"
    )['InstanceId']
    S2L1_i1 = client.create_instance(
        StackId=S2, LayerIds=[S2L1], InstanceType="t2.micro"
    )['InstanceId']
    S2L2_i1 = client.create_instance(
        StackId=S2, LayerIds=[S2L2], InstanceType="t2.micro"
    )['InstanceId']
    S2L2_i2 = client.create_instance(
        StackId=S2, LayerIds=[S2L2], InstanceType="t2.micro"
    )['InstanceId']

    # instances in Stack 1
    response = client.describe_instances(StackId=S1)['Instances']
    response.should.have.length_of(2)
    S1L1_i1.should.be.within([i["InstanceId"] for i in response])
    S1L1_i2.should.be.within([i["InstanceId"] for i in response])

    response2 = client.describe_instances(
        InstanceIds=[S1L1_i1, S1L1_i2])['Instances']
    sorted(response2, key=lambda d: d['InstanceId']).should.equal(
        sorted(response, key=lambda d: d['InstanceId']))

    response3 = client.describe_instances(LayerId=S1L1)['Instances']
    sorted(response3, key=lambda d: d['InstanceId']).should.equal(
        sorted(response, key=lambda d: d['InstanceId']))

    response = client.describe_instances(StackId=S1)['Instances']
    response.should.have.length_of(2)
    S1L1_i1.should.be.within([i["InstanceId"] for i in response])
    S1L1_i2.should.be.within([i["InstanceId"] for i in response])

    # instances in Stack 2
    response = client.describe_instances(StackId=S2)['Instances']
    response.should.have.length_of(3)
    S2L1_i1.should.be.within([i["InstanceId"] for i in response])
    S2L2_i1.should.be.within([i["InstanceId"] for i in response])
    S2L2_i2.should.be.within([i["InstanceId"] for i in response])

    response = client.describe_instances(LayerId=S2L1)['Instances']
    response.should.have.length_of(1)
    S2L1_i1.should.be.within([i["InstanceId"] for i in response])

    response = client.describe_instances(LayerId=S2L2)['Instances']
    response.should.have.length_of(2)
    S2L1_i1.should_not.be.within([i["InstanceId"] for i in response])

    # ClientError
    client.describe_instances.when.called_with(
        StackId=S1,
        LayerId=S1L1
    ).should.throw(
        Exception, "Please provide either one or more"
    )
    # ClientError
    client.describe_instances.when.called_with(
        StackId="nothere"
    ).should.throw(
        Exception, "nothere"
    )
    # ClientError
    client.describe_instances.when.called_with(
        LayerId="nothere"
    ).should.throw(
        Exception, "nothere"
    )
    # ClientError
    client.describe_instances.when.called_with(
        InstanceIds=["nothere"]
    ).should.throw(
        Exception, "nothere"
    )


@mock_opsworks
@mock_ec2
def test_ec2_integration():
    """
    instances created via OpsWorks should be discoverable via ec2
    """

    opsworks = boto3.client('opsworks', region_name='us-east-1')
    stack_id = opsworks.create_stack(
        Name="S1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn"
    )['StackId']

    layer_id = opsworks.create_layer(
        StackId=stack_id,
        Type="custom",
        Name="S1L1",
        Shortname="S1L1"
    )['LayerId']

    instance_id = opsworks.create_instance(
        StackId=stack_id, LayerIds=[layer_id], InstanceType="t2.micro", SshKeyName="testSSH"
    )['InstanceId']

    ec2 = boto3.client('ec2', region_name='us-east-1')

    # Before starting the instance, it shouldn't be discoverable via ec2
    reservations = ec2.describe_instances()['Reservations']
    assert reservations.should.be.empty

    # After starting the instance, it should be discoverable via ec2
    opsworks.start_instance(InstanceId=instance_id)
    reservations = ec2.describe_instances()['Reservations']
    reservations[0]['Instances'].should.have.length_of(1)
    instance = reservations[0]['Instances'][0]
    opsworks_instance = opsworks.describe_instances(StackId=stack_id)[
        'Instances'][0]

    instance['InstanceId'].should.equal(opsworks_instance['Ec2InstanceId'])
    instance['PrivateIpAddress'].should.equal(opsworks_instance['PrivateIp'])
