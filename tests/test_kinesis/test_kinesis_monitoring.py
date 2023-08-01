import boto3

from moto import mock_kinesis
from tests import DEFAULT_ACCOUNT_ID
from .test_kinesis import get_stream_arn


@mock_kinesis
def test_enable_enhanced_monitoring_all():
    client = boto3.client("kinesis", region_name="us-east-1")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=4)

    resp = client.enable_enhanced_monitoring(
        StreamName=stream_name, ShardLevelMetrics=["ALL"]
    )

    assert resp["StreamName"] == stream_name
    assert resp["CurrentShardLevelMetrics"] == []
    assert resp["DesiredShardLevelMetrics"] == ["ALL"]
    assert (
        resp["StreamARN"]
        == f"arn:aws:kinesis:us-east-1:{DEFAULT_ACCOUNT_ID}:stream/{stream_name}"
    )


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
    assert set(metrics) == {"IncomingBytes", "OutgoingBytes"}


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

    assert len(resp["CurrentShardLevelMetrics"]) == 2
    assert "IncomingBytes" in resp["CurrentShardLevelMetrics"]
    assert "OutgoingBytes" in resp["CurrentShardLevelMetrics"]
    assert len(resp["DesiredShardLevelMetrics"]) == 3
    assert "IncomingBytes" in resp["DesiredShardLevelMetrics"]
    assert "OutgoingBytes" in resp["DesiredShardLevelMetrics"]
    assert "WriteProvisionedThroughputExceeded" in resp["DesiredShardLevelMetrics"]

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    metrics = stream["EnhancedMonitoring"][0]["ShardLevelMetrics"]
    assert len(metrics) == 3
    assert "IncomingBytes" in metrics
    assert "OutgoingBytes" in metrics
    assert "WriteProvisionedThroughputExceeded" in metrics


@mock_kinesis
def test_disable_enhanced_monitoring():
    client = boto3.client("kinesis", region_name="us-east-1")
    stream_name = "my_stream_summary"
    client.create_stream(StreamName=stream_name, ShardCount=4)
    stream_arn = get_stream_arn(client, stream_name)

    client.enable_enhanced_monitoring(
        StreamARN=stream_arn,
        ShardLevelMetrics=[
            "IncomingBytes",
            "OutgoingBytes",
            "WriteProvisionedThroughputExceeded",
        ],
    )

    resp = client.disable_enhanced_monitoring(
        StreamName=stream_name, ShardLevelMetrics=["OutgoingBytes"]
    )

    assert resp["StreamName"] == stream_name
    assert (
        resp["StreamARN"]
        == f"arn:aws:kinesis:us-east-1:{DEFAULT_ACCOUNT_ID}:stream/{stream_name}"
    )

    assert len(resp["CurrentShardLevelMetrics"]) == 3
    assert "IncomingBytes" in resp["CurrentShardLevelMetrics"]
    assert "OutgoingBytes" in resp["CurrentShardLevelMetrics"]
    assert "WriteProvisionedThroughputExceeded" in resp["CurrentShardLevelMetrics"]
    assert len(resp["DesiredShardLevelMetrics"]) == 2
    assert "IncomingBytes" in resp["DesiredShardLevelMetrics"]
    assert "WriteProvisionedThroughputExceeded" in resp["DesiredShardLevelMetrics"]

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    metrics = stream["EnhancedMonitoring"][0]["ShardLevelMetrics"]
    assert len(metrics) == 2
    assert "IncomingBytes" in metrics
    assert "WriteProvisionedThroughputExceeded" in metrics

    resp = client.disable_enhanced_monitoring(
        StreamARN=stream_arn, ShardLevelMetrics=["IncomingBytes"]
    )

    assert len(resp["CurrentShardLevelMetrics"]) == 2
    assert len(resp["DesiredShardLevelMetrics"]) == 1


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
    assert metrics == []
