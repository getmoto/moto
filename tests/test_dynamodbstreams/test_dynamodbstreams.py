from __future__ import print_function

import pytest

import boto3
from moto import mock_dynamodb2, mock_dynamodbstreams


class TestCore:
    stream_arn = None
    mocks = []

    def setup(self):
        self.mocks = [mock_dynamodb2(), mock_dynamodbstreams()]
        for m in self.mocks:
            m.start()

        # create a table with a stream
        conn = boto3.client("dynamodb", region_name="us-east-1")

        resp = conn.create_table(
            TableName="test-streams",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
            StreamSpecification={
                "StreamEnabled": True,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
        )
        self.stream_arn = resp["TableDescription"]["LatestStreamArn"]

    def teardown(self):
        conn = boto3.client("dynamodb", region_name="us-east-1")
        conn.delete_table(TableName="test-streams")
        self.stream_arn = None

        for m in self.mocks:
            try:
                m.stop()
            except RuntimeError:
                pass

    def test_verify_stream(self):
        conn = boto3.client("dynamodb", region_name="us-east-1")
        resp = conn.describe_table(TableName="test-streams")
        assert "LatestStreamArn" in resp["Table"]

    def test_describe_stream(self):
        conn = boto3.client("dynamodbstreams", region_name="us-east-1")

        resp = conn.describe_stream(StreamArn=self.stream_arn)
        assert "StreamDescription" in resp
        desc = resp["StreamDescription"]
        assert desc["StreamArn"] == self.stream_arn
        assert desc["TableName"] == "test-streams"

    def test_list_streams(self):
        conn = boto3.client("dynamodbstreams", region_name="us-east-1")

        resp = conn.list_streams()
        assert resp["Streams"][0]["StreamArn"] == self.stream_arn

        resp = conn.list_streams(TableName="no-stream")
        assert not resp["Streams"]

    def test_get_shard_iterator(self):
        conn = boto3.client("dynamodbstreams", region_name="us-east-1")

        resp = conn.describe_stream(StreamArn=self.stream_arn)
        shard_id = resp["StreamDescription"]["Shards"][0]["ShardId"]

        resp = conn.get_shard_iterator(
            StreamArn=self.stream_arn,
            ShardId=shard_id,
            ShardIteratorType="TRIM_HORIZON",
        )
        assert "ShardIterator" in resp

    def test_get_shard_iterator_at_sequence_number(self):
        conn = boto3.client("dynamodbstreams", region_name="us-east-1")

        resp = conn.describe_stream(StreamArn=self.stream_arn)
        shard_id = resp["StreamDescription"]["Shards"][0]["ShardId"]

        resp = conn.get_shard_iterator(
            StreamArn=self.stream_arn,
            ShardId=shard_id,
            ShardIteratorType="AT_SEQUENCE_NUMBER",
            SequenceNumber=resp["StreamDescription"]["Shards"][0][
                "SequenceNumberRange"
            ]["StartingSequenceNumber"],
        )
        assert "ShardIterator" in resp

    def test_get_shard_iterator_after_sequence_number(self):
        conn = boto3.client("dynamodbstreams", region_name="us-east-1")

        resp = conn.describe_stream(StreamArn=self.stream_arn)
        shard_id = resp["StreamDescription"]["Shards"][0]["ShardId"]

        resp = conn.get_shard_iterator(
            StreamArn=self.stream_arn,
            ShardId=shard_id,
            ShardIteratorType="AFTER_SEQUENCE_NUMBER",
            SequenceNumber=resp["StreamDescription"]["Shards"][0][
                "SequenceNumberRange"
            ]["StartingSequenceNumber"],
        )
        assert "ShardIterator" in resp

    def test_get_records_empty(self):
        conn = boto3.client("dynamodbstreams", region_name="us-east-1")

        resp = conn.describe_stream(StreamArn=self.stream_arn)
        shard_id = resp["StreamDescription"]["Shards"][0]["ShardId"]

        resp = conn.get_shard_iterator(
            StreamArn=self.stream_arn, ShardId=shard_id, ShardIteratorType="LATEST"
        )
        iterator_id = resp["ShardIterator"]

        resp = conn.get_records(ShardIterator=iterator_id)
        assert "Records" in resp
        assert len(resp["Records"]) == 0

    def test_get_records_seq(self):
        conn = boto3.client("dynamodb", region_name="us-east-1")

        conn.put_item(
            TableName="test-streams",
            Item={"id": {"S": "entry1"}, "first_col": {"S": "foo"}},
        )
        conn.put_item(
            TableName="test-streams",
            Item={
                "id": {"S": "entry1"},
                "first_col": {"S": "bar"},
                "second_col": {"S": "baz"},
                "a": {"L": [{"M": {"b": {"S": "bar1"}}}]},
            },
        )
        conn.delete_item(TableName="test-streams", Key={"id": {"S": "entry1"}})

        conn = boto3.client("dynamodbstreams", region_name="us-east-1")

        resp = conn.describe_stream(StreamArn=self.stream_arn)
        shard_id = resp["StreamDescription"]["Shards"][0]["ShardId"]

        resp = conn.get_shard_iterator(
            StreamArn=self.stream_arn,
            ShardId=shard_id,
            ShardIteratorType="TRIM_HORIZON",
        )
        iterator_id = resp["ShardIterator"]

        resp = conn.get_records(ShardIterator=iterator_id)
        assert len(resp["Records"]) == 3
        assert resp["Records"][0]["eventName"] == "INSERT"
        assert resp["Records"][1]["eventName"] == "MODIFY"
        assert resp["Records"][2]["eventName"] == "REMOVE"

        sequence_number_modify = resp["Records"][1]["dynamodb"]["SequenceNumber"]

        # now try fetching from the next shard iterator, it should be
        # empty
        resp = conn.get_records(ShardIterator=resp["NextShardIterator"])
        assert len(resp["Records"]) == 0

        # check that if we get the shard iterator AT_SEQUENCE_NUMBER will get the MODIFY event
        resp = conn.get_shard_iterator(
            StreamArn=self.stream_arn,
            ShardId=shard_id,
            ShardIteratorType="AT_SEQUENCE_NUMBER",
            SequenceNumber=sequence_number_modify,
        )
        iterator_id = resp["ShardIterator"]
        resp = conn.get_records(ShardIterator=iterator_id)
        assert len(resp["Records"]) == 2
        assert resp["Records"][0]["eventName"] == "MODIFY"
        assert resp["Records"][1]["eventName"] == "REMOVE"

        # check that if we get the shard iterator AFTER_SEQUENCE_NUMBER will get the DELETE event
        resp = conn.get_shard_iterator(
            StreamArn=self.stream_arn,
            ShardId=shard_id,
            ShardIteratorType="AFTER_SEQUENCE_NUMBER",
            SequenceNumber=sequence_number_modify,
        )
        iterator_id = resp["ShardIterator"]
        resp = conn.get_records(ShardIterator=iterator_id)
        assert len(resp["Records"]) == 1
        assert resp["Records"][0]["eventName"] == "REMOVE"


class TestEdges:
    mocks = []

    def setup(self):
        self.mocks = [mock_dynamodb2(), mock_dynamodbstreams()]
        for m in self.mocks:
            m.start()

    def teardown(self):
        for m in self.mocks:
            try:
                m.stop()
            except RuntimeError:
                pass

    def test_enable_stream_on_table(self):
        conn = boto3.client("dynamodb", region_name="us-east-1")
        resp = conn.create_table(
            TableName="test-streams",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        assert "StreamSpecification" not in resp["TableDescription"]

        resp = conn.update_table(
            TableName="test-streams",
            StreamSpecification={"StreamViewType": "KEYS_ONLY", "StreamEnabled": True},
        )
        assert "StreamSpecification" in resp["TableDescription"]
        assert resp["TableDescription"]["StreamSpecification"] == {
            "StreamEnabled": True,
            "StreamViewType": "KEYS_ONLY",
        }
        assert "LatestStreamLabel" in resp["TableDescription"]

        # now try to enable it again
        with pytest.raises(conn.exceptions.ResourceInUseException):
            resp = conn.update_table(
                TableName="test-streams",
                StreamSpecification={
                    "StreamViewType": "OLD_IMAGES",
                    "StreamEnabled": True,
                },
            )

    def test_stream_with_range_key(self):
        dyn = boto3.client("dynamodb", region_name="us-east-1")

        resp = dyn.create_table(
            TableName="test-streams",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"},
                {"AttributeName": "color", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "color", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
            StreamSpecification={"StreamViewType": "NEW_IMAGES", "StreamEnabled": True},
        )
        stream_arn = resp["TableDescription"]["LatestStreamArn"]

        streams = boto3.client("dynamodbstreams", region_name="us-east-1")
        resp = streams.describe_stream(StreamArn=stream_arn)
        shard_id = resp["StreamDescription"]["Shards"][0]["ShardId"]

        resp = streams.get_shard_iterator(
            StreamArn=stream_arn, ShardId=shard_id, ShardIteratorType="LATEST"
        )
        iterator_id = resp["ShardIterator"]

        dyn.put_item(
            TableName="test-streams", Item={"id": {"S": "row1"}, "color": {"S": "blue"}}
        )
        dyn.put_item(
            TableName="test-streams",
            Item={"id": {"S": "row2"}, "color": {"S": "green"}},
        )

        resp = streams.get_records(ShardIterator=iterator_id)
        assert len(resp["Records"]) == 2
        assert resp["Records"][0]["eventName"] == "INSERT"
        assert resp["Records"][1]["eventName"] == "INSERT"
