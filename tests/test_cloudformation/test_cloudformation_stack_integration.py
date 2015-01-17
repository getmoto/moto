from __future__ import unicode_literals
import json

import boto
import boto.cloudformation
import boto.ec2
import boto.ec2.autoscale
import boto.ec2.elb
from boto.exception import BotoServerError
import boto.iam
import boto.sqs
import boto.vpc
import sure  # noqa

from moto import (
    mock_autoscaling,
    mock_cloudformation,
    mock_ec2,
    mock_elb,
    mock_iam,
    mock_rds,
    mock_route53,
    mock_sqs,
)

from .fixtures import (
    ec2_classic_eip,
    fn_join,
    rds_mysql_with_read_replica,
    route53_roundrobin,
    single_instance_with_ebs_volume,
    vpc_eip,
    vpc_single_instance_in_subnet,
)


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

    conn = boto.cloudformation.connect_to_region("us-west-1")
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

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "ec2_stack",
        template_body=ec2_template_json,
    )

    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    stack = conn.describe_stacks()[0]
    instance = stack.describe_resources()[0]
    instance.resource_type.should.equal('AWS::EC2::Instance')
    instance.logical_resource_id.should.contain("WebServerGroup")
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

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "elb_stack",
        template_body=elb_template_json,
    )

    elb_conn = boto.ec2.elb.connect_to_region("us-west-1")
    load_balancer = elb_conn.get_all_load_balancers()[0]

    ec2_conn = boto.ec2.connect_to_region("us-west-1")
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

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "security_group_stack",
        template_body=security_group_template_json,
    )

    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    security_groups = ec2_conn.get_all_security_groups()
    for group in security_groups:
        if "InstanceSecurityGroup" in group.name:
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
                    "LoadBalancerName": "my-elb",
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

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "web_stack",
        template_body=web_setup_template_json,
    )

    autoscale_conn = boto.ec2.autoscale.connect_to_region("us-west-1")
    autoscale_group = autoscale_conn.get_all_groups()[0]
    autoscale_group.launch_config_name.should.contain("my-launch-config")
    autoscale_group.load_balancers[0].should.equal('my-elb')

    # Confirm the Launch config was actually created
    autoscale_conn.get_all_launch_configurations().should.have.length_of(1)

    # Confirm the ELB was actually created
    elb_conn = boto.ec2.elb.connect_to_region("us-west-1")
    elb_conn.get_all_load_balancers().should.have.length_of(1)

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    as_group_resource = [resource for resource in resources if resource.resource_type == 'AWS::AutoScaling::AutoScalingGroup'][0]
    as_group_resource.physical_resource_id.should.contain("my-as-group")

    launch_config_resource = [resource for resource in resources if resource.resource_type == 'AWS::AutoScaling::LaunchConfiguration'][0]
    launch_config_resource.physical_resource_id.should.contain("my-launch-config")

    elb_resource = [resource for resource in resources if resource.resource_type == 'AWS::ElasticLoadBalancing::LoadBalancer'][0]
    elb_resource.physical_resource_id.should.contain("my-elb")


@mock_ec2()
@mock_cloudformation()
def test_vpc_single_instance_in_subnet():

    template_json = json.dumps(vpc_single_instance_in_subnet.template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack",
        template_body=template_json,
        parameters=[("KeyName", "my_key")],
    )

    vpc_conn = boto.vpc.connect_to_region("us-west-1")
    vpc = vpc_conn.get_all_vpcs()[0]
    vpc.cidr_block.should.equal("10.0.0.0/16")

    # Add this once we implement the endpoint
    # vpc_conn.get_all_internet_gateways().should.have.length_of(1)

    subnet = vpc_conn.get_all_subnets()[0]
    subnet.vpc_id.should.equal(vpc.id)

    ec2_conn = boto.ec2.connect_to_region("us-west-1")
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


@mock_cloudformation()
@mock_ec2()
@mock_rds()
def test_rds_mysql_with_read_replica():
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    ec2_conn.create_security_group('application', 'Our Application Group')

    template_json = json.dumps(rds_mysql_with_read_replica.template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack",
        template_body=template_json,
        parameters=[
            ("DBInstanceIdentifier", "master_db"),
            ("DBName", "my_db"),
            ("DBUser", "my_user"),
            ("DBPassword", "my_password"),
            ("DBAllocatedStorage", "20"),
            ("DBInstanceClass", "db.m1.medium"),
            ("EC2SecurityGroup", "application"),
            ("MultiAZ", "true"),
        ],
    )

    rds_conn = boto.rds.connect_to_region("us-west-1")

    primary = rds_conn.get_all_dbinstances("master_db")[0]
    primary.master_username.should.equal("my_user")
    primary.allocated_storage.should.equal(20)
    primary.instance_class.should.equal("db.m1.medium")
    primary.multi_az.should.equal(True)
    list(primary.read_replica_dbinstance_identifiers).should.have.length_of(1)
    replica_id = primary.read_replica_dbinstance_identifiers[0]

    replica = rds_conn.get_all_dbinstances(replica_id)[0]
    replica.instance_class.should.equal("db.m1.medium")

    security_group_name = primary.security_groups[0].name
    security_group = rds_conn.get_all_dbsecurity_groups(security_group_name)[0]
    security_group.ec2_groups[0].name.should.equal("application")


