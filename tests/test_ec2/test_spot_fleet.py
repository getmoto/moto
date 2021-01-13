from __future__ import unicode_literals

import boto3
import sure  # noqa

from moto import mock_ec2
from moto.core import ACCOUNT_ID
from tests import EXAMPLE_AMI_ID


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
        "IamFleetRole": "arn:aws:iam::{}:role/fleet".format(ACCOUNT_ID),
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
                "IamInstanceProfile": {
                    "Arn": "arn:aws:iam::{}:role/fleet".format(ACCOUNT_ID)
                },
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
                "IamInstanceProfile": {
                    "Arn": "arn:aws:iam::{}:role/fleet".format(ACCOUNT_ID)
                },
                "EbsOptimized": False,
                "WeightedCapacity": 4.0,
                "SpotPrice": "10.00",
            },
        ],
        "AllocationStrategy": allocation_strategy,
        "FulfilledCapacity": 6,
    }


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
    len(spot_fleet_requests).should.equal(1)
    spot_fleet_request = spot_fleet_requests[0]
    spot_fleet_request["SpotFleetRequestState"].should.equal("active")
    spot_fleet_config = spot_fleet_request["SpotFleetRequestConfig"]

    spot_fleet_config["SpotPrice"].should.equal("0.12")
    spot_fleet_config["TargetCapacity"].should.equal(6)
    spot_fleet_config["IamFleetRole"].should.equal(
        "arn:aws:iam::{}:role/fleet".format(ACCOUNT_ID)
    )
    spot_fleet_config["AllocationStrategy"].should.equal("lowestPrice")
    spot_fleet_config["FulfilledCapacity"].should.equal(6.0)

    len(spot_fleet_config["LaunchSpecifications"]).should.equal(2)
    launch_spec = spot_fleet_config["LaunchSpecifications"][0]

    launch_spec["EbsOptimized"].should.equal(False)
    launch_spec["SecurityGroups"].should.equal([{"GroupId": "sg-123"}])
    launch_spec["IamInstanceProfile"].should.equal(
        {"Arn": "arn:aws:iam::{}:role/fleet".format(ACCOUNT_ID)}
    )
    launch_spec["ImageId"].should.equal(EXAMPLE_AMI_ID)
    launch_spec["InstanceType"].should.equal("t2.small")
    launch_spec["KeyName"].should.equal("my-key")
    launch_spec["Monitoring"].should.equal({"Enabled": True})
    launch_spec["SpotPrice"].should.equal("0.13")
    launch_spec["SubnetId"].should.equal(subnet_id)
    launch_spec["UserData"].should.equal("some user data")
    launch_spec["WeightedCapacity"].should.equal(2.0)

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(3)


@mock_ec2
def test_create_diversified_spot_fleet():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)
    diversified_config = spot_config(subnet_id, allocation_strategy="diversified")

    spot_fleet_res = conn.request_spot_fleet(SpotFleetRequestConfig=diversified_config)
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(2)
    instance_types = set([instance["InstanceType"] for instance in instances])
    instance_types.should.equal(set(["t2.small", "t2.large"]))
    instances[0]["InstanceId"].should.contain("i-")


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
    spot_fleet_config["LaunchSpecifications"][0]["TagSpecifications"][0][
        "ResourceType"
    ].should.equal("instance")
    for tag in tag_spec[0]["Tags"]:
        spot_fleet_config["LaunchSpecifications"][0]["TagSpecifications"][0][
            "Tags"
        ].should.contain(tag)

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = conn.describe_instances(
        InstanceIds=[i["InstanceId"] for i in instance_res["ActiveInstances"]]
    )
    for instance in instances["Reservations"][0]["Instances"]:
        for tag in tag_spec[0]["Tags"]:
            instance["Tags"].should.contain(tag)


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
    len(spot_fleet_requests).should.equal(0)


@mock_ec2
def test_modify_spot_fleet_request_up():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    conn.modify_spot_fleet_request(SpotFleetRequestId=spot_fleet_id, TargetCapacity=20)

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(10)

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    spot_fleet_config["TargetCapacity"].should.equal(20)
    spot_fleet_config["FulfilledCapacity"].should.equal(20.0)


@mock_ec2
def test_modify_spot_fleet_request_up_diversified():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id, allocation_strategy="diversified")
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    conn.modify_spot_fleet_request(SpotFleetRequestId=spot_fleet_id, TargetCapacity=19)

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(7)

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    spot_fleet_config["TargetCapacity"].should.equal(19)
    spot_fleet_config["FulfilledCapacity"].should.equal(20.0)


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

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(3)

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    spot_fleet_config["TargetCapacity"].should.equal(1)
    spot_fleet_config["FulfilledCapacity"].should.equal(6.0)


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

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(3)

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    spot_fleet_config["TargetCapacity"].should.equal(5)
    spot_fleet_config["FulfilledCapacity"].should.equal(6.0)


@mock_ec2
def test_modify_spot_fleet_request_down():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    conn.modify_spot_fleet_request(SpotFleetRequestId=spot_fleet_id, TargetCapacity=1)

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(1)

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    spot_fleet_config["TargetCapacity"].should.equal(1)
    spot_fleet_config["FulfilledCapacity"].should.equal(2.0)


@mock_ec2
def test_modify_spot_fleet_request_down_no_terminate_after_custom_terminate():
    conn = boto3.client("ec2", region_name="us-west-2")
    subnet_id = get_subnet_id(conn)

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=spot_config(subnet_id)
    )
    spot_fleet_id = spot_fleet_res["SpotFleetRequestId"]

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res["ActiveInstances"]
    conn.terminate_instances(InstanceIds=[i["InstanceId"] for i in instances[1:]])

    conn.modify_spot_fleet_request(
        SpotFleetRequestId=spot_fleet_id,
        TargetCapacity=1,
        ExcessCapacityTerminationPolicy="noTermination",
    )

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res["ActiveInstances"]
    len(instances).should.equal(1)

    spot_fleet_config = conn.describe_spot_fleet_requests(
        SpotFleetRequestIds=[spot_fleet_id]
    )["SpotFleetRequestConfigs"][0]["SpotFleetRequestConfig"]
    spot_fleet_config["TargetCapacity"].should.equal(1)
    spot_fleet_config["FulfilledCapacity"].should.equal(2.0)


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
    len(spot_fleet_requests).should.equal(1)
    spot_fleet_request = spot_fleet_requests[0]
    spot_fleet_config = spot_fleet_request["SpotFleetRequestConfig"]

    len(spot_fleet_config["LaunchSpecifications"]).should.equal(2)
    launch_spec1 = spot_fleet_config["LaunchSpecifications"][0]
    launch_spec2 = spot_fleet_config["LaunchSpecifications"][1]

    # AWS will figure out the price
    assert "SpotPrice" not in launch_spec1
    assert "SpotPrice" not in launch_spec2
