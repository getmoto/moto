import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_ec2
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


def get_subnet_id(conn):
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = conn.create_subnet(
        VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/16", AvailabilityZone="us-east-1a"
    )["Subnet"]
    subnet_id = subnet["SubnetId"]
    return subnet_id


def get_launch_template(conn, instance_type="t2.micro"):
    launch_template = conn.create_launch_template(
        LaunchTemplateName="test" + str(uuid4()),
        LaunchTemplateData={
            "ImageId": EXAMPLE_AMI_ID,
            "InstanceType": instance_type,
            "KeyName": "test",
            "SecurityGroups": ["sg-123456"],
            "DisableApiTermination": False,
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "test", "Value": "value"},
                        {"Key": "Name", "Value": "test"},
                    ],
                }
            ],
        },
    )["LaunchTemplate"]
    launch_template_id = launch_template["LaunchTemplateId"]
    launch_template_name = launch_template["LaunchTemplateName"]
    return launch_template_id, launch_template_name


@mock_ec2
def test_create_spot_fleet_with_lowest_price():
    conn = boto3.client("ec2", region_name="us-west-2")
    launch_template_id, _ = get_launch_template(conn)

    fleet_res = conn.create_fleet(
        ExcessCapacityTerminationPolicy="terminate",
        LaunchTemplateConfigs=[
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": launch_template_id,
                    "Version": "1",
                },
            },
        ],
        TargetCapacitySpecification={
            "DefaultTargetCapacityType": "spot",
            "OnDemandTargetCapacity": 0,
            "SpotTargetCapacity": 1,
            "TotalTargetCapacity": 1,
        },
        SpotOptions={
            "AllocationStrategy": "lowest-price",
        },
        Type="maintain",
        ValidFrom="2020-01-01T00:00:00Z",
        ValidUntil="2020-12-31T00:00:00Z",
    )

    fleet_id = fleet_res["FleetId"]
    fleet_id.should.be.a(str)
    fleet_id.should.have.length_of(42)

    fleets_res = conn.describe_fleets(FleetIds=[fleet_id])
    fleets_res.should.have.key("Fleets")
    fleets = fleets_res["Fleets"]

    fleet = fleets[0]
    fleet["FleetState"].should.equal("active")
    fleet_config = fleet["LaunchTemplateConfigs"][0]

    launch_template_spec = fleet_config["LaunchTemplateSpecification"]

    launch_template_spec["LaunchTemplateId"].should.equal(launch_template_id)
    launch_template_spec["Version"].should.equal("1")

    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(1)


@mock_ec2
def test_create_on_demand_fleet():
    conn = boto3.client("ec2", region_name="us-west-2")
    launch_template_id, _ = get_launch_template(conn)

    fleet_res = conn.create_fleet(
        ExcessCapacityTerminationPolicy="terminate",
        LaunchTemplateConfigs=[
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": launch_template_id,
                    "Version": "1",
                },
            },
        ],
        TargetCapacitySpecification={
            "DefaultTargetCapacityType": "on-demand",
            "OnDemandTargetCapacity": 1,
            "SpotTargetCapacity": 0,
            "TotalTargetCapacity": 1,
        },
        OnDemandOptions={
            "AllocationStrategy": "lowestPrice",
        },
        Type="maintain",
        ValidFrom="2020-01-01T00:00:00Z",
        ValidUntil="2020-12-31T00:00:00Z",
    )

    fleet_id = fleet_res["FleetId"]
    fleet_id.should.be.a(str)
    fleet_id.should.have.length_of(42)

    fleets_res = conn.describe_fleets(FleetIds=[fleet_id])
    fleets_res.should.have.key("Fleets")
    fleets = fleets_res["Fleets"]

    fleet = fleets[0]
    fleet["FleetState"].should.equal("active")
    fleet_config = fleet["LaunchTemplateConfigs"][0]

    launch_template_spec = fleet_config["LaunchTemplateSpecification"]

    launch_template_spec["LaunchTemplateId"].should.equal(launch_template_id)
    launch_template_spec["Version"].should.equal("1")

    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(1)


