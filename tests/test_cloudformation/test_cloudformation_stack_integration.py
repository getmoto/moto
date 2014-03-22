import json

import boto
import sure  # noqa

from moto import mock_autoscaling, mock_cloudformation, mock_ec2, mock_elb


@mock_cloudformation()
def test_stack_sqs_integration():
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


@mock_ec2()
@mock_cloudformation()
def test_stack_ec2_integration():
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


@mock_ec2()
@mock_elb()
@mock_cloudformation()
def test_stack_elb_integration_with_attached_ec2_instances():
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
    list(load_balancer.availability_zones).should.equal(['us-east1'])
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


@mock_ec2()
@mock_cloudformation()
def test_stack_security_groups():
    security_group_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "Ec2Instance2": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "SecurityGroups": [{"Ref": "InstanceSecurityGroup"}],
                    "ImageId": "ami-1234abcd",
                }
            },
            "InstanceSecurityGroup": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "My security group",
                    "SecurityGroupIngress": [{
                        "IpProtocol": "tcp",
                        "FromPort": "22",
                        "ToPort": "22",
                        "CidrIp": {"Ref": "SSHLocation"}
                    }, {
                        "IpProtocol": "tcp",
                        "FromPort": {"Ref": "WebServerPort"},
                        "ToPort": {"Ref": "WebServerPort"},
                        "CidrIp": "0.0.0.0/0"
                    }]
                }
            }
        },
    }
    security_group_template_json = json.dumps(security_group_template)

    conn = boto.connect_cloudformation()
    conn.create_stack(
        "security_group_stack",
        template_body=security_group_template_json,
    )

    ec2_conn = boto.connect_ec2()
    security_group = ec2_conn.get_all_security_groups()[0]
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    ec2_instance.groups[0].id.should.equal(security_group.id)
    security_group.description.should.equal("My security group")


@mock_autoscaling()
@mock_elb()
@mock_cloudformation()
def test_autoscaling_group_with_elb():

    web_setup_template = {
        "AWSTemplateFormatVersion": "2010-09-09",

        "Resources": {
            "my-as-group": {
                "Type": "AWS::AutoScaling::AutoScalingGroup",
                "Properties": {
                    "AvailabilityZones": ['us-east1'],
                    "LaunchConfigurationName": {"Ref": "my-launch-config"},
                    "MinSize": "2",
                    "MaxSize": "2",
                    "LoadBalancerNames": [{"Ref": "my-elb"}]
                },
            },

            "my-launch-config": {
                "Type": "AWS::AutoScaling::LaunchConfiguration",
                "Properties": {
                    "ImageId": "ami-1234abcd",
                    "UserData": "some user data",
                }
            },

            "my-elb": {
                "Type": "AWS::ElasticLoadBalancing::LoadBalancer",
                "Properties": {
                    "AvailabilityZones": ['us-east1'],
                    "Listeners": [{
                        "LoadBalancerPort": "80",
                        "InstancePort": "80",
                        "Protocol": "HTTP"
                    }],
                    "HealthCheck": {
                        "Target": "80",
                        "HealthyThreshold": "3",
                        "UnhealthyThreshold": "5",
                        "Interval": "30",
                        "Timeout": "5",
                    },
                },
            },
        }
    }

    web_setup_template_json = json.dumps(web_setup_template)

    conn = boto.connect_cloudformation()
    conn.create_stack(
        "web_stack",
        template_body=web_setup_template_json,
    )

    autoscale_conn = boto.connect_autoscale()
    autoscale_group = autoscale_conn.get_all_groups()[0]
    autoscale_group.launch_config_name.should.equal("my-launch-config")
    autoscale_group.load_balancers[0].should.equal('my-elb')

    # Confirm the Launch config was actually created
    autoscale_conn.get_all_launch_configurations().should.have.length_of(1)

    # Confirm the ELB was actually created
    elb_conn = boto.connect_elb()
    elb_conn.get_all_load_balancers().should.have.length_of(1)
