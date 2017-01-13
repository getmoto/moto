from __future__ import unicode_literals
import json

import base64
import boto
import boto.cloudformation
import boto.datapipeline
import boto.ec2
import boto.ec2.autoscale
import boto.ec2.elb
from boto.exception import BotoServerError
import boto.iam
import boto.redshift
import boto.sns
import boto.sqs
import boto.vpc
import boto3
import sure  # noqa

from moto import (
    mock_autoscaling,
    mock_cloudformation,
    mock_datapipeline,
    mock_ec2,
    mock_elb,
    mock_iam,
    mock_kms,
    mock_lambda,
    mock_rds,
    mock_rds2,
    mock_redshift,
    mock_route53,
    mock_sns,
    mock_sqs,
)

from .fixtures import (
    ec2_classic_eip,
    fn_join,
    rds_mysql_with_db_parameter_group,
    rds_mysql_with_read_replica,
    redshift,
    route53_ec2_instance_with_public_ip,
    route53_health_check,
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


@mock_cloudformation()
def test_stack_list_resources():
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

    resources = conn.list_stack_resources("test_stack")
    assert len(resources) == 1
    queue = resources[0]
    queue.resource_type.should.equal('AWS::SQS::Queue')
    queue.logical_resource_id.should.equal("QueueGroup")
    queue.physical_resource_id.should.equal("my-queue")


@mock_cloudformation()
@mock_sqs()
def test_update_stack():
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

    sqs_conn = boto.sqs.connect_to_region("us-west-1")
    queues = sqs_conn.get_all_queues()
    queues.should.have.length_of(1)
    queues[0].get_attributes('VisibilityTimeout')['VisibilityTimeout'].should.equal('60')

    sqs_template['Resources']['QueueGroup']['Properties']['VisibilityTimeout'] = 100
    sqs_template_json = json.dumps(sqs_template)
    conn.update_stack("test_stack", sqs_template_json)

    queues = sqs_conn.get_all_queues()
    queues.should.have.length_of(1)
    queues[0].get_attributes('VisibilityTimeout')['VisibilityTimeout'].should.equal('100')


@mock_cloudformation()
@mock_sqs()
def test_update_stack_and_remove_resource():
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

    sqs_conn = boto.sqs.connect_to_region("us-west-1")
    queues = sqs_conn.get_all_queues()
    queues.should.have.length_of(1)

    sqs_template['Resources'].pop('QueueGroup')
    sqs_template_json = json.dumps(sqs_template)
    conn.update_stack("test_stack", sqs_template_json)

    queues = sqs_conn.get_all_queues()
    queues.should.have.length_of(0)


@mock_cloudformation()
@mock_sqs()
def test_update_stack_and_add_resource():
    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {},
    }
    sqs_template_json = json.dumps(sqs_template)

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack",
        template_body=sqs_template_json,
    )

    sqs_conn = boto.sqs.connect_to_region("us-west-1")
    queues = sqs_conn.get_all_queues()
    queues.should.have.length_of(0)

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
    conn.update_stack("test_stack", sqs_template_json)

    queues = sqs_conn.get_all_queues()
    queues.should.have.length_of(1)


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
                "Properties": {
                    "Instances": [{"Ref": "Ec2Instance1"}],
                    "LoadBalancerName": "test-elb",
                    "AvailabilityZones": ['us-east-1'],
                    "Listeners": [
                        {
                            "InstancePort": "80",
                            "LoadBalancerPort": "80",
                            "Protocol": "HTTP",
                        }
                    ],
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

    load_balancer.instances[0].id.should.equal(ec2_instance.id)
    list(load_balancer.availability_zones).should.equal(['us-east-1'])


@mock_elb()
@mock_cloudformation()
def test_stack_elb_integration_with_health_check():
    elb_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyELB": {
                "Type": "AWS::ElasticLoadBalancing::LoadBalancer",
                "Properties": {
                    "LoadBalancerName": "test-elb",
                    "AvailabilityZones": ['us-west-1'],
                    "HealthCheck": {
                        "HealthyThreshold": "3",
                        "Interval": "5",
                        "Target": "HTTP:80/healthcheck",
                        "Timeout": "4",
                        "UnhealthyThreshold": "2",
                    },
                    "Listeners": [
                        {
                            "InstancePort": "80",
                            "LoadBalancerPort": "80",
                            "Protocol": "HTTP",
                        }
                    ],
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
    health_check = load_balancer.health_check

    health_check.healthy_threshold.should.equal(3)
    health_check.interval.should.equal(5)
    health_check.target.should.equal("HTTP:80/healthcheck")
    health_check.timeout.should.equal(4)
    health_check.unhealthy_threshold.should.equal(2)


@mock_elb()
@mock_cloudformation()
def test_stack_elb_integration_with_update():
    elb_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyELB": {
                "Type": "AWS::ElasticLoadBalancing::LoadBalancer",
                "Properties": {
                    "LoadBalancerName": "test-elb",
                    "AvailabilityZones": ['us-west-1a'],
                    "Listeners": [
                        {
                            "InstancePort": "80",
                            "LoadBalancerPort": "80",
                            "Protocol": "HTTP",
                        }
                    ],
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
    load_balancer.availability_zones[0].should.equal('us-west-1a')

    elb_template['Resources']['MyELB']['Properties']['AvailabilityZones'] = ['us-west-1b']
    elb_template_json = json.dumps(elb_template)
    conn.update_stack(
        "elb_stack",
        template_body=elb_template_json,
    )
    load_balancer = elb_conn.get_all_load_balancers()[0]
    load_balancer.availability_zones[0].should.equal('us-west-1b')


@mock_ec2()
@mock_redshift()
@mock_cloudformation()
def test_redshift_stack():
    redshift_template_json = json.dumps(redshift.template)

    vpc_conn = boto.vpc.connect_to_region("us-west-2")
    conn = boto.cloudformation.connect_to_region("us-west-2")
    conn.create_stack(
        "redshift_stack",
        template_body=redshift_template_json,
        parameters=[
            ("DatabaseName", "mydb"),
            ("ClusterType", "multi-node"),
            ("NumberOfNodes", 2),
            ("NodeType", "dw1.xlarge"),
            ("MasterUsername", "myuser"),
            ("MasterUserPassword", "mypass"),
            ("InboundTraffic", "10.0.0.1/16"),
            ("PortNumber", 5439),
        ]
    )

    redshift_conn = boto.redshift.connect_to_region("us-west-2")

    cluster_res = redshift_conn.describe_clusters()
    clusters = cluster_res['DescribeClustersResponse']['DescribeClustersResult']['Clusters']
    clusters.should.have.length_of(1)
    cluster = clusters[0]
    cluster['DBName'].should.equal("mydb")
    cluster['NumberOfNodes'].should.equal(2)
    cluster['NodeType'].should.equal("dw1.xlarge")
    cluster['MasterUsername'].should.equal("myuser")
    cluster['Port'].should.equal(5439)
    cluster['VpcSecurityGroups'].should.have.length_of(1)
    security_group_id = cluster['VpcSecurityGroups'][0]['VpcSecurityGroupId']

    groups = vpc_conn.get_all_security_groups(group_ids=[security_group_id])
    groups.should.have.length_of(1)
    group = groups[0]
    group.rules.should.have.length_of(1)
    group.rules[0].grants[0].cidr_ip.should.equal("10.0.0.1/16")


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
                    "Tags": [
                        {
                            "Key": "bar",
                            "Value": "baz"
                        }
                    ],
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
        tags={"foo":"bar"}
    )

    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    instance_group = ec2_conn.get_all_security_groups(filters={'description': ['My security group']})[0]
    other_group = ec2_conn.get_all_security_groups(filters={'description': ['My other group']})[0]

    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    ec2_instance.groups[0].id.should.equal(instance_group.id)
    instance_group.description.should.equal("My security group")
    instance_group.tags.should.have.key('foo').which.should.equal('bar')
    instance_group.tags.should.have.key('bar').which.should.equal('baz')
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
                        "Protocol": "HTTP",
                    }],
                    "LoadBalancerName": "my-elb",
                    "HealthCheck": {
                        "Target": "HTTP:80",
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


@mock_autoscaling()
@mock_cloudformation()
def test_autoscaling_group_update():
    asg_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "my-as-group": {
                "Type": "AWS::AutoScaling::AutoScalingGroup",
                "Properties": {
                    "AvailabilityZones": ['us-west-1'],
                    "LaunchConfigurationName": {"Ref": "my-launch-config"},
                    "MinSize": "2",
                    "MaxSize": "2",
                },
            },

            "my-launch-config": {
                "Type": "AWS::AutoScaling::LaunchConfiguration",
                "Properties": {
                    "ImageId": "ami-1234abcd",
                    "UserData": "some user data",
                }
            },
        },
    }
    asg_template_json = json.dumps(asg_template)

    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "asg_stack",
        template_body=asg_template_json,
    )

    autoscale_conn = boto.ec2.autoscale.connect_to_region("us-west-1")
    asg = autoscale_conn.get_all_groups()[0]
    asg.min_size.should.equal(2)
    asg.max_size.should.equal(2)

    asg_template['Resources']['my-as-group']['Properties']['MaxSize'] = 3
    asg_template_json = json.dumps(asg_template)
    conn.update_stack(
        "asg_stack",
        template_body=asg_template_json,
    )
    asg = autoscale_conn.get_all_groups()[0]
    asg.min_size.should.equal(2)
    asg.max_size.should.equal(3)


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

    vpc = vpc_conn.get_all_vpcs(filters={'cidrBlock': '10.0.0.0/16'})[0]
    vpc.cidr_block.should.equal("10.0.0.0/16")

    # Add this once we implement the endpoint
    # vpc_conn.get_all_internet_gateways().should.have.length_of(1)

    subnet = vpc_conn.get_all_subnets(filters={'vpcId': vpc.id})[0]
    subnet.vpc_id.should.equal(vpc.id)

    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    reservation = ec2_conn.get_all_instances()[0]
    instance = reservation.instances[0]
    # Check that the EIP is attached the the EC2 instance
    eip = ec2_conn.get_all_addresses()[0]
    eip.domain.should.equal('vpc')
    eip.instance_id.should.equal(instance.id)

    security_group = ec2_conn.get_all_security_groups(filters={'vpc_id': [vpc.id]})[0]
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
@mock_rds2()
def test_rds_db_parameter_groups():
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    ec2_conn.create_security_group('application', 'Our Application Group')

    template_json = json.dumps(rds_mysql_with_db_parameter_group.template)
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

    rds_conn = boto3.client('rds', region_name="us-west-1")

    db_parameter_groups = rds_conn.describe_db_parameter_groups()
    len(db_parameter_groups['DBParameterGroups']).should.equal(1)
    db_parameter_group_name = db_parameter_groups['DBParameterGroups'][0]['DBParameterGroupName']

    found_cloudformation_set_parameter = False
    for db_parameter in rds_conn.describe_db_parameters(DBParameterGroupName=db_parameter_group_name)['Parameters']:
        if db_parameter['ParameterName'] == 'BACKLOG_QUEUE_LIMIT' and db_parameter['ParameterValue'] == '2048':
            found_cloudformation_set_parameter = True

    found_cloudformation_set_parameter.should.equal(True)



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

    volumes = ec2_conn.get_all_volumes()
    # Grab the mounted drive
    volume = [volume for volume in volumes if volume.attach_data.device == '/dev/sdh'][0]
    volume.volume_state().should.equal('in-use')
    volume.attach_data.instance_id.should.equal(ec2_instance.id)

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    ebs_volumes = [resource for resource in resources if resource.resource_type == 'AWS::EC2::Volume']
    ebs_volumes[0].physical_resource_id.should.equal(volume.id)


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
    stack = conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    zones = route53_conn.get_all_hosted_zones()['ListHostedZonesResponse']['HostedZones']
    list(zones).should.have.length_of(1)
    zone_id = zones[0]['Id']
    zone_id = zone_id.split('/')
    zone_id = zone_id[2]

    rrsets = route53_conn.get_all_rrsets(zone_id)
    rrsets.hosted_zone_id.should.equal(zone_id)
    rrsets.should.have.length_of(2)
    record_set1 = rrsets[0]
    record_set1.name.should.equal('test_stack.us-west-1.my_zone.')
    record_set1.identifier.should.equal("test_stack AWS")
    record_set1.type.should.equal('CNAME')
    record_set1.ttl.should.equal('900')
    record_set1.weight.should.equal('3')
    record_set1.resource_records[0].should.equal("aws.amazon.com")

    record_set2 = rrsets[1]
    record_set2.name.should.equal('test_stack.us-west-1.my_zone.')
    record_set2.identifier.should.equal("test_stack Amazon")
    record_set2.type.should.equal('CNAME')
    record_set2.ttl.should.equal('900')
    record_set2.weight.should.equal('1')
    record_set2.resource_records[0].should.equal("www.amazon.com")

    stack = conn.describe_stacks()[0]
    output = stack.outputs[0]
    output.key.should.equal('DomainName')
    output.value.should.equal('arn:aws:route53:::hostedzone/{0}'.format(zone_id))


