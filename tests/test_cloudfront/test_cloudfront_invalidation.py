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


@mock_cloudfront
def test_list_invalidations():
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
    invalidation_id = resp["Invalidation"]["Id"]

    resp = client.list_invalidations(
        DistributionId=dist_id,
    )

    resp.should.have.key("InvalidationList")
    resp["InvalidationList"].shouldnt.have.key("NextMarker")
    resp["InvalidationList"].should.have.key("MaxItems").equal(100)
    resp["InvalidationList"].should.have.key("IsTruncated").equal(False)
    resp["InvalidationList"].should.have.key("Quantity").equal(1)
    resp["InvalidationList"].should.have.key("Items").length_of(1)
    resp["InvalidationList"]["Items"][0].should.have.key("Id").equal(invalidation_id)
    resp["InvalidationList"]["Items"][0].should.have.key("CreateTime")
    resp["InvalidationList"]["Items"][0].should.have.key("Status").equal("COMPLETED")


@mock_cloudfront
def test_list_invalidations__no_entries():
    client = boto3.client("cloudfront", region_name="us-west-1")

    resp = client.list_invalidations(
        DistributionId="SPAM",
    )

    resp.should.have.key("InvalidationList")
    resp["InvalidationList"].shouldnt.have.key("NextMarker")
    resp["InvalidationList"].should.have.key("MaxItems").equal(100)
    resp["InvalidationList"].should.have.key("IsTruncated").equal(False)
    resp["InvalidationList"].should.have.key("Quantity").equal(0)
    resp["InvalidationList"].shouldnt.have.key("Items")
