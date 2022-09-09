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

    delete_fleet_out = conn.delete_fleets(FleetIds=[fleet_id], TerminateInstances=True)

    delete_fleet_out["SuccessfulFleetDeletions"].should.have.length_of(1)
    delete_fleet_out["SuccessfulFleetDeletions"][0]["FleetId"].should.equal(fleet_id)
    delete_fleet_out["SuccessfulFleetDeletions"][0]["CurrentFleetState"].should.equal(
        "deleted"
    )

    fleets = conn.describe_fleets(FleetIds=[fleet_id])["Fleets"]
    len(fleets).should.equal(1)

    target_capacity_specification = fleets[0]["TargetCapacitySpecification"]
    target_capacity_specification.should.have.key("TotalTargetCapacity").equals(0)
    fleets[0]["FleetState"].should.equal("deleted")

    # Instances should be terminated
    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(0)


@mock_ec2
def test_describe_fleet_instences_api():
    conn = boto3.client("ec2", region_name="us-west-1")

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
    fleet_res = conn.describe_fleet_instances(FleetId=fleet_id)

    fleet_res["FleetId"].should.equal(fleet_id)
    fleet_res["ActiveInstances"].should.have.length_of(3)

    instance_ids = [i["InstanceId"] for i in fleet_res["ActiveInstances"]]
    for instance_id in instance_ids:
        instance_id.startswith("i-").should.be.true

    instance_types = [i["InstanceType"] for i in fleet_res["ActiveInstances"]]
    instance_types.should.equal(["t2.micro", "t2.micro", "t2.micro"])

    instance_healths = [i["InstanceHealth"] for i in fleet_res["ActiveInstances"]]
    instance_healths.should.equal(["healthy", "healthy", "healthy"])


@mock_ec2
def test_create_fleet_api():
    conn = boto3.client("ec2", region_name="us-west-1")

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
        Type="instant",
        ValidFrom="2020-01-01T00:00:00Z",
        ValidUntil="2020-12-31T00:00:00Z",
    )

    fleet_res.should.have.key("FleetId")
    fleet_res["FleetId"].startswith("fleet-").should.be.true

    fleet_res.should.have.key("Instances")
    fleet_res["Instances"].should.have.length_of(3)

    instance_ids = [i["InstanceIds"] for i in fleet_res["Instances"]]
    for instance_id in instance_ids:
        instance_id[0].startswith("i-").should.be.true

    instance_types = [i["InstanceType"] for i in fleet_res["Instances"]]
    instance_types.should.equal(["t2.micro", "t2.micro", "t2.micro"])

    lifecycle = [i["Lifecycle"] for i in fleet_res["Instances"]]
    lifecycle.should.contain("spot")
    lifecycle.should.contain("on-demand")


