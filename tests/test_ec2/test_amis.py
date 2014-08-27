# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
from boto.exception import EC2ResponseError

import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_ami_create_and_delete():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")

    all_images = conn.get_all_images()
    image = all_images[0]

    image.id.should.equal(image_id)
    image.virtualization_type.should.equal(instance.virtualization_type)
    image.architecture.should.equal(instance.architecture)
    image.kernel_id.should.equal(instance.kernel)
    image.platform.should.equal(instance.platform)

    # Validate auto-created volume and snapshot
    volumes = conn.get_all_volumes()
    volumes.should.have.length_of(1)
    volume = volumes[0]

    snapshots = conn.get_all_snapshots()
    snapshots.should.have.length_of(1)
    snapshot = snapshots[0]

    image.block_device_mapping.current_value.snapshot_id.should.equal(snapshot.id)
    snapshot.description.should.equal("Auto-created snapshot for AMI {0}".format(image.id))
    snapshot.volume_id.should.equal(volume.id)

    # Deregister
    success = conn.deregister_image(image_id)
    success.should.be.true

    with assert_raises(EC2ResponseError) as cm:
        conn.deregister_image(image_id)
    cm.exception.code.should.equal('InvalidAMIID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_ami_tagging():
    conn = boto.connect_vpc('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_all_images()[0]

    image.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the DHCP options
    image = conn.get_all_images()[0]
    image.tags.should.have.length_of(1)
    image.tags["a key"].should.equal("some value")


@mock_ec2
def test_ami_create_from_missing_instance():
    conn = boto.connect_ec2('the_key', 'the_secret')
    args = ["i-abcdefg", "test-ami", "this is a test ami"]

    with assert_raises(EC2ResponseError) as cm:
        conn.create_image(*args)
    cm.exception.code.should.equal('InvalidInstanceID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_ami_pulls_attributes_from_instance():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    instance.modify_attribute("kernel", "test-kernel")

    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)
    image.kernel_id.should.equal('test-kernel')


@mock_ec2
def test_ami_filters():
    conn = boto.connect_ec2('the_key', 'the_secret')

    reservationA = conn.run_instances('ami-1234abcd')
    instanceA = reservationA.instances[0]
    instanceA.modify_attribute("architecture", "i386")
    instanceA.modify_attribute("kernel", "k-1234abcd")
    instanceA.modify_attribute("platform", "windows")
    instanceA.modify_attribute("virtualization_type", "hvm")
    imageA_id = conn.create_image(instanceA.id, "test-ami-A", "this is a test ami")
    imageA = conn.get_image(imageA_id)

    reservationB = conn.run_instances('ami-abcd1234')
    instanceB = reservationB.instances[0]
    instanceB.modify_attribute("architecture", "x86_64")
    instanceB.modify_attribute("kernel", "k-abcd1234")
    instanceB.modify_attribute("platform", "linux")
    instanceB.modify_attribute("virtualization_type", "paravirtual")
    imageB_id = conn.create_image(instanceB.id, "test-ami-B", "this is a test ami")
    imageB = conn.get_image(imageB_id)

    amis_by_architecture = conn.get_all_images(filters={'architecture': 'x86_64'})
    set([ami.id for ami in amis_by_architecture]).should.equal(set([imageB.id]))

    amis_by_kernel = conn.get_all_images(filters={'kernel-id': 'k-abcd1234'})
    set([ami.id for ami in amis_by_kernel]).should.equal(set([imageB.id]))

    amis_by_virtualization = conn.get_all_images(filters={'virtualization-type': 'paravirtual'})
    set([ami.id for ami in amis_by_virtualization]).should.equal(set([imageB.id]))

    amis_by_platform = conn.get_all_images(filters={'platform': 'windows'})
    set([ami.id for ami in amis_by_platform]).should.equal(set([imageA.id]))

    amis_by_id = conn.get_all_images(filters={'image-id': imageA.id})
    set([ami.id for ami in amis_by_id]).should.equal(set([imageA.id]))


@mock_ec2
def test_getting_missing_ami():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.get_image('ami-missing')
    cm.exception.code.should.equal('InvalidAMIID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_getting_malformed_ami():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.get_image('foo-missing')
    cm.exception.code.should.equal('InvalidAMIID.Malformed')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_ami_attribute():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)

    # Baseline
    attributes = conn.get_image_attribute(image.id, attribute='launchPermission')
    attributes.name.should.equal('launch_permission')
    attributes.attrs.should.have.length_of(0)

    ADD_GROUP_ARGS = {'image_id': image.id,
                      'attribute': 'launchPermission',
                      'operation': 'add',
                      'groups': 'all'}

    REMOVE_GROUP_ARGS = {'image_id': image.id,
                         'attribute': 'launchPermission',
                         'operation': 'remove',
                         'groups': 'all'}

    # Add 'all' group and confirm
    conn.modify_image_attribute(**ADD_GROUP_ARGS)

    attributes = conn.get_image_attribute(image.id, attribute='launchPermission')
    attributes.attrs['groups'].should.have.length_of(1)
    attributes.attrs['groups'].should.equal(['all'])

    # Add is idempotent
    conn.modify_image_attribute.when.called_with(**ADD_GROUP_ARGS).should_not.throw(EC2ResponseError)

    # Remove 'all' group and confirm
    conn.modify_image_attribute(**REMOVE_GROUP_ARGS)

    attributes = conn.get_image_attribute(image.id, attribute='launchPermission')
    attributes.attrs.should.have.length_of(0)

    # Remove is idempotent
    conn.modify_image_attribute.when.called_with(**REMOVE_GROUP_ARGS).should_not.throw(EC2ResponseError)

    # Error: Add with group != 'all'
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(image.id,
                                    attribute='launchPermission',
                                    operation='add',
                                    groups='everyone')
    cm.exception.code.should.equal('InvalidAMIAttributeItemValue')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Add with invalid image ID
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute("ami-abcd1234",
                                    attribute='launchPermission',
                                    operation='add',
                                    groups='all')
    cm.exception.code.should.equal('InvalidAMIID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Remove with invalid image ID
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute("ami-abcd1234",
                                    attribute='launchPermission',
                                    operation='remove',
                                    groups='all')
    cm.exception.code.should.equal('InvalidAMIID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Add or remove with user ID instead of group
    conn.modify_image_attribute.when.called_with(image.id,
                                                 attribute='launchPermission',
                                                 operation='add',
                                                 user_ids=['user']).should.throw(NotImplementedError)
    conn.modify_image_attribute.when.called_with(image.id,
                                                 attribute='launchPermission',
                                                 operation='remove',
                                                 user_ids=['user']).should.throw(NotImplementedError)

