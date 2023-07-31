import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_kinesis
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from .test_kinesis import get_stream_arn


@mock_kinesis
def test_describe_stream_limit_parameter():
    client = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"

    client.create_stream(StreamName=stream_name, ShardCount=5)

    without_filter = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    assert len(without_filter["Shards"]) == 5
    assert without_filter["HasMoreShards"] is False

    with_filter = client.describe_stream(StreamName=stream_name, Limit=2)[
        "StreamDescription"
    ]
    assert len(with_filter["Shards"]) == 2
    assert with_filter["HasMoreShards"] is True

    with_filter = client.describe_stream(StreamName=stream_name, Limit=5)[
        "StreamDescription"
    ]
    assert len(with_filter["Shards"]) == 5
    assert with_filter["HasMoreShards"] is False

    with_filter = client.describe_stream(StreamName=stream_name, Limit=6)[
        "StreamDescription"
    ]
    assert len(with_filter["Shards"]) == 5
    assert with_filter["HasMoreShards"] is False


@mock_kinesis
def test_list_shards():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"

    conn.create_stream(StreamName=stream_name, ShardCount=2)

    # Create some data
    for index in range(1, 100):
        conn.put_record(
            StreamName=stream_name, Data="data:" + str(index), PartitionKey=str(index)
        )

    shard_list = conn.list_shards(StreamName=stream_name)["Shards"]
    assert len(shard_list) == 2
    # Verify IDs
    assert [s["ShardId"] for s in shard_list] == [
        "shardId-000000000000",
        "shardId-000000000001",
    ]
    # Verify hash range
    for shard in shard_list:
        assert "HashKeyRange" in shard
        assert "StartingHashKey" in shard["HashKeyRange"]
        assert "EndingHashKey" in shard["HashKeyRange"]
    assert shard_list[0]["HashKeyRange"]["EndingHashKey"] == str(
        int(shard_list[1]["HashKeyRange"]["StartingHashKey"]) - 1
    )
    # Verify sequence numbers
    for shard in shard_list:
        assert "SequenceNumberRange" in shard
        assert "StartingSequenceNumber" in shard["SequenceNumberRange"]


@mock_kinesis
def test_list_shards_paging():
    client = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    client.create_stream(StreamName=stream_name, ShardCount=10)

    # Get shard 1-10
    shard_list = client.list_shards(StreamName=stream_name)
    assert len(shard_list["Shards"]) == 10
    assert "NextToken" not in shard_list

    # Get shard 1-4
    resp = client.list_shards(StreamName=stream_name, MaxResults=4)
    assert len(resp["Shards"]) == 4
    assert [s["ShardId"] for s in resp["Shards"]] == [
        "shardId-000000000000",
        "shardId-000000000001",
        "shardId-000000000002",
        "shardId-000000000003",
    ]
    assert "NextToken" in resp

    # Get shard 4-8
    resp = client.list_shards(
        StreamName=stream_name, MaxResults=4, NextToken=str(resp["NextToken"])
    )
    assert len(resp["Shards"]) == 4
    assert [s["ShardId"] for s in resp["Shards"]] == [
        "shardId-000000000004",
        "shardId-000000000005",
        "shardId-000000000006",
        "shardId-000000000007",
    ]
    assert "NextToken" in resp

    # Get shard 8-10
    resp = client.list_shards(
        StreamName=stream_name, MaxResults=4, NextToken=str(resp["NextToken"])
    )
    assert len(resp["Shards"]) == 2
    assert [s["ShardId"] for s in resp["Shards"]] == [
        "shardId-000000000008",
        "shardId-000000000009",
    ]
    assert "NextToken" not in resp


@mock_kinesis
def test_create_shard():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)

    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    assert desc["StreamName"] == "my-stream"
    assert (
        desc["StreamARN"] == f"arn:aws:kinesis:us-west-2:{ACCOUNT_ID}:stream/my-stream"
    )
    assert len(desc["Shards"]) == 2
    assert desc["StreamStatus"] == "ACTIVE"
    assert desc["HasMoreShards"] is False
    assert desc["RetentionPeriodHours"] == 24
    assert "StreamCreationTimestamp" in desc
    assert desc["EnhancedMonitoring"] == [{"ShardLevelMetrics": []}]
    assert desc["EncryptionType"] == "NONE"

    shards = desc["Shards"]
    assert shards[0]["ShardId"] == "shardId-000000000000"
    assert "HashKeyRange" in shards[0]
    assert shards[0]["HashKeyRange"]["StartingHashKey"] == "0"
    assert "EndingHashKey" in shards[0]["HashKeyRange"]
    assert "SequenceNumberRange" in shards[0]
    assert "StartingSequenceNumber" in shards[0]["SequenceNumberRange"]
    assert "EndingSequenceNumber" not in shards[0]["SequenceNumberRange"]


@mock_kinesis
def test_split_shard_with_invalid_name():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)

    with pytest.raises(ClientError) as exc:
        client.split_shard(
            StreamName="my-stream",
            ShardToSplit="?",
            NewStartingHashKey="170141183460469231731687303715884105728",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected: Value '?' at 'shardToSplit' failed to satisfy constraint: Member must satisfy regular expression pattern: [a-zA-Z0-9_.-]+"
    )


@mock_kinesis
def test_split_shard_with_unknown_name():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)

    with pytest.raises(ClientError) as exc:
        client.split_shard(
            StreamName="my-stream",
            ShardToSplit="unknown",
            NewStartingHashKey="170141183460469231731687303715884105728",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Could not find shard unknown in stream my-stream under account 123456789012."
    )


