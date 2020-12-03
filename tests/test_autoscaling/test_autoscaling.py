from __future__ import unicode_literals
import boto
import boto3
import boto.ec2.autoscale
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.group import AutoScalingGroup
from boto.ec2.autoscale import Tag
import boto.ec2.elb
import sure  # noqa
from botocore.exceptions import ClientError
import pytest

from moto import (
    mock_autoscaling,
    mock_ec2_deprecated,
    mock_elb_deprecated,
    mock_elb,
    mock_autoscaling_deprecated,
    mock_ec2,
    mock_cloudformation,
)
from tests.helpers import requires_boto_gte

from .utils import (
    setup_networking,
    setup_networking_deprecated,
    setup_instance_with_networking,
)


@mock_autoscaling_deprecated
@mock_elb_deprecated
def test_create_autoscaling_group():
    mocked_networking = setup_networking_deprecated()
    elb_conn = boto.ec2.elb.connect_to_region("us-east-1")
    elb_conn.create_load_balancer("test_lb", zones=[], listeners=[(80, 8080, "http")])

    conn = boto.ec2.autoscale.connect_to_region("us-east-1")
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        availability_zones=["us-east-1a", "us-east-1b"],
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
            subnet1=mocked_networking["subnet1"], subnet2=mocked_networking["subnet2"]
        ),
        termination_policies=["OldestInstance", "NewestInstance"],
        tags=[
            Tag(
                resource_id="tester_group",
                key="test_key",
                value="test_value",
                propagate_at_launch=True,
            )
        ],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.name.should.equal("tester_group")
    set(group.availability_zones).should.equal(set(["us-east-1a", "us-east-1b"]))
    group.desired_capacity.should.equal(2)
    group.max_size.should.equal(2)
    group.min_size.should.equal(2)
    group.instances.should.have.length_of(2)
    group.vpc_zone_identifier.should.equal(
        "{subnet1},{subnet2}".format(
            subnet1=mocked_networking["subnet1"], subnet2=mocked_networking["subnet2"]
        )
    )
    group.launch_config_name.should.equal("tester")
    group.default_cooldown.should.equal(60)
    group.health_check_period.should.equal(100)
    group.health_check_type.should.equal("EC2")
    list(group.load_balancers).should.equal(["test_lb"])
    group.placement_group.should.equal("test_placement")
    list(group.termination_policies).should.equal(["OldestInstance", "NewestInstance"])
    len(list(group.tags)).should.equal(1)
    tag = list(group.tags)[0]
    tag.resource_id.should.equal("tester_group")
    tag.key.should.equal("test_key")
    tag.value.should.equal("test_value")
    tag.propagate_at_launch.should.equal(True)


@mock_autoscaling_deprecated
def test_create_autoscaling_groups_defaults():
    """Test with the minimum inputs and check that all of the proper defaults
    are assigned for the other attributes"""

    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking["subnet1"],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.name.should.equal("tester_group")
    group.max_size.should.equal(2)
    group.min_size.should.equal(2)
    group.launch_config_name.should.equal("tester")

    # Defaults
    list(group.availability_zones).should.equal(["us-east-1a"])  # subnet1
    group.desired_capacity.should.equal(2)
    group.vpc_zone_identifier.should.equal(mocked_networking["subnet1"])
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
    conn = boto3.client("autoscaling", region_name="us-east-1")
    conn.create_launch_configuration(LaunchConfigurationName="TestLC")

    for i in range(51):
        conn.create_auto_scaling_group(
            AutoScalingGroupName="TestGroup%d" % i,
            MinSize=1,
            MaxSize=2,
            LaunchConfigurationName="TestLC",
            VPCZoneIdentifier=mocked_networking["subnet1"],
        )

    response = conn.describe_auto_scaling_groups()
    groups = response["AutoScalingGroups"]
    marker = response["NextToken"]
    groups.should.have.length_of(50)
    marker.should.equal(groups[-1]["AutoScalingGroupName"])

    response2 = conn.describe_auto_scaling_groups(NextToken=marker)

    groups.extend(response2["AutoScalingGroups"])
    groups.should.have.length_of(51)
    assert "NextToken" not in response2.keys()


