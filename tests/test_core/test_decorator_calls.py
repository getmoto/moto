import boto3
import sure  # noqa # pylint: disable=unused-import
import os
import unittest

import pytest

from botocore.exceptions import ClientError
from moto import mock_ec2, mock_s3, settings
from unittest import SkipTest

"""
Test the different ways that the decorator can be used
"""


@mock_ec2
def test_basic_decorator():
    client = boto3.client("ec2", region_name="us-west-1")
    client.describe_addresses()["Addresses"].should.equal([])


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.mark.network
def test_context_manager(aws_credentials):
    client = boto3.client("ec2", region_name="us-west-1")
    with pytest.raises(ClientError) as exc:
        client.describe_addresses()
    err = exc.value.response["Error"]
    err["Code"].should.equal("AuthFailure")
    err["Message"].should.equal(
        "AWS was not able to validate the provided access credentials"
    )

    with mock_ec2():
        client = boto3.client("ec2", region_name="us-west-1")
        client.describe_addresses()["Addresses"].should.equal([])


@pytest.mark.network
def test_decorator_start_and_stop():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Authentication always works in ServerMode")
    mock = mock_ec2()
    mock.start()
    client = boto3.client("ec2", region_name="us-west-1")
    client.describe_addresses()["Addresses"].should.equal([])
    mock.stop()

    with pytest.raises(ClientError) as exc:
        client.describe_addresses()
    err = exc.value.response["Error"]
    err["Code"].should.equal("AuthFailure")
    err["Message"].should.equal(
        "AWS was not able to validate the provided access credentials"
    )


@mock_ec2
def test_decorater_wrapped_gets_set():
    """
    Moto decorator's __wrapped__ should get set to the tests function
    """
    test_decorater_wrapped_gets_set.__wrapped__.__name__.should.equal(
        "test_decorater_wrapped_gets_set"
    )


@mock_ec2
class Tester(object):
    def test_the_class(self):
        client = boto3.client("ec2", region_name="us-west-1")
        client.describe_addresses()["Addresses"].should.equal([])

    def test_still_the_same(self):
        client = boto3.client("ec2", region_name="us-west-1")
        client.describe_addresses()["Addresses"].should.equal([])


@mock_s3
class TesterWithSetup(unittest.TestCase):
    def setUp(self):
        self.client = boto3.client("s3")
        self.client.create_bucket(Bucket="mybucket")

    def test_still_the_same(self):
        buckets = self.client.list_buckets()["Buckets"]
        bucket_names = [b["Name"] for b in buckets]
        # There is a potential bug in the class-decorator, where the reset API is not called on start.
        # This leads to a situation where 'bucket_names' may contain buckets created by earlier tests
        bucket_names.should.contain("mybucket")


@mock_s3
class TesterWithStaticmethod(object):
    @staticmethod
    def static(*args):
        assert not args or not isinstance(args[0], TesterWithStaticmethod)

    def test_no_instance_sent_to_staticmethod(self):
        self.static()
