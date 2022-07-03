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
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

TEST_REGION = "us-east-1"


def config_aggregators_info(client):
    """Return list of dicts of ConfigAggregators ARNs and tags.

    One ConfigAggregator would do, but this tests that a list of
    configs can be handled by the caller.
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
            {"arn": config_info["ConfigurationAggregatorArn"], "tags": tags}
        )
    return config_aggs


@mock_config
def test_tag_resource():
    """Test the ConfigSource API tag_resource()."""
    client = boto3.client("config", region_name=TEST_REGION)

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
    rsp = client.list_tags_for_resource(ResourceArn=good_arn)
    tags = rsp["Tags"]

    new_tags = [{"Key": "test_key", "Value": "test_value"}]
    client.tag_resource(ResourceArn=good_arn, Tags=new_tags)
    tags.extend(new_tags)

    updated_rsp = client.list_tags_for_resource(ResourceArn=good_arn)
    assert tags == updated_rsp["Tags"]

    # Verify keys added to AggregationAuthorization.
    response = client.put_aggregation_authorization(
        AuthorizedAccountId=ACCOUNT_ID,
        AuthorizedAwsRegion=TEST_REGION,
        Tags=[{"Key": f"{x}", "Value": f"{x}"} for x in range(10)],
    )
    agg_auth_arn = response["AggregationAuthorization"]["AggregationAuthorizationArn"]
    rsp = client.list_tags_for_resource(ResourceArn=agg_auth_arn)
    tags = rsp["Tags"]

    client.tag_resource(ResourceArn=agg_auth_arn, Tags=new_tags)
    tags.extend(new_tags)

    updated_rsp = client.list_tags_for_resource(ResourceArn=agg_auth_arn)
    assert tags == updated_rsp["Tags"]

    # Verify keys added to ConfigRule.
    config_rule_name = f"config-rule-test-{random_string()}"
    client.put_config_rule(
        ConfigRule={
            "ConfigRuleName": config_rule_name,
            "Scope": {"ComplianceResourceTypes": ["AWS::IAM::Group"]},
            "Source": {"Owner": "AWS", "SourceIdentifier": "IAM_PASSWORD_POLICY"},
        },
        Tags=[{"Key": f"{x}", "Value": f"{x}"} for x in range(10)],
    )
    config_rule = client.describe_config_rules(ConfigRuleNames=[config_rule_name])[
        "ConfigRules"
    ][0]
    config_rule_arn = config_rule["ConfigRuleArn"]
    rsp = client.list_tags_for_resource(ResourceArn=config_rule_arn)
    tags = rsp["Tags"]

    client.tag_resource(ResourceArn=config_rule_arn, Tags=new_tags)
    tags.extend(new_tags)

    updated_rsp = client.list_tags_for_resource(ResourceArn=config_rule_arn)
    assert tags == updated_rsp["Tags"]


@mock_config
def test_untag_resource():
    """Test the ConfigSource API untag_resource()."""
    client = boto3.client("config", region_name=TEST_REGION)

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
            ResourceArn=good_arn, TagKeys=[f"{x}" for x in range(MAX_TAGS_IN_ARG + 1)]
        )
    assert cerr.value.response["Error"]["Code"] == "ValidationException"
    assert (
        "at 'tags' failed to satisfy constraint: Member must have length "
        "less than or equal to 50"
    ) in cerr.value.response["Error"]["Message"]

    # Try specifying an invalid key -- it should be ignored.
    client.untag_resource(ResourceArn=good_arn, TagKeys=["foo"])

    # Try a mix of existing and non-existing tags.
    rsp = client.list_tags_for_resource(ResourceArn=good_arn)
    tags = rsp["Tags"]

    client.untag_resource(ResourceArn=good_arn, TagKeys=["10", "foo", "13"])

    updated_rsp = client.list_tags_for_resource(ResourceArn=good_arn)
    expected_tags = [x for x in tags if x["Key"] not in ["10", "13"]]
    assert expected_tags == updated_rsp["Tags"]

    # Verify keys removed from ConfigurationAggregator.  Add a new tag to
    # the current set of tags, then delete the new tag.  The original set
    # of tags should remain.
    rsp = client.list_tags_for_resource(ResourceArn=good_arn)
    tags = rsp["Tags"]

    test_tags = [{"Key": "test_key", "Value": "test_value"}]
    client.tag_resource(ResourceArn=good_arn, Tags=test_tags)
    client.untag_resource(ResourceArn=good_arn, TagKeys=[test_tags[0]["Key"]])

    updated_rsp = client.list_tags_for_resource(ResourceArn=good_arn)
    assert tags == updated_rsp["Tags"]

    # Verify keys removed from AggregationAuthorization.  Add a new tag to
    # the current set of tags, then delete the new tag.  The original set
    # of tags should remain.
    response = client.put_aggregation_authorization(
        AuthorizedAccountId=ACCOUNT_ID,
        AuthorizedAwsRegion=TEST_REGION,
        Tags=[{"Key": f"{x}", "Value": f"{x}"} for x in range(10)],
    )
    agg_auth_arn = response["AggregationAuthorization"]["AggregationAuthorizationArn"]
    rsp = client.list_tags_for_resource(ResourceArn=agg_auth_arn)
    tags = rsp["Tags"]

    test_tags = [{"Key": "test_key", "Value": "test_value"}]
    client.tag_resource(ResourceArn=agg_auth_arn, Tags=test_tags)
    client.untag_resource(ResourceArn=agg_auth_arn, TagKeys=[test_tags[0]["Key"]])

    updated_rsp = client.list_tags_for_resource(ResourceArn=agg_auth_arn)
    assert tags == updated_rsp["Tags"]

    # Delete all the tags.
    rsp = client.list_tags_for_resource(ResourceArn=good_arn)
    client.untag_resource(ResourceArn=good_arn, TagKeys=[x["Key"] for x in rsp["Tags"]])

    updated_rsp = client.list_tags_for_resource(ResourceArn=good_arn)
    assert not updated_rsp["Tags"]

    # Verify keys removed from ConfigRule.  Add a new tag to the current set
    # of tags, then delete the new tag.  The original set of tags should remain.
    rule_name = f"config-rule-delete-tags-test-{random_string()}"
    client.put_config_rule(
        ConfigRule={
            "ConfigRuleName": rule_name,
            "Scope": {"ComplianceResourceTypes": ["AWS::IAM::Group"]},
            "Source": {"Owner": "AWS", "SourceIdentifier": "IAM_PASSWORD_POLICY"},
        },
        Tags=[{"Key": f"{x}", "Value": f"{x}"} for x in range(10)],
    )
    config_rule_arn = client.describe_config_rules(ConfigRuleNames=[rule_name])[
        "ConfigRules"
    ][0]["ConfigRuleArn"]
    tags = client.list_tags_for_resource(ResourceArn=config_rule_arn)["Tags"]

    test_tags = [{"Key": "cr_test_key", "Value": "cr_test_value"}]
    client.tag_resource(ResourceArn=config_rule_arn, Tags=test_tags)
    client.untag_resource(ResourceArn=config_rule_arn, TagKeys=[test_tags[0]["Key"]])

    updated_rsp = client.list_tags_for_resource(ResourceArn=config_rule_arn)
    assert tags == updated_rsp["Tags"]


@mock_config
def test_list_tags_for_resource():
    """Test the ConfigSource API list_tags_for_resource()."""
    client = boto3.client("config", region_name=TEST_REGION)

    # Try an invalid ARN.
    bad_arn = "bad_arn"
    with pytest.raises(ClientError) as cerr:
        client.list_tags_for_resource(ResourceArn=bad_arn)
    assert cerr.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        f"ResourceArn '{bad_arn}' does not exist"
        in cerr.value.response["Error"]["Message"]
    )

    # Create some configs and use the ARN from one of them for testing the
    # tags argument.
    config_aggs = config_aggregators_info(client)
    good_arn = config_aggs[1]["arn"]

    # Try a limit that is out of range (> 100).
    with pytest.raises(ClientError) as cerr:
        client.list_tags_for_resource(ResourceArn=good_arn, Limit=101)
    assert cerr.value.response["Error"]["Code"] == "InvalidLimitException"
    assert (
        "Value '101' at 'limit' failed to satisfy constraint"
        in cerr.value.response["Error"]["Message"]
    )

    # Verify there are 10 tags, 10 through 19.
    expected_tags = [{"Key": f"{x}", "Value": f"{x}"} for x in range(10, 20)]
    rsp = client.list_tags_for_resource(ResourceArn=good_arn)
    assert expected_tags == rsp["Tags"]
