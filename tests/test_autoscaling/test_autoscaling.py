from __future__ import unicode_literals
import boto
import boto3
import boto.ec2.autoscale
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.group import AutoScalingGroup
from boto.ec2.autoscale import Tag
import boto.ec2.elb
import sure  # noqa

from moto import mock_autoscaling, mock_ec2_deprecated, mock_elb_deprecated, mock_elb, mock_autoscaling_deprecated, mock_ec2
from tests.helpers import requires_boto_gte

from utils import setup_networking, setup_networking_deprecated


@mock_autoscaling_deprecated
@mock_elb_deprecated
def test_create_autoscaling_group():
    mocked_networking = setup_networking_deprecated()
    elb_conn = boto.ec2.elb.connect_to_region('us-east-1')
    elb_conn.create_load_balancer(
        'test_lb', zones=[], listeners=[(80, 8080, 'http')])

    conn = boto.ec2.autoscale.connect_to_region('us-east-1')
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1a', 'us-east-1b'],
        default_cooldown=60,
        desired_capacity=2,
        health_check_period=100,
        health_check_type="EC2",
        max_size=2,
        min_size=2,
        launch_config=config,
        load_balancers=["test_lb"],
        placement_group="test_placement",
        vpc_zone_identifier="{subnet1},{subnet2}".format(
            subnet1=mocked_networking['subnet1'],
            subnet2=mocked_networking['subnet2'],
        ),
        termination_policies=["OldestInstance", "NewestInstance"],
        tags=[Tag(
            resource_id='tester_group',
            key='test_key',
            value='test_value',
            propagate_at_launch=True
        )
        ],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.name.should.equal('tester_group')
    set(group.availability_zones).should.equal(
        set(['us-east-1a', 'us-east-1b']))
    group.desired_capacity.should.equal(2)
    group.max_size.should.equal(2)
    group.min_size.should.equal(2)
    group.instances.should.have.length_of(2)
    group.vpc_zone_identifier.should.equal("{subnet1},{subnet2}".format(
        subnet1=mocked_networking['subnet1'],
        subnet2=mocked_networking['subnet2'],
    ))
    group.launch_config_name.should.equal('tester')
    group.default_cooldown.should.equal(60)
    group.health_check_period.should.equal(100)
    group.health_check_type.should.equal("EC2")
    list(group.load_balancers).should.equal(["test_lb"])
    group.placement_group.should.equal("test_placement")
    list(group.termination_policies).should.equal(
        ["OldestInstance", "NewestInstance"])
    len(list(group.tags)).should.equal(1)
    tag = list(group.tags)[0]
    tag.resource_id.should.equal('tester_group')
    tag.key.should.equal('test_key')
    tag.value.should.equal('test_value')
    tag.propagate_at_launch.should.equal(True)


@mock_autoscaling_deprecated
def test_create_autoscaling_groups_defaults():
    """ Test with the minimum inputs and check that all of the proper defaults
    are assigned for the other attributes """

    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.name.should.equal('tester_group')
    group.max_size.should.equal(2)
    group.min_size.should.equal(2)
    group.launch_config_name.should.equal('tester')

    # Defaults
    list(group.availability_zones).should.equal(['us-east-1a'])  # subnet1
    group.desired_capacity.should.equal(2)
    group.vpc_zone_identifier.should.equal(mocked_networking['subnet1'])
    group.default_cooldown.should.equal(300)
    group.health_check_period.should.equal(300)
    group.health_check_type.should.equal("EC2")
    list(group.load_balancers).should.equal([])
    group.placement_group.should.equal(None)
    list(group.termination_policies).should.equal([])
    list(group.tags).should.equal([])


@mock_autoscaling
def test_list_many_autoscaling_groups():
    mocked_networking = setup_networking()
    conn = boto3.client('autoscaling', region_name='us-east-1')
    conn.create_launch_configuration(LaunchConfigurationName='TestLC')

    for i in range(51):
        conn.create_auto_scaling_group(AutoScalingGroupName='TestGroup%d' % i,
                                       MinSize=1,
                                       MaxSize=2,
                                       LaunchConfigurationName='TestLC',
                                       VPCZoneIdentifier=mocked_networking['subnet1'])

    response = conn.describe_auto_scaling_groups()
    groups = response["AutoScalingGroups"]
    marker = response["NextToken"]
    groups.should.have.length_of(50)
    marker.should.equal(groups[-1]['AutoScalingGroupName'])

    response2 = conn.describe_auto_scaling_groups(NextToken=marker)

    groups.extend(response2["AutoScalingGroups"])
    groups.should.have.length_of(51)
    assert 'NextToken' not in response2.keys()