@mock_cloudformation()
@mock_ec2()
@mock_route53()
def test_route53_ec2_instance_with_public_ip():
    route53_conn = boto.connect_route53()
    ec2_conn = boto.ec2.connect_to_region("us-west-1")

    template_json = json.dumps(route53_ec2_instance_with_public_ip.template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    instance_id = ec2_conn.get_all_reservations()[0].instances[0].id

    zones = route53_conn.get_all_hosted_zones()['ListHostedZonesResponse']['HostedZones']
    list(zones).should.have.length_of(1)
    zone_id = zones[0]['Id']
    zone_id = zone_id.split('/')
    zone_id = zone_id[2]


    rrsets = route53_conn.get_all_rrsets(zone_id)
    rrsets.should.have.length_of(1)

    record_set1 = rrsets[0]
    record_set1.name.should.equal('{0}.us-west-1.my_zone.'.format(instance_id))
    record_set1.identifier.should.equal(None)
    record_set1.type.should.equal('A')
    record_set1.ttl.should.equal('900')
    record_set1.weight.should.equal(None)
    record_set1.resource_records[0].should.equal("10.0.0.25")


@mock_cloudformation()
@mock_route53()
def test_route53_associate_health_check():
    route53_conn = boto.connect_route53()

    template_json = json.dumps(route53_health_check.template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    checks = route53_conn.get_list_health_checks()['ListHealthChecksResponse']['HealthChecks']
    list(checks).should.have.length_of(1)
    check = checks[0]
    health_check_id = check['Id']
    config = check['HealthCheckConfig']
    config["FailureThreshold"].should.equal("3")
    config["IPAddress"].should.equal("10.0.0.4")
    config["Port"].should.equal("80")
    config["RequestInterval"].should.equal("10")
    config["ResourcePath"].should.equal("/")
    config["Type"].should.equal("HTTP")

    zones = route53_conn.get_all_hosted_zones()['ListHostedZonesResponse']['HostedZones']
    list(zones).should.have.length_of(1)
    zone_id = zones[0]['Id']
    zone_id = zone_id.split('/')
    zone_id = zone_id[2]

    rrsets = route53_conn.get_all_rrsets(zone_id)
    rrsets.should.have.length_of(1)

    record_set = rrsets[0]
    record_set.health_check.should.equal(health_check_id)


@mock_cloudformation()
@mock_route53()
def test_route53_with_update():
    route53_conn = boto.connect_route53()

    template_json = json.dumps(route53_health_check.template)
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    zones = route53_conn.get_all_hosted_zones()['ListHostedZonesResponse']['HostedZones']
    list(zones).should.have.length_of(1)
    zone_id = zones[0]['Id']
    zone_id = zone_id.split('/')
    zone_id = zone_id[2]

    rrsets = route53_conn.get_all_rrsets(zone_id)
    rrsets.should.have.length_of(1)

    record_set = rrsets[0]
    record_set.resource_records.should.equal(["my.example.com"])

    route53_health_check.template['Resources']['myDNSRecord']['Properties']['ResourceRecords'] = ["my_other.example.com"]
    template_json = json.dumps(route53_health_check.template)
    cf_conn.update_stack(
        "test_stack",
        template_body=template_json,
    )

    zones = route53_conn.get_all_hosted_zones()['ListHostedZonesResponse']['HostedZones']
    list(zones).should.have.length_of(1)
    zone_id = zones[0]['Id']
    zone_id = zone_id.split('/')
    zone_id = zone_id[2]

    rrsets = route53_conn.get_all_rrsets(zone_id)
    rrsets.should.have.length_of(1)

    record_set = rrsets[0]
    record_set.resource_records.should.equal(["my_other.example.com"])


@mock_cloudformation()
@mock_sns()
def test_sns_topic():
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MySNSTopic": {
                "Type": "AWS::SNS::Topic",
                "Properties": {
                    "Subscription": [
                        {"Endpoint": "https://example.com", "Protocol": "https"},
                    ],
                    "TopicName": "my_topics",
                }
            }
        },
        "Outputs": {
            "topic_name": {
                "Value": {"Fn::GetAtt": ["MySNSTopic", "TopicName"]}
            },
            "topic_arn": {
                "Value": {"Ref": "MySNSTopic"}
            },
        }
    }
    template_json = json.dumps(dummy_template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    stack = conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    sns_conn = boto.sns.connect_to_region("us-west-1")
    topics = sns_conn.get_all_topics()["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    topics.should.have.length_of(1)
    topic_arn = topics[0]['TopicArn']
    topic_arn.should.contain("my_topics")

    subscriptions = sns_conn.get_all_subscriptions()["ListSubscriptionsResponse"]["ListSubscriptionsResult"]["Subscriptions"]
    subscriptions.should.have.length_of(1)
    subscription = subscriptions[0]
    subscription["TopicArn"].should.equal(topic_arn)
    subscription["Protocol"].should.equal("https")
    subscription["SubscriptionArn"].should.contain(topic_arn)
    subscription["Endpoint"].should.equal("https://example.com")

    stack = conn.describe_stacks()[0]
    topic_name_output = [x for x in stack.outputs if x.key == 'topic_name'][0]
    topic_name_output.value.should.equal("my_topics")
    topic_arn_output = [x for x in stack.outputs if x.key == 'topic_arn'][0]
    topic_arn_output.value.should.equal(topic_arn)


@mock_cloudformation
@mock_ec2
def test_vpc_gateway_attachment_creation_should_attach_itself_to_vpc():
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "internetgateway": {
                "Type": "AWS::EC2::InternetGateway"
            },
            "testvpc": {
                "Type": "AWS::EC2::VPC",
                "Properties": {
                    "CidrBlock": "10.0.0.0/16",
                    "EnableDnsHostnames": "true",
                    "EnableDnsSupport": "true",
                    "InstanceTenancy": "default"
                },
            },
            "vpcgatewayattachment": {
                "Type": "AWS::EC2::VPCGatewayAttachment",
                "Properties": {
                    "InternetGatewayId": {
                        "Ref": "internetgateway"
                    },
                    "VpcId": {
                        "Ref": "testvpc"
                    }
                },
            },
        }
    }

    template_json = json.dumps(template)
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    vpc_conn = boto.vpc.connect_to_region("us-west-1")
    vpc = vpc_conn.get_all_vpcs(filters={'cidrBlock': '10.0.0.0/16'})[0]
    igws = vpc_conn.get_all_internet_gateways(
        filters={'attachment.vpc-id': vpc.id}
    )

    igws.should.have.length_of(1)


