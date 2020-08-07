from __future__ import unicode_literals

import boto
import boto.ec2
import boto3
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError

# Ensure 'assert_raises' context manager support for Python 2.6
from nose.tools import assert_raises
import sure  # noqa

from moto import mock_ec2_deprecated, mock_ec2
from moto.ec2.models import AMIS, OWNER_ID
from moto.iam.models import ACCOUNT_ID
from tests.helpers import requires_boto_gte


@mock_ec2_deprecated
def test_ami_create_and_delete():
    conn = boto.connect_ec2("the_key", "the_secret")

    initial_ami_count = len(AMIS)
    conn.get_all_volumes().should.have.length_of(0)
    conn.get_all_snapshots().should.have.length_of(initial_ami_count)

    reservation = conn.run_instances("ami-1234abcd")
    instance = reservation.instances[0]

    with assert_raises(EC2ResponseError) as ex:
        image_id = conn.create_image(
            instance.id, "test-ami", "this is a test ami", dry_run=True
        )
    ex.exception.error_code.should.equal("DryRunOperation")
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateImage operation: Request would have succeeded, but DryRun flag is set"
    )

    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")

    all_images = conn.get_all_images()
    set([i.id for i in all_images]).should.contain(image_id)

    retrieved_image = [i for i in all_images if i.id == image_id][0]

    retrieved_image.id.should.equal(image_id)
    retrieved_image.virtualization_type.should.equal(instance.virtualization_type)
    retrieved_image.architecture.should.equal(instance.architecture)
    retrieved_image.kernel_id.should.equal(instance.kernel)
    retrieved_image.platform.should.equal(instance.platform)
    retrieved_image.creationDate.should_not.be.none
    instance.terminate()

    # Ensure we're no longer creating a volume
    volumes = conn.get_all_volumes()
    volumes.should.have.length_of(0)

    # Validate auto-created snapshot
    snapshots = conn.get_all_snapshots()
    snapshots.should.have.length_of(initial_ami_count + 1)

    retrieved_image_snapshot_id = (
        retrieved_image.block_device_mapping.current_value.snapshot_id
    )
    [s.id for s in snapshots].should.contain(retrieved_image_snapshot_id)
    snapshot = [s for s in snapshots if s.id == retrieved_image_snapshot_id][0]
    snapshot.description.should.equal(
        "Auto-created snapshot for AMI {0}".format(retrieved_image.id)
    )

    # root device should be in AMI's block device mappings
    root_mapping = retrieved_image.block_device_mapping.get(
        retrieved_image.root_device_name
    )
    root_mapping.should_not.be.none

    # Deregister
    with assert_raises(EC2ResponseError) as ex:
        success = conn.deregister_image(image_id, dry_run=True)
    ex.exception.error_code.should.equal("DryRunOperation")
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DeregisterImage operation: Request would have succeeded, but DryRun flag is set"
    )

    success = conn.deregister_image(image_id)
    success.should.be.true

    with assert_raises(EC2ResponseError) as cm:
        conn.deregister_image(image_id)
    cm.exception.code.should.equal("InvalidAMIID.NotFound")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@requires_boto_gte("2.14.0")
