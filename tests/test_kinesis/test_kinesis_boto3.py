import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_kinesis
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from .test_kinesis import get_stream_arn

import sure  # noqa # pylint: disable=unused-import


@mock_kinesis
def test_describe_stream_limit_parameter():
    client = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"

    client.create_stream(StreamName=stream_name, ShardCount=5)

    without_filter = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    without_filter["Shards"].should.have.length_of(5)
    without_filter["HasMoreShards"].should.equal(False)

    with_filter = client.describe_stream(StreamName=stream_name, Limit=2)[
        "StreamDescription"
    ]
    with_filter["Shards"].should.have.length_of(2)
    with_filter["HasMoreShards"].should.equal(True)

    with_filter = client.describe_stream(StreamName=stream_name, Limit=5)[
        "StreamDescription"
    ]
    with_filter["Shards"].should.have.length_of(5)
    with_filter["HasMoreShards"].should.equal(False)

    with_filter = client.describe_stream(StreamName=stream_name, Limit=6)[
        "StreamDescription"
    ]
    with_filter["Shards"].should.have.length_of(5)
    with_filter["HasMoreShards"].should.equal(False)


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
    shard_list.should.have.length_of(2)
    # Verify IDs
    [s["ShardId"] for s in shard_list].should.equal(
        ["shardId-000000000000", "shardId-000000000001"]
    )
    # Verify hash range
    for shard in shard_list:
        shard.should.have.key("HashKeyRange")
        shard["HashKeyRange"].should.have.key("StartingHashKey")
        shard["HashKeyRange"].should.have.key("EndingHashKey")
    shard_list[0]["HashKeyRange"]["EndingHashKey"].should.equal(
        str(int(shard_list[1]["HashKeyRange"]["StartingHashKey"]) - 1)
    )
    # Verify sequence numbers
    for shard in shard_list:
        shard.should.have.key("SequenceNumberRange")
        shard["SequenceNumberRange"].should.have.key("StartingSequenceNumber")


@mock_kinesis
def test_list_shards_paging():
    client = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"
    client.create_stream(StreamName=stream_name, ShardCount=10)

    # Get shard 1-10
    shard_list = client.list_shards(StreamName=stream_name)
    shard_list["Shards"].should.have.length_of(10)
    shard_list.should_not.have.key("NextToken")

    # Get shard 1-4
    resp = client.list_shards(StreamName=stream_name, MaxResults=4)
    resp["Shards"].should.have.length_of(4)
    [s["ShardId"] for s in resp["Shards"]].should.equal(
        [
            "shardId-000000000000",
            "shardId-000000000001",
            "shardId-000000000002",
            "shardId-000000000003",
        ]
    )
    resp.should.have.key("NextToken")

    # Get shard 4-8
    resp = client.list_shards(
        StreamName=stream_name, MaxResults=4, NextToken=str(resp["NextToken"])
    )
    resp["Shards"].should.have.length_of(4)
    [s["ShardId"] for s in resp["Shards"]].should.equal(
        [
            "shardId-000000000004",
            "shardId-000000000005",
            "shardId-000000000006",
            "shardId-000000000007",
        ]
    )
    resp.should.have.key("NextToken")

    # Get shard 8-10
    resp = client.list_shards(
        StreamName=stream_name, MaxResults=4, NextToken=str(resp["NextToken"])
    )
    resp["Shards"].should.have.length_of(2)
    [s["ShardId"] for s in resp["Shards"]].should.equal(
        ["shardId-000000000008", "shardId-000000000009"]
    )
    resp.should_not.have.key("NextToken")


