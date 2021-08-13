"""Unit tests specific to the ConfigService ConfigRule APIs.

 These APIs include:
   put_config_rule
   describe_config_rule
   delete_config_rule
"""
import string

import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import ParamValidationError
import pytest

from moto.config import mock_config
from moto.config.models import random_string
from moto.config.models import ConfigRule
from moto.core import ACCOUNT_ID

TEST_REGION = "us-east-1"


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
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal(
        "MaxNumberOfConfigRulesExceededException"
    )
    exc_value.response["Error"]["Message"].should.contain(
        "maximum number of config rules"
    )

    # Free up the memory from the limits test.
    for idx in range(ConfigRule.MAX_RULES):
        client.delete_config_rule(ConfigRuleName=f"{rule_name_base}_{idx}")

    # Rule name that exceeds 128 chars in length.
    rule_name = string.ascii_lowercase * 5
    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleName"] = rule_name
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("ValidationException")
    exc_value.response["Error"]["Message"].should.contain(
        "Member must have length less than or equal to 128"
    )

    # Tag key that isn't "Key" or "Value".
    with pytest.raises(ParamValidationError) as exc:
        client.put_config_rule(ConfigRule=managed_config_rule(), Tags=[{"Test": "abc"}])
    assert 'Unknown parameter in Tags[0]: "Test", must be one of: Key, Value' in str(
        exc
    )


@mock_config
def test_config_rule_errors():  # pylint: disable=too-many-statements
    """Test various error conditions in ConfigRule instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)

    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleName"] = ""
    with pytest.raises(ParamValidationError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    # boto3 has a much nicer error, but moto performs an earlier check on
    # parameters using botocore and the error is not as nice.  Here's boto3's
    # error message:
    #
    # botocore.errorfactory.InvalidParameterValueException: An error occurred
    # (InvalidParameterValueException) when calling the PutConfigRule
    # operation: One or more identifiers needs to be provided. Provide Name
    # or Id or Arn
    assert "Invalid length for parameter ConfigRule.ConfigRuleName" in str(exc)

    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleArn"] = "arn"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "ConfigRule Arn and Id can not be specified when creating a new ConfigRule."
    )

    managed_rule = managed_config_rule()
    managed_rule["Source"] = None
    with pytest.raises(ParamValidationError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    # moto catches this error earlier and prints a different error than boto3:
    #
    # botocore.exceptions.ParamValidationError: Parameter validation failed:
    # Missing required parameter in ConfigRule: "Source"
    assert "Invalid type for parameter ConfigRule.Source, value: None" in str(exc)

    managed_rule = managed_config_rule()
    bad_json_string = "{'name': 'test', 'type': null, }"
    managed_rule["InputParameters"] = bad_json_string
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        f"Invalid json {bad_json_string} passed in the InputParameters field"
    )

    managed_rule = managed_config_rule()
    managed_rule["MaximumExecutionFrequency"] = "HOUR"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("ValidationException")
    exc_value.response["Error"]["Message"].should.contain(
        "Member must satisfy enum value set ['TwentyFour_Hours', "
        "'Twelve_Hours', 'Three_Hours', 'Six_Hours', 'One_Hour']"
    )

    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleState"] = "BOGUS"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("ValidationException")
    exc_value.response["Error"]["Message"].should.contain(
        "Value 'BOGUS' at 'configRule.configRuleState' failed to satisfy "
        "constraint: Member must satisfy enum value set: ['ACTIVE', "
        "'DELETING', 'DELETING_RESULTS', 'EVALUATION']"
    )

    managed_rule = managed_config_rule()
    managed_rule["ConfigRuleState"] = "DELETING"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "The ConfigRuleState DELETING is invalid.  Only the following values "
        "are permitted: ACTIVE"
    )

    managed_rule = managed_config_rule()
    managed_rule["CreatedBy"] = "tester"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "AWS Config populates the CreatedBy field for ServiceLinkedConfigRule. "
        "Try again without populating the CreatedBy field"
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
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "Tag key should not be empty when tag value is provided in scope"
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["ComplianceResourceId"] = "12345"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "A single resourceType should be provided when resourceId is provided "
        "in scope"
    )

    managed_rule = managed_config_rule()
    tag_key = "hellobye" * 16 + "x"
    managed_rule["Scope"]["TagKey"] = tag_key
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("ValidationException")
    exc_value.response["Error"]["Message"].should.contain(
        f"Value '{tag_key}' at 'ConfigRule.Scope.TagKey' failed to satisfy "
        f"constraint: Member must have length less than or equal to 128"
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagKey"] = "test"
    tag_value = "01234567890123456" * 16 + "x"
    managed_rule["Scope"]["TagValue"] = tag_value
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("ValidationException")
    exc_value.response["Error"]["Message"].should.contain(
        f"Value '{tag_value}' at 'ConfigRule.Scope.TagValue' failed to "
        f"satisfy constraint: Member must have length less than or equal to "
        f"256"
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagKey"] = "test"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "Scope cannot be applied to both resource and tag"
    )

    managed_rule = managed_config_rule()
    managed_rule["Scope"]["TagKey"] = "test_key"
    managed_rule["Scope"]["ComplianceResourceTypes"] = []
    managed_rule["Scope"]["ComplianceResourceId"] = "12345"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "Scope cannot be applied to both resource and tag"
    )


@mock_config
def test_config_rules_source_errors():  # pylint: disable=too-many-statements
    """Test various error conditions in ConfigRule.Source instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)

    managed_rule = managed_config_rule()
    managed_rule["Source"] = {"Owner": "AWS"}
    with pytest.raises(ParamValidationError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    assert 'Missing required parameter in ConfigRule.Source: "SourceIdentifier"' in str(
        exc
    )

    managed_rule = managed_config_rule()
    managed_rule["Source"]["Owner"] = "test"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("ValidationException")
    exc_value.response["Error"]["Message"].should.contain(
        "Member must satisfy enum value set: ['CUSTOM_LAMBDA', 'AWS']"
    )

    managed_rule = managed_config_rule()
    managed_rule["Source"]["SourceIdentifier"] = "test"
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "The sourceIdentifier test is invalid.  Please refer to the "
        "documentation for a list of valid sourceIdentifiers that can be used "
        "when AWS is the Owner"
    )

    managed_rule = managed_config_rule()
    managed_rule["Source"]["SourceDetails"] = [
        {"EventSource": "aws.config", "MessageType": "ScheduledNotification"}
    ]
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=managed_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "SourceDetails should be null/empty if the owner is AWS. "
        "SourceDetails should be provided if the owner is CUSTOM_LAMBDA"
    )

    custom_rule = custom_config_rule()
    custom_rule["Source"] = {
        "Owner": "CUSTOM_LAMBDA",
        "SourceIdentifier": "test",
    }
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterValueException")
    exc_value.response["Error"]["Message"].should.contain(
        "SourceDetails should be null/empty if the owner is AWS. "
        "SourceDetails should be provided if the owner is CUSTOM_LAMBDA"
    )

    custom_rule = custom_config_rule()
    with pytest.raises(ClientError) as exc:
        client.put_config_rule(ConfigRule=custom_rule)
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InsufficientPermissionsException")
    exc_value.response["Error"]["Message"].should.contain(
        f'The AWS Lambda function {custom_rule["Source"]["SourceIdentifier"]} '
        f"cannot be invoked. Check the specified function ARN, and check the "
        f"function's permissions"
    )