@mock_ec2_deprecated
def test_ami_copy():
    conn = boto.ec2.connect_to_region("us-west-1")

    initial_ami_count = len(AMIS)
    conn.get_all_volumes().should.have.length_of(0)
    conn.get_all_snapshots().should.have.length_of(initial_ami_count)

    reservation = conn.run_instances("ami-1234abcd")
    instance = reservation.instances[0]

    source_image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    instance.terminate()
    source_image = conn.get_all_images(image_ids=[source_image_id])[0]

    # Boto returns a 'CopyImage' object with an image_id attribute here. Use
    # the image_id to fetch the full info.
    with assert_raises(EC2ResponseError) as ex:
        copy_image_ref = conn.copy_image(
            source_image.region.name,
            source_image.id,
            "test-copy-ami",
            "this is a test copy ami",
            dry_run=True,
        )
    ex.exception.error_code.should.equal("DryRunOperation")
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CopyImage operation: Request would have succeeded, but DryRun flag is set"
    )

    copy_image_ref = conn.copy_image(
        source_image.region.name,
        source_image.id,
        "test-copy-ami",
        "this is a test copy ami",
    )
    copy_image_id = copy_image_ref.image_id
    copy_image = conn.get_all_images(image_ids=[copy_image_id])[0]

    copy_image.id.should.equal(copy_image_id)
    copy_image.virtualization_type.should.equal(source_image.virtualization_type)
    copy_image.architecture.should.equal(source_image.architecture)
    copy_image.kernel_id.should.equal(source_image.kernel_id)
    copy_image.platform.should.equal(source_image.platform)

    # Ensure we're no longer creating a volume
    conn.get_all_volumes().should.have.length_of(0)

    # Validate auto-created snapshot
    conn.get_all_snapshots().should.have.length_of(initial_ami_count + 2)

    copy_image.block_device_mapping.current_value.snapshot_id.should_not.equal(
        source_image.block_device_mapping.current_value.snapshot_id
    )

    # Copy from non-existent source ID.
    with assert_raises(EC2ResponseError) as cm:
        conn.copy_image(
            source_image.region.name,
            "ami-abcd1234",
            "test-copy-ami",
            "this is a test copy ami",
        )
    cm.exception.code.should.equal("InvalidAMIID.NotFound")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Copy from non-existent source region.
    with assert_raises(EC2ResponseError) as cm:
        invalid_region = (
            "us-east-1" if (source_image.region.name != "us-east-1") else "us-west-1"
        )
        conn.copy_image(
            invalid_region, source_image.id, "test-copy-ami", "this is a test copy ami"
        )
    cm.exception.code.should.equal("InvalidAMIID.NotFound")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_copy_image_changes_owner_id():
    conn = boto3.client("ec2", region_name="us-east-1")

    # this source AMI ID is from moto/ec2/resources/amis.json
    source_ami_id = "ami-03cf127a"

    # confirm the source ami owner id is different from the default owner id.
    # if they're ever the same it means this test is invalid.
    check_resp = conn.describe_images(ImageIds=[source_ami_id])
    check_resp["Images"][0]["OwnerId"].should_not.equal(OWNER_ID)

    copy_resp = conn.copy_image(
        SourceImageId=source_ami_id,
        Name="new-image",
        Description="a copy of an image",
        SourceRegion="us-east-1",
    )

    describe_resp = conn.describe_images(Owners=["self"])
    describe_resp["Images"][0]["OwnerId"].should.equal(OWNER_ID)
    describe_resp["Images"][0]["ImageId"].should.equal(copy_resp["ImageId"])


@mock_ec2_deprecated
def test_ami_tagging():
    conn = boto.connect_vpc("the_key", "the_secret")
    reservation = conn.run_instances("ami-1234abcd")
    instance = reservation.instances[0]
    conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_all_images()[0]

    with assert_raises(EC2ResponseError) as ex:
        image.add_tag("a key", "some value", dry_run=True)
    ex.exception.error_code.should.equal("DryRunOperation")
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    image.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the DHCP options
    image = conn.get_all_images()[0]
    image.tags.should.have.length_of(1)
    image.tags["a key"].should.equal("some value")


@mock_ec2_deprecated
def test_ami_create_from_missing_instance():
    conn = boto.connect_ec2("the_key", "the_secret")
    args = ["i-abcdefg", "test-ami", "this is a test ami"]

    with assert_raises(EC2ResponseError) as cm:
        conn.create_image(*args)
    cm.exception.code.should.equal("InvalidInstanceID.NotFound")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_ami_pulls_attributes_from_instance():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances("ami-1234abcd")
    instance = reservation.instances[0]
    instance.modify_attribute("kernel", "test-kernel")

    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)
    image.kernel_id.should.equal("test-kernel")


@mock_ec2_deprecated
def test_ami_uses_account_id_if_valid_access_key_is_supplied():
    access_key = "AKIAXXXXXXXXXXXXXXXX"
    conn = boto.connect_ec2(access_key, "the_secret")
    reservation = conn.run_instances("ami-1234abcd")
    instance = reservation.instances[0]
    instance.modify_attribute("kernel", "test-kernel")

    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    images = conn.get_all_images(owners=["self"])
    [(ami.id, ami.owner_id) for ami in images].should.equal([(image_id, ACCOUNT_ID)])


