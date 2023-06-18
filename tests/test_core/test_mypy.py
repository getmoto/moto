import boto3
from moto import mock_s3


@mock_s3
def test_without_parentheses() -> int:
    assert boto3.client("s3").list_buckets()["Buckets"] == []
    return 123


y: int = test_without_parentheses()  # type: ignore
assert y == 123
