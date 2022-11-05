"""Unit tests for ebs-supported APIs."""
import boto3
import hashlib
import sure  # noqa # pylint: disable=unused-import
from moto import mock_ebs, mock_ec2
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_ebs
def test_start_snapshot__minimal():
    client = boto3.client("ebs", region_name="eu-west-1")
    resp = client.start_snapshot(VolumeSize=720)

    resp.should.have.key("SnapshotId")
    resp.should.have.key("OwnerId").equals(ACCOUNT_ID)
    resp.should.have.key("Status").equals("pending")
    resp.should.have.key("StartTime")
    resp.should.have.key("VolumeSize").equals(720)
    resp.should.have.key("BlockSize").equals(512)


@mock_ebs
def test_start_snapshot():
    client = boto3.client("ebs", region_name="eu-west-1")
    resp = client.start_snapshot(
        VolumeSize=120,
        Tags=[{"Key": "kt", "Value": "vt"}],
        Description="my fancy snapshot",
    )

    resp.should.have.key("SnapshotId")
    resp.should.have.key("OwnerId").equals(ACCOUNT_ID)
    resp.should.have.key("Status").equals("pending")
    resp.should.have.key("StartTime")
    resp.should.have.key("VolumeSize").equals(120)
    resp.should.have.key("BlockSize").equals(512)
    resp.should.have.key("Tags").equals([{"Key": "kt", "Value": "vt"}])
    resp.should.have.key("Description").equals("my fancy snapshot")


@mock_ebs
def test_complete_snapshot():
    client = boto3.client("ebs", region_name="ap-southeast-1")
    snapshot_id = client.start_snapshot(VolumeSize=720)["SnapshotId"]

    resp = client.complete_snapshot(SnapshotId=snapshot_id, ChangedBlocksCount=0)
    resp.should.have.key("Status").equals("completed")


@mock_ebs
def test_put_snapshot_block():
    data = b"data for this specific block"
    checksum = hashlib.sha256(data).hexdigest()
    client = boto3.client("ebs", region_name="eu-west-1")
    snapshot_id = client.start_snapshot(VolumeSize=720)["SnapshotId"]
    resp = client.put_snapshot_block(
        SnapshotId=snapshot_id,
        BlockIndex=5,
        BlockData=data,
        DataLength=524288,
        Checksum=checksum,
        ChecksumAlgorithm="SHA256",
    )

    resp.should.have.key("Checksum").equals(checksum)
    resp.should.have.key("ChecksumAlgorithm").equals("SHA256")


@mock_ebs
def test_get_snapshot_block():
    client = boto3.client("ebs", region_name="eu-west-1")
    snapshot_id = client.start_snapshot(VolumeSize=720)["SnapshotId"]
    for idx, data in [(1, b"data 1"), (2, b"data 2"), (3, b"data 3")]:
        checksum = hashlib.sha256(data).hexdigest()
        client.put_snapshot_block(
            SnapshotId=snapshot_id,
            BlockIndex=idx,
            BlockData=data,
            DataLength=524288,
            Checksum=checksum,
            ChecksumAlgorithm="SHA256",
        )

    resp = client.get_snapshot_block(
        SnapshotId=snapshot_id, BlockIndex=2, BlockToken="n/a"
    )

    resp.should.have.key("DataLength").equals(524288)
    resp.should.have.key("BlockData")
    resp["BlockData"].read().should.equal(b"data 2")
    resp.should.have.key("Checksum")
    resp.should.have.key("ChecksumAlgorithm").equals("SHA256")


@mock_ebs
def test_list_changed_blocks():
    client = boto3.client("ebs", region_name="ap-southeast-1")
    snapshot_id1 = client.start_snapshot(VolumeSize=415)["SnapshotId"]
    snapshot_id2 = client.start_snapshot(VolumeSize=415)["SnapshotId"]
    for idx, data in [(1, b"data 1"), (2, b"data 2"), (3, b"data 3")]:
        checksum = hashlib.sha256(data).hexdigest()
        client.put_snapshot_block(
            SnapshotId=snapshot_id1,
            BlockIndex=idx,
            BlockData=data,
            DataLength=524288,
            Checksum=checksum,
            ChecksumAlgorithm="SHA256",
        )
    for idx, data in [(1, b"data 1.1"), (2, b"data 2"), (4, b"data 3.1")]:
        checksum = hashlib.sha256(data).hexdigest()
        client.put_snapshot_block(
            SnapshotId=snapshot_id2,
            BlockIndex=idx,
            BlockData=data,
            DataLength=524288,
            Checksum=checksum,
            ChecksumAlgorithm="SHA256",
        )
    resp = client.list_changed_blocks(
        FirstSnapshotId=snapshot_id1, SecondSnapshotId=snapshot_id2
    )
    changed_blocks = resp["ChangedBlocks"]
    changed_idxes = [b["BlockIndex"] for b in changed_blocks]
    changed_idxes.should.equal([1, 3])

    changed_blocks[0].should.have.key("FirstBlockToken")
    changed_blocks[0].should.have.key("SecondBlockToken")

    changed_blocks[1].should.have.key("FirstBlockToken")
    changed_blocks[1].shouldnt.have.key("SecondBlockToken")


@mock_ebs
def test_list_snapshot_blocks():
    client = boto3.client("ebs", region_name="ap-southeast-1")
    snapshot_id = client.start_snapshot(VolumeSize=415)["SnapshotId"]
    for idx, data in [(1, b"data 1"), (2, b"data 2"), (3, b"data 3")]:
        checksum = hashlib.sha256(data).hexdigest()
        client.put_snapshot_block(
            SnapshotId=snapshot_id,
            BlockIndex=idx,
            BlockData=data,
            DataLength=524288,
            Checksum=checksum,
            ChecksumAlgorithm="SHA256",
        )

    resp = client.list_snapshot_blocks(SnapshotId=snapshot_id)

    resp.should.have.key("VolumeSize").equals(415)
    resp.should.have.key("BlockSize").equals(512)
    resp.should.have.key("Blocks").length_of(3)

    [b["BlockIndex"] for b in resp["Blocks"]].should.equal([1, 2, 3])


@mock_ebs
@mock_ec2
def test_start_snapshot__should_be_created_in_ec2():
    ebs = boto3.client("ebs", region_name="eu-north-1")
    ec2 = boto3.client("ec2", region_name="eu-north-1")
    snapshot_id = ebs.start_snapshot(VolumeSize=720)["SnapshotId"]
    resp = ec2.describe_snapshots(SnapshotIds=[snapshot_id])["Snapshots"]
    resp.should.have.length_of(1)

    resp[0].should.have.key("VolumeSize").equals(720)
