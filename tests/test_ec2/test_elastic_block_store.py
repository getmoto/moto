import boto3

import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from moto import mock_ec2
from moto.core import DEFAULT_ACCOUNT_ID as OWNER_ID
from moto.ec2.models.elastic_block_store import IOPS_REQUIRED_VOLUME_TYPES
from moto.kms import mock_kms
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


@mock_ec2
def test_create_and_delete_volume():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")

    all_volumes = client.describe_volumes()["Volumes"]

    current_volume = [item for item in all_volumes if item["VolumeId"] == volume.id]
    current_volume.should.have.length_of(1)
    current_volume[0]["Size"].should.equal(80)
    current_volume[0]["AvailabilityZone"].should.equal("us-east-1a")
    current_volume[0]["Encrypted"].should.be(False)

    with pytest.raises(ClientError) as ex:
        volume.delete(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    volume.delete()

    all_volumes = client.describe_volumes()["Volumes"]
    my_volume = [item for item in all_volumes if item["VolumeId"] == volume.id]
    my_volume.should.have.length_of(0)

    # Deleting something that was already deleted should throw an error
    with pytest.raises(ClientError) as ex:
        volume.delete()
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidVolume.NotFound")


@mock_ec2
def test_modify_volumes():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    old_size = 80
    new_size = 160
    new_type = "io2"

    volume_id = ec2.create_volume(Size=old_size, AvailabilityZone="us-east-1a").id

    # Ensure no modification records exist
    modifications = client.describe_volumes_modifications()
    modifications["VolumesModifications"].should.have.length_of(0)

    # Ensure volume size can be modified
    response = client.modify_volume(VolumeId=volume_id, Size=new_size)
    response["VolumeModification"]["OriginalSize"].should.equal(old_size)
    response["VolumeModification"]["TargetSize"].should.equal(new_size)
    client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0]["Size"].should.equal(
        new_size
    )

    # Ensure volume type can be modified
    response = client.modify_volume(VolumeId=volume_id, VolumeType=new_type)
    response["VolumeModification"]["OriginalVolumeType"].should.equal("gp2")
    response["VolumeModification"]["TargetVolumeType"].should.equal(new_type)
    client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0][
        "VolumeType"
    ].should.equal(new_type)

    # Ensure volume modifications are tracked
    modifications = client.describe_volumes_modifications()
    modifications["VolumesModifications"].should.have.length_of(2)


@mock_ec2
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

    volume.state.should.equal("in-use")
    volume.attachments.should.have.length_of(1)
    volume.attachments[0]["InstanceId"].should.equal(instance["InstanceId"])
    volume.attachments[0]["State"].should.equal("attached")

    # attempt to delete volume
    # assert raises VolumeInUseError
    with pytest.raises(ClientError) as ex:
        volume.delete()
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("VolumeInUse")
    ex.value.response["Error"]["Message"].should.equal(
        f"Volume {volume.id} is currently attached to {instance['InstanceId']}"
    )

    volume.detach_from_instance(InstanceId=instance["InstanceId"])

    volume.state.should.equal("available")

    volume.delete()

    all_volumes = client.describe_volumes()["Volumes"]
    [v["VolumeId"] for v in all_volumes].shouldnt.contain(volume.id)


