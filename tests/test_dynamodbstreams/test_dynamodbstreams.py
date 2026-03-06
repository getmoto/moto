import boto3
import pytest

from moto import mock_aws


class TestCore:
    stream_arn = None
    mocks = []

    def setup_method(self):
        self.mock = mock_aws()
        self.mock.start()

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

    def teardown_method(self):
        conn = boto3.client("dynamodb", region_name="us-east-1")
        conn.delete_table(TableName="test-streams")
        self.stream_arn = None

        try:
            self.mock.stop()
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

    def setup_method(self):
        self.mock = mock_aws()
        self.mock.start()

    def teardown_method(self):
        self.mock.stop()

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


class TestStreamRecordImages:
    """Verify that stream records include the correct image keys.

    AWS behavior:
    - INSERT: NewImage present, OldImage absent
    - MODIFY: both NewImage and OldImage present
    - REMOVE: OldImage present, NewImage absent

    Empty images (e.g. OldImage on INSERT) must be omitted entirely,
    not included as empty dicts.
    """

    @staticmethod
    def _get_records(table_name, stream_arn):
        """Helper to read all records from a stream."""
        streams = boto3.client("dynamodbstreams", region_name="us-east-1")
        desc = streams.describe_stream(StreamArn=stream_arn)
        shard_id = desc["StreamDescription"]["Shards"][0]["ShardId"]
        resp = streams.get_shard_iterator(
            StreamArn=stream_arn,
            ShardId=shard_id,
            ShardIteratorType="TRIM_HORIZON",
        )
        return streams.get_records(ShardIterator=resp["ShardIterator"])[
            "Records"
        ]

    @mock_aws
    def test_new_and_old_images_insert_has_no_old_image(self):
        """INSERT with NEW_AND_OLD_IMAGES should not have OldImage."""
        client = boto3.client("dynamodb", region_name="us-east-1")
        resp = client.create_table(
            TableName="img-test",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
            StreamSpecification={
                "StreamEnabled": True,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
        )
        stream_arn = resp["TableDescription"]["LatestStreamArn"]
        client.put_item(
            TableName="img-test",
            Item={"pk": {"S": "k1"}, "val": {"S": "a"}},
        )

        records = self._get_records("img-test", stream_arn)
        assert len(records) == 1
        rec = records[0]
        assert rec["eventName"] == "INSERT"
        assert "NewImage" in rec["dynamodb"]
        assert rec["dynamodb"]["NewImage"]["val"] == {"S": "a"}
        # INSERT must NOT have OldImage
        assert "OldImage" not in rec["dynamodb"]

    @mock_aws
    def test_new_and_old_images_modify_has_both(self):
        """MODIFY with NEW_AND_OLD_IMAGES should have both images."""
        client = boto3.client("dynamodb", region_name="us-east-1")
        resp = client.create_table(
            TableName="img-test",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
            StreamSpecification={
                "StreamEnabled": True,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
        )
        stream_arn = resp["TableDescription"]["LatestStreamArn"]
        client.put_item(
            TableName="img-test",
            Item={"pk": {"S": "k1"}, "val": {"S": "original"}},
        )
        client.put_item(
            TableName="img-test",
            Item={"pk": {"S": "k1"}, "val": {"S": "updated"}},
        )

        records = self._get_records("img-test", stream_arn)
        assert len(records) == 2
        modify = records[1]
        assert modify["eventName"] == "MODIFY"
        assert "OldImage" in modify["dynamodb"]
        assert "NewImage" in modify["dynamodb"]
        assert modify["dynamodb"]["OldImage"]["val"] == {"S": "original"}
        assert modify["dynamodb"]["NewImage"]["val"] == {"S": "updated"}

    @mock_aws
    def test_new_and_old_images_remove_has_no_new_image(self):
        """REMOVE with NEW_AND_OLD_IMAGES should not have NewImage."""
        client = boto3.client("dynamodb", region_name="us-east-1")
        resp = client.create_table(
            TableName="img-test",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
            StreamSpecification={
                "StreamEnabled": True,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
        )
        stream_arn = resp["TableDescription"]["LatestStreamArn"]
        client.put_item(
            TableName="img-test",
            Item={"pk": {"S": "k1"}, "val": {"S": "a"}},
        )
        client.delete_item(
            TableName="img-test", Key={"pk": {"S": "k1"}}
        )

        records = self._get_records("img-test", stream_arn)
        remove = records[1]
        assert remove["eventName"] == "REMOVE"
        assert "OldImage" in remove["dynamodb"]
        assert remove["dynamodb"]["OldImage"]["val"] == {"S": "a"}
        # REMOVE must NOT have NewImage
        assert "NewImage" not in remove["dynamodb"]

    @mock_aws
    def test_new_image_only_remove_has_no_new_image(self):
        """REMOVE with NEW_IMAGE should not have NewImage (nothing new)."""
        client = boto3.client("dynamodb", region_name="us-east-1")
        resp = client.create_table(
            TableName="img-test",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
            StreamSpecification={
                "StreamEnabled": True,
                "StreamViewType": "NEW_IMAGE",
            },
        )
        stream_arn = resp["TableDescription"]["LatestStreamArn"]
        client.put_item(
            TableName="img-test",
            Item={"pk": {"S": "k1"}, "val": {"S": "a"}},
        )
        client.delete_item(
            TableName="img-test", Key={"pk": {"S": "k1"}}
        )

        records = self._get_records("img-test", stream_arn)
        remove = records[1]
        assert remove["eventName"] == "REMOVE"
        # NEW_IMAGE on a REMOVE: there is no new image
        assert "NewImage" not in remove["dynamodb"]
        assert "OldImage" not in remove["dynamodb"]

    @mock_aws
    def test_old_image_only_insert_has_no_old_image(self):
        """INSERT with OLD_IMAGE should not have OldImage (nothing old)."""
        client = boto3.client("dynamodb", region_name="us-east-1")
        resp = client.create_table(
            TableName="img-test",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
            StreamSpecification={
                "StreamEnabled": True,
                "StreamViewType": "OLD_IMAGE",
            },
        )
        stream_arn = resp["TableDescription"]["LatestStreamArn"]
        client.put_item(
            TableName="img-test",
            Item={"pk": {"S": "k1"}, "val": {"S": "a"}},
        )

        records = self._get_records("img-test", stream_arn)
        insert = records[0]
        assert insert["eventName"] == "INSERT"
        # OLD_IMAGE on an INSERT: there is no old image
        assert "OldImage" not in insert["dynamodb"]
        assert "NewImage" not in insert["dynamodb"]
