import boto3
from moto import mock_cloudfront
from . import cloudfront_test_scaffolding as scaffold
import sure  # noqa # pylint: disable=unused-import


@mock_cloudfront
def test_create_distribution_with_tags():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    tags = {"Items": [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]}
    config = {"DistributionConfig": config, "Tags": tags}

    resp = client.create_distribution_with_tags(DistributionConfigWithTags=config)
    resp.should.have.key("Distribution")

    resp = client.list_tags_for_resource(Resource=resp["Distribution"]["ARN"])
    resp.should.have.key("Tags")
    resp["Tags"].should.have.key("Items").length_of(2)
    resp["Tags"]["Items"].should.contain({"Key": "k1", "Value": "v1"})
    resp["Tags"]["Items"].should.contain({"Key": "k2", "Value": "v2"})


@mock_cloudfront
def test_create_distribution_with_tags_only_one_tag():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    tags = {"Items": [{"Key": "k1", "Value": "v1"}]}
    config = {"DistributionConfig": config, "Tags": tags}

    resp = client.create_distribution_with_tags(DistributionConfigWithTags=config)
    resp.should.have.key("Distribution")

    resp = client.list_tags_for_resource(Resource=resp["Distribution"]["ARN"])
    resp.should.have.key("Tags")
    resp["Tags"].should.have.key("Items").length_of(1)
    resp["Tags"]["Items"].should.contain({"Key": "k1", "Value": "v1"})
