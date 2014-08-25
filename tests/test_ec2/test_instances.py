import base64

import boto
from boto.ec2.instance import Reservation, InstanceAttribute
from boto.exception import EC2ResponseError
import sure  # noqa
from nose.tools import assert_raises

from moto import mock_ec2


################ Test Readme ###############
def add_servers(ami_id, count):
    conn = boto.connect_ec2()
    for index in range(count):
        conn.run_instances(ami_id)


@mock_ec2
def test_add_servers():
    add_servers('ami-1234abcd', 2)

    conn = boto.connect_ec2()
    reservations = conn.get_all_instances()
    assert len(reservations) == 2
    instance1 = reservations[0].instances[0]
    assert instance1.image_id == 'ami-1234abcd'

############################################


@mock_ec2
def test_instance_launch_and_terminate():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    reservation.should.be.a(Reservation)
    reservation.instances.should.have.length_of(1)
    instance = reservation.instances[0]
    instance.state.should.equal('pending')

    reservations = conn.get_all_instances()
    reservations.should.have.length_of(1)
    reservations[0].id.should.equal(reservation.id)
    instances = reservations[0].instances
    instances.should.have.length_of(1)
    instances[0].id.should.equal(instance.id)
    instances[0].state.should.equal('running')

    conn.terminate_instances([instances[0].id])

    reservations = conn.get_all_instances()
    instance = reservations[0].instances[0]
    instance.state.should.equal('terminated')


@mock_ec2
def test_get_instances_by_id():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=2)
    instance1, instance2 = reservation.instances

    reservations = conn.get_all_instances(instance_ids=[instance1.id])
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation.instances.should.have.length_of(1)
    reservation.instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_instances(instance_ids=[instance1.id, instance2.id])
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation.instances.should.have.length_of(2)
    instance_ids = [instance.id for instance in reservation.instances]
    instance_ids.should.equal([instance1.id, instance2.id])

    # Call get_all_instances with a bad id should raise an error
    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_instances(instance_ids=[instance1.id, "i-1234abcd"])
    cm.exception.code.should.equal('InvalidInstanceID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_get_instances_filtering_by_state():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances

    conn.terminate_instances([instance1.id])

    reservations = conn.get_all_instances(filters={'instance-state-name': 'running'})
    reservations.should.have.length_of(1)
    # Since we terminated instance1, only instance2 and instance3 should be returned
    instance_ids = [instance.id for instance in reservations[0].instances]
    set(instance_ids).should.equal(set([instance2.id, instance3.id]))

    reservations = conn.get_all_instances([instance2.id], filters={'instance-state-name': 'running'})
    reservations.should.have.length_of(1)
    instance_ids = [instance.id for instance in reservations[0].instances]
    instance_ids.should.equal([instance2.id])

    reservations = conn.get_all_instances([instance2.id], filters={'instance-state-name': 'terminated'})
    list(reservations).should.equal([])

    # get_all_instances should still return all 3
    reservations = conn.get_all_instances()
    reservations[0].instances.should.have.length_of(3)

    conn.get_all_instances.when.called_with(filters={'not-implemented-filter': 'foobar'}).should.throw(NotImplementedError)

@mock_ec2
def test_get_instances_filtering_by_instance_id():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances

    reservations = conn.get_all_instances(filters={'instance-id': instance1.id})
    # get_all_instances should return just instance1
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_instances(filters={'instance-id': [instance1.id, instance2.id]})
    # get_all_instances should return two
    reservations[0].instances.should.have.length_of(2)

    reservations = conn.get_all_instances(filters={'instance-id': 'non-existing-id'})
    reservations.should.have.length_of(0)

@mock_ec2
def test_instance_start_and_stop():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', min_count=2)
    instances = reservation.instances
    instances.should.have.length_of(2)

    instance_ids = [instance.id for instance in instances]
    stopped_instances = conn.stop_instances(instance_ids)

    for instance in stopped_instances:
        instance.state.should.equal('stopping')

    started_instances = conn.start_instances([instances[0].id])
    started_instances[0].state.should.equal('pending')


@mock_ec2
def test_instance_reboot():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    instance.reboot()
    instance.state.should.equal('pending')


@mock_ec2
def test_instance_attribute_instance_type():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.modify_attribute("instanceType", "m1.small")

    instance_attribute = instance.get_attribute("instanceType")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get('instanceType').should.equal("m1.small")


@mock_ec2
def test_instance_attribute_user_data():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.modify_attribute("userData", "this is my user data")

    instance_attribute = instance.get_attribute("userData")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("userData").should.equal("this is my user data")


@mock_ec2
def test_user_data_with_run_instance():
    user_data = "some user data"
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', user_data=user_data)
    instance = reservation.instances[0]

    instance_attribute = instance.get_attribute("userData")
    instance_attribute.should.be.a(InstanceAttribute)
    decoded_user_data = base64.decodestring(instance_attribute.get("userData"))
    decoded_user_data.should.equal("some user data")


@mock_ec2
def test_run_instance_with_security_group_name():
    conn = boto.connect_ec2('the_key', 'the_secret')
    group = conn.create_security_group('group1', "some description")

    reservation = conn.run_instances('ami-1234abcd',
                                     security_groups=['group1'])
    instance = reservation.instances[0]

    instance.groups[0].id.should.equal(group.id)
    instance.groups[0].name.should.equal("group1")


@mock_ec2
def test_run_instance_with_security_group_id():
    conn = boto.connect_ec2('the_key', 'the_secret')
    group = conn.create_security_group('group1', "some description")

    reservation = conn.run_instances('ami-1234abcd',
                                     security_group_ids=[group.id])
    instance = reservation.instances[0]

    instance.groups[0].id.should.equal(group.id)
    instance.groups[0].name.should.equal("group1")


@mock_ec2
def test_run_instance_with_instance_type():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', instance_type="t1.micro")
    instance = reservation.instances[0]

    instance.instance_type.should.equal("t1.micro")


@mock_ec2
def test_run_instance_with_subnet():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd',
                                     subnet_id="subnet-abcd1234")
    instance = reservation.instances[0]

    instance.subnet_id.should.equal("subnet-abcd1234")


@mock_ec2
def test_run_instance_with_keypair():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', key_name="keypair_name")
    instance = reservation.instances[0]

    instance.key_name.should.equal("keypair_name")
