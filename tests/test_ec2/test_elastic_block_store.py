from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2
from moto.ec2.models import ec2_backend


@mock_ec2
def test_create_and_delete_volume():
    conn = boto.connect_ec2('the_key', 'the_secret')
    volume = conn.create_volume(80, "us-east-1a")

    all_volumes = conn.get_all_volumes()
    all_volumes.should.have.length_of(1)
    all_volumes[0].size.should.equal(80)
    all_volumes[0].zone.should.equal("us-east-1a")

    volume = all_volumes[0]
    volume.delete()

    conn.get_all_volumes().should.have.length_of(0)

    # Deleting something that was already deleted should throw an error
    with assert_raises(EC2ResponseError) as cm:
        volume.delete()
    cm.exception.code.should.equal('InvalidVolume.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_volume_attach_and_detach():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    volume = conn.create_volume(80, "us-east-1a")

    volume.update()
    volume.volume_state().should.equal('available')

    volume.attach(instance.id, "/dev/sdh")

    volume.update()
    volume.volume_state().should.equal('in-use')

    volume.attach_data.instance_id.should.equal(instance.id)

    volume.detach()

    volume.update()
    volume.volume_state().should.equal('available')

    with assert_raises(EC2ResponseError) as cm1:
        volume.attach('i-1234abcd', "/dev/sdh")
    cm1.exception.code.should.equal('InvalidInstanceID.NotFound')
    cm1.exception.status.should.equal(400)
    cm1.exception.request_id.should_not.be.none

    with assert_raises(EC2ResponseError) as cm2:
        conn.detach_volume(volume.id, instance.id, "/dev/sdh")
    cm2.exception.code.should.equal('InvalidAttachment.NotFound')
    cm2.exception.status.should.equal(400)
    cm2.exception.request_id.should_not.be.none

    with assert_raises(EC2ResponseError) as cm3:
        conn.detach_volume(volume.id, 'i-1234abcd', "/dev/sdh")
    cm3.exception.code.should.equal('InvalidInstanceID.NotFound')
    cm3.exception.status.should.equal(400)
    cm3.exception.request_id.should_not.be.none


@mock_ec2
def test_create_snapshot():
    conn = boto.connect_ec2('the_key', 'the_secret')
    volume = conn.create_volume(80, "us-east-1a")

    volume.create_snapshot('a test snapshot')

    snapshots = conn.get_all_snapshots()
    snapshots.should.have.length_of(1)
    snapshots[0].description.should.equal('a test snapshot')

    # Create snapshot without description
    snapshot = volume.create_snapshot()
    conn.get_all_snapshots().should.have.length_of(2)

    snapshot.delete()
    conn.get_all_snapshots().should.have.length_of(1)

    # Deleting something that was already deleted should throw an error
    with assert_raises(EC2ResponseError) as cm:
        snapshot.delete()
    cm.exception.code.should.equal('InvalidSnapshot.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_snapshot_attribute():
    conn = boto.connect_ec2('the_key', 'the_secret')
    volume = conn.create_volume(80, "us-east-1a")
    snapshot = volume.create_snapshot()

    # Baseline
    attributes = conn.get_snapshot_attribute(snapshot.id, attribute='createVolumePermission')
    attributes.name.should.equal('create_volume_permission')
    attributes.attrs.should.have.length_of(0)

    ADD_GROUP_ARGS = {'snapshot_id': snapshot.id,
                      'attribute': 'createVolumePermission',
                      'operation': 'add',
                      'groups': 'all'}

    REMOVE_GROUP_ARGS = {'snapshot_id': snapshot.id,
                         'attribute': 'createVolumePermission',
                         'operation': 'remove',
                         'groups': 'all'}

    # Add 'all' group and confirm
    conn.modify_snapshot_attribute(**ADD_GROUP_ARGS)

    attributes = conn.get_snapshot_attribute(snapshot.id, attribute='createVolumePermission')
    attributes.attrs['groups'].should.have.length_of(1)
    attributes.attrs['groups'].should.equal(['all'])

    # Add is idempotent
    conn.modify_snapshot_attribute.when.called_with(**ADD_GROUP_ARGS).should_not.throw(EC2ResponseError)

    # Remove 'all' group and confirm
    conn.modify_snapshot_attribute(**REMOVE_GROUP_ARGS)

    attributes = conn.get_snapshot_attribute(snapshot.id, attribute='createVolumePermission')
    attributes.attrs.should.have.length_of(0)

    # Remove is idempotent
    conn.modify_snapshot_attribute.when.called_with(**REMOVE_GROUP_ARGS).should_not.throw(EC2ResponseError)

    # Error: Add with group != 'all'
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_snapshot_attribute(snapshot.id,
                                       attribute='createVolumePermission',
                                       operation='add',
                                       groups='everyone')
    cm.exception.code.should.equal('InvalidAMIAttributeItemValue')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Add with invalid snapshot ID
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_snapshot_attribute("snapshot-abcd1234",
                                       attribute='createVolumePermission',
                                       operation='add',
                                       groups='all')
    cm.exception.code.should.equal('InvalidSnapshot.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Remove with invalid snapshot ID
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_snapshot_attribute("snapshot-abcd1234",
                                       attribute='createVolumePermission',
                                       operation='remove',
                                       groups='all')
    cm.exception.code.should.equal('InvalidSnapshot.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Add or remove with user ID instead of group
    conn.modify_snapshot_attribute.when.called_with(snapshot.id,
                                                    attribute='createVolumePermission',
                                                    operation='add',
                                                    user_ids=['user']).should.throw(NotImplementedError)
    conn.modify_snapshot_attribute.when.called_with(snapshot.id,
                                                    attribute='createVolumePermission',
                                                    operation='remove',
                                                    user_ids=['user']).should.throw(NotImplementedError)


@mock_ec2
def test_modify_attribute_blockDeviceMapping():
    """
    Reproduces the missing feature explained at [0], where we want to mock a
    call to modify an instance attribute of type: blockDeviceMapping.

    [0] https://github.com/spulec/moto/issues/160
    """
    conn = boto.connect_ec2('the_key', 'the_secret')

    reservation = conn.run_instances('ami-1234abcd')

    instance = reservation.instances[0]

    instance.modify_attribute('blockDeviceMapping', {'/dev/sda1': True})

    instance = ec2_backend.get_instance(instance.id)
    instance.block_device_mapping.should.have.key('/dev/sda1')
    instance.block_device_mapping['/dev/sda1'].delete_on_termination.should.be(True)