@mock_kinesis
def test_split_shard_invalid_hashkey():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)

    with pytest.raises(ClientError) as exc:
        client.split_shard(
            StreamName="my-stream",
            ShardToSplit="shardId-000000000001",
            NewStartingHashKey="sth",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected: Value 'sth' at 'newStartingHashKey' failed to satisfy constraint: Member must satisfy regular expression pattern: 0|([1-9]\\d{0,38})"
    )


@mock_kinesis
def test_split_shard_hashkey_out_of_bounds():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)

    with pytest.raises(ClientError) as exc:
        client.split_shard(
            StreamName="my-stream",
            ShardToSplit="shardId-000000000001",
            NewStartingHashKey="170141183460469231731687303715884000000",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        err["Message"]
        == f"NewStartingHashKey 170141183460469231731687303715884000000 used in SplitShard() on shard shardId-000000000001 in stream my-stream under account {ACCOUNT_ID} is not both greater than one plus the shard's StartingHashKey 170141183460469231731687303715884105728 and less than the shard's EndingHashKey 340282366920938463463374607431768211455."
    )


@mock_kinesis
def test_split_shard():
    client = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my-stream"
    client.create_stream(StreamName=stream_name, ShardCount=2)

    for index in range(1, 100):
        client.put_record(
            StreamName=stream_name,
            Data=f"data_{index}".encode("utf-8"),
            PartitionKey=str(index),
        )

    original_shards = client.describe_stream(StreamName=stream_name)[
        "StreamDescription"
    ]["Shards"]

    client.split_shard(
        StreamName=stream_name,
        ShardToSplit="shardId-000000000001",
        NewStartingHashKey="170141183460469231731687303715884105829",
    )

    resp = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shards = resp["Shards"]
    assert len(shards) == 4
    assert shards[0]["ShardId"] == "shardId-000000000000"
    assert "HashKeyRange" in shards[0]
    assert "ParentShardId" not in shards[0]

    assert shards[1]["ShardId"] == "shardId-000000000001"
    assert "ParentShardId" not in shards[1]
    assert "HashKeyRange" in shards[1]
    assert (
        shards[1]["HashKeyRange"]["StartingHashKey"]
        == original_shards[1]["HashKeyRange"]["StartingHashKey"]
    )
    assert (
        shards[1]["HashKeyRange"]["EndingHashKey"]
        == original_shards[1]["HashKeyRange"]["EndingHashKey"]
    )
    assert "StartingSequenceNumber" in shards[1]["SequenceNumberRange"]
    assert "EndingSequenceNumber" in shards[1]["SequenceNumberRange"]

    assert shards[2]["ShardId"] == "shardId-000000000002"
    assert shards[2]["ParentShardId"] == shards[1]["ShardId"]
    assert "StartingSequenceNumber" in shards[2]["SequenceNumberRange"]
    assert "EndingSequenceNumber" not in shards[2]["SequenceNumberRange"]

    assert shards[3]["ShardId"] == "shardId-000000000003"
    assert shards[3]["ParentShardId"] == shards[1]["ShardId"]
    assert "StartingSequenceNumber" in shards[3]["SequenceNumberRange"]
    assert "EndingSequenceNumber" not in shards[3]["SequenceNumberRange"]


@mock_kinesis
def test_split_shard_that_was_split_before():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)
    stream_arn = get_stream_arn(client, "my-stream")

    client.split_shard(
        StreamARN=stream_arn,
        ShardToSplit="shardId-000000000001",
        NewStartingHashKey="170141183460469231731687303715884105829",
    )

    with pytest.raises(ClientError) as exc:
        client.split_shard(
            StreamName="my-stream",
            ShardToSplit="shardId-000000000001",
            NewStartingHashKey="170141183460469231731687303715884105829",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        err["Message"]
        == f"Shard shardId-000000000001 in stream my-stream under account {ACCOUNT_ID} has already been merged or split, and thus is not eligible for merging or splitting."
    )


@mock_kinesis
@pytest.mark.parametrize(
    "initial,target,expected_total",
    [(2, 4, 6), (4, 5, 15), (10, 13, 37), (4, 2, 6), (5, 3, 7), (10, 3, 17)],
)
def test_update_shard_count(initial, target, expected_total):
    """
    Test that we update the shard count in a similar manner to AWS
    Assert on: initial_shard_count, target_shard_count and total_shard_count

    total_shard_count gives an idea of the number of splits/merges required to reach the target

    These numbers have been verified against AWS
    """
    client = boto3.client("kinesis", region_name="eu-west-1")
    client.create_stream(StreamName="my-stream", ShardCount=initial)

    resp = client.update_shard_count(
        StreamName="my-stream", TargetShardCount=target, ScalingType="UNIFORM_SCALING"
    )

    assert resp["StreamName"] == "my-stream"
    assert resp["CurrentShardCount"] == initial
    assert resp["TargetShardCount"] == target

    stream = client.describe_stream(StreamName="my-stream")["StreamDescription"]
    assert stream["StreamStatus"] == "ACTIVE"
    assert len(stream["Shards"]) == expected_total

    active_shards = [
        shard
        for shard in stream["Shards"]
        if "EndingSequenceNumber" not in shard["SequenceNumberRange"]
    ]
    assert len(active_shards) == target

    resp = client.describe_stream_summary(StreamName="my-stream")
    stream = resp["StreamDescriptionSummary"]

    assert stream["OpenShardCount"] == target
