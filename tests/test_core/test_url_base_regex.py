import boto3
import pytest

from moto import mock_aws
from moto.backends import list_of_moto_modules


class TestMockBucketStartingWithServiceName:
    """
    https://github.com/getmoto/moto/issues/4099
    """

    @pytest.mark.parametrize("service_name", list(list_of_moto_modules()))
    def test_bucketname_starting_with_service_name(self, service_name: str) -> None:
        with mock_aws():
            s3_client = boto3.client("s3", "eu-west-1")
            bucket_name = f"{service_name}-bucket"
            s3_client.create_bucket(
                ACL="private",
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
            )
