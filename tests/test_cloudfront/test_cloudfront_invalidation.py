import boto3
from moto import mock_cloudfront
from . import cloudfront_test_scaffolding as scaffold
import sure  # noqa # pylint: disable=unused-import


@mock_cloudfront
def test_create_invalidation():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    resp = client.create_distribution(DistributionConfig=config)
    dist_id = resp["Distribution"]["Id"]

    resp = client.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            "Paths": {"Quantity": 2, "Items": ["/path1", "/path2"]},
            "CallerReference": "ref2",
        },
    )

    resp.should.have.key("Location")
    resp.should.have.key("Invalidation")

    resp["Invalidation"].should.have.key("Id")
    resp["Invalidation"].should.have.key("Status").equals("COMPLETED")
    resp["Invalidation"].should.have.key("CreateTime")
    resp["Invalidation"].should.have.key("InvalidationBatch").equals(
        {
            "Paths": {"Quantity": 2, "Items": ["/path1", "/path2"]},
            "CallerReference": "ref2",
        }
    )