@mock_autoscaling
@mock_ec2
def test_propogate_tags():
    mocked_networking = setup_networking()
    conn = boto3.client("autoscaling", region_name="us-east-1")
    conn.create_launch_configuration(LaunchConfigurationName="TestLC")

    conn.create_auto_scaling_group(
        AutoScalingGroupName="TestGroup1",
        MinSize=1,
        MaxSize=2,
        LaunchConfigurationName="TestLC",
        Tags=[
            {
                "ResourceId": "TestGroup1",
                "ResourceType": "auto-scaling-group",
                "PropagateAtLaunch": True,
                "Key": "TestTagKey1",
                "Value": "TestTagValue1",
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    ec2 = boto3.client("ec2", region_name="us-east-1")
    instances = ec2.describe_instances()

    tags = instances["Reservations"][0]["Instances"][0]["Tags"]
    tags.should.contain({"Value": "TestTagValue1", "Key": "TestTagKey1"})
    tags.should.contain({"Value": "TestGroup1", "Key": "aws:autoscaling:groupName"})


@mock_autoscaling_deprecated
def test_autoscaling_group_describe_filter():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking["subnet1"],
    )
    conn.create_auto_scaling_group(group)
    group.name = "tester_group2"
    conn.create_auto_scaling_group(group)
    group.name = "tester_group3"
    conn.create_auto_scaling_group(group)

    conn.get_all_groups(names=["tester_group", "tester_group2"]).should.have.length_of(
        2
    )
    conn.get_all_groups().should.have.length_of(3)


@mock_autoscaling_deprecated
def test_autoscaling_update():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking["subnet1"],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.availability_zones.should.equal(["us-east-1a"])
    group.vpc_zone_identifier.should.equal(mocked_networking["subnet1"])

    group.availability_zones = ["us-east-1b"]
    group.vpc_zone_identifier = mocked_networking["subnet2"]
    group.update()

    group = conn.get_all_groups()[0]
    group.availability_zones.should.equal(["us-east-1b"])
    group.vpc_zone_identifier.should.equal(mocked_networking["subnet2"])


@mock_autoscaling_deprecated
def test_autoscaling_tags_update():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        availability_zones=["us-east-1a"],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        tags=[
            Tag(
                resource_id="tester_group",
                key="test_key",
                value="test_value",
                propagate_at_launch=True,
            )
        ],
        vpc_zone_identifier=mocked_networking["subnet1"],
    )
    conn.create_auto_scaling_group(group)

    conn.create_or_update_tags(
        tags=[
            Tag(
                resource_id="tester_group",
                key="test_key",
                value="new_test_value",
                propagate_at_launch=True,
            ),
            Tag(
                resource_id="tester_group",
                key="test_key2",
                value="test_value2",
                propagate_at_launch=True,
            ),
        ]
    )
    group = conn.get_all_groups()[0]
    group.tags.should.have.length_of(2)


@mock_autoscaling_deprecated
def test_autoscaling_group_delete():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking["subnet1"],
    )
    conn.create_auto_scaling_group(group)

    conn.get_all_groups().should.have.length_of(1)

    conn.delete_auto_scaling_group("tester_group")
    conn.get_all_groups().should.have.length_of(0)


@mock_ec2_deprecated
@mock_autoscaling_deprecated
def test_autoscaling_group_describe_instances():
    mocked_networking = setup_networking_deprecated()
    conn = boto.ec2.autoscale.connect_to_region("us-east-1")
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking["subnet1"],
    )
    conn.create_auto_scaling_group(group)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)
    instances[0].launch_config_name.should.equal("tester")
    instances[0].health_status.should.equal("Healthy")
    autoscale_instance_ids = [instance.instance_id for instance in instances]

    ec2_conn = boto.ec2.connect_to_region("us-east-1")
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
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        availability_zones=["us-east-1a"],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking["subnet1"],
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
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        availability_zones=["us-east-1a"],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking["subnet1"],
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
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        availability_zones=["us-east-1a"],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking["subnet1"],
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
    zones = ["us-east-1a", "us-east-1b"]
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = elb_conn.create_load_balancer("my-lb", zones, ports)
    instances_health = elb_conn.describe_instance_health("my-lb")
    instances_health.should.be.empty

    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="t2.medium"
    )
    conn.create_launch_configuration(config)
    group = AutoScalingGroup(
        name="tester_group",
        max_size=2,
        min_size=2,
        launch_config=config,
        load_balancers=["my-lb"],
        vpc_zone_identifier=mocked_networking["subnet1"],
    )
    conn.create_auto_scaling_group(group)
    group = conn.get_all_groups()[0]
    elb = elb_conn.get_all_load_balancers()[0]
    group.desired_capacity.should.equal(2)
    elb.instances.should.have.length_of(2)

    autoscale_instance_ids = set(instance.instance_id for instance in group.instances)
    elb_instace_ids = set(instance.id for instance in elb.instances)
    autoscale_instance_ids.should.equal(elb_instace_ids)

    conn.set_desired_capacity("tester_group", 3)
    group = conn.get_all_groups()[0]
    elb = elb_conn.get_all_load_balancers()[0]
    group.desired_capacity.should.equal(3)
    elb.instances.should.have.length_of(3)

    autoscale_instance_ids = set(instance.instance_id for instance in group.instances)
    elb_instace_ids = set(instance.id for instance in elb.instances)
    autoscale_instance_ids.should.equal(elb_instace_ids)

    conn.delete_auto_scaling_group("tester_group")
    conn.get_all_groups().should.have.length_of(0)
    elb = elb_conn.get_all_load_balancers()[0]
    elb.instances.should.have.length_of(0)