@mock_ec2_deprecated
def test_ami_filters():
    conn = boto.connect_ec2("the_key", "the_secret")

    reservationA = conn.run_instances("ami-1234abcd")
    instanceA = reservationA.instances[0]
    instanceA.modify_attribute("architecture", "i386")
    instanceA.modify_attribute("kernel", "k-1234abcd")
    instanceA.modify_attribute("platform", "windows")
    instanceA.modify_attribute("virtualization_type", "hvm")
    imageA_id = conn.create_image(instanceA.id, "test-ami-A", "this is a test ami")
    imageA = conn.get_image(imageA_id)

    reservationB = conn.run_instances("ami-abcd1234")
    instanceB = reservationB.instances[0]
    instanceB.modify_attribute("architecture", "x86_64")
    instanceB.modify_attribute("kernel", "k-abcd1234")
    instanceB.modify_attribute("platform", "linux")
    instanceB.modify_attribute("virtualization_type", "paravirtual")
    imageB_id = conn.create_image(instanceB.id, "test-ami-B", "this is a test ami")
    imageB = conn.get_image(imageB_id)
    imageB.set_launch_permissions(group_names=("all"))

    amis_by_architecture = conn.get_all_images(filters={"architecture": "x86_64"})
    set([ami.id for ami in amis_by_architecture]).should.contain(imageB.id)
    len(amis_by_architecture).should.equal(35)

    amis_by_kernel = conn.get_all_images(filters={"kernel-id": "k-abcd1234"})
    set([ami.id for ami in amis_by_kernel]).should.equal(set([imageB.id]))

    amis_by_virtualization = conn.get_all_images(
        filters={"virtualization-type": "paravirtual"}
    )
    set([ami.id for ami in amis_by_virtualization]).should.contain(imageB.id)
    len(amis_by_virtualization).should.equal(3)

    amis_by_platform = conn.get_all_images(filters={"platform": "windows"})
    set([ami.id for ami in amis_by_platform]).should.contain(imageA.id)
    len(amis_by_platform).should.equal(24)

    amis_by_id = conn.get_all_images(filters={"image-id": imageA.id})
    set([ami.id for ami in amis_by_id]).should.equal(set([imageA.id]))

    amis_by_state = conn.get_all_images(filters={"state": "available"})
    ami_ids_by_state = [ami.id for ami in amis_by_state]
    ami_ids_by_state.should.contain(imageA.id)
    ami_ids_by_state.should.contain(imageB.id)
    len(amis_by_state).should.equal(36)

    amis_by_name = conn.get_all_images(filters={"name": imageA.name})
    set([ami.id for ami in amis_by_name]).should.equal(set([imageA.id]))

    amis_by_public = conn.get_all_images(filters={"is-public": "true"})
    set([ami.id for ami in amis_by_public]).should.contain(imageB.id)
    len(amis_by_public).should.equal(35)

    amis_by_nonpublic = conn.get_all_images(filters={"is-public": "false"})
    set([ami.id for ami in amis_by_nonpublic]).should.contain(imageA.id)
    len(amis_by_nonpublic).should.equal(1)


@mock_ec2_deprecated
def test_ami_filtering_via_tag():
    conn = boto.connect_vpc("the_key", "the_secret")

    reservationA = conn.run_instances("ami-1234abcd")
    instanceA = reservationA.instances[0]
    imageA_id = conn.create_image(instanceA.id, "test-ami-A", "this is a test ami")
    imageA = conn.get_image(imageA_id)
    imageA.add_tag("a key", "some value")

    reservationB = conn.run_instances("ami-abcd1234")
    instanceB = reservationB.instances[0]
    imageB_id = conn.create_image(instanceB.id, "test-ami-B", "this is a test ami")
    imageB = conn.get_image(imageB_id)
    imageB.add_tag("another key", "some other value")

    amis_by_tagA = conn.get_all_images(filters={"tag:a key": "some value"})
    set([ami.id for ami in amis_by_tagA]).should.equal(set([imageA.id]))

    amis_by_tagB = conn.get_all_images(filters={"tag:another key": "some other value"})
    set([ami.id for ami in amis_by_tagB]).should.equal(set([imageB.id]))


