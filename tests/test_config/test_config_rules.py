"""Unit tests specific to the ConfigService ConfigRule APIs.

 These APIs include:
   put_config_rule
   describe_config_rule
   delete_config_rule
"""
from io import BytesIO
import json
from string import ascii_lowercase
from zipfile import ZipFile, ZIP_DEFLATED

import boto3
from botocore.exceptions import ClientError
import pytest

from moto.config import mock_config
from moto.config.models import random_string
from moto.config.models import ConfigRule, CONFIG_RULE_PAGE_SIZE
from moto.core import ACCOUNT_ID
from moto import settings, mock_iam, mock_lambda

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


def managed_config_rule():
    """Return a valid managed AWS Config Rule."""
    return {
        "ConfigRuleName": f"managed_rule_{random_string()}",
        "Description": "Managed S3 Public Read Prohibited Bucket Rule",
        "Scope": {"ComplianceResourceTypes": ["AWS::S3::Bucket", "AWS::IAM::Group"]},
        "Source": {
            "Owner": "AWS",
            "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
        },
        "MaximumExecutionFrequency": "One_Hour",
    }


def custom_config_rule():
    """Return a valid custom AWS Config Rule."""
    return {
        "ConfigRuleName": f"custom_rule_{random_string()}",
        "Description": "Custom S3 Public Read Prohibited Bucket Rule",
        "Scope": {"ComplianceResourceTypes": ["AWS::S3::Bucket", "AWS::IAM::Group"]},
        "Source": {
            "Owner": "CUSTOM_LAMBDA",
            "SourceIdentifier": f"arn:aws:lambda:{TEST_REGION}:{ACCOUNT_ID}:function:test_config_rule",
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
                RoleName=role_name, AssumeRolePolicyDocument="test policy", Path="/",
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
def test_put_config_rule_errors():
    """Test various error conditions in put_config_rule API call."""
    client = boto3.client("config", region_name=TEST_REGION)

    rule_name_base = "cf_limit_test"
    for idx in range(ConfigRule.MAX_RULES):
        managed_rule = managed_config_rule()
        managed_rule["ConfigRuleName"] = f"{rule_name_base}_{idx}"
        client.put_config_rule(ConfigRule=managed_rule)

    with pytest.raises(ClientError) as exc:
        managed_rule = managed_config_rule()
        managed_rule["ConfigRuleName"] = f"{rule_name_base}_{ConfigRule.MAX_RULES}"
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "MaxNumberOfConfigRulesExceededException"
    assert "maximum number of config rules" in err["Message"]

    # Free up the memory from the limits test.
    for idx in range(ConfigRule.MAX_RULES):
        client.delete_config_rule(ConfigRuleName=f"{rule_name_base}_{idx}")

    # Rule name that exceeds 128 chars in length.
    rule_name = ascii_lowercase * 5
    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleName"] = rule_name
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "Member must have length less than or equal to 128" in err["Message"]


@mock_config
def test_put_config_rule_update_errors():
    """Test various error conditions when updating ConfigRule."""
    client = boto3.client("config", region_name=TEST_REGION)

    # No name, arn or id.
    managed_rule = {
        "Description": "Managed S3 Public Read Prohibited Bucket Rule",
        "Scope": {"ComplianceResourceTypes": ["AWS::S3::Bucket"]},
        "Source": {
            "Owner": "AWS",
            "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
        },
    }
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "One or more identifiers needs to be provided. Provide Name or Id or Arn"
        in err["Message"]
    )

    # Provide an id for a rule that does not exist.
    managed_rule = {
        "ConfigRuleId": "foo",
        "Description": "Managed S3 Public Read Prohibited Bucket Rule",
        "Scope": {"ComplianceResourceTypes": ["AWS::S3::Bucket"]},
        "Source": {
            "Owner": "AWS",
            "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
        },
    }
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "One or more identifiers needs to be provided. Provide Name or Id or Arn"
        in err["Message"]
    )


