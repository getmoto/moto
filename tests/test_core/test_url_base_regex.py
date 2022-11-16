import boto3
import moto
import pytest
from moto import mock_s3


service_names = [
    (d[5:], "")
    for d in dir(moto)
    if d.startswith("mock_") and not d == "mock_xray_client" and not d == "mock_all"
]


class TestMockBucketStartingWithServiceName:
    """
    https://github.com/spulec/moto/issues/4099
    """

    @pytest.mark.parametrize("service_name,decorator", service_names)
    def test_bucketname_starting_with_service_name(self, service_name, decorator):

        decorator = getattr(moto, f"mock_{service_name}")
        with decorator():
            with mock_s3():
                s3_client = boto3.client("s3", "eu-west-1")
                bucket_name = f"{service_name}-bucket"
                s3_client.create_bucket(
                    ACL="private",
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
                )
