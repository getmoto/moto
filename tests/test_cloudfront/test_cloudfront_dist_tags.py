import boto3

from moto import mock_aws

from . import cloudfront_test_scaffolding as scaffold


@mock_aws
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


@mock_aws
def test_create_distribution_with_tags_only_one_tag():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    tags = {"Items": [{"Key": "k1", "Value": "v1"}]}
    config = {"DistributionConfig": config, "Tags": tags}

    resp = client.create_distribution_with_tags(DistributionConfigWithTags=config)

    resp = client.list_tags_for_resource(Resource=resp["Distribution"]["ARN"])
    assert len(resp["Tags"]["Items"]) == 1
    assert {"Key": "k1", "Value": "v1"} in resp["Tags"]["Items"]


@mock_aws
def test_tag_resource_on_existing_distribution():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")

    resp = client.create_distribution(DistributionConfig=config)
    dist_arn = resp["Distribution"]["ARN"]

    resp = client.list_tags_for_resource(Resource=dist_arn)
    assert len(resp["Tags"]["Items"]) == 0

    client.tag_resource(
        Resource=dist_arn, Tags={"Items": [{"Key": "k1", "Value": "v1"}]}
    )

    resp = client.list_tags_for_resource(Resource=dist_arn)
    assert len(resp["Tags"]["Items"]) == 1
    assert {"Key": "k1", "Value": "v1"} in resp["Tags"]["Items"]


@mock_aws
def test_untag_resource_on_existing_distribution():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")

    resp = client.create_distribution(DistributionConfig=config)
    dist_arn = resp["Distribution"]["ARN"]

    client.tag_resource(
        Resource=dist_arn,
        Tags={"Items": [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]},
    )

    resp = client.list_tags_for_resource(Resource=dist_arn)
    assert len(resp["Tags"]["Items"]) == 2

    client.untag_resource(Resource=dist_arn, TagKeys={"Items": ["k1"]})

    resp = client.list_tags_for_resource(Resource=dist_arn)
    assert len(resp["Tags"]["Items"]) == 1
    assert {"Key": "k2", "Value": "v2"} in resp["Tags"]["Items"]
    assert {"Key": "k1", "Value": "v1"} not in resp["Tags"]["Items"]