@mock_config
def test_config_rule_errors():  # pylint: disable=too-many-statements
    """Test various error conditions in ConfigRule instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)

    # Missing fields (ParamValidationError) caught by botocore and not
    # tested here:  ConfigRule.Source, ConfigRule.ConfigRuleName

    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleArn"] = "arn"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "ConfigRule Arn and Id can not be specified when creating a new "
        "ConfigRule." in err["Message"]
    )

    managed_rule = managed_config_rule()
    bad_json_string = "{'name': 'test', 'type': null, }"
    managed_rule["InputParameters"] = bad_json_string
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        f"Invalid json {bad_json_string} passed in the InputParameters field"
        in err["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["MaximumExecutionFrequency"] = "HOUR"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        "Member must satisfy enum value set: {One_Hour, Six_Hours, "
        "Three_Hours, Twelve_Hours, TwentyFour_Hours}" in err["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleState"] = "BOGUS"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        "Value 'BOGUS' at 'configRule.configRuleState' failed to satisfy "
        "constraint: Member must satisfy enum value set: {ACTIVE, "
        "DELETING, DELETING_RESULTS, EVALUATING}" in err["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleState"] = "DELETING"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "The ConfigRuleState DELETING is invalid.  Only the following values "
        "are permitted: ACTIVE" in err["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["CreatedBy"] = "tester"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "AWS Config populates the CreatedBy field for ServiceLinkedConfigRule. "
        "Try again without populating the CreatedBy field" in err["Message"]
    )


@mock_config
def test_aws_managed_rule_errors():
    """Test various error conditions in ConfigRule instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)

    # Extra, unknown input parameter should raise an error.
    managed_rule = managed_config_rule()
    managed_rule["Source"]["SourceIdentifier"] = "IAM_PASSWORD_POLICY"
    managed_rule["InputParameters"] = '{"RequireNumbers":"true","Extra":"10"}'
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        f"Unknown parameters provided in the inputParameters: "
        f"{managed_rule['InputParameters']}" in err["Message"]
    )

    # Missing required parameters should raise an error.
    managed_rule = managed_config_rule()
    managed_rule["Source"]["SourceIdentifier"] = "CLOUDWATCH_ALARM_ACTION_CHECK"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "The required parameter [alarmActionRequired, "
        "insufficientDataActionRequired, okActionRequired] is not present "
        "in the inputParameters" in err["Message"]
    )

    # If no MaxExecutionFrequency specified, set it to the default.
    # rule_name = f"managed_rule_{random_string()}"
    # managed_rule = {
    #     "ConfigRuleName": rule_name,
    #     "Description": "Managed S3 Public Read Prohibited Bucket Rule",
    #     "Scope": {"ComplianceResourceTypes": ["AWS::IAM::Group"]},
    #     "Source": {
    #         "Owner": "AWS",
    #         "SourceIdentifier": "IAM_PASSWORD_POLICY",
    #     },
    # }
    # client.put_config_rule(ConfigRule=managed_rule)
    # rsp = client.describe_config_rules(ConfigRuleNames=[rule_name])
    # new_config_rule = rsp["ConfigRules"][0]
    # assert new_config_rule["MaximumExecutionFrequency"] == "TwentyFour_Hours"