"""
Boto3
"""


@mock_autoscaling
@mock_elb
def test_describe_load_balancers():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        LoadBalancerNames=["my-lb"],
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "test_value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    response = client.describe_load_balancers(AutoScalingGroupName="test_asg")
    assert response["ResponseMetadata"]["RequestId"]
    list(response["LoadBalancers"]).should.have.length_of(1)
    response["LoadBalancers"][0]["LoadBalancerName"].should.equal("my-lb")


@mock_autoscaling
@mock_elb
def test_create_elb_and_autoscaling_group_no_relationship():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2
    ELB_NAME = "my-elb"

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName=ELB_NAME,
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )

    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    # autoscaling group and elb should have no relationship
    response = client.describe_load_balancers(AutoScalingGroupName="test_asg")
    list(response["LoadBalancers"]).should.have.length_of(0)
    response = elb_client.describe_load_balancers(LoadBalancerNames=[ELB_NAME])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(0)


@mock_autoscaling
@mock_elb
def test_attach_load_balancer():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "test_value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(
        INSTANCE_COUNT
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    list(response["AutoScalingGroups"][0]["LoadBalancerNames"]).should.have.length_of(1)


@mock_autoscaling
@mock_elb
def test_detach_load_balancer():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        LoadBalancerNames=["my-lb"],
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "test_value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    response = client.detach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(0)

    response = client.describe_load_balancers(AutoScalingGroupName="test_asg")
    list(response["LoadBalancers"]).should.have.length_of(0)


@mock_autoscaling
def test_create_autoscaling_group_boto3():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    response = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            },
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "not-propogated-tag-key",
                "Value": "not-propagate-tag-value",
                "PropagateAtLaunch": False,
            },
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_autoscaling
def test_create_autoscaling_group_from_instance():
    autoscaling_group_name = "test_asg"
    image_id = "ami-0cc293023f983ed53"
    instance_type = "t2.micro"

    mocked_instance_with_networking = setup_instance_with_networking(
        image_id, instance_type
    )
    client = boto3.client("autoscaling", region_name="us-east-1")
    response = client.create_auto_scaling_group(
        AutoScalingGroupName=autoscaling_group_name,
        InstanceId=mocked_instance_with_networking["instance"],
        MinSize=1,
        MaxSize=3,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            },
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "not-propogated-tag-key",
                "Value": "not-propagate-tag-value",
                "PropagateAtLaunch": False,
            },
        ],
        VPCZoneIdentifier=mocked_instance_with_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    describe_launch_configurations_response = client.describe_launch_configurations()
    describe_launch_configurations_response[
        "LaunchConfigurations"
    ].should.have.length_of(1)
    launch_configuration_from_instance = describe_launch_configurations_response[
        "LaunchConfigurations"
    ][0]
    launch_configuration_from_instance["LaunchConfigurationName"].should.equal(
        "test_asg"
    )
    launch_configuration_from_instance["ImageId"].should.equal(image_id)
    launch_configuration_from_instance["InstanceType"].should.equal(instance_type)


@mock_autoscaling
def test_create_autoscaling_group_from_invalid_instance_id():
    invalid_instance_id = "invalid_instance"

    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            InstanceId=invalid_instance_id,
            MinSize=9,
            MaxSize=15,
            DesiredCapacity=12,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("ValidationError")
    ex.value.response["Error"]["Message"].should.equal(
        "Instance [{0}] is invalid.".format(invalid_instance_id)
    )


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_group_from_template():
    mocked_networking = setup_networking()

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={
            "ImageId": "ami-0cc293023f983ed53",
            "InstanceType": "t2.micro",
        },
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    response = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={
            "LaunchTemplateId": template["LaunchTemplateId"],
            "Version": str(template["LatestVersionNumber"]),
        },
        MinSize=1,
        MaxSize=3,
        DesiredCapacity=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_group_no_template_ref():
    mocked_networking = setup_networking()

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={
            "ImageId": "ami-0cc293023f983ed53",
            "InstanceType": "t2.micro",
        },
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            LaunchTemplate={"Version": str(template["LatestVersionNumber"])},
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("ValidationError")
    ex.value.response["Error"]["Message"].should.equal(
        "Valid requests must contain either launchTemplateId or LaunchTemplateName"
    )


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_group_multiple_template_ref():
    mocked_networking = setup_networking()

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={
            "ImageId": "ami-0cc293023f983ed53",
            "InstanceType": "t2.micro",
        },
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            LaunchTemplate={
                "LaunchTemplateId": template["LaunchTemplateId"],
                "LaunchTemplateName": template["LaunchTemplateName"],
                "Version": str(template["LatestVersionNumber"]),
            },
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("ValidationError")
    ex.value.response["Error"]["Message"].should.equal(
        "Valid requests must contain either launchTemplateId or LaunchTemplateName"
    )