@mock_cloudformation
@mock_ec2
def test_vpc_peering_creation():
    vpc_conn = boto.vpc.connect_to_region("us-west-1")
    vpc_source = vpc_conn.create_vpc("10.0.0.0/16")
    peer_vpc = vpc_conn.create_vpc("10.1.0.0/16")
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "vpcpeeringconnection": {
                "Type": "AWS::EC2::VPCPeeringConnection",
                "Properties": {
                    "PeerVpcId": peer_vpc.id,
                    "VpcId": vpc_source.id,
                }
            },
        }
    }

    template_json = json.dumps(template)
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    peering_connections = vpc_conn.get_all_vpc_peering_connections()
    peering_connections.should.have.length_of(1)


@mock_cloudformation
@mock_ec2
def test_multiple_security_group_ingress_separate_from_security_group_by_id():
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group1": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "Tags": [
                        {
                            "Key": "sg-name",
                            "Value": "sg1"
                        }
                    ]
                },
            },
            "test-security-group2": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "Tags": [
                        {
                            "Key": "sg-name",
                            "Value": "sg2"
                        }
                    ]
                },
            },
            "test-sg-ingress": {
                "Type": "AWS::EC2::SecurityGroupIngress",
                "Properties": {
                    "GroupId": {"Ref": "test-security-group1"},
                    "IpProtocol": "tcp",
                    "FromPort": "80",
                    "ToPort": "8080",
                    "SourceSecurityGroupId": {"Ref": "test-security-group2"},
                }
            }
        }
    }

    template_json = json.dumps(template)
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )
    ec2_conn = boto.ec2.connect_to_region("us-west-1")

    security_group1 = ec2_conn.get_all_security_groups(filters={"tag:sg-name": "sg1"})[0]
    security_group2 = ec2_conn.get_all_security_groups(filters={"tag:sg-name": "sg2"})[0]

    security_group1.rules.should.have.length_of(1)
    security_group1.rules[0].grants.should.have.length_of(1)
    security_group1.rules[0].grants[0].group_id.should.equal(security_group2.id)
    security_group1.rules[0].ip_protocol.should.equal('tcp')
    security_group1.rules[0].from_port.should.equal('80')
    security_group1.rules[0].to_port.should.equal('8080')


