import boto3

from moto import mock_s3, XRaySegment
from moto.core.models import BaseMockAWS
from contextlib import AbstractContextManager


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


def test_xray() -> None:
    xray: "AbstractContextManager[object]" = XRaySegment()
    with xray:
        assert True


def dont_call_me() -> None:
    # This is not a test and should never be called.
    #
    # warn_unused_ignores is enabed, so this will fail mypy if the typing of XRaySegment
    # would allow this. Normally that wouldn't be a concern at all, but since lazy_load is
    # a pretty complicated overload type, it seems worth double checking

    @XRaySegment  # type: ignore[call-arg]
    def this_is_the_wrong_use_of_XRaySegment() -> None:
        pass

    assert False
