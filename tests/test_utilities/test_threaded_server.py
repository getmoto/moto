import unittest
from unittest import SkipTest

import boto3
import requests

from moto import mock_aws, settings
from moto.server import ThreadedMotoServer


class TestThreadedMotoServer(unittest.TestCase):
    def setUp(self):
        if settings.TEST_SERVER_MODE:
            raise SkipTest("No point in testing ServerMode within ServerMode")
        self.server = ThreadedMotoServer(ip_address="127.0.0.1")
        self.server.start()
        requests.post("http://localhost:5000/moto-api/reset")

    def tearDown(self):
        self.server.stop()

    def test_server_is_reachable(self):
        s3_client = boto3.client("s3", endpoint_url="http://127.0.0.1:5000")
        s3_client.create_bucket(Bucket="test")
        buckets = s3_client.list_buckets()["Buckets"]
        assert len(buckets) == 1
        assert [b["Name"] for b in buckets] == ["test"]

    def test_server_can_handle_multiple_services(self):
        s3_client = boto3.client("s3", endpoint_url="http://127.0.0.1:5000")
        dynamodb_client = boto3.client(
            "dynamodb",
            endpoint_url="http://127.0.0.1:5000",
            region_name="us-east-1",
        )
        s3_client.create_bucket(Bucket="test")
        dynamodb_client.create_table(
            TableName="table1",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        buckets = s3_client.list_buckets()["Buckets"]
        assert [b["Name"] for b in buckets] == ["test"]

        assert dynamodb_client.list_tables()["TableNames"] == ["table1"]

    @mock_aws
    def test_load_data_from_inmemory_client(self):
        server_client = boto3.client("s3", endpoint_url="http://127.0.0.1:5000")
        server_client.create_bucket(Bucket="test")

        in_mem_client = boto3.client("s3")
        buckets = in_mem_client.list_buckets()["Buckets"]
        assert [b["Name"] for b in buckets] == ["test"]


def test_threaded_moto_server__different_port():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("No point in testing ServerMode within ServerMode")
    server = ThreadedMotoServer(port=5001)
    server.start()
    requests.post("http://localhost:5001/moto-api/reset")
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url="http://127.0.0.1:5001",
            aws_access_key_id="ak",
            aws_secret_access_key="sk",
            region_name="us-east-1",
        )
        s3_client.create_bucket(Bucket="test")
        buckets = s3_client.list_buckets()["Buckets"]
        assert [b["Name"] for b in buckets] == ["test"]
    finally:
        server.stop()


def test_threaded_moto_server__using_requests():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("No point in testing ServerMode within ServerMode")
    server = ThreadedMotoServer(port=5001)
    server.start()
    requests.post("http://localhost:5001/moto-api/reset")
    try:
        r = requests.get("http://localhost:5001/moto-api")
        assert b"<title>Moto</title>" in r.content
        assert r.status_code == 200
    finally:
        server.stop()
