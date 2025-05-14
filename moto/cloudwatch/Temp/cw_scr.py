import boto3
from moto import mock_aws

@mock_aws
def create_insight_rule(rule_name: str, log_group_name: str):
    """
    Create or update a CloudWatch Contributor Insights rule.

    Args:
        rule_name (str): Name of the insight rule.
        log_group_name (str): The name of the CloudWatch log group.
    """
    cloudwatch = boto3.client('cloudwatch', 'us-east-1')

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

    #############################
    # TODO: Test tagging
    try:
        response = cloudwatch.put_insight_rule(
            RuleName=rule_name,
            RuleDefinition=rule_body,
            RuleState='ENABLED'
        )
        cloudwatch.put_insight_rule(
            RuleName="rule_2",
            RuleDefinition=rule_body,
            RuleState='ENABLED'
        )
        cloudwatch.put_insight_rule(
            RuleName="rule_3",
            RuleDefinition=rule_body,
            RuleState='ENABLED',
            Tags=[{"Key":"ThisIsAKey", "Value":"ThisIsAValue"}]
        )
        response = cloudwatch.describe_insight_rules()
        print(f"Response: {len(response["InsightRules"])}")

        # DELTE
        delete_resp = cloudwatch.delete_insight_rules(RuleNames=["rule_3"])
        response = cloudwatch.describe_insight_rules()
        print(f"EXPECTING TWO HERE: {len(response["InsightRules"])}")

        # TAGS
        arn = f"arn:aws:cloudwatch:us-east-1:123456789012:insight-rule/rule_3"
        resp = cloudwatch.list_tags_for_resource(ResourceARN=arn)
        print(resp)

        # ENABLE STATE

        # DISABLE STATE
    except Exception as e:
        print(f"Error creating rule '{rule_name}': {e}")


if __name__ == "__main__":
    # Example usage
    rule_name = "MySampleInsightRule"
    log_group_name = "my-log-group"  # Replace with your actual log group name

    create_insight_rule(rule_name, log_group_name)
