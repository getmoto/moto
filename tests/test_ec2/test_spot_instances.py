import pytest
import datetime

import boto3
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ec2, settings
from moto.core.utils import iso_8601_datetime_with_milliseconds
from tests import EXAMPLE_AMI_ID
from uuid import uuid4
from unittest import SkipTest


@mock_ec2
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
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the RequestSpotInstances operation: Request would have succeeded, but DryRun flag is set"
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
    requests.should.have.length_of(1)
    request = requests[0]

    request["State"].should.equal("active")
    request["SpotPrice"].should.equal("0.500000")
    request["Type"].should.equal("one-time")
    request["ValidFrom"].should.equal(start_dt)
    request["ValidUntil"].should.equal(end_dt)
    request["LaunchGroup"].should.equal("the-group")
    request["AvailabilityZoneGroup"].should.equal("my-group")

    launch_spec = request["LaunchSpecification"]
    security_group_names = [
        group["GroupName"] for group in launch_spec["SecurityGroups"]
    ]
    set(security_group_names).should.equal(set([sec_name_1, sec_name_2]))

    launch_spec["ImageId"].should.equal(EXAMPLE_AMI_ID)
    launch_spec["KeyName"].should.equal("test")
    launch_spec["InstanceType"].should.equal("m1.small")
    launch_spec["KernelId"].should.equal("test-kernel")
    launch_spec["RamdiskId"].should.equal("test-ramdisk")
    launch_spec["SubnetId"].should.equal(subnet_id)


@mock_ec2
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
    requests.should.have.length_of(1)
    request = requests[0]

    request["State"].should.equal("active")
    request["SpotPrice"].should.equal("0.500000")
    request["Type"].should.equal("one-time")
    request.shouldnt.contain("ValidFrom")
    request.shouldnt.contain("ValidUntil")
    request.shouldnt.contain("LaunchGroup")
    request.shouldnt.contain("AvailabilityZoneGroup")
    request.should.have.key("InstanceInterruptionBehavior").equals("terminate")

    launch_spec = request["LaunchSpecification"]

    security_group_names = [
        group["GroupName"] for group in launch_spec["SecurityGroups"]
    ]
    security_group_names.should.equal(["default"])

    launch_spec["ImageId"].should.equal(EXAMPLE_AMI_ID)
    request.shouldnt.contain("KeyName")
    launch_spec["InstanceType"].should.equal("m1.small")
    request.shouldnt.contain("KernelId")
    request.shouldnt.contain("RamdiskId")
    request.shouldnt.contain("SubnetId")


@mock_ec2
def test_cancel_spot_instance_request():
    client = boto3.client("ec2", region_name="us-west-1")

    rsi = client.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    spot_id = rsi["SpotInstanceRequests"][0]["SpotInstanceRequestId"]

    requests = client.describe_spot_instance_requests(SpotInstanceRequestIds=[spot_id])[
        "SpotInstanceRequests"
    ]
    requests.should.have.length_of(1)
    request = requests[0]
    request.should.have.key("CreateTime")
    request.should.have.key("Type").equal("one-time")
    request.should.have.key("SpotInstanceRequestId")
    request.should.have.key("SpotPrice").equal("0.500000")
    request["LaunchSpecification"]["ImageId"].should.equal(EXAMPLE_AMI_ID)

    with pytest.raises(ClientError) as ex:
        client.cancel_spot_instance_requests(
            SpotInstanceRequestIds=[request["SpotInstanceRequestId"]], DryRun=True
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CancelSpotInstanceRequests operation: Request would have succeeded, but DryRun flag is set"
    )

    client.cancel_spot_instance_requests(
        SpotInstanceRequestIds=[request["SpotInstanceRequestId"]]
    )

    requests = client.describe_spot_instance_requests(SpotInstanceRequestIds=[spot_id])[
        "SpotInstanceRequests"
    ]
    requests.should.have.length_of(0)


@mock_ec2
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
    requests.should.have.length_of(1)
    request = requests[0]

    request["State"].should.equal("active")


@mock_ec2
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
    requests.should.have.length_of(1)
    request = requests[0]

    request["Tags"].should.have.length_of(2)
    request["Tags"].should.contain({"Key": "tag1", "Value": "value1"})
    request["Tags"].should.contain({"Key": "tag2", "Value": "value2"})


@mock_ec2
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
    r_ids.shouldnt.contain(request1_id)
    r_ids.shouldnt.contain(request2_id)

    requests = client.describe_spot_instance_requests(
        Filters=[{"Name": "state", "Values": ["active"]}]
    )["SpotInstanceRequests"]
    r_ids = [r["SpotInstanceRequestId"] for r in requests]
    r_ids.should.contain(request1_id)
    r_ids.should.contain(request2_id)

    requests = client.describe_spot_instance_requests(
        Filters=[{"Name": "tag:tag1", "Values": [tag_value1]}]
    )["SpotInstanceRequests"]
    requests.should.have.length_of(2)

    requests = client.describe_spot_instance_requests(
        Filters=[
            {"Name": "tag:tag1", "Values": [tag_value1]},
            {"Name": "tag:tag2", "Values": ["value2"]},
        ]
    )["SpotInstanceRequests"]
    requests.should.have.length_of(1)


@mock_ec2
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
    instance["InstanceLifecycle"].should.equal("spot")


@mock_ec2
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
    request.should.have.key("Tags").equals([{"Key": "k", "Value": "v"}])


@mock_ec2
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
    instance["InstanceLifecycle"].should.equal("spot")


@mock_ec2
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
    instance.get("InstanceLifecycle").should.equal(None)


@mock_ec2
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
    price["InstanceType"].should.equal("t3a.micro")
    price["AvailabilityZone"].should.equal("us-east-1a")

    # test instance types
    i_types = ["t3a.micro", "t3.micro"]
    response = client.describe_spot_price_history(InstanceTypes=i_types)
    price = response["SpotPriceHistory"][0]
    assert price["InstanceType"] in i_types


@mock_ec2
def test_request_spot_instances__instance_should_exist():
    client = boto3.client("ec2", region_name="us-east-1")
    request = client.request_spot_instances(
        SpotPrice="0.5", LaunchSpecification={"ImageId": EXAMPLE_AMI_ID}
    )
    request_id = request["SpotInstanceRequests"][0]["SpotInstanceRequestId"]

    request = client.describe_spot_instance_requests(
        SpotInstanceRequestIds=[request_id]
    )["SpotInstanceRequests"][0]
    request.should.have.key("InstanceId")
    instance_id = request["InstanceId"]

    response = client.describe_instances(InstanceIds=[instance_id])
    instance = response["Reservations"][0]["Instances"][0]
    instance.should.have.key("InstanceId").equals(instance_id)
    instance.should.have.key("ImageId").equals(EXAMPLE_AMI_ID)