@mock_cloudformation()
@mock_ec2()
@mock_rds()
def test_rds_mysql_with_read_replica_in_vpc():
    template_json = json.dumps(rds_mysql_with_read_replica.template)
    conn = boto.cloudformation.connect_to_region("eu-central-1")
    conn.create_stack(
        "test_stack",
        template_body=template_json,
        parameters=[
            ("DBInstanceIdentifier", "master_db"),
            ("DBName", "my_db"),
            ("DBUser", "my_user"),
            ("DBPassword", "my_password"),
            ("DBAllocatedStorage", "20"),
            ("DBInstanceClass", "db.m1.medium"),
            ("MultiAZ", "true"),
        ],
    )

    rds_conn = boto.rds.connect_to_region("eu-central-1")
    primary = rds_conn.get_all_dbinstances("master_db")[0]

    subnet_group_name = primary.subnet_group.name
    subnet_group = rds_conn.get_all_db_subnet_groups(subnet_group_name)[0]
    subnet_group.description.should.equal("my db subnet group")


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
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack",
        template_body=iam_template_json,
    )

    iam_conn = boto.iam.connect_to_region("us-west-1")

    role_result = iam_conn.list_roles()['list_roles_response']['list_roles_result']['roles'][0]
    role = iam_conn.get_role(role_result.role_name)
    role.role_name.should.contain("my-role")
    role.path.should.equal("my-path")

    instance_profile_response = iam_conn.list_instance_profiles()['list_instance_profiles_response']
    cfn_instance_profile = instance_profile_response['list_instance_profiles_result']['instance_profiles'][0]
    instance_profile = iam_conn.get_instance_profile(cfn_instance_profile.instance_profile_name)
    instance_profile.instance_profile_name.should.contain("my-instance-profile")
    instance_profile.path.should.equal("my-path")
    instance_profile.role_id.should.equal(role.role_id)

    autoscale_conn = boto.ec2.autoscale.connect_to_region("us-west-1")
    launch_config = autoscale_conn.get_all_launch_configurations()[0]
    launch_config.instance_profile_name.should.contain("my-instance-profile")

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
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack",
        template_body=template_json,
        parameters=[("KeyName", "key_name")]
    )

    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    volume = ec2_conn.get_all_volumes()[0]
    volume.volume_state().should.equal('in-use')
    volume.attach_data.instance_id.should.equal(ec2_instance.id)

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    ebs_volume = [resource for resource in resources if resource.resource_type == 'AWS::EC2::Volume'][0]
    ebs_volume.physical_resource_id.should.equal(volume.id)


@mock_cloudformation()
def test_create_template_without_required_param():
    template_json = json.dumps(single_instance_with_ebs_volume.template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack.when.called_with(
        "test_stack",
        template_body=template_json,
    ).should.throw(BotoServerError)


@mock_ec2()
@mock_cloudformation()
def test_classic_eip():

    template_json = json.dumps(ec2_classic_eip.template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack("test_stack", template_body=template_json)
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    eip = ec2_conn.get_all_addresses()[0]

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    cfn_eip = [resource for resource in resources if resource.resource_type == 'AWS::EC2::EIP'][0]
    cfn_eip.physical_resource_id.should.equal(eip.public_ip)


@mock_ec2()
@mock_cloudformation()
def test_vpc_eip():

    template_json = json.dumps(vpc_eip.template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack("test_stack", template_body=template_json)
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    eip = ec2_conn.get_all_addresses()[0]

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    cfn_eip = [resource for resource in resources if resource.resource_type == 'AWS::EC2::EIP'][0]
    cfn_eip.physical_resource_id.should.equal(eip.allocation_id)


@mock_ec2()
@mock_cloudformation()
def test_fn_join():

    template_json = json.dumps(fn_join.template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack("test_stack", template_body=template_json)
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    eip = ec2_conn.get_all_addresses()[0]

    stack = conn.describe_stacks()[0]
    fn_join_output = stack.outputs[0]
    fn_join_output.value.should.equal('test eip:{0}'.format(eip.public_ip))


@mock_cloudformation()
@mock_sqs()
def test_conditional_resources():
    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Parameters": {
            "EnvType": {
                "Description": "Environment type.",
                "Type": "String",
            }
        },
        "Conditions": {
            "CreateQueue": {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]}
        },
        "Resources": {
            "QueueGroup": {
                "Condition": "CreateQueue",
                "Type": "AWS::SQS::Queue",
                "Properties": {
                    "QueueName": "my-queue",
                    "VisibilityTimeout": 60,
                }
            },
        },
    }
    sqs_template_json = json.dumps(sqs_template)

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack_without_queue",
        template_body=sqs_template_json,
        parameters=[("EnvType", "staging")],
    )
    sqs_conn = boto.sqs.connect_to_region("us-west-1")
    list(sqs_conn.get_all_queues()).should.have.length_of(0)

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack_with_queue",
        template_body=sqs_template_json,
        parameters=[("EnvType", "prod")],
    )
    sqs_conn = boto.sqs.connect_to_region("us-west-1")
    list(sqs_conn.get_all_queues()).should.have.length_of(1)


