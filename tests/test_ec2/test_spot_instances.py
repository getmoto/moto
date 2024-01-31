import datetime
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core.utils import iso_8601_datetime_with_milliseconds
from tests import EXAMPLE_AMI_ID


@mock_aws
def test_request_spot_instances():
    conn = boto3.client("ec2", "us-east-1")
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = conn.create_subnet(
        VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/16", AvailabilityZone="us-east-1a"
    )["Subnet"]
    subnet_id = subnet["SubnetId"]

    sec_name_1 = str(uuid4())
    sec_name_2 = str(uuid4())
    conn.create_security_group(GroupName=sec_name_1, Description="description")
    conn.create_security_group(GroupName=sec_name_2, Description="description")

    start_dt = datetime.datetime(2013, 1, 1).replace(tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2013, 1, 2).replace(tzinfo=datetime.timezone.utc)
    start = iso_8601_datetime_with_milliseconds(start_dt)
    end = iso_8601_datetime_with_milliseconds(end_dt)

    with pytest.raises(ClientError) as ex:
        request = conn.request_spot_instances(
            SpotPrice="0.5",
            InstanceCount=1,
            Type="one-time",
            ValidFrom=start,
            ValidUntil=end,
            LaunchGroup="the-group",
            AvailabilityZoneGroup="my-group",
            LaunchSpecification={
                "ImageId": EXAMPLE_AMI_ID,
                "KeyName": "test",
                "SecurityGroups": [sec_name_1, sec_name_2],
                "UserData": "some test data",
                "InstanceType": "m1.small",
                "Placement": {"AvailabilityZone": "us-east-1c"},
                "KernelId": "test-kernel",
                "RamdiskId": "test-ramdisk",
                "Monitoring": {"Enabled": True},
                "SubnetId": subnet_id,
            },
            DryRun=True,
        )
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the RequestSpotInstances operation: Request would have succeeded, but DryRun flag is set"
    )

    request = conn.request_spot_instances(
        SpotPrice="0.5",
        InstanceCount=1,
        Type="one-time",
        ValidFrom=start,
        ValidUntil=end,
        LaunchGroup="the-group",
        AvailabilityZoneGroup="my-group",
        LaunchSpecification={
            "ImageId": EXAMPLE_AMI_ID,
            "KeyName": "test",
            "SecurityGroups": [sec_name_1, sec_name_2],
            "UserData": "some test data",
            "InstanceType": "m1.small",
            "Placement": {"AvailabilityZone": "us-east-1c"},
            "KernelId": "test-kernel",
            "RamdiskId": "test-ramdisk",
            "Monitoring": {"Enabled": True},
            "SubnetId": subnet_id,
        },
    )
    request_id = request["SpotInstanceRequests"][0]["SpotInstanceRequestId"]

    all_requests = conn.describe_spot_instance_requests()["SpotInstanceRequests"]
    requests = [r for r in all_requests if r["SpotInstanceRequestId"] == request_id]
    assert len(requests) == 1
    request = requests[0]

    assert request["State"] == "active"
    assert request["SpotPrice"] == "0.500000"
    assert request["Type"] == "one-time"
    assert request["ValidFrom"] == start_dt
    assert request["ValidUntil"] == end_dt
    assert request["LaunchGroup"] == "the-group"
    assert request["AvailabilityZoneGroup"] == "my-group"

    launch_spec = request["LaunchSpecification"]
    security_group_names = [
        group["GroupName"] for group in launch_spec["SecurityGroups"]
    ]
    assert set(security_group_names) == set([sec_name_1, sec_name_2])

    assert launch_spec["ImageId"] == EXAMPLE_AMI_ID
    assert launch_spec["KeyName"] == "test"
    assert launch_spec["InstanceType"] == "m1.small"
    assert launch_spec["KernelId"] == "test-kernel"
    assert launch_spec["RamdiskId"] == "test-ramdisk"
    assert launch_spec["SubnetId"] == subnet_id


@mock_aws
def test_request_spot_instances_default_arguments():
    """
    Test that moto set the correct default arguments
    """
    conn = boto3.client("ec2", "us-east-1")

    request = conn.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    request_id = request["SpotInstanceRequests"][0]["SpotInstanceRequestId"]

    all_requests = conn.describe_spot_instance_requests()["SpotInstanceRequests"]
    requests = [r for r in all_requests if r["SpotInstanceRequestId"] == request_id]
    assert len(requests) == 1
    request = requests[0]

    assert request["State"] == "active"
    assert request["SpotPrice"] == "0.500000"
    assert request["Type"] == "one-time"
    assert "ValidFrom" not in request
    assert "ValidUntil" not in request
    assert "LaunchGroup" not in request
    assert "AvailabilityZoneGroup" not in request
    assert request["InstanceInterruptionBehavior"] == "terminate"

    launch_spec = request["LaunchSpecification"]

    security_group_names = [
        group["GroupName"] for group in launch_spec["SecurityGroups"]
    ]
    assert security_group_names == ["default"]

    assert launch_spec["ImageId"] == EXAMPLE_AMI_ID
    assert "KeyName" not in request
    assert launch_spec["InstanceType"] == "m1.small"
    assert "KernelId" not in request
    assert "RamdiskId" not in request
    assert "SubnetId" not in request


