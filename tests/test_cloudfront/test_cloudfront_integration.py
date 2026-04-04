import boto3

from moto import mock_aws

from . import cloudfront_test_scaffolding as scaffold


@mock_aws
def test_rgtapi_get_tag_values():
    client = boto3.client("cloudfront", "us-east-1")

    for i in range(1, 3):
        caller_reference = f"distribution{i}"
        client.create_distribution_with_tags(
            DistributionConfigWithTags=scaffold.example_dist_config_with_tags(
                caller_reference
            )
        )

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["cloudfront"],
        TagFilters=[{"Key": "k1", "Values": ["v1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 2
    assert {"Key": "k1", "Value": "v1"} in resp["ResourceTagMappingList"][0]["Tags"]


@mock_aws
def test_rgtapi_tag_resources():
    client = boto3.client("cloudfront", "us-east-1")
    dist = client.create_distribution_with_tags(
        DistributionConfigWithTags=scaffold.example_dist_config_with_tags("ref")
    )

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")
    dist_arn = dist["Distribution"]["ARN"]

    rtapi.tag_resources(
        ResourceARNList=[dist_arn],
        Tags={"NewKey": "NewValue"},
    )

    tags = client.list_tags_for_resource(Resource=dist_arn)["Tags"]["Items"]

    assert {"Key": "k1", "Value": "v1"} in tags
    assert {"Key": "NewKey", "Value": "NewValue"} in tags


@mock_aws
def test_rgtapi_untag_resources():
    client = boto3.client("cloudfront", "us-east-1")

    dist = client.create_distribution_with_tags(
        DistributionConfigWithTags=scaffold.example_dist_config_with_tags("ref")
    )

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")
    dist_arn = dist["Distribution"]["ARN"]

    rtapi.tag_resources(
        ResourceARNList=[dist_arn],
        Tags={"NewKey": "NewValue"},
    )

    rtapi.untag_resources(
        ResourceARNList=[dist_arn],
        TagKeys=["k1", "k2"],
    )

    tags = client.list_tags_for_resource(Resource=dist_arn)["Tags"]["Items"]

    assert {"Key": "k1", "Value": "v1"} not in tags
    assert {"Key": "k2", "Value": "v2"} not in tags
    assert {"Key": "NewKey", "Value": "NewValue"} in tags