@mock_autoscaling
def test_create_autoscaling_group_boto3_no_launch_configuration():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("ValidationError")
    ex.value.response["Error"]["Message"].should.equal(
        "Valid requests must contain either LaunchTemplate, LaunchConfigurationName, "
        "InstanceId or MixedInstancesPolicy parameter."
    )


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_group_boto3_multiple_launch_configurations():
    mocked_networking = setup_networking()

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={
            "ImageId": "ami-0cc293023f983ed53",
            "InstanceType": "t2.micro",
        },
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )

    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            LaunchConfigurationName="test_launch_configuration",
            LaunchTemplate={
                "LaunchTemplateId": template["LaunchTemplateId"],
                "Version": str(template["LatestVersionNumber"]),
            },
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("ValidationError")
    ex.value.response["Error"]["Message"].should.equal(
        "Valid requests must contain either LaunchTemplate, LaunchConfigurationName, "
        "InstanceId or MixedInstancesPolicy parameter."
    )


@mock_autoscaling
def test_describe_autoscaling_groups_boto3_launch_config():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration", InstanceType="t2.micro",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    group = response["AutoScalingGroups"][0]
    group["AutoScalingGroupName"].should.equal("test_asg")
    group["LaunchConfigurationName"].should.equal("test_launch_configuration")
    group.should_not.have.key("LaunchTemplate")
    group["AvailabilityZones"].should.equal(["us-east-1a"])
    group["VPCZoneIdentifier"].should.equal(mocked_networking["subnet1"])
    group["NewInstancesProtectedFromScaleIn"].should.equal(True)
    for instance in group["Instances"]:
        instance["LaunchConfigurationName"].should.equal("test_launch_configuration")
        instance.should_not.have.key("LaunchTemplate")
        instance["AvailabilityZone"].should.equal("us-east-1a")
        instance["ProtectedFromScaleIn"].should.equal(True)
        instance["InstanceType"].should.equal("t2.micro")


@mock_autoscaling
@mock_ec2
def test_describe_autoscaling_groups_boto3_launch_template():
    mocked_networking = setup_networking()
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={
            "ImageId": "ami-0cc293023f983ed53",
            "InstanceType": "t2.micro",
        },
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={"LaunchTemplateName": "test_launch_template", "Version": "1"},
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )
    expected_launch_template = {
        "LaunchTemplateId": template["LaunchTemplateId"],
        "LaunchTemplateName": "test_launch_template",
        "Version": "1",
    }

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    group = response["AutoScalingGroups"][0]
    group["AutoScalingGroupName"].should.equal("test_asg")
    group["LaunchTemplate"].should.equal(expected_launch_template)
    group.should_not.have.key("LaunchConfigurationName")
    group["AvailabilityZones"].should.equal(["us-east-1a"])
    group["VPCZoneIdentifier"].should.equal(mocked_networking["subnet1"])
    group["NewInstancesProtectedFromScaleIn"].should.equal(True)
    for instance in group["Instances"]:
        instance["LaunchTemplate"].should.equal(expected_launch_template)
        instance.should_not.have.key("LaunchConfigurationName")
        instance["AvailabilityZone"].should.equal("us-east-1a")
        instance["ProtectedFromScaleIn"].should.equal(True)
        instance["InstanceType"].should.equal("t2.micro")


@mock_autoscaling
def test_describe_autoscaling_instances_boto3_launch_config():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration", InstanceType="t2.micro",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_instances()
    len(response["AutoScalingInstances"]).should.equal(5)
    for instance in response["AutoScalingInstances"]:
        instance["LaunchConfigurationName"].should.equal("test_launch_configuration")
        instance.should_not.have.key("LaunchTemplate")
        instance["AutoScalingGroupName"].should.equal("test_asg")
        instance["AvailabilityZone"].should.equal("us-east-1a")
        instance["ProtectedFromScaleIn"].should.equal(True)
        instance["InstanceType"].should.equal("t2.micro")


