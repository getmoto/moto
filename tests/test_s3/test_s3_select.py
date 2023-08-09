import json
from unittest import TestCase
from uuid import uuid4

import boto3
import pytest

from moto import mock_s3


SIMPLE_JSON = {"a1": "b1", "a2": "b2", "a3": None}
SIMPLE_JSON2 = {"a1": "b2", "a3": "b3"}
EXTENSIVE_JSON = [
    {
        "staff": [
            {"name": "Janelyn M", "city": "Chicago", "kids": 2},
            {"name": "Stacy P", "city": "Seattle", "kids": 1},
        ],
        "country": "USA",
    }
]
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
        self.client.put_object(
            Bucket=self.bucket_name,
            Key="extensive.json",
            Body=json.dumps(EXTENSIVE_JSON),
        )

    def tearDown(self) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key="list.json")
        self.client.delete_object(Bucket=self.bucket_name, Key="simple.json")
        self.client.delete_object(Bucket=self.bucket_name, Key="simple_csv")
        self.client.delete_object(Bucket=self.bucket_name, Key="extensive.json")
        self.client.delete_bucket(Bucket=self.bucket_name)

    def test_query_all(self):
        content = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="simple.json",
            Expression="SELECT * FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(content["Payload"])
        assert {"Records": {"Payload": b'{"a1":"b1","a2":"b2","a3":null},'}} in result

        # Verify result is valid JSON
        json.loads(result[0]["Records"]["Payload"][0:-1].decode("utf-8"))

        # Verify result contains metadata
        assert {
            "Stats": {
                "Details": {
                    "BytesScanned": 24,
                    "BytesProcessed": 24,
                    "BytesReturned": 22,
                }
            }
        } in result
        assert {"End": {}} in result

    def test_count_function(self):
        content = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="simple.json",
            Expression="SELECT count(*) FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(content["Payload"])
        assert {"Records": {"Payload": b'{"_1":1},'}} in result

    @pytest.mark.xfail(message="Not yet implement in our parser")
    def test_count_as(self):
        content = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="simple.json",
            Expression="SELECT count(*) as cnt FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(content["Payload"])
        assert {"Records": {"Payload": b'{"cnt":1},'}} in result

    @pytest.mark.xfail(message="Not yet implement in our parser")
    def test_count_list_as(self):
        content = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="list.json",
            Expression="SELECT count(*) as cnt FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(content["Payload"])
        assert {"Records": {"Payload": b'{"cnt":1},'}} in result

    def test_count_csv(self):
        content = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="simple_csv",
            Expression="SELECT count(*) FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={
                "CSV": {"FileHeaderInfo": "USE", "FieldDelimiter": ","}
            },
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(content["Payload"])
        assert {"Records": {"Payload": b'{"_1":3},'}} in result

    def test_default_record_delimiter(self):
        content = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="simple_csv",
            Expression="SELECT count(*) FROM S3Object",
            ExpressionType="SQL",
            InputSerialization={
                "CSV": {"FileHeaderInfo": "USE", "FieldDelimiter": ","}
            },
            # RecordDelimiter is not specified - should default to new line (\n)
            OutputSerialization={"JSON": {}},
        )
        result = list(content["Payload"])
        assert {"Records": {"Payload": b'{"_1":3}\n'}} in result

    def test_extensive_json__select_list(self):
        content = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="extensive.json",
            Expression="select * from s3object[*].staff[*] s",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(content["Payload"])
        assert {"Records": {"Payload": b"{},"}} in result

    def test_extensive_json__select_all(self):
        content = self.client.select_object_content(
            Bucket=self.bucket_name,
            Key="extensive.json",
            Expression="select * from s3object s",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": ","}},
        )
        result = list(content["Payload"])
        assert {
            "Records": {
                "Payload": b'{"_1":[{"staff":[{"name":"Janelyn M","city":"Chicago","kids":2},{"name":"Stacy P","city":"Seattle","kids":1}],"country":"USA"}]},'
            }
        } in result