@mock_ec2
def test_create_encrypted_volume_dryrun():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        ec2.create_volume(Size=80, AvailabilityZone="us-east-1a", DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateVolume operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_create_encrypted_volume():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a", Encrypted=True)

    all_volumes = client.describe_volumes(VolumeIds=[volume.id])["Volumes"]
    all_volumes[0]["Encrypted"].should.be(True)


@mock_ec2
def test_filter_volume_by_id():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume1 = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")
    volume2 = ec2.create_volume(Size=36, AvailabilityZone="us-east-1b")
    volume3 = ec2.create_volume(Size=20, AvailabilityZone="us-east-1c")

    vol3 = client.describe_volumes(VolumeIds=[volume3.id])["Volumes"]
    vol3.should.have.length_of(1)
    vol3[0]["Size"].should.equal(20)
    vol3[0]["AvailabilityZone"].should.equal("us-east-1c")

    vol12 = client.describe_volumes(VolumeIds=[volume1.id, volume2.id])["Volumes"]
    vol12.should.have.length_of(2)

    with pytest.raises(ClientError) as ex:
        client.describe_volumes(VolumeIds=["vol-does_not_exist"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("InvalidVolume.NotFound")


@mock_ec2
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
        expected = expected if type(expected) == list else [expected]
        volumes = client.describe_volumes(Filters=[{"Name": name, "Values": [value]}])[
            "Volumes"
        ]
        actual = [vol["VolumeId"] for vol in volumes]
        if multiple_results:
            for e in expected:
                actual.should.contain(e)
            for e in not_expected:
                actual.shouldnt.contain(e)
        else:
            set(actual).should.equal(set(expected))

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
    [vol["VolumeId"] for vol in volumes_by_attach_device].should.contain(volume4.id)


@mock_ec2
def test_volume_attach_and_detach():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    volumes = client.describe_volumes(
        Filters=[{"Name": "attachment.instance-id", "Values": [instance["InstanceId"]]}]
    )["Volumes"]
    volumes.should.have.length_of(1)
    volumes[0]["AvailabilityZone"].should.equal("us-east-1a")

    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")

    volume.reload()
    volume.state.should.equal("available")

    with pytest.raises(ClientError) as ex:
        volume.attach_to_instance(
            InstanceId=instance["InstanceId"], Device="/dev/sdh", DryRun=True
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the AttachVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    volume.attach_to_instance(InstanceId=instance["InstanceId"], Device="/dev/sdh")

    volume.state.should.equal("in-use")
    volume.attachments[0]["State"].should.equal("attached")
    volume.attachments[0]["InstanceId"].should.equal(instance["InstanceId"])

    with pytest.raises(ClientError) as ex:
        volume.detach_from_instance(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DetachVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    volume.detach_from_instance(InstanceId=instance["InstanceId"])

    volume.state.should.equal("available")

    with pytest.raises(ClientError) as ex1:
        volume.attach_to_instance(InstanceId="i-1234abcd", Device="/dev/sdh")
    ex1.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex1.value.response["Error"]["Code"].should.equal("InvalidInstanceID.NotFound")

    with pytest.raises(ClientError) as ex2:
        client.detach_volume(
            VolumeId=volume.id, InstanceId=instance["InstanceId"], Device="/dev/sdh"
        )
    ex2.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex2.value.response["Error"]["Code"].should.equal("InvalidAttachment.NotFound")

    with pytest.raises(ClientError) as ex3:
        client.detach_volume(
            VolumeId=volume.id, InstanceId="i-1234abcd", Device="/dev/sdh"
        )
    ex3.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex3.value.response["Error"]["Code"].should.equal("InvalidInstanceID.NotFound")


@mock_ec2
def test_create_snapshot():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a")

    with pytest.raises(ClientError) as ex:
        volume.create_snapshot(Description="a dryrun snapshot", DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateSnapshot operation: Request would have succeeded, but DryRun flag is set"
    )

    snapshot = volume.create_snapshot(Description="a test snapshot")
    snapshot.reload()
    snapshot.state.should.equal("completed")

    snapshots = [
        snap
        for snap in client.describe_snapshots()["Snapshots"]
        if snap["SnapshotId"] == snapshot.id
    ]
    snapshots.should.have.length_of(1)
    snapshots[0]["Description"].should.equal("a test snapshot")
    snapshots[0]["StartTime"].shouldnt.equal(None)
    snapshots[0]["Encrypted"].should.be(False)

    # Create snapshot without description
    snapshot = volume.create_snapshot()
    current_snapshots = client.describe_snapshots()["Snapshots"]
    [s["SnapshotId"] for s in current_snapshots].should.contain(snapshot.id)

    snapshot.delete()
    current_snapshots = client.describe_snapshots()["Snapshots"]
    [s["SnapshotId"] for s in current_snapshots].shouldnt.contain(snapshot.id)

    # Deleting something that was already deleted should throw an error
    with pytest.raises(ClientError) as ex:
        snapshot.delete()
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("InvalidSnapshot.NotFound")


@mock_ec2
@pytest.mark.parametrize("encrypted", [True, False])
def test_create_encrypted_snapshot(encrypted):
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(
        Size=80, AvailabilityZone="us-east-1a", Encrypted=encrypted
    )
    snapshot = volume.create_snapshot(Description="a test snapshot")
    snapshot.encrypted.should.be(encrypted)
    snapshot.reload()
    snapshot.state.should.equal("completed")

    snapshots = [
        snap
        for snap in client.describe_snapshots()["Snapshots"]
        if snap["SnapshotId"] == snapshot.id
    ]
    snapshots.should.have.length_of(1)
    snapshots[0]["Description"].should.equal("a test snapshot")
    snapshots[0]["StartTime"].shouldnt.equal(None)
    snapshots[0]["Encrypted"].should.be(encrypted)


@mock_ec2
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
    snapshots1.should.have.length_of(1)
    snapshots1[0]["VolumeId"].should.equal(volume1.id)
    snapshots2 = client.describe_snapshots(SnapshotIds=[snap2.id, snap3.id])[
        "Snapshots"
    ]
    snapshots2.should.have.length_of(2)
    for s in snapshots2:
        s["StartTime"].shouldnt.equal(None)
        s["VolumeId"].should.be.within([volume2.id, volume3.id])

    with pytest.raises(ClientError) as ex:
        client.describe_snapshots(SnapshotIds=["snap-does_not_exist"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidSnapshot.NotFound")


@mock_ec2
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
        expected = expected if type(expected) == list else [expected]
        snapshots = client.describe_snapshots(
            Filters=[{"Name": name, "Values": [value]}]
        )["Snapshots"]
        if others:
            actual = set([s["SnapshotId"] for s in snapshots])
            for e in expected:
                actual.should.contain(e)
        else:
            set([s["SnapshotId"] for s in snapshots]).should.equal(set(expected))

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
    [s["SnapshotId"] for s in snapshots].should.contain(snapshot1.id)
    snapshots = client.describe_snapshots(
        Filters=[{"Name": "status", "Values": ["completed"]}]
    )["Snapshots"]
    [s["SnapshotId"] for s in snapshots].should.contain(snapshot1.id)
    [s["SnapshotId"] for s in snapshots].should.contain(snapshot2.id)
    [s["SnapshotId"] for s in snapshots].should.contain(snapshot3.id)


@mock_ec2
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

    cm.value.response["Error"]["Code"].should.equal("DryRunOperation")
    cm.value.response["ResponseMetadata"]["RequestId"].shouldnt.equal(None)
    cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)

    ec2_client.modify_snapshot_attribute(**ADD_GROUP_ARGS)

    attributes = ec2_client.describe_snapshot_attribute(
        SnapshotId=snapshot.id, Attribute="createVolumePermission"
    )
    assert attributes["CreateVolumePermissions"] == [
        {"Group": "all"}
    ], "This snapshot should have public group permissions."

    # Add is idempotent
    ec2_client.modify_snapshot_attribute.when.called_with(
        **ADD_GROUP_ARGS
    ).should_not.throw(ClientError)
    assert attributes["CreateVolumePermissions"] == [
        {"Group": "all"}
    ], "This snapshot should have public group permissions."

    # Remove 'all' group and confirm
    with pytest.raises(ClientError):
        ec2_client.modify_snapshot_attribute(
            **dict(REMOVE_GROUP_ARGS, **{"DryRun": True})
        )
    cm.value.response["Error"]["Code"].should.equal("DryRunOperation")
    cm.value.response["ResponseMetadata"]["RequestId"].shouldnt.equal(None)
    cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)

    ec2_client.modify_snapshot_attribute(**REMOVE_GROUP_ARGS)

    attributes = ec2_client.describe_snapshot_attribute(
        SnapshotId=snapshot.id, Attribute="createVolumePermission"
    )
    assert not attributes[
        "CreateVolumePermissions"
    ], "This snapshot should have no permissions."

    # Remove is idempotent
    ec2_client.modify_snapshot_attribute.when.called_with(
        **REMOVE_GROUP_ARGS
    ).should_not.throw(ClientError)
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
    cm.value.response["Error"]["Code"].should.equal("InvalidAMIAttributeItemValue")
    cm.value.response["ResponseMetadata"]["RequestId"].shouldnt.equal(None)
    cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)

    # Error: Add with invalid snapshot ID
    with pytest.raises(ClientError) as cm:
        ec2_client.modify_snapshot_attribute(
            SnapshotId="snapshot-abcd1234",
            Attribute="createVolumePermission",
            OperationType="add",
            GroupNames=["all"],
        )
    cm.value.response["Error"]["Code"].should.equal("InvalidSnapshot.NotFound")
    cm.value.response["ResponseMetadata"]["RequestId"].shouldnt.equal(None)
    cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)

    # Error: Remove with invalid snapshot ID
    with pytest.raises(ClientError) as cm:
        ec2_client.modify_snapshot_attribute(
            SnapshotId="snapshot-abcd1234",
            Attribute="createVolumePermission",
            OperationType="remove",
            GroupNames=["all"],
        )
    cm.value.response["Error"]["Code"].should.equal("InvalidSnapshot.NotFound")
    cm.value.response["ResponseMetadata"]["RequestId"].shouldnt.equal(None)
    cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)

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


@mock_ec2
@pytest.mark.parametrize("encrypted", [True, False])
def test_create_volume_from_snapshot(encrypted):
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(
        Size=80, AvailabilityZone="us-east-1a", Encrypted=encrypted
    )
    snapshot = volume.create_snapshot(Description="a test snapshot")
    snapshot.reload()
    snapshot.state.should.equal("completed")

    new_volume = client.create_volume(
        SnapshotId=snapshot.id, AvailabilityZone="us-east-1a"
    )
    new_volume["Size"].should.equal(80)
    new_volume["SnapshotId"].should.equal(snapshot.id)
    new_volume["Encrypted"].should.equal(encrypted)


@mock_ec2
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
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyInstanceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute(
        BlockDeviceMappings=[
            {"DeviceName": "/dev/sda1", "Ebs": {"DeleteOnTermination": True}}
        ]
    )

    instance.reload()
    mapping = instance.block_device_mappings[0]
    mapping.should.have.key("DeviceName").equal("/dev/sda1")
    mapping["Ebs"]["DeleteOnTermination"].should.be(True)


@mock_ec2
def test_volume_tag_escaping():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(Size=10, AvailabilityZone="us-east-1a")
    snapshot = client.create_snapshot(VolumeId=volume.id, Description="Desc")
    snapshot = ec2.Snapshot(snapshot["SnapshotId"])

    with pytest.raises(ClientError) as ex:
        snapshot.create_tags(Tags=[{"Key": "key", "Value": "</closed>"}], DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    snapshot.tags.should.have.length_of(0)

    snapshot.create_tags(Tags=[{"Key": "key", "Value": "</closed>"}])

    snapshot.tags.should.equal([{"Key": "key", "Value": "</closed>"}])


@mock_ec2
def test_volume_property_hidden_when_no_tags_exist():
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    volume_response = ec2_client.create_volume(Size=10, AvailabilityZone="us-east-1a")

    volume_response.get("Tags").should.equal(None)


@mock_ec2
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
    copy_snapshot_response["Tags"].should.equal(tag_spec[0]["Tags"])

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
        getattr(source, attrib).should.equal(getattr(dest, attrib))

    # Copy from non-existent source ID.
    with pytest.raises(ClientError) as cm:
        ec2_client.create_snapshot(VolumeId="vol-abcd1234")
    cm.value.response["Error"]["Code"].should.equal("InvalidVolume.NotFound")
    cm.value.response["Error"]["Message"].should.equal(
        "The volume 'vol-abcd1234' does not exist."
    )
    cm.value.response["ResponseMetadata"]["RequestId"].shouldnt.equal(None)
    cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)

    # Copy from non-existent source region.
    with pytest.raises(ClientError) as cm:
        dest_ec2_client.copy_snapshot(
            SourceSnapshotId=create_snapshot_response["SnapshotId"],
            SourceRegion="eu-west-2",
        )
    cm.value.response["Error"]["Code"].should.equal("InvalidSnapshot.NotFound")
    cm.value.response["Error"]["Message"].should.equal(None)
    cm.value.response["ResponseMetadata"]["RequestId"].shouldnt.equal(None)
    cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_ec2
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


@mock_ec2
def test_create_unencrypted_volume_with_kms_key_fails():
    resource = boto3.resource("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        resource.create_volume(
            AvailabilityZone="us-east-1a", Encrypted=False, KmsKeyId="key", Size=10
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterDependency")
    ex.value.response["Error"]["Message"].should.contain("KmsKeyId")


@mock_kms
@mock_ec2
def test_create_encrypted_volume_without_kms_key_should_use_default_key():
    kms = boto3.client("kms", region_name="us-east-1")

    # Creating an encrypted volume should create (and use) the default key.
    resource = boto3.resource("ec2", region_name="us-east-1")
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=True, Size=10
    )
    default_ebs_key_arn = kms.describe_key(KeyId="alias/aws/ebs")["KeyMetadata"]["Arn"]
    volume.kms_key_id.should.equal(default_ebs_key_arn)
    volume.encrypted.should.equal(True)
    # Subsequent encrypted volumes should use the now-created default key.
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=True, Size=10
    )
    volume.kms_key_id.should.equal(default_ebs_key_arn)
    volume.encrypted.should.equal(True)


@mock_ec2
def test_create_volume_with_kms_key():
    resource = boto3.resource("ec2", region_name="us-east-1")
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=True, KmsKeyId="key", Size=10
    )
    volume.kms_key_id.should.equal("key")
    volume.encrypted.should.equal(True)