@mock_autoscaling
@mock_ec2
def test_describe_autoscaling_instances_boto3_launch_template():
    mocked_networking = setup_networking()
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={
            "ImageId": "ami-0cc293023f983ed53",
            "InstanceType": "t2.micro",
        },
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={"LaunchTemplateName": "test_launch_template", "Version": "1"},
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )
    expected_launch_template = {
        "LaunchTemplateId": template["LaunchTemplateId"],
        "LaunchTemplateName": "test_launch_template",
        "Version": "1",
    }

    response = client.describe_auto_scaling_instances()
    len(response["AutoScalingInstances"]).should.equal(5)
    for instance in response["AutoScalingInstances"]:
        instance["LaunchTemplate"].should.equal(expected_launch_template)
        instance.should_not.have.key("LaunchConfigurationName")
        instance["AutoScalingGroupName"].should.equal("test_asg")
        instance["AvailabilityZone"].should.equal("us-east-1a")
        instance["ProtectedFromScaleIn"].should.equal(True)
        instance["InstanceType"].should.equal("t2.micro")


@mock_autoscaling
def test_describe_autoscaling_instances_instanceid_filter():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_ids = [
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    ]

    response = client.describe_auto_scaling_instances(
        InstanceIds=instance_ids[0:2]
    )  # Filter by first 2 of 5
    len(response["AutoScalingInstances"]).should.equal(2)
    for instance in response["AutoScalingInstances"]:
        instance["AutoScalingGroupName"].should.equal("test_asg")
        instance["AvailabilityZone"].should.equal("us-east-1a")
        instance["ProtectedFromScaleIn"].should.equal(True)


@mock_autoscaling
def test_update_autoscaling_group_boto3_launch_config():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration_new"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    client.update_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration_new",
        MinSize=1,
        VPCZoneIdentifier="{subnet1},{subnet2}".format(
            subnet1=mocked_networking["subnet1"], subnet2=mocked_networking["subnet2"]
        ),
        NewInstancesProtectedFromScaleIn=False,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    group["LaunchConfigurationName"].should.equal("test_launch_configuration_new")
    group["MinSize"].should.equal(1)
    set(group["AvailabilityZones"]).should.equal({"us-east-1a", "us-east-1b"})
    group["NewInstancesProtectedFromScaleIn"].should.equal(False)


@mock_autoscaling
@mock_ec2
def test_update_autoscaling_group_boto3_launch_template():
    mocked_networking = setup_networking()
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={
            "ImageId": "ami-0cc293023f983ed53",
            "InstanceType": "t2.micro",
        },
    )
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template_new",
        LaunchTemplateData={
            "ImageId": "ami-1ea5b10a3d8867db4",
            "InstanceType": "t2.micro",
        },
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={"LaunchTemplateName": "test_launch_template", "Version": "1"},
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    client.update_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={
            "LaunchTemplateName": "test_launch_template_new",
            "Version": "1",
        },
        MinSize=1,
        VPCZoneIdentifier="{subnet1},{subnet2}".format(
            subnet1=mocked_networking["subnet1"], subnet2=mocked_networking["subnet2"]
        ),
        NewInstancesProtectedFromScaleIn=False,
    )

    expected_launch_template = {
        "LaunchTemplateId": template["LaunchTemplateId"],
        "LaunchTemplateName": "test_launch_template_new",
        "Version": "1",
    }

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    group["LaunchTemplate"].should.equal(expected_launch_template)
    group["MinSize"].should.equal(1)
    set(group["AvailabilityZones"]).should.equal({"us-east-1a", "us-east-1b"})
    group["NewInstancesProtectedFromScaleIn"].should.equal(False)


@mock_autoscaling
def test_update_autoscaling_group_min_size_desired_capacity_change():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")

    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=2,
        MaxSize=20,
        DesiredCapacity=3,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )
    client.update_auto_scaling_group(AutoScalingGroupName="test_asg", MinSize=5)
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    group["DesiredCapacity"].should.equal(5)
    group["MinSize"].should.equal(5)
    group["Instances"].should.have.length_of(5)


@mock_autoscaling
def test_update_autoscaling_group_max_size_desired_capacity_change():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")

    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=2,
        MaxSize=20,
        DesiredCapacity=10,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )
    client.update_auto_scaling_group(AutoScalingGroupName="test_asg", MaxSize=5)
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    group["DesiredCapacity"].should.equal(5)
    group["MaxSize"].should.equal(5)
    group["Instances"].should.have.length_of(5)


@mock_autoscaling
def test_autoscaling_tags_update_boto3():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "test_value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    client.create_or_update_tags(
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "updated_test_value",
                "PropagateAtLaunch": True,
            },
            {
                "ResourceId": "test_asg",
                "Key": "test_key2",
                "Value": "test_value2",
                "PropagateAtLaunch": False,
            },
        ]
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Tags"].should.have.length_of(2)


