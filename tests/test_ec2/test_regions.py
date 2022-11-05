import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_autoscaling, mock_ec2, mock_elb

from tests import EXAMPLE_AMI_ID, EXAMPLE_AMI_ID2
from uuid import uuid4
from .test_instances import retrieve_all_instances


def add_servers_to_region_boto3(ami_id, count, region):
    ec2 = boto3.resource("ec2", region_name=region)
    return ec2.create_instances(ImageId=ami_id, MinCount=count, MaxCount=count)


@mock_ec2
def test_add_servers_to_a_single_region_boto3():
    region = "ap-northeast-1"
    id_1 = add_servers_to_region_boto3(EXAMPLE_AMI_ID, 1, region)[0].id
    id_2 = add_servers_to_region_boto3(EXAMPLE_AMI_ID2, 1, region)[0].id

    client = boto3.client("ec2", region_name=region)
    instances = retrieve_all_instances(client)

    instance1 = [i for i in instances if i["InstanceId"] == id_1][0]
    instance1["ImageId"].should.equal(EXAMPLE_AMI_ID)
    instance2 = [i for i in instances if i["InstanceId"] == id_2][0]
    instance2["ImageId"].should.equal(EXAMPLE_AMI_ID2)


@mock_ec2
def test_add_servers_to_multiple_regions_boto3():
    region1 = "us-east-1"
    region2 = "ap-northeast-1"
    us_id = add_servers_to_region_boto3(EXAMPLE_AMI_ID, 1, region1)[0].id
    ap_id = add_servers_to_region_boto3(EXAMPLE_AMI_ID2, 1, region2)[0].id

    us_client = boto3.client("ec2", region_name=region1)
    ap_client = boto3.client("ec2", region_name=region2)
    us_instances = retrieve_all_instances(us_client)
    ap_instances = retrieve_all_instances(ap_client)

    [r["InstanceId"] for r in us_instances].should.contain(us_id)
    [r["InstanceId"] for r in us_instances].shouldnt.contain(ap_id)
    [r["InstanceId"] for r in ap_instances].should.contain(ap_id)
    [r["InstanceId"] for r in ap_instances].shouldnt.contain(us_id)

    us_instance = us_client.describe_instances(InstanceIds=[us_id])["Reservations"][0][
        "Instances"
    ][0]
    us_instance["ImageId"].should.equal(EXAMPLE_AMI_ID)
    ap_instance = ap_client.describe_instances(InstanceIds=[ap_id])["Reservations"][0][
        "Instances"
    ][0]
    ap_instance["ImageId"].should.equal(EXAMPLE_AMI_ID2)


@mock_autoscaling
@mock_elb
@mock_ec2
def test_create_autoscaling_group_boto3():
    regions = [("us-east-1", "c"), ("ap-northeast-1", "a")]
    for region, zone in regions:
        a_zone = "{}{}".format(region, zone)
        asg_name = "{}_tester_group_{}".format(region, str(uuid4())[0:6])
        lb_name = "{}_lb_{}".format(region, str(uuid4())[0:6])
        config_name = "{}_tester_{}".format(region, str(uuid4())[0:6])

        elb_client = boto3.client("elb", region_name=region)
        elb_client.create_load_balancer(
            LoadBalancerName=lb_name,
            Listeners=[
                {"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}
            ],
            AvailabilityZones=[],
        )

        as_client = boto3.client("autoscaling", region_name=region)
        as_client.create_launch_configuration(
            LaunchConfigurationName=config_name,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="m1.small",
        )

        ec2_client = boto3.client("ec2", region_name=region)
        subnet_id = ec2_client.describe_subnets(
            Filters=[{"Name": "availability-zone", "Values": [a_zone]}]
        )["Subnets"][0]["SubnetId"]

        as_client.create_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            AvailabilityZones=[a_zone],
            DefaultCooldown=60,
            DesiredCapacity=2,
            HealthCheckGracePeriod=100,
            HealthCheckType="EC2",
            LaunchConfigurationName=config_name,
            LoadBalancerNames=[lb_name],
            MinSize=2,
            MaxSize=2,
            PlacementGroup="us_test_placement",
            VPCZoneIdentifier=subnet_id,
            TerminationPolicies=["OldestInstance", "NewestInstance"],
        )

        groups = as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name]
        )["AutoScalingGroups"]
        groups.should.have.length_of(1)
        group = groups[0]

        group["AutoScalingGroupName"].should.equal(asg_name)
        group["DesiredCapacity"].should.equal(2)
        group["MaxSize"].should.equal(2)
        group["MinSize"].should.equal(2)
        group["VPCZoneIdentifier"].should.equal(subnet_id)
        group["LaunchConfigurationName"].should.equal(config_name)
        group["DefaultCooldown"].should.equal(60)
        group["HealthCheckGracePeriod"].should.equal(100)
        group["HealthCheckType"].should.equal("EC2")
        group["LoadBalancerNames"].should.equal([lb_name])
        group["PlacementGroup"].should.equal("us_test_placement")
        group["TerminationPolicies"].should.equal(["OldestInstance", "NewestInstance"])


@mock_ec2
def test_describe_regions_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_regions(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DescribeRegions operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
@pytest.mark.parametrize(
    "region_name", ["us-east-1", "us-east-2", "us-west-1", "us-west-2"]
)
def test_describe_zones_and_get_instance_types(region_name):
    """
    Verify that instance types exist in all exposed Availability Zones
    https://github.com/spulec/moto/issues/5494
    """
    client = boto3.client("ec2", region_name=region_name)
    zones = client.describe_availability_zones()["AvailabilityZones"]
    zone_names = [z["ZoneName"] for z in zones]

    for zone in zone_names:
        offerings = client.describe_instance_type_offerings(
            LocationType="availability-zone",
            Filters=[{"Name": "location", "Values": [zone]}],
        )["InstanceTypeOfferings"]
        assert len(offerings) > 0
