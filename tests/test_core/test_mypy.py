import boto3

from moto import mock_s3
from moto.core.models import BaseMockAWS


@mock_s3
def test_without_parentheses() -> int:
    assert boto3.client("s3").list_buckets()["Buckets"] == []
    return 123


@mock_s3()
def test_with_parentheses() -> int:
    assert boto3.client("s3").list_buckets()["Buckets"] == []
    return 456


@mock_s3
def test_no_return() -> None:
    assert boto3.client("s3").list_buckets()["Buckets"] == []


def test_with_context_manager() -> None:
    with mock_s3():
        assert boto3.client("s3").list_buckets()["Buckets"] == []


def test_manual() -> None:
    # this has the explicit type not because it's necessary but so that mypy will
    # complain if it's wrong
    m: BaseMockAWS = mock_s3()
    m.start()
    assert boto3.client("s3").list_buckets()["Buckets"] == []
    m.stop()


x: int = test_with_parentheses()
assert x == 456

y: int = test_without_parentheses()
assert y == 123
