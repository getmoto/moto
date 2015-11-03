from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

from moto.ec2 import ec2_backends
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


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
def test_filter_volume_by_id():
    conn = boto.connect_ec2('the_key', 'the_secret')
    volume1 = conn.create_volume(80, "us-east-1a")
    volume2 = conn.create_volume(36, "us-east-1b")
    volume3 = conn.create_volume(20, "us-east-1c")
    vol1 = conn.get_all_volumes(volume_ids=volume3.id)
    vol1.should.have.length_of(1)
    vol1[0].size.should.equal(20)
    vol1[0].zone.should.equal('us-east-1c')
    vol2 = conn.get_all_volumes(volume_ids=[volume1.id, volume2.id])
    vol2.should.have.length_of(2)


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

    snapshot = volume.create_snapshot('a test snapshot')
    snapshot.update()
    snapshot.status.should.equal('completed')

    snapshots = conn.get_all_snapshots()
    snapshots.should.have.length_of(1)
    snapshots[0].description.should.equal('a test snapshot')
    snapshots[0].start_time.should_not.be.none

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
def test_filter_snapshot_by_id():
    conn = boto.connect_ec2('the_key', 'the_secret')
    volume1 = conn.create_volume(36, "us-east-1a")
    snap1 = volume1.create_snapshot('a test snapshot 1')
    volume2 = conn.create_volume(42, 'us-east-1a')
    snap2 = volume2.create_snapshot('a test snapshot 2')
    volume3 = conn.create_volume(84, 'us-east-1a')
    snap3 = volume3.create_snapshot('a test snapshot 3')
    snapshots1 = conn.get_all_snapshots(snapshot_ids=snap2.id)
    snapshots1.should.have.length_of(1)
    snapshots1[0].volume_id.should.equal(volume2.id)
    snapshots1[0].region.name.should.equal(conn.region.name)
    snapshots2 = conn.get_all_snapshots(snapshot_ids=[snap2.id, snap3.id])
    snapshots2.should.have.length_of(2)
    for s in snapshots2:
        s.start_time.should_not.be.none
        s.volume_id.should.be.within([volume2.id, volume3.id])
        s.region.name.should.equal(conn.region.name)

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
    conn = boto.ec2.connect_to_region("us-east-1")

    reservation = conn.run_instances('ami-1234abcd')

    instance = reservation.instances[0]

    instance.modify_attribute('blockDeviceMapping', {'/dev/sda1': True})

    instance = ec2_backends[conn.region.name].get_instance(instance.id)
    instance.block_device_mapping.should.have.key('/dev/sda1')
    instance.block_device_mapping['/dev/sda1'].delete_on_termination.should.be(True)


@mock_ec2
def test_volume_tag_escaping():
    conn = boto.connect_ec2('the_key', 'the_secret')
    vol = conn.create_volume(10, 'us-east-1a')
    snapshot = conn.create_snapshot(vol.id, 'Desc')
    snapshot.add_tags({'key': '</closed>'})

    dict(conn.get_all_snapshots()[0].tags).should.equal({'key': '</closed>'})