@mock_autoscaling
@mock_ec2
def test_list_many_autoscaling_groups():
    mocked_networking = setup_networking()
    conn = boto3.client('autoscaling', region_name='us-east-1')
    conn.create_launch_configuration(LaunchConfigurationName='TestLC')

    conn.create_auto_scaling_group(AutoScalingGroupName='TestGroup1',
                                   MinSize=1,
                                   MaxSize=2,
                                   LaunchConfigurationName='TestLC',
                                   Tags=[{
                                       "ResourceId": 'TestGroup1',
                                       "ResourceType": "auto-scaling-group",
                                       "PropagateAtLaunch": True,
                                       "Key": 'TestTagKey1',
                                       "Value": 'TestTagValue1'
                                   }],
                                   VPCZoneIdentifier=mocked_networking['subnet1'])

    ec2 = boto3.client('ec2', region_name='us-east-1')
    instances = ec2.describe_instances()

    tags = instances['Reservations'][0]['Instances'][0]['Tags']
    tags.should.contain({u'Value': 'TestTagValue1', u'Key': 'TestTagKey1'})
    tags.should.contain({u'Value': 'TestGroup1', u'Key': 'aws:autoscaling:groupName'})


@mock_autoscaling_deprecated
def test_autoscaling_group_describe_filter():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)
    group.name = 'tester_group2'
    conn.create_auto_scaling_group(group)
    group.name = 'tester_group3'
    conn.create_auto_scaling_group(group)

    conn.get_all_groups(
        names=['tester_group', 'tester_group2']).should.have.length_of(2)
    conn.get_all_groups().should.have.length_of(3)


@mock_autoscaling_deprecated
def test_autoscaling_update():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.availability_zones.should.equal(['us-east-1a'])
    group.vpc_zone_identifier.should.equal(mocked_networking['subnet1'])

    group.availability_zones = ['us-east-1b']
    group.vpc_zone_identifier = mocked_networking['subnet2']
    group.update()

    group = conn.get_all_groups()[0]
    group.availability_zones.should.equal(['us-east-1b'])
    group.vpc_zone_identifier.should.equal(mocked_networking['subnet2'])


@mock_autoscaling_deprecated
def test_autoscaling_tags_update():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1a'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        tags=[Tag(
            resource_id='tester_group',
            key='test_key',
            value='test_value',
            propagate_at_launch=True
        )],
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)

    conn.create_or_update_tags(tags=[Tag(
        resource_id='tester_group',
        key='test_key',
        value='new_test_value',
        propagate_at_launch=True
    ), Tag(
        resource_id='tester_group',
        key='test_key2',
        value='test_value2',
        propagate_at_launch=True
    )])
    group = conn.get_all_groups()[0]
    group.tags.should.have.length_of(2)


@mock_autoscaling_deprecated
def test_autoscaling_group_delete():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)

    conn.get_all_groups().should.have.length_of(1)

    conn.delete_auto_scaling_group('tester_group')
    conn.get_all_groups().should.have.length_of(0)


@mock_ec2_deprecated
@mock_autoscaling_deprecated
def test_autoscaling_group_describe_instances():
    mocked_networking = setup_networking_deprecated()
    conn = boto.ec2.autoscale.connect_to_region('us-east-1')
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)
    instances[0].launch_config_name.should.equal('tester')
    instances[0].health_status.should.equal('Healthy')
    autoscale_instance_ids = [instance.instance_id for instance in instances]

    ec2_conn = boto.ec2.connect_to_region('us-east-1')
    reservations = ec2_conn.get_all_instances()
    instances = reservations[0].instances
    instances.should.have.length_of(2)
    instance_ids = [instance.id for instance in instances]
    set(autoscale_instance_ids).should.equal(set(instance_ids))
    instances[0].instance_type.should.equal("t2.medium")


@requires_boto_gte("2.8")
@mock_autoscaling_deprecated
def test_set_desired_capacity_up():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1a'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)
    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

    conn.set_desired_capacity("tester_group", 3)
    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(3)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(3)


@requires_boto_gte("2.8")
@mock_autoscaling_deprecated
def test_set_desired_capacity_down():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1a'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)
    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

    conn.set_desired_capacity("tester_group", 1)
    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(1)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(1)


