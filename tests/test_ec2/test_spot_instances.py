from __future__ import unicode_literals
from nose.tools import assert_raises
import datetime

import boto
import boto3
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError
import pytz
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated
from moto.backends import get_model
from moto.core.utils import iso_8601_datetime_with_milliseconds


@mock_ec2
def test_request_spot_instances():
    conn = boto3.client("ec2", "us-east-1")
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = conn.create_subnet(
        VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/16", AvailabilityZone="us-east-1a"
    )["Subnet"]
    subnet_id = subnet["SubnetId"]

    conn.create_security_group(GroupName="group1", Description="description")
    conn.create_security_group(GroupName="group2", Description="description")

    start_dt = datetime.datetime(2013, 1, 1).replace(tzinfo=pytz.utc)
    end_dt = datetime.datetime(2013, 1, 2).replace(tzinfo=pytz.utc)
    start = iso_8601_datetime_with_milliseconds(start_dt)
    end = iso_8601_datetime_with_milliseconds(end_dt)

    with assert_raises(ClientError) as ex:
        request = conn.request_spot_instances(
            SpotPrice="0.5",
            InstanceCount=1,
            Type="one-time",
            ValidFrom=start,
            ValidUntil=end,
            LaunchGroup="the-group",
            AvailabilityZoneGroup="my-group",
            LaunchSpecification={
                "ImageId": "ami-abcd1234",
                "KeyName": "test",
                "SecurityGroups": ["group1", "group2"],
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
    ex.exception.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the RequestSpotInstance operation: Request would have succeeded, but DryRun flag is set"
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
            "ImageId": "ami-abcd1234",
            "KeyName": "test",
            "SecurityGroups": ["group1", "group2"],
            "UserData": "some test data",
            "InstanceType": "m1.small",
            "Placement": {"AvailabilityZone": "us-east-1c"},
            "KernelId": "test-kernel",
            "RamdiskId": "test-ramdisk",
            "Monitoring": {"Enabled": True},
            "SubnetId": subnet_id,
        },
    )

    requests = conn.describe_spot_instance_requests()["SpotInstanceRequests"]
    requests.should.have.length_of(1)
    request = requests[0]

    request["State"].should.equal("open")
    request["SpotPrice"].should.equal("0.5")
    request["Type"].should.equal("one-time")
    request["ValidFrom"].should.equal(start_dt)
    request["ValidUntil"].should.equal(end_dt)
    request["LaunchGroup"].should.equal("the-group")
    request["AvailabilityZoneGroup"].should.equal("my-group")

    launch_spec = request["LaunchSpecification"]
    security_group_names = [
        group["GroupName"] for group in launch_spec["SecurityGroups"]
    ]
    set(security_group_names).should.equal(set(["group1", "group2"]))

    launch_spec["ImageId"].should.equal("ami-abcd1234")
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
        SpotPrice="0.5", LaunchSpecification={"ImageId": "ami-abcd1234"}
    )

    requests = conn.describe_spot_instance_requests()["SpotInstanceRequests"]
    requests.should.have.length_of(1)
    request = requests[0]

    request["State"].should.equal("open")
    request["SpotPrice"].should.equal("0.5")
    request["Type"].should.equal("one-time")
    request.shouldnt.contain("ValidFrom")
    request.shouldnt.contain("ValidUntil")
    request.shouldnt.contain("LaunchGroup")
    request.shouldnt.contain("AvailabilityZoneGroup")

    launch_spec = request["LaunchSpecification"]

    security_group_names = [
        group["GroupName"] for group in launch_spec["SecurityGroups"]
    ]
    security_group_names.should.equal(["default"])

    launch_spec["ImageId"].should.equal("ami-abcd1234")
    request.shouldnt.contain("KeyName")
    launch_spec["InstanceType"].should.equal("m1.small")
    request.shouldnt.contain("KernelId")
    request.shouldnt.contain("RamdiskId")
    request.shouldnt.contain("SubnetId")


@mock_ec2_deprecated
def test_cancel_spot_instance_request():
    conn = boto.connect_ec2()

    conn.request_spot_instances(price=0.5, image_id="ami-abcd1234")

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)

    with assert_raises(EC2ResponseError) as ex:
        conn.cancel_spot_instance_requests([requests[0].id], dry_run=True)
    ex.exception.error_code.should.equal("DryRunOperation")
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CancelSpotInstance operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.cancel_spot_instance_requests([requests[0].id])

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(0)


@mock_ec2_deprecated
def test_request_spot_instances_fulfilled():
    """
    Test that moto correctly fullfills a spot instance request
    """
    conn = boto.ec2.connect_to_region("us-east-1")

    request = conn.request_spot_instances(price=0.5, image_id="ami-abcd1234")

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    request.state.should.equal("open")

    get_model("SpotInstanceRequest", "us-east-1")[0].state = "active"

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    request.state.should.equal("active")


@mock_ec2_deprecated
def test_tag_spot_instance_request():
    """
    Test that moto correctly tags a spot instance request
    """
    conn = boto.connect_ec2()

    request = conn.request_spot_instances(price=0.5, image_id="ami-abcd1234")
    request[0].add_tag("tag1", "value1")
    request[0].add_tag("tag2", "value2")

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    tag_dict = dict(request.tags)
    tag_dict.should.equal({"tag1": "value1", "tag2": "value2"})


@mock_ec2_deprecated
def test_get_all_spot_instance_requests_filtering():
    """
    Test that moto correctly filters spot instance requests
    """
    conn = boto.connect_ec2()

    request1 = conn.request_spot_instances(price=0.5, image_id="ami-abcd1234")
    request2 = conn.request_spot_instances(price=0.5, image_id="ami-abcd1234")
    conn.request_spot_instances(price=0.5, image_id="ami-abcd1234")
    request1[0].add_tag("tag1", "value1")
    request1[0].add_tag("tag2", "value2")
    request2[0].add_tag("tag1", "value1")
    request2[0].add_tag("tag2", "wrong")

    requests = conn.get_all_spot_instance_requests(filters={"state": "active"})
    requests.should.have.length_of(0)

    requests = conn.get_all_spot_instance_requests(filters={"state": "open"})
    requests.should.have.length_of(3)

    requests = conn.get_all_spot_instance_requests(filters={"tag:tag1": "value1"})
    requests.should.have.length_of(2)

    requests = conn.get_all_spot_instance_requests(
        filters={"tag:tag1": "value1", "tag:tag2": "value2"}
    )
    requests.should.have.length_of(1)


@mock_ec2_deprecated
def test_request_spot_instances_setting_instance_id():
    conn = boto.ec2.connect_to_region("us-east-1")
    request = conn.request_spot_instances(price=0.5, image_id="ami-abcd1234")

    req = get_model("SpotInstanceRequest", "us-east-1")[0]
    req.state = "active"
    req.instance_id = "i-12345678"

    request = conn.get_all_spot_instance_requests()[0]
    assert request.state == "active"
    assert request.instance_id == "i-12345678"
