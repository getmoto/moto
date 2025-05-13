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
    # TODO: Test managed_rules, want to add logic in the model for the json
    # Want to make sure it errors out if it is a managed_rule and we try to delete
    # Want to ensure the count of remaining (and correct) insight rules exists
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
            RuleState='ENABLED'
        )
        response_two = cloudwatch.describe_insight_rules()

        print("Response Two")
        print(response_two)
        print(len(response_two["InsightRules"]))
    except Exception as e:
        print(f"Error creating rule '{rule_name}': {e}")


if __name__ == "__main__":
    # Example usage
    rule_name = "MySampleInsightRule"
    log_group_name = "my-log-group"  # Replace with your actual log group name

    create_insight_rule(rule_name, log_group_name)
