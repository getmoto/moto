"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import json
from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_kinesis import KinesisClient, KinesisConfig
    from aws_sdk_kinesis.models import ResourceNotFoundException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-kinesis is not installed", allow_module_level=True)


@pytest.mark.skip(
    reason="Moto ignores the Tags-parameter of CreateStream, so ListTagsForStream returns no tags"
)
@mock_aws
def test_clickstream():
    """Publish click events to a stream, and read them back from the shard."""
    config = KinesisConfig.resolve(region="us-east-1")
    stream_name = f"clickstream-{uuid4()}"

    with KinesisClient(config=config) as client:
        client.create_stream(
            stream_name=stream_name, shard_count=1, tags={"team": "analytics"}
        )
        summary = client.describe_stream_summary(
            stream_name=stream_name
        ).stream_description_summary
        assert summary.stream_status == "ACTIVE"
        assert summary.open_shard_count == 1
        assert summary.retention_period_hours == 24
        stream_arn = summary.stream_arn

        client.increase_stream_retention_period(
            stream_name=stream_name, retention_period_hours=48
        )

        first = client.put_record(
            stream_name=stream_name,
            data=json.dumps({"user": "alice", "page": "/home"}).encode(),
            partition_key="alice",
        )
        batch = client.put_records(
            stream_arn=stream_arn,
            records=[
                {
                    "data": json.dumps({"user": user, "page": page}).encode(),
                    "partition_key": user,
                }
                for user, page in [("bob", "/cart"), ("alice", "/checkout")]
            ],
        )
        assert batch.failed_record_count == 0
        assert len(batch.records) == 2

        shards = client.list_shards(stream_name=stream_name).shards
        assert [shard.shard_id for shard in shards] == [first.shard_id]

        iterator = client.get_shard_iterator(
            stream_name=stream_name,
            shard_id=first.shard_id,
            shard_iterator_type="TRIM_HORIZON",
        ).shard_iterator
        records = client.get_records(shard_iterator=iterator, limit=10).records
        assert [json.loads(record.data) for record in records] == [
            {"user": "alice", "page": "/home"},
            {"user": "bob", "page": "/cart"},
            {"user": "alice", "page": "/checkout"},
        ]
        assert records[0].sequence_number == first.sequence_number
        assert records[0].partition_key == "alice"

        summary = client.describe_stream_summary(
            stream_name=stream_name
        ).stream_description_summary
        assert summary.retention_period_hours == 48
        tags = client.list_tags_for_stream(stream_name=stream_name).tags
        assert [(tag.key, tag.value) for tag in tags] == [("team", "analytics")]

        client.delete_stream(stream_name=stream_name)
        with pytest.raises(ResourceNotFoundException):
            client.describe_stream_summary(stream_name=stream_name)
