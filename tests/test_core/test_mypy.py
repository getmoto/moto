import boto3

from moto import mock_aws
from moto.core.decorator import MockAWS


@mock_aws
def method_without_parentheses() -> int:
    assert boto3.client("s3").list_buckets()["Buckets"] == []
    return 123


@mock_aws()
def method_with_parentheses() -> int:
    assert boto3.client("s3").list_buckets()["Buckets"] == []
    return 456


@mock_aws
def test_no_return() -> None:
    assert boto3.client("s3").list_buckets()["Buckets"] == []


def test_with_context_manager() -> None:
    with mock_aws():
        assert boto3.client("s3").list_buckets()["Buckets"] == []


def test_manual() -> None:
    # this has the explicit type not because it's necessary but so that mypy will
    # complain if it's wrong
    m: MockAWS = mock_aws()
    m.start()
    assert boto3.client("s3").list_buckets()["Buckets"] == []
    m.stop()


x: int = method_with_parentheses()
assert x == 456

y: int = method_without_parentheses()
assert y == 123
