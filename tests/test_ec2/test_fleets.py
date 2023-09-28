import boto3
import pytest

from moto import mock_ec2
from tests import EXAMPLE_AMI_ID
from uuid import uuid4

from . import ec2_aws_verified


def get_subnet_id(conn):
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = conn.create_subnet(
        VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/16", AvailabilityZone="us-east-1a"
    )["Subnet"]
    subnet_id = subnet["SubnetId"]
    return subnet_id


def get_launch_template(conn, instance_type="t2.micro", ami_id=EXAMPLE_AMI_ID):
    launch_template = conn.create_launch_template(
        LaunchTemplateName="test" + str(uuid4()),
        LaunchTemplateData={
            "ImageId": ami_id,
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


class launch_template_context:
    def __init__(self, region: str = "us-west-2"):
        self.ec2 = boto3.client("ec2", region_name=region)
        self.ssm = boto3.client("ssm", region_name=region)

    def __enter__(self):
        kernel_61 = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
        ami_id = self.ssm.get_parameter(Name=kernel_61)["Parameter"]["Value"]
        self.lt_id, self.lt_name = get_launch_template(self.ec2, ami_id=ami_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ec2.delete_launch_template(LaunchTemplateId=self.lt_id)


@ec2_aws_verified
def test_launch_template_is_created_properly():
    with launch_template_context() as ctxt:
        template = ctxt.ec2.describe_launch_templates()["LaunchTemplates"][0]
        assert template["DefaultVersionNumber"] == 1
        assert template["LatestVersionNumber"] == 1


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
    assert isinstance(fleet_id, str)
    assert len(fleet_id) == 42

    fleets_res = conn.describe_fleets(FleetIds=[fleet_id])
    assert "Fleets" in fleets_res
    fleets = fleets_res["Fleets"]

    fleet = fleets[0]
    assert fleet["FleetState"] == "active"
    fleet_config = fleet["LaunchTemplateConfigs"][0]

    launch_template_spec = fleet_config["LaunchTemplateSpecification"]

    assert launch_template_spec["LaunchTemplateId"] == launch_template_id
    assert launch_template_spec["Version"] == "1"

    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = instance_res["ActiveInstances"]
    assert len(instances) == 1


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
    assert isinstance(fleet_id, str)
    assert len(fleet_id) == 42

    fleets_res = conn.describe_fleets(FleetIds=[fleet_id])
    assert "Fleets" in fleets_res
    fleets = fleets_res["Fleets"]

    fleet = fleets[0]
    assert fleet["FleetState"] == "active"
    fleet_config = fleet["LaunchTemplateConfigs"][0]

    launch_template_spec = fleet_config["LaunchTemplateSpecification"]

    assert launch_template_spec["LaunchTemplateId"] == launch_template_id
    assert launch_template_spec["Version"] == "1"

    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = instance_res["ActiveInstances"]
    assert len(instances) == 1


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
    assert len(instances) == 2
    instance_types = set([instance["InstanceType"] for instance in instances])
    assert instance_types == set(["t2.small", "t2.large"])
    assert "i-" in instances[0]["InstanceId"]


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
    assert len(instances) == 3
    instance_types = set([instance["InstanceType"] for instance in instances])
    assert instance_types == set(["t2.medium"])
    assert "i-" in instances[0]["InstanceId"]


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

    assert fleets[0]["Tags"] == tags

    instance_res = conn.describe_fleet_instances(FleetId=fleet_id)
    instances = conn.describe_instances(
        InstanceIds=[i["InstanceId"] for i in instance_res["ActiveInstances"]]
    )
    for instance in instances["Reservations"][0]["Instances"]:
        for tag in tags_instance:
            assert tag in instance["Tags"]


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
    assert len(instances) == 1
    assert instances[0]["InstanceType"] == "t2.nano"

    instance = conn.describe_instances(
        InstanceIds=[i["InstanceId"] for i in instances]
    )["Reservations"][0]["Instances"][0]
    assert instance["SubnetId"] == subnet_id


@ec2_aws_verified
def test_delete_fleet():
    with launch_template_context() as ctxt:

        fleet_res = ctxt.ec2.create_fleet(
            LaunchTemplateConfigs=[
                {
                    "LaunchTemplateSpecification": {
                        "LaunchTemplateId": ctxt.lt_id,
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
        )
        fleet_id = fleet_res["FleetId"]

        successfull_deletions = ctxt.ec2.delete_fleets(
            FleetIds=[fleet_id], TerminateInstances=False
        )["SuccessfulFleetDeletions"]

        assert len(successfull_deletions) == 1
        assert successfull_deletions[0]["FleetId"] == fleet_id
        assert successfull_deletions[0]["CurrentFleetState"] == "deleted_running"

        successfull_deletions = ctxt.ec2.delete_fleets(
            FleetIds=[fleet_id], TerminateInstances=True
        )["SuccessfulFleetDeletions"]

        assert len(successfull_deletions) == 1
        assert successfull_deletions[0]["FleetId"] == fleet_id
        assert successfull_deletions[0]["CurrentFleetState"] == "deleted_terminating"

        fleets = ctxt.ec2.describe_fleets(FleetIds=[fleet_id])["Fleets"]
        assert len(fleets) == 1

        # AWS doesn't reset this, but Moto does
        # we should figure out why Moto sets this value to 0
        # target_capacity_specification = fleets[0]["TargetCapacitySpecification"]
        # assert target_capacity_specification["TotalTargetCapacity"] == 3
        assert fleets[0]["FleetState"] == "deleted_terminating"

        # Instances should be terminated
        instance_res = ctxt.ec2.describe_fleet_instances(FleetId=fleet_id)
        instances = instance_res["ActiveInstances"]
        assert len(instances) == 0


@mock_ec2
def test_describe_fleet_instances_api():
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

    assert fleet_res["FleetId"] == fleet_id
    assert len(fleet_res["ActiveInstances"]) == 3

    instance_ids = [i["InstanceId"] for i in fleet_res["ActiveInstances"]]
    for instance_id in instance_ids:
        assert instance_id.startswith("i-") is True

    instance_types = [i["InstanceType"] for i in fleet_res["ActiveInstances"]]
    assert instance_types == ["t2.micro", "t2.micro", "t2.micro"]

    instance_healths = [i["InstanceHealth"] for i in fleet_res["ActiveInstances"]]
    assert instance_healths == ["healthy", "healthy", "healthy"]


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

    assert "FleetId" in fleet_res
    assert fleet_res["FleetId"].startswith("fleet-") is True

    assert "Instances" in fleet_res
    assert len(fleet_res["Instances"]) == 3

    instance_ids = [i["InstanceIds"] for i in fleet_res["Instances"]]
    for instance_id in instance_ids:
        assert instance_id[0].startswith("i-") is True

    instance_types = [i["InstanceType"] for i in fleet_res["Instances"]]
    assert instance_types == ["t2.micro", "t2.micro", "t2.micro"]

    lifecycle = [i["Lifecycle"] for i in fleet_res["Instances"]]
    assert "spot" in lifecycle
    assert "on-demand" in lifecycle


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
    assert len(fleet_res) == 1
    assert fleet_res[0]["FleetId"] == fleet_id
    assert fleet_res[0]["ExcessCapacityTerminationPolicy"] == "no-termination"
    assert fleet_res[0]["LaunchTemplateConfigs"] == [lt_config]
    assert fleet_res[0]["TargetCapacitySpecification"] == {
        "DefaultTargetCapacityType": "on-demand",
        "OnDemandTargetCapacity": 10,
        "SpotTargetCapacity": 10,
        "TotalTargetCapacity": 30,
    }
    assert fleet_res[0]["SpotOptions"] == {
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
    assert fleet_res[0]["OnDemandOptions"] == {
        "AllocationStrategy": "lowest-price",
        "MaxTotalPrice": "50",
        "MinTargetCapacity": 1,
        "SingleAvailabilityZone": True,
        "SingleInstanceType": True,
    }
    assert fleet_res[0]["ReplaceUnhealthyInstances"] is True
    assert fleet_res[0]["TerminateInstancesWithExpiration"] is True
    assert fleet_res[0]["Type"] == "maintain"
    assert "ValidFrom" in fleet_res[0]
    assert fleet_res[0]["ValidFrom"].isoformat() == "2020-01-01T00:00:00+00:00"
    assert "ValidUntil" in fleet_res[0]
    assert fleet_res[0]["ValidUntil"].isoformat() == "2020-12-31T00:00:00+00:00"
