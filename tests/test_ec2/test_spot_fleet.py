import boto3
import pytest

from moto import mock_ec2
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from botocore.exceptions import ClientError
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


def get_subnet_id(conn):
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = conn.create_subnet(
        VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/16", AvailabilityZone="us-east-1a"
    )["Subnet"]
    subnet_id = subnet["SubnetId"]
    return subnet_id


def spot_config(subnet_id, allocation_strategy="lowestPrice"):
    return {
        "ClientToken": "string",
        "SpotPrice": "0.12",
        "TargetCapacity": 6,
        "IamFleetRole": f"arn:aws:iam::{ACCOUNT_ID}:role/fleet",
        "LaunchSpecifications": [
            {
                "ImageId": EXAMPLE_AMI_ID,
                "KeyName": "my-key",
                "SecurityGroups": [{"GroupId": "sg-123"}],
                "UserData": "some user data",
                "InstanceType": "t2.small",
                "BlockDeviceMappings": [
                    {
                        "VirtualName": "string",
                        "DeviceName": "string",
                        "Ebs": {
                            "SnapshotId": "string",
                            "VolumeSize": 123,
                            "DeleteOnTermination": True | False,
                            "VolumeType": "standard",
                            "Iops": 123,
                            "Encrypted": True | False,
                        },
                        "NoDevice": "string",
                    }
                ],
                "Monitoring": {"Enabled": True},
                "SubnetId": subnet_id,
                "IamInstanceProfile": {"Arn": f"arn:aws:iam::{ACCOUNT_ID}:role/fleet"},
                "EbsOptimized": False,
                "WeightedCapacity": 2.0,
                "SpotPrice": "0.13",
            },
            {
                "ImageId": EXAMPLE_AMI_ID,
                "KeyName": "my-key",
                "SecurityGroups": [{"GroupId": "sg-123"}],
                "UserData": "some user data",
                "InstanceType": "t2.large",
                "Monitoring": {"Enabled": True},
                "SubnetId": subnet_id,
                "IamInstanceProfile": {"Arn": f"arn:aws:iam::{ACCOUNT_ID}:role/fleet"},
                "EbsOptimized": False,
                "WeightedCapacity": 4.0,
                "SpotPrice": "10.00",
                "TagSpecifications": [
                    {
                        "ResourceType": "instance",
                        "Tags": [{"Key": "test", "Value": "value"}],
                    }
                ],
            },
        ],
        "AllocationStrategy": allocation_strategy,
        "FulfilledCapacity": 6,
        "TagSpecifications": [
            {
                "ResourceType": "spot-fleet-request",
                "Tags": [{"Key": "test2", "Value": "value2"}],
            }
        ],
    }


@mock_ec2
def test_create_spot_fleet_with_invalid_tag_specifications():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    config = spot_config(subnet_id)
    invalid_resource_type = "invalid-resource-type"
    config["TagSpecifications"] = [
        {
            "ResourceType": invalid_resource_type,
            "Tags": [{"Key": "test2", "Value": "value2"}],
        }
    ]

    with pytest.raises(ClientError) as ex:
        _ = conn.request_spot_fleet(SpotFleetRequestConfig=config)

    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == f"The value for `ResourceType` must be `spot-fleet-request`, but got `{invalid_resource_type}` instead."
    )


