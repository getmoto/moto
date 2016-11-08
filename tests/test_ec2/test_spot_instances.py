from __future__ import unicode_literals
from nose.tools import assert_raises
import datetime

import boto
import boto3
import sure  # noqa
from boto.exception import JSONResponseError

from moto import mock_ec2
from moto.backends import get_model
from moto.core.utils import iso_8601_datetime_with_milliseconds


@mock_ec2
def test_request_spot_instances():
    conn = boto3.client('ec2', 'us-east-1')
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/8")['Vpc']
    subnet = conn.create_subnet(VpcId=vpc['VpcId'], CidrBlock='10.0.0.0/16', AvailabilityZone='us-east-1a')['Subnet']
    subnet_id = subnet['SubnetId']

    conn = boto.connect_ec2()

    conn.create_security_group('group1', 'description')
    conn.create_security_group('group2', 'description')

    start = iso_8601_datetime_with_milliseconds(datetime.datetime(2013, 1, 1))
    end = iso_8601_datetime_with_milliseconds(datetime.datetime(2013, 1, 2))

    with assert_raises(JSONResponseError) as ex:
        request = conn.request_spot_instances(
            price=0.5, image_id='ami-abcd1234', count=1, type='one-time',
            valid_from=start, valid_until=end, launch_group="the-group",
            availability_zone_group='my-group', key_name="test",
            security_groups=['group1', 'group2'], user_data=b"some test data",
            instance_type='m1.small', placement='us-east-1c',
            kernel_id="test-kernel", ramdisk_id="test-ramdisk",
            monitoring_enabled=True, subnet_id=subnet_id, dry_run=True
        )
    ex.exception.reason.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal('An error occurred (DryRunOperation) when calling the RequestSpotInstance operation: Request would have succeeded, but DryRun flag is set')

    request = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234', count=1, type='one-time',
        valid_from=start, valid_until=end, launch_group="the-group",
        availability_zone_group='my-group', key_name="test",
        security_groups=['group1', 'group2'], user_data=b"some test data",
        instance_type='m1.small', placement='us-east-1c',
        kernel_id="test-kernel", ramdisk_id="test-ramdisk",
        monitoring_enabled=True, subnet_id=subnet_id,
    )

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    request.state.should.equal("open")
    request.price.should.equal(0.5)
    request.launch_specification.image_id.should.equal('ami-abcd1234')
    request.type.should.equal('one-time')
    request.valid_from.should.equal(start)
    request.valid_until.should.equal(end)
    request.launch_group.should.equal("the-group")
    request.availability_zone_group.should.equal('my-group')
    request.launch_specification.key_name.should.equal("test")
    security_group_names = [group.name for group in request.launch_specification.groups]
    set(security_group_names).should.equal(set(['group1', 'group2']))
    request.launch_specification.instance_type.should.equal('m1.small')
    request.launch_specification.placement.should.equal('us-east-1c')
    request.launch_specification.kernel.should.equal("test-kernel")
    request.launch_specification.ramdisk.should.equal("test-ramdisk")
    request.launch_specification.subnet_id.should.equal(subnet_id)


@mock_ec2
def test_request_spot_instances_default_arguments():
    """
    Test that moto set the correct default arguments
    """
    conn = boto.connect_ec2()

    request = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234',
    )

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    request.state.should.equal("open")
    request.price.should.equal(0.5)
    request.launch_specification.image_id.should.equal('ami-abcd1234')
    request.type.should.equal('one-time')
    request.valid_from.should.equal(None)
    request.valid_until.should.equal(None)
    request.launch_group.should.equal(None)
    request.availability_zone_group.should.equal(None)
    request.launch_specification.key_name.should.equal(None)
    security_group_names = [group.name for group in request.launch_specification.groups]
    security_group_names.should.equal(["default"])
    request.launch_specification.instance_type.should.equal('m1.small')
    request.launch_specification.placement.should.equal(None)
    request.launch_specification.kernel.should.equal(None)
    request.launch_specification.ramdisk.should.equal(None)
    request.launch_specification.subnet_id.should.equal(None)


@mock_ec2
def test_cancel_spot_instance_request():
    conn = boto.connect_ec2()

    conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234',
    )

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)


    with assert_raises(JSONResponseError) as ex:
        conn.cancel_spot_instance_requests([requests[0].id], dry_run=True)
    ex.exception.reason.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal('An error occurred (DryRunOperation) when calling the CancelSpotInstance operation: Request would have succeeded, but DryRun flag is set')

    conn.cancel_spot_instance_requests([requests[0].id])

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(0)


@mock_ec2
def test_request_spot_instances_fulfilled():
    """
    Test that moto correctly fullfills a spot instance request
    """
    conn = boto.ec2.connect_to_region("us-east-1")

    request = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234',
    )

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    request.state.should.equal("open")

    get_model('SpotInstanceRequest')[0].state = 'active'

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    request.state.should.equal("active")


@mock_ec2
def test_tag_spot_instance_request():
    """
    Test that moto correctly tags a spot instance request
    """
    conn = boto.connect_ec2()

    request = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234',
    )
    request[0].add_tag('tag1', 'value1')
    request[0].add_tag('tag2', 'value2')

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    tag_dict = dict(request.tags)
    tag_dict.should.equal({'tag1': 'value1', 'tag2': 'value2'})


@mock_ec2
def test_get_all_spot_instance_requests_filtering():
    """
    Test that moto correctly filters spot instance requests
    """
    conn = boto.connect_ec2()

    request1 = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234',
    )
    request2 = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234',
    )
    conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234',
    )
    request1[0].add_tag('tag1', 'value1')
    request1[0].add_tag('tag2', 'value2')
    request2[0].add_tag('tag1', 'value1')
    request2[0].add_tag('tag2', 'wrong')

    requests = conn.get_all_spot_instance_requests(filters={'state': 'active'})
    requests.should.have.length_of(0)

    requests = conn.get_all_spot_instance_requests(filters={'state': 'open'})
    requests.should.have.length_of(3)

    requests = conn.get_all_spot_instance_requests(filters={'tag:tag1': 'value1'})
    requests.should.have.length_of(2)

    requests = conn.get_all_spot_instance_requests(filters={'tag:tag1': 'value1', 'tag:tag2': 'value2'})
    requests.should.have.length_of(1)


@mock_ec2
def test_request_spot_instances_setting_instance_id():
    conn = boto.ec2.connect_to_region("us-east-1")
    request = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234')

    req = get_model('SpotInstanceRequest')[0]
    req.state = 'active'
    req.instance_id = 'i-12345678'

    request = conn.get_all_spot_instance_requests()[0]
    assert request.state == 'active'
    assert request.instance_id == 'i-12345678'