@mock_config
def test_config_rules_scope_errors():  # pylint: disable=too-many-statements
    """Test various error conditions in ConfigRule.Scope instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagValue"] = "tester"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "Tag key should not be empty when tag value is provided in scope"
        in err["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["ComplianceResourceId"] = "12345"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        "A single resourceType should be provided when resourceId is provided "
        "in scope" in err["Message"]
    )

    managed_rule = managed_config_rule()
    tag_key = "hellobye" * 16 + "x"
    managed_rule["Scope"]["TagKey"] = tag_key
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        f"Value '{tag_key}' at 'ConfigRule.Scope.TagKey' failed to satisfy "
        f"constraint: Member must have length less than or equal to 128"
        in err["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagKey"] = "test"
    tag_value = "01234567890123456" * 16 + "x"
    managed_rule["Scope"]["TagValue"] = tag_value
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        f"Value '{tag_value}' at 'ConfigRule.Scope.TagValue' failed to "
        f"satisfy constraint: Member must have length less than or equal to "
        f"256" in err["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagKey"] = "test"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert "Scope cannot be applied to both resource and tag" in err["Message"]

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagKey"] = "test_key"
    managed_rule["Scope"]["ComplianceResourceTypes"] = []
    managed_rule["Scope"]["ComplianceResourceId"] = "12345"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert "Scope cannot be applied to both resource and tag" in err["Message"]


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

    custom_rule = custom_config_rule()
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    err = exc.value.response["Error"]
    assert err["Code"] == "InsufficientPermissionsException"
    assert (
        f'The AWS Lambda function {custom_rule["Source"]["SourceIdentifier"]} '
        f"cannot be invoked. Check the specified function ARN, and check the "
        f"function's permissions" in err["Message"]
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
def test_valid_put_config_managed_rule():
    """Test valid put_config_rule API calls for managed rules."""
    client = boto3.client("config", region_name=TEST_REGION)

    # Create managed rule and compare input against describe_config_rule()
    # output.
    managed_rule = managed_config_rule()
    managed_rule["Scope"]["ComplianceResourceTypes"] = ["AWS::IAM::Group"]
    managed_rule["Scope"]["ComplianceResourceId"] = "basic_test"
    managed_rule["InputParameters"] = '{"RequireUppercaseCharacters":"true"}'
    managed_rule["ConfigRuleState"] = "ACTIVE"
    client.put_config_rule(ConfigRule=managed_rule)

    rsp = client.describe_config_rules(ConfigRuleNames=[managed_rule["ConfigRuleName"]])
    managed_rule_json = json.dumps(managed_rule, sort_keys=True)
    new_config_rule = rsp["ConfigRules"][0]
    rule_arn = new_config_rule.pop("ConfigRuleArn")
    rule_id = new_config_rule.pop("ConfigRuleId")
    rsp_json = json.dumps(new_config_rule, sort_keys=True)
    assert managed_rule_json == rsp_json

    # Update managed rule and compare again.
    managed_rule["ConfigRuleArn"] = rule_arn
    managed_rule["ConfigRuleId"] = rule_id
    managed_rule["Description"] = "Updated Managed S3 Public Read Rule"
    managed_rule["Scope"]["ComplianceResourceTypes"] = ["AWS::S3::Bucket"]
    managed_rule["Scope"]["ComplianceResourceId"] = "S3-BUCKET_VERSIONING_ENABLED"
    managed_rule["MaximumExecutionFrequency"] = "Six_Hours"
    managed_rule["InputParameters"] = "{}"
    client.put_config_rule(ConfigRule=managed_rule)

    rsp = client.describe_config_rules(ConfigRuleNames=[managed_rule["ConfigRuleName"]])
    managed_rule_json = json.dumps(managed_rule, sort_keys=True)
    rsp_json = json.dumps(rsp["ConfigRules"][0], sort_keys=True)
    assert managed_rule_json == rsp_json


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
def test_describe_config_rules():
    """Test the describe_config_rules API."""
    client = boto3.client("config", region_name=TEST_REGION)

    response = client.describe_config_rules()
    assert len(response["ConfigRules"]) == 0

    rule_name_base = "describe_test"
    for idx in range(ConfigRule.MAX_RULES):
        managed_rule = managed_config_rule()
        managed_rule["ConfigRuleName"] = f"{rule_name_base}_{idx}"
        client.put_config_rule(ConfigRule=managed_rule)

    with pytest.raises(ClientError) as exc:
        client.describe_config_rules(
            ConfigRuleNames=[
                f"{rule_name_base}_1",
                f"{rule_name_base}_10",
                "fooey",
                f"{rule_name_base}_20",
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchConfigRuleException"
    assert "The ConfigRule 'fooey' provided in the request is invalid" in err["Message"]

    # Request three specific ConfigRules.
    response = client.describe_config_rules(
        ConfigRuleNames=[
            f"{rule_name_base}_1",
            f"{rule_name_base}_10",
            f"{rule_name_base}_20",
        ]
    )
    assert len(response["ConfigRules"]) == 3

    # By default, if no ConfigRules are specified, all that can be fit on a
    # "page" will be returned.
    response = client.describe_config_rules()
    assert len(response["ConfigRules"]) == CONFIG_RULE_PAGE_SIZE

    # Test a bad token.
    with pytest.raises(ClientError) as exc:
        client.describe_config_rules(NextToken="foo")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidNextTokenException"
    assert "The nextToken provided is invalid" in err["Message"]

    # Loop using tokens, verifying the tokens are as expected.
    expected_tokens = [  # Non-alphanumeric sorted token numbers
        f"{rule_name_base}_120",
        f"{rule_name_base}_143",
        f"{rule_name_base}_31",
        f"{rule_name_base}_54",
        f"{rule_name_base}_77",
        None,
    ]
    idx = 0
    token = f"{rule_name_base}_0"
    while token:
        rsp = client.describe_config_rules(NextToken=token)
        token = rsp.get("NextToken")
        assert token == expected_tokens[idx]
        idx += 1


@mock_config
def test_delete_config_rules():
    """Test the delete_config_rule API."""
    client = boto3.client("config", region_name=TEST_REGION)

    # Create a ConfigRule:
    rule_name = "test_delete_config_rule"
    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleName"] = rule_name
    client.put_config_rule(ConfigRule=managed_rule)

    # Delete it:
    client.delete_config_rule(ConfigRuleName=rule_name)

    # Verify that none are there:
    assert not client.describe_config_rules()["ConfigRules"]

    # Try it again -- it should error indicating the rule could not be found.
    with pytest.raises(ClientError) as exc:
        client.delete_config_rule(ConfigRuleName=rule_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchConfigRuleException"
    assert (
        f"The ConfigRule '{rule_name}' provided in the request is invalid"
        in err["Message"]
    )