@mock_ec2
def test_create_spot_fleet_with_lowest_price():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    assert len(spot_fleet_requests) == 1
    spot_fleet_request = spot_fleet_requests[0]
    assert spot_fleet_request["SpotFleetRequestState"] == "active"
    assert spot_fleet_request["Tags"] == [{"Key": "test2", "Value": "value2"}]
    spot_fleet_config = spot_fleet_request["SpotFleetRequestConfig"]

    assert spot_fleet_config["SpotPrice"] == "0.12"
    assert spot_fleet_config["TargetCapacity"] == 6
    assert spot_fleet_config["IamFleetRole"] == f"arn:aws:iam::{ACCOUNT_ID}:role/fleet"
    assert spot_fleet_config["AllocationStrategy"] == "lowestPrice"
    assert spot_fleet_config["FulfilledCapacity"] == 6.0

    assert len(spot_fleet_config["LaunchSpecifications"]) == 2
    launch_spec = spot_fleet_config["LaunchSpecifications"][0]

    assert launch_spec["EbsOptimized"] is False
    assert launch_spec["SecurityGroups"] == [{"GroupId": "sg-123"}]
    assert launch_spec["IamInstanceProfile"] == {
        "Arn": f"arn:aws:iam::{ACCOUNT_ID}:role/fleet"
    }
    assert launch_spec["ImageId"] == EXAMPLE_AMI_ID
    assert launch_spec["InstanceType"] == "t2.small"
    assert launch_spec["KeyName"] == "my-key"
    assert launch_spec["Monitoring"] == {"Enabled": True}
    assert launch_spec["SpotPrice"] == "0.13"
    assert launch_spec["SubnetId"] == subnet_id
    assert launch_spec["UserData"] == "some user data"
    assert launch_spec["WeightedCapacity"] == 2.0

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 3


@mock_ec2
def test_create_diversified_spot_fleet():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)
    diversified_config = spot_config(subnet_id, allocation_strategy="diversified")

    spot_fleet_res = conn.request_spot_fleet(SpotFleetRequestConfig=diversified_config)
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 2
    instance_types = set([instance["InstanceType"] for instance in instances])
    assert instance_types == set(["t2.small", "t2.large"])
    assert "i-" in instances[0]["InstanceId"]


@mock_ec2
@pytest.mark.parametrize("allocation_strategy", ["diversified", "lowestCost"])
def test_request_spot_fleet_using_launch_template_config__name(allocation_strategy):
    conn = boto3.client("ec2", region_name="us-east-2")

    template_data = {
        "ImageId": EXAMPLE_AMI_ID,
        "InstanceType": "t2.medium",
        "DisableApiTermination": False,
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": [{"Key": "test", "Value": "value"}]}
        ],
        "SecurityGroupIds": ["sg-abcd1234"],
    }

    template_name = str(uuid4())
    conn.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData=template_data
    )

    template_config = {
        "ClientToken": "string",
        "SpotPrice": "0.01",
        "TargetCapacity": 1,
        "IamFleetRole": "arn:aws:iam::486285699788:role/aws-ec2-spot-fleet-tagging-role",
        "LaunchTemplateConfigs": [
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateName": template_name,
                    "Version": "$Latest",
                }
            }
        ],
        "AllocationStrategy": allocation_strategy,
    }

    spot_fleet_res = conn.request_spot_fleet(SpotFleetRequestConfig=template_config)
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 1
    instance_types = set([instance["InstanceType"] for instance in instances])
    assert instance_types == set(["t2.medium"])
    assert "i-" in instances[0]["InstanceId"]


@mock_ec2
def test_request_spot_fleet_using_launch_template_config__id():
    conn = boto3.client("ec2", region_name="us-east-2")

    template_data = {
        "ImageId": EXAMPLE_AMI_ID,
        "InstanceType": "t2.medium",
        "DisableApiTermination": False,
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": [{"Key": "test", "Value": "value"}]}
        ],
        "SecurityGroupIds": ["sg-abcd1234"],
    }

    template_name = str(uuid4())
    template = conn.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData=template_data
    )["LaunchTemplate"]
    template_id = template["LaunchTemplateId"]

    template_config = {
        "ClientToken": "string",
        "SpotPrice": "0.01",
        "TargetCapacity": 1,
        "IamFleetRole": "arn:aws:iam::486285699788:role/aws-ec2-spot-fleet-tagging-role",
        "LaunchTemplateConfigs": [
            {"LaunchTemplateSpecification": {"LaunchTemplateId": template_id}}
        ],
        "AllocationStrategy": "lowestCost",
    }

    spot_fleet_res = conn.request_spot_fleet(SpotFleetRequestConfig=template_config)
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 1
    instance_types = set([instance["InstanceType"] for instance in instances])
    assert instance_types == set(["t2.medium"])
    assert "i-" in instances[0]["InstanceId"]


