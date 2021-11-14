import boto3
import pytest

from moto import mock_batch


@pytest.mark.parametrize("region", ["us-west-2", "cn-northwest-1"])
@mock_batch
def test_batch_regions(region):
    client = boto3.client("batch", region_name=region)
    resp = client.describe_jobs(jobs=[""])
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