@mock_ec2_deprecated
def test_getting_missing_ami():
    conn = boto.connect_ec2("the_key", "the_secret")

    with assert_raises(EC2ResponseError) as cm:
        conn.get_image("ami-missing")
    cm.exception.code.should.equal("InvalidAMIID.NotFound")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_getting_malformed_ami():
    conn = boto.connect_ec2("the_key", "the_secret")

    with assert_raises(EC2ResponseError) as cm:
        conn.get_image("foo-missing")
    cm.exception.code.should.equal("InvalidAMIID.Malformed")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_ami_attribute_group_permissions():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances("ami-1234abcd")
    instance = reservation.instances[0]
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)

    # Baseline
    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.name.should.equal("launch_permission")
    attributes.attrs.should.have.length_of(0)

    ADD_GROUP_ARGS = {
        "image_id": image.id,
        "attribute": "launchPermission",
        "operation": "add",
        "groups": "all",
    }

    REMOVE_GROUP_ARGS = {
        "image_id": image.id,
        "attribute": "launchPermission",
        "operation": "remove",
        "groups": "all",
    }

    # Add 'all' group and confirm
    with assert_raises(EC2ResponseError) as ex:
        conn.modify_image_attribute(**dict(ADD_GROUP_ARGS, **{"dry_run": True}))
    ex.exception.error_code.should.equal("DryRunOperation")
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyImageAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.modify_image_attribute(**ADD_GROUP_ARGS)

    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.attrs["groups"].should.have.length_of(1)
    attributes.attrs["groups"].should.equal(["all"])
    image = conn.get_image(image_id)
    image.is_public.should.equal(True)

    # Add is idempotent
    conn.modify_image_attribute.when.called_with(**ADD_GROUP_ARGS).should_not.throw(
        EC2ResponseError
    )

    # Remove 'all' group and confirm
    conn.modify_image_attribute(**REMOVE_GROUP_ARGS)

    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.attrs.should.have.length_of(0)
    image = conn.get_image(image_id)
    image.is_public.should.equal(False)

    # Remove is idempotent
    conn.modify_image_attribute.when.called_with(**REMOVE_GROUP_ARGS).should_not.throw(
        EC2ResponseError
    )


@mock_ec2_deprecated
def test_ami_attribute_user_permissions():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances("ami-1234abcd")
    instance = reservation.instances[0]
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)

    # Baseline
    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.name.should.equal("launch_permission")
    attributes.attrs.should.have.length_of(0)

    # Both str and int values should work.
    USER1 = "123456789011"
    USER2 = 123456789022

    ADD_USERS_ARGS = {
        "image_id": image.id,
        "attribute": "launchPermission",
        "operation": "add",
        "user_ids": [USER1, USER2],
    }

    REMOVE_USERS_ARGS = {
        "image_id": image.id,
        "attribute": "launchPermission",
        "operation": "remove",
        "user_ids": [USER1, USER2],
    }

    REMOVE_SINGLE_USER_ARGS = {
        "image_id": image.id,
        "attribute": "launchPermission",
        "operation": "remove",
        "user_ids": [USER1],
    }

    # Add multiple users and confirm
    conn.modify_image_attribute(**ADD_USERS_ARGS)

    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.attrs["user_ids"].should.have.length_of(2)
    set(attributes.attrs["user_ids"]).should.equal(set([str(USER1), str(USER2)]))
    image = conn.get_image(image_id)
    image.is_public.should.equal(False)

    # Add is idempotent
    conn.modify_image_attribute.when.called_with(**ADD_USERS_ARGS).should_not.throw(
        EC2ResponseError
    )

    # Remove single user and confirm
    conn.modify_image_attribute(**REMOVE_SINGLE_USER_ARGS)

    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.attrs["user_ids"].should.have.length_of(1)
    set(attributes.attrs["user_ids"]).should.equal(set([str(USER2)]))
    image = conn.get_image(image_id)
    image.is_public.should.equal(False)

    # Remove multiple users and confirm
    conn.modify_image_attribute(**REMOVE_USERS_ARGS)

    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.attrs.should.have.length_of(0)
    image = conn.get_image(image_id)
    image.is_public.should.equal(False)

    # Remove is idempotent
    conn.modify_image_attribute.when.called_with(**REMOVE_USERS_ARGS).should_not.throw(
        EC2ResponseError
    )