@mock_ec2
def test_request_spot_fleet_using_launch_template_config__overrides():
    conn = boto3.client("ec2", region_name="us-east-2")
    subnet_id = get_subnet_id(conn)

    template_data = {
        "ImageId": EXAMPLE_AMI_ID,
        "InstanceType": "t2.medium",
        "DisableApiTermination": False,
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": [{"Key": "test", "Value": "value"}]}
        ],
        "SecurityGroupIds": ["sg-abcd1234"],
    }

    template_name = str(uuid4())
    template = conn.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData=template_data
    )["LaunchTemplate"]
    template_id = template["LaunchTemplateId"]

    template_config = {
        "ClientToken": "string",
        "SpotPrice": "0.01",
        "TargetCapacity": 1,
        "IamFleetRole": "arn:aws:iam::486285699788:role/aws-ec2-spot-fleet-tagging-role",
        "LaunchTemplateConfigs": [
            {
                "LaunchTemplateSpecification": {"LaunchTemplateId": template_id},
                "Overrides": [
                    {
                        "InstanceType": "t2.nano",
                        "SubnetId": subnet_id,
                        "AvailabilityZone": "us-west-1",
                        "WeightedCapacity": 2,
                    }
                ],
            }
        ],
        "AllocationStrategy": "lowestCost",
    }

    spot_fleet_res = conn.request_spot_fleet(SpotFleetRequestConfig=template_config)
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 1
    assert instances[0]["InstanceType"] == "t2.nano"

    instance = conn.describe_instances(
        InstanceIds=[i["InstanceId"] for i in instances]
    )["Reservations"][0]["Instances"][0]
    assert instance["SubnetId"] == subnet_id


@mock_ec2
def test_create_spot_fleet_request_with_tag_spec():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    tag_spec = [
        {
            "ResourceType": "instance",
            "Tags": [
                {"Key": "tag-1", "Value": "foo"},
                {"Key": "tag-2", "Value": "bar"},
            ],
        }
    ]
    config = spot_config(subnet_id)
    config["LaunchSpecifications"][0]["TagSpecifications"] = tag_spec
    spot_fleet_res = conn.request_spot_fleet(SpotFleetRequestConfig=config)
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]
    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    spot_fleet_config = spot_fleet_requests[0]["SpotFleetRequestConfig"]
    fleet_tag_spec = spot_fleet_config["LaunchSpecifications"][0]["TagSpecifications"][
        0
    ]
    assert fleet_tag_spec["ResourceType"] == "instance"
    for tag in tag_spec[0]["Tags"]:
        assert tag in fleet_tag_spec["Tags"]

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = conn.describe_instances(
        InstanceIds=[i["InstanceId"] for i in instance_res["ActiveInstances"]]
    )
    for instance in instances["Reservations"][0]["Instances"]:
        for tag in tag_spec[0]["Tags"]:
            assert tag in instance["Tags"]


@mock_ec2
def test_cancel_spot_fleet_request():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    conn.cancel_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id], TerminateInstances=True
    )

    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    assert len(spot_fleet_requests) == 0


@mock_ec2
def test_cancel_spot_fleet_request__but_dont_terminate_instances():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    assert len(get_active_instances(conn, spot_fleet_id)) == 3

    conn.cancel_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id], TerminateInstances=False
    )

    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    assert len(spot_fleet_requests) == 1
    assert spot_fleet_requests[0]["SpotFleetRequestState"] == "cancelled_running"

    assert len(get_active_instances(conn, spot_fleet_id)) == 3

    # Cancel again and terminate instances
    conn.cancel_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id], TerminateInstances=True
    )

    assert len(get_active_instances(conn, spot_fleet_id)) == 0
    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    assert len(spot_fleet_requests) == 0