@mock_autoscaling
def test_autoscaling_describe_policies_boto3():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "test_value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    client.put_scaling_policy(
        AutoScalingGroupName="test_asg",
        PolicyName="test_policy_down",
        PolicyType="SimpleScaling",
        AdjustmentType="PercentChangeInCapacity",
        ScalingAdjustment=-10,
        Cooldown=60,
        MinAdjustmentMagnitude=1,
    )
    client.put_scaling_policy(
        AutoScalingGroupName="test_asg",
        PolicyName="test_policy_up",
        PolicyType="SimpleScaling",
        AdjustmentType="PercentChangeInCapacity",
        ScalingAdjustment=10,
        Cooldown=60,
        MinAdjustmentMagnitude=1,
    )

    response = client.describe_policies()
    response["ScalingPolicies"].should.have.length_of(2)

    response = client.describe_policies(AutoScalingGroupName="test_asg")
    response["ScalingPolicies"].should.have.length_of(2)

    response = client.describe_policies(PolicyTypes=["StepScaling"])
    response["ScalingPolicies"].should.have.length_of(0)

    response = client.describe_policies(
        AutoScalingGroupName="test_asg",
        PolicyNames=["test_policy_down"],
        PolicyTypes=["SimpleScaling"],
    )
    response["ScalingPolicies"].should.have.length_of(1)
    response["ScalingPolicies"][0]["PolicyName"].should.equal("test_policy_down")


