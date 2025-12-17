import boto3
import pytest

from moto import mock_aws


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("eu-west-1", "aws"), ("cn-north-1", "aws-cn")]
)
def test_put_insight_rule(region, partition):
    cloudwatch = boto3.client("cloudwatch", region)

    rule_name = "MySampleInsightRule"
    log_group_name = "my-log-group"
    rule_body = f"""
    {{
      "Schema": "CloudWatchLogRule",
      "LogGroupNames": ["{log_group_name}"],
      "LogFormat": "JSON",
      "Filter": "[timestamp, request, statusCode = *]",
      "Contribution": {{
        "Keys": ["statusCode"],
        "ValueOf": "Count"
      }}
    }}
    """
    cloudwatch.put_insight_rule(
        RuleName=rule_name, RuleDefinition=rule_body, RuleState="ENABLED"
    )

    rules = cloudwatch.describe_insight_rules()["InsightRules"]
    assert len(rules) == 1
    rule = rules[0]
    assert rule["Name"] == "MySampleInsightRule"
    assert rule["State"] == "ENABLED"
    assert rule["Schema"] == '{"Name" : "CloudWatchLogRule", "Version" : 1}'
    assert rule["Definition"] == rule_body
    assert rule["ManagedRule"] is not True


@mock_aws
def test_delete_insight_rules():
    cloudwatch = boto3.client("cloudwatch", region_name="eu-central-1")

    rule_name = "MySampleInsightRule"
    log_group_name = "my-log-group"
    rule_body = f"""
    {{
      "Schema": "CloudWatchLogRule",
      "LogGroupNames": ["{log_group_name}"],
      "LogFormat": "JSON",
      "Filter": "[timestamp, request, statusCode = *]",
      "Contribution": {{
        "Keys": ["statusCode"],
        "ValueOf": "Count"
      }}
    }}
    """

    cloudwatch.put_insight_rule(
        RuleName=rule_name, RuleDefinition=rule_body, RuleState="ENABLED"
    )

    cloudwatch.put_insight_rule(
        RuleName=f"{rule_name}_Backup", RuleDefinition=rule_body, RuleState="ENABLED"
    )
    rules = cloudwatch.describe_insight_rules()["InsightRules"]
    assert len(rules) == 2

    cloudwatch.delete_insight_rules(RuleNames=[rule_name])
    rules = cloudwatch.describe_insight_rules()["InsightRules"]
    assert len(rules) == 1

    rule = rules[0]
    assert rule["Name"] == "MySampleInsightRule_Backup"


@mock_aws
def test_disable_insight_rules():
    cloudwatch = boto3.client("cloudwatch", region_name="eu-central-1")

    rule_name = "MySampleInsightRule"
    log_group_name = "my-log-group"
    rule_body = f"""
    {{
      "Schema": "CloudWatchLogRule",
      "LogGroupNames": ["{log_group_name}"],
      "LogFormat": "JSON",
      "Filter": "[timestamp, request, statusCode = *]",
      "Contribution": {{
        "Keys": ["statusCode"],
        "ValueOf": "Count"
      }}
    }}
    """

    cloudwatch.put_insight_rule(
        RuleName=rule_name, RuleDefinition=rule_body, RuleState="ENABLED"
    )

    cloudwatch.put_insight_rule(
        RuleName=f"{rule_name}_Backup", RuleDefinition=rule_body, RuleState="ENABLED"
    )

    cloudwatch.disable_insight_rules(RuleNames=[rule_name])

    rules = cloudwatch.describe_insight_rules()

    # Ensuring correct rule was disabled, other should remain enabled
    for r in rules["InsightRules"]:
        if r["Name"] == rule_name:
            assert r["State"] == "DISABLED"
        else:
            assert r["State"] == "ENABLED"


@mock_aws
def test_enable_insight_rules():
    cloudwatch = boto3.client("cloudwatch", region_name="eu-central-1")

    rule_name = "MySampleInsightRule"
    log_group_name = "my-log-group"
    rule_body = f"""
    {{
      "Schema": "CloudWatchLogRule",
      "LogGroupNames": ["{log_group_name}"],
      "LogFormat": "JSON",
      "Filter": "[timestamp, request, statusCode = *]",
      "Contribution": {{
        "Keys": ["statusCode"],
        "ValueOf": "Count"
      }}
    }}
    """

    cloudwatch.put_insight_rule(
        RuleName=rule_name, RuleDefinition=rule_body, RuleState="DISABLED"
    )

    cloudwatch.put_insight_rule(
        RuleName=f"{rule_name}_Backup", RuleDefinition=rule_body, RuleState="DISABLED"
    )

    cloudwatch.enable_insight_rules(RuleNames=[rule_name])

    rules = cloudwatch.describe_insight_rules()

    # Ensuring correct rule was enabled, other should remain disabled
    for r in rules["InsightRules"]:
        if r["Name"] == rule_name:
            assert r["State"] == "ENABLED"
        else:
            assert r["State"] == "DISABLED"
