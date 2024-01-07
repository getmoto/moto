from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from tests import EXAMPLE_AMI_ID, EXAMPLE_AMI_ID2

from .test_instances import retrieve_all_instances


def add_servers_to_region_boto3(ami_id, count, region):
    ec2 = boto3.resource("ec2", region_name=region)
    return ec2.create_instances(ImageId=ami_id, MinCount=count, MaxCount=count)


@mock_aws
def test_add_servers_to_a_single_region_boto3():
    region = "ap-northeast-1"
    id_1 = add_servers_to_region_boto3(EXAMPLE_AMI_ID, 1, region)[0].id
    id_2 = add_servers_to_region_boto3(EXAMPLE_AMI_ID2, 1, region)[0].id

    client = boto3.client("ec2", region_name=region)
    instances = retrieve_all_instances(client)

    instance1 = [i for i in instances if i["InstanceId"] == id_1][0]
    assert instance1["ImageId"] == EXAMPLE_AMI_ID
    instance2 = [i for i in instances if i["InstanceId"] == id_2][0]
    assert instance2["ImageId"] == EXAMPLE_AMI_ID2


@mock_aws
def test_add_servers_to_multiple_regions_boto3():
    region1 = "us-east-1"
    region2 = "ap-northeast-1"
    us_id = add_servers_to_region_boto3(EXAMPLE_AMI_ID, 1, region1)[0].id
    ap_id = add_servers_to_region_boto3(EXAMPLE_AMI_ID2, 1, region2)[0].id

    us_client = boto3.client("ec2", region_name=region1)
    ap_client = boto3.client("ec2", region_name=region2)
    us_instances = retrieve_all_instances(us_client)
    ap_instances = retrieve_all_instances(ap_client)

    assert us_id in [r["InstanceId"] for r in us_instances]
    assert ap_id not in [r["InstanceId"] for r in us_instances]
    assert ap_id in [r["InstanceId"] for r in ap_instances]
    assert us_id not in [r["InstanceId"] for r in ap_instances]

    us_instance = us_client.describe_instances(InstanceIds=[us_id])["Reservations"][0][
        "Instances"
    ][0]
    assert us_instance["ImageId"] == EXAMPLE_AMI_ID
    ap_instance = ap_client.describe_instances(InstanceIds=[ap_id])["Reservations"][0][
        "Instances"
    ][0]
    assert ap_instance["ImageId"] == EXAMPLE_AMI_ID2


@mock_aws
def test_create_autoscaling_group_boto3():
    regions = [("us-east-1", "c"), ("ap-northeast-1", "a")]
    for region, zone in regions:
        a_zone = f"{region}{zone}"
        asg_name = f"{region}_tester_group_{str(uuid4())[0:6]}"
        lb_name = f"{region}_lb_{str(uuid4())[0:6]}"
        config_name = f"{region}_tester_{str(uuid4())[0:6]}"

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
        assert len(groups) == 1
        group = groups[0]

        assert group["AutoScalingGroupName"] == asg_name
        assert group["DesiredCapacity"] == 2
        assert group["MaxSize"] == 2
        assert group["MinSize"] == 2
        assert group["VPCZoneIdentifier"] == subnet_id
        assert group["LaunchConfigurationName"] == config_name
        assert group["DefaultCooldown"] == 60
        assert group["HealthCheckGracePeriod"] == 100
        assert group["HealthCheckType"] == "EC2"
        assert group["LoadBalancerNames"] == [lb_name]
        assert group["PlacementGroup"] == "us_test_placement"
        assert group["TerminationPolicies"] == ["OldestInstance", "NewestInstance"]


@mock_aws
def test_describe_regions_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_regions(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DescribeRegions operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_aws
@pytest.mark.parametrize(
    "region_name", ["us-east-1", "us-east-2", "us-west-1", "us-west-2"]
)
def test_describe_zones_and_get_instance_types(region_name):
    """
    Verify that instance types exist in all exposed Availability Zones
    https://github.com/getmoto/moto/issues/5494
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