@mock_ec2
def test_create_fleet_api_response():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    launch_template_id, _ = get_launch_template(conn)

    lt_config = {
        "LaunchTemplateSpecification": {
            "LaunchTemplateId": launch_template_id,
            "Version": "1",
        },
        "Overrides": [
            {
                "AvailabilityZone": "us-west-1a",
                "InstanceRequirements": {
                    "AcceleratorCount": {
                        "Max": 10,
                        "Min": 1,
                    },
                    "AcceleratorManufacturers": ["nvidia"],
                    "AcceleratorNames": ["t4"],
                    "AcceleratorTotalMemoryMiB": {
                        "Max": 20972,
                        "Min": 1,
                    },
                    "AcceleratorTypes": ["gpu"],
                    "BareMetal": "included",
                    "BaselineEbsBandwidthMbps": {
                        "Max": 10000,
                        "Min": 125,
                    },
                    "BurstablePerformance": "included",
                    "CpuManufacturers": ["amd", "intel"],
                    "ExcludedInstanceTypes": ["m5.8xlarge"],
                    "InstanceGenerations": ["current"],
                    "LocalStorage": "included",
                    "LocalStorageTypes": ["ssd"],
                    "MemoryGiBPerVCpu": {
                        "Min": 1,
                        "Max": 160,
                    },
                    "MemoryMiB": {
                        "Min": 2048,
                        "Max": 40960,
                    },
                    "NetworkInterfaceCount": {
                        "Max": 1,
                        "Min": 1,
                    },
                    "OnDemandMaxPricePercentageOverLowestPrice": 99999,
                    "RequireHibernateSupport": True,
                    "SpotMaxPricePercentageOverLowestPrice": 99999,
                    "TotalLocalStorageGB": {
                        "Min": 100,
                        "Max": 10000,
                    },
                    "VCpuCount": {
                        "Min": 2,
                        "Max": 160,
                    },
                },
                "MaxPrice": "0.5",
                "Priority": 2,
                "SubnetId": subnet_id,
                "WeightedCapacity": 1,
            },
        ],
    }

    fleet_res = conn.create_fleet(
        ExcessCapacityTerminationPolicy="no-termination",
        LaunchTemplateConfigs=[lt_config],
        TargetCapacitySpecification={
            "DefaultTargetCapacityType": "on-demand",
            "OnDemandTargetCapacity": 10,
            "SpotTargetCapacity": 10,
            "TotalTargetCapacity": 30,
        },
        SpotOptions={
            "AllocationStrategy": "lowest-price",
            "InstanceInterruptionBehavior": "terminate",
            "InstancePoolsToUseCount": 1,
            "MaintenanceStrategies": {
                "CapacityRebalance": {
                    "ReplacementStrategy": "launch-before-terminate",
                    "TerminationDelay": 120,
                },
            },
            "MaxTotalPrice": "50",
            "MinTargetCapacity": 1,
            "SingleAvailabilityZone": True,
            "SingleInstanceType": True,
        },
        OnDemandOptions={
            "AllocationStrategy": "lowest-price",
            "MaxTotalPrice": "50",
            "MinTargetCapacity": 1,
            "SingleAvailabilityZone": True,
            "SingleInstanceType": True,
        },
        ReplaceUnhealthyInstances=True,
        TerminateInstancesWithExpiration=True,
        Type="maintain",
        ValidFrom="2020-01-01T00:00:00Z",
        ValidUntil="2020-12-31T00:00:00Z",
    )
    fleet_id = fleet_res["FleetId"]

    fleet_res = conn.describe_fleets(FleetIds=[fleet_id])["Fleets"]
    fleet_res.should.have.length_of(1)
    fleet_res[0].should.have.key("FleetId").equals(fleet_id)
    fleet_res[0].should.have.key("ExcessCapacityTerminationPolicy").equals(
        "no-termination"
    )
    fleet_res[0].should.have.key("LaunchTemplateConfigs").equals([lt_config])
    fleet_res[0].should.have.key("TargetCapacitySpecification").equals(
        {
            "DefaultTargetCapacityType": "on-demand",
            "OnDemandTargetCapacity": 10,
            "SpotTargetCapacity": 10,
            "TotalTargetCapacity": 30,
        }
    )
    fleet_res[0].should.have.key("SpotOptions").equals(
        {
            "AllocationStrategy": "lowest-price",
            "InstanceInterruptionBehavior": "terminate",
            "InstancePoolsToUseCount": 1,
            "MaintenanceStrategies": {
                "CapacityRebalance": {
                    "ReplacementStrategy": "launch-before-terminate",
                    "TerminationDelay": 120,
                },
            },
            "MaxTotalPrice": "50",
            "MinTargetCapacity": 1,
            "SingleAvailabilityZone": True,
            "SingleInstanceType": True,
        }
    )
    fleet_res[0].should.have.key("OnDemandOptions").equals(
        {
            "AllocationStrategy": "lowest-price",
            "MaxTotalPrice": "50",
            "MinTargetCapacity": 1,
            "SingleAvailabilityZone": True,
            "SingleInstanceType": True,
        }
    )
    fleet_res[0].should.have.key("ReplaceUnhealthyInstances").equals(True)
    fleet_res[0].should.have.key("TerminateInstancesWithExpiration").equals(True)
    fleet_res[0].should.have.key("Type").equals("maintain")
    fleet_res[0].should.have.key("ValidFrom")
    fleet_res[0]["ValidFrom"].isoformat().should.equal("2020-01-01T00:00:00+00:00")
    fleet_res[0].should.have.key("ValidUntil")
    fleet_res[0]["ValidUntil"].isoformat().should.equal("2020-12-31T00:00:00+00:00")
