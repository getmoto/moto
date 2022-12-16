from collections import defaultdict
import json
from .models import Key
from .exceptions import AccessDeniedException


ALTERNATIVE_ACTIONS = defaultdict(list)
ALTERNATIVE_ACTIONS["kms:DescribeKey"] = ["kms:*", "kms:Describe*", "kms:DescribeKey"]


def validate_policy(key: Key, action: str):
    """
    Relevant docs:
     - https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-default.html
     - https://docs.aws.amazon.com/kms/latest/developerguide/policy-evaluation.html

    This method currently denies action based on whether:
     - There is a applicable DENY-statement in the policy
    """
    try:
        policy = json.loads(key.policy)
    except (ValueError, AttributeError):
        return
    for statement in policy.get("Statement", []):
        statement_applies = check_statement(statement, key.arn, action)
        if statement_applies and statement.get("Effect", "").lower() == "deny":
            raise AccessDeniedException(
                message=f"Action {action} is now allowed by the given key policy"
            )


def check_statement(statement, resource, action):
    return action_matches(statement.get("Action", []), action) and resource_matches(
        statement.get("Resource", ""), resource
    )


def action_matches(applicable_actions, action):
    alternatives = ALTERNATIVE_ACTIONS[action]
    if any(alt in applicable_actions for alt in alternatives):
        return True
    return False


def resource_matches(applicable_resources, resource):  # pylint: disable=unused-argument
    if applicable_resources == "*":
        return True
    return False