@mock_kinesis
def test_create_shard():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)

    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    desc.should.have.key("StreamName").equal("my-stream")
    desc.should.have.key("StreamARN").equal(
        f"arn:aws:kinesis:us-west-2:{ACCOUNT_ID}:stream/my-stream"
    )
    desc.should.have.key("Shards").length_of(2)
    desc.should.have.key("StreamStatus").equals("ACTIVE")
    desc.should.have.key("HasMoreShards").equals(False)
    desc.should.have.key("RetentionPeriodHours").equals(24)
    desc.should.have.key("StreamCreationTimestamp")
    desc.should.have.key("EnhancedMonitoring").should.equal([{"ShardLevelMetrics": []}])
    desc.should.have.key("EncryptionType").should.equal("NONE")

    shards = desc["Shards"]
    shards[0].should.have.key("ShardId").equal("shardId-000000000000")
    shards[0].should.have.key("HashKeyRange")
    shards[0]["HashKeyRange"].should.have.key("StartingHashKey").equals("0")
    shards[0]["HashKeyRange"].should.have.key("EndingHashKey")
    shards[0].should.have.key("SequenceNumberRange")
    shards[0]["SequenceNumberRange"].should.have.key("StartingSequenceNumber")
    shards[0]["SequenceNumberRange"].shouldnt.have.key("EndingSequenceNumber")


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
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "1 validation error detected: Value '?' at 'shardToSplit' failed to satisfy constraint: Member must satisfy regular expression pattern: [a-zA-Z0-9_.-]+"
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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(
        "Could not find shard unknown in stream my-stream under account 123456789012."
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
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "1 validation error detected: Value 'sth' at 'newStartingHashKey' failed to satisfy constraint: Member must satisfy regular expression pattern: 0|([1-9]\\d{0,38})"
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
    err["Code"].should.equal("InvalidArgumentException")
    err["Message"].should.equal(
        f"NewStartingHashKey 170141183460469231731687303715884000000 used in SplitShard() on shard shardId-000000000001 in stream my-stream under account {ACCOUNT_ID} is not both greater than one plus the shard's StartingHashKey 170141183460469231731687303715884105728 and less than the shard's EndingHashKey 340282366920938463463374607431768211455."
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
    shards.should.have.length_of(4)
    shards[0].should.have.key("ShardId").equals("shardId-000000000000")
    shards[0].should.have.key("HashKeyRange")
    shards[0].shouldnt.have.key("ParentShardId")

    shards[1].should.have.key("ShardId").equals("shardId-000000000001")
    shards[1].shouldnt.have.key("ParentShardId")
    shards[1].should.have.key("HashKeyRange")
    shards[1]["HashKeyRange"].should.have.key("StartingHashKey").equals(
        original_shards[1]["HashKeyRange"]["StartingHashKey"]
    )
    shards[1]["HashKeyRange"].should.have.key("EndingHashKey").equals(
        original_shards[1]["HashKeyRange"]["EndingHashKey"]
    )
    shards[1]["SequenceNumberRange"].should.have.key("StartingSequenceNumber")
    shards[1]["SequenceNumberRange"].should.have.key("EndingSequenceNumber")

    shards[2].should.have.key("ShardId").equals("shardId-000000000002")
    shards[2].should.have.key("ParentShardId").equals(shards[1]["ShardId"])
    shards[2]["SequenceNumberRange"].should.have.key("StartingSequenceNumber")
    shards[2]["SequenceNumberRange"].shouldnt.have.key("EndingSequenceNumber")

    shards[3].should.have.key("ShardId").equals("shardId-000000000003")
    shards[3].should.have.key("ParentShardId").equals(shards[1]["ShardId"])
    shards[3]["SequenceNumberRange"].should.have.key("StartingSequenceNumber")
    shards[3]["SequenceNumberRange"].shouldnt.have.key("EndingSequenceNumber")


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
    err["Code"].should.equal("InvalidArgumentException")
    err["Message"].should.equal(
        f"Shard shardId-000000000001 in stream my-stream under account {ACCOUNT_ID} has already been merged or split, and thus is not eligible for merging or splitting."
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

    resp.should.have.key("StreamName").equals("my-stream")
    resp.should.have.key("CurrentShardCount").equals(initial)
    resp.should.have.key("TargetShardCount").equals(target)

    stream = client.describe_stream(StreamName="my-stream")["StreamDescription"]
    stream["StreamStatus"].should.equal("ACTIVE")
    stream["Shards"].should.have.length_of(expected_total)

    active_shards = [
        shard
        for shard in stream["Shards"]
        if "EndingSequenceNumber" not in shard["SequenceNumberRange"]
    ]
    active_shards.should.have.length_of(target)

    resp = client.describe_stream_summary(StreamName="my-stream")
    stream = resp["StreamDescriptionSummary"]

    stream["OpenShardCount"].should.equal(target)