@mock_aws
def test_cancel_spot_instance_request():
    client = boto3.client("ec2", region_name="us-west-1")

    rsi = client.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    spot_id = rsi["SpotInstanceRequests"][0]["SpotInstanceRequestId"]

    requests = client.describe_spot_instance_requests(SpotInstanceRequestIds=[spot_id])[
        "SpotInstanceRequests"
    ]
    assert len(requests) == 1
    request = requests[0]
    assert "CreateTime" in request
    assert request["Type"] == "one-time"
    assert "SpotInstanceRequestId" in request
    assert request["SpotPrice"] == "0.500000"
    assert request["LaunchSpecification"]["ImageId"] == EXAMPLE_AMI_ID

    with pytest.raises(ClientError) as ex:
        client.cancel_spot_instance_requests(
            SpotInstanceRequestIds=[request["SpotInstanceRequestId"]], DryRun=True
        )
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CancelSpotInstanceRequests operation: Request would have succeeded, but DryRun flag is set"
    )

    client.cancel_spot_instance_requests(
        SpotInstanceRequestIds=[request["SpotInstanceRequestId"]]
    )

    requests = client.describe_spot_instance_requests(SpotInstanceRequestIds=[spot_id])[
        "SpotInstanceRequests"
    ]
    assert len(requests) == 0


@mock_aws
def test_request_spot_instances_fulfilled():
    """
    Test that moto correctly fullfills a spot instance request
    """
    client = boto3.client("ec2", region_name="us-east-1")

    request = client.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    request_id = request["SpotInstanceRequests"][0]["SpotInstanceRequestId"]

    requests = client.describe_spot_instance_requests(
        SpotInstanceRequestIds=[request_id]
    )["SpotInstanceRequests"]
    assert len(requests) == 1
    request = requests[0]

    assert request["State"] == "active"


