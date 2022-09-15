import boto3
import json
import requests

from moto.moto_server.threaded_moto_server import ThreadedMotoServer
from unittest import TestCase


class TestBucketPolicy(TestCase):
    def setUpClass() -> None:
        TestBucketPolicy.server = ThreadedMotoServer(
            ip_address="127.0.0.1", port="6000", verbose=False
        )
        TestBucketPolicy.server.start()

    def setUp(self) -> None:
        self.client = boto3.client(
            "s3", region_name="us-east-1", endpoint_url="http://localhost:6000"
        )
        self.client.create_bucket(Bucket="mybucket")
        self.client.put_object(Bucket="mybucket", Key="test_txt", Body=b"mybytes")

    def tearDown(self) -> None:
        self.client.delete_object(Bucket="mybucket", Key="test_txt")
        self.client.delete_bucket(Bucket="mybucket")

    def tearDownClass() -> None:
        TestBucketPolicy.server.stop()

    def test_policy_allow_all(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": "arn:aws:s3:::mybucket/*",
                }
            ],
        }
        self._put_policy(policy)

        r = requests.get("http://localhost:6000/mybucket/test_txt")
        assert r.status_code == 200

    def test_policy_allow_different_action(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:PutObject"],
                    "Resource": "arn:aws:s3:::mybucket/*",
                }
            ],
        }
        self._put_policy(policy)

        r = requests.get("http://localhost:6000/mybucket/test_txt")
        assert r.status_code == 403

    def test_policy_allow_different_bucket(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": "arn:aws:s3:::notmybucket/*",
                }
            ],
        }
        self._put_policy(policy)

        r = requests.get("http://localhost:6000/mybucket/test_txt")
        assert r.status_code == 403

    def test_policy_allow_different_resource(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": "arn:aws:s3:::mybucket/other*",
                }
            ],
        }
        self._put_policy(policy)

        r = requests.get("http://localhost:6000/mybucket/test_txt")
        assert r.status_code == 403

    def test_policy_allow_exact_resource(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": "arn:aws:s3:::mybucket/test_txt",
                }
            ],
        }
        self._put_policy(policy)

        r = requests.get("http://localhost:6000/mybucket/test_txt")
        assert r.status_code == 200

    def test_policy_deny(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": "arn:aws:s3:::mybucket/*",
                }
            ],
        }
        self._put_policy(policy)

        r = requests.get("http://localhost:6000/mybucket/test_txt")
        assert r.status_code == 403

    def _put_policy(self, policy):
        self.client.put_bucket_policy(Bucket="mybucket", Policy=json.dumps(policy))
