import os
from unittest import SkipTest, mock
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as OWNER_ID
from moto.ec2.models.elastic_block_store import IOPS_REQUIRED_VOLUME_TYPES
from tests import EXAMPLE_AMI_ID


@mock_aws
def test_create_and_delete_volume():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")

    all_volumes = client.describe_volumes()["Volumes"]

    current_volume = [item for item in all_volumes if item["VolumeId"] == volume.id]
    assert len(current_volume) == 1
    assert current_volume[0]["Size"] == 80
    assert current_volume[0]["AvailabilityZone"] == "us-east-1a"
    assert current_volume[0]["Encrypted"] is False

    with pytest.raises(ClientError) as ex:
        volume.delete(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DeleteVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    volume.delete()

    all_volumes = client.describe_volumes()["Volumes"]
    my_volume = [item for item in all_volumes if item["VolumeId"] == volume.id]
    assert len(my_volume) == 0

    # Deleting something that was already deleted should throw an error
    with pytest.raises(ClientError) as ex:
        volume.delete()
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidVolume.NotFound"


@mock_aws
def test_modify_volumes():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    old_size = 80
    new_size = 160
    new_type = "io2"

    volume_id = ec2.create_volume(Size=old_size, AvailabilityZone="us-east-1a").id

    # Ensure no modification records exist
    modifications = client.describe_volumes_modifications()
    assert len(modifications["VolumesModifications"]) == 0

    # Ensure volume size can be modified
    response = client.modify_volume(VolumeId=volume_id, Size=new_size)
    assert response["VolumeModification"]["OriginalSize"] == old_size
    assert response["VolumeModification"]["TargetSize"] == new_size
    assert (
        client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0]["Size"] == new_size
    )

    # Ensure volume type can be modified
    response = client.modify_volume(VolumeId=volume_id, VolumeType=new_type)
    assert response["VolumeModification"]["OriginalVolumeType"] == "gp2"
    assert response["VolumeModification"]["TargetVolumeType"] == new_type
    assert (
        client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0]["VolumeType"]
        == new_type
    )

    # Ensure volume modifications are tracked
    modifications = client.describe_volumes_modifications()
    assert len(modifications["VolumesModifications"]) == 2


@mock_aws
def test_delete_attached_volume():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

    # create an instance
    instance = reservation["Instances"][0]
    # create a volume
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")
    # attach volume to instance
    volume.attach_to_instance(InstanceId=instance["InstanceId"], Device="/dev/sdh")

    assert volume.state == "in-use"
    assert len(volume.attachments) == 1
    assert volume.attachments[0]["InstanceId"] == instance["InstanceId"]
    assert volume.attachments[0]["State"] == "attached"

    # attempt to delete volume
    # assert raises VolumeInUseError
    with pytest.raises(ClientError) as ex:
        volume.delete()
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Code"] == "VolumeInUse"
    assert (
        ex.value.response["Error"]["Message"]
        == f"Volume {volume.id} is currently attached to {instance['InstanceId']}"
    )

    volume.detach_from_instance(InstanceId=instance["InstanceId"])

    assert volume.state == "available"

    volume.delete()

    all_volumes = client.describe_volumes()["Volumes"]
    assert volume.id not in [v["VolumeId"] for v in all_volumes]


