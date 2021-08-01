"""Unit tests specific to the tag-related ConfigService APIs.

 These APIs include:
   list_tags_for_resource
   tag_resource
   untag_resource

"""
import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import ParamValidationError
import pytest

from moto.config import mock_config
from moto.config.models import MAX_TAGS_IN_ARG
from moto.config.models import random_string
from moto.core import ACCOUNT_ID

TEST_REGION = "us-east-1"


def config_aggregators_info(client):
    """Return list of dicts of ConfigAggregators ARNs and tags.

    One ConfigAggregator would do, but this help tests that a list
    of configs can be handled by the caller.
    """
    config_aggs = []
    for idx in range(3):
        tags = [
            {"Key": f"{x}", "Value": f"{x}"} for x in range(idx * 10, idx * 10 + 10)
        ]
        response = client.put_configuration_aggregator(
            ConfigurationAggregatorName=f"testing_{idx}_{random_string()}",
            AccountAggregationSources=[
                {"AccountIds": [ACCOUNT_ID], "AllAwsRegions": True}
            ],
            Tags=tags,
        )
        config_info = response["ConfigurationAggregator"]
        config_aggs.append(
            {"arn": config_info["ConfigurationAggregatorArn"], "tags": tags,}
        )
    return config_aggs


@mock_config
def test_tag_resource():
    """Test the ConfigSource API tag_resource()."""
    client = boto3.client("config", region_name="us-east-1")

    # Try an ARN when there are no configs instantiated.
    no_config_arn = "no_configs"
    with pytest.raises(ClientError) as cerr:
        client.tag_resource(
            ResourceArn=no_config_arn, Tags=[{"Key": "test_key", "Value": "test_value"}]
        )
    assert cerr.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        f"ResourceArn '{no_config_arn}' does not exist"
        in cerr.value.response["Error"]["Message"]
    )

    # Try an invalid ARN.
    bad_arn = "bad_arn"
    with pytest.raises(ClientError) as cerr:
        client.tag_resource(
            ResourceArn=bad_arn, Tags=[{"Key": "test_key", "Value": "test_value"}]
        )
    assert cerr.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        f"ResourceArn '{bad_arn}' does not exist"
        in cerr.value.response["Error"]["Message"]
    )

    # Create some configs and use the ARN from one of them for testing the
    # tags argument.
    config_aggs = config_aggregators_info(client)
    good_arn = config_aggs[1]["arn"]

    # Try specifying more than 50 keys.
    with pytest.raises(ClientError) as cerr:
        client.tag_resource(
            ResourceArn=good_arn,
            Tags=[{"Key": f"{x}", "Value": f"{x}"} for x in range(MAX_TAGS_IN_ARG + 1)],
        )
    assert cerr.value.response["Error"]["Code"] == "ValidationException"
    assert (
        "at 'tags' failed to satisfy constraint: Member must have length "
        "less than or equal to 50"
    ) in cerr.value.response["Error"]["Message"]

    # Try specifying an invalid key.
    with pytest.raises(ParamValidationError) as cerr:
        client.tag_resource(ResourceArn=good_arn, Tags=[{"Test": "abc"}])
    assert cerr.typename == "ParamValidationError"
    assert 'Unknown parameter in Tags[0]: "Test", must be one of: Key, Value' in str(
        cerr
    )

    # Verify keys added to ConfigurationAggregator.
    # TODO - use list_tags_for_resources() to get current set of tags.
    new_tags = [{"Key": "test_key", "Value": "test_value"}]
    client.tag_resource(ResourceArn=good_arn, Tags=new_tags)
    # TODO - use list_tags_for_resources() to verify the list of tags include
    #        the original set of tags, plus the new ones.

    # Verify keys added to AggregationAuthorization.
    response = client.put_aggregation_authorization(
        AuthorizedAccountId=ACCOUNT_ID,
        AuthorizedAwsRegion=TEST_REGION,
        Tags=[{"Key": f"{x}", "Value": f"{x}"} for x in range(10)],
    )
    agg_auth_arn = response["AggregationAuthorization"]["AggregationAuthorizationArn"]
    # TODO - use list_tags_for_resources() to get current set of tags.
    client.tag_resource(ResourceArn=agg_auth_arn, Tags=new_tags)
    # TODO - use list_tags_for_resources() to verify the list of tags include
    #        the original set of tags, plus the new ones.

    # TODO - Verify keys added to ConfigRule, when implemented.