@requires_boto_gte("2.8")
@mock_autoscaling_deprecated
def test_set_desired_capacity_the_same():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1a'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)
    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

    conn.set_desired_capacity("tester_group", 2)
    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)


@mock_autoscaling_deprecated
@mock_elb_deprecated
def test_autoscaling_group_with_elb():
    mocked_networking = setup_networking_deprecated()
    elb_conn = boto.connect_elb()
    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = elb_conn.create_load_balancer('my-lb', zones, ports)
    instances_health = elb_conn.describe_instance_health('my-lb')
    instances_health.should.be.empty

    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t2.medium',
    )
    conn.create_launch_configuration(config)
    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
        load_balancers=["my-lb"],
        vpc_zone_identifier=mocked_networking['subnet1'],
    )
    conn.create_auto_scaling_group(group)
    group = conn.get_all_groups()[0]
    elb = elb_conn.get_all_load_balancers()[0]
    group.desired_capacity.should.equal(2)
    elb.instances.should.have.length_of(2)

    autoscale_instance_ids = set(
        instance.instance_id for instance in group.instances)
    elb_instace_ids = set(instance.id for instance in elb.instances)
    autoscale_instance_ids.should.equal(elb_instace_ids)

    conn.set_desired_capacity("tester_group", 3)
    group = conn.get_all_groups()[0]
    elb = elb_conn.get_all_load_balancers()[0]
    group.desired_capacity.should.equal(3)
    elb.instances.should.have.length_of(3)

    autoscale_instance_ids = set(
        instance.instance_id for instance in group.instances)
    elb_instace_ids = set(instance.id for instance in elb.instances)
    autoscale_instance_ids.should.equal(elb_instace_ids)

    conn.delete_auto_scaling_group('tester_group')
    conn.get_all_groups().should.have.length_of(0)
    elb = elb_conn.get_all_load_balancers()[0]
    elb.instances.should.have.length_of(0)


'''
Boto3
'''


@mock_autoscaling
@mock_elb
def test_describe_load_balancers():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2

    elb_client = boto3.client('elb', region_name='us-east-1')
    elb_client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )

    client = boto3.client('autoscaling', region_name='us-east-1')
    client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        LoadBalancerNames=['my-lb'],
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        Tags=[{
            "ResourceId": 'test_asg',
            "Key": 'test_key',
            "Value": 'test_value',
            "PropagateAtLaunch": True
        }],
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )

    response = client.describe_load_balancers(AutoScalingGroupName='test_asg')
    assert response['ResponseMetadata']['RequestId']
    list(response['LoadBalancers']).should.have.length_of(1)
    response['LoadBalancers'][0]['LoadBalancerName'].should.equal('my-lb')

@mock_autoscaling
@mock_elb
def test_create_elb_and_autoscaling_group_no_relationship():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2
    ELB_NAME = 'my-elb'

    elb_client = boto3.client('elb', region_name='us-east-1')
    elb_client.create_load_balancer(
        LoadBalancerName=ELB_NAME,
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )

    client = boto3.client('autoscaling', region_name='us-east-1')
    client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )

    client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )

    # autoscaling group and elb should have no relationship
    response = client.describe_load_balancers(
        AutoScalingGroupName='test_asg'
    )
    list(response['LoadBalancers']).should.have.length_of(0)
    response = elb_client.describe_load_balancers(
        LoadBalancerNames=[ELB_NAME]
    )
    list(response['LoadBalancerDescriptions'][0]['Instances']).should.have.length_of(0)


@mock_autoscaling
@mock_elb
def test_attach_load_balancer():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2

    elb_client = boto3.client('elb', region_name='us-east-1')
    elb_client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )

    client = boto3.client('autoscaling', region_name='us-east-1')
    client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        Tags=[{
            "ResourceId": 'test_asg',
            "Key": 'test_key',
            "Value": 'test_value',
            "PropagateAtLaunch": True
        }],
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName='test_asg',
        LoadBalancerNames=['my-lb'])
    response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)

    response = elb_client.describe_load_balancers(
        LoadBalancerNames=['my-lb']
    )
    list(response['LoadBalancerDescriptions'][0]['Instances']).should.have.length_of(INSTANCE_COUNT)

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=["test_asg"]
    )
    list(response['AutoScalingGroups'][0]['LoadBalancerNames']).should.have.length_of(1)