@mock_elb
@mock_autoscaling
@mock_ec2
def test_detach_one_instance_decrement():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_detach = response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"]
    instance_to_keep = response["AutoScalingGroups"][0]["Instances"][1]["InstanceId"]

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    response = client.detach_instances(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_detach],
        ShouldDecrementDesiredCapacity=True,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(1)
    instance_to_detach.shouldnt.be.within(
        [x["InstanceId"] for x in response["AutoScalingGroups"][0]["Instances"]]
    )

    # test to ensure tag has been removed
    response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])
    tags = response["Reservations"][0]["Instances"][0]["Tags"]
    tags.should.have.length_of(1)

    # test to ensure tag is present on other instance
    response = ec2_client.describe_instances(InstanceIds=[instance_to_keep])
    tags = response["Reservations"][0]["Instances"][0]["Tags"]
    tags.should.have.length_of(2)

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(1)
    instance_to_detach.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_detach_one_instance():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_detach = response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"]
    instance_to_keep = response["AutoScalingGroups"][0]["Instances"][1]["InstanceId"]

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    response = client.detach_instances(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_detach],
        ShouldDecrementDesiredCapacity=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    # test to ensure instance was replaced
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(2)

    response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])
    tags = response["Reservations"][0]["Instances"][0]["Tags"]
    tags.should.have.length_of(1)

    response = ec2_client.describe_instances(InstanceIds=[instance_to_keep])
    tags = response["Reservations"][0]["Instances"][0]["Tags"]
    tags.should.have.length_of(2)

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(2)
    instance_to_detach.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_standby_one_instance_decrement():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_standby = response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"]
    instance_to_keep = response["AutoScalingGroups"][0]["Instances"][1]["InstanceId"]

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    response = client.enter_standby(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby],
        ShouldDecrementDesiredCapacity=True,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(2)
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(1)

    response = client.describe_auto_scaling_instances(InstanceIds=[instance_to_standby])
    response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

    # test to ensure tag has been retained (standby instance is still part of the ASG)
    response = ec2_client.describe_instances()
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            tags = instance["Tags"]
            tags.should.have.length_of(2)

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(1)
    instance_to_standby.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_standby_one_instance():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_standby = response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"]
    instance_to_keep = response["AutoScalingGroups"][0]["Instances"][1]["InstanceId"]

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    response = client.enter_standby(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby],
        ShouldDecrementDesiredCapacity=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

    response = client.describe_auto_scaling_instances(InstanceIds=[instance_to_standby])
    response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

    # test to ensure tag has been retained (standby instance is still part of the ASG)
    response = ec2_client.describe_instances()
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            tags = instance["Tags"]
            tags.should.have.length_of(2)

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(2)
    instance_to_standby.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_standby_elb_update():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_standby = response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"]

    response = client.enter_standby(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby],
        ShouldDecrementDesiredCapacity=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

    response = client.describe_auto_scaling_instances(InstanceIds=[instance_to_standby])
    response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(2)
    instance_to_standby.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_standby_terminate_instance_decrement():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=3,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_standby_terminate = response["AutoScalingGroups"][0]["Instances"][0][
        "InstanceId"
    ]

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    response = client.enter_standby(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby_terminate],
        ShouldDecrementDesiredCapacity=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

    response = client.describe_auto_scaling_instances(
        InstanceIds=[instance_to_standby_terminate]
    )
    response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

    response = client.terminate_instance_in_auto_scaling_group(
        InstanceId=instance_to_standby_terminate, ShouldDecrementDesiredCapacity=True
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # AWS still decrements desired capacity ASG if requested, even if the terminated instance is in standby
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(1)
    response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"].should_not.equal(
        instance_to_standby_terminate
    )
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(1)

    response = ec2_client.describe_instances(
        InstanceIds=[instance_to_standby_terminate]
    )
    response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal(
        "terminated"
    )

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(1)
    instance_to_standby_terminate.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_standby_terminate_instance_no_decrement():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=3,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_standby_terminate = response["AutoScalingGroups"][0]["Instances"][0][
        "InstanceId"
    ]

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    response = client.enter_standby(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby_terminate],
        ShouldDecrementDesiredCapacity=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

    response = client.describe_auto_scaling_instances(
        InstanceIds=[instance_to_standby_terminate]
    )
    response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

    response = client.terminate_instance_in_auto_scaling_group(
        InstanceId=instance_to_standby_terminate, ShouldDecrementDesiredCapacity=False
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    group["Instances"].should.have.length_of(2)
    instance_to_standby_terminate.shouldnt.be.within(
        [x["InstanceId"] for x in group["Instances"]]
    )
    group["DesiredCapacity"].should.equal(2)

    response = ec2_client.describe_instances(
        InstanceIds=[instance_to_standby_terminate]
    )
    response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal(
        "terminated"
    )

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(2)
    instance_to_standby_terminate.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_standby_detach_instance_decrement():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=3,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_standby_detach = response["AutoScalingGroups"][0]["Instances"][0][
        "InstanceId"
    ]

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    response = client.enter_standby(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby_detach],
        ShouldDecrementDesiredCapacity=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

    response = client.describe_auto_scaling_instances(
        InstanceIds=[instance_to_standby_detach]
    )
    response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

    response = client.detach_instances(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby_detach],
        ShouldDecrementDesiredCapacity=True,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # AWS still decrements desired capacity ASG if requested, even if the detached instance was in standby
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(1)
    response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"].should_not.equal(
        instance_to_standby_detach
    )
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(1)

    response = ec2_client.describe_instances(InstanceIds=[instance_to_standby_detach])
    response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal("running")

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(1)
    instance_to_standby_detach.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_standby_detach_instance_no_decrement():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=3,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_standby_detach = response["AutoScalingGroups"][0]["Instances"][0][
        "InstanceId"
    ]

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    response = client.enter_standby(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby_detach],
        ShouldDecrementDesiredCapacity=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

    response = client.describe_auto_scaling_instances(
        InstanceIds=[instance_to_standby_detach]
    )
    response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

    response = client.detach_instances(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby_detach],
        ShouldDecrementDesiredCapacity=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    group["Instances"].should.have.length_of(2)
    instance_to_standby_detach.shouldnt.be.within(
        [x["InstanceId"] for x in group["Instances"]]
    )
    group["DesiredCapacity"].should.equal(2)

    response = ec2_client.describe_instances(InstanceIds=[instance_to_standby_detach])
    response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal("running")

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(2)
    instance_to_standby_detach.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_standby_exit_standby():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=3,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_to_standby_exit_standby = response["AutoScalingGroups"][0]["Instances"][0][
        "InstanceId"
    ]

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    response = client.enter_standby(
        AutoScalingGroupName="test_asg",
        InstanceIds=[instance_to_standby_exit_standby],
        ShouldDecrementDesiredCapacity=False,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

    response = client.describe_auto_scaling_instances(
        InstanceIds=[instance_to_standby_exit_standby]
    )
    response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

    response = client.exit_standby(
        AutoScalingGroupName="test_asg", InstanceIds=[instance_to_standby_exit_standby],
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    group["Instances"].should.have.length_of(3)
    instance_to_standby_exit_standby.should.be.within(
        [x["InstanceId"] for x in group["Instances"]]
    )
    group["DesiredCapacity"].should.equal(3)

    response = ec2_client.describe_instances(
        InstanceIds=[instance_to_standby_exit_standby]
    )
    response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal("running")

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(3)
    instance_to_standby_exit_standby.should.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )


@mock_elb
@mock_autoscaling
@mock_ec2
def test_attach_one_instance():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=4,
        DesiredCapacity=2,
        Tags=[
            {
                "ResourceId": "test_asg",
                "ResourceType": "auto-scaling-group",
                "Key": "propogated-tag-key",
                "Value": "propagate-tag-value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    ec2 = boto3.resource("ec2", "us-east-1")
    instances_to_add = [
        x.id for x in ec2.create_instances(ImageId="", MinCount=1, MaxCount=1)
    ]

    response = client.attach_instances(
        AutoScalingGroupName="test_asg", InstanceIds=instances_to_add
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instances = response["AutoScalingGroups"][0]["Instances"]
    instances.should.have.length_of(3)
    for instance in instances:
        instance["ProtectedFromScaleIn"].should.equal(True)

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(3)


@mock_autoscaling
@mock_ec2
def test_describe_instance_health():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=2,
        MaxSize=4,
        DesiredCapacity=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])

    instance1 = response["AutoScalingGroups"][0]["Instances"][0]
    instance1["HealthStatus"].should.equal("Healthy")


@mock_autoscaling
@mock_ec2
def test_set_instance_health():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=2,
        MaxSize=4,
        DesiredCapacity=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])

    instance1 = response["AutoScalingGroups"][0]["Instances"][0]
    instance1["HealthStatus"].should.equal("Healthy")

    client.set_instance_health(
        InstanceId=instance1["InstanceId"], HealthStatus="Unhealthy"
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])

    instance1 = response["AutoScalingGroups"][0]["Instances"][0]
    instance1["HealthStatus"].should.equal("Unhealthy")