@mock_cloudformation
@mock_ec2
def test_security_group_ingress_separate_from_security_group_by_id():
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    ec2_conn.create_security_group("test-security-group1", "test security group")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group2": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "Tags": [
                        {
                            "Key": "sg-name",
                            "Value": "sg2"
                        }
                    ]
                },
            },
            "test-sg-ingress": {
                "Type": "AWS::EC2::SecurityGroupIngress",
                "Properties": {
                    "GroupName": "test-security-group1",
                    "IpProtocol": "tcp",
                    "FromPort": "80",
                    "ToPort": "8080",
                    "SourceSecurityGroupId": {"Ref": "test-security-group2"},
                }
            }
        }
    }

    template_json = json.dumps(template)
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )
    security_group1 = ec2_conn.get_all_security_groups(groupnames=["test-security-group1"])[0]
    security_group2 = ec2_conn.get_all_security_groups(filters={"tag:sg-name": "sg2"})[0]

    security_group1.rules.should.have.length_of(1)
    security_group1.rules[0].grants.should.have.length_of(1)
    security_group1.rules[0].grants[0].group_id.should.equal(security_group2.id)
    security_group1.rules[0].ip_protocol.should.equal('tcp')
    security_group1.rules[0].from_port.should.equal('80')
    security_group1.rules[0].to_port.should.equal('8080')