@mock_config
def test_config_rules_source_details_errors():
    """Test error conditions with ConfigRule.Source_Details instantiation."""
    client = boto3.client("config", region_name=TEST_REGION)


#    TODO
#    custom_rule = custom_config_rule()
#    custom_rule["Source"]["SourceDetails"][0] = {"MessageType": "ScheduledNotification"}
#    with pytest.raises(ClientError) as exc:
#        client.put_config_rule(ConfigRule=custom_rule)
#    exc_value = exc.value
#    exc_value.operation_name.should.equal("PutConfigRule")
#    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
#    exc_value.response["Error"]["Code"].should.equal("InsufficientPermissionsException")
#    exc_value.response["Error"]["Message"].should.contain(
#         'Missing x required parameter in ConfigRule.SourceDetails: "EventSource"'
#    )


@mock_config
def test_valid_put_config_rule():
    """Test valid put_config_rule API calls."""
    client = boto3.client("config", region_name=TEST_REGION)
    # test both managed and custom, compare field results using describe
    # TODO


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
    # TODO
    # assert not client.describe_aggregation_authorizations()["AggregationAuthorizations"]

    # Try it again -- it should error indicating the rule could not be found.
    with pytest.raises(ClientError) as exc:
        client.delete_config_rule(ConfigRuleName=rule_name)
    exc_value = exc.value
    exc_value.operation_name.should.equal("DeleteConfigRule")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("NoSuchConfigRuleException")
    exc_value.response["Error"]["Message"].should.contain(
        f"The ConfigRule '{rule_name}' provided in the request is invalid"
    )

    # TODO - test the config_rule_state
