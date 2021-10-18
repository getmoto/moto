from __future__ import unicode_literals

import boto
import boto.ec2
import boto3

import pytest
import sure  # noqa
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError
from moto import mock_ec2, mock_ec2_deprecated
from moto.ec2 import ec2_backends
from moto.ec2.models import OWNER_ID
from moto.kms import mock_kms
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


# Has boto3 equivalent
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

    with pytest.raises(EC2ResponseError) as ex:
        volume.delete(dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    volume.delete()

    all_volumes = conn.get_all_volumes()
    my_volume = [item for item in all_volumes if item.id == volume.id]
    my_volume.should.have.length_of(0)

    # Deleting something that was already deleted should throw an error
    with pytest.raises(EC2ResponseError) as cm:
        volume.delete()
    cm.value.code.should.equal("InvalidVolume.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_create_and_delete_volume_boto3():
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_delete_attached_volume():
    conn = boto.ec2.connect_to_region("us-east-1")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    # create an instance
    instance = reservation.instances[0]
    # create a volume
    volume = conn.create_volume(80, "us-east-1a")
    # attach volume to instance
    volume.attach(instance.id, "/dev/sdh")

    volume.update()
    volume.volume_state().should.equal("in-use")
    volume.attachment_state().should.equal("attached")

    volume.attach_data.instance_id.should.equal(instance.id)

    # attempt to delete volume
    # assert raises VolumeInUseError
    with pytest.raises(EC2ResponseError) as ex:
        volume.delete()
    ex.value.error_code.should.equal("VolumeInUse")
    ex.value.status.should.equal(400)
    ex.value.message.should.equal(
        "Volume {0} is currently attached to {1}".format(volume.id, instance.id)
    )

    volume.detach()

    volume.update()
    volume.volume_state().should.equal("available")

    volume.delete()

    all_volumes = conn.get_all_volumes()
    my_volume = [item for item in all_volumes if item.id == volume.id]
    my_volume.should.have.length_of(0)


@mock_ec2
def test_delete_attached_volume_boto3():
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
        "Volume {0} is currently attached to {1}".format(
            volume.id, instance["InstanceId"]
        )
    )

    volume.detach_from_instance(InstanceId=instance["InstanceId"])

    volume.state.should.equal("available")

    volume.delete()

    all_volumes = client.describe_volumes()["Volumes"]
    [v["VolumeId"] for v in all_volumes].shouldnt.contain(volume.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_encrypted_volume_dryrun():
    conn = boto.ec2.connect_to_region("us-east-1")
    with pytest.raises(EC2ResponseError) as ex:
        conn.create_volume(80, "us-east-1a", encrypted=True, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateVolume operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_create_encrypted_volume_dryrun_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        ec2.create_volume(Size=80, AvailabilityZone="us-east-1a", DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateVolume operation: Request would have succeeded, but DryRun flag is set"
    )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_encrypted_volume():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a", encrypted=True)

    with pytest.raises(EC2ResponseError) as ex:
        conn.create_volume(80, "us-east-1a", encrypted=True, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    all_volumes = [vol for vol in conn.get_all_volumes() if vol.id == volume.id]
    all_volumes[0].encrypted.should.be(True)


@mock_ec2
def test_create_encrypted_volume_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    volume = ec2.create_volume(Size=80, AvailabilityZone="us-east-1a", Encrypted=True)

    all_volumes = client.describe_volumes(VolumeIds=[volume.id])["Volumes"]
    all_volumes[0]["Encrypted"].should.be(True)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_filter_volume_by_id():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume1 = conn.create_volume(80, "us-east-1a")
    volume2 = conn.create_volume(36, "us-east-1b")
    volume3 = conn.create_volume(20, "us-east-1c")
    vol1 = conn.get_all_volumes(volume_ids=volume3.id)
    vol1.should.have.length_of(1)
    vol1[0].size.should.equal(20)
    vol1[0].zone.should.equal("us-east-1c")
    vol2 = conn.get_all_volumes(volume_ids=[volume1.id, volume2.id])
    vol2.should.have.length_of(2)

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_volumes(volume_ids=["vol-does_not_exist"])
    cm.value.code.should.equal("InvalidVolume.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_filter_volume_by_id_boto3():
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_volume_filters():
    conn = boto.ec2.connect_to_region("us-east-1")

    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    instance.update()

    volume1 = conn.create_volume(80, "us-east-1a", encrypted=True)
    volume2 = conn.create_volume(36, "us-east-1b", encrypted=False)
    volume3 = conn.create_volume(20, "us-east-1c", encrypted=True)

    snapshot = volume3.create_snapshot(description="testsnap")
    volume4 = conn.create_volume(25, "us-east-1a", snapshot=snapshot)

    conn.create_tags([volume1.id], {"testkey1": "testvalue1"})
    conn.create_tags([volume2.id], {"testkey2": "testvalue2"})

    volume1.update()
    volume2.update()
    volume3.update()
    volume4.update()

    block_mapping = instance.block_device_mapping["/dev/sda1"]

    volume_ids = (
        volume1.id,
        volume2.id,
        volume3.id,
        volume4.id,
        block_mapping.volume_id,
    )

    volumes_by_attach_time = conn.get_all_volumes(
        filters={"attachment.attach-time": block_mapping.attach_time}
    )
    set([vol.id for vol in volumes_by_attach_time]).should.equal(
        {block_mapping.volume_id}
    )

    volumes_by_attach_device = conn.get_all_volumes(
        filters={"attachment.device": "/dev/sda1"}
    )
    set([vol.id for vol in volumes_by_attach_device]).should.equal(
        {block_mapping.volume_id}
    )

    volumes_by_attach_instance_id = conn.get_all_volumes(
        filters={"attachment.instance-id": instance.id}
    )
    set([vol.id for vol in volumes_by_attach_instance_id]).should.equal(
        {block_mapping.volume_id}
    )

    volumes_by_attach_status = conn.get_all_volumes(
        filters={"attachment.status": "attached"}
    )
    set([vol.id for vol in volumes_by_attach_status]).should.equal(
        {block_mapping.volume_id}
    )

    volumes_by_create_time = conn.get_all_volumes(
        filters={"create-time": volume4.create_time}
    )
    set([vol.create_time for vol in volumes_by_create_time]).should.equal(
        {volume4.create_time}
    )

    volumes_by_size = conn.get_all_volumes(filters={"size": volume2.size})
    set([vol.id for vol in volumes_by_size]).should.equal({volume2.id})

    volumes_by_snapshot_id = conn.get_all_volumes(filters={"snapshot-id": snapshot.id})
    set([vol.id for vol in volumes_by_snapshot_id]).should.equal({volume4.id})

    volumes_by_status = conn.get_all_volumes(filters={"status": "in-use"})
    set([vol.id for vol in volumes_by_status]).should.equal({block_mapping.volume_id})

    volumes_by_id = conn.get_all_volumes(filters={"volume-id": volume1.id})
    set([vol.id for vol in volumes_by_id]).should.equal({volume1.id})

    volumes_by_tag_key = conn.get_all_volumes(filters={"tag-key": "testkey1"})
    set([vol.id for vol in volumes_by_tag_key]).should.equal({volume1.id})

    volumes_by_tag_value = conn.get_all_volumes(filters={"tag-value": "testvalue1"})
    set([vol.id for vol in volumes_by_tag_value]).should.equal({volume1.id})

    volumes_by_tag = conn.get_all_volumes(filters={"tag:testkey1": "testvalue1"})
    set([vol.id for vol in volumes_by_tag]).should.equal({volume1.id})

    volumes_by_unencrypted = conn.get_all_volumes(filters={"encrypted": "false"})
    set(
        [vol.id for vol in volumes_by_unencrypted if vol.id in volume_ids]
    ).should.equal({block_mapping.volume_id, volume2.id})

    volumes_by_encrypted = conn.get_all_volumes(filters={"encrypted": "true"})
    set([vol.id for vol in volumes_by_encrypted if vol.id in volume_ids]).should.equal(
        {volume1.id, volume3.id, volume4.id}
    )

    volumes_by_availability_zone = conn.get_all_volumes(
        filters={"availability-zone": "us-east-1b"}
    )
    set(
        [vol.id for vol in volumes_by_availability_zone if vol.id in volume_ids]
    ).should.equal({volume2.id})


@mock_ec2
def test_volume_filters_boto3():
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_volume_attach_and_detach():
    conn = boto.ec2.connect_to_region("us-east-1")
    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]
    volume = conn.create_volume(80, "us-east-1a")

    volume.update()
    volume.volume_state().should.equal("available")

    with pytest.raises(EC2ResponseError) as ex:
        volume.attach(instance.id, "/dev/sdh", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the AttachVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    volume.attach(instance.id, "/dev/sdh")

    volume.update()
    volume.volume_state().should.equal("in-use")
    volume.attachment_state().should.equal("attached")

    volume.attach_data.instance_id.should.equal(instance.id)

    with pytest.raises(EC2ResponseError) as ex:
        volume.detach(dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DetachVolume operation: Request would have succeeded, but DryRun flag is set"
    )

    volume.detach()

    volume.update()
    volume.volume_state().should.equal("available")

    with pytest.raises(EC2ResponseError) as cm1:
        volume.attach("i-1234abcd", "/dev/sdh")
    cm1.value.code.should.equal("InvalidInstanceID.NotFound")
    cm1.value.status.should.equal(400)
    cm1.value.request_id.should_not.be.none

    with pytest.raises(EC2ResponseError) as cm2:
        conn.detach_volume(volume.id, instance.id, "/dev/sdh")
    cm2.value.code.should.equal("InvalidAttachment.NotFound")
    cm2.value.status.should.equal(400)
    cm2.value.request_id.should_not.be.none

    with pytest.raises(EC2ResponseError) as cm3:
        conn.detach_volume(volume.id, "i-1234abcd", "/dev/sdh")
    cm3.value.code.should.equal("InvalidInstanceID.NotFound")
    cm3.value.status.should.equal(400)
    cm3.value.request_id.should_not.be.none


@mock_ec2
def test_volume_attach_and_detach_boto3():
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_snapshot():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a")

    with pytest.raises(EC2ResponseError) as ex:
        snapshot = volume.create_snapshot("a dryrun snapshot", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateSnapshot operation: Request would have succeeded, but DryRun flag is set"
    )

    snapshot = volume.create_snapshot("a test snapshot")
    snapshot.update()
    snapshot.status.should.equal("completed")

    snapshots = [snap for snap in conn.get_all_snapshots() if snap.id == snapshot.id]
    snapshots.should.have.length_of(1)
    snapshots[0].description.should.equal("a test snapshot")
    snapshots[0].start_time.should_not.be.none
    snapshots[0].encrypted.should.be(False)

    # Create snapshot without description
    num_snapshots = len(conn.get_all_snapshots())

    snapshot = volume.create_snapshot()
    conn.get_all_snapshots().should.have.length_of(num_snapshots + 1)

    snapshot.delete()
    conn.get_all_snapshots().should.have.length_of(num_snapshots)

    # Deleting something that was already deleted should throw an error
    with pytest.raises(EC2ResponseError) as cm:
        snapshot.delete()
    cm.value.code.should.equal("InvalidSnapshot.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_create_snapshot_boto3():
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
    snapshots[0]["StartTime"].should_not.be.none
    snapshots[0]["Encrypted"].should.be(False)

    # Create snapshot without description
    num_snapshots = len(client.describe_snapshots()["Snapshots"])

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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_encrypted_snapshot():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a", encrypted=True)
    snapshot = volume.create_snapshot("a test snapshot")
    snapshot.update()
    snapshot.status.should.equal("completed")

    snapshots = [snap for snap in conn.get_all_snapshots() if snap.id == snapshot.id]
    snapshots.should.have.length_of(1)
    snapshots[0].description.should.equal("a test snapshot")
    snapshots[0].start_time.should_not.be.none
    snapshots[0].encrypted.should.be(True)


@mock_ec2
@pytest.mark.parametrize("encrypted", [True, False])
def test_create_encrypted_snapshot_boto3(encrypted):
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
    snapshots[0]["StartTime"].should_not.be.none
    snapshots[0]["Encrypted"].should.be(encrypted)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_filter_snapshot_by_id():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume1 = conn.create_volume(36, "us-east-1a")
    snap1 = volume1.create_snapshot("a test snapshot 1")
    volume2 = conn.create_volume(42, "us-east-1a")
    snap2 = volume2.create_snapshot("a test snapshot 2")
    volume3 = conn.create_volume(84, "us-east-1a")
    snap3 = volume3.create_snapshot("a test snapshot 3")
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

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_snapshots(snapshot_ids=["snap-does_not_exist"])
    cm.value.code.should.equal("InvalidSnapshot.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_filter_snapshot_by_id_boto3():
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
        s["StartTime"].should_not.be.none
        s["VolumeId"].should.be.within([volume2.id, volume3.id])

    with pytest.raises(ClientError) as ex:
        client.describe_snapshots(SnapshotIds=["snap-does_not_exist"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidSnapshot.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_snapshot_filters():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume1 = conn.create_volume(20, "us-east-1a", encrypted=False)
    volume2 = conn.create_volume(25, "us-east-1a", encrypted=True)

    snapshot1 = volume1.create_snapshot(description="testsnapshot1")
    snapshot2 = volume1.create_snapshot(description="testsnapshot2")
    snapshot3 = volume2.create_snapshot(description="testsnapshot3")

    conn.create_tags([snapshot1.id], {"testkey1": "testvalue1"})
    conn.create_tags([snapshot2.id], {"testkey2": "testvalue2"})

    snapshots_by_description = conn.get_all_snapshots(
        filters={"description": "testsnapshot1"}
    )
    set([snap.id for snap in snapshots_by_description]).should.equal({snapshot1.id})

    snapshots_by_id = conn.get_all_snapshots(filters={"snapshot-id": snapshot1.id})
    set([snap.id for snap in snapshots_by_id]).should.equal({snapshot1.id})

    snapshots_by_start_time = conn.get_all_snapshots(
        filters={"start-time": snapshot1.start_time}
    )
    set([snap.start_time for snap in snapshots_by_start_time]).should.equal(
        {snapshot1.start_time}
    )

    snapshots_by_volume_id = conn.get_all_snapshots(filters={"volume-id": volume1.id})
    set([snap.id for snap in snapshots_by_volume_id]).should.equal(
        {snapshot1.id, snapshot2.id}
    )

    snapshots_by_status = conn.get_all_snapshots(filters={"status": "completed"})
    (
        {snapshot1.id, snapshot2.id, snapshot3.id}
        - {snap.id for snap in snapshots_by_status}
    ).should.have.length_of(0)

    snapshots_by_volume_size = conn.get_all_snapshots(
        filters={"volume-size": volume1.size}
    )
    set([snap.id for snap in snapshots_by_volume_size]).should.equal(
        {snapshot1.id, snapshot2.id}
    )

    snapshots_by_tag_key = conn.get_all_snapshots(filters={"tag-key": "testkey1"})
    set([snap.id for snap in snapshots_by_tag_key]).should.equal({snapshot1.id})

    snapshots_by_tag_value = conn.get_all_snapshots(filters={"tag-value": "testvalue1"})
    set([snap.id for snap in snapshots_by_tag_value]).should.equal({snapshot1.id})

    snapshots_by_tag = conn.get_all_snapshots(filters={"tag:testkey1": "testvalue1"})
    set([snap.id for snap in snapshots_by_tag]).should.equal({snapshot1.id})

    snapshots_by_encrypted = conn.get_all_snapshots(filters={"encrypted": "true"})
    set([snap.id for snap in snapshots_by_encrypted]).should.equal({snapshot3.id})

    snapshots_by_owner_id = conn.get_all_snapshots(filters={"owner-id": OWNER_ID})
    set([snap.id for snap in snapshots_by_owner_id]).should.equal(
        {snapshot1.id, snapshot2.id, snapshot3.id}
    )


@mock_ec2
def test_snapshot_filters_boto3():
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_snapshot_attribute():
    import copy

    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a")
    snapshot = volume.create_snapshot()

    # Baseline
    attributes = conn.get_snapshot_attribute(
        snapshot.id, attribute="createVolumePermission"
    )
    attributes.name.should.equal("create_volume_permission")
    attributes.attrs.should.have.length_of(0)

    ADD_GROUP_ARGS = {
        "snapshot_id": snapshot.id,
        "attribute": "createVolumePermission",
        "operation": "add",
        "groups": "all",
    }

    REMOVE_GROUP_ARGS = {
        "snapshot_id": snapshot.id,
        "attribute": "createVolumePermission",
        "operation": "remove",
        "groups": "all",
    }

    # Add 'all' group and confirm

    with pytest.raises(EC2ResponseError) as ex:
        conn.modify_snapshot_attribute(**dict(ADD_GROUP_ARGS, **{"dry_run": True}))
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifySnapshotAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.modify_snapshot_attribute(**ADD_GROUP_ARGS)

    attributes = conn.get_snapshot_attribute(
        snapshot.id, attribute="createVolumePermission"
    )
    attributes.attrs["groups"].should.have.length_of(1)
    attributes.attrs["groups"].should.equal(["all"])

    # Add is idempotent
    conn.modify_snapshot_attribute.when.called_with(**ADD_GROUP_ARGS).should_not.throw(
        EC2ResponseError
    )

    # Remove 'all' group and confirm
    with pytest.raises(EC2ResponseError) as ex:
        conn.modify_snapshot_attribute(**dict(REMOVE_GROUP_ARGS, **{"dry_run": True}))
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifySnapshotAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.modify_snapshot_attribute(**REMOVE_GROUP_ARGS)

    attributes = conn.get_snapshot_attribute(
        snapshot.id, attribute="createVolumePermission"
    )
    attributes.attrs.should.have.length_of(0)

    # Remove is idempotent
    conn.modify_snapshot_attribute.when.called_with(
        **REMOVE_GROUP_ARGS
    ).should_not.throw(EC2ResponseError)

    # Error: Add with group != 'all'
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_snapshot_attribute(
            snapshot.id,
            attribute="createVolumePermission",
            operation="add",
            groups="everyone",
        )
    cm.value.code.should.equal("InvalidAMIAttributeItemValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Add with invalid snapshot ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_snapshot_attribute(
            "snapshot-abcd1234",
            attribute="createVolumePermission",
            operation="add",
            groups="all",
        )
    cm.value.code.should.equal("InvalidSnapshot.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Error: Remove with invalid snapshot ID
    with pytest.raises(EC2ResponseError) as cm:
        conn.modify_snapshot_attribute(
            "snapshot-abcd1234",
            attribute="createVolumePermission",
            operation="remove",
            groups="all",
        )
    cm.value.code.should.equal("InvalidSnapshot.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_modify_snapshot_attribute():
    import copy

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
    cm.value.response["ResponseMetadata"]["RequestId"].should_not.be.none
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
    with pytest.raises(ClientError) as ex:
        ec2_client.modify_snapshot_attribute(
            **dict(REMOVE_GROUP_ARGS, **{"DryRun": True})
        )
    cm.value.response["Error"]["Code"].should.equal("DryRunOperation")
    cm.value.response["ResponseMetadata"]["RequestId"].should_not.be.none
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
    cm.value.response["ResponseMetadata"]["RequestId"].should_not.be.none
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
    cm.value.response["ResponseMetadata"]["RequestId"].should_not.be.none
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
    cm.value.response["ResponseMetadata"]["RequestId"].should_not.be.none
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_volume_from_snapshot():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a")
    snapshot = volume.create_snapshot("a test snapshot")

    with pytest.raises(EC2ResponseError) as ex:
        snapshot = volume.create_snapshot("a test snapshot", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateSnapshot operation: Request would have succeeded, but DryRun flag is set"
    )

    snapshot = volume.create_snapshot("a test snapshot")
    snapshot.update()
    snapshot.status.should.equal("completed")

    new_volume = snapshot.create_volume("us-east-1a")
    new_volume.size.should.equal(80)
    new_volume.snapshot_id.should.equal(snapshot.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_volume_from_encrypted_snapshot():
    conn = boto.ec2.connect_to_region("us-east-1")
    volume = conn.create_volume(80, "us-east-1a", encrypted=True)

    snapshot = volume.create_snapshot("a test snapshot")
    snapshot.update()
    snapshot.status.should.equal("completed")

    new_volume = snapshot.create_volume("us-east-1a")
    new_volume.size.should.equal(80)
    new_volume.snapshot_id.should.equal(snapshot.id)
    new_volume.encrypted.should.be(True)


@mock_ec2
@pytest.mark.parametrize("encrypted", [True, False])
def test_create_volume_from_snapshot_boto3(encrypted):
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_modify_attribute_blockDeviceMapping():
    """
    Reproduces the missing feature explained at [0], where we want to mock a
    call to modify an instance attribute of type: blockDeviceMapping.

    [0] https://github.com/spulec/moto/issues/160
    """
    conn = boto.ec2.connect_to_region("us-east-1")

    reservation = conn.run_instances(EXAMPLE_AMI_ID)

    instance = reservation.instances[0]

    with pytest.raises(EC2ResponseError) as ex:
        instance.modify_attribute(
            "blockDeviceMapping", {"/dev/sda1": True}, dry_run=True
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ModifyInstanceAttribute operation: Request would have succeeded, but DryRun flag is set"
    )

    instance.modify_attribute("blockDeviceMapping", {"/dev/sda1": True})

    instance = ec2_backends[conn.region.name].get_instance(instance.id)
    instance.block_device_mapping.should.have.key("/dev/sda1")
    instance.block_device_mapping["/dev/sda1"].delete_on_termination.should.be(True)


@mock_ec2
def test_modify_attribute_blockDeviceMapping_boto3():
    """
    Reproduces the missing feature explained at [0], where we want to mock a
    call to modify an instance attribute of type: blockDeviceMapping.

    [0] https://github.com/spulec/moto/issues/160
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_volume_tag_escaping():
    conn = boto.ec2.connect_to_region("us-east-1")
    vol = conn.create_volume(10, "us-east-1a")
    snapshot = conn.create_snapshot(vol.id, "Desc")

    with pytest.raises(EC2ResponseError) as ex:
        snapshot.add_tags({"key": "</closed>"}, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )
    snaps = [snap for snap in conn.get_all_snapshots() if snap.id == snapshot.id]
    dict(snaps[0].tags).should_not.be.equal({"key": "</closed>"})

    snapshot.add_tags({"key": "</closed>"})

    snaps = [snap for snap in conn.get_all_snapshots() if snap.id == snapshot.id]
    dict(snaps[0].tags).should.equal({"key": "</closed>"})


@mock_ec2
def test_volume_tag_escaping_boto3():
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
        create_snapshot_error = ec2_client.create_snapshot(VolumeId="vol-abcd1234")
        cm.value.response["Error"]["Code"].should.equal("InvalidVolume.NotFound")
        cm.value.response["Error"]["Message"].should.equal(
            "The volume 'vol-abcd1234' does not exist."
        )
        cm.value.response["ResponseMetadata"]["RequestId"].should_not.be.none
        cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)

    # Copy from non-existent source region.
    with pytest.raises(ClientError) as cm:
        copy_snapshot_response = dest_ec2_client.copy_snapshot(
            SourceSnapshotId=create_snapshot_response["SnapshotId"],
            SourceRegion="eu-west-2",
        )
        cm.value.response["Error"]["Code"].should.equal("InvalidSnapshot.NotFound")
        cm.value.response["Error"]["Message"].should.be.none
        cm.value.response["ResponseMetadata"]["RequestId"].should_not.be.none
        cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_ec2
def test_search_for_many_snapshots():
    ec2_client = boto3.client("ec2", region_name="eu-west-1")

    volume_response = ec2_client.create_volume(AvailabilityZone="eu-west-1a", Size=10)

    snapshot_ids = []
    for i in range(1, 20):
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
    volume.encrypted.should.be.true
    # Subsequent encrypted volumes should use the now-created default key.
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=True, Size=10
    )
    volume.kms_key_id.should.equal(default_ebs_key_arn)
    volume.encrypted.should.be.true


@mock_ec2
def test_create_volume_with_kms_key():
    resource = boto3.resource("ec2", region_name="us-east-1")
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=True, KmsKeyId="key", Size=10
    )
    volume.kms_key_id.should.equal("key")
    volume.encrypted.should.be.true


@mock_ec2
def test_kms_key_id_property_hidden_when_volume_not_encrypted():
    client = boto3.client("ec2", region_name="us-east-1")
    resp = client.create_volume(AvailabilityZone="us-east-1a", Encrypted=False, Size=10)
    resp["Encrypted"].should.be.false
    resp.should_not.have.key("KmsKeyId")
    resp = client.describe_volumes(VolumeIds=[resp["VolumeId"]])
    resp["Volumes"][0]["Encrypted"].should.be.false
    resp["Volumes"][0].should_not.have.key("KmsKeyId")
    resource = boto3.resource("ec2", region_name="us-east-1")
    volume = resource.create_volume(
        AvailabilityZone="us-east-1a", Encrypted=False, Size=10
    )
    volume.encrypted.should.be.false
    volume.kms_key_id.should.be.none


@mock_ec2
def test_create_volume_with_standard_type():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume = ec2.create_volume(AvailabilityZone="us-east-1a", Size=100, Iops=1000)
    volume["VolumeType"].should.equal("gp2")

    volume = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])["Volumes"][0]
    volume["VolumeType"].should.equal("gp2")


@pytest.mark.parametrize("volume_type", ["gp2", "gp3", "io1", "io2", "standard"])
@mock_ec2
def test_create_volume_with_non_standard_type(volume_type):
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume = ec2.create_volume(
        AvailabilityZone="us-east-1a", Size=100, Iops=1000, VolumeType=volume_type
    )
    volume["VolumeType"].should.equal(volume_type)

    volume = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])["Volumes"][0]
    volume["VolumeType"].should.equal(volume_type)