@mock_cloudformation
@mock_ec2
def test_security_group_ingress_separate_from_security_group_by_id_using_vpc():
    vpc_conn = boto.vpc.connect_to_region("us-west-1")
    vpc = vpc_conn.create_vpc("10.0.0.0/16")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group1": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "VpcId": vpc.id,
                    "Tags": [
                        {
                            "Key": "sg-name",
                            "Value": "sg1"
                        }
                    ]
                },
            },
            "test-security-group2": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "VpcId": vpc.id,
                    "Tags": [
                        {
                            "Key": "sg-name",
                            "Value": "sg2"
                        }
                    ]
                },
            },
            "test-sg-ingress": {
                "Type": "AWS::EC2::SecurityGroupIngress",
                "Properties": {
                    "GroupId": {"Ref": "test-security-group1"},
                    "VpcId": vpc.id,
                    "IpProtocol": "tcp",
                    "FromPort": "80",
                    "ToPort": "8080",
                    "SourceSecurityGroupId": {"Ref": "test-security-group2"},
                }
            }
        }
    }

    template_json = json.dumps(template)
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )
    security_group1 = vpc_conn.get_all_security_groups(filters={"tag:sg-name": "sg1"})[0]
    security_group2 = vpc_conn.get_all_security_groups(filters={"tag:sg-name": "sg2"})[0]

    security_group1.rules.should.have.length_of(1)
    security_group1.rules[0].grants.should.have.length_of(1)
    security_group1.rules[0].grants[0].group_id.should.equal(security_group2.id)
    security_group1.rules[0].ip_protocol.should.equal('tcp')
    security_group1.rules[0].from_port.should.equal('80')
    security_group1.rules[0].to_port.should.equal('8080')