@mock_autoscaling
def test_suspend_processes():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(LaunchConfigurationName="lc")
    client.create_auto_scaling_group(
        LaunchConfigurationName="lc",
        AutoScalingGroupName="test-asg",
        MinSize=1,
        MaxSize=1,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    # When we suspend the 'Launch' process on the ASG client
    client.suspend_processes(
        AutoScalingGroupName="test-asg", ScalingProcesses=["Launch"]
    )

    res = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test-asg"])

    # The 'Launch' process should, in fact, be suspended
    launch_suspended = False
    for proc in res["AutoScalingGroups"][0]["SuspendedProcesses"]:
        if proc.get("ProcessName") == "Launch":
            launch_suspended = True

    assert launch_suspended is True


@mock_autoscaling
def test_set_instance_protection():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_ids = [
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    ]
    protected = instance_ids[:3]

    _ = client.set_instance_protection(
        AutoScalingGroupName="test_asg",
        InstanceIds=protected,
        ProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    for instance in response["AutoScalingGroups"][0]["Instances"]:
        instance["ProtectedFromScaleIn"].should.equal(
            instance["InstanceId"] in protected
        )


@mock_autoscaling
def test_set_desired_capacity_up_boto3():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    _ = client.set_desired_capacity(AutoScalingGroupName="test_asg", DesiredCapacity=10)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instances = response["AutoScalingGroups"][0]["Instances"]
    instances.should.have.length_of(10)
    for instance in instances:
        instance["ProtectedFromScaleIn"].should.equal(True)


@mock_autoscaling
def test_set_desired_capacity_down_boto3():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_ids = [
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    ]
    unprotected, protected = instance_ids[:2], instance_ids[2:]

    _ = client.set_instance_protection(
        AutoScalingGroupName="test_asg",
        InstanceIds=unprotected,
        ProtectedFromScaleIn=False,
    )

    _ = client.set_desired_capacity(AutoScalingGroupName="test_asg", DesiredCapacity=1)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    group["DesiredCapacity"].should.equal(1)
    instance_ids = {instance["InstanceId"] for instance in group["Instances"]}
    set(protected).should.equal(instance_ids)
    set(unprotected).should_not.be.within(instance_ids)  # only unprotected killed


@mock_autoscaling
@mock_ec2
def test_terminate_instance_via_ec2_in_autoscaling_group():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=1,
        MaxSize=20,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    original_instance_id = next(
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    )
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    ec2_client.terminate_instances(InstanceIds=[original_instance_id])

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    replaced_instance_id = next(
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    )
    replaced_instance_id.should_not.equal(original_instance_id)


@mock_elb
@mock_autoscaling
@mock_ec2
def test_terminate_instance_in_auto_scaling_group_decrement():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        DesiredCapacity=1,
        MaxSize=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    original_instance_id = next(
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    )
    client.terminate_instance_in_auto_scaling_group(
        InstanceId=original_instance_id, ShouldDecrementDesiredCapacity=True
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    response["AutoScalingGroups"][0]["Instances"].should.equal([])
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(0)

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(0)


@mock_elb
@mock_autoscaling
@mock_ec2
def test_terminate_instance_in_auto_scaling_group_no_decrement():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        DesiredCapacity=1,
        MaxSize=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )

    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.attach_load_balancers(
        AutoScalingGroupName="test_asg", LoadBalancerNames=["my-lb"]
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    original_instance_id = next(
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    )
    client.terminate_instance_in_auto_scaling_group(
        InstanceId=original_instance_id, ShouldDecrementDesiredCapacity=False
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    replaced_instance_id = next(
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    )
    replaced_instance_id.should_not.equal(original_instance_id)
    response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(1)

    response = elb_client.describe_load_balancers(LoadBalancerNames=["my-lb"])
    list(response["LoadBalancerDescriptions"][0]["Instances"]).should.have.length_of(1)
    original_instance_id.shouldnt.be.within(
        [x["InstanceId"] for x in response["LoadBalancerDescriptions"][0]["Instances"]]
    )
