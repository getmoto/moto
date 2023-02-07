import boto3
import json
import requests
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
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
            ({"resource": ["arn:aws:s3:::mybucket", "arn:aws:s3:::mybucket/*"]}, 200),
            (
                {
                    "resource": [
                        "arn:aws:s3:::notmybucket",
                        "arn:aws:s3:::notmybucket/*",
                    ]
                },
                403,
            ),
            (
                {"resource": ["arn:aws:s3:::mybucket", "arn:aws:s3:::notmybucket/*"]},
                403,
            ),
            ({"effect": "Deny"}, 403),
        ],
    )
    def test_block_or_allow_get_object(self, kwargs, status):
        self._put_policy(**kwargs)

        if status == 200:
            self.client.get_object(Bucket="mybucket", Key="test_txt")
        else:
            with pytest.raises(ClientError):
                self.client.get_object(Bucket="mybucket", Key="test_txt")

        requests.get(self.key_name).status_code.should.equal(status)

    def test_block_put_object(self):
        # Block Put-access
        self._put_policy(**{"effect": "Deny", "actions": ["s3:PutObject"]})

        # GET still works
        self.client.get_object(Bucket="mybucket", Key="test_txt")

        # But Put (via boto3 or requests) is not allowed
        with pytest.raises(ClientError) as exc:
            self.client.put_object(Bucket="mybucket", Key="test_txt", Body="new data")
        err = exc.value.response["Error"]
        err["Message"].should.equal("Forbidden")

        requests.put(self.key_name).status_code.should.equal(403)

    def test_block_all_actions(self):
        # Block all access
        self._put_policy(**{"effect": "Deny", "actions": ["s3:*"]})

        # Nothing works
        with pytest.raises(ClientError) as exc:
            self.client.get_object(Bucket="mybucket", Key="test_txt")
        err = exc.value.response["Error"]
        err["Message"].should.equal("Forbidden")

        # But Put (via boto3 or requests) is not allowed
        with pytest.raises(ClientError) as exc:
            self.client.put_object(Bucket="mybucket", Key="test_txt", Body="new data")
        err = exc.value.response["Error"]
        err["Message"].should.equal("Forbidden")

        requests.get(self.key_name).status_code.should.equal(403)
        requests.put(self.key_name).status_code.should.equal(403)

        # Allow access again, because we want to delete the object during teardown
        self._put_policy(**{"effect": "Allow", "actions": ["s3:*"]})

    def test_block_all_with_different_principal(self):
        # Block all access for principal y
        self._put_policy(**{"effect": "Deny", "actions": ["s3:*"], "principal": "y"})

        # Everything works - Moto only blocks access for principal *
        self.client.get_object(Bucket="mybucket", Key="test_txt")
        self.client.put_object(Bucket="mybucket", Key="test_txt", Body="new data")

    def _put_policy(
        self,
        resource="arn:aws:s3:::mybucket/*",
        effect="Allow",
        actions=None,
        principal=None,
    ):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": effect,
                    "Principal": principal or "*",
                    "Action": actions or ["s3:GetObject"],
                    "Resource": resource,
                }
            ],
        }
        self.client.put_bucket_policy(Bucket="mybucket", Policy=json.dumps(policy))