@mock_cloudformation
@mock_ec2
def test_security_group_with_update():
    vpc_conn = boto.vpc.connect_to_region("us-west-1")
    vpc1 = vpc_conn.create_vpc("10.0.0.0/16")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "VpcId": vpc1.id,
                    "Tags": [
                        {
                            "Key": "sg-name",
                            "Value": "sg"
                        }
                    ]
                },
            },
        }
    }

    template_json = json.dumps(template)
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )
    security_group = vpc_conn.get_all_security_groups(filters={"tag:sg-name": "sg"})[0]
    security_group.vpc_id.should.equal(vpc1.id)

    vpc2 = vpc_conn.create_vpc("10.1.0.0/16")
    template['Resources']['test-security-group']['Properties']['VpcId'] = vpc2.id
    template_json = json.dumps(template)
    cf_conn.update_stack(
        "test_stack",
        template_body=template_json,
    )
    security_group = vpc_conn.get_all_security_groups(filters={"tag:sg-name": "sg"})[0]
    security_group.vpc_id.should.equal(vpc2.id)


@mock_cloudformation
@mock_ec2
def test_subnets_should_be_created_with_availability_zone():
    vpc_conn = boto.vpc.connect_to_region('us-west-1')
    vpc = vpc_conn.create_vpc("10.0.0.0/16")

    subnet_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testSubnet": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "VpcId": vpc.id,
                    "CidrBlock": "10.0.0.0/24",
                    "AvailabilityZone": "us-west-1b",
                }
            }
        }
    }
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    template_json = json.dumps(subnet_template)
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )
    subnet = vpc_conn.get_all_subnets(filters={'cidrBlock': '10.0.0.0/24'})[0]
    subnet.availability_zone.should.equal('us-west-1b')