@mock_ec2
def test_modify_spot_fleet_request_up():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    conn.modify_spot_fleet_request(SpotFleetRequestId=spot_fleet_id, TargetCapacity=20)

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 10

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    assert spot_fleet_config["TargetCapacity"] == 20
    assert spot_fleet_config["FulfilledCapacity"] == 20.0


@mock_ec2
def test_modify_spot_fleet_request_up_diversified():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id, allocation_strategy="diversified")
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    conn.modify_spot_fleet_request(SpotFleetRequestId=spot_fleet_id, TargetCapacity=19)

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 7

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    assert spot_fleet_config["TargetCapacity"] == 19
    assert spot_fleet_config["FulfilledCapacity"] == 20.0


@mock_ec2
def test_modify_spot_fleet_request_down_no_terminate():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    conn.modify_spot_fleet_request(
        SpotFleetRequestId=spot_fleet_id,
        TargetCapacity=1,
        ExcessCapacityTerminationPolicy="noTermination",
    )

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 3

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    assert spot_fleet_config["TargetCapacity"] == 1
    assert spot_fleet_config["FulfilledCapacity"] == 6.0


@mock_ec2
def test_modify_spot_fleet_request_down_odd():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    conn.modify_spot_fleet_request(SpotFleetRequestId=spot_fleet_id, TargetCapacity=7)
    conn.modify_spot_fleet_request(SpotFleetRequestId=spot_fleet_id, TargetCapacity=5)

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 3

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    assert spot_fleet_config["TargetCapacity"] == 5
    assert spot_fleet_config["FulfilledCapacity"] == 6.0


@mock_ec2
def test_modify_spot_fleet_request_down():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    conn.modify_spot_fleet_request(SpotFleetRequestId=spot_fleet_id, TargetCapacity=1)

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 1

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    assert spot_fleet_config["TargetCapacity"] == 1
    assert spot_fleet_config["FulfilledCapacity"] == 2.0


@mock_ec2
def test_modify_spot_fleet_request_down_no_terminate_after_custom_terminate():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    instances = get_active_instances(conn, spot_fleet_id)
    conn.terminate_instances(InstanceIds=[i["InstanceId"] for i in instances[1:]])

    conn.modify_spot_fleet_request(
        SpotFleetRequestId=spot_fleet_id,
        TargetCapacity=1,
        ExcessCapacityTerminationPolicy="noTermination",
    )

    instances = get_active_instances(conn, spot_fleet_id)
    assert len(instances) == 1

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    assert spot_fleet_config["TargetCapacity"] == 1
    assert spot_fleet_config["FulfilledCapacity"] == 2.0


@mock_ec2
def test_create_spot_fleet_without_spot_price():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    # remove prices to force a fallback to ondemand price
    spot_config_without_price = spot_config(subnet_id)
    del spot_config_without_price["SpotPrice"]
    for spec in spot_config_without_price["LaunchSpecifications"]:
        del spec["SpotPrice"]

    spot_fleet_id = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config_without_price
    )["SpotFleetRequestId"]
    spot_fleet_requests = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"]
    assert len(spot_fleet_requests) == 1
    spot_fleet_request = spot_fleet_requests[0]
    spot_fleet_config = spot_fleet_request["SpotFleetRequestConfig"]

    assert len(spot_fleet_config["LaunchSpecifications"]) == 2
    launch_spec1 = spot_fleet_config["LaunchSpecifications"][0]
    launch_spec2 = spot_fleet_config["LaunchSpecifications"][1]

    # AWS will figure out the price
    assert "SpotPrice" not in launch_spec1
    assert "SpotPrice" not in launch_spec2


def get_active_instances(conn, spot_fleet_id):
    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    return instance_res["ActiveInstances"]