@mock_aws
def test_create_encrypted_volume_dryrun():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        ec2.create_volume(Size=80, AvailabilityZone="us-east-1a", DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateVolume operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_aws
def test_create_encrypted_volume():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a", Encrypted=True)

    all_volumes = client.describe_volumes(VolumeIds=[volume.id])["Volumes"]
    assert all_volumes[0]["Encrypted"] is True


@mock_aws
def test_filter_volume_by_id():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume1 = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")
    volume2 = ec2.create_volume(Size=36, AvailabilityZone="us-east-1b")
    volume3 = ec2.create_volume(Size=20, AvailabilityZone="us-east-1c")

    vol3 = client.describe_volumes(VolumeIds=[volume3.id])["Volumes"]
    assert len(vol3) == 1
    assert vol3[0]["Size"] == 20
    assert vol3[0]["AvailabilityZone"] == "us-east-1c"

    vol12 = client.describe_volumes(VolumeIds=[volume1.id, volume2.id])["Volumes"]
    assert len(vol12) == 2

    with pytest.raises(ClientError) as ex:
        client.describe_volumes(VolumeIds=["vol-does_not_exist"])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Code"] == "InvalidVolume.NotFound"


@mock_aws
def test_volume_filters():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    volume1 = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a", Encrypted=True)
    volume2 = ec2.create_volume(Size=36, AvailabilityZone="us-east-1b", Encrypted=False)
    volume3 = ec2.create_volume(Size=20, AvailabilityZone="us-east-1c", Encrypted=True)

    snapshot = volume3.create_snapshot(Description="testsnap")
    volume4 = ec2.create_volume(
        Size=25, AvailabilityZone="us-east-1a", SnapshotId=snapshot.id
    )

    tag_key1 = str(uuid4())[0:6]
    tag_val1 = str(uuid4())
    ec2.create_tags(Resources=[volume1.id], Tags=[{"Key": tag_key1, "Value": tag_val1}])
    ec2.create_tags(
        Resources=[volume2.id], Tags=[{"Key": "testkey2", "Value": "testvalue2"}]
    )

    volume1.reload()
    volume2.reload()
    volume3.reload()
    volume4.reload()

    instance = ec2.Instance(instance["InstanceId"])
    instance.reload()

    block_mapping = [
        m for m in instance.block_device_mappings if m["DeviceName"] == "/dev/sda1"
    ][0]
    block_volume = block_mapping["Ebs"]["VolumeId"]

    def verify_filter(name, value, expected=None, not_expected=None):
        multiple_results = not_expected is not None
        expected = expected or block_volume
        expected = expected if isinstance(expected, list) else [expected]
        volumes = client.describe_volumes(Filters=[{"Name": name, "Values": [value]}])[
            "Volumes"
        ]
        actual = [vol["VolumeId"] for vol in volumes]
        if multiple_results:
            for e in expected:
                assert e in actual
            for e in not_expected:
                assert e not in actual
        else:
            assert set(actual) == set(expected)

    # We should probably make this less strict, i.e. figure out which formats AWS expects/approves of
    attach_time = block_mapping["Ebs"]["AttachTime"].strftime("%Y-%m-%dT%H:%M:%S.000Z")
    verify_filter(
        "attachment.attach-time",
        attach_time,
        not_expected=[volume1.id, volume2.id, volume3.id, volume4.id],
    )
    verify_filter(
        "attachment.device",
        "/dev/sda1",
        not_expected=[volume1.id, volume2.id, volume3.id, volume4.id],
    )
    verify_filter("attachment.instance-id", instance.id)
    verify_filter(
        "attachment.status",
        "attached",
        not_expected=[volume1.id, volume2.id, volume3.id, volume4.id],
    )
    verify_filter(
        "size",
        str(volume2.size),
        expected=volume2.id,
        not_expected=[volume1.id, volume3.id, volume4.id],
    )
    verify_filter(
        "snapshot-id",
        snapshot.id,
        expected=volume4.id,
        not_expected=[volume1.id, volume2.id, volume3.id],
    )
    verify_filter(
        "status",
        "in-use",
        not_expected=[volume1.id, volume2.id, volume3.id, volume4.id],
    )
    verify_filter(
        "volume-id",
        volume1.id,
        expected=volume1.id,
        not_expected=[volume2.id, volume3.id, volume4.id],
    )
    verify_filter("tag-key", tag_key1, expected=volume1.id)
    verify_filter("tag-value", tag_val1, expected=volume1.id)
    verify_filter(f"tag:{tag_key1}", tag_val1, expected=volume1.id)
    verify_filter(
        "encrypted",
        "false",
        expected=[block_volume, volume2.id],
        not_expected=[volume1.id, volume3.id, volume4.id],
    )
    verify_filter(
        "encrypted",
        "true",
        expected=[volume1.id, volume3.id, volume4.id],
        not_expected=[block_volume, volume2.id],
    )
    verify_filter(
        "availability-zone",
        "us-east-1b",
        expected=volume2.id,
        not_expected=[volume1.id, volume3.id, volume4.id],
    )
    #
    create_time = volume4.create_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    volumes_by_attach_device = client.describe_volumes(
        Filters=[{"Name": "create-time", "Values": [create_time]}]
    )["Volumes"]
    assert volume4.id in [vol["VolumeId"] for vol in volumes_by_attach_device]


@mock_aws
def test_volume_attach_and_detach():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    volumes = client.describe_volumes(
        Filters=[{"Name": "attachment.instance-id", "Values": [instance["InstanceId"]]}]
    )["Volumes"]
    assert len(volumes) == 1
    assert volumes[0]["AvailabilityZone"] == "us-east-1a"

    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")

    volume.reload()
    assert volume.state == "available"

    with pytest.raises(ClientError) as ex:
        volume.attach_to_instance(
            InstanceId=instance["InstanceId"], Device="/dev/sdh", DryRun=True
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the AttachVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    volume.attach_to_instance(InstanceId=instance["InstanceId"], Device="/dev/sdh")

    assert volume.state == "in-use"
    assert volume.attachments[0]["State"] == "attached"
    assert volume.attachments[0]["InstanceId"] == instance["InstanceId"]

    with pytest.raises(ClientError) as ex:
        volume.detach_from_instance(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DetachVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    volume.detach_from_instance(InstanceId=instance["InstanceId"])

    assert volume.state == "available"

    with pytest.raises(ClientError) as ex1:
        volume.attach_to_instance(InstanceId="i-1234abcd", Device="/dev/sdh")
    assert ex1.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex1.value.response["Error"]["Code"] == "InvalidInstanceID.NotFound"

    with pytest.raises(ClientError) as ex2:
        client.detach_volume(
            VolumeId=volume.id, InstanceId=instance["InstanceId"], Device="/dev/sdh"
        )
    assert ex2.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex2.value.response["Error"]["Code"] == "InvalidAttachment.NotFound"

    with pytest.raises(ClientError) as ex3:
        client.detach_volume(
            VolumeId=volume.id, InstanceId="i-1234abcd", Device="/dev/sdh"
        )
    assert ex3.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex3.value.response["Error"]["Code"] == "InvalidInstanceID.NotFound"


@mock_aws
def test_create_snapshot():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")

    with pytest.raises(ClientError) as ex:
        volume.create_snapshot(Description="a dryrun snapshot", DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateSnapshot operation: Request would have succeeded, but DryRun flag is set"
    )

    snapshot = volume.create_snapshot(Description="a test snapshot")
    snapshot.reload()
    assert snapshot.state == "completed"

    snapshots = [
        snap
        for snap in client.describe_snapshots()["Snapshots"]
        if snap["SnapshotId"] == snapshot.id
    ]
    assert len(snapshots) == 1
    assert snapshots[0]["Description"] == "a test snapshot"
    assert snapshots[0]["StartTime"] is not None
    assert snapshots[0]["Encrypted"] is False

    # Create snapshot without description
    snapshot = volume.create_snapshot()
    current_snapshots = client.describe_snapshots()["Snapshots"]
    assert snapshot.id in [s["SnapshotId"] for s in current_snapshots]

    snapshot.delete()
    current_snapshots = client.describe_snapshots()["Snapshots"]
    assert snapshot.id not in [s["SnapshotId"] for s in current_snapshots]

    # Deleting something that was already deleted should throw an error
    with pytest.raises(ClientError) as ex:
        snapshot.delete()
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Code"] == "InvalidSnapshot.NotFound"


@mock_aws
@pytest.mark.parametrize("encrypted", [True, False])
def test_create_encrypted_snapshot(encrypted):
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(
        Size=80, AvailabilityZone="us-east-1a", Encrypted=encrypted
    )
    snapshot = volume.create_snapshot(Description="a test snapshot")
    assert snapshot.encrypted == encrypted
    snapshot.reload()
    assert snapshot.state == "completed"

    snapshots = [
        snap
        for snap in client.describe_snapshots()["Snapshots"]
        if snap["SnapshotId"] == snapshot.id
    ]
    assert len(snapshots) == 1
    assert snapshots[0]["Description"] == "a test snapshot"
    assert snapshots[0]["StartTime"] is not None
    assert snapshots[0]["Encrypted"] == encrypted


@mock_aws
def test_filter_snapshot_by_id():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume1 = ec2.create_volume(Size=36, AvailabilityZone="us-east-1a")
    snap1 = volume1.create_snapshot(Description="a test snapshot 1")
    volume2 = ec2.create_volume(Size=42, AvailabilityZone="us-east-1a")
    snap2 = volume2.create_snapshot(Description="a test snapshot 2")
    volume3 = ec2.create_volume(Size=84, AvailabilityZone="us-east-1a")
    snap3 = volume3.create_snapshot(Description="a test snapshot 3")
    snapshots1 = client.describe_snapshots(SnapshotIds=[snap1.id])["Snapshots"]
    assert len(snapshots1) == 1
    assert snapshots1[0]["VolumeId"] == volume1.id
    snapshots2 = client.describe_snapshots(SnapshotIds=[snap2.id, snap3.id])[
        "Snapshots"
    ]
    assert len(snapshots2) == 2
    for s in snapshots2:
        assert s["StartTime"] is not None
        assert s["VolumeId"] in [volume2.id, volume3.id]

    with pytest.raises(ClientError) as ex:
        client.describe_snapshots(SnapshotIds=["snap-does_not_exist"])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidSnapshot.NotFound"


@mock_aws
def test_snapshot_filters():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume1 = ec2.create_volume(Size=20, AvailabilityZone="us-east-1a", Encrypted=False)
    volume2 = ec2.create_volume(Size=25, AvailabilityZone="us-east-1a", Encrypted=True)

    snapshot1_desc = str(uuid4())

    snapshot1 = volume1.create_snapshot(Description=snapshot1_desc)
    snapshot2 = volume1.create_snapshot(Description="testsnapshot2")
    snapshot3 = volume2.create_snapshot(Description="testsnapshot3")

    key_name_1 = str(uuid4())[0:6]
    key_value_1 = str(uuid4())[0:6]
    key_name_2 = str(uuid4())[0:6]
    key_value_2 = str(uuid4())[0:6]
    ec2.create_tags(
        Resources=[snapshot1.id], Tags=[{"Key": key_name_1, "Value": key_value_1}]
    )
    ec2.create_tags(
        Resources=[snapshot2.id], Tags=[{"Key": key_name_2, "Value": key_value_2}]
    )

    def verify_filter(name, value, expected, others=False):
        expected = expected if isinstance(expected, list) else [expected]
        snapshots = client.describe_snapshots(
            Filters=[{"Name": name, "Values": [value]}]
        )["Snapshots"]
        if others:
            actual = set([s["SnapshotId"] for s in snapshots])
            for e in expected:
                assert e in actual
        else:
            assert set([s["SnapshotId"] for s in snapshots]) == set(expected)

    verify_filter("description", snapshot1_desc, expected=snapshot1.id)
    verify_filter("snapshot-id", snapshot1.id, expected=snapshot1.id)
    verify_filter("volume-id", volume1.id, expected=[snapshot1.id, snapshot2.id])
    verify_filter(
        "volume-size",
        str(volume1.size),
        expected=[snapshot1.id, snapshot2.id],
        others=True,
    )
    verify_filter("tag-key", key_name_1, expected=snapshot1.id)
    verify_filter("tag-value", key_value_1, expected=snapshot1.id)
    verify_filter(f"tag:{key_name_2}", key_value_2, expected=snapshot2.id)
    verify_filter("encrypted", "true", expected=snapshot3.id, others=True)
    verify_filter(
        "owner-id",
        OWNER_ID,
        expected=[snapshot1.id, snapshot2.id, snapshot3.id],
        others=True,
    )
    #
    # We should probably make this less strict, i.e. figure out which formats AWS expects/approves of
    start_time = snapshot1.start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    snapshots = client.describe_snapshots(
        Filters=[{"Name": "start-time", "Values": [start_time]}]
    )["Snapshots"]
    assert snapshot1.id in [s["SnapshotId"] for s in snapshots]
    snapshots = client.describe_snapshots(
        Filters=[{"Name": "status", "Values": ["completed"]}]
    )["Snapshots"]
    assert snapshot1.id in [s["SnapshotId"] for s in snapshots]
    assert snapshot2.id in [s["SnapshotId"] for s in snapshots]
    assert snapshot3.id in [s["SnapshotId"] for s in snapshots]


@mock_aws
def test_modify_snapshot_attribute():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    response = ec2_client.create_volume(Size=80, AvailabilityZone="us-east-1a")
    volume = boto3.resource("ec2", region_name="us-east-1").Volume(response["VolumeId"])
    snapshot = volume.create_snapshot()

    # Baseline
    attributes = ec2_client.describe_snapshot_attribute(
        SnapshotId=snapshot.id, Attribute="createVolumePermission"
    )
    assert not attributes[
        "CreateVolumePermissions"
    ], "Snapshot should have no permissions."

    ADD_GROUP_ARGS = {
        "SnapshotId": snapshot.id,
        "Attribute": "createVolumePermission",
        "OperationType": "add",
        "GroupNames": ["all"],
    }

    REMOVE_GROUP_ARGS = {
        "SnapshotId": snapshot.id,
        "Attribute": "createVolumePermission",
        "OperationType": "remove",
        "GroupNames": ["all"],
    }

    # Add 'all' group and confirm
    with pytest.raises(ClientError) as cm:
        ec2_client.modify_snapshot_attribute(**dict(ADD_GROUP_ARGS, **{"DryRun": True}))

    assert cm.value.response["Error"]["Code"] == "DryRunOperation"
    assert cm.value.response["ResponseMetadata"]["RequestId"] is not None
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412

    ec2_client.modify_snapshot_attribute(**ADD_GROUP_ARGS)

    attributes = ec2_client.describe_snapshot_attribute(
        SnapshotId=snapshot.id, Attribute="createVolumePermission"
    )
    assert attributes["CreateVolumePermissions"] == [
        {"Group": "all"}
    ], "This snapshot should have public group permissions."

    # Add is idempotent
    ec2_client.modify_snapshot_attribute(**ADD_GROUP_ARGS)
    assert attributes["CreateVolumePermissions"] == [
        {"Group": "all"}
    ], "This snapshot should have public group permissions."

    # Remove 'all' group and confirm
    with pytest.raises(ClientError):
        ec2_client.modify_snapshot_attribute(
            **dict(REMOVE_GROUP_ARGS, **{"DryRun": True})
        )
    assert cm.value.response["Error"]["Code"] == "DryRunOperation"
    assert cm.value.response["ResponseMetadata"]["RequestId"] is not None
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412

    ec2_client.modify_snapshot_attribute(**REMOVE_GROUP_ARGS)

    attributes = ec2_client.describe_snapshot_attribute(
        SnapshotId=snapshot.id, Attribute="createVolumePermission"
    )
    assert not attributes[
        "CreateVolumePermissions"
    ], "This snapshot should have no permissions."

    # Remove is idempotent
    ec2_client.modify_snapshot_attribute(**REMOVE_GROUP_ARGS)
    assert not attributes[
        "CreateVolumePermissions"
    ], "This snapshot should have no permissions."

    # Error: Add with group != 'all'
    with pytest.raises(ClientError) as cm:
        ec2_client.modify_snapshot_attribute(
            SnapshotId=snapshot.id,
            Attribute="createVolumePermission",
            OperationType="add",
            GroupNames=["everyone"],
        )
    assert cm.value.response["Error"]["Code"] == "InvalidAMIAttributeItemValue"
    assert cm.value.response["ResponseMetadata"]["RequestId"] is not None
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Error: Add with invalid snapshot ID
    with pytest.raises(ClientError) as cm:
        ec2_client.modify_snapshot_attribute(
            SnapshotId="snapshot-abcd1234",
            Attribute="createVolumePermission",
            OperationType="add",
            GroupNames=["all"],
        )
    assert cm.value.response["Error"]["Code"] == "InvalidSnapshot.NotFound"
    assert cm.value.response["ResponseMetadata"]["RequestId"] is not None
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Error: Remove with invalid snapshot ID
    with pytest.raises(ClientError) as cm:
        ec2_client.modify_snapshot_attribute(
            SnapshotId="snapshot-abcd1234",
            Attribute="createVolumePermission",
            OperationType="remove",
            GroupNames=["all"],
        )
    assert cm.value.response["Error"]["Code"] == "InvalidSnapshot.NotFound"
    assert cm.value.response["ResponseMetadata"]["RequestId"] is not None
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Test adding user id
    ec2_client.modify_snapshot_attribute(
        SnapshotId=snapshot.id,
        Attribute="createVolumePermission",
        OperationType="add",
        UserIds=["1234567891"],
    )

    attributes = ec2_client.describe_snapshot_attribute(
        SnapshotId=snapshot.id, Attribute="createVolumePermission"
    )
    assert len(attributes["CreateVolumePermissions"]) == 1

    # Test adding user id again along with additional.
    ec2_client.modify_snapshot_attribute(
        SnapshotId=snapshot.id,
        Attribute="createVolumePermission",
        OperationType="add",
        UserIds=["1234567891", "2345678912"],
    )

    attributes = ec2_client.describe_snapshot_attribute(
        SnapshotId=snapshot.id, Attribute="createVolumePermission"
    )
    assert len(attributes["CreateVolumePermissions"]) == 2

    # Test removing both user IDs.
    ec2_client.modify_snapshot_attribute(
        SnapshotId=snapshot.id,
        Attribute="createVolumePermission",
        OperationType="remove",
        UserIds=["1234567891", "2345678912"],
    )

    attributes = ec2_client.describe_snapshot_attribute(
        SnapshotId=snapshot.id, Attribute="createVolumePermission"
    )
    assert len(attributes["CreateVolumePermissions"]) == 0

    # Idempotency when removing users.
    ec2_client.modify_snapshot_attribute(
        SnapshotId=snapshot.id,
        Attribute="createVolumePermission",
        OperationType="remove",
        UserIds=["1234567891"],
    )

    attributes = ec2_client.describe_snapshot_attribute(
        SnapshotId=snapshot.id, Attribute="createVolumePermission"
    )
    assert len(attributes["CreateVolumePermissions"]) == 0


@mock_aws
@pytest.mark.parametrize("encrypted", [True, False])
def test_create_volume_from_snapshot(encrypted):
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(
        Size=80, AvailabilityZone="us-east-1a", Encrypted=encrypted
    )
    snapshot = volume.create_snapshot(Description="a test snapshot")
    snapshot.reload()
    assert snapshot.state == "completed"

    new_volume = client.create_volume(
        SnapshotId=snapshot.id, AvailabilityZone="us-east-1a"
    )
    assert new_volume["Size"] == 80
    assert new_volume["SnapshotId"] == snapshot.id
    assert new_volume["Encrypted"] == encrypted


@mock_aws
def test_modify_attribute_blockDeviceMapping():
    """
    Reproduces the missing feature explained at [0], where we want to mock a
    call to modify an instance attribute of type: blockDeviceMapping.

    [0] https://github.com/getmoto/moto/issues/160
    """
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = ec2.Instance(reservation["Instances"][0]["InstanceId"])

    with pytest.raises(ClientError) as ex:
        instance.modify_attribute(
            BlockDeviceMappings=[
                {"DeviceName": "/dev/sda1", "Ebs": {"DeleteOnTermination": True}}
            ],
            DryRun=True,
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the ModifyInstanceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(
        BlockDeviceMappings=[
            {"DeviceName": "/dev/sda1", "Ebs": {"DeleteOnTermination": True}}
        ]
    )

    instance.reload()
    mapping = instance.block_device_mappings[0]
    assert mapping["DeviceName"] == "/dev/sda1"
    assert mapping["Ebs"]["DeleteOnTermination"] is True


@mock_aws
def test_volume_tag_escaping():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(Size=10, AvailabilityZone="us-east-1a")
    snapshot = client.create_snapshot(VolumeId=volume.id, Description="Desc")
    snapshot = ec2.Snapshot(snapshot["SnapshotId"])

    with pytest.raises(ClientError) as ex:
        snapshot.create_tags(Tags=[{"Key": "key", "Value": "</closed>"}], DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    assert len(snapshot.tags) == 0

    snapshot.create_tags(Tags=[{"Key": "key", "Value": "</closed>"}])

    assert snapshot.tags == [{"Key": "key", "Value": "</closed>"}]


@mock_aws
def test_volume_property_hidden_when_no_tags_exist():
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    volume_response = ec2_client.create_volume(Size=10, AvailabilityZone="us-east-1a")

    assert volume_response.get("Tags") is None


@mock_aws
def test_copy_snapshot():
    ec2_client = boto3.client("ec2", region_name="eu-west-1")
    dest_ec2_client = boto3.client("ec2", region_name="eu-west-2")

    volume_response = ec2_client.create_volume(AvailabilityZone="eu-west-1a", Size=10)
    tag_spec = [
        {"ResourceType": "snapshot", "Tags": [{"Key": "key", "Value": "value"}]}
    ]

    create_snapshot_response = ec2_client.create_snapshot(
        VolumeId=volume_response["VolumeId"], TagSpecifications=tag_spec
    )

    copy_snapshot_response = dest_ec2_client.copy_snapshot(
        SourceSnapshotId=create_snapshot_response["SnapshotId"],
        SourceRegion="eu-west-1",
        TagSpecifications=tag_spec,
    )
    assert copy_snapshot_response["Tags"] == tag_spec[0]["Tags"]

    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    dest_ec2 = boto3.resource("ec2", region_name="eu-west-2")

    source = ec2.Snapshot(create_snapshot_response["SnapshotId"])
    dest = dest_ec2.Snapshot(copy_snapshot_response["SnapshotId"])

    attribs = [
        "data_encryption_key_id",
        "encrypted",
        "kms_key_id",
        "owner_alias",
        "owner_id",
        "progress",
        "state",
        "state_message",
        "tags",
        "volume_id",
        "volume_size",
    ]

    for attrib in attribs:
        assert getattr(source, attrib) == getattr(dest, attrib)

    # Copy from non-existent source ID.
    with pytest.raises(ClientError) as cm:
        ec2_client.create_snapshot(VolumeId="vol-abcd1234")
    assert cm.value.response["Error"]["Code"] == "InvalidVolume.NotFound"
    assert (
        cm.value.response["Error"]["Message"]
        == "The volume 'vol-abcd1234' does not exist."
    )
    assert cm.value.response["ResponseMetadata"]["RequestId"] is not None
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Copy from non-existent source region.
    with pytest.raises(ClientError) as cm:
        dest_ec2_client.copy_snapshot(
            SourceSnapshotId=create_snapshot_response["SnapshotId"],
            SourceRegion="eu-west-2",
        )
    assert cm.value.response["Error"]["Code"] == "InvalidSnapshot.NotFound"
    assert cm.value.response["Error"]["Message"] is None
    assert cm.value.response["ResponseMetadata"]["RequestId"] is not None
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_search_for_many_snapshots():
    ec2_client = boto3.client("ec2", region_name="eu-west-1")

    volume_response = ec2_client.create_volume(AvailabilityZone="eu-west-1a", Size=10)

    snapshot_ids = []
    for _ in range(1, 20):
        create_snapshot_response = ec2_client.create_snapshot(
            VolumeId=volume_response["VolumeId"]
        )
        snapshot_ids.append(create_snapshot_response["SnapshotId"])

    snapshots_response = ec2_client.describe_snapshots(SnapshotIds=snapshot_ids)

    assert len(snapshots_response["Snapshots"]) == len(snapshot_ids)


@mock_aws
def test_create_unencrypted_volume_with_kms_key_fails():
    resource = boto3.resource("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        resource.create_volume(
            AvailabilityZone="us-east-1a", Encrypted=False, KmsKeyId="key", Size=10
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameterDependency"
    assert "KmsKeyId" in ex.value.response["Error"]["Message"]


@mock_aws
def test_create_encrypted_volume_without_kms_key_should_use_default_key():
    kms = boto3.client("kms", region_name="us-east-1")

    # Creating an encrypted volume should create (and use) the default key.
    resource = boto3.resource("ec2", region_name="us-east-1")
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=True, Size=10
    )
    default_ebs_key_arn = kms.describe_key(KeyId="alias/aws/ebs")["KeyMetadata"]["Arn"]
    assert volume.kms_key_id == default_ebs_key_arn
    assert volume.encrypted is True
    # Subsequent encrypted volumes should use the now-created default key.
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=True, Size=10
    )
    assert volume.kms_key_id == default_ebs_key_arn
    assert volume.encrypted is True


@mock_aws
def test_create_volume_with_kms_key():
    resource = boto3.resource("ec2", region_name="us-east-1")
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=True, KmsKeyId="key", Size=10
    )
    assert volume.kms_key_id == "key"
    assert volume.encrypted is True


@mock_aws
def test_kms_key_id_property_hidden_when_volume_not_encrypted():
    client = boto3.client("ec2", region_name="us-east-1")
    resp = client.create_volume(AvailabilityZone="us-east-1a", Encrypted=False, Size=10)
    assert resp["Encrypted"] is False
    assert "KmsKeyId" not in resp
    resp = client.describe_volumes(VolumeIds=[resp["VolumeId"]])
    assert resp["Volumes"][0]["Encrypted"] is False
    assert "KmsKeyId" not in resp["Volumes"][0]
    resource = boto3.resource("ec2", region_name="us-east-1")
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=False, Size=10
    )
    assert volume.encrypted is False
    assert volume.kms_key_id is None


@mock_aws
def test_create_volume_with_standard_type():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume = ec2.create_volume(AvailabilityZone="us-east-1a", Size=100)
    assert volume["VolumeType"] == "gp2"

    volume = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])["Volumes"][0]
    assert volume["VolumeType"] == "gp2"


