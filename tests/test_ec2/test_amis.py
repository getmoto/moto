import os
import random
from unittest import SkipTest, mock
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.ec2.models.amis import AMIS
from tests import EXAMPLE_AMI_ID, EXAMPLE_AMI_PARAVIRTUAL


# The default AMIs are not loaded for our test case, to speed things up
# But we do need it for this specific test (and others in this file..)
@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_snapshots_for_initial_amis():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
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
        assert expected_description in snapshot_descs


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ami_create_and_delete():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    ec2 = boto3.client("ec2", region_name="us-east-1")

    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]
    instance_id = instance["InstanceId"]

    with pytest.raises(ClientError) as ex:
        ec2.create_image(
            InstanceId=instance["InstanceId"], Name="test-ami", DryRun=True
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    err = ex.value.response["Error"]
    assert err["Code"] == "DryRunOperation"
    assert (
        err["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateImage operation: Request would have succeeded, but DryRun flag is set"
    )

    image_id = ec2.create_image(
        InstanceId=instance_id, Name="test-ami", Description="this is a test ami"
    )["ImageId"]

    all_images = ec2.describe_images()["Images"]
    assert image_id in set([i["ImageId"] for i in all_images])

    retrieved_image = [i for i in all_images if i["ImageId"] == image_id][0]

    assert retrieved_image["ImageId"] == image_id
    assert retrieved_image["VirtualizationType"] == instance["VirtualizationType"]
    assert retrieved_image["Architecture"] == instance["Architecture"]
    assert retrieved_image["KernelId"] == instance["KernelId"]
    assert retrieved_image["Platform"] == instance["Platform"]
    assert "CreationDate" in retrieved_image
    ec2.terminate_instances(InstanceIds=[instance_id])

    # Ensure we're no longer creating a volume
    volumes_for_instance = [
        v
        for v in ec2.describe_volumes()["Volumes"]
        if "Attachment" in v and v["Attachment"][0]["InstanceId"] == instance_id
    ]
    assert len(volumes_for_instance) == 0

    # Validate auto-created snapshot
    snapshots = ec2.describe_snapshots()["Snapshots"]

    retrieved_image_snapshot_id = retrieved_image["BlockDeviceMappings"][0]["Ebs"][
        "SnapshotId"
    ]
    assert retrieved_image_snapshot_id in [s["SnapshotId"] for s in snapshots]
    snapshot = [s for s in snapshots if s["SnapshotId"] == retrieved_image_snapshot_id][
        0
    ]
    image_id = retrieved_image["ImageId"]
    assert (
        snapshot["Description"]
        == f"Created by CreateImage({instance_id}) for {image_id}"
    )

    # root device should be in AMI's block device mappings
    root_mapping = [
        m
        for m in retrieved_image["BlockDeviceMappings"]
        if m["DeviceName"] == retrieved_image["RootDeviceName"]
    ]
    assert root_mapping != []

    # Deregister
    with pytest.raises(ClientError) as ex:
        ec2.deregister_image(ImageId=image_id, DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    err = ex.value.response["Error"]
    assert err["Code"] == "DryRunOperation"
    assert (
        err["Message"]
        == "An error occurred (DryRunOperation) when calling the DeregisterImage operation: Request would have succeeded, but DryRun flag is set"
    )

    success = ec2.deregister_image(ImageId=image_id)
    assert success["ResponseMetadata"]["HTTPStatusCode"] == 200

    with pytest.raises(ClientError) as ex:
        ec2.deregister_image(ImageId=image_id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidAMIID.Unavailable"
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None


@mock_aws
def test_deregister_image__unknown():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.deregister_image(ImageId="ami-unknown-ami")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidAMIID.NotFound"
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None


@mock_aws
def test_deregister_image__and_describe():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]
    instance_id = instance["InstanceId"]

    image_id = ec2.create_image(
        InstanceId=instance_id, Name="test-ami", Description="this is a test ami"
    )["ImageId"]

    ec2.deregister_image(ImageId=image_id)

    # Searching for a deleted image ID should not throw an error
    # It should simply not return this image
    assert len(ec2.describe_images(ImageIds=[image_id])["Images"]) == 0


@mock_aws
def test_ami_copy_dryrun():
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
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    err = ex.value.response["Error"]
    assert err["Code"] == "DryRunOperation"
    assert (
        err["Message"]
        == "An error occurred (DryRunOperation) when calling the CopyImage operation: Request would have succeeded, but DryRun flag is set"
    )


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ami_copy():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
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

    assert copy_image["Name"] == "test-copy-ami"
    assert copy_image["Description"] == "this is a test copy ami"
    assert copy_image["ImageId"] == copy_image_id
    assert copy_image["VirtualizationType"] == source_image["VirtualizationType"]
    assert copy_image["Architecture"] == source_image["Architecture"]
    assert copy_image["KernelId"] == source_image["KernelId"]
    assert copy_image["Platform"] == source_image["Platform"]

    # Validate auto-created snapshot
    source_image_snapshot_id = source_image["BlockDeviceMappings"][0]["Ebs"][
        "SnapshotId"
    ]
    copied_image_snapshot_id = copy_image["BlockDeviceMappings"][0]["Ebs"]["SnapshotId"]

    snapshot_ids = [s["SnapshotId"] for s in ec2.describe_snapshots()["Snapshots"]]
    assert source_image_snapshot_id in snapshot_ids
    assert copied_image_snapshot_id in snapshot_ids

    assert copied_image_snapshot_id != source_image_snapshot_id


@mock_aws
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
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIID.NotFound"


@mock_aws
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
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIID.NotFound"


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_copy_image_changes_owner_id():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    conn = boto3.client("ec2", region_name="us-east-1")

    # this source AMI ID is from moto/ec2/resources/amis.json
    source_ami_id = "ami-03cf127a"

    # confirm the source ami owner id is different from the default owner id.
    # if they're ever the same it means this test is invalid.
    check_resp = conn.describe_images(ImageIds=[source_ami_id])
    assert check_resp["Images"][0]["OwnerId"] != ACCOUNT_ID

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
    assert len(describe_resp) == 1
    assert describe_resp[0]["OwnerId"] == ACCOUNT_ID
    assert describe_resp[0]["ImageId"] == copy_resp["ImageId"]


@mock_aws
def test_ami_tagging():
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
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    err = ex.value.response["Error"]
    assert err["Code"] == "DryRunOperation"
    assert (
        err["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    image.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])
    assert image.tags == [{"Value": "some value", "Key": "a key"}]

    image = ec2.describe_images(ImageIds=[image_id])["Images"][0]
    assert image["Tags"] == [{"Value": "some value", "Key": "a key"}]


@mock_aws
def test_ami_create_from_missing_instance():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.create_image(
            InstanceId="i-abcdefg", Name="test-ami", Description="this is a test ami"
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidInstanceID.NotFound"


@mock_aws
def test_ami_pulls_attributes_from_instance():
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
    assert image.kernel_id == "test-kernel"


@mock_aws
def test_ami_uses_account_id_if_valid_access_key_is_supplied():
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
    assert (image_id, ACCOUNT_ID) in [
        (ami["ImageId"], ami["OwnerId"]) for ami in images
    ]


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ami_filters():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
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
    assert imageB.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ] == [{"Group": "all"}]

    amis_by_architecture = ec2.describe_images(
        Filters=[{"Name": "architecture", "Values": ["x86_64"]}]
    )["Images"]
    assert imageB_id in [ami["ImageId"] for ami in amis_by_architecture]
    assert (
        len(amis_by_architecture) >= 40
    ), "Should have at least 40 AMI's of type x86_64"

    amis_by_kernel = ec2.describe_images(
        Filters=[{"Name": "kernel-id", "Values": [kernel_value_B]}]
    )["Images"]
    assert [ami["ImageId"] for ami in amis_by_kernel] == [imageB.id]

    amis_by_virtualization = ec2.describe_images(
        Filters=[{"Name": "virtualization-type", "Values": ["paravirtual"]}]
    )["Images"]
    assert imageB.id in [ami["ImageId"] for ami in amis_by_virtualization]
    assert len(amis_by_virtualization) >= 3, "Should have at least 3 paravirtual AMI's"

    amis_by_platform = ec2.describe_images(
        Filters=[{"Name": "platform", "Values": ["windows"]}]
    )["Images"]
    assert imageA_id in [ami["ImageId"] for ami in amis_by_platform]
    assert len(amis_by_platform) >= 25, "Should have at least 25 Windows images"

    amis_by_id = ec2.describe_images(
        Filters=[{"Name": "image-id", "Values": [imageA_id]}]
    )["Images"]
    assert [ami["ImageId"] for ami in amis_by_id] == [imageA_id]

    amis_by_state = ec2.describe_images(
        Filters=[{"Name": "state", "Values": ["available"]}]
    )["Images"]
    ami_ids_by_state = [ami["ImageId"] for ami in amis_by_state]
    assert imageA_id in ami_ids_by_state
    assert imageB.id in ami_ids_by_state
    assert len(amis_by_state) >= 40, "Should have at least 40 images available"

    amis_by_name = ec2.describe_images(
        Filters=[{"Name": "name", "Values": [imageA.name]}]
    )["Images"]
    assert [ami["ImageId"] for ami in amis_by_name] == [imageA.id]

    amis_by_public = ec2.describe_images(
        Filters=[{"Name": "is-public", "Values": ["true"]}]
    )["Images"]
    assert len(amis_by_public) >= 38, "Should have at least 38 public images"

    amis_by_nonpublic = ec2.describe_images(
        Filters=[{"Name": "is-public", "Values": ["false"]}]
    )["Images"]
    assert imageA.id in [ami["ImageId"] for ami in amis_by_nonpublic]

    amis_by_product_code = ec2.describe_images(
        Filters=[
            {"Name": "product-code", "Values": ["code123"]},
            {"Name": "product-code.type", "Values": ["marketplace"]},
        ]
    )["Images"]
    assert "ami-0b301ce3ce3475r4f" in [ami["ImageId"] for ami in amis_by_product_code]


@mock_aws
def test_ami_filtering_via_tag():
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
    assert [ami["ImageId"] for ami in amis_by_tagA] == [imageA_id]

    amis_by_tagB = ec2.describe_images(
        Filters=[{"Name": "tag:another key", "Values": [other_value]}]
    )["Images"]
    assert [ami["ImageId"] for ami in amis_by_tagB] == [imageB_id]


@mock_aws
def test_getting_missing_ami():
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.Image("ami-missing").load()
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIID.NotFound"


@mock_aws
def test_getting_malformed_ami():
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.Image("foo-missing").load()
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIID.Malformed"


@mock_aws
def test_ami_attribute_group_permissions():
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
    assert permissions == []

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
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the ModifyImageAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    image.modify_attribute(**ADD_GROUP_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    assert permissions == [{"Group": "all"}]
    image.reload()
    assert image.public is True

    # Add is idempotent
    image.modify_attribute(**ADD_GROUP_ARGS)

    # Remove 'all' group and confirm
    image.modify_attribute(**REMOVE_GROUP_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    assert permissions == []
    image.reload()
    assert image.public is False

    # Remove is idempotent
    image.modify_attribute(**REMOVE_GROUP_ARGS)


@mock_aws
def test_ami_attribute_user_permissions():
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
    assert permissions == []

    USER1 = "".join([f"{random.randint(0, 9)}" for _ in range(0, 12)])
    USER2 = "".join([f"{random.randint(0, 9)}" for _ in range(0, 12)])

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
    assert len(permissions) == 2
    assert {"UserId": USER1} in permissions
    assert {"UserId": USER2} in permissions
    image.reload()
    assert image.public is False

    # Add is idempotent
    image.modify_attribute(**ADD_USERS_ARGS)

    # Remove single user and confirm
    image.modify_attribute(**REMOVE_SINGLE_USER_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    assert permissions == [{"UserId": USER2}]
    image.reload()
    assert image.public is False

    # Remove multiple users and confirm
    image.modify_attribute(**REMOVE_USERS_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    assert permissions == []
    image.reload()
    assert image.public is False

    # Remove is idempotent
    image.modify_attribute(**REMOVE_USERS_ARGS)


@mock_aws
def test_ami_attribute_organizations():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance_id = reservation["Instances"][0]["InstanceId"]
    image_id = ec2.create_image(InstanceId=instance_id, Name="test-ami-A")["ImageId"]
    image = boto3.resource("ec2", "us-east-1").Image(image_id)
    arn = "someOrganizationArn"
    image.modify_attribute(
        Attribute="launchPermission",
        OperationType="add",
        OrganizationArns=[arn],
    )
    image.modify_attribute(
        Attribute="launchPermission",
        OperationType="add",
        OrganizationalUnitArns=["ou1"],
    )

    ec2.modify_image_attribute(
        Attribute="launchPermission",
        ImageId=image_id,
        LaunchPermission={
            "Add": [
                {"UserId": "111122223333"},
                {"UserId": "555566667777"},
                {"Group": "all"},
                {"OrganizationArn": "orgarn"},
                {"OrganizationalUnitArn": "ou2"},
            ]
        },
    )

    launch_permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    assert launch_permissions == [
        {"OrganizationArn": "someOrganizationArn"},
        {"OrganizationalUnitArn": "ou1"},
        {"UserId": "111122223333"},
        {"UserId": "555566667777"},
        {"Group": "all"},
        {"OrganizationArn": "orgarn"},
        {"OrganizationalUnitArn": "ou2"},
    ]


@mock_aws
def test_ami_describe_executable_users():
    conn = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", "us-east-1")
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    image_id = conn.create_image(InstanceId=instance_id, Name="TestImage")["ImageId"]

    USER1 = "".join([f"{random.randint(0, 9)}" for _ in range(0, 12)])

    ADD_USER_ARGS = {
        "ImageId": image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserIds": [USER1],
    }

    # Add users and get no images
    conn.modify_image_attribute(**ADD_USER_ARGS)

    attributes = conn.describe_image_attribute(
        ImageId=image_id, Attribute="launchPermission", DryRun=False
    )
    assert len(attributes["LaunchPermissions"]) == 1
    assert attributes["LaunchPermissions"][0]["UserId"] == USER1
    images = conn.describe_images(ExecutableUsers=[USER1])["Images"]
    assert image_id in [image["ImageId"] for image in images]


@mock_aws
def test_ami_describe_executable_users_negative():
    conn = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", "us-east-1")
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    image_id = conn.create_image(InstanceId=instance_id, Name="TestImage")["ImageId"]

    USER1 = "".join([f"{random.randint(0, 9)}" for _ in range(0, 12)])
    USER2 = "".join([f"{random.randint(0, 9)}" for _ in range(0, 12)])

    ADD_USER_ARGS = {
        "ImageId": image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserIds": [USER1],
    }

    # Add users and get no images
    conn.modify_image_attribute(**ADD_USER_ARGS)

    attributes = conn.describe_image_attribute(
        ImageId=image_id, Attribute="launchPermission", DryRun=False
    )
    assert len(attributes["LaunchPermissions"]) == 1
    assert attributes["LaunchPermissions"][0]["UserId"] == USER1
    images = conn.describe_images(ExecutableUsers=[USER2])["Images"]
    assert image_id not in [image["ImageId"] for image in images]


@mock_aws
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

    USER1 = "".join([f"{random.randint(0, 9)}" for _ in range(0, 12)])

    ADD_USER_ARGS = {
        "ImageId": image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserIds": [USER1],
    }

    # Add users and get no images
    conn.modify_image_attribute(**ADD_USER_ARGS)

    attributes = conn.describe_image_attribute(
        ImageId=image_id, Attribute="launchPermission", DryRun=False
    )
    assert len(attributes["LaunchPermissions"]) == 1
    assert attributes["LaunchPermissions"][0]["UserId"] == USER1
    images = conn.describe_images(
        ExecutableUsers=[USER1], Filters=[{"Name": "state", "Values": ["available"]}]
    )["Images"]
    assert image_id in [image["ImageId"] for image in images]


@mock_aws
def test_ami_describe_images_executable_user_public():
    conn = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", "us-east-1")
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    public_image_id = conn.create_image(InstanceId=instance_id, Name="PublicImage")[
        "ImageId"
    ]
    private_image_id = conn.create_image(InstanceId=instance_id, Name="PrivateImage")[
        "ImageId"
    ]

    USER1 = "".join([f"{random.randint(0, 9)}" for _ in range(0, 12)])
    USER2 = "".join([f"{random.randint(0, 9)}" for _ in range(0, 12)])

    SET_IMAGE_PUBLIC = {
        "ImageId": public_image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserGroups": ["all"],
    }
    conn.modify_image_attribute(**SET_IMAGE_PUBLIC)

    SET_IMAGE_PRIVATE = {
        "ImageId": private_image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserIds": [USER2],
    }
    conn.modify_image_attribute(**SET_IMAGE_PRIVATE)

    images = conn.describe_images(
        ExecutableUsers=[USER1],
    )["Images"]

    image_ids = [image["ImageId"] for image in images]
    assert public_image_id in image_ids
    assert private_image_id not in image_ids


@mock_aws
def test_ami_describe_images_executable_users_self():
    conn = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", "us-east-1")
    ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    response = conn.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
    image_id = conn.create_image(InstanceId=instance_id, Name="PublicImage")["ImageId"]

    SET_IMAGE_TO_SELF = {
        "ImageId": image_id,
        "Attribute": "launchPermission",
        "OperationType": "add",
        "UserIds": [ACCOUNT_ID],
    }
    conn.modify_image_attribute(**SET_IMAGE_TO_SELF)

    images = conn.describe_images(ExecutableUsers=["self"])["Images"]

    assert image_id in [image["ImageId"] for image in images]


@mock_aws
def test_ami_attribute_user_and_group_permissions():
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
    assert permissions == []

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
    assert len(permissions) == 3
    assert {"Group": "all"} in permissions
    assert {"UserId": "123456789022"} in permissions
    assert {"UserId": "123456789011"} in permissions
    image.reload()
    assert image.public is True

    # Remove and confirm
    image.modify_attribute(**REMOVE_ARGS)

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    assert permissions == []
    image.reload()
    assert image.public is False


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_filter_description():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    # https://github.com/getmoto/moto/issues/4460
    client = boto3.client("ec2", region_name="us-west-2")

    # Search for partial description
    resp = client.describe_images(
        Owners=["amazon"],
        Filters=[{"Name": "description", "Values": ["Amazon Linux AMI*"]}],
    )["Images"]
    assert len(resp) > 9

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
    assert len(resp) == 1


@mock_aws
def test_ami_attribute_error_cases():
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
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIAttributeItemValue"

    # Error: Add with user ID that isn't an integer.
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId=image_id,
            Attribute="launchPermission",
            OperationType="add",
            UserIds=["12345678901A"],
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIAttributeItemValue"

    # Error: Add with user ID that is > length 12.
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId=image_id,
            Attribute="launchPermission",
            OperationType="add",
            UserIds=["1234567890123"],
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIAttributeItemValue"

    # Error: Add with user ID that is < length 12.
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId=image_id,
            Attribute="launchPermission",
            OperationType="add",
            UserIds=["12345678901"],
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIAttributeItemValue"

    # Error: Add with one invalid user ID among other valid IDs, ensure no
    # partial changes.
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId=image_id,
            Attribute="launchPermission",
            OperationType="add",
            UserIds=["123456789011", "foo", "123456789022"],
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIAttributeItemValue"

    permissions = image.describe_attribute(Attribute="launchPermission")[
        "LaunchPermissions"
    ]
    assert permissions == []

    # Error: Add with invalid image ID
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId="ami-abcd1234",
            Attribute="launchPermission",
            OperationType="add",
            UserGroups=["all"],
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIID.NotFound"

    # Error: Remove with invalid image ID
    with pytest.raises(ClientError) as ex:
        image.modify_attribute(
            ImageId="ami-abcd1234",
            Attribute="launchPermission",
            OperationType="remove",
            UserGroups=["all"],
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidAMIID.NotFound"


@mock_aws
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


@mock_aws
def test_ami_registration():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    image_id = ec2.register_image(Name="test-register-image").get("ImageId", "")
    images = ec2.describe_images(ImageIds=[image_id]).get("Images", [])
    assert images[0]["Name"] == "test-register-image", "No image was registered."
    assert images[0]["RootDeviceName"] == "/dev/sda1", "Wrong root device name."
    assert images[0]["State"] == "available", "State should be available."


@mock_aws
def test_ami_filter_wildcard():
    ec2_resource = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")

    image_name = str(uuid4())[0:12]

    instance = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]
    instance.create_image(Name=image_name)

    # create an image with the same owner but will not match the filter
    instance.create_image(Name=str(uuid4())[0:6])

    my_images = ec2_client.describe_images(
        Owners=[ACCOUNT_ID],
        Filters=[{"Name": "name", "Values": [f"{image_name[0:8]}*"]}],
    )["Images"]
    assert len(my_images) == 1


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ami_filter_by_owner_id():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
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


@mock_aws
def test_ami_filter_by_self():
    ec2_resource = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")

    unique_name = str(uuid4())[0:6]

    images = ec2_client.describe_images(Owners=["self"])["Images"]
    image_names = [i["Name"] for i in images]
    assert unique_name not in image_names

    # Create a new image
    instance = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
    )[0]
    instance.create_image(Name=unique_name)

    images = ec2_client.describe_images(Owners=["self"])["Images"]
    image_names = [i["Name"] for i in images]
    assert unique_name in image_names


@mock_aws
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


@mock_aws
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
                {"Key": "OS_Version", "Value": "AWS Linux 2"},
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
    assert image["Tags"] == tag_specifications[0]["Tags"]

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
    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert (
        ex.value.response["Error"]["Message"]
        == "'invalid-resource-type' is not a valid taggable resource type for this operation."
    )


@mock_aws
def test_ami_filter_by_empty_tag():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    fake_images = []
    instance = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)[0]
    for i in range(10):
        image = client.create_image(
            InstanceId=instance.instance_id,
            Name=f"MyAMI{i}",
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


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ami_filter_by_ownerid():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    ec2_connection = boto3.client("ec2", region_name="us-east-1")

    images = ec2_connection.describe_images(
        Filters=[
            {"Name": "name", "Values": ["amzn-ami-*"]},
            {"Name": "owner-alias", "Values": ["amazon"]},
        ]
    )["Images"]
    assert len(images) > 0, "We should have at least 1 image created by amazon"


@mock_aws
def test_ami_filter_by_unknown_ownerid():
    ec2_connection = boto3.client("ec2", region_name="us-east-1")

    images = ec2_connection.describe_images(
        Filters=[{"Name": "owner-alias", "Values": ["unknown"]}]
    )["Images"]
    assert len(images) == 0


@mock_aws
def test_describe_images_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_images(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DescribeImages operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_aws
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
    assert err["Code"] == "InvalidSnapshot.InUse"
    assert (
        err["Message"] == f"The snapshot {snapshot_id} is currently in use by {ami_id}"
    )

    # Deregister the Ami first
    ec2_client.deregister_image(ImageId=ami_id)

    # Now we can delete the snapshot without problems
    ec2_client.delete_snapshot(SnapshotId=snapshot_id)

    with pytest.raises(ClientError) as exc:
        ec2_client.describe_snapshots(SnapshotIds=[snapshot_id])
    assert exc.value.response["Error"]["Code"] == "InvalidSnapshot.NotFound"


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ami_describe_image_attribute_product_codes():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    # Setup
    conn = boto3.client("ec2", region_name="us-east-1")

    # test ami loaded from moto/ec2/resources/ami.json
    test_image = conn.describe_images(
        Filters=[{"Name": "name", "Values": ["product_codes_test"]}]
    )
    image_id = test_image["Images"][0]["ImageId"]
    expected_codes = [
        {"ProductCodeId": "code123", "ProductCodeType": "marketplace"},
        {"ProductCodeId": "code456", "ProductCodeType": "marketplace"},
    ]
    # Execute
    attributes = conn.describe_image_attribute(
        ImageId=image_id, Attribute="productCodes", DryRun=False
    )

    # Verify
    assert "ProductCodes" in attributes
    assert len(attributes["ProductCodes"]) == 2
    assert attributes["ProductCodes"] == expected_codes


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ami_describe_image_attribute():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    # Setup
    conn = boto3.client("ec2", region_name="us-east-1")

    # test ami loaded from moto/ec2/resources/ami.json
    test_image = conn.describe_images(
        Filters=[{"Name": "name", "Values": ["product_codes_test"]}]
    )
    image_id = test_image["Images"][0]["ImageId"]

    # Execute
    description = conn.describe_image_attribute(
        ImageId=image_id, Attribute="description", DryRun=False
    )
    boot_mode = conn.describe_image_attribute(
        ImageId=image_id, Attribute="bootMode", DryRun=False
    )
    sriov = conn.describe_image_attribute(
        ImageId=image_id, Attribute="sriovNetSupport", DryRun=False
    )

    # Verify
    assert "Description" in description
    assert description["Description"]["Value"] == "Test ami for product codes"
    assert "BootMode" in boot_mode
    assert boot_mode["BootMode"]["Value"] == "uefi"
    assert "SriovNetSupport" in sriov
    assert sriov["SriovNetSupport"]["Value"] == "simple"


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ami_describe_image_attribute_block_device_fail():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    # Setup
    conn = boto3.client("ec2", region_name="us-east-1")
    test_image = conn.describe_images()
    image_id = test_image["Images"][0]["ImageId"]

    # Execute
    with pytest.raises(ClientError) as e:
        conn.describe_image_attribute(
            ImageId=image_id, Attribute="blockDeviceMapping", DryRun=False
        )

    # Verify
    assert e.value.response["Error"]["Code"] == "AuthFailure"
    assert (
        e.value.response["Error"]["Message"]
        == "Unauthorized attempt to access restricted resource"
    )


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ami_describe_image_attribute_invalid_param():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    # Setup
    conn = boto3.client("ec2", region_name="us-east-1")
    test_image = conn.describe_images()
    image_id = test_image["Images"][0]["ImageId"]

    # Execute
    with pytest.raises(ClientError) as e:
        conn.describe_image_attribute(
            ImageId=image_id, Attribute="invalid", DryRun=False
        )

    # Verify
    assert e.value.response["Error"]["Code"] == "InvalidRequest"
    assert e.value.response["Error"]["Message"] == "The request received was invalid"
