import os
from unittest import SkipTest
from unittest.mock import patch

import boto3
import pytest
import requests
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core.versions import is_werkzeug_2_0_x_or_older


def test_passthrough_calls_for_entire_service() -> None:
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only test config when using decorators")
    if is_werkzeug_2_0_x_or_older():
        raise SkipTest(
            "Bug in old werkzeug versions where headers with byte-values throw errors"
        )
    # Still mock the credentials ourselves, we don't want to reach out to AWS for real
    with patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "a", "AWS_SECRET_ACCESS_KEY": "b"}
    ):
        list_buckets_url = "https://s3.amazonaws.com/"

        # All requests to S3 are passed through
        with mock_aws(
            config={
                "core": {"mock_credentials": False, "passthrough": {"services": ["s3"]}}
            }
        ):
            s3 = boto3.client("s3", "us-east-1")
            with pytest.raises(ClientError) as exc:
                s3.list_buckets()
            assert exc.value.response["Error"]["Code"] == "InvalidAccessKeyId"

            resp = _aws_request(list_buckets_url)
            assert resp.status_code == 403

            # Calls to SQS are mocked normally
            sqs = boto3.client("sqs", "us-east-1")
            sqs.list_queues()

        # Sanity check that the passthrough does not persist
        with mock_aws():
            s3 = boto3.client("s3", "us-east-1")
            assert s3.list_buckets()["Buckets"] == []

            resp = _aws_request(list_buckets_url)
            assert resp.status_code == 200
            assert b"<Buckets></Buckets>" in resp.content


def test_passthrough_calls_for_specific_url() -> None:
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only test config when using decorators")
    if is_werkzeug_2_0_x_or_older():
        raise SkipTest(
            "Bug in old werkzeug versions where headers with byte-values throw errors"
        )
    # Still mock the credentials ourselves, we don't want to reach out to AWS for real
    with patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "a", "AWS_SECRET_ACCESS_KEY": "b"}
    ):
        list_buckets_url = "https://s3.amazonaws.com/"

        # All requests to these URL's are passed through
        with mock_aws(
            config={
                "core": {
                    "mock_credentials": False,
                    "passthrough": {"urls": ["https://realbucket.s3.amazonaws.com/"]},
                }
            }
        ):
            s3 = boto3.client("s3", "us-east-1")
            with pytest.raises(ClientError) as exc:
                s3.create_bucket(Bucket="realbucket")
            assert exc.value.response["Error"]["Code"] == "InvalidAccessKeyId"

            # List buckets works
            assert _aws_request(list_buckets_url).status_code == 200
            assert s3.list_buckets()["Buckets"] == []

            # Creating different buckets works
            s3.create_bucket(Bucket="diff")

            # Manual requests are also not allowed
            assert (
                _aws_request("https://realbucket.s3.amazonaws.com/").status_code == 403
            )


def test_passthrough_calls_for_wildcard_urls() -> None:
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only test config when using decorators")
    # Still mock the credentials ourselves, we don't want to reach out to AWS for real
    with patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "a", "AWS_SECRET_ACCESS_KEY": "b"}
    ):
        # All requests to these URL's are passed through
        with mock_aws(
            config={
                "core": {
                    "mock_credentials": False,
                    "passthrough": {
                        "urls": [
                            "https://companyname_*.s3.amazonaws.com/",
                            "https://s3.amazonaws.com/companyname_*",
                        ]
                    },
                }
            }
        ):
            s3 = boto3.client("s3", "us-east-1")
            with pytest.raises(ClientError) as exc:
                s3.create_bucket(Bucket="companyname_prod")
            assert exc.value.response["Error"]["Code"] == "InvalidAccessKeyId"

            # Creating different buckets works
            s3.create_bucket(Bucket="diffcompany_prod")

            # Manual requests are also not allowed
            assert (
                _aws_request("https://s3.amazonaws.com/companyname_prod").status_code
                == 403
            )


def test_passthrough__using_unsupported_service() -> None:
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only test config when using decorators")
    with patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "a", "AWS_SECRET_ACCESS_KEY": "b"}
    ):
        # Requests to unsupported services still throw a NotYetImplemented
        with mock_aws(
            config={
                "core": {
                    "mock_credentials": False,
                    "passthrough": {"services": ["s3"]},
                }
            }
        ):
            workdocs = boto3.client("workdocs", "us-east-1")
            with pytest.raises(ClientError) as exc:
                workdocs.describe_users()
            assert "Not yet implemented" in str(exc.value)


def _aws_request(url: str) -> requests.Response:
    creds = b"AWS4-HMAC-SHA256 Credential=a/20240107/us-east-1/s3/aws4_request, Signature=sig"
    headers = {"Authorization": creds, "X-Amz-Content-SHA256": b"UNSIGNED-PAYLOAD"}
    return requests.get(url, headers=headers)