@pytest.mark.parametrize("volume_type", ["gp2", "gp3", "io1", "io2", "standard"])
@mock_aws
def test_create_volume_with_non_standard_type(volume_type):
    ec2 = boto3.client("ec2", region_name="us-east-1")
    if volume_type in IOPS_REQUIRED_VOLUME_TYPES:
        volume = ec2.create_volume(
            AvailabilityZone="us-east-1a", Size=100, Iops=3000, VolumeType=volume_type
        )
    else:
        volume = ec2.create_volume(
            AvailabilityZone="us-east-1a", Size=100, VolumeType=volume_type
        )
    assert volume["VolumeType"] == volume_type

    volume = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])["Volumes"][0]
    assert volume["VolumeType"] == volume_type


@mock_aws
def test_create_snapshots_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_snapshots(
            InstanceSpecification={"InstanceId": "asf"}, DryRun=True
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateSnapshots operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_aws
def test_create_snapshots_with_tagspecification():
    client = boto3.client("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    resp = client.create_snapshots(
        Description="my tagged snapshots",
        InstanceSpecification={"InstanceId": instance["InstanceId"]},
        TagSpecifications=[
            {
                "ResourceType": "snapshot",
                "Tags": [
                    {"Key": "key1", "Value": "val1"},
                    {"Key": "key2", "Value": "val2"},
                ],
            }
        ],
    )
    snapshots = resp["Snapshots"]

    assert len(snapshots) == 1
    assert snapshots[0]["Description"] == "my tagged snapshots"
    assert snapshots[0]["Tags"] == [
        {"Key": "key1", "Value": "val1"},
        {"Key": "key2", "Value": "val2"},
    ]


@mock_aws
def test_create_snapshots_single_volume():
    client = boto3.client("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    instance = client.describe_instances(InstanceIds=[instance["InstanceId"]])[
        "Reservations"
    ][0]["Instances"][0]
    boot_volume = instance["BlockDeviceMappings"][0]["Ebs"]

    snapshots = client.create_snapshots(
        InstanceSpecification={"InstanceId": instance["InstanceId"]}
    )["Snapshots"]

    assert len(snapshots) == 1
    assert snapshots[0]["Encrypted"] is False
    assert snapshots[0]["VolumeId"] == boot_volume["VolumeId"]
    assert snapshots[0]["VolumeSize"] == 8
    assert "SnapshotId" in snapshots[0]
    assert snapshots[0]["Description"] == ""
    assert snapshots[0]["Tags"] == []


@mock_aws
def test_create_snapshots_multiple_volumes():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    instance = client.describe_instances(InstanceIds=[instance["InstanceId"]])[
        "Reservations"
    ][0]["Instances"][0]
    boot_volume = instance["BlockDeviceMappings"][0]["Ebs"]

    volume1 = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")
    volume1.attach_to_instance(InstanceId=instance["InstanceId"], Device="/dev/sdh")

    volume2 = ec2.create_volume(Size=100, AvailabilityZone="us-east-1b")
    volume2.attach_to_instance(InstanceId=instance["InstanceId"], Device="/dev/sdg")

    snapshots = client.create_snapshots(
        InstanceSpecification={"InstanceId": instance["InstanceId"]}
    )["Snapshots"]

    # 3 Snapshots ; 1 boot, two additional volumes
    assert len(snapshots) == 3
    # 3 unique snapshot IDs
    assert len(set([s["SnapshotId"] for s in snapshots])) == 3

    boot_snapshot = next(
        s for s in snapshots if s["VolumeId"] == boot_volume["VolumeId"]
    )
    assert boot_snapshot["VolumeSize"] == 8

    snapshot1 = next(s for s in snapshots if s["VolumeId"] == volume1.volume_id)
    assert snapshot1["VolumeSize"] == 80

    snapshot2 = next(s for s in snapshots if s["VolumeId"] == volume2.volume_id)
    assert snapshot2["VolumeSize"] == 100


# The default AMIs are not loaded for our test case, to speed things up
# But we do need it for this specific test
@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_create_snapshots_multiple_volumes_without_boot():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    volume1 = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")
    volume1.attach_to_instance(InstanceId=instance["InstanceId"], Device="/dev/sdh")

    volume2 = ec2.create_volume(Size=100, AvailabilityZone="us-east-1b")
    volume2.attach_to_instance(InstanceId=instance["InstanceId"], Device="/dev/sdg")

    snapshots = client.create_snapshots(
        InstanceSpecification={
            "InstanceId": instance["InstanceId"],
            "ExcludeBootVolume": True,
        }
    )["Snapshots"]

    # 1 Snapshots ; Only the additional volumes are returned
    assert len(snapshots) == 2

    snapshot1 = next(s for s in snapshots if s["VolumeId"] == volume1.volume_id)
    assert snapshot1["VolumeSize"] == 80

    snapshot2 = next(s for s in snapshots if s["VolumeId"] == volume2.volume_id)
    assert snapshot2["VolumeSize"] == 100


@mock_aws
def test_create_volume_with_iops():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume = ec2.create_volume(
        AvailabilityZone="us-east-1a", Size=10, VolumeType="gp3", Iops=4000
    )
    assert volume["Iops"] == 4000

    volume = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])["Volumes"][0]
    assert volume["Iops"] == 4000


@mock_aws
def test_create_volume_with_throughput():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume = ec2.create_volume(
        AvailabilityZone="us-east-1a", Size=10, VolumeType="gp3", Throughput=200
    )
    assert volume["Throughput"] == 200

    volume = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])["Volumes"][0]
    assert volume["Throughput"] == 200


@mock_aws
def test_create_volume_with_throughput_fails():
    resource = boto3.resource("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        resource.create_volume(
            AvailabilityZone="us-east-1a", Size=10, VolumeType="gp2", Throughput=200
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameterDependency"
    assert "Throughput" in ex.value.response["Error"]["Message"]