@mock_ec2
def test_ami_describe_executable_users():
    conn = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", "us-east-1")
    ec2.create_instances(ImageId="", MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    image_id = conn.create_image(InstanceId=instance_id, Name="TestImage")["ImageId"]

    USER1 = "123456789011"

    ADD_USER_ARGS = {
        "ImageId": image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserIds": [USER1],
    }

    # Add users and get no images
    conn.modify_image_attribute(**ADD_USER_ARGS)

    attributes = conn.describe_image_attribute(
        ImageId=image_id, Attribute="LaunchPermissions", DryRun=False
    )
    attributes["LaunchPermissions"].should.have.length_of(1)
    attributes["LaunchPermissions"][0]["UserId"].should.equal(USER1)
    images = conn.describe_images(ExecutableUsers=[USER1])["Images"]
    images.should.have.length_of(1)
    images[0]["ImageId"].should.equal(image_id)


@mock_ec2
def test_ami_describe_executable_users_negative():
    conn = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", "us-east-1")
    ec2.create_instances(ImageId="", MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    image_id = conn.create_image(InstanceId=instance_id, Name="TestImage")["ImageId"]

    USER1 = "123456789011"
    USER2 = "113355789012"

    ADD_USER_ARGS = {
        "ImageId": image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserIds": [USER1],
    }

    # Add users and get no images
    # Add users and get no images
    conn.modify_image_attribute(**ADD_USER_ARGS)

    attributes = conn.describe_image_attribute(
        ImageId=image_id, Attribute="LaunchPermissions", DryRun=False
    )
    attributes["LaunchPermissions"].should.have.length_of(1)
    attributes["LaunchPermissions"][0]["UserId"].should.equal(USER1)
    images = conn.describe_images(ExecutableUsers=[USER2])["Images"]
    images.should.have.length_of(0)


@mock_ec2
def test_ami_describe_executable_users_and_filter():
    conn = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", "us-east-1")
    ec2.create_instances(ImageId="", MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    image_id = conn.create_image(InstanceId=instance_id, Name="ImageToDelete")[
        "ImageId"
    ]

    USER1 = "123456789011"

    ADD_USER_ARGS = {
        "ImageId": image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserIds": [USER1],
    }

    # Add users and get no images
    conn.modify_image_attribute(**ADD_USER_ARGS)

    attributes = conn.describe_image_attribute(
        ImageId=image_id, Attribute="LaunchPermissions", DryRun=False
    )
    attributes["LaunchPermissions"].should.have.length_of(1)
    attributes["LaunchPermissions"][0]["UserId"].should.equal(USER1)
    images = conn.describe_images(
        ExecutableUsers=[USER1], Filters=[{"Name": "state", "Values": ["available"]}]
    )["Images"]
    images.should.have.length_of(1)
    images[0]["ImageId"].should.equal(image_id)


@mock_ec2_deprecated
def test_ami_attribute_user_and_group_permissions():
    """
      Boto supports adding/removing both users and groups at the same time.
      Just spot-check this -- input variations, idempotency, etc are validated
        via user-specific and group-specific tests above.
    """
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances("ami-1234abcd")
    instance = reservation.instances[0]
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)

    # Baseline
    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.name.should.equal("launch_permission")
    attributes.attrs.should.have.length_of(0)

    USER1 = "123456789011"
    USER2 = "123456789022"

    ADD_ARGS = {
        "image_id": image.id,
        "attribute": "launchPermission",
        "operation": "add",
        "groups": ["all"],
        "user_ids": [USER1, USER2],
    }

    REMOVE_ARGS = {
        "image_id": image.id,
        "attribute": "launchPermission",
        "operation": "remove",
        "groups": ["all"],
        "user_ids": [USER1, USER2],
    }

    # Add and confirm
    conn.modify_image_attribute(**ADD_ARGS)

    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.attrs["user_ids"].should.have.length_of(2)
    set(attributes.attrs["user_ids"]).should.equal(set([USER1, USER2]))
    set(attributes.attrs["groups"]).should.equal(set(["all"]))
    image = conn.get_image(image_id)
    image.is_public.should.equal(True)

    # Remove and confirm
    conn.modify_image_attribute(**REMOVE_ARGS)

    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.attrs.should.have.length_of(0)
    image = conn.get_image(image_id)
    image.is_public.should.equal(False)


@mock_ec2_deprecated
def test_ami_attribute_error_cases():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances("ami-1234abcd")
    instance = reservation.instances[0]
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)

    # Error: Add with group != 'all'
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id, attribute="launchPermission", operation="add", groups="everyone"
        )
    cm.exception.code.should.equal("InvalidAMIAttributeItemValue")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Add with user ID that isn't an integer.
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id,
            attribute="launchPermission",
            operation="add",
            user_ids="12345678901A",
        )
    cm.exception.code.should.equal("InvalidAMIAttributeItemValue")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Add with user ID that is > length 12.
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id,
            attribute="launchPermission",
            operation="add",
            user_ids="1234567890123",
        )
    cm.exception.code.should.equal("InvalidAMIAttributeItemValue")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Add with user ID that is < length 12.
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id,
            attribute="launchPermission",
            operation="add",
            user_ids="12345678901",
        )
    cm.exception.code.should.equal("InvalidAMIAttributeItemValue")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Add with one invalid user ID among other valid IDs, ensure no
    # partial changes.
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id,
            attribute="launchPermission",
            operation="add",
            user_ids=["123456789011", "foo", "123456789022"],
        )
    cm.exception.code.should.equal("InvalidAMIAttributeItemValue")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.attrs.should.have.length_of(0)

    # Error: Add with invalid image ID
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            "ami-abcd1234", attribute="launchPermission", operation="add", groups="all"
        )
    cm.exception.code.should.equal("InvalidAMIID.NotFound")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Error: Remove with invalid image ID
    with assert_raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            "ami-abcd1234",
            attribute="launchPermission",
            operation="remove",
            groups="all",
        )
    cm.exception.code.should.equal("InvalidAMIID.NotFound")
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_ami_describe_non_existent():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    # Valid pattern but non-existent id
    img = ec2.Image("ami-abcd1234")
    with assert_raises(ClientError):
        img.load()
    # Invalid ami pattern
    img = ec2.Image("not_an_ami_id")
    with assert_raises(ClientError):
        img.load()