@mock_config
def test_untag_resource():
    """Test the ConfigSource API untag_resource()."""
    client = boto3.client("config", region_name="us-east-1")

    # Try an ARN when there are no configs instantiated.
    no_config_arn = "no_configs"
    with pytest.raises(ClientError) as cerr:
        client.untag_resource(
            ResourceArn=no_config_arn, TagKeys=["untest_key", "untest_value"]
        )
    assert cerr.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        f"ResourceArn '{no_config_arn}' does not exist"
        in cerr.value.response["Error"]["Message"]
    )

    # Try an invalid ARN.
    bad_arn = "bad_arn"
    with pytest.raises(ClientError) as cerr:
        client.untag_resource(
            ResourceArn=bad_arn, TagKeys=["untest_key", "untest_value"]
        )
    assert cerr.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        f"ResourceArn '{bad_arn}' does not exist"
        in cerr.value.response["Error"]["Message"]
    )

    # Create some configs and use the ARN from one of them for testing the
    # tags argument.
    config_aggs = config_aggregators_info(client)
    good_arn = config_aggs[1]["arn"]

    # Try specifying more than 50 keys.
    with pytest.raises(ClientError) as cerr:
        client.untag_resource(
            ResourceArn=good_arn, TagKeys=[f"{x}" for x in range(MAX_TAGS_IN_ARG + 1)],
        )
    assert cerr.value.response["Error"]["Code"] == "ValidationException"
    assert (
        "at 'tags' failed to satisfy constraint: Member must have length "
        "less than or equal to 50"
    ) in cerr.value.response["Error"]["Message"]

    # Try specifying an invalid key -- it should be ignored.
    client.untag_resource(ResourceArn=good_arn, TagKeys=["foo"])

    # Try a mix of existing and non-existing tags.
    client.untag_resource(ResourceArn=good_arn, TagKeys=["0", "1", "foo", "3"])
    # TODO - use list_tags_for_resources() to verify the existing tags are
    #        removed

    # Verify keys removed from ConfigurationAggregator.  Add a new tag to
    # the current set of tags, then delete the new tag.  The original set
    # of tags should remain.
    # TODO - use list_tags_for_resources() to get current set of tags.
    test_tags = [{"Key": "test_key", "Value": "test_value"}]
    client.tag_resource(ResourceArn=good_arn, Tags=test_tags)
    client.untag_resource(ResourceArn=good_arn, TagKeys=[test_tags[0]["Key"]])
    # TODO - use list_tags_for_resources() to verify the list of tags only
    #        contains the original set of tags.

    # Verify keys removed from AggregationAuthorization.  Add a new tag to
    # the current set of tags, then delete the new tag.  The original set
    # of tags should remain.
    response = client.put_aggregation_authorization(
        AuthorizedAccountId=ACCOUNT_ID,
        AuthorizedAwsRegion=TEST_REGION,
        Tags=[{"Key": f"{x}", "Value": f"{x}"} for x in range(10)],
    )
    agg_auth_arn = response["AggregationAuthorization"]["AggregationAuthorizationArn"]
    # TODO - use list_tags_for_resources() to get current set of tags.
    test_tags = [{"Key": "test_key", "Value": "test_value"}]
    client.tag_resource(ResourceArn=agg_auth_arn, Tags=test_tags)
    client.untag_resource(ResourceArn=good_arn, TagKeys=[test_tags[0]["Key"]])
    # TODO - use list_tags_for_resources() to verify the list of tags only
    #        contains the original set of tags.

    # Delete all the tags.
    client.untag_resource(ResourceArn=good_arn, TagKeys=[f"{x}" for x in range(10)])
    # TODO - use list_tags_for_resources() to verify there are no tags.

    # TODO - Verify keys removed from ConfigRule, when implemented.