@mock_cloudformation
@mock_datapipeline
def test_datapipeline():
    dp_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "dataPipeline": {
                "Properties": {
                    "Activate": "true",
                    "Name": "testDataPipeline",
                    "PipelineObjects": [
                        {
                            "Fields": [
                                {
                                    "Key": "failureAndRerunMode",
                                    "StringValue": "CASCADE"
                                },
                                {
                                    "Key": "scheduleType",
                                    "StringValue": "cron"
                                },
                                {
                                    "Key": "schedule",
                                    "RefValue": "DefaultSchedule"
                                },
                                {
                                    "Key": "pipelineLogUri",
                                    "StringValue": "s3://bucket/logs"
                                },
                                {
                                    "Key": "type",
                                    "StringValue": "Default"
                                },
                            ],
                            "Id": "Default",
                            "Name": "Default"
                        },
                        {
                            "Fields": [
                                {
                                    "Key": "startDateTime",
                                    "StringValue": "1970-01-01T01:00:00"
                                },
                                {
                                    "Key": "period",
                                    "StringValue": "1 Day"
                                },
                                {
                                    "Key": "type",
                                    "StringValue": "Schedule"
                                }
                            ],
                            "Id": "DefaultSchedule",
                            "Name": "RunOnce"
                        }
                    ],
                    "PipelineTags": []
                },
                "Type": "AWS::DataPipeline::Pipeline"
            }
        }
    }
    cf_conn = boto.cloudformation.connect_to_region("us-east-1")
    template_json = json.dumps(dp_template)
    stack_id = cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    dp_conn = boto.datapipeline.connect_to_region('us-east-1')
    data_pipelines = dp_conn.list_pipelines()

    data_pipelines['pipelineIdList'].should.have.length_of(1)
    data_pipelines['pipelineIdList'][0]['name'].should.equal('testDataPipeline')

    stack_resources = cf_conn.list_stack_resources(stack_id)
    stack_resources.should.have.length_of(1)
    stack_resources[0].physical_resource_id.should.equal(data_pipelines['pipelineIdList'][0]['id'])

def _process_lamda(pfunc):
    import io
    import zipfile
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED)
    zip_file.writestr('lambda_function.zip', pfunc)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def get_test_zip_file1():
    pfunc = """
def lambda_handler(event, context):
    return (event, context)
"""
    return _process_lamda(pfunc)


@mock_cloudformation
@mock_lambda
def test_lambda_function():
    # switch this to python as backend lambda only supports python execution.
    conn = boto3.client('lambda', 'us-east-1')
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "lambdaTest": {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "Code": {
                        "ZipFile": base64.b64encode(get_test_zip_file1()).decode('utf-8')
                    },
                    "Handler": "lambda_function.handler",
                    "Description": "Test function",
                    "MemorySize": 128,
                    "Role": "test-role",
                    "Runtime": "python2.7"
                }
            }
        }
    }

    template_json = json.dumps(template)
    cf_conn = boto.cloudformation.connect_to_region("us-east-1")
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    result = conn.list_functions()
    result['Functions'].should.have.length_of(1)
    result['Functions'][0]['Description'].should.equal('Test function')
    result['Functions'][0]['Handler'].should.equal('lambda_function.handler')
    result['Functions'][0]['MemorySize'].should.equal(128)
    result['Functions'][0]['Role'].should.equal('test-role')
    result['Functions'][0]['Runtime'].should.equal('python2.7')


@mock_cloudformation
@mock_ec2
def test_nat_gateway():
    ec2_conn = boto3.client('ec2', 'us-east-1')
    vpc_id = ec2_conn.create_vpc(CidrBlock="10.0.0.0/16")['Vpc']['VpcId']
    subnet_id = ec2_conn.create_subnet(CidrBlock='10.0.1.0/24', VpcId=vpc_id)['Subnet']['SubnetId']
    route_table_id = ec2_conn.create_route_table(VpcId=vpc_id)['RouteTable']['RouteTableId']

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "NAT" : {
                "DependsOn" : "vpcgatewayattachment",
                "Type" : "AWS::EC2::NatGateway",
                "Properties" : {
                    "AllocationId" : { "Fn::GetAtt" : ["EIP", "AllocationId"]},
                    "SubnetId" : subnet_id
                    }
            },
            "EIP" : {
                "Type" : "AWS::EC2::EIP",
                "Properties" : {
                    "Domain" : "vpc"
                }
            },
            "Route" : {
                "Type" : "AWS::EC2::Route",
                "Properties" : {
                    "RouteTableId" : route_table_id,
                    "DestinationCidrBlock" : "0.0.0.0/0",
                    "NatGatewayId" : { "Ref" : "NAT" }
              }
            },
            "internetgateway": {
                "Type": "AWS::EC2::InternetGateway"
            },
            "vpcgatewayattachment": {
                "Type": "AWS::EC2::VPCGatewayAttachment",
                "Properties": {
                    "InternetGatewayId": {
                        "Ref": "internetgateway"
                    },
                    "VpcId": vpc_id,
                },
            }
        }
    }

    cf_conn = boto3.client('cloudformation', 'us-east-1')
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=json.dumps(template),
    )

    result = ec2_conn.describe_nat_gateways()

    result['NatGateways'].should.have.length_of(1)
    result['NatGateways'][0]['VpcId'].should.equal(vpc_id)
    result['NatGateways'][0]['SubnetId'].should.equal(subnet_id)
    result['NatGateways'][0]['State'].should.equal('available')