@mock_ec2
def test_kms_key_id_property_hidden_when_volume_not_encrypted():
    client = boto3.client("ec2", region_name="us-east-1")
    resp = client.create_volume(AvailabilityZone="us-east-1a", Encrypted=False, Size=10)
    resp["Encrypted"].should.equal(False)
    resp.should_not.have.key("KmsKeyId")
    resp = client.describe_volumes(VolumeIds=[resp["VolumeId"]])
    resp["Volumes"][0]["Encrypted"].should.equal(False)
    resp["Volumes"][0].should_not.have.key("KmsKeyId")
    resource = boto3.resource("ec2", region_name="us-east-1")
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=False, Size=10
    )
    volume.encrypted.should.equal(False)
    volume.kms_key_id.should.equal(None)


@mock_ec2
def test_create_volume_with_standard_type():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume = ec2.create_volume(AvailabilityZone="us-east-1a", Size=100)
    volume["VolumeType"].should.equal("gp2")

    volume = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])["Volumes"][0]
    volume["VolumeType"].should.equal("gp2")


@pytest.mark.parametrize("volume_type", ["gp2", "gp3", "io1", "io2", "standard"])
@mock_ec2
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
    volume["VolumeType"].should.equal(volume_type)

    volume = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])["Volumes"][0]
    volume["VolumeType"].should.equal(volume_type)