@mock_autoscaling
@mock_elb
def test_detach_load_balancer():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2

    elb_client = boto3.client('elb', region_name='us-east-1')
    elb_client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )

    client = boto3.client('autoscaling', region_name='us-east-1')
    client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        LoadBalancerNames=['my-lb'],
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        Tags=[{
            "ResourceId": 'test_asg',
            "Key": 'test_key',
            "Value": 'test_value',
            "PropagateAtLaunch": True
        }],
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )

    response = client.detach_load_balancers(
        AutoScalingGroupName='test_asg',
        LoadBalancerNames=['my-lb'])
    response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)

    response = elb_client.describe_load_balancers(
        LoadBalancerNames=['my-lb']
    )
    list(response['LoadBalancerDescriptions'][0]['Instances']).should.have.length_of(0)

    response = client.describe_load_balancers(AutoScalingGroupName='test_asg')
    list(response['LoadBalancers']).should.have.length_of(0)


@mock_autoscaling
def test_create_autoscaling_group_boto3():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    response = client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[
            {'ResourceId': 'test_asg',
             'ResourceType': 'auto-scaling-group',
             'Key': 'propogated-tag-key',
             'Value': 'propogate-tag-value',
             'PropagateAtLaunch': True
             },
            {'ResourceId': 'test_asg',
             'ResourceType': 'auto-scaling-group',
             'Key': 'not-propogated-tag-key',
             'Value': 'not-propogate-tag-value',
             'PropagateAtLaunch': False
             }],
        VPCZoneIdentifier=mocked_networking['subnet1'],
        NewInstancesProtectedFromScaleIn=False,
    )
    response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)


@mock_autoscaling
def test_describe_autoscaling_groups_boto3():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking['subnet1'],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=["test_asg"]
    )
    response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)
    group = response['AutoScalingGroups'][0]
    group['AutoScalingGroupName'].should.equal('test_asg')
    group['AvailabilityZones'].should.equal(['us-east-1a'])
    group['VPCZoneIdentifier'].should.equal(mocked_networking['subnet1'])
    group['NewInstancesProtectedFromScaleIn'].should.equal(True)
    for instance in group['Instances']:
        instance['AvailabilityZone'].should.equal('us-east-1a')
        instance['ProtectedFromScaleIn'].should.equal(True)


@mock_autoscaling
def test_describe_autoscaling_instances_boto3():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking['subnet1'],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=["test_asg"]
    )
    instance_ids = [
        instance['InstanceId']
        for instance in response['AutoScalingGroups'][0]['Instances']
    ]

    response = client.describe_auto_scaling_instances(InstanceIds=instance_ids)
    for instance in response['AutoScalingInstances']:
        instance['AutoScalingGroupName'].should.equal('test_asg')
        instance['AvailabilityZone'].should.equal('us-east-1a')
        instance['ProtectedFromScaleIn'].should.equal(True)


@mock_autoscaling
def test_update_autoscaling_group_boto3():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking['subnet1'],
        NewInstancesProtectedFromScaleIn=True,
    )

    _ = client.update_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        MinSize=1,
        VPCZoneIdentifier="{subnet1},{subnet2}".format(
            subnet1=mocked_networking['subnet1'],
            subnet2=mocked_networking['subnet2'],
        ),
        NewInstancesProtectedFromScaleIn=False,
    )

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=["test_asg"]
    )
    group = response['AutoScalingGroups'][0]
    group['MinSize'].should.equal(1)
    set(group['AvailabilityZones']).should.equal({'us-east-1a', 'us-east-1b'})
    group['NewInstancesProtectedFromScaleIn'].should.equal(False)


@mock_autoscaling
def test_autoscaling_taqs_update_boto3():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[{
            "ResourceId": 'test_asg',
            "Key": 'test_key',
            "Value": 'test_value',
            "PropagateAtLaunch": True
        }],
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )

    client.create_or_update_tags(Tags=[{
        "ResourceId": 'test_asg',
        "Key": 'test_key',
        "Value": 'updated_test_value',
        "PropagateAtLaunch": True
    }, {
        "ResourceId": 'test_asg',
        "Key": 'test_key2',
        "Value": 'test_value2',
        "PropagateAtLaunch": False
    }])

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=["test_asg"]
    )
    response['AutoScalingGroups'][0]['Tags'].should.have.length_of(2)