@mock_cloudformation()
@mock_kms()
def test_stack_kms():
    kms_key_template = {
        'Resources': {
            'kmskey': {
                'Properties': {
                    'Description': 'A kms key',
                    'EnableKeyRotation': True,
                    'Enabled': True,
                    'KeyPolicy': 'a policy',
                },
                'Type': 'AWS::KMS::Key'
            }
        }
    }
    kms_key_template_json = json.dumps(kms_key_template)

    cf_conn = boto3.client('cloudformation', 'us-east-1')
    cf_conn.create_stack(
        StackName='test_stack',
        TemplateBody=kms_key_template_json,
    )

    kms_conn = boto3.client('kms', 'us-east-1')
    keys = kms_conn.list_keys()['Keys']
    len(keys).should.equal(1)
    result = kms_conn.describe_key(KeyId=keys[0]['KeyId'])

    result['KeyMetadata']['Enabled'].should.equal(True)
    result['KeyMetadata']['KeyUsage'].should.equal('ENCRYPT_DECRYPT')


@mock_cloudformation()
@mock_ec2()
def test_stack_spot_fleet():
    conn = boto3.client('ec2', 'us-east-1')

    vpc = conn.create_vpc(CidrBlock="10.0.0.0/8")['Vpc']
    subnet = conn.create_subnet(VpcId=vpc['VpcId'], CidrBlock='10.0.0.0/16', AvailabilityZone='us-east-1a')['Subnet']
    subnet_id = subnet['SubnetId']

    spot_fleet_template = {
        'Resources': {
            "SpotFleet": {
              "Type": "AWS::EC2::SpotFleet",
              "Properties": {
                "SpotFleetRequestConfigData": {
                  "IamFleetRole": "arn:aws:iam::123456789012:role/fleet",
                  "SpotPrice": "0.12",
                  "TargetCapacity": 6,
                  "AllocationStrategy": "diversified",
                  "LaunchSpecifications": [
                  {
                    "EbsOptimized": "false",
                    "InstanceType": 't2.small',
                    "ImageId": "ami-1234",
                    "SubnetId": subnet_id,
                    "WeightedCapacity": "2",
                    "SpotPrice": "0.13",
                  },
                  {
                    "EbsOptimized": "true",
                    "InstanceType": 't2.large',
                    "ImageId": "ami-1234",
                    "Monitoring": { "Enabled": "true" },
                    "SecurityGroups": [{"GroupId": "sg-123"}],
                    "SubnetId": subnet_id,
                    "IamInstanceProfile": {"Arn": "arn:aws:iam::123456789012:role/fleet"},
                    "WeightedCapacity": "4",
                    "SpotPrice": "10.00",
                  }
                  ]
                }
              }
            }
        }
    }
    spot_fleet_template_json = json.dumps(spot_fleet_template)

    cf_conn = boto3.client('cloudformation', 'us-east-1')
    stack_id = cf_conn.create_stack(
        StackName='test_stack',
        TemplateBody=spot_fleet_template_json,
    )['StackId']

    stack_resources = cf_conn.list_stack_resources(StackName=stack_id)
    stack_resources['StackResourceSummaries'].should.have.length_of(1)
    spot_fleet_id = stack_resources['StackResourceSummaries'][0]['PhysicalResourceId']

    spot_fleet_requests = conn.describe_spot_fleet_requests(SpotFleetRequestIds=[spot_fleet_id])['SpotFleetRequestConfigs']
    len(spot_fleet_requests).should.equal(1)
    spot_fleet_request = spot_fleet_requests[0]
    spot_fleet_request['SpotFleetRequestState'].should.equal("active")
    spot_fleet_config = spot_fleet_request['SpotFleetRequestConfig']

    spot_fleet_config['SpotPrice'].should.equal('0.12')
    spot_fleet_config['TargetCapacity'].should.equal(6)
    spot_fleet_config['IamFleetRole'].should.equal('arn:aws:iam::123456789012:role/fleet')
    spot_fleet_config['AllocationStrategy'].should.equal('diversified')
    spot_fleet_config['FulfilledCapacity'].should.equal(6.0)

    len(spot_fleet_config['LaunchSpecifications']).should.equal(2)
    launch_spec = spot_fleet_config['LaunchSpecifications'][0]

    launch_spec['EbsOptimized'].should.equal(False)
    launch_spec['ImageId'].should.equal("ami-1234")
    launch_spec['InstanceType'].should.equal("t2.small")
    launch_spec['SubnetId'].should.equal(subnet_id)
    launch_spec['SpotPrice'].should.equal("0.13")
    launch_spec['WeightedCapacity'].should.equal(2.0)
