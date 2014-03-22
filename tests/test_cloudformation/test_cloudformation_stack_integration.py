import json

import boto
import sure  # noqa

from moto import mock_cloudformation, mock_ec2, mock_elb

sqs_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "QueueGroup": {

            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": "my-queue",
                "VisibilityTimeout": 60,
            }
        },
    },
}
sqs_template_json = json.dumps(sqs_template)


@mock_cloudformation()
def test_stack_sqs_integration():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=sqs_template_json,
    )

    stack = conn.describe_stacks()[0]
    queue = stack.describe_resources()[0]
    queue.resource_type.should.equal('AWS::SQS::Queue')
    queue.logical_resource_id.should.equal("QueueGroup")
    queue.physical_resource_id.should.equal("my-queue")


ec2_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "WebServerGroup": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": "ami-1234abcd",
                "UserData": "some user data",
            }
        },
    },
}
ec2_template_json = json.dumps(ec2_template)


@mock_ec2()
@mock_cloudformation()
def test_stack_ec2_integration():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "ec2_stack",
        template_body=ec2_template_json,
    )

    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    stack = conn.describe_stacks()[0]
    instance = stack.describe_resources()[0]
    instance.resource_type.should.equal('AWS::EC2::Instance')
    instance.logical_resource_id.should.equal("WebServerGroup")
    instance.physical_resource_id.should.equal(ec2_instance.id)


elb_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "MyELB": {
            "Type": "AWS::ElasticLoadBalancing::LoadBalancer",
            "Instances": [{"Ref": "Ec2Instance1"}],
            "Properties": {
                "LoadBalancerName": "test-elb",
                "AvailabilityZones": ['us-east1'],
            }
        },
        "Ec2Instance1": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": "ami-1234abcd",
                "UserData": "some user data",
            }
        },
    },
}
elb_template_json = json.dumps(elb_template)


@mock_ec2()
@mock_elb()
@mock_cloudformation()
def test_stack_elb_integration_with_attached_ec2_instances():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "elb_stack",
        template_body=elb_template_json,
    )

    elb_conn = boto.connect_elb()
    load_balancer = elb_conn.get_all_load_balancers()[0]

    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]
    instance_id = ec2_instance.id

    load_balancer.instances[0].id.should.equal(ec2_instance.id)
    load_balancer_name = load_balancer.name

    stack = conn.describe_stacks()[0]
    stack_resources = stack.describe_resources()
    stack_resources.should.have.length_of(2)
    for resource in stack_resources:
        if resource.resource_type == 'AWS::ElasticLoadBalancing::LoadBalancer':
            load_balancer = resource
        else:
            ec2_instance = resource

    load_balancer.logical_resource_id.should.equal("MyELB")
    load_balancer.physical_resource_id.should.equal(load_balancer_name)
    ec2_instance.physical_resource_id.should.equal(instance_id)