@mock_autoscaling
def test_autoscaling_describe_policies_boto3():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[{
            "ResourceId": 'test_asg',
            "Key": 'test_key',
            "Value": 'test_value',
            "PropagateAtLaunch": True
        }],
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )

    client.put_scaling_policy(
        AutoScalingGroupName='test_asg',
        PolicyName='test_policy_down',
        PolicyType='SimpleScaling',
        AdjustmentType='PercentChangeInCapacity',
        ScalingAdjustment=-10,
        Cooldown=60,
        MinAdjustmentMagnitude=1)
    client.put_scaling_policy(
        AutoScalingGroupName='test_asg',
        PolicyName='test_policy_up',
        PolicyType='SimpleScaling',
        AdjustmentType='PercentChangeInCapacity',
        ScalingAdjustment=10,
        Cooldown=60,
        MinAdjustmentMagnitude=1)

    response = client.describe_policies()
    response['ScalingPolicies'].should.have.length_of(2)

    response = client.describe_policies(AutoScalingGroupName='test_asg')
    response['ScalingPolicies'].should.have.length_of(2)

    response = client.describe_policies(PolicyTypes=['StepScaling'])
    response['ScalingPolicies'].should.have.length_of(0)

    response = client.describe_policies(
        AutoScalingGroupName='test_asg',
        PolicyNames=['test_policy_down'],
        PolicyTypes=['SimpleScaling']
    )
    response['ScalingPolicies'].should.have.length_of(1)
    response['ScalingPolicies'][0][
        'PolicyName'].should.equal('test_policy_down')

@mock_autoscaling
@mock_ec2
def test_detach_one_instance_decrement():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=2,
        Tags=[{
            'ResourceId': 'test_asg',
            'ResourceType': 'auto-scaling-group',
            'Key': 'propogated-tag-key',
            'Value': 'propogate-tag-value',
            'PropagateAtLaunch': True
        }],
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )
    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=['test_asg']
    )
    instance_to_detach = response['AutoScalingGroups'][0]['Instances'][0]['InstanceId']
    instance_to_keep = response['AutoScalingGroups'][0]['Instances'][1]['InstanceId']

    ec2_client = boto3.client('ec2', region_name='us-east-1')

    response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])

    response = client.detach_instances(
        AutoScalingGroupName='test_asg',
        InstanceIds=[instance_to_detach],
        ShouldDecrementDesiredCapacity=True
    )
    response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=['test_asg']
    )
    response['AutoScalingGroups'][0]['Instances'].should.have.length_of(1)

    # test to ensure tag has been removed
    response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])
    tags = response['Reservations'][0]['Instances'][0]['Tags']
    tags.should.have.length_of(1)

    # test to ensure tag is present on other instance
    response = ec2_client.describe_instances(InstanceIds=[instance_to_keep])
    tags = response['Reservations'][0]['Instances'][0]['Tags']
    tags.should.have.length_of(2)

@mock_autoscaling
@mock_ec2
def test_detach_one_instance():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=2,
        Tags=[{
            'ResourceId': 'test_asg',
            'ResourceType': 'auto-scaling-group',
            'Key': 'propogated-tag-key',
            'Value': 'propogate-tag-value',
            'PropagateAtLaunch': True
        }],
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )
    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=['test_asg']
    )
    instance_to_detach = response['AutoScalingGroups'][0]['Instances'][0]['InstanceId']
    instance_to_keep = response['AutoScalingGroups'][0]['Instances'][1]['InstanceId']

    ec2_client = boto3.client('ec2', region_name='us-east-1')

    response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])

    response = client.detach_instances(
        AutoScalingGroupName='test_asg',
        InstanceIds=[instance_to_detach],
        ShouldDecrementDesiredCapacity=False
    )
    response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=['test_asg']
    )
    # test to ensure instance was replaced
    response['AutoScalingGroups'][0]['Instances'].should.have.length_of(2)

    response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])
    tags = response['Reservations'][0]['Instances'][0]['Tags']
    tags.should.have.length_of(1)

    response = ec2_client.describe_instances(InstanceIds=[instance_to_keep])
    tags = response['Reservations'][0]['Instances'][0]['Tags']
    tags.should.have.length_of(2)

@mock_autoscaling
@mock_ec2
def test_attach_one_instance():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=4,
        DesiredCapacity=2,
        Tags=[{
            'ResourceId': 'test_asg',
            'ResourceType': 'auto-scaling-group',
            'Key': 'propogated-tag-key',
            'Value': 'propogate-tag-value',
            'PropagateAtLaunch': True
        }],
        VPCZoneIdentifier=mocked_networking['subnet1'],
        NewInstancesProtectedFromScaleIn=True,
    )

    ec2 = boto3.resource('ec2', 'us-east-1')
    instances_to_add = [x.id for x in ec2.create_instances(ImageId='', MinCount=1, MaxCount=1)]

    response = client.attach_instances(
        AutoScalingGroupName='test_asg',
        InstanceIds=instances_to_add
    )
    response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=['test_asg']
    )
    instances = response['AutoScalingGroups'][0]['Instances']
    instances.should.have.length_of(3)
    for instance in instances:
        instance['ProtectedFromScaleIn'].should.equal(True)


