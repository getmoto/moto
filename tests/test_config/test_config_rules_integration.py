from .test_config_rules import managed_config_rule, TEST_REGION
from botocore.exceptions import ClientError
from moto import mock_config, mock_iam, mock_lambda
from moto.core import ACCOUNT_ID
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

import boto3
import json
import pytest


def custom_config_rule(func_name="test_config_rule"):
    """Return a valid custom AWS Config Rule."""
    return {
        "ConfigRuleName": f"custom_rule_{uuid4()}[:6]",
        "Description": "Custom S3 Public Read Prohibited Bucket Rule",
        "Scope": {"ComplianceResourceTypes": ["AWS::S3::Bucket", "AWS::IAM::Group"]},
        "Source": {
            "Owner": "CUSTOM_LAMBDA",
            "SourceIdentifier": f"arn:aws:lambda:{TEST_REGION}:{ACCOUNT_ID}:function:{func_name}",
            "SourceDetails": [
                {
                    "EventSource": "aws.config",
                    "MessageType": "ScheduledNotification",
                    "MaximumExecutionFrequency": "Three_Hours",
                },
            ],
        },
        "MaximumExecutionFrequency": "One_Hour",
    }


def zipped_lambda_function():
    """Return a simple test lambda function, zipped."""
    func_str = """
def lambda_handler(event, context):
    print("testing")
    return event
"""
    zip_output = BytesIO()
    with ZipFile(zip_output, "w", ZIP_DEFLATED) as zip_file:
        zip_file.writestr("lambda_function.py", func_str)
        zip_file.close()
        zip_output.seek(0)
        return zip_output.read()


@mock_lambda
def create_lambda_for_config_rule():
    """Return the ARN of a lambda that can be used by a custom rule."""
    role_name = "test-role"
    lambda_role = None
    with mock_iam():
        iam_client = boto3.client("iam", region_name=TEST_REGION)
        try:
            lambda_role = iam_client.get_role(RoleName=role_name)["Role"]["Arn"]
        except ClientError:
            lambda_role = iam_client.create_role(
                RoleName=role_name, AssumeRolePolicyDocument="test policy", Path="/"
            )["Role"]["Arn"]

    # Create the lambda function and identify its location.
    lambda_client = boto3.client("lambda", region_name=TEST_REGION)
    lambda_client.create_function(
        FunctionName="test_config_rule",
        Runtime="python3.8",
        Role=lambda_role,
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zipped_lambda_function()},
        Description="Lambda test function for config rule",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )


@mock_config
def test_config_rules_source_details_errors():
    """Test error conditions with ConfigRule.Source_Details instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)

    create_lambda_for_config_rule()

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0] = {"MessageType": "ScheduledNotification"}
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ParamValidationError"
    assert (
        "Missing required parameter in ConfigRule.SourceDetails: 'EventSource'"
        in err["Message"]
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0]["EventSource"] = "foo"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "Member must satisfy enum value set: {aws.config}" in err["Message"]

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0] = {"EventSource": "aws.config"}
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ParamValidationError"
    assert (
        "Missing required parameter in ConfigRule.SourceDetails: 'MessageType'"
        in err["Message"]
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0] = {
        "MessageType": "foo",
        "EventSource": "aws.config",
    }
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        "Member must satisfy enum value set: "
        "{ConfigurationItemChangeNotification, "
        "ConfigurationSnapshotDeliveryCompleted, "
        "OversizedConfigurationItemChangeNotification, ScheduledNotification}"
        in err["Message"]
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0]["MaximumExecutionFrequency"] = "foo"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        "Member must satisfy enum value set: "
        "{One_Hour, Six_Hours, Three_Hours, Twelve_Hours, TwentyFour_Hours}"
        in err["Message"]
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0][
        "MessageType"
    ] = "ConfigurationItemChangeNotification"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "A maximum execution frequency is not allowed if MessageType "
        "is ConfigurationItemChangeNotification or "
        "OversizedConfigurationItemChangeNotification" in err["Message"]
    )


@mock_config
def test_valid_put_config_custom_rule():
    """Test valid put_config_rule API calls for custom rules."""
    client = boto3.client("config", region_name=TEST_REGION)
    # Create custom rule and compare input against describe_config_rule
    # output.
    create_lambda_for_config_rule()
    custom_rule = custom_config_rule()
    custom_rule["Scope"]["ComplianceResourceTypes"] = ["AWS::IAM::Group"]
    custom_rule["Scope"]["ComplianceResourceId"] = "basic_custom_test"
    custom_rule["InputParameters"] = '{"TestName":"true"}'
    custom_rule["ConfigRuleState"] = "ACTIVE"
    client.put_config_rule(ConfigRule=custom_rule)

    rsp = client.describe_config_rules(ConfigRuleNames=[custom_rule["ConfigRuleName"]])
    custom_rule_json = json.dumps(custom_rule, sort_keys=True)
    new_config_rule = rsp["ConfigRules"][0]
    rule_arn = new_config_rule.pop("ConfigRuleArn")
    rule_id = new_config_rule.pop("ConfigRuleId")
    rsp_json = json.dumps(new_config_rule, sort_keys=True)
    assert custom_rule_json == rsp_json

    # Update custom rule and compare again.
    custom_rule["ConfigRuleArn"] = rule_arn
    custom_rule["ConfigRuleId"] = rule_id
    custom_rule["Description"] = "Updated Managed S3 Public Read Rule"
    custom_rule["Scope"]["ComplianceResourceTypes"] = ["AWS::S3::Bucket"]
    custom_rule["Scope"]["ComplianceResourceId"] = "S3-BUCKET_VERSIONING_ENABLED"
    custom_rule["Source"]["SourceDetails"][0] = {
        "EventSource": "aws.config",
        "MessageType": "ConfigurationItemChangeNotification",
    }
    custom_rule["InputParameters"] = "{}"
    client.put_config_rule(ConfigRule=custom_rule)

    rsp = client.describe_config_rules(ConfigRuleNames=[custom_rule["ConfigRuleName"]])
    custom_rule_json = json.dumps(custom_rule, sort_keys=True)
    rsp_json = json.dumps(rsp["ConfigRules"][0], sort_keys=True)
    assert custom_rule_json == rsp_json

    # Update a custom rule specifying just the rule Id.  Test the default
    # value for MaximumExecutionFrequency while we're at it.
    del custom_rule["ConfigRuleArn"]
    rule_name = custom_rule.pop("ConfigRuleName")
    custom_rule["Source"]["SourceDetails"][0] = {
        "EventSource": "aws.config",
        "MessageType": "ConfigurationSnapshotDeliveryCompleted",
    }
    client.put_config_rule(ConfigRule=custom_rule)
    rsp = client.describe_config_rules(ConfigRuleNames=[rule_name])
    updated_rule = rsp["ConfigRules"][0]
    assert updated_rule["ConfigRuleName"] == rule_name
    assert (
        updated_rule["Source"]["SourceDetails"][0]["MaximumExecutionFrequency"]
        == "TwentyFour_Hours"
    )

    # Update a custom rule specifying just the rule ARN.
    custom_rule["ConfigRuleArn"] = rule_arn
    del custom_rule["ConfigRuleId"]
    custom_rule["MaximumExecutionFrequency"] = "Six_Hours"
    client.put_config_rule(ConfigRule=custom_rule)
    rsp = client.describe_config_rules(ConfigRuleNames=[rule_name])
    updated_rule = rsp["ConfigRules"][0]
    assert updated_rule["ConfigRuleName"] == rule_name
    assert updated_rule["MaximumExecutionFrequency"] == "Six_Hours"


@mock_config
def test_config_rules_source_errors():  # pylint: disable=too-many-statements
    """Test various error conditions in ConfigRule.Source instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)

    # Missing fields (ParamValidationError) caught by botocore and not
    # tested here:  ConfigRule.Source.SourceIdentifier

    managed_rule = managed_config_rule()
    managed_rule["Source"]["Owner"] = "test"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "Member must satisfy enum value set: {AWS, CUSTOM_LAMBDA}" in err["Message"]

    managed_rule = managed_config_rule()
    managed_rule["Source"]["SourceIdentifier"] = "test"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "The sourceIdentifier test is invalid.  Please refer to the "
        "documentation for a list of valid sourceIdentifiers that can be used "
        "when AWS is the Owner" in err["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Source"]["SourceDetails"] = [
        {"EventSource": "aws.config", "MessageType": "ScheduledNotification"}
    ]
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "SourceDetails should be null/empty if the owner is AWS. "
        "SourceDetails should be provided if the owner is CUSTOM_LAMBDA"
        in err["Message"]
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"] = {
        "Owner": "CUSTOM_LAMBDA",
        "SourceIdentifier": "test",
    }
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "SourceDetails should be null/empty if the owner is AWS. "
        "SourceDetails should be provided if the owner is CUSTOM_LAMBDA"
        in err["Message"]
    )

    custom_rule = custom_config_rule(func_name="unknown_func")
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InsufficientPermissionsException"
    assert (
        f'The AWS Lambda function {custom_rule["Source"]["SourceIdentifier"]} '
        f"cannot be invoked. Check the specified function ARN, and check the "
        f"function's permissions" in err["Message"]
    )
