import boto
import boto.ec2
import boto3
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError

import pytest
import sure  # noqa # pylint: disable=unused-import
import random

from moto import mock_ec2_deprecated, mock_ec2
from moto.ec2.models import AMIS, OWNER_ID
from moto.core import ACCOUNT_ID
from tests import EXAMPLE_AMI_ID, EXAMPLE_AMI_PARAVIRTUAL
from tests.helpers import requires_boto_gte
from uuid import uuid4


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_create_and_delete():
    conn = boto.connect_ec2("the_key", "the_secret")

    initial_ami_count = len(AMIS)
    conn.get_all_volumes().should.have.length_of(0)
    conn.get_all_snapshots().should.have.length_of(initial_ami_count)

    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    with pytest.raises(EC2ResponseError) as ex:
        conn.create_image(instance.id, "test-ami", "this is a test ami", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
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
    snapshot.description.should.match("Created by CreateImage")

    # root device should be in AMI's block device mappings
    root_mapping = retrieved_image.block_device_mapping.get(
        retrieved_image.root_device_name
    )
    root_mapping.should_not.be.none

    # Deregister
    with pytest.raises(EC2ResponseError) as ex:
        success = conn.deregister_image(image_id, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DeregisterImage operation: Request would have succeeded, but DryRun flag is set"
    )

    success = conn.deregister_image(image_id)
    success.should.be.true

    with pytest.raises(EC2ResponseError) as cm:
        conn.deregister_image(image_id)
    cm.value.code.should.equal("InvalidAMIID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_snapshots_for_initial_amis():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    snapshots = ec2.describe_snapshots()["Snapshots"]
    snapshot_descs = [s["Description"] for s in snapshots]
    initial_ami_count = len(AMIS)

    assert (
        len(snapshots) >= initial_ami_count
    ), "Should have at least as many snapshots as AMIs"

    for ami in AMIS:
        ami_id = ami["ami_id"]
        expected_description = f"Auto-created snapshot for AMI {ami_id}"
        snapshot_descs.should.contain(expected_description)


@mock_ec2
def test_ami_create_and_delete_boto3():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]
    instance_id = instance["InstanceId"]

    with pytest.raises(ClientError) as ex:
        ec2.create_image(
            InstanceId=instance["InstanceId"], Name="test-ami", DryRun=True
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    err = ex.value.response["Error"]
    err["Code"].should.equal("DryRunOperation")
    err["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateImage operation: Request would have succeeded, but DryRun flag is set"
    )

    image_id = ec2.create_image(
        InstanceId=instance_id, Name="test-ami", Description="this is a test ami",
    )["ImageId"]

    all_images = ec2.describe_images()["Images"]
    set([i["ImageId"] for i in all_images]).should.contain(image_id)

    retrieved_image = [i for i in all_images if i["ImageId"] == image_id][0]

    retrieved_image.should.have.key("ImageId").equal(image_id)
    retrieved_image.should.have.key("VirtualizationType").equal(
        instance["VirtualizationType"]
    )
    retrieved_image.should.have.key("Architecture").equal(instance["Architecture"])
    retrieved_image.should.have.key("KernelId").equal(instance["KernelId"])
    retrieved_image.should.have.key("Platform").equal(instance["Platform"])
    retrieved_image.should.have.key("CreationDate")
    ec2.terminate_instances(InstanceIds=[instance_id])

    # Ensure we're no longer creating a volume
    volumes_for_instance = [
        v
        for v in ec2.describe_volumes()["Volumes"]
        if "Attachment" in v and v["Attachment"][0]["InstanceId"] == instance_id
    ]
    volumes_for_instance.should.have.length_of(0)

    # Validate auto-created snapshot
    snapshots = ec2.describe_snapshots()["Snapshots"]

    retrieved_image_snapshot_id = retrieved_image["BlockDeviceMappings"][0]["Ebs"][
        "SnapshotId"
    ]
    [s["SnapshotId"] for s in snapshots].should.contain(retrieved_image_snapshot_id)
    snapshot = [s for s in snapshots if s["SnapshotId"] == retrieved_image_snapshot_id][
        0
    ]
    image_id = retrieved_image["ImageId"]
    snapshot["Description"].should.equal(
        f"Created by CreateImage({instance_id}) for {image_id}"
    )

    # root device should be in AMI's block device mappings
    root_mapping = [
        m
        for m in retrieved_image["BlockDeviceMappings"]
        if m["DeviceName"] == retrieved_image["RootDeviceName"]
    ]
    root_mapping.should_not.equal([])

    # Deregister
    with pytest.raises(ClientError) as ex:
        ec2.deregister_image(ImageId=image_id, DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    err = ex.value.response["Error"]
    err["Code"].should.equal("DryRunOperation")
    err["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DeregisterImage operation: Request would have succeeded, but DryRun flag is set"
    )

    success = ec2.deregister_image(ImageId=image_id)
    success["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    with pytest.raises(ClientError) as ex:
        ec2.deregister_image(ImageId=image_id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidAMIID.NotFound")
    ex.value.response["ResponseMetadata"]["RequestId"].should_not.be.none


# Has boto3 equivalent
@requires_boto_gte("2.14.0")
@mock_ec2_deprecated
def test_ami_copy():
    conn = boto.ec2.connect_to_region("us-west-1")

    initial_ami_count = len(AMIS)
    conn.get_all_volumes().should.have.length_of(0)
    conn.get_all_snapshots().should.have.length_of(initial_ami_count)

    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    source_image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    instance.terminate()
    source_image = conn.get_all_images(image_ids=[source_image_id])[0]

    # Boto returns a 'CopyImage' object with an image_id attribute here. Use
    # the image_id to fetch the full info.
    with pytest.raises(EC2ResponseError) as ex:
        copy_image_ref = conn.copy_image(
            source_image.region.name,
            source_image.id,
            "test-copy-ami",
            "this is a test copy ami",
            dry_run=True,
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
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
    with pytest.raises(EC2ResponseError) as cm:
        conn.copy_image(
            source_image.region.name,
            "ami-abcd1234",
            "test-copy-ami",
            "this is a test copy ami",
        )
    cm.value.code.should.equal("InvalidAMIID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Copy from non-existent source region.
    with pytest.raises(EC2ResponseError) as cm:
        invalid_region = (
            "us-east-1" if (source_image.region.name != "us-east-1") else "us-west-1"
        )
        conn.copy_image(
            invalid_region, source_image.id, "test-copy-ami", "this is a test copy ami"
        )
    cm.value.code.should.equal("InvalidAMIID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_ami_copy_boto3_dryrun():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    source_image_id = ec2.create_image(
        InstanceId=instance["InstanceId"],
        Name="test-ami",
        Description="this is a test ami",
    )["ImageId"]
    source_image = ec2.describe_images(ImageIds=[source_image_id])["Images"][0]

    with pytest.raises(ClientError) as ex:
        ec2.copy_image(
            SourceRegion="us-west-1",
            SourceImageId=source_image["ImageId"],
            Name="test-copy-ami",
            Description="this is a test copy ami",
            DryRun=True,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    err = ex.value.response["Error"]
    err["Code"].should.equal("DryRunOperation")
    err["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CopyImage operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_ami_copy_boto3():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    source_image_id = ec2.create_image(
        InstanceId=instance["InstanceId"],
        Name="test-ami",
        Description="this is a test ami",
    )["ImageId"]
    ec2.terminate_instances(InstanceIds=[instance["InstanceId"]])
    source_image = ec2.describe_images(ImageIds=[source_image_id])["Images"][0]

    copy_image_ref = ec2.copy_image(
        SourceRegion="us-west-1",
        SourceImageId=source_image["ImageId"],
        Name="test-copy-ami",
        Description="this is a test copy ami",
    )
    copy_image_id = copy_image_ref["ImageId"]
    copy_image = ec2.describe_images(ImageIds=[copy_image_id])["Images"][0]

    copy_image["Name"].should.equal("test-copy-ami")
    copy_image["Description"].should.equal("this is a test copy ami")
    copy_image["ImageId"].should.equal(copy_image_id)
    copy_image["VirtualizationType"].should.equal(source_image["VirtualizationType"])
    copy_image["Architecture"].should.equal(source_image["Architecture"])
    copy_image["KernelId"].should.equal(source_image["KernelId"])
    copy_image["Platform"].should.equal(source_image["Platform"])

    # Validate auto-created snapshot
    source_image_snapshot_id = source_image["BlockDeviceMappings"][0]["Ebs"][
        "SnapshotId"
    ]
    copied_image_snapshot_id = copy_image["BlockDeviceMappings"][0]["Ebs"]["SnapshotId"]

    snapshot_ids = [s["SnapshotId"] for s in ec2.describe_snapshots()["Snapshots"]]
    snapshot_ids.should.contain(source_image_snapshot_id)
    snapshot_ids.should.contain(copied_image_snapshot_id)

    copied_image_snapshot_id.shouldnt.equal(source_image_snapshot_id)


@mock_ec2
def test_ami_copy_nonexistent_source_id():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    # Copy from non-existent source ID.
    with pytest.raises(ClientError) as ex:
        ec2.copy_image(
            SourceRegion="us-west-1",
            SourceImageId="ami-abcd1234",
            Name="test-copy-ami",
            Description="this is a test copy ami",
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIID.NotFound")


@mock_ec2
def test_ami_copy_nonexisting_source_region():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    source_image_id = ec2.create_image(
        InstanceId=instance["InstanceId"],
        Name="test-ami",
        Description="this is a test ami",
    )["ImageId"]
    source_image = ec2.describe_images(ImageIds=[source_image_id])["Images"][0]

    # Copy from non-existent source region.
    with pytest.raises(ClientError) as ex:
        ec2.copy_image(
            SourceRegion="us-east-1",
            SourceImageId=source_image["ImageId"],
            Name="test-copy-ami",
            Description="this is a test copy ami",
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIID.NotFound")


@mock_ec2
def test_copy_image_changes_owner_id():
    conn = boto3.client("ec2", region_name="us-east-1")

    # this source AMI ID is from moto/ec2/resources/amis.json
    source_ami_id = "ami-03cf127a"

    # confirm the source ami owner id is different from the default owner id.
    # if they're ever the same it means this test is invalid.
    check_resp = conn.describe_images(ImageIds=[source_ami_id])
    check_resp["Images"][0]["OwnerId"].should_not.equal(OWNER_ID)

    new_image_name = str(uuid4())[0:6]

    copy_resp = conn.copy_image(
        SourceImageId=source_ami_id,
        Name=new_image_name,
        Description="a copy of an image",
        SourceRegion="us-east-1",
    )

    describe_resp = conn.describe_images(
        Owners=["self"], Filters=[{"Name": "name", "Values": [new_image_name]}]
    )["Images"]
    describe_resp.should.have.length_of(1)
    describe_resp[0]["OwnerId"].should.equal(OWNER_ID)
    describe_resp[0]["ImageId"].should.equal(copy_resp["ImageId"])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_tagging():
    conn = boto.connect_vpc("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_all_images()[0]

    with pytest.raises(EC2ResponseError) as ex:
        image.add_tag("a key", "some value", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
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


@mock_ec2
def test_ami_tagging_boto3():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    res = boto3.resource("ec2", region_name="us-east-1")
    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]
    image_id = ec2.create_image(
        InstanceId=instance["InstanceId"],
        Name="test-ami",
        Description="this is a test ami",
    )["ImageId"]
    image = res.Image(image_id)

    with pytest.raises(ClientError) as ex:
        image.create_tags(Tags=[{"Key": "a key", "Value": "some value"}], DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    err = ex.value.response["Error"]
    err["Code"].should.equal("DryRunOperation")
    err["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    image.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])
    image.tags.should.equal([{"Value": "some value", "Key": "a key"}])

    image = ec2.describe_images(ImageIds=[image_id])["Images"][0]
    image["Tags"].should.equal([{"Value": "some value", "Key": "a key"}])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_create_from_missing_instance():
    conn = boto.connect_ec2("the_key", "the_secret")
    args = ["i-abcdefg", "test-ami", "this is a test ami"]

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_image(*args)
    cm.value.code.should.equal("InvalidInstanceID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_ami_create_from_missing_instance_boto3():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.create_image(
            InstanceId="i-abcdefg", Name="test-ami", Description="this is a test ami"
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidInstanceID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_pulls_attributes_from_instance():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    instance.modify_attribute("kernel", "test-kernel")

    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)
    image.kernel_id.should.equal("test-kernel")


@mock_ec2
def test_ami_pulls_attributes_from_instance_boto3():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]
    ec2.modify_instance_attribute(
        InstanceId=instance["InstanceId"], Kernel={"Value": "test-kernel"}
    )

    image_id = ec2.create_image(InstanceId=instance["InstanceId"], Name="test-ami")[
        "ImageId"
    ]
    image = boto3.resource("ec2", region_name="us-east-1").Image(image_id)
    image.kernel_id.should.equal("test-kernel")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_uses_account_id_if_valid_access_key_is_supplied():
    access_key = "AKIAXXXXXXXXXXXXXXXX"
    conn = boto.connect_ec2(access_key, "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    instance.modify_attribute("kernel", "test-kernel")

    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    images = conn.get_all_images(owners=["self"])
    [(ami.id, ami.owner_id) for ami in images].should.equal([(image_id, ACCOUNT_ID)])


@mock_ec2
def test_ami_uses_account_id_if_valid_access_key_is_supplied_boto3():
    # The boto-equivalent required an access_key to be passed in, but Moto will always mock this in boto3
    # So the only thing we're testing here, really.. is whether OwnerId is equal to ACCOUNT_ID?
    # TODO: Maybe patch account_id with multiple values, and verify it always  matches with OwnerId
    ec2 = boto3.client("ec2", region_name="us-east-1")
    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    image_id = ec2.create_image(InstanceId=instance["InstanceId"], Name="test-ami")[
        "ImageId"
    ]
    images = ec2.describe_images(Owners=["self"])["Images"]
    [(ami["ImageId"], ami["OwnerId"]) for ami in images].should.contain(
        (image_id, ACCOUNT_ID)
    )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_filters():
    conn = boto.connect_ec2("the_key", "the_secret")

    reservationA = conn.run_instances(EXAMPLE_AMI_ID)
    instanceA = reservationA.instances[0]
    instanceA.modify_attribute("architecture", "i386")
    instanceA.modify_attribute("kernel", "k-1234abcd")
    instanceA.modify_attribute("platform", "windows")
    instanceA.modify_attribute("virtualization_type", "hvm")
    imageA_id = conn.create_image(instanceA.id, "test-ami-A", "this is a test ami")
    imageA = conn.get_image(imageA_id)

    reservationB = conn.run_instances(EXAMPLE_AMI_ID)
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
    len(amis_by_architecture).should.equal(39)

    amis_by_kernel = conn.get_all_images(filters={"kernel-id": "k-abcd1234"})
    set([ami.id for ami in amis_by_kernel]).should.equal(set([imageB.id]))

    amis_by_virtualization = conn.get_all_images(
        filters={"virtualization-type": "paravirtual"}
    )
    set([ami.id for ami in amis_by_virtualization]).should.contain(imageB.id)
    len(amis_by_virtualization).should.equal(3)

    amis_by_platform = conn.get_all_images(filters={"platform": "windows"})
    set([ami.id for ami in amis_by_platform]).should.contain(imageA.id)
    len(amis_by_platform).should.equal(25)

    amis_by_id = conn.get_all_images(filters={"image-id": imageA.id})
    set([ami.id for ami in amis_by_id]).should.equal(set([imageA.id]))

    amis_by_state = conn.get_all_images(filters={"state": "available"})
    ami_ids_by_state = [ami.id for ami in amis_by_state]
    ami_ids_by_state.should.contain(imageA.id)
    ami_ids_by_state.should.contain(imageB.id)
    len(amis_by_state).should.equal(40)

    amis_by_name = conn.get_all_images(filters={"name": imageA.name})
    set([ami.id for ami in amis_by_name]).should.equal(set([imageA.id]))

    amis_by_public = conn.get_all_images(filters={"is-public": "true"})
    set([ami.id for ami in amis_by_public]).should.contain(imageB.id)
    len(amis_by_public).should.equal(39)

    amis_by_nonpublic = conn.get_all_images(filters={"is-public": "false"})
    set([ami.id for ami in amis_by_nonpublic]).should.contain(imageA.id)
    len(amis_by_nonpublic).should.equal(1)


@mock_ec2
def test_ami_filters_boto3():
    image_name_A = f"test-ami-{str(uuid4())[0:6]}"
    kernel_value_A = f"k-{str(uuid4())[0:6]}"
    kernel_value_B = f"k-{str(uuid4())[0:6]}"

    ec2 = boto3.client("ec2", region_name="us-east-1")
    reservationA = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instanceA = reservationA["Instances"][0]
    ec2.modify_instance_attribute(
        InstanceId=instanceA["InstanceId"], Kernel={"Value": kernel_value_A}
    )

    imageA_id = ec2.create_image(InstanceId=instanceA["InstanceId"], Name=image_name_A)[
        "ImageId"
    ]
    imageA = boto3.resource("ec2", region_name="us-east-1").Image(imageA_id)

    reservationB = ec2.run_instances(
        ImageId=EXAMPLE_AMI_PARAVIRTUAL, MinCount=1, MaxCount=1
    )
    instanceB = reservationB["Instances"][0]
    ec2.modify_instance_attribute(
        InstanceId=instanceB["InstanceId"], Kernel={"Value": kernel_value_B}
    )
    imageB_id = ec2.create_image(InstanceId=instanceB["InstanceId"], Name="test-ami-B")[
        "ImageId"
    ]
    imageB = boto3.resource("ec2", region_name="us-east-1").Image(imageB_id)
    imageB.modify_attribute(LaunchPermission={"Add": [{"Group": "all"}]})

    amis_by_architecture = ec2.describe_images(
        Filters=[{"Name": "architecture", "Values": ["x86_64"]}]
    )["Images"]
    [ami["ImageId"] for ami in amis_by_architecture].should.contain(imageB_id)
    assert (
        len(amis_by_architecture) >= 40
    ), "Should have at least 40 AMI's of type x86_64"

    amis_by_kernel = ec2.describe_images(
        Filters=[{"Name": "kernel-id", "Values": [kernel_value_B]}]
    )["Images"]
    [ami["ImageId"] for ami in amis_by_kernel].should.equal([imageB.id])

    amis_by_virtualization = ec2.describe_images(
        Filters=[{"Name": "virtualization-type", "Values": ["paravirtual"]}]
    )["Images"]
    [ami["ImageId"] for ami in amis_by_virtualization].should.contain(imageB.id)
    assert len(amis_by_virtualization) >= 3, "Should have at least 3 paravirtual AMI's"

    amis_by_platform = ec2.describe_images(
        Filters=[{"Name": "platform", "Values": ["windows"]}]
    )["Images"]
    [ami["ImageId"] for ami in amis_by_platform].should.contain(imageA_id)
    assert len(amis_by_platform) >= 25, "Should have at least 25 Windows images"

    amis_by_id = ec2.describe_images(
        Filters=[{"Name": "image-id", "Values": [imageA_id]}]
    )["Images"]
    [ami["ImageId"] for ami in amis_by_id].should.equal([imageA_id])

    amis_by_state = ec2.describe_images(
        Filters=[{"Name": "state", "Values": ["available"]}]
    )["Images"]
    ami_ids_by_state = [ami["ImageId"] for ami in amis_by_state]
    ami_ids_by_state.should.contain(imageA_id)
    ami_ids_by_state.should.contain(imageB.id)
    assert len(amis_by_state) >= 40, "Should have at least 40 images available"

    amis_by_name = ec2.describe_images(
        Filters=[{"Name": "name", "Values": [imageA.name]}]
    )["Images"]
    [ami["ImageId"] for ami in amis_by_name].should.equal([imageA.id])

    amis_by_public = ec2.describe_images(
        Filters=[{"Name": "is-public", "Values": ["true"]}]
    )["Images"]
    assert len(amis_by_public) >= 38, "Should have at least 38 public images"

    amis_by_nonpublic = ec2.describe_images(
        Filters=[{"Name": "is-public", "Values": ["false"]}]
    )["Images"]
    [ami["ImageId"] for ami in amis_by_nonpublic].should.contain(imageA.id)
    assert len(amis_by_nonpublic) >= 2, "Should have at least 2 non-public images"


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_filtering_via_tag():
    conn = boto.connect_vpc("the_key", "the_secret")

    reservationA = conn.run_instances(EXAMPLE_AMI_ID)
    instanceA = reservationA.instances[0]
    imageA_id = conn.create_image(instanceA.id, "test-ami-A", "this is a test ami")
    imageA = conn.get_image(imageA_id)
    imageA.add_tag("a key", "some value")

    reservationB = conn.run_instances(EXAMPLE_AMI_ID)
    instanceB = reservationB.instances[0]
    imageB_id = conn.create_image(instanceB.id, "test-ami-B", "this is a test ami")
    imageB = conn.get_image(imageB_id)
    imageB.add_tag("another key", "some other value")

    amis_by_tagA = conn.get_all_images(filters={"tag:a key": "some value"})
    set([ami.id for ami in amis_by_tagA]).should.equal(set([imageA.id]))

    amis_by_tagB = conn.get_all_images(filters={"tag:another key": "some other value"})
    set([ami.id for ami in amis_by_tagB]).should.equal(set([imageB.id]))


@mock_ec2
def test_ami_filtering_via_tag_boto3():
    tag_value = f"value {str(uuid4())}"
    other_value = f"value {str(uuid4())}"
    ec2 = boto3.client("ec2", region_name="us-east-1")
    reservationA = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instanceA = reservationA["Instances"][0]

    imageA_id = ec2.create_image(InstanceId=instanceA["InstanceId"], Name="test-ami-A")[
        "ImageId"
    ]
    imageA = boto3.resource("ec2", region_name="us-east-1").Image(imageA_id)
    imageA.create_tags(Tags=[{"Key": "a key", "Value": tag_value}])

    reservationB = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instanceB = reservationB["Instances"][0]
    imageB_id = ec2.create_image(InstanceId=instanceB["InstanceId"], Name="test-ami-B")[
        "ImageId"
    ]
    imageB = boto3.resource("ec2", region_name="us-east-1").Image(imageB_id)
    imageB.create_tags(Tags=[{"Key": "another key", "Value": other_value}])

    amis_by_tagA = ec2.describe_images(
        Filters=[{"Name": "tag:a key", "Values": [tag_value]}]
    )["Images"]
    [ami["ImageId"] for ami in amis_by_tagA].should.equal([imageA_id])

    amis_by_tagB = ec2.describe_images(
        Filters=[{"Name": "tag:another key", "Values": [other_value]}]
    )["Images"]
    [ami["ImageId"] for ami in amis_by_tagB].should.equal([imageB_id])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_getting_missing_ami():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_image("ami-missing")
    cm.value.code.should.equal("InvalidAMIID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_getting_missing_ami_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.Image("ami-missing").load()
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_getting_malformed_ami():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_image("foo-missing")
    cm.value.code.should.equal("InvalidAMIID.Malformed")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_getting_malformed_ami_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.Image("foo-missing").load()
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIID.Malformed")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_attribute_group_permissions():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
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
    with pytest.raises(EC2ResponseError) as ex:
        conn.modify_image_attribute(**dict(ADD_GROUP_ARGS, **{"dry_run": True}))
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
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


@mock_ec2
def test_ami_attribute_group_permissions_boto3():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    image_id = ec2.create_image(InstanceId=instance["InstanceId"], Name="test-ami-A")[
        "ImageId"
    ]
    image = boto3.resource("ec2", region_name="us-east-1").Image(image_id)

    # Baseline
    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.equal([])

    ADD_GROUP_ARGS = {
        "ImageId": image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserGroups": ["all"],
    }

    REMOVE_GROUP_ARGS = {
        "ImageId": image_id,
        "Attribute": "launchPermission",
        "OperationType": "remove",
        "UserGroups": ["all"],
    }

    # Add 'all' group and confirm
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyImageAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    image.modify_attribute(**ADD_GROUP_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.equal([{"Group": "all"}])
    image.reload()
    image.public.should.equal(True)

    # Add is idempotent
    image.modify_attribute(**ADD_GROUP_ARGS)

    # Remove 'all' group and confirm
    image.modify_attribute(**REMOVE_GROUP_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.equal([])
    image.reload()
    image.public.should.equal(False)

    # Remove is idempotent
    image.modify_attribute(**REMOVE_GROUP_ARGS)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_attribute_user_permissions():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
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
def test_ami_attribute_user_permissions_boto3():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    image_id = ec2.create_image(InstanceId=instance["InstanceId"], Name="test-ami-A")[
        "ImageId"
    ]
    image = boto3.resource("ec2", region_name="us-east-1").Image(image_id)

    # Baseline
    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.equal([])

    USER1 = "".join(["{}".format(random.randint(0, 9)) for _ in range(0, 12)])
    USER2 = "".join(["{}".format(random.randint(0, 9)) for _ in range(0, 12)])

    ADD_USERS_ARGS = {
        "ImageId": image.id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserIds": [USER1, USER2],
    }

    REMOVE_USERS_ARGS = {
        "ImageId": image.id,
        "Attribute": "launchPermission",
        "OperationType": "remove",
        "UserIds": [USER1, USER2],
    }

    REMOVE_SINGLE_USER_ARGS = {
        "ImageId": image.id,
        "Attribute": "launchPermission",
        "OperationType": "remove",
        "UserIds": [USER1],
    }

    # Add multiple users and confirm
    image.modify_attribute(**ADD_USERS_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.have.length_of(2)
    permissions.should.contain({"UserId": USER1})
    permissions.should.contain({"UserId": USER2})
    image.reload()
    image.public.should.equal(False)

    # Add is idempotent
    image.modify_attribute(**ADD_USERS_ARGS)

    # Remove single user and confirm
    image.modify_attribute(**REMOVE_SINGLE_USER_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.equal([{"UserId": USER2}])
    image.reload()
    image.public.should.equal(False)

    # Remove multiple users and confirm
    image.modify_attribute(**REMOVE_USERS_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.equal([])
    image.reload()
    image.public.should.equal(False)

    # Remove is idempotent
    image.modify_attribute(**REMOVE_USERS_ARGS)


@mock_ec2
def test_ami_describe_executable_users():
    conn = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", "us-east-1")
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    image_id = conn.create_image(InstanceId=instance_id, Name="TestImage")["ImageId"]

    USER1 = "".join(["{}".format(random.randint(0, 9)) for _ in range(0, 12)])

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
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    image_id = conn.create_image(InstanceId=instance_id, Name="TestImage")["ImageId"]

    USER1 = "".join(["{}".format(random.randint(0, 9)) for _ in range(0, 12)])
    USER2 = "".join(["{}".format(random.randint(0, 9)) for _ in range(0, 12)])

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
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    image_id = conn.create_image(InstanceId=instance_id, Name="ImageToDelete")[
        "ImageId"
    ]

    USER1 = "".join(["{}".format(random.randint(0, 9)) for _ in range(0, 12)])

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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_attribute_user_and_group_permissions():
    """
    Boto supports adding/removing both users and groups at the same time.
    Just spot-check this -- input variations, idempotency, etc are validated
      via user-specific and group-specific tests above.
    """
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
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


@mock_ec2
def test_ami_attribute_user_and_group_permissions_boto3():
    """
    Boto supports adding/removing both users and groups at the same time.
    Just spot-check this -- input variations, idempotency, etc are validated
      via user-specific and group-specific tests above.
    """
    ec2 = boto3.client("ec2", region_name="us-east-1")
    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    image_id = ec2.create_image(InstanceId=instance["InstanceId"], Name="test-ami-A")[
        "ImageId"
    ]
    image = boto3.resource("ec2", region_name="us-east-1").Image(image_id)

    # Baseline
    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.equal([])

    USER1 = "123456789011"
    USER2 = "123456789022"

    ADD_ARGS = {
        "ImageId": image.id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserGroups": ["all"],
        "UserIds": [USER1, USER2],
    }

    REMOVE_ARGS = {
        "ImageId": image.id,
        "Attribute": "launchPermission",
        "OperationType": "remove",
        "UserGroups": ["all"],
        "UserIds": [USER1, USER2],
    }

    # Add and confirm
    image.modify_attribute(**ADD_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.have.length_of(3)
    permissions.should.contain({"Group": "all"})
    permissions.should.contain({"UserId": "123456789022"})
    permissions.should.contain({"UserId": "123456789011"})
    image.reload()
    image.public.should.equal(True)

    # Remove and confirm
    image.modify_attribute(**REMOVE_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.equal([])
    image.reload()
    image.public.should.equal(False)


@mock_ec2
def test_filter_description():
    # https://github.com/spulec/moto/issues/4460
    client = boto3.client("ec2", region_name="us-west-2")

    # Search for partial description
    resp = client.describe_images(
        Owners=["amazon"],
        Filters=[{"Name": "description", "Values": ["Amazon Linux AMI*"]}],
    )["Images"]
    resp.should.have.length_of(4)

    # Search for full description
    resp = client.describe_images(
        Owners=["amazon"],
        Filters=[
            {
                "Name": "description",
                "Values": ["Amazon Linux AMI 2018.03.0.20210721.0 x86_64 VPC HVM ebs"],
            }
        ],
    )["Images"]
    resp.should.have.length_of(1)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_ami_attribute_error_cases():
    conn = boto.connect_ec2("the_key", "the_secret")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)

    # Error: Add with group != 'all'
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id, attribute="launchPermission", operation="add", groups="everyone"
        )
    cm.value.code.should.equal("InvalidAMIAttributeItemValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Add with user ID that isn't an integer.
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id,
            attribute="launchPermission",
            operation="add",
            user_ids="12345678901A",
        )
    cm.value.code.should.equal("InvalidAMIAttributeItemValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Add with user ID that is > length 12.
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id,
            attribute="launchPermission",
            operation="add",
            user_ids="1234567890123",
        )
    cm.value.code.should.equal("InvalidAMIAttributeItemValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Add with user ID that is < length 12.
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id,
            attribute="launchPermission",
            operation="add",
            user_ids="12345678901",
        )
    cm.value.code.should.equal("InvalidAMIAttributeItemValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Add with one invalid user ID among other valid IDs, ensure no
    # partial changes.
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            image.id,
            attribute="launchPermission",
            operation="add",
            user_ids=["123456789011", "foo", "123456789022"],
        )
    cm.value.code.should.equal("InvalidAMIAttributeItemValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    attributes = conn.get_image_attribute(image.id, attribute="launchPermission")
    attributes.attrs.should.have.length_of(0)

    # Error: Add with invalid image ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            "ami-abcd1234", attribute="launchPermission", operation="add", groups="all"
        )
    cm.value.code.should.equal("InvalidAMIID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Remove with invalid image ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_image_attribute(
            "ami-abcd1234",
            attribute="launchPermission",
            operation="remove",
            groups="all",
        )
    cm.value.code.should.equal("InvalidAMIID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_ami_attribute_error_cases_boto3():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    image_id = ec2.create_image(InstanceId=instance["InstanceId"], Name="test-ami-A")[
        "ImageId"
    ]
    image = boto3.resource("ec2", region_name="us-east-1").Image(image_id)

    # Error: Add with group != 'all'
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId=image_id,
            Attribute="launchPermission",
            OperationType="add",
            UserGroups=["everyone"],
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIAttributeItemValue")

    # Error: Add with user ID that isn't an integer.
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId=image_id,
            Attribute="launchPermission",
            OperationType="add",
            UserIds=["12345678901A"],
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIAttributeItemValue")

    # Error: Add with user ID that is > length 12.
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId=image_id,
            Attribute="launchPermission",
            OperationType="add",
            UserIds=["1234567890123"],
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIAttributeItemValue")

    # Error: Add with user ID that is < length 12.
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId=image_id,
            Attribute="launchPermission",
            OperationType="add",
            UserIds=["12345678901"],
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIAttributeItemValue")

    # Error: Add with one invalid user ID among other valid IDs, ensure no
    # partial changes.
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId=image_id,
            Attribute="launchPermission",
            OperationType="add",
            UserIds=["123456789011", "foo", "123456789022"],
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIAttributeItemValue")

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    permissions.should.equal([])

    # Error: Add with invalid image ID
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId="ami-abcd1234",
            Attribute="launchPermission",
            OperationType="add",
            UserGroups=["all"],
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIID.NotFound")

    # Error: Remove with invalid image ID
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId="ami-abcd1234",
            Attribute="launchPermission",
            OperationType="remove",
            UserGroups=["all"],
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidAMIID.NotFound")


@mock_ec2
def test_ami_describe_non_existent():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    # Valid pattern but non-existent id
    img = ec2.Image("ami-abcd1234")
    with pytest.raises(ClientError):
        img.load()
    # Invalid ami pattern
    img = ec2.Image("not_an_ami_id")
    with pytest.raises(ClientError):
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
def test_ami_filter_wildcard():
    ec2_resource = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")

    image_name = str(uuid4())[0:6]

    instance = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]
    instance.create_image(Name=image_name)

    # create an image with the same owner but will not match the filter
    instance.create_image(Name=str(uuid4())[0:6])

    my_images = ec2_client.describe_images(
        Owners=[ACCOUNT_ID],
        Filters=[{"Name": "name", "Values": [f"{image_name[0:4]}*"]}],
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

    unique_name = str(uuid4())[0:6]

    images = ec2_client.describe_images(Owners=["self"])["Images"]
    image_names = [i["Name"] for i in images]
    image_names.shouldnt.contain(unique_name)

    # Create a new image
    instance = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]
    instance.create_image(Name=unique_name)

    images = ec2_client.describe_images(Owners=["self"])["Images"]
    image_names = [i["Name"] for i in images]
    image_names.should.contain(unique_name)


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


@mock_ec2
def test_create_image_with_tag_specification():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    tag_specifications = [
        {
            "ResourceType": "image",
            "Tags": [
                {
                    "Key": "Base_AMI_Name",
                    "Value": "Deep Learning Base AMI (Amazon Linux 2) Version 31.0",
                },
                {"Key": "OS_Version", "Value": "AWS Linux 2",},
            ],
        },
    ]
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]
    image_id = client.create_image(
        InstanceId=instance.instance_id,
        Name="test-image",
        Description="test ami",
        TagSpecifications=tag_specifications,
    )["ImageId"]

    image = client.describe_images(ImageIds=[image_id])["Images"][0]
    image["Tags"].should.equal(tag_specifications[0]["Tags"])

    with pytest.raises(ClientError) as ex:
        client.create_image(
            InstanceId=instance.instance_id,
            Name="test-image",
            Description="test ami",
            TagSpecifications=[
                {
                    "ResourceType": "invalid-resource-type",
                    "Tags": [{"Key": "key", "Value": "value"}],
                }
            ],
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")
    ex.value.response["Error"]["Message"].should.equal(
        "'invalid-resource-type' is not a valid taggable resource type for this operation."
    )


@mock_ec2
def test_ami_filter_by_empty_tag():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    fake_images = []
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]
    for i in range(10):
        image = client.create_image(
            InstanceId=instance.instance_id,
            Name="MyAMI{}".format(i),
            Description="Test",
        )

        ec2.create_tags(
            Resources=[image["ImageId"]],
            Tags=[
                {
                    "Key": "Base_AMI_Name",
                    "Value": "Deep Learning Base AMI (Amazon Linux 2) Version 31.0",
                },
                {"Key": "OS_Version", "Value": "AWS Linux 2"},
            ],
        )
        fake_images.append(image)
    # Add release tags to some of the images in the middle
    release_version = str(uuid4())[0:6]
    for image in fake_images[3:6]:
        ec2.create_tags(
            Resources=[image["ImageId"]],
            Tags=[{"Key": "RELEASE", "Value": release_version}],
        )
    images_filter = [
        {
            "Name": "tag:Base_AMI_Name",
            "Values": ["Deep Learning Base AMI (Amazon Linux 2) Version 31.0"],
        },
        {"Name": "tag:OS_Version", "Values": ["AWS Linux 2"]},
        {"Name": "tag:RELEASE", "Values": [release_version]},
    ]
    assert len(client.describe_images(Filters=images_filter)["Images"]) == 3


@mock_ec2
def test_ami_filter_by_ownerid():
    ec2_connection = boto3.client("ec2", region_name="us-east-1")

    images = ec2_connection.describe_images(
        Filters=[
            {"Name": "name", "Values": ["amzn-ami-*",]},
            {"Name": "owner-alias", "Values": ["amazon",]},
        ]
    )["Images"]
    assert len(images) > 0, "We should have at least 1 image created by amazon"


@mock_ec2
def test_ami_filter_by_unknown_ownerid():
    ec2_connection = boto3.client("ec2", region_name="us-east-1")

    images = ec2_connection.describe_images(
        Filters=[{"Name": "owner-alias", "Values": ["unknown",]},]
    )["Images"]
    images.should.have.length_of(0)


@mock_ec2
def test_describe_images_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_images(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DescribeImages operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_delete_snapshot_from_create_image():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    resp = ec2_client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance_id = resp["Instances"][0]["InstanceId"]
    ami = ec2_client.create_image(InstanceId=instance_id, Name="test")
    ami_id = ami["ImageId"]

    snapshots = ec2_client.describe_snapshots(
        Filters=[
            {
                "Name": "description",
                "Values": ["Created by CreateImage(" + instance_id + "*"],
            }
        ]
    )["Snapshots"]
    snapshot_id = snapshots[0]["SnapshotId"]
    with pytest.raises(ClientError) as exc:
        ec2_client.delete_snapshot(SnapshotId=snapshot_id)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidSnapshot.InUse")
    err["Message"].should.equal(
        f"The snapshot {snapshot_id} is currently in use by {ami_id}"
    )

    # Deregister the Ami first
    ec2_client.deregister_image(ImageId=ami_id)

    # Now we can delete the snapshot without problems
    ec2_client.delete_snapshot(SnapshotId=snapshot_id)

    with pytest.raises(ClientError) as exc:
        ec2_client.describe_snapshots(SnapshotIds=[snapshot_id])
    exc.value.response["Error"]["Code"].should.equal("InvalidSnapshot.NotFound")
