import boto3
import json
import pytest
from moto import mock_s3
from unittest import TestCase
from uuid import uuid4


SIMPLE_JSON = {"a1": "b1", "a2": "b2"}
SIMPLE_JSON2 = {"a1": "b2", "a3": "b3"}
SIMPLE_LIST = [SIMPLE_JSON, SIMPLE_JSON2]
SIMPLE_CSV = """a,b,c
e,r,f
y,u,i
q,w,y"""


@mock_s3
class TestS3Select(TestCase):
    def setUp(self) -> None:
        self.client = boto3.client("s3", "us-east-1")
        self.bucket_name = str(uuid4())
        self.client.create_bucket(Bucket=self.bucket_name)
        self.client.put_object(
            Bucket=self.bucket_name, Key="simple.json", Body=json.dumps(SIMPLE_JSON)
        )
        self.client.put_object(
            Bucket=self.bucket_name, Key="list.json", Body=json.dumps(SIMPLE_LIST)
        )
        self.client.put_object(
            Bucket=self.bucket_name, Key="simple_csv", Body=SIMPLE_CSV
        )

    def tearDown(self) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key="list.json")
        self.client.delete_object(Bucket=self.bucket_name, Key="simple.json")
        self.client.delete_object(Bucket=self.bucket_name, Key="simple_csv")
        self.client.delete_bucket(Bucket=self.bucket_name)

    def test_query_all(self):
        x = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="simple.json",
            Expression="SELECT * FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(x["Payload"])
        result.should.contain({"Records": {"Payload": b'{"a1":"b1","a2":"b2"},'}})
        result.should.contain(
            {
                "Stats": {
                    "Details": {
                        "BytesScanned": 24,
                        "BytesProcessed": 24,
                        "BytesReturned": 22,
                    }
                }
            }
        )
        result.should.contain({"End": {}})

    def test_count_function(self):
        x = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="simple.json",
            Expression="SELECT count(*) FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(x["Payload"])
        result.should.contain({"Records": {"Payload": b'{"_1":1},'}})

    @pytest.mark.xfail(message="Not yet implement in our parser")
    def test_count_as(self):
        x = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="simple.json",
            Expression="SELECT count(*) as cnt FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(x["Payload"])
        result.should.contain({"Records": {"Payload": b'{"cnt":1},'}})

    @pytest.mark.xfail(message="Not yet implement in our parser")
    def test_count_list_as(self):
        x = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="list.json",
            Expression="SELECT count(*) as cnt FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(x["Payload"])
        result.should.contain({"Records": {"Payload": b'{"cnt":1},'}})

    def test_count_csv(self):
        x = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="simple_csv",
            Expression="SELECT count(*) FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={
                "CSV": {"FileHeaderInfo": "USE", "FieldDelimiter": ","}
            },
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(x["Payload"])
        result.should.contain({"Records": {"Payload": b'{"_1":3},'}})
