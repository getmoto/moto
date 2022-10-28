import boto3
import json
import requests
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto.moto_server.threaded_moto_server import ThreadedMotoServer


class TestBucketPolicy:
    @staticmethod
    def setup_class(cls):
        cls.server = ThreadedMotoServer(port="6000", verbose=False)
        cls.server.start()

    def setup_method(self) -> None:
        self.client = boto3.client(
            "s3", region_name="us-east-1", endpoint_url="http://localhost:6000"
        )
        self.client.create_bucket(Bucket="mybucket")
        self.client.put_object(Bucket="mybucket", Key="test_txt", Body=b"mybytes")
        self.key_name = "http://localhost:6000/mybucket/test_txt"

    def teardown_method(self) -> None:
        self.client.delete_object(Bucket="mybucket", Key="test_txt")
        self.client.delete_bucket(Bucket="mybucket")

    @staticmethod
    def teardown_class(cls):
        cls.server.stop()

    @pytest.mark.parametrize(
        "kwargs,status",
        [
            ({}, 200),
            ({"resource": "arn:aws:s3:::mybucket/test_txt"}, 200),
            ({"resource": "arn:aws:s3:::notmybucket/*"}, 403),
            ({"resource": "arn:aws:s3:::mybucket/other*"}, 403),
            ({"actions": ["s3:PutObject"]}, 403),
            ({"effect": "Deny"}, 403),
        ],
    )
    def test_policy_allow_all(self, kwargs, status):
        self._put_policy(**kwargs)

        requests.get(self.key_name).status_code.should.equal(status)

    def _put_policy(
        self, resource="arn:aws:s3:::mybucket/*", effect="Allow", actions=None
    ):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": effect,
                    "Principal": "*",
                    "Action": actions or ["s3:GetObject"],
                    "Resource": resource,
                }
            ],
        }
        self.client.put_bucket_policy(Bucket="mybucket", Policy=json.dumps(policy))
