import boto3
from moto import mock_cloudfront
from . import cloudfront_test_scaffolding as scaffold


@mock_cloudfront
def test_create_distribution_with_tags():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    tags = {"Items": [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]}
    config = {"DistributionConfig": config, "Tags": tags}

    resp = client.create_distribution_with_tags(DistributionConfigWithTags=config)

    resp = client.list_tags_for_resource(Resource=resp["Distribution"]["ARN"])
    assert len(resp["Tags"]["Items"]) == 2
    assert {"Key": "k1", "Value": "v1"} in resp["Tags"]["Items"]
    assert {"Key": "k2", "Value": "v2"} in resp["Tags"]["Items"]


@mock_cloudfront
def test_create_distribution_with_tags_only_one_tag():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    tags = {"Items": [{"Key": "k1", "Value": "v1"}]}
    config = {"DistributionConfig": config, "Tags": tags}

    resp = client.create_distribution_with_tags(DistributionConfigWithTags=config)

    resp = client.list_tags_for_resource(Resource=resp["Distribution"]["ARN"])
    assert len(resp["Tags"]["Items"]) == 1
    assert {"Key": "k1", "Value": "v1"} in resp["Tags"]["Items"]
