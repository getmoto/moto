import datetime

import boto
import sure  # noqa

from moto import mock_ec2
from moto.core.utils import iso_8601_datetime


@mock_ec2
def test_request_spot_instances():
    conn = boto.connect_ec2()

    conn.create_security_group('group1', 'description')
    conn.create_security_group('group2', 'description')

    start = iso_8601_datetime(datetime.datetime(2013, 1, 1))
    end = iso_8601_datetime(datetime.datetime(2013, 1, 2))

    request = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234', count=1, type='one-time',
        valid_from=start, valid_until=end, launch_group="the-group",
        availability_zone_group='my-group', key_name="test",
        security_groups=['group1', 'group2'], user_data="some test data",
        instance_type='m1.small', placement='us-east-1c',
        kernel_id="test-kernel", ramdisk_id="test-ramdisk",
        monitoring_enabled=True, subnet_id="subnet123",
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
    request.launch_specification.subnet_id.should.equal("subnet123")


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

    conn.cancel_spot_instance_requests([requests[0].id])

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(0)
