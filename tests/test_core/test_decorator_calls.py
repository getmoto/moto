import inspect
import os
import unittest
from typing import Any
from unittest import SkipTest, mock

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core.decorator import ProxyModeMockAWS, ServerModeMockAWS

"""
Test the different ways that the decorator can be used
"""


@mock_aws
def test_basic_decorator() -> None:
    client = boto3.client("ec2", region_name="us-west-1")
    assert client.describe_addresses()["Addresses"] == []


@pytest.fixture(name="aws_credentials")
def fixture_aws_credentials(monkeypatch: Any) -> None:  # type: ignore[misc]
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.mark.network
def test_context_manager(aws_credentials: Any) -> None:  # type: ignore[misc]  # pylint: disable=unused-argument
    client = boto3.client("ec2", region_name="us-west-1")
    with pytest.raises(ClientError) as exc:
        client.describe_addresses()
    err = exc.value.response["Error"]
    assert err["Code"] == "AuthFailure"
    assert (
        err["Message"] == "AWS was not able to validate the provided access credentials"
    )

    with mock_aws():
        client = boto3.client("ec2", region_name="us-west-1")
        assert client.describe_addresses()["Addresses"] == []


@mock.patch.dict(os.environ, {"MOTO_CALL_RESET_API": "false"})
@pytest.mark.parametrize("mock_class", [mock_aws, ServerModeMockAWS, ProxyModeMockAWS])
def test_context_decorator_exposes_bare_essentials(mock_class: Any) -> None:  # type: ignore
    # Verify we're only exposing the necessary methods
    with mock_class() as m:
        exposed_attributes = [a for a in m.__dict__.keys() if not a.startswith("_")]
        assert exposed_attributes == []

        # Methods + Static attributes
        exposed_methods = [n for n, _ in inspect.getmembers(m) if not n.startswith("_")]
        assert sorted(exposed_methods) == ["reset", "start", "stop"]


@pytest.mark.network
def test_decorator_start_and_stop() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Authentication always works in ServerMode")
    my_mock = mock_aws()
    my_mock.start()
    client = boto3.client("ec2", region_name="us-west-1")
    assert client.describe_addresses()["Addresses"] == []
    my_mock.stop()

    with pytest.raises(ClientError) as exc:
        client.describe_addresses()
    err = exc.value.response["Error"]
    assert err["Code"] == "AuthFailure"
    assert (
        err["Message"] == "AWS was not able to validate the provided access credentials"
    )


@mock_aws
def test_decorater_wrapped_gets_set() -> None:
    """
    Moto decorator's __wrapped__ should get set to the tests function
    """
    assert (
        test_decorater_wrapped_gets_set.__wrapped__.__name__  # type: ignore
        == "test_decorater_wrapped_gets_set"
    )


@mock_aws
class Tester:
    def test_the_class(self) -> None:
        client = boto3.client("ec2", region_name="us-west-1")
        assert client.describe_addresses()["Addresses"] == []

    def test_still_the_same(self) -> None:
        client = boto3.client("ec2", region_name="us-west-1")
        assert client.describe_addresses()["Addresses"] == []


@mock_aws
class TesterWithSetup(unittest.TestCase):
    def setUp(self) -> None:
        self.client = boto3.client("s3", region_name="us-east-1")
        self.client.create_bucket(Bucket="mybucket")

    def test_still_the_same(self) -> None:
        buckets = self.client.list_buckets()["Buckets"]
        bucket_names = [b["Name"] for b in buckets]
        # There is a potential bug in the class-decorator, where the reset API is not called on start.
        # This leads to a situation where 'bucket_names' may contain buckets created by earlier tests
        assert "mybucket" in bucket_names


@mock_aws
class TesterWithStaticmethod:
    @staticmethod
    def static(*args: Any) -> None:  # type: ignore[misc]
        assert not args or not isinstance(args[0], TesterWithStaticmethod)

    def test_no_instance_sent_to_staticmethod(self) -> None:
        self.static()