@mock_aws
def test_tag_spot_instance_request():
    """
    Test that moto correctly tags a spot instance request
    """
    client = boto3.client("ec2", region_name="us-west-1")

    request = client.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    request_id = request["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
    client.create_tags(
        Resources=[request_id],
        Tags=[{"Key": "tag1", "Value": "value1"}, {"Key": "tag2", "Value": "value2"}],
    )

    requests = client.describe_spot_instance_requests(
        SpotInstanceRequestIds=[request_id]
    )["SpotInstanceRequests"]
    assert len(requests) == 1
    request = requests[0]

    assert len(request["Tags"]) == 2
    assert {"Key": "tag1", "Value": "value1"} in request["Tags"]
    assert {"Key": "tag2", "Value": "value2"} in request["Tags"]


@mock_aws
def test_get_all_spot_instance_requests_filtering():
    """
    Test that moto correctly filters spot instance requests
    """
    client = boto3.client("ec2", region_name="us-west-1")

    request1 = client.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    request1_id = request1["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
    request2 = client.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    request2_id = request2["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
    client.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    tag_value1 = str(uuid4())
    client.create_tags(
        Resources=[request1_id],
        Tags=[{"Key": "tag1", "Value": tag_value1}, {"Key": "tag2", "Value": "value2"}],
    )
    client.create_tags(
        Resources=[request2_id],
        Tags=[{"Key": "tag1", "Value": tag_value1}, {"Key": "tag2", "Value": "wrong"}],
    )

    requests = client.describe_spot_instance_requests(
        Filters=[{"Name": "state", "Values": ["failed"]}]
    )["SpotInstanceRequests"]
    r_ids = [r["SpotInstanceRequestId"] for r in requests]
    assert request1_id not in r_ids
    assert request2_id not in r_ids

    requests = client.describe_spot_instance_requests(
        Filters=[{"Name": "state", "Values": ["active"]}]
    )["SpotInstanceRequests"]
    r_ids = [r["SpotInstanceRequestId"] for r in requests]
    assert request1_id in r_ids
    assert request2_id in r_ids

    requests = client.describe_spot_instance_requests(
        Filters=[{"Name": "tag:tag1", "Values": [tag_value1]}]
    )["SpotInstanceRequests"]
    assert len(requests) == 2

    requests = client.describe_spot_instance_requests(
        Filters=[
            {"Name": "tag:tag1", "Values": [tag_value1]},
            {"Name": "tag:tag2", "Values": ["value2"]},
        ]
    )["SpotInstanceRequests"]
    assert len(requests) == 1


@mock_aws
@pytest.mark.filterwarnings("ignore")
def test_request_spot_instances_instance_lifecycle():
    if settings.TEST_SERVER_MODE:
        # Currently no easy way to check which instance was created by request_spot_instance
        # And we can't just pick the first instance in ServerMode and expect it to be the right one
        raise SkipTest("ServerMode is not guaranteed to be empty")
    client = boto3.client("ec2", region_name="us-east-1")
    client.request_spot_instances(SpotPrice="0.5")

    response = client.describe_instances()

    instance = response["Reservations"][0]["Instances"][0]
    assert instance["InstanceLifecycle"] == "spot"


@mock_aws
@pytest.mark.filterwarnings("ignore")
def test_request_spot_instances_with_tags():
    client = boto3.client("ec2", region_name="us-east-1")
    request = client.request_spot_instances(
        SpotPrice="0.5",
        TagSpecifications=[
            {
                "ResourceType": "spot-instances-request",
                "Tags": [{"Key": "k", "Value": "v"}],
            }
        ],
    )

    request_id = request["SpotInstanceRequests"][0]["SpotInstanceRequestId"]

    request = client.describe_spot_instance_requests(
        SpotInstanceRequestIds=[request_id]
    )["SpotInstanceRequests"][0]
    assert request["Tags"] == [{"Key": "k", "Value": "v"}]


@mock_aws
def test_launch_spot_instance_instance_lifecycle():
    client = boto3.client("ec2", region_name="us-east-1")

    kwargs = {
        "KeyName": "foobar",
        "ImageId": EXAMPLE_AMI_ID,
        "MinCount": 1,
        "MaxCount": 1,
        "InstanceType": "c4.2xlarge",
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": [{"Key": "key", "Value": "val"}]},
        ],
        "InstanceMarketOptions": {"MarketType": "spot"},
    }

    instance = client.run_instances(**kwargs)["Instances"][0]
    instance_id = instance["InstanceId"]

    response = client.describe_instances(InstanceIds=[instance_id])
    instance = response["Reservations"][0]["Instances"][0]
    assert instance["InstanceLifecycle"] == "spot"


@mock_aws
def test_launch_instance_instance_lifecycle():
    client = boto3.client("ec2", region_name="us-east-1")

    kwargs = {
        "KeyName": "foobar",
        "ImageId": EXAMPLE_AMI_ID,
        "MinCount": 1,
        "MaxCount": 1,
        "InstanceType": "c4.2xlarge",
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": [{"Key": "key", "Value": "val"}]},
        ],
    }

    instance = client.run_instances(**kwargs)["Instances"][0]
    instance_id = instance["InstanceId"]

    response = client.describe_instances(InstanceIds=[instance_id])
    instance = response["Reservations"][0]["Instances"][0]
    assert instance.get("InstanceLifecycle") is None


@mock_aws
def test_spot_price_history():
    client = boto3.client("ec2", region_name="us-east-1")
    # test filter
    response = client.describe_spot_price_history(
        Filters=[
            {"Name": "availability-zone", "Values": ["us-east-1a"]},
            {"Name": "instance-type", "Values": ["t3a.micro"]},
        ]
    )
    price = response["SpotPriceHistory"][0]
    assert price["InstanceType"] == "t3a.micro"
    assert price["AvailabilityZone"] == "us-east-1a"

    # test instance types
    i_types = ["t3a.micro", "t3.micro"]
    response = client.describe_spot_price_history(InstanceTypes=i_types)
    price = response["SpotPriceHistory"][0]
    assert price["InstanceType"] in i_types


@mock_aws
def test_request_spot_instances__instance_should_exist():
    client = boto3.client("ec2", region_name="us-east-1")
    request = client.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    request_id = request["SpotInstanceRequests"][0]["SpotInstanceRequestId"]

    request = client.describe_spot_instance_requests(
        SpotInstanceRequestIds=[request_id]
    )["SpotInstanceRequests"][0]
    assert "InstanceId" in request
    instance_id = request["InstanceId"]

    response = client.describe_instances(InstanceIds=[instance_id])
    instance = response["Reservations"][0]["Instances"][0]
    assert instance["InstanceId"] == instance_id
    assert instance["ImageId"] == EXAMPLE_AMI_ID