@mock_ec2
def test_create_diversified_spot_fleet():
    conn = boto3.client("ec2", region_name="us-west-2")
    launch_template_id_1, _ = get_launch_template(conn, instance_type="t2.small")
    launch_template_id_2, _ = get_launch_template(conn, instance_type="t2.large")

    fleet_res = conn.create_fleet(
        ExcessCapacityTerminationPolicy="terminate",
        LaunchTemplateConfigs=[
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": launch_template_id_1,
                    "Version": "1",
                },
            },
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": launch_template_id_2,
                    "Version": "1",
                },
            },
        ],
        TargetCapacitySpecification={
            "DefaultTargetCapacityType": "spot",
            "OnDemandTargetCapacity": 0,
            "SpotTargetCapacity": 2,
            "TotalTargetCapacity": 2,
        },
        SpotOptions={
            "AllocationStrategy": "diversified",
        },
        Type="maintain",
        ValidFrom="2020-01-01T00:00:00Z",
        ValidUntil="2020-12-31T00:00:00Z",
    )
    fleet_id = fleet_res["FleetId"]

    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(2)
    instance_types = set([instance["InstanceType"] for instance in instances])
    instance_types.should.equal(set(["t2.small", "t2.large"]))
    instances[0]["InstanceId"].should.contain("i-")


@mock_ec2
@pytest.mark.parametrize(
    "spot_allocation_strategy",
    [
        "diversified",
        "lowest-price",
        "capacity-optimized",
        "capacity-optimized-prioritized",
    ],
)
@pytest.mark.parametrize(
    "on_demand_allocation_strategy",
    ["lowestPrice", "prioritized"],
)
def test_request_fleet_using_launch_template_config__name(
    spot_allocation_strategy, on_demand_allocation_strategy
):

    conn = boto3.client("ec2", region_name="us-east-2")

    _, launch_template_name = get_launch_template(conn, instance_type="t2.medium")

    fleet_res = conn.create_fleet(
        LaunchTemplateConfigs=[
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateName": launch_template_name,
                    "Version": "1",
                },
            },
        ],
        TargetCapacitySpecification={
            "DefaultTargetCapacityType": "spot",
            "OnDemandTargetCapacity": 1,
            "SpotTargetCapacity": 2,
            "TotalTargetCapacity": 3,
        },
        SpotOptions={
            "AllocationStrategy": spot_allocation_strategy,
        },
        OnDemandOptions={
            "AllocationStrategy": on_demand_allocation_strategy,
        },
        Type="maintain",
        ValidFrom="2020-01-01T00:00:00Z",
        ValidUntil="2020-12-31T00:00:00Z",
    )

    fleet_id = fleet_res["FleetId"]

    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(3)
    instance_types = set([instance["InstanceType"] for instance in instances])
    instance_types.should.equal(set(["t2.medium"]))
    instances[0]["InstanceId"].should.contain("i-")