@mock_aws
class TestWithSetup_UppercaseU(unittest.TestCase):
    def setUp(self) -> None:
        # This method will be executed automatically, provided we extend the TestCase-class
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")

    def test_should_find_bucket(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        self.assertIsNotNone(s3.head_bucket(Bucket="mybucket"))

    def test_should_not_find_unknown_bucket(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ClientError):
            s3.head_bucket(Bucket="unknown_bucket")


@mock_aws
class TestWithSetup_LowercaseU:
    def setup_method(self, *args: Any) -> None:  # pylint: disable=unused-argument
        # This method will be executed automatically using pytest
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")

    def test_should_find_bucket(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        assert s3.head_bucket(Bucket="mybucket") is not None

    def test_should_not_find_unknown_bucket(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ClientError):
            s3.head_bucket(Bucket="unknown_bucket")


@mock_aws
class TestWithSetupMethod:
    def setup_method(self, *args: Any) -> None:  # pylint: disable=unused-argument
        # This method will be executed automatically using pytest
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")

    def test_should_find_bucket(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        assert s3.head_bucket(Bucket="mybucket") is not None

    def test_should_not_find_unknown_bucket(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ClientError):
            s3.head_bucket(Bucket="unknown_bucket")


@mock_aws
class TestKinesisUsingSetupMethod:
    def setup_method(self, *args: Any) -> None:  # pylint: disable=unused-argument
        self.stream_name = "test_stream"
        self.boto3_kinesis_client = boto3.client("kinesis", region_name="us-east-1")
        self.boto3_kinesis_client.create_stream(
            StreamName=self.stream_name, ShardCount=1
        )

    def test_stream_creation(self) -> None:
        pass

    def test_stream_recreation(self) -> None:
        # The setup-method will run again for this test
        # The fact that it passes, means the state was reset
        # Otherwise it would complain about a stream already existing
        pass


@mock_aws
class TestWithInvalidSetupMethod:
    def setupmethod(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")

    def test_should_not_find_bucket(self) -> None:
        # Name of setupmethod is not recognized, so it will not be executed
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ClientError):
            s3.head_bucket(Bucket="mybucket")


@mock_aws
class TestWithPublicMethod(unittest.TestCase):
    def ensure_bucket_exists(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")

    def test_should_find_bucket(self) -> None:
        self.ensure_bucket_exists()

        s3 = boto3.client("s3", region_name="us-east-1")
        assert s3.head_bucket(Bucket="mybucket") is not None

    def test_should_not_find_bucket(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ClientError):
            s3.head_bucket(Bucket="mybucket")


@mock_aws
class TestWithPseudoPrivateMethod(unittest.TestCase):
    def _ensure_bucket_exists(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")

    def test_should_find_bucket(self) -> None:
        self._ensure_bucket_exists()
        s3 = boto3.client("s3", region_name="us-east-1")
        assert s3.head_bucket(Bucket="mybucket") is not None

    def test_should_not_find_bucket(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ClientError):
            s3.head_bucket(Bucket="mybucket")


@mock_aws
class Baseclass(unittest.TestCase):
    def setUp(self) -> None:
        self.s3 = boto3.resource("s3", region_name="us-east-1")
        self.client = boto3.client("s3", region_name="us-east-1")
        self.test_bucket = self.s3.Bucket("testbucket")
        self.test_bucket.create()

    def tearDown(self) -> None:
        # The bucket will still exist at this point
        self.test_bucket.delete()


@mock_aws
class TestSetUpInBaseClass(Baseclass):
    def test_a_thing(self) -> None:
        # Verify that we can 'see' the setUp-method in the parent class
        assert self.client.head_bucket(Bucket="testbucket") is not None


@mock_aws
class TestWithNestedClasses:
    class NestedClass(unittest.TestCase):
        def _ensure_bucket_exists(self) -> None:
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="bucketclass1")

        def test_should_find_bucket(self) -> None:
            self._ensure_bucket_exists()
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.head_bucket(Bucket="bucketclass1")

    class NestedClass2(unittest.TestCase):
        def _ensure_bucket_exists(self) -> None:
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="bucketclass2")

        def test_should_find_bucket(self) -> None:
            self._ensure_bucket_exists()
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.head_bucket(Bucket="bucketclass2")

        def test_should_not_find_bucket_from_different_class(self) -> None:
            s3 = boto3.client("s3", region_name="us-east-1")
            with pytest.raises(ClientError):
                s3.head_bucket(Bucket="bucketclass1")

    class TestWithSetup(unittest.TestCase):
        def setUp(self) -> None:
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="mybucket")

        def test_should_find_bucket(self) -> None:
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.head_bucket(Bucket="mybucket")

            s3.create_bucket(Bucket="bucketinsidetest")

        def test_should_not_find_bucket_from_test_method(self) -> None:
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.head_bucket(Bucket="mybucket")

            with pytest.raises(ClientError):
                s3.head_bucket(Bucket="bucketinsidetest")