@mock_autoscaling
@mock_ec2
def test_describe_instance_health():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=2,
        MaxSize=4,
        DesiredCapacity=2,
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=['test_asg']
    )

    instance1 = response['AutoScalingGroups'][0]['Instances'][0]
    instance1['HealthStatus'].should.equal('Healthy')

@mock_autoscaling
@mock_ec2
def test_set_instance_health():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=2,
        MaxSize=4,
        DesiredCapacity=2,
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=['test_asg']
    )

    instance1 = response['AutoScalingGroups'][0]['Instances'][0]
    instance1['HealthStatus'].should.equal('Healthy')

    client.set_instance_health(InstanceId=instance1['InstanceId'], HealthStatus='Unhealthy')

    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=['test_asg']
    )

    instance1 = response['AutoScalingGroups'][0]['Instances'][0]
    instance1['HealthStatus'].should.equal('Unhealthy')

@mock_autoscaling
def test_suspend_processes():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    client.create_launch_configuration(
        LaunchConfigurationName='lc',
    )
    client.create_auto_scaling_group(
        LaunchConfigurationName='lc',
        AutoScalingGroupName='test-asg',
        MinSize=1,
        MaxSize=1,
        VPCZoneIdentifier=mocked_networking['subnet1'],
    )

    # When we suspend the 'Launch' process on the ASG client
    client.suspend_processes(
        AutoScalingGroupName='test-asg',
        ScalingProcesses=['Launch']
    )

    res = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=['test-asg']
    )

    # The 'Launch' process should, in fact, be suspended
    launch_suspended = False
    for proc in res['AutoScalingGroups'][0]['SuspendedProcesses']:
        if proc.get('ProcessName') == 'Launch':
            launch_suspended = True

    assert launch_suspended is True

@mock_autoscaling
def test_set_instance_protection():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking['subnet1'],
        NewInstancesProtectedFromScaleIn=False,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=['test_asg'])
    instance_ids = [
        instance['InstanceId']
        for instance in response['AutoScalingGroups'][0]['Instances']
    ]
    protected = instance_ids[:3]

    _ = client.set_instance_protection(
        AutoScalingGroupName='test_asg',
        InstanceIds=protected,
        ProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=['test_asg'])
    for instance in response['AutoScalingGroups'][0]['Instances']:
        instance['ProtectedFromScaleIn'].should.equal(
            instance['InstanceId'] in protected
        )


@mock_autoscaling
def test_set_desired_capacity_up_boto3():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking['subnet1'],
        NewInstancesProtectedFromScaleIn=True,
    )

    _ = client.set_desired_capacity(
        AutoScalingGroupName='test_asg',
        DesiredCapacity=10,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=['test_asg'])
    instances = response['AutoScalingGroups'][0]['Instances']
    instances.should.have.length_of(10)
    for instance in instances:
        instance['ProtectedFromScaleIn'].should.equal(True)


@mock_autoscaling
def test_set_desired_capacity_down_boto3():
    mocked_networking = setup_networking()
    client = boto3.client('autoscaling', region_name='us-east-1')
    _ = client.create_launch_configuration(
        LaunchConfigurationName='test_launch_configuration'
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName='test_asg',
        LaunchConfigurationName='test_launch_configuration',
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking['subnet1'],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=['test_asg'])
    instance_ids = [
        instance['InstanceId']
        for instance in response['AutoScalingGroups'][0]['Instances']
    ]
    unprotected, protected = instance_ids[:2], instance_ids[2:]

    _ = client.set_instance_protection(
        AutoScalingGroupName='test_asg',
        InstanceIds=unprotected,
        ProtectedFromScaleIn=False,
    )

    _ = client.set_desired_capacity(
        AutoScalingGroupName='test_asg',
        DesiredCapacity=1,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=['test_asg'])
    group = response['AutoScalingGroups'][0]
    group['DesiredCapacity'].should.equal(1)
    instance_ids = {instance['InstanceId'] for instance in group['Instances']}
    set(protected).should.equal(instance_ids)
    set(unprotected).should_not.be.within(instance_ids)  # only unprotected killed
