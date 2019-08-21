from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

from moto.ec2 import ec2_backends
import boto
import boto3
from botocore.exceptions import ClientError
from boto.exception import EC2ResponseError
from freezegun import freeze_time
import sure  # noqa

from moto import mock_ec2_deprecated, mock_ec2
from moto.ec2.models import OWNER_ID


@mock_ec2_deprecated
def test_create_and_delete_volume():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a")

    all_volumes = conn.get_all_volumes()

    current_volume = [item for item in all_volumes if item.id == volume.id]
    current_volume.should.have.length_of(1)
    current_volume[0].size.should.equal(80)
    current_volume[0].zone.should.equal("us-east-1a")
    current_volume[0].encrypted.should.be(False)

    volume = current_volume[0]

    with assert_raises(EC2ResponseError) as ex:
        volume.delete(dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the DeleteVolume operation: Request would have succeeded, but DryRun flag is set')

    volume.delete()

    all_volumes = conn.get_all_volumes()
    my_volume = [item for item in all_volumes if item.id == volume.id]
    my_volume.should.have.length_of(0)

    # Deleting something that was already deleted should throw an error
    with assert_raises(EC2ResponseError) as cm:
        volume.delete()
    cm.exception.code.should.equal('InvalidVolume.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_create_encrypted_volume_dryrun():
    conn = boto.ec2.connect_to_region("us-east-1")
    with assert_raises(EC2ResponseError) as ex:
        conn.create_volume(80, "us-east-1a", encrypted=True, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the CreateVolume operation: Request would have succeeded, but DryRun flag is set')


@mock_ec2_deprecated
def test_create_encrypted_volume():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a", encrypted=True)

    with assert_raises(EC2ResponseError) as ex:
        conn.create_volume(80, "us-east-1a", encrypted=True, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the CreateVolume operation: Request would have succeeded, but DryRun flag is set')

    all_volumes = [vol for vol in conn.get_all_volumes() if vol.id == volume.id]
    all_volumes[0].encrypted.should.be(True)


@mock_ec2_deprecated
def test_filter_volume_by_id():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume1 = conn.create_volume(80, "us-east-1a")
    volume2 = conn.create_volume(36, "us-east-1b")
    volume3 = conn.create_volume(20, "us-east-1c")
    vol1 = conn.get_all_volumes(volume_ids=volume3.id)
    vol1.should.have.length_of(1)
    vol1[0].size.should.equal(20)
    vol1[0].zone.should.equal('us-east-1c')
    vol2 = conn.get_all_volumes(volume_ids=[volume1.id, volume2.id])
    vol2.should.have.length_of(2)

    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_volumes(volume_ids=['vol-does_not_exist'])
    cm.exception.code.should.equal('InvalidVolume.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_volume_filters():
    conn = boto.ec2.connect_to_region("us-east-1")

    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.update()

    volume1 = conn.create_volume(80, "us-east-1a", encrypted=True)
    volume2 = conn.create_volume(36, "us-east-1b", encrypted=False)
    volume3 = conn.create_volume(20, "us-east-1c", encrypted=True)

    snapshot = volume3.create_snapshot(description='testsnap')
    volume4 = conn.create_volume(25, "us-east-1a", snapshot=snapshot)

    conn.create_tags([volume1.id], {'testkey1': 'testvalue1'})
    conn.create_tags([volume2.id], {'testkey2': 'testvalue2'})

    volume1.update()
    volume2.update()
    volume3.update()
    volume4.update()

    block_mapping = instance.block_device_mapping['/dev/sda1']

    volume_ids = (volume1.id, volume2.id, volume3.id, volume4.id, block_mapping.volume_id)

    volumes_by_attach_time = conn.get_all_volumes(
        filters={'attachment.attach-time': block_mapping.attach_time})
    set([vol.id for vol in volumes_by_attach_time]
        ).should.equal({block_mapping.volume_id})

    volumes_by_attach_device = conn.get_all_volumes(
        filters={'attachment.device': '/dev/sda1'})
    set([vol.id for vol in volumes_by_attach_device]
        ).should.equal({block_mapping.volume_id})

    volumes_by_attach_instance_id = conn.get_all_volumes(
        filters={'attachment.instance-id': instance.id})
    set([vol.id for vol in volumes_by_attach_instance_id]
        ).should.equal({block_mapping.volume_id})

    volumes_by_attach_status = conn.get_all_volumes(
        filters={'attachment.status': 'attached'})
    set([vol.id for vol in volumes_by_attach_status]
        ).should.equal({block_mapping.volume_id})

    volumes_by_create_time = conn.get_all_volumes(
        filters={'create-time': volume4.create_time})
    set([vol.create_time for vol in volumes_by_create_time]
        ).should.equal({volume4.create_time})

    volumes_by_size = conn.get_all_volumes(filters={'size': volume2.size})
    set([vol.id for vol in volumes_by_size]).should.equal({volume2.id})

    volumes_by_snapshot_id = conn.get_all_volumes(
        filters={'snapshot-id': snapshot.id})
    set([vol.id for vol in volumes_by_snapshot_id]
        ).should.equal({volume4.id})

    volumes_by_status = conn.get_all_volumes(filters={'status': 'in-use'})
    set([vol.id for vol in volumes_by_status]).should.equal(
        {block_mapping.volume_id})

    volumes_by_id = conn.get_all_volumes(filters={'volume-id': volume1.id})
    set([vol.id for vol in volumes_by_id]).should.equal({volume1.id})

    volumes_by_tag_key = conn.get_all_volumes(filters={'tag-key': 'testkey1'})
    set([vol.id for vol in volumes_by_tag_key]).should.equal({volume1.id})

    volumes_by_tag_value = conn.get_all_volumes(
        filters={'tag-value': 'testvalue1'})
    set([vol.id for vol in volumes_by_tag_value]
        ).should.equal({volume1.id})

    volumes_by_tag = conn.get_all_volumes(
        filters={'tag:testkey1': 'testvalue1'})
    set([vol.id for vol in volumes_by_tag]).should.equal({volume1.id})

    volumes_by_unencrypted = conn.get_all_volumes(
        filters={'encrypted': 'false'})
    set([vol.id for vol in volumes_by_unencrypted if vol.id in volume_ids]).should.equal(
        {block_mapping.volume_id, volume2.id}
    )

    volumes_by_encrypted = conn.get_all_volumes(filters={'encrypted': 'true'})
    set([vol.id for vol in volumes_by_encrypted if vol.id in volume_ids]).should.equal(
        {volume1.id, volume3.id, volume4.id}
    )

    volumes_by_availability_zone = conn.get_all_volumes(filters={'availability-zone': 'us-east-1b'})
    set([vol.id for vol in volumes_by_availability_zone if vol.id in volume_ids]).should.equal(
        {volume2.id}
    )


@mock_ec2_deprecated
def test_volume_attach_and_detach():
    conn = boto.ec2.connect_to_region("us-east-1")
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    volume = conn.create_volume(80, "us-east-1a")

    volume.update()
    volume.volume_state().should.equal('available')

    with assert_raises(EC2ResponseError) as ex:
        volume.attach(instance.id, "/dev/sdh", dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the AttachVolume operation: Request would have succeeded, but DryRun flag is set')

    volume.attach(instance.id, "/dev/sdh")

    volume.update()
    volume.volume_state().should.equal('in-use')
    volume.attachment_state().should.equal('attached')

    volume.attach_data.instance_id.should.equal(instance.id)

    with assert_raises(EC2ResponseError) as ex:
        volume.detach(dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the DetachVolume operation: Request would have succeeded, but DryRun flag is set')

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


@mock_ec2_deprecated
def test_create_snapshot():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a")

    with assert_raises(EC2ResponseError) as ex:
        snapshot = volume.create_snapshot('a dryrun snapshot', dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the CreateSnapshot operation: Request would have succeeded, but DryRun flag is set')

    snapshot = volume.create_snapshot('a test snapshot')
    snapshot.update()
    snapshot.status.should.equal('completed')

    snapshots = [snap for snap in conn.get_all_snapshots() if snap.id == snapshot.id]
    snapshots.should.have.length_of(1)
    snapshots[0].description.should.equal('a test snapshot')
    snapshots[0].start_time.should_not.be.none
    snapshots[0].encrypted.should.be(False)

    # Create snapshot without description
    num_snapshots = len(conn.get_all_snapshots())

    snapshot = volume.create_snapshot()
    conn.get_all_snapshots().should.have.length_of(num_snapshots + 1)

    snapshot.delete()
    conn.get_all_snapshots().should.have.length_of(num_snapshots)

    # Deleting something that was already deleted should throw an error
    with assert_raises(EC2ResponseError) as cm:
        snapshot.delete()
    cm.exception.code.should.equal('InvalidSnapshot.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_create_encrypted_snapshot():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a", encrypted=True)
    snapshot = volume.create_snapshot('a test snapshot')
    snapshot.update()
    snapshot.status.should.equal('completed')

    snapshots = [snap for snap in conn.get_all_snapshots() if snap.id == snapshot.id]
    snapshots.should.have.length_of(1)
    snapshots[0].description.should.equal('a test snapshot')
    snapshots[0].start_time.should_not.be.none
    snapshots[0].encrypted.should.be(True)


@mock_ec2_deprecated
def test_filter_snapshot_by_id():
    conn = boto.ec2.connect_to_region("us-east-1")
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

    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_snapshots(snapshot_ids=['snap-does_not_exist'])
    cm.exception.code.should.equal('InvalidSnapshot.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_snapshot_filters():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume1 = conn.create_volume(20, "us-east-1a", encrypted=False)
    volume2 = conn.create_volume(25, "us-east-1a", encrypted=True)

    snapshot1 = volume1.create_snapshot(description='testsnapshot1')
    snapshot2 = volume1.create_snapshot(description='testsnapshot2')
    snapshot3 = volume2.create_snapshot(description='testsnapshot3')

    conn.create_tags([snapshot1.id], {'testkey1': 'testvalue1'})
    conn.create_tags([snapshot2.id], {'testkey2': 'testvalue2'})

    snapshots_by_description = conn.get_all_snapshots(
        filters={'description': 'testsnapshot1'})
    set([snap.id for snap in snapshots_by_description]
        ).should.equal({snapshot1.id})

    snapshots_by_id = conn.get_all_snapshots(
        filters={'snapshot-id': snapshot1.id})
    set([snap.id for snap in snapshots_by_id]
        ).should.equal({snapshot1.id})

    snapshots_by_start_time = conn.get_all_snapshots(
        filters={'start-time': snapshot1.start_time})
    set([snap.start_time for snap in snapshots_by_start_time]
        ).should.equal({snapshot1.start_time})

    snapshots_by_volume_id = conn.get_all_snapshots(
        filters={'volume-id': volume1.id})
    set([snap.id for snap in snapshots_by_volume_id]
        ).should.equal({snapshot1.id, snapshot2.id})

    snapshots_by_status = conn.get_all_snapshots(
        filters={'status': 'completed'})
    ({snapshot1.id, snapshot2.id, snapshot3.id} -
     {snap.id for snap in snapshots_by_status}).should.have.length_of(0)

    snapshots_by_volume_size = conn.get_all_snapshots(
        filters={'volume-size': volume1.size})
    set([snap.id for snap in snapshots_by_volume_size]
        ).should.equal({snapshot1.id, snapshot2.id})

    snapshots_by_tag_key = conn.get_all_snapshots(
        filters={'tag-key': 'testkey1'})
    set([snap.id for snap in snapshots_by_tag_key]
        ).should.equal({snapshot1.id})

    snapshots_by_tag_value = conn.get_all_snapshots(
        filters={'tag-value': 'testvalue1'})
    set([snap.id for snap in snapshots_by_tag_value]
        ).should.equal({snapshot1.id})

    snapshots_by_tag = conn.get_all_snapshots(
        filters={'tag:testkey1': 'testvalue1'})
    set([snap.id for snap in snapshots_by_tag]
        ).should.equal({snapshot1.id})

    snapshots_by_encrypted = conn.get_all_snapshots(
        filters={'encrypted': 'true'})
    set([snap.id for snap in snapshots_by_encrypted]
        ).should.equal({snapshot3.id})

    snapshots_by_owner_id = conn.get_all_snapshots(
        filters={'owner-id': OWNER_ID})
    set([snap.id for snap in snapshots_by_owner_id]
        ).should.equal({snapshot1.id, snapshot2.id, snapshot3.id})


@mock_ec2_deprecated
def test_snapshot_attribute():
    import copy

    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a")
    snapshot = volume.create_snapshot()

    # Baseline
    attributes = conn.get_snapshot_attribute(
        snapshot.id, attribute='createVolumePermission')
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

    with assert_raises(EC2ResponseError) as ex:
        conn.modify_snapshot_attribute(
            **dict(ADD_GROUP_ARGS, **{'dry_run': True}))
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ModifySnapshotAttribute operation: Request would have succeeded, but DryRun flag is set')

    conn.modify_snapshot_attribute(**ADD_GROUP_ARGS)

    attributes = conn.get_snapshot_attribute(
        snapshot.id, attribute='createVolumePermission')
    attributes.attrs['groups'].should.have.length_of(1)
    attributes.attrs['groups'].should.equal(['all'])

    # Add is idempotent
    conn.modify_snapshot_attribute.when.called_with(
        **ADD_GROUP_ARGS).should_not.throw(EC2ResponseError)

    # Remove 'all' group and confirm
    with assert_raises(EC2ResponseError) as ex:
        conn.modify_snapshot_attribute(
            **dict(REMOVE_GROUP_ARGS, **{'dry_run': True}))
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ModifySnapshotAttribute operation: Request would have succeeded, but DryRun flag is set')

    conn.modify_snapshot_attribute(**REMOVE_GROUP_ARGS)

    attributes = conn.get_snapshot_attribute(
        snapshot.id, attribute='createVolumePermission')
    attributes.attrs.should.have.length_of(0)

    # Remove is idempotent
    conn.modify_snapshot_attribute.when.called_with(
        **REMOVE_GROUP_ARGS).should_not.throw(EC2ResponseError)

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


@mock_ec2_deprecated
def test_create_volume_from_snapshot():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a")
    snapshot = volume.create_snapshot('a test snapshot')

    with assert_raises(EC2ResponseError) as ex:
        snapshot = volume.create_snapshot('a test snapshot', dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the CreateSnapshot operation: Request would have succeeded, but DryRun flag is set')

    snapshot = volume.create_snapshot('a test snapshot')
    snapshot.update()
    snapshot.status.should.equal('completed')

    new_volume = snapshot.create_volume('us-east-1a')
    new_volume.size.should.equal(80)
    new_volume.snapshot_id.should.equal(snapshot.id)


@mock_ec2_deprecated
def test_create_volume_from_encrypted_snapshot():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a", encrypted=True)

    snapshot = volume.create_snapshot('a test snapshot')
    snapshot.update()
    snapshot.status.should.equal('completed')

    new_volume = snapshot.create_volume('us-east-1a')
    new_volume.size.should.equal(80)
    new_volume.snapshot_id.should.equal(snapshot.id)
    new_volume.encrypted.should.be(True)


@mock_ec2_deprecated
def test_modify_attribute_blockDeviceMapping():
    """
    Reproduces the missing feature explained at [0], where we want to mock a
    call to modify an instance attribute of type: blockDeviceMapping.

    [0] https://github.com/spulec/moto/issues/160
    """
    conn = boto.ec2.connect_to_region("us-east-1")

    reservation = conn.run_instances('ami-1234abcd')

    instance = reservation.instances[0]

    with assert_raises(EC2ResponseError) as ex:
        instance.modify_attribute('blockDeviceMapping', {
                                  '/dev/sda1': True}, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ModifyInstanceAttribute operation: Request would have succeeded, but DryRun flag is set')

    instance.modify_attribute('blockDeviceMapping', {'/dev/sda1': True})

    instance = ec2_backends[conn.region.name].get_instance(instance.id)
    instance.block_device_mapping.should.have.key('/dev/sda1')
    instance.block_device_mapping[
        '/dev/sda1'].delete_on_termination.should.be(True)


@mock_ec2_deprecated
def test_volume_tag_escaping():
    conn = boto.ec2.connect_to_region("us-east-1")
    vol = conn.create_volume(10, 'us-east-1a')
    snapshot = conn.create_snapshot(vol.id, 'Desc')

    with assert_raises(EC2ResponseError) as ex:
        snapshot.add_tags({'key': '</closed>'}, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set')
    snaps = [snap for snap in conn.get_all_snapshots() if snap.id == snapshot.id]
    dict(snaps[0].tags).should_not.be.equal(
        {'key': '</closed>'})

    snapshot.add_tags({'key': '</closed>'})

    snaps = [snap for snap in conn.get_all_snapshots() if snap.id == snapshot.id]
    dict(snaps[0].tags).should.equal({'key': '</closed>'})


@mock_ec2
def test_volume_property_hidden_when_no_tags_exist():
    ec2_client = boto3.client('ec2', region_name='us-east-1')

    volume_response = ec2_client.create_volume(
        Size=10,
        AvailabilityZone='us-east-1a'
    )

    volume_response.get('Tags').should.equal(None)


@freeze_time
@mock_ec2
def test_copy_snapshot():
    ec2_client = boto3.client('ec2', region_name='eu-west-1')
    dest_ec2_client = boto3.client('ec2', region_name='eu-west-2')

    volume_response = ec2_client.create_volume(
        AvailabilityZone='eu-west-1a', Size=10
    )

    create_snapshot_response = ec2_client.create_snapshot(
        VolumeId=volume_response['VolumeId']
    )

    copy_snapshot_response = dest_ec2_client.copy_snapshot(
        SourceSnapshotId=create_snapshot_response['SnapshotId'],
        SourceRegion="eu-west-1"
    )

    ec2 = boto3.resource('ec2', region_name='eu-west-1')
    dest_ec2 = boto3.resource('ec2', region_name='eu-west-2')

    source = ec2.Snapshot(create_snapshot_response['SnapshotId'])
    dest = dest_ec2.Snapshot(copy_snapshot_response['SnapshotId'])

    attribs = ['data_encryption_key_id', 'encrypted',
                'kms_key_id', 'owner_alias', 'owner_id',
                'progress', 'state', 'state_message',
                'tags', 'volume_id', 'volume_size']

    for attrib in attribs:
        getattr(source, attrib).should.equal(getattr(dest, attrib))

    # Copy from non-existent source ID.
    with assert_raises(ClientError) as cm:
        create_snapshot_error = ec2_client.create_snapshot(
            VolumeId='vol-abcd1234'
        )
    cm.exception.response['Error']['Code'].should.equal('InvalidVolume.NotFound')
    cm.exception.response['Error']['Message'].should.equal("The volume 'vol-abcd1234' does not exist.")
    cm.exception.response['ResponseMetadata']['RequestId'].should_not.be.none
    cm.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)

    # Copy from non-existent source region.
    with assert_raises(ClientError) as cm:
        copy_snapshot_response = dest_ec2_client.copy_snapshot(
            SourceSnapshotId=create_snapshot_response['SnapshotId'],
            SourceRegion="eu-west-2"
        )
    cm.exception.response['Error']['Code'].should.equal('InvalidSnapshot.NotFound')
    cm.exception.response['Error']['Message'].should.be.none
    cm.exception.response['ResponseMetadata']['RequestId'].should_not.be.none
    cm.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)

@mock_ec2
def test_search_for_many_snapshots():
    ec2_client = boto3.client('ec2', region_name='eu-west-1')

    volume_response = ec2_client.create_volume(
        AvailabilityZone='eu-west-1a', Size=10
    )

    snapshot_ids = []
    for i in range(1, 20):
        create_snapshot_response = ec2_client.create_snapshot(
            VolumeId=volume_response['VolumeId']
        )
        snapshot_ids.append(create_snapshot_response['SnapshotId'])

    snapshots_response = ec2_client.describe_snapshots(
        SnapshotIds=snapshot_ids
    )

    assert len(snapshots_response['Snapshots']) == len(snapshot_ids)