@mock_cloudformation()
@mock_ec2()
def test_conditional_if_handling():
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Conditions": {
            "EnvEqualsPrd": {
                "Fn::Equals": [
                    {
                        "Ref": "ENV"
                    },
                    "prd"
                ]
            }
        },
        "Parameters": {
            "ENV": {
                "Default": "dev",
                "Description": "Deployment environment for the stack (dev/prd)",
                "Type": "String"
            },
        },
        "Description": "Stack 1",
        "Resources": {
            "App1": {
                "Properties": {
                    "ImageId": {
                        "Fn::If": [
                            "EnvEqualsPrd",
                            "ami-00000000",
                            "ami-ffffffff"
                        ]
                    },
                },
                "Type": "AWS::EC2::Instance"
            },
        }
    }
    dummy_template_json = json.dumps(dummy_template)

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack('test_stack1', template_body=dummy_template_json)
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]
    ec2_instance.image_id.should.equal("ami-ffffffff")
    ec2_instance.terminate()

    conn = boto.cloudformation.connect_to_region("us-west-2")
    conn.create_stack('test_stack1', template_body=dummy_template_json, parameters=[("ENV", "prd")])
    ec2_conn = boto.ec2.connect_to_region("us-west-2")
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]
    ec2_instance.image_id.should.equal("ami-00000000")


@mock_cloudformation()
@mock_ec2()
def test_cloudformation_mapping():
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Mappings": {
            "RegionMap": {
                "us-east-1": {"32": "ami-6411e20d", "64": "ami-7a11e213"},
                "us-west-1": {"32": "ami-c9c7978c", "64": "ami-cfc7978a"},
                "eu-west-1": {"32": "ami-37c2f643", "64": "ami-31c2f645"},
                "ap-southeast-1": {"32": "ami-66f28c34", "64": "ami-60f28c32"},
                "ap-northeast-1": {"32": "ami-9c03a89d", "64": "ami-a003a8a1"}
            }
        },
        "Resources": {
            "WebServer": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": {
                        "Fn::FindInMap": ["RegionMap", {"Ref": "AWS::Region"}, "32"]
                    },
                    "InstanceType": "m1.small"
                },
                "Type": "AWS::EC2::Instance",
            },
        },
    }

    dummy_template_json = json.dumps(dummy_template)

    conn = boto.cloudformation.connect_to_region("us-east-1")
    conn.create_stack('test_stack1', template_body=dummy_template_json)
    ec2_conn = boto.ec2.connect_to_region("us-east-1")
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]
    ec2_instance.image_id.should.equal("ami-6411e20d")

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack('test_stack1', template_body=dummy_template_json)
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]
    ec2_instance.image_id.should.equal("ami-c9c7978c")


@mock_cloudformation()
@mock_route53()
def test_route53_roundrobin():
    route53_conn = boto.connect_route53()

    template_json = json.dumps(route53_roundrobin.template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    zones = route53_conn.get_all_hosted_zones()['ListHostedZonesResponse']['HostedZones']
    list(zones).should.have.length_of(1)
    zone_id = zones[0]['Id']

    rrsets = route53_conn.get_all_rrsets(zone_id)
    rrsets.hosted_zone_id.should.equal(zone_id)
    rrsets.should.have.length_of(2)
    record_set1 = rrsets[0]
    record_set1.name.should.equal('test_stack.us-west-1.my_zone.')
    record_set1.identifier.should.equal("test_stack AWS")
    record_set1.type.should.equal('CNAME')
    record_set1.ttl.should.equal('900')
    record_set1.weight.should.equal('3')
    # FIXME record_set1.resource_records[0].should.equal("aws.amazon.com")

    record_set2 = rrsets[1]
    record_set2.name.should.equal('test_stack.us-west-1.my_zone.')
    record_set2.identifier.should.equal("test_stack Amazon")
    record_set2.type.should.equal('CNAME')
    record_set2.ttl.should.equal('900')
    record_set2.weight.should.equal('1')
    # FIXME record_set2.resource_records[0].should.equal("www.amazon.com")