@mock_ec2
def test_create_snapshots_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_snapshots(
            InstanceSpecification={"InstanceId": "asf"}, DryRun=True
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateSnapshots operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
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

    snapshots.should.have.length_of(1)
    snapshots[0].should.have.key("Description").equals("my tagged snapshots")
    snapshots[0].should.have.key("Tags").equals(
        [{"Key": "key1", "Value": "val1"}, {"Key": "key2", "Value": "val2"}]
    )


@mock_ec2
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

    snapshots.should.have.length_of(1)
    snapshots[0].should.have.key("Encrypted").equals(False)
    snapshots[0].should.have.key("VolumeId").equals(boot_volume["VolumeId"])
    snapshots[0].should.have.key("VolumeSize").equals(8)
    snapshots[0].should.have.key("SnapshotId")
    snapshots[0].should.have.key("Description").equals("")
    snapshots[0].should.have.key("Tags").equals([])


@mock_ec2
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
    snapshots.should.have.length_of(3)
    # 3 unique snapshot IDs
    set([s["SnapshotId"] for s in snapshots]).should.have.length_of(3)

    boot_snapshot = next(
        s for s in snapshots if s["VolumeId"] == boot_volume["VolumeId"]
    )
    boot_snapshot.should.have.key("VolumeSize").equals(8)

    snapshot1 = next(s for s in snapshots if s["VolumeId"] == volume1.volume_id)
    snapshot1.should.have.key("VolumeSize").equals(80)

    snapshot2 = next(s for s in snapshots if s["VolumeId"] == volume2.volume_id)
    snapshot2.should.have.key("VolumeSize").equals(100)


@mock_ec2
def test_create_snapshots_multiple_volumes_without_boot():
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
    snapshots.should.have.length_of(2)

    snapshot1 = next(s for s in snapshots if s["VolumeId"] == volume1.volume_id)
    snapshot1.should.have.key("VolumeSize").equals(80)

    snapshot2 = next(s for s in snapshots if s["VolumeId"] == volume2.volume_id)
    snapshot2.should.have.key("VolumeSize").equals(100)


@mock_ec2
def test_create_volume_with_iops():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume = ec2.create_volume(
        AvailabilityZone="us-east-1a", Size=10, VolumeType="gp3", Iops=4000
    )
    volume["Iops"].should.equal(4000)

    volume = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])["Volumes"][0]
    volume["Iops"].should.equal(4000)