@mock_ec2
def test_ami_registration():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    image_id = ec2.register_image(Name="test-register-image").get("ImageId", "")
    images = ec2.describe_images(ImageIds=[image_id]).get("Images", [])
    assert images[0]["Name"] == "test-register-image", "No image was registered."
    assert images[0]["RootDeviceName"] == "/dev/sda1", "Wrong root device name."
    assert images[0]["State"] == "available", "State should be available."


@mock_ec2
def test_ami_registration():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    image_id = ec2.register_image(Name="test-register-image").get("ImageId", "")
    images = ec2.describe_images(ImageIds=[image_id]).get("Images", [])
    assert images[0]["Name"] == "test-register-image", "No image was registered."
    assert images[0]["RootDeviceName"] == "/dev/sda1", "Wrong root device name."
    assert images[0]["State"] == "available", "State should be available."


@mock_ec2
def test_ami_filter_wildcard():
    ec2_resource = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")

    instance = ec2_resource.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
    )[0]
    instance.create_image(Name="test-image")

    # create an image with the same owner but will not match the filter
    instance.create_image(Name="not-matching-image")

    my_images = ec2_client.describe_images(
        Owners=[ACCOUNT_ID], Filters=[{"Name": "name", "Values": ["test*"]}]
    )["Images"]
    my_images.should.have.length_of(1)


@mock_ec2
def test_ami_filter_by_owner_id():
    client = boto3.client("ec2", region_name="us-east-1")

    ubuntu_id = "099720109477"

    ubuntu_images = client.describe_images(Owners=[ubuntu_id])
    all_images = client.describe_images()

    ubuntu_ids = [ami["OwnerId"] for ami in ubuntu_images["Images"]]
    all_ids = [ami["OwnerId"] for ami in all_images["Images"]]

    # Assert all ubuntu_ids are the same and one equals ubuntu_id
    assert all(ubuntu_ids) and ubuntu_ids[0] == ubuntu_id
    # Check we actually have a subset of images
    assert len(ubuntu_ids) < len(all_ids)


@mock_ec2
def test_ami_filter_by_self():
    ec2_resource = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")

    my_images = ec2_client.describe_images(Owners=["self"])["Images"]
    my_images.should.have.length_of(0)

    # Create a new image
    instance = ec2_resource.create_instances(
        ImageId="ami-1234abcd", MinCount=1, MaxCount=1
    )[0]
    instance.create_image(Name="test-image")

    my_images = ec2_client.describe_images(Owners=["self"])["Images"]
    my_images.should.have.length_of(1)


@mock_ec2
def test_ami_snapshots_have_correct_owner():
    ec2_client = boto3.client("ec2", region_name="us-west-1")

    images_response = ec2_client.describe_images()

    owner_id_to_snapshot_ids = {}
    for image in images_response["Images"]:
        owner_id = image["OwnerId"]
        snapshot_ids = [
            block_device_mapping["Ebs"]["SnapshotId"]
            for block_device_mapping in image["BlockDeviceMappings"]
        ]
        existing_snapshot_ids = owner_id_to_snapshot_ids.get(owner_id, [])
        owner_id_to_snapshot_ids[owner_id] = existing_snapshot_ids + snapshot_ids
        # adding an assertion to volumeType
        assert (
            image.get("BlockDeviceMappings", {})[0].get("Ebs", {}).get("VolumeType")
            == "standard"
        )
    for owner_id in owner_id_to_snapshot_ids:
        snapshots_rseponse = ec2_client.describe_snapshots(
            SnapshotIds=owner_id_to_snapshot_ids[owner_id]
        )

        for snapshot in snapshots_rseponse["Snapshots"]:
            assert owner_id == snapshot["OwnerId"]