@mock_ec2
def test_create_fleet_request_with_tags():
    conn = boto3.client("ec2", region_name="us-west-2")

    launch_template_id, _ = get_launch_template(conn)
    tags = [
        {"Key": "Name", "Value": "test-fleet"},
        {"Key": "Another", "Value": "tag"},
    ]
    tags_instance = [
        {"Key": "test", "Value": "value"},
        {"Key": "Name", "Value": "test"},
    ]
    fleet_res = conn.create_fleet(
        DryRun=False,
        SpotOptions={
            "AllocationStrategy": "lowestPrice",
            "InstanceInterruptionBehavior": "terminate",
        },
        LaunchTemplateConfigs=[
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": launch_template_id,
                    "Version": "1",
                },
            },
        ],
        TargetCapacitySpecification={
            "DefaultTargetCapacityType": "spot",
            "OnDemandTargetCapacity": 1,
            "SpotTargetCapacity": 2,
            "TotalTargetCapacity": 3,
        },
        Type="request",
        ValidFrom="2020-01-01T00:00:00Z",
        ValidUntil="2020-12-31T00:00:00Z",
        TagSpecifications=[
            {
                "ResourceType": "fleet",
                "Tags": tags,
            },
        ],
    )
    fleet_id = fleet_res["FleetId"]
    fleets = conn.describe_fleets(FleetIds=[fleet_id])["Fleets"]

    fleets[0]["Tags"].should.equal(tags)

    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = conn.describe_instances(
        InstanceIds=[i["InstanceId"] for i in instance_res["ActiveInstances"]]
    )
    for instance in instances["Reservations"][0]["Instances"]:
        for tag in tags_instance:
            instance["Tags"].should.contain(tag)


@mock_ec2
def test_create_fleet_using_launch_template_config__overrides():

    conn = boto3.client("ec2", region_name="us-east-2")
    subnet_id = get_subnet_id(conn)

    template_id, _ = get_launch_template(conn, instance_type="t2.medium")

    template_config_overrides = [
        {
            "InstanceType": "t2.nano",
            "SubnetId": subnet_id,
            "AvailabilityZone": "us-west-1",
            "WeightedCapacity": 2,
        }
    ]

    fleet_res = conn.create_fleet(
        LaunchTemplateConfigs=[
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": template_id,
                    "Version": "1",
                },
                "Overrides": template_config_overrides,
            },
        ],
        TargetCapacitySpecification={
            "DefaultTargetCapacityType": "spot",
            "OnDemandTargetCapacity": 1,
            "SpotTargetCapacity": 0,
            "TotalTargetCapacity": 1,
        },
        SpotOptions={
            "AllocationStrategy": "lowest-price",
            "InstanceInterruptionBehavior": "terminate",
        },
        Type="maintain",
        ValidFrom="2020-01-01T00:00:00Z",
        ValidUntil="2020-12-31T00:00:00Z",
    )
    fleet_id = fleet_res["FleetId"]

    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = instance_res["ActiveInstances"]
    instances.should.have.length_of(1)
    instances[0].should.have.key("InstanceType").equals("t2.nano")

    instance = conn.describe_instances(
        InstanceIds=[i["InstanceId"] for i in instances]
    )["Reservations"][0]["Instances"][0]
    instance.should.have.key("SubnetId").equals(subnet_id)


@mock_ec2
def test_delete_fleet():
    conn = boto3.client("ec2", region_name="us-west-2")

    launch_template_id, _ = get_launch_template(conn)

    fleet_res = conn.create_fleet(
        LaunchTemplateConfigs=[
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": launch_template_id,
                    "Version": "1",
                },
            },
        ],
        TargetCapacitySpecification={
            "DefaultTargetCapacityType": "spot",
            "OnDemandTargetCapacity": 1,
            "SpotTargetCapacity": 2,
            "TotalTargetCapacity": 3,
        },
        SpotOptions={
            "AllocationStrategy": "lowestPrice",
            "InstanceInterruptionBehavior": "terminate",
        },
        Type="maintain",
        ValidFrom="2020-01-01T00:00:00Z",
        ValidUntil="2020-12-31T00:00:00Z",
    )
    fleet_id = fleet_res["FleetId"]

    conn.delete_fleets(FleetIds=[fleet_id], TerminateInstances=True)

    fleets = conn.describe_fleets(FleetIds=[fleet_id])["Fleets"]
    len(fleets).should.equal(1)

    target_capacity_specification = fleets[0]["TargetCapacitySpecification"]
    target_capacity_specification.should.have.key("TotalTargetCapacity").equals(0)
    fleets[0]["FleetState"].should.equal("deleted")

    # Instances should be terminated
    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(0)
