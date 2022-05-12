import boto3

from moto import mock_kinesis


@mock_kinesis
def test_enable_enhanced_monitoring_all():
    client = boto3.client("kinesis", region_name="us-east-1")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=4)

    resp = client.enable_enhanced_monitoring(
        StreamName=stream_name, ShardLevelMetrics=["ALL"]
    )

    resp.should.have.key("StreamName").equals(stream_name)
    resp.should.have.key("CurrentShardLevelMetrics").equals([])
    resp.should.have.key("DesiredShardLevelMetrics").equals(["ALL"])


@mock_kinesis
def test_enable_enhanced_monitoring_is_persisted():
    client = boto3.client("kinesis", region_name="us-east-1")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=4)

    client.enable_enhanced_monitoring(
        StreamName=stream_name, ShardLevelMetrics=["IncomingBytes", "OutgoingBytes"]
    )

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    metrics = stream["EnhancedMonitoring"][0]["ShardLevelMetrics"]
    set(metrics).should.equal({"IncomingBytes", "OutgoingBytes"})


@mock_kinesis
def test_enable_enhanced_monitoring_in_steps():
    client = boto3.client("kinesis", region_name="us-east-1")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=4)

    client.enable_enhanced_monitoring(
        StreamName=stream_name, ShardLevelMetrics=["IncomingBytes", "OutgoingBytes"]
    )

    resp = client.enable_enhanced_monitoring(
        StreamName=stream_name, ShardLevelMetrics=["WriteProvisionedThroughputExceeded"]
    )

    resp.should.have.key("CurrentShardLevelMetrics").should.have.length_of(2)
    resp["CurrentShardLevelMetrics"].should.contain("IncomingBytes")
    resp["CurrentShardLevelMetrics"].should.contain("OutgoingBytes")
    resp.should.have.key("DesiredShardLevelMetrics").should.have.length_of(3)
    resp["DesiredShardLevelMetrics"].should.contain("IncomingBytes")
    resp["DesiredShardLevelMetrics"].should.contain("OutgoingBytes")
    resp["DesiredShardLevelMetrics"].should.contain(
        "WriteProvisionedThroughputExceeded"
    )

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    metrics = stream["EnhancedMonitoring"][0]["ShardLevelMetrics"]
    metrics.should.have.length_of(3)
    metrics.should.contain("IncomingBytes")
    metrics.should.contain("OutgoingBytes")
    metrics.should.contain("WriteProvisionedThroughputExceeded")


@mock_kinesis
def test_disable_enhanced_monitoring():
    client = boto3.client("kinesis", region_name="us-east-1")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=4)

    client.enable_enhanced_monitoring(
        StreamName=stream_name,
        ShardLevelMetrics=[
            "IncomingBytes",
            "OutgoingBytes",
            "WriteProvisionedThroughputExceeded",
        ],
    )

    resp = client.disable_enhanced_monitoring(
        StreamName=stream_name, ShardLevelMetrics=["OutgoingBytes"]
    )

    resp.should.have.key("CurrentShardLevelMetrics").should.have.length_of(3)
    resp["CurrentShardLevelMetrics"].should.contain("IncomingBytes")
    resp["CurrentShardLevelMetrics"].should.contain("OutgoingBytes")
    resp["CurrentShardLevelMetrics"].should.contain(
        "WriteProvisionedThroughputExceeded"
    )
    resp.should.have.key("DesiredShardLevelMetrics").should.have.length_of(2)
    resp["DesiredShardLevelMetrics"].should.contain("IncomingBytes")
    resp["DesiredShardLevelMetrics"].should.contain(
        "WriteProvisionedThroughputExceeded"
    )

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    metrics = stream["EnhancedMonitoring"][0]["ShardLevelMetrics"]
    metrics.should.have.length_of(2)
    metrics.should.contain("IncomingBytes")
    metrics.should.contain("WriteProvisionedThroughputExceeded")


@mock_kinesis
def test_disable_enhanced_monitoring_all():
    client = boto3.client("kinesis", region_name="us-east-1")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=4)

    client.enable_enhanced_monitoring(
        StreamName=stream_name,
        ShardLevelMetrics=[
            "IncomingBytes",
            "OutgoingBytes",
            "WriteProvisionedThroughputExceeded",
        ],
    )

    client.disable_enhanced_monitoring(
        StreamName=stream_name, ShardLevelMetrics=["ALL"]
    )

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    metrics = stream["EnhancedMonitoring"][0]["ShardLevelMetrics"]
    metrics.should.equal([])
