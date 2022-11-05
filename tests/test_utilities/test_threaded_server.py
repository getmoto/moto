import boto3
import sure  # noqa # pylint: disable=unused-import
import requests
import unittest
from moto import mock_s3, settings
from moto.server import ThreadedMotoServer
from unittest import SkipTest


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
        buckets.should.have.length_of(1)
        [b["Name"] for b in buckets].should.equal(["test"])

    def test_server_can_handle_multiple_services(self):
        s3_client = boto3.client("s3", endpoint_url="http://127.0.0.1:5000")
        dynamodb_client = boto3.client(
            "dynamodb", endpoint_url="http://127.0.0.1:5000", region_name="us-east-1"
        )
        s3_client.create_bucket(Bucket="test")
        dynamodb_client.create_table(
            TableName="table1",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        buckets = s3_client.list_buckets()["Buckets"]
        [b["Name"] for b in buckets].should.equal(["test"])

        dynamodb_client.list_tables()["TableNames"].should.equal(["table1"])

    @mock_s3
    def test_load_data_from_inmemory_client(self):
        server_client = boto3.client("s3", endpoint_url="http://127.0.0.1:5000")
        server_client.create_bucket(Bucket="test")

        in_mem_client = boto3.client("s3")
        buckets = in_mem_client.list_buckets()["Buckets"]
        [b["Name"] for b in buckets].should.equal(["test"])


def test_threaded_moto_server__different_port():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("No point in testing ServerMode within ServerMode")
    server = ThreadedMotoServer(port=5001)
    server.start()
    requests.post("http://localhost:5001/moto-api/reset")
    try:
        s3_client = boto3.client("s3", endpoint_url="http://127.0.0.1:5001")
        s3_client.create_bucket(Bucket="test")
        buckets = s3_client.list_buckets()["Buckets"]
        [b["Name"] for b in buckets].should.equal(["test"])
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
        r.content.should.contain(b"<title>Moto</title>")
        r.status_code.should.equal(200)
    finally:
        server.stop()
        pass
