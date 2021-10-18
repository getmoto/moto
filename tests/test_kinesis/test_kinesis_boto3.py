import boto3

from moto import mock_kinesis

import sure  # noqa


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
def test_split_shard():
    conn = boto3.client("kinesis", region_name="us-west-2")
    stream_name = "my_stream"

    conn.create_stream(StreamName=stream_name, ShardCount=2)

    # Create some data
    for index in range(1, 100):
        conn.put_record(
            StreamName=stream_name, Data="data:" + str(index), PartitionKey=str(index)
        )

    stream_response = conn.describe_stream(StreamName=stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(2)

    shard_range = shards[0]["HashKeyRange"]
    new_starting_hash = (
        int(shard_range["EndingHashKey"]) + int(shard_range["StartingHashKey"])
    ) // 2
    conn.split_shard(
        StreamName=stream_name,
        ShardToSplit=shards[0]["ShardId"],
        NewStartingHashKey=str(new_starting_hash),
    )

    stream_response = conn.describe_stream(StreamName=stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(3)

    shard_range = shards[2]["HashKeyRange"]
    new_starting_hash = (
        int(shard_range["EndingHashKey"]) + int(shard_range["StartingHashKey"])
    ) // 2
    conn.split_shard(
        StreamName=stream_name,
        ShardToSplit=shards[2]["ShardId"],
        NewStartingHashKey=str(new_starting_hash),
    )

    stream_response = conn.describe_stream(StreamName=stream_name)

    stream = stream_response["StreamDescription"]
    shards = stream["Shards"]
    shards.should.have.length_of(4)


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
        shard_list[1]["HashKeyRange"]["StartingHashKey"]
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
