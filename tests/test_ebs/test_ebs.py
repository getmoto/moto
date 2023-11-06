import hashlib

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_start_snapshot__minimal():
    client = boto3.client("ebs", region_name="eu-west-1")
    resp = client.start_snapshot(VolumeSize=720)

    assert "SnapshotId" in resp
    assert resp["OwnerId"] == ACCOUNT_ID
    assert resp["Status"] == "pending"
    assert "StartTime" in resp
    assert resp["VolumeSize"] == 720
    assert resp["BlockSize"] == 512


@mock_aws
def test_start_snapshot():
    client = boto3.client("ebs", region_name="eu-west-1")
    resp = client.start_snapshot(
        VolumeSize=120,
        Tags=[{"Key": "kt", "Value": "vt"}],
        Description="my fancy snapshot",
    )

    assert "SnapshotId" in resp
    assert resp["OwnerId"] == ACCOUNT_ID
    assert resp["Status"] == "pending"
    assert "StartTime" in resp
    assert resp["VolumeSize"] == 120
    assert resp["BlockSize"] == 512
    assert resp["Tags"] == [{"Key": "kt", "Value": "vt"}]
    assert resp["Description"] == "my fancy snapshot"


@mock_aws
def test_complete_snapshot():
    client = boto3.client("ebs", region_name="ap-southeast-1")
    snapshot_id = client.start_snapshot(VolumeSize=720)["SnapshotId"]

    resp = client.complete_snapshot(SnapshotId=snapshot_id, ChangedBlocksCount=0)
    assert resp["Status"] == "completed"


@mock_aws
def test_put_snapshot_block():
    data = b"data for this specific block\xbf"
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

    assert resp["Checksum"] == checksum
    assert resp["ChecksumAlgorithm"] == "SHA256"


@mock_aws
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

    assert resp["DataLength"] == 524288
    assert "BlockData" in resp
    assert resp["BlockData"].read() == b"data 2"
    assert "Checksum" in resp
    assert resp["ChecksumAlgorithm"] == "SHA256"


@mock_aws
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
    assert changed_idxes == [1, 3]

    assert "FirstBlockToken" in changed_blocks[0]
    assert "SecondBlockToken" in changed_blocks[0]

    assert "FirstBlockToken" in changed_blocks[1]
    assert "SecondBlockToken" not in changed_blocks[1]


@mock_aws
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

    assert resp["VolumeSize"] == 415
    assert resp["BlockSize"] == 512
    assert len(resp["Blocks"]) == 3

    assert [b["BlockIndex"] for b in resp["Blocks"]] == [1, 2, 3]


@mock_aws
def test_start_snapshot__should_be_created_in_ec2():
    ebs = boto3.client("ebs", region_name="eu-north-1")
    ec2 = boto3.client("ec2", region_name="eu-north-1")
    snapshot_id = ebs.start_snapshot(VolumeSize=720)["SnapshotId"]
    resp = ec2.describe_snapshots(SnapshotIds=[snapshot_id])["Snapshots"]
    assert len(resp) == 1

    assert resp[0]["VolumeSize"] == 720
