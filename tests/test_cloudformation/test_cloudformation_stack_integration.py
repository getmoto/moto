from __future__ import unicode_literals
import json

import boto
import sure  # noqa

from moto import (
    mock_autoscaling,
    mock_cloudformation,
    mock_ec2,
    mock_elb,
    mock_iam,
)

from .fixtures import single_instance_with_ebs_volume, vpc_single_instance_in_subnet


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
            "my-security-group": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "My other group",
                },
            },
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
                        "CidrIp": "123.123.123.123/32",
                    }, {
                        "IpProtocol": "tcp",
                        "FromPort": "80",
                        "ToPort": "8000",
                        "SourceSecurityGroupId": {"Ref": "my-security-group"},
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
    security_groups = ec2_conn.get_all_security_groups()
    for group in security_groups:
        if group.name == "InstanceSecurityGroup":
            instance_group = group
        else:
            other_group = group

    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    ec2_instance.groups[0].id.should.equal(instance_group.id)
    instance_group.description.should.equal("My security group")
    rule1, rule2 = instance_group.rules
    int(rule1.to_port).should.equal(22)
    int(rule1.from_port).should.equal(22)
    rule1.grants[0].cidr_ip.should.equal("123.123.123.123/32")
    rule1.ip_protocol.should.equal('tcp')

    int(rule2.to_port).should.equal(8000)
    int(rule2.from_port).should.equal(80)
    rule2.ip_protocol.should.equal('tcp')
    rule2.grants[0].group_id.should.equal(other_group.id)


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

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    as_group_resource = [resource for resource in resources if resource.resource_type == 'AWS::AutoScaling::AutoScalingGroup'][0]
    as_group_resource.physical_resource_id.should.equal("my-as-group")

    launch_config_resource = [resource for resource in resources if resource.resource_type == 'AWS::AutoScaling::LaunchConfiguration'][0]
    launch_config_resource.physical_resource_id.should.equal("my-launch-config")

    elb_resource = [resource for resource in resources if resource.resource_type == 'AWS::ElasticLoadBalancing::LoadBalancer'][0]
    elb_resource.physical_resource_id.should.equal("my-elb")


@mock_ec2()
@mock_cloudformation()
def test_vpc_single_instance_in_subnet():

    template_json = json.dumps(vpc_single_instance_in_subnet.template)
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    vpc_conn = boto.connect_vpc()
    vpc = vpc_conn.get_all_vpcs()[0]
    vpc.cidr_block.should.equal("10.0.0.0/16")

    # Add this once we implement the endpoint
    # vpc_conn.get_all_internet_gateways().should.have.length_of(1)

    subnet = vpc_conn.get_all_subnets()[0]
    subnet.vpc_id.should.equal(vpc.id)

    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.get_all_instances()[0]
    instance = reservation.instances[0]
    # Check that the EIP is attached the the EC2 instance
    eip = ec2_conn.get_all_addresses()[0]
    eip.domain.should.equal('vpc')
    eip.instance_id.should.equal(instance.id)

    security_group = ec2_conn.get_all_security_groups()[0]
    security_group.vpc_id.should.equal(vpc.id)

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    vpc_resource = [resource for resource in resources if resource.resource_type == 'AWS::EC2::VPC'][0]
    vpc_resource.physical_resource_id.should.equal(vpc.id)

    subnet_resource = [resource for resource in resources if resource.resource_type == 'AWS::EC2::Subnet'][0]
    subnet_resource.physical_resource_id.should.equal(subnet.id)

    eip_resource = [resource for resource in resources if resource.resource_type == 'AWS::EC2::EIP'][0]
    eip_resource.physical_resource_id.should.equal(eip.allocation_id)


@mock_autoscaling()
@mock_iam()
@mock_cloudformation()
def test_iam_roles():
    iam_template = {
        "AWSTemplateFormatVersion": "2010-09-09",

        "Resources": {

            "my-launch-config": {
                "Properties": {
                    "IamInstanceProfile": {"Ref": "my-instance-profile"},
                    "ImageId": "ami-1234abcd",
                },
                "Type": "AWS::AutoScaling::LaunchConfiguration"
            },
            "my-instance-profile": {
                "Properties": {
                    "Path": "my-path",
                    "Roles": [{"Ref": "my-role"}],
                },
                "Type": "AWS::IAM::InstanceProfile"
            },
            "my-role": {
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Statement": [
                            {
                                "Action": [
                                    "sts:AssumeRole"
                                ],
                                "Effect": "Allow",
                                "Principal": {
                                    "Service": [
                                        "ec2.amazonaws.com"
                                    ]
                                }
                            }
                        ]
                    },
                    "Path": "my-path",
                    "Policies": [
                        {
                            "PolicyDocument": {
                                "Statement": [
                                    {
                                        "Action": [
                                            "ec2:CreateTags",
                                            "ec2:DescribeInstances",
                                            "ec2:DescribeTags"
                                        ],
                                        "Effect": "Allow",
                                        "Resource": [
                                            "*"
                                        ]
                                    }
                                ],
                                "Version": "2012-10-17"
                            },
                            "PolicyName": "EC2_Tags"
                        },
                        {
                            "PolicyDocument": {
                                "Statement": [
                                    {
                                        "Action": [
                                            "sqs:*"
                                        ],
                                        "Effect": "Allow",
                                        "Resource": [
                                            "*"
                                        ]
                                    }
                                ],
                                "Version": "2012-10-17"
                            },
                            "PolicyName": "SQS"
                        },
                    ]
                },
                "Type": "AWS::IAM::Role"
            }
        }
    }

    iam_template_json = json.dumps(iam_template)
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=iam_template_json,
    )

    iam_conn = boto.connect_iam()

    role = iam_conn.get_role("my-role")
    role.role_name.should.equal("my-role")
    role.path.should.equal("my-path")

    instance_profile = iam_conn.get_instance_profile("my-instance-profile")
    instance_profile.instance_profile_name.should.equal("my-instance-profile")
    instance_profile.path.should.equal("my-path")
    instance_profile.role_id.should.equal(role.role_id)

    autoscale_conn = boto.connect_autoscale()
    launch_config = autoscale_conn.get_all_launch_configurations()[0]
    launch_config.instance_profile_name.should.equal("my-instance-profile")

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    instance_profile_resource = [resource for resource in resources if resource.resource_type == 'AWS::IAM::InstanceProfile'][0]
    instance_profile_resource.physical_resource_id.should.equal(instance_profile.instance_profile_name)

    role_resource = [resource for resource in resources if resource.resource_type == 'AWS::IAM::Role'][0]
    role_resource.physical_resource_id.should.equal(role.role_id)


@mock_ec2()
@mock_cloudformation()
def test_single_instance_with_ebs_volume():

    template_json = json.dumps(single_instance_with_ebs_volume.template)
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    volume = ec2_conn.get_all_volumes()[0]
    volume.volume_state().should.equal('in-use')
    volume.attach_data.instance_id.should.equal(ec2_instance.id)

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    ebs_volume = [resource for resource in resources if resource.resource_type == 'AWS::EC2::Volume'][0]
    ebs_volume.physical_resource_id.should.equal(volume.id)
