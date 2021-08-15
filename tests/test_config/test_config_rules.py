"""Unit tests specific to the ConfigService ConfigRule APIs.

 These APIs include:
   put_config_rule
   describe_config_rule
   delete_config_rule
"""
from io import BytesIO
from string import ascii_lowercase
from zipfile import ZipFile, ZIP_DEFLATED

import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import ParamValidationError
import pytest

from moto.config import mock_config
from moto.config.models import random_string
from moto.config.models import ConfigRule
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
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        exc_value.response["Error"]["Code"] == "MaxNumberOfConfigRulesExceededException"
    )
    assert "maximum number of config rules" in exc_value.response["Error"]["Message"]

    # Free up the memory from the limits test.
    for idx in range(ConfigRule.MAX_RULES):
        client.delete_config_rule(ConfigRuleName=f"{rule_name_base}_{idx}")

    # Rule name that exceeds 128 chars in length.
    rule_name = ascii_lowercase * 5
    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleName"] = rule_name
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ValidationException"
    assert (
        "Member must have length less than or equal to 128"
        in exc_value.response["Error"]["Message"]
    )


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
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "One or more identifiers needs to be provided. Provide Name or Id or Arn"
        in exc_value.response["Error"]["Message"]
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
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "One or more identifiers needs to be provided. Provide Name or Id or Arn"
        in exc_value.response["Error"]["Message"]
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
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "ConfigRule Arn and Id can not be specified when creating a new "
        "ConfigRule." in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    bad_json_string = "{'name': 'test', 'type': null, }"
    managed_rule["InputParameters"] = bad_json_string
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        f"Invalid json {bad_json_string} passed in the InputParameters field"
        in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["MaximumExecutionFrequency"] = "HOUR"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ValidationException"
    assert (
        "Member must satisfy enum value set: {One_Hour, Six_Hours, "
        "Three_Hours, Twelve_Hours, TwentyFour_Hours}"
        in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleState"] = "BOGUS"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ValidationException"
    assert (
        "Value 'BOGUS' at 'configRule.configRuleState' failed to satisfy "
        "constraint: Member must satisfy enum value set: {ACTIVE, "
        "DELETING, DELETING_RESULTS, EVALUATING}"
        in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleState"] = "DELETING"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "The ConfigRuleState DELETING is invalid.  Only the following values "
        "are permitted: ACTIVE" in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["CreatedBy"] = "tester"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "AWS Config populates the CreatedBy field for ServiceLinkedConfigRule. "
        "Try again without populating the CreatedBy field"
        in exc_value.response["Error"]["Message"]
    )


@mock_config
def test_config_rules_scope_errors():  # pylint: disable=too-many-statements
    """Test various error conditions in ConfigRule.Scope instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagValue"] = "tester"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "Tag key should not be empty when tag value is provided in scope"
        in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["ComplianceResourceId"] = "12345"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "A single resourceType should be provided when resourceId is provided "
        "in scope" in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    tag_key = "hellobye" * 16 + "x"
    managed_rule["Scope"]["TagKey"] = tag_key
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ValidationException"
    assert (
        f"Value '{tag_key}' at 'ConfigRule.Scope.TagKey' failed to satisfy "
        f"constraint: Member must have length less than or equal to 128"
        in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagKey"] = "test"
    tag_value = "01234567890123456" * 16 + "x"
    managed_rule["Scope"]["TagValue"] = tag_value
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ValidationException"
    assert (
        f"Value '{tag_value}' at 'ConfigRule.Scope.TagValue' failed to "
        f"satisfy constraint: Member must have length less than or equal to "
        f"256" in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagKey"] = "test"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "Scope cannot be applied to both resource and tag"
        in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagKey"] = "test_key"
    managed_rule["Scope"]["ComplianceResourceTypes"] = []
    managed_rule["Scope"]["ComplianceResourceId"] = "12345"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "Scope cannot be applied to both resource and tag"
        in exc_value.response["Error"]["Message"]
    )


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
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ValidationException"
    assert (
        "Member must satisfy enum value set: {AWS, CUSTOM_LAMBDA}"
        in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Source"]["SourceIdentifier"] = "test"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "The sourceIdentifier test is invalid.  Please refer to the "
        "documentation for a list of valid sourceIdentifiers that can be used "
        "when AWS is the Owner" in exc_value.response["Error"]["Message"]
    )

    managed_rule = managed_config_rule()
    managed_rule["Source"]["SourceDetails"] = [
        {"EventSource": "aws.config", "MessageType": "ScheduledNotification"}
    ]
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "SourceDetails should be null/empty if the owner is AWS. "
        "SourceDetails should be provided if the owner is CUSTOM_LAMBDA"
        in exc_value.response["Error"]["Message"]
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"] = {
        "Owner": "CUSTOM_LAMBDA",
        "SourceIdentifier": "test",
    }
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "SourceDetails should be null/empty if the owner is AWS. "
        "SourceDetails should be provided if the owner is CUSTOM_LAMBDA"
        in exc_value.response["Error"]["Message"]
    )

    custom_rule = custom_config_rule()
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InsufficientPermissionsException"
    assert (
        f'The AWS Lambda function {custom_rule["Source"]["SourceIdentifier"]} '
        f"cannot be invoked. Check the specified function ARN, and check the "
        f"function's permissions" in exc_value.response["Error"]["Message"]
    )


@mock_config
def test_config_rules_source_details_errors():
    """Test error conditions with ConfigRule.Source_Details instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)

    create_lambda_for_config_rule()

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0] = {"MessageType": "ScheduledNotification"}
    with pytest.raises(ParamValidationError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    assert (
        'Missing required parameter in ConfigRule.SourceDetails: "EventSource"'
        in str(exc)
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0]["EventSource"] = "foo"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ValidationException"
    assert (
        "Member must satisfy enum value set: {aws.config}"
        in exc_value.response["Error"]["Message"]
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0] = {"EventSource": "aws.config"}
    with pytest.raises(ParamValidationError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    assert (
        'Missing required parameter in ConfigRule.SourceDetails: "MessageType"'
        in str(exc)
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0] = {
        "MessageType": "foo",
        "EventSource": "aws.config",
    }
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ValidationException"
    assert (
        "Member must satisfy enum value set: "
        "{ConfigurationItemChangeNotification, "
        "ConfigurationSnapshotDeliveryCompleted, "
        "OversizedConfigurationItemChangeNotification, ScheduledNotification}"
        in exc_value.response["Error"]["Message"]
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0]["MaximumExecutionFrequency"] = "foo"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ValidationException"
    assert (
        "Member must satisfy enum value set: "
        "{One_Hour, Six_Hours, Three_Hours, Twelve_Hours, TwentyFour_Hours}"
        in exc_value.response["Error"]["Message"]
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"]["SourceDetails"][0][
        "MessageType"
    ] = "ConfigurationItemChangeNotification"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    exc_value = exc.value
    assert exc_value.operation_name == "PutConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "A maximum execution frequency is not allowed if MessageType "
        "is ConfigurationItemChangeNotification or "
        "OversizedConfigurationItemChangeNotification"
        in exc_value.response["Error"]["Message"]
    )


@mock_config
def test_valid_put_config_rule():
    """Test valid put_config_rule API calls."""
    client = boto3.client("config", region_name=TEST_REGION)
    # test both managed and custom, compare field results using describe
    # test update
    # TODO


@mock_config
def test_describe_config_rules():
    """Test the describe_config_rules API."""
    client = boto3.client("config", region_name=TEST_REGION)

    response = client.describe_config_rules()
    assert len(response["ConfigRules"]) == 0

    rule_name_base = "describe_test_"
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
    exc_value = exc.value
    assert exc_value.operation_name == "DescribeConfigRules"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "NoSuchConfigRuleException"
    assert (
        "The ConfigRule 'fooey' provided in the request is invalid"
        in exc_value.response["Error"]["Message"]
    )

    response = client.describe_config_rules(
        ConfigRuleNames=[
            f"{rule_name_base}_1",
            f"{rule_name_base}_10",
            f"{rule_name_base}_20",
        ]
    )
    assert len(response["ConfigRules"]) == 3

    response = client.describe_config_rules()
    assert len(response["ConfigRules"]) == ConfigRule.MAX_RULES

    # TODO test tokens: InvalidNextTokenException, good token
    # TODO test content of response


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
    exc_value = exc.value
    assert exc_value.operation_name == "DeleteConfigRule"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "NoSuchConfigRuleException"
    assert (
        f"The ConfigRule '{rule_name}' provided in the request is invalid"
        in exc_value.response["Error"]["Message"]
    )
