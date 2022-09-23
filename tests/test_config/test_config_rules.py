"""Unit tests specific to the ConfigService ConfigRule APIs.

 These APIs include:
   put_config_rule
   describe_config_rule
   delete_config_rule
"""
import json
from string import ascii_lowercase

import boto3
from botocore.exceptions import ClientError
import pytest

from moto.config import mock_config
from moto.config.models import ConfigRule, CONFIG_RULE_PAGE_SIZE
from moto import settings
from moto.moto_api._internal import mock_random

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


def managed_config_rule():
    """Return a valid managed AWS Config Rule."""
    return {
        "ConfigRuleName": f"managed_rule_{mock_random.get_random_string()}",
        "Description": "Managed S3 Public Read Prohibited Bucket Rule",
        "Scope": {"ComplianceResourceTypes": ["AWS::S3::Bucket", "AWS::IAM::Group"]},
        "Source": {
            "Owner": "AWS",
            "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
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
    # rule_name = f"managed_rule_{mock_random.get_random_string()}"
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
def test_valid_put_config_managed_rule():
    """Test valid put_config_rule API calls for managed rules."""
    client = boto3.client("config", region_name=TEST_REGION)

    # Create managed rule and compare input against describe_config_rule()
    # output.
    managed_rule = managed_config_rule()
    managed_rule["Source"]["SourceIdentifier"] = "IAM_PASSWORD_POLICY"
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
    managed_rule["MaximumExecutionFrequency"] = "Six_Hours"
    managed_rule["InputParameters"] = "{}"
    client.put_config_rule(ConfigRule=managed_rule)

    rsp = client.describe_config_rules(ConfigRuleNames=[managed_rule["ConfigRuleName"]])
    managed_rule_json = json.dumps(managed_rule, sort_keys=True)
    rsp_json = json.dumps(rsp["ConfigRules"][0], sort_keys=True)
    assert managed_rule_json == rsp_json

    # Valid InputParameters.
    managed_rule = {
        "ConfigRuleName": f"input_param_test_{mock_random.get_random_string()}",
        "Description": "Provide subset of allowed input parameters",
        "InputParameters": '{"blockedPort1":"22","blockedPort2":"3389"}',
        "Scope": {"ComplianceResourceTypes": ["AWS::IAM::SecurityGroup"]},
        "Source": {"Owner": "AWS", "SourceIdentifier": "RESTRICTED_INCOMING_TRAFFIC"},
    }
    client.put_config_rule(ConfigRule=managed_rule)

    rsp = client.describe_config_rules(ConfigRuleNames=[managed_rule["ConfigRuleName"]])
    managed_rule_json = json.dumps(managed_rule, sort_keys=True)
    new_config_rule = rsp["ConfigRules"][0]
    del new_config_rule["ConfigRuleArn"]
    del new_config_rule["ConfigRuleId"]
    del new_config_rule["ConfigRuleState"]
    rsp_json = json.dumps(new_config_rule, sort_keys=True)
    assert managed_rule_json == rsp_json


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
