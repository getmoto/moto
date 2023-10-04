import json

import boto3
import requests
import pytest

from botocore.exceptions import ClientError
from moto import settings
from moto.moto_server.threaded_moto_server import ThreadedMotoServer
from unittest import SkipTest


class TestBucketPolicy:
    @classmethod
    def setup_class(cls):
        if not settings.TEST_DECORATOR_MODE:
            raise SkipTest("No point testing the ThreadedServer in Server/Proxy-mode")
        cls.server = ThreadedMotoServer(port="6000", verbose=False)
        cls.server.start()

    def setup_method(self) -> None:
        self.client = boto3.client(
            "s3",
            region_name="us-east-1",
            endpoint_url="http://localhost:6000",
            aws_access_key_id="ak",
            aws_secret_access_key="sk",
        )
        self.client.create_bucket(Bucket="mybucket")
        self.client.put_object(Bucket="mybucket", Key="test_txt", Body=b"mybytes")
        self.key_name = "http://localhost:6000/mybucket/test_txt"

    def teardown_method(self) -> None:
        self.client.delete_object(Bucket="mybucket", Key="test_txt")
        self.client.delete_bucket(Bucket="mybucket")

    @classmethod
    def teardown_class(cls):
        cls.server.stop()

    @pytest.mark.parametrize(
        "kwargs,boto3_status,unauthorized_status",
        [
            # The default policy is to allow access to 'mybucket/*'
            ({}, 200, 200),
            # We'll also allow access to the specific key
            ({"resource": "arn:aws:s3:::mybucket/test_txt"}, 200, 200),
            # We're allowing authorized access to an unrelated bucket
            # Accessing our key is allowed for authenticated users, as there is no explicit deny
            # It should block unauthenticated (public) users, as there is no explicit allow
            ({"resource": "arn:aws:s3:::notmybucket/*"}, 200, 403),
            # Verify public access when the policy contains multiple resources
            ({"resource": ["arn:aws:s3:::other", "arn:aws:s3:::mybucket/*"]}, 200, 200),
            # Deny all access, for any resource
            ({"effect": "Deny"}, 403, 403),
            # We don't explicitly deny authenticated access
            # We'll deny an unrelated resource, but that should not affect anyone
            # It should block unauthorized users, as there is no explicit allow
            ({"resource": "arn:aws:s3:::notmybucket/*", "effect": "Deny"}, 200, 403),
        ],
    )
    def test_block_or_allow_get_object(self, kwargs, boto3_status, unauthorized_status):
        self._put_policy(**kwargs)

        if boto3_status == 200:
            self.client.get_object(Bucket="mybucket", Key="test_txt")
        else:
            with pytest.raises(ClientError):
                self.client.get_object(Bucket="mybucket", Key="test_txt")

        assert requests.get(self.key_name).status_code == unauthorized_status

    def test_block_put_object(self):
        # Block Put-access
        self._put_policy(**{"effect": "Deny", "actions": ["s3:PutObject"]})

        # GET still works
        self.client.get_object(Bucket="mybucket", Key="test_txt")

        # But Put (via boto3 or requests) is not allowed
        with pytest.raises(ClientError) as exc:
            self.client.put_object(Bucket="mybucket", Key="test_txt", Body="new data")
        err = exc.value.response["Error"]
        assert err["Message"] == "Forbidden"

        assert requests.put(self.key_name).status_code == 403

    def test_block_all_actions(self):
        # Block all access
        self._put_policy(**{"effect": "Deny", "actions": ["s3:*"]})

        # Nothing works
        with pytest.raises(ClientError) as exc:
            self.client.get_object(Bucket="mybucket", Key="test_txt")
        err = exc.value.response["Error"]
        assert err["Message"] == "Forbidden"

        # But Put (via boto3 or requests) is not allowed
        with pytest.raises(ClientError) as exc:
            self.client.put_object(Bucket="mybucket", Key="test_txt", Body="new data")
        err = exc.value.response["Error"]
        assert err["Message"] == "Forbidden"

        assert requests.get(self.key_name).status_code == 403
        assert requests.put(self.key_name).status_code == 403

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
