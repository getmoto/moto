import json
import os
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError
from nose import SkipTest
from nose.tools import assert_raises

from moto import mock_s3
from moto.config import mock_config
from moto.core import ACCOUNT_ID

import sure  # noqa


@mock_config
def test_put_configuration_recorder():
    client = boto3.client("config", region_name="us-west-2")

    # Try without a name supplied:
    with assert_raises(ClientError) as ce:
        client.put_configuration_recorder(ConfigurationRecorder={"roleARN": "somearn"})
    assert (
        ce.exception.response["Error"]["Code"]
        == "InvalidConfigurationRecorderNameException"
    )
    assert "is not valid, blank string." in ce.exception.response["Error"]["Message"]

    # Try with a really long name:
    with assert_raises(ClientError) as ce:
        client.put_configuration_recorder(
            ConfigurationRecorder={"name": "a" * 257, "roleARN": "somearn"}
        )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"
    assert (
        "Member must have length less than or equal to 256"
        in ce.exception.response["Error"]["Message"]
    )

    # With resource types and flags set to True:
    bad_groups = [
        {
            "allSupported": True,
            "includeGlobalResourceTypes": True,
            "resourceTypes": ["item"],
        },
        {
            "allSupported": False,
            "includeGlobalResourceTypes": True,
            "resourceTypes": ["item"],
        },
        {
            "allSupported": True,
            "includeGlobalResourceTypes": False,
            "resourceTypes": ["item"],
        },
        {
            "allSupported": False,
            "includeGlobalResourceTypes": False,
            "resourceTypes": [],
        },
        {"includeGlobalResourceTypes": False, "resourceTypes": []},
        {"includeGlobalResourceTypes": True},
        {"resourceTypes": []},
        {},
    ]

    for bg in bad_groups:
        with assert_raises(ClientError) as ce:
            client.put_configuration_recorder(
                ConfigurationRecorder={
                    "name": "default",
                    "roleARN": "somearn",
                    "recordingGroup": bg,
                }
            )
        assert (
            ce.exception.response["Error"]["Code"] == "InvalidRecordingGroupException"
        )
        assert (
            ce.exception.response["Error"]["Message"]
            == "The recording group provided is not valid"
        )

    # With an invalid Resource Type:
    with assert_raises(ClientError) as ce:
        client.put_configuration_recorder(
            ConfigurationRecorder={
                "name": "default",
                "roleARN": "somearn",
                "recordingGroup": {
                    "allSupported": False,
                    "includeGlobalResourceTypes": False,
                    # 2 good, and 2 bad:
                    "resourceTypes": [
                        "AWS::EC2::Volume",
                        "LOLNO",
                        "AWS::EC2::VPC",
                        "LOLSTILLNO",
                    ],
                },
            }
        )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"
    assert "2 validation error detected: Value '['LOLNO', 'LOLSTILLNO']" in str(
        ce.exception.response["Error"]["Message"]
    )
    assert "AWS::EC2::Instance" in ce.exception.response["Error"]["Message"]

    # Create a proper one:
    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": False,
                "includeGlobalResourceTypes": False,
                "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
            },
        }
    )

    result = client.describe_configuration_recorders()["ConfigurationRecorders"]
    assert len(result) == 1
    assert result[0]["name"] == "testrecorder"
    assert result[0]["roleARN"] == "somearn"
    assert not result[0]["recordingGroup"]["allSupported"]
    assert not result[0]["recordingGroup"]["includeGlobalResourceTypes"]
    assert len(result[0]["recordingGroup"]["resourceTypes"]) == 2
    assert (
        "AWS::EC2::Volume" in result[0]["recordingGroup"]["resourceTypes"]
        and "AWS::EC2::VPC" in result[0]["recordingGroup"]["resourceTypes"]
    )

    # Now update the configuration recorder:
    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": True,
                "includeGlobalResourceTypes": True,
            },
        }
    )
    result = client.describe_configuration_recorders()["ConfigurationRecorders"]
    assert len(result) == 1
    assert result[0]["name"] == "testrecorder"
    assert result[0]["roleARN"] == "somearn"
    assert result[0]["recordingGroup"]["allSupported"]
    assert result[0]["recordingGroup"]["includeGlobalResourceTypes"]
    assert len(result[0]["recordingGroup"]["resourceTypes"]) == 0

    # With a default recording group (i.e. lacking one)
    client.put_configuration_recorder(
        ConfigurationRecorder={"name": "testrecorder", "roleARN": "somearn"}
    )
    result = client.describe_configuration_recorders()["ConfigurationRecorders"]
    assert len(result) == 1
    assert result[0]["name"] == "testrecorder"
    assert result[0]["roleARN"] == "somearn"
    assert result[0]["recordingGroup"]["allSupported"]
    assert not result[0]["recordingGroup"]["includeGlobalResourceTypes"]
    assert not result[0]["recordingGroup"].get("resourceTypes")

    # Can currently only have exactly 1 Config Recorder in an account/region:
    with assert_raises(ClientError) as ce:
        client.put_configuration_recorder(
            ConfigurationRecorder={
                "name": "someotherrecorder",
                "roleARN": "somearn",
                "recordingGroup": {
                    "allSupported": False,
                    "includeGlobalResourceTypes": False,
                },
            }
        )
    assert (
        ce.exception.response["Error"]["Code"]
        == "MaxNumberOfConfigurationRecordersExceededException"
    )
    assert (
        "maximum number of configuration recorders: 1 is reached."
        in ce.exception.response["Error"]["Message"]
    )


@mock_config
def test_put_configuration_aggregator():
    client = boto3.client("config", region_name="us-west-2")

    # With too many aggregation sources:
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[
                {
                    "AccountIds": ["012345678910", "111111111111", "222222222222"],
                    "AwsRegions": ["us-east-1", "us-west-2"],
                },
                {
                    "AccountIds": ["012345678910", "111111111111", "222222222222"],
                    "AwsRegions": ["us-east-1", "us-west-2"],
                },
            ],
        )
    assert (
        "Member must have length less than or equal to 1"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # With an invalid region config (no regions defined):
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[
                {
                    "AccountIds": ["012345678910", "111111111111", "222222222222"],
                    "AllAwsRegions": False,
                }
            ],
        )
    assert (
        "Your request does not specify any regions"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "InvalidParameterValueException"

    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            OrganizationAggregationSource={
                "RoleArn": "arn:aws:iam::012345678910:role/SomeRole"
            },
        )
    assert (
        "Your request does not specify any regions"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "InvalidParameterValueException"

    # With both region flags defined:
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[
                {
                    "AccountIds": ["012345678910", "111111111111", "222222222222"],
                    "AwsRegions": ["us-east-1", "us-west-2"],
                    "AllAwsRegions": True,
                }
            ],
        )
    assert (
        "You must choose one of these options"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "InvalidParameterValueException"

    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            OrganizationAggregationSource={
                "RoleArn": "arn:aws:iam::012345678910:role/SomeRole",
                "AwsRegions": ["us-east-1", "us-west-2"],
                "AllAwsRegions": True,
            },
        )
    assert (
        "You must choose one of these options"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "InvalidParameterValueException"

    # Name too long:
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="a" * 257,
            AccountAggregationSources=[
                {"AccountIds": ["012345678910"], "AllAwsRegions": True}
            ],
        )
    assert "configurationAggregatorName" in ce.exception.response["Error"]["Message"]
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # Too many tags (>50):
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[
                {"AccountIds": ["012345678910"], "AllAwsRegions": True}
            ],
            Tags=[
                {"Key": "{}".format(x), "Value": "{}".format(x)} for x in range(0, 51)
            ],
        )
    assert (
        "Member must have length less than or equal to 50"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # Tag key is too big (>128 chars):
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[
                {"AccountIds": ["012345678910"], "AllAwsRegions": True}
            ],
            Tags=[{"Key": "a" * 129, "Value": "a"}],
        )
    assert (
        "Member must have length less than or equal to 128"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # Tag value is too big (>256 chars):
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[
                {"AccountIds": ["012345678910"], "AllAwsRegions": True}
            ],
            Tags=[{"Key": "tag", "Value": "a" * 257}],
        )
    assert (
        "Member must have length less than or equal to 256"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # Duplicate Tags:
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[
                {"AccountIds": ["012345678910"], "AllAwsRegions": True}
            ],
            Tags=[{"Key": "a", "Value": "a"}, {"Key": "a", "Value": "a"}],
        )
    assert "Duplicate tag keys found." in ce.exception.response["Error"]["Message"]
    assert ce.exception.response["Error"]["Code"] == "InvalidInput"

    # Invalid characters in the tag key:
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[
                {"AccountIds": ["012345678910"], "AllAwsRegions": True}
            ],
            Tags=[{"Key": "!", "Value": "a"}],
        )
    assert (
        "Member must satisfy regular expression pattern:"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # If it contains both the AccountAggregationSources and the OrganizationAggregationSource
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[
                {"AccountIds": ["012345678910"], "AllAwsRegions": False}
            ],
            OrganizationAggregationSource={
                "RoleArn": "arn:aws:iam::012345678910:role/SomeRole",
                "AllAwsRegions": False,
            },
        )
    assert (
        "AccountAggregationSource and the OrganizationAggregationSource"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "InvalidParameterValueException"

    # If it contains neither:
    with assert_raises(ClientError) as ce:
        client.put_configuration_aggregator(ConfigurationAggregatorName="testing")
    assert (
        "AccountAggregationSource or the OrganizationAggregationSource"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "InvalidParameterValueException"

    # Just make one:
    account_aggregation_source = {
        "AccountIds": ["012345678910", "111111111111", "222222222222"],
        "AwsRegions": ["us-east-1", "us-west-2"],
        "AllAwsRegions": False,
    }

    result = client.put_configuration_aggregator(
        ConfigurationAggregatorName="testing",
        AccountAggregationSources=[account_aggregation_source],
    )
    assert result["ConfigurationAggregator"]["ConfigurationAggregatorName"] == "testing"
    assert result["ConfigurationAggregator"]["AccountAggregationSources"] == [
        account_aggregation_source
    ]
    assert (
        "arn:aws:config:us-west-2:{}:config-aggregator/config-aggregator-".format(
            ACCOUNT_ID
        )
        in result["ConfigurationAggregator"]["ConfigurationAggregatorArn"]
    )
    assert (
        result["ConfigurationAggregator"]["CreationTime"]
        == result["ConfigurationAggregator"]["LastUpdatedTime"]
    )

    # Update the existing one:
    original_arn = result["ConfigurationAggregator"]["ConfigurationAggregatorArn"]
    account_aggregation_source.pop("AwsRegions")
    account_aggregation_source["AllAwsRegions"] = True
    result = client.put_configuration_aggregator(
        ConfigurationAggregatorName="testing",
        AccountAggregationSources=[account_aggregation_source],
    )

    assert result["ConfigurationAggregator"]["ConfigurationAggregatorName"] == "testing"
    assert result["ConfigurationAggregator"]["AccountAggregationSources"] == [
        account_aggregation_source
    ]
    assert (
        result["ConfigurationAggregator"]["ConfigurationAggregatorArn"] == original_arn
    )

    # Make an org one:
    result = client.put_configuration_aggregator(
        ConfigurationAggregatorName="testingOrg",
        OrganizationAggregationSource={
            "RoleArn": "arn:aws:iam::012345678910:role/SomeRole",
            "AwsRegions": ["us-east-1", "us-west-2"],
        },
    )

    assert (
        result["ConfigurationAggregator"]["ConfigurationAggregatorName"] == "testingOrg"
    )
    assert result["ConfigurationAggregator"]["OrganizationAggregationSource"] == {
        "RoleArn": "arn:aws:iam::012345678910:role/SomeRole",
        "AwsRegions": ["us-east-1", "us-west-2"],
        "AllAwsRegions": False,
    }


@mock_config
def test_describe_configuration_aggregators():
    client = boto3.client("config", region_name="us-west-2")

    # Without any config aggregators:
    assert not client.describe_configuration_aggregators()["ConfigurationAggregators"]

    # Make 10 config aggregators:
    for x in range(0, 10):
        client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing{}".format(x),
            AccountAggregationSources=[
                {"AccountIds": ["012345678910"], "AllAwsRegions": True}
            ],
        )

    # Describe with an incorrect name:
    with assert_raises(ClientError) as ce:
        client.describe_configuration_aggregators(
            ConfigurationAggregatorNames=["DoesNotExist"]
        )
    assert (
        "The configuration aggregator does not exist."
        in ce.exception.response["Error"]["Message"]
    )
    assert (
        ce.exception.response["Error"]["Code"]
        == "NoSuchConfigurationAggregatorException"
    )

    # Error describe with more than 1 item in the list:
    with assert_raises(ClientError) as ce:
        client.describe_configuration_aggregators(
            ConfigurationAggregatorNames=["testing0", "DoesNotExist"]
        )
    assert (
        "At least one of the configuration aggregators does not exist."
        in ce.exception.response["Error"]["Message"]
    )
    assert (
        ce.exception.response["Error"]["Code"]
        == "NoSuchConfigurationAggregatorException"
    )

    # Get the normal list:
    result = client.describe_configuration_aggregators()
    assert not result.get("NextToken")
    assert len(result["ConfigurationAggregators"]) == 10

    # Test filtered list:
    agg_names = ["testing0", "testing1", "testing2"]
    result = client.describe_configuration_aggregators(
        ConfigurationAggregatorNames=agg_names
    )
    assert not result.get("NextToken")
    assert len(result["ConfigurationAggregators"]) == 3
    assert [
        agg["ConfigurationAggregatorName"] for agg in result["ConfigurationAggregators"]
    ] == agg_names

    # Test Pagination:
    result = client.describe_configuration_aggregators(Limit=4)
    assert len(result["ConfigurationAggregators"]) == 4
    assert result["NextToken"] == "testing4"
    assert [
        agg["ConfigurationAggregatorName"] for agg in result["ConfigurationAggregators"]
    ] == ["testing{}".format(x) for x in range(0, 4)]
    result = client.describe_configuration_aggregators(Limit=4, NextToken="testing4")
    assert len(result["ConfigurationAggregators"]) == 4
    assert result["NextToken"] == "testing8"
    assert [
        agg["ConfigurationAggregatorName"] for agg in result["ConfigurationAggregators"]
    ] == ["testing{}".format(x) for x in range(4, 8)]
    result = client.describe_configuration_aggregators(Limit=4, NextToken="testing8")
    assert len(result["ConfigurationAggregators"]) == 2
    assert not result.get("NextToken")
    assert [
        agg["ConfigurationAggregatorName"] for agg in result["ConfigurationAggregators"]
    ] == ["testing{}".format(x) for x in range(8, 10)]

    # Test Pagination with Filtering:
    result = client.describe_configuration_aggregators(
        ConfigurationAggregatorNames=["testing2", "testing4"], Limit=1
    )
    assert len(result["ConfigurationAggregators"]) == 1
    assert result["NextToken"] == "testing4"
    assert (
        result["ConfigurationAggregators"][0]["ConfigurationAggregatorName"]
        == "testing2"
    )
    result = client.describe_configuration_aggregators(
        ConfigurationAggregatorNames=["testing2", "testing4"],
        Limit=1,
        NextToken="testing4",
    )
    assert not result.get("NextToken")
    assert (
        result["ConfigurationAggregators"][0]["ConfigurationAggregatorName"]
        == "testing4"
    )

    # Test with an invalid filter:
    with assert_raises(ClientError) as ce:
        client.describe_configuration_aggregators(NextToken="WRONG")
    assert (
        "The nextToken provided is invalid" == ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "InvalidNextTokenException"


@mock_config
def test_put_aggregation_authorization():
    client = boto3.client("config", region_name="us-west-2")

    # Too many tags (>50):
    with assert_raises(ClientError) as ce:
        client.put_aggregation_authorization(
            AuthorizedAccountId="012345678910",
            AuthorizedAwsRegion="us-west-2",
            Tags=[
                {"Key": "{}".format(x), "Value": "{}".format(x)} for x in range(0, 51)
            ],
        )
    assert (
        "Member must have length less than or equal to 50"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # Tag key is too big (>128 chars):
    with assert_raises(ClientError) as ce:
        client.put_aggregation_authorization(
            AuthorizedAccountId="012345678910",
            AuthorizedAwsRegion="us-west-2",
            Tags=[{"Key": "a" * 129, "Value": "a"}],
        )
    assert (
        "Member must have length less than or equal to 128"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # Tag value is too big (>256 chars):
    with assert_raises(ClientError) as ce:
        client.put_aggregation_authorization(
            AuthorizedAccountId="012345678910",
            AuthorizedAwsRegion="us-west-2",
            Tags=[{"Key": "tag", "Value": "a" * 257}],
        )
    assert (
        "Member must have length less than or equal to 256"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # Duplicate Tags:
    with assert_raises(ClientError) as ce:
        client.put_aggregation_authorization(
            AuthorizedAccountId="012345678910",
            AuthorizedAwsRegion="us-west-2",
            Tags=[{"Key": "a", "Value": "a"}, {"Key": "a", "Value": "a"}],
        )
    assert "Duplicate tag keys found." in ce.exception.response["Error"]["Message"]
    assert ce.exception.response["Error"]["Code"] == "InvalidInput"

    # Invalid characters in the tag key:
    with assert_raises(ClientError) as ce:
        client.put_aggregation_authorization(
            AuthorizedAccountId="012345678910",
            AuthorizedAwsRegion="us-west-2",
            Tags=[{"Key": "!", "Value": "a"}],
        )
    assert (
        "Member must satisfy regular expression pattern:"
        in ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "ValidationException"

    # Put a normal one there:
    result = client.put_aggregation_authorization(
        AuthorizedAccountId="012345678910",
        AuthorizedAwsRegion="us-east-1",
        Tags=[{"Key": "tag", "Value": "a"}],
    )

    assert result["AggregationAuthorization"][
        "AggregationAuthorizationArn"
    ] == "arn:aws:config:us-west-2:{}:aggregation-authorization/012345678910/us-east-1".format(
        ACCOUNT_ID
    )
    assert result["AggregationAuthorization"]["AuthorizedAccountId"] == "012345678910"
    assert result["AggregationAuthorization"]["AuthorizedAwsRegion"] == "us-east-1"
    assert isinstance(result["AggregationAuthorization"]["CreationTime"], datetime)

    creation_date = result["AggregationAuthorization"]["CreationTime"]

    # And again:
    result = client.put_aggregation_authorization(
        AuthorizedAccountId="012345678910", AuthorizedAwsRegion="us-east-1"
    )
    assert result["AggregationAuthorization"][
        "AggregationAuthorizationArn"
    ] == "arn:aws:config:us-west-2:{}:aggregation-authorization/012345678910/us-east-1".format(
        ACCOUNT_ID
    )
    assert result["AggregationAuthorization"]["AuthorizedAccountId"] == "012345678910"
    assert result["AggregationAuthorization"]["AuthorizedAwsRegion"] == "us-east-1"
    assert result["AggregationAuthorization"]["CreationTime"] == creation_date


@mock_config
def test_describe_aggregation_authorizations():
    client = boto3.client("config", region_name="us-west-2")

    # With no aggregation authorizations:
    assert not client.describe_aggregation_authorizations()["AggregationAuthorizations"]

    # Make 10 account authorizations:
    for i in range(0, 10):
        client.put_aggregation_authorization(
            AuthorizedAccountId="{}".format(str(i) * 12),
            AuthorizedAwsRegion="us-west-2",
        )

    result = client.describe_aggregation_authorizations()
    assert len(result["AggregationAuthorizations"]) == 10
    assert not result.get("NextToken")
    for i in range(0, 10):
        assert (
            result["AggregationAuthorizations"][i]["AuthorizedAccountId"] == str(i) * 12
        )

    # Test Pagination:
    result = client.describe_aggregation_authorizations(Limit=4)
    assert len(result["AggregationAuthorizations"]) == 4
    assert result["NextToken"] == ("4" * 12) + "/us-west-2"
    assert [
        auth["AuthorizedAccountId"] for auth in result["AggregationAuthorizations"]
    ] == ["{}".format(str(x) * 12) for x in range(0, 4)]

    result = client.describe_aggregation_authorizations(
        Limit=4, NextToken=("4" * 12) + "/us-west-2"
    )
    assert len(result["AggregationAuthorizations"]) == 4
    assert result["NextToken"] == ("8" * 12) + "/us-west-2"
    assert [
        auth["AuthorizedAccountId"] for auth in result["AggregationAuthorizations"]
    ] == ["{}".format(str(x) * 12) for x in range(4, 8)]

    result = client.describe_aggregation_authorizations(
        Limit=4, NextToken=("8" * 12) + "/us-west-2"
    )
    assert len(result["AggregationAuthorizations"]) == 2
    assert not result.get("NextToken")
    assert [
        auth["AuthorizedAccountId"] for auth in result["AggregationAuthorizations"]
    ] == ["{}".format(str(x) * 12) for x in range(8, 10)]

    # Test with an invalid filter:
    with assert_raises(ClientError) as ce:
        client.describe_aggregation_authorizations(NextToken="WRONG")
    assert (
        "The nextToken provided is invalid" == ce.exception.response["Error"]["Message"]
    )
    assert ce.exception.response["Error"]["Code"] == "InvalidNextTokenException"


@mock_config
def test_delete_aggregation_authorization():
    client = boto3.client("config", region_name="us-west-2")

    client.put_aggregation_authorization(
        AuthorizedAccountId="012345678910", AuthorizedAwsRegion="us-west-2"
    )

    # Delete it:
    client.delete_aggregation_authorization(
        AuthorizedAccountId="012345678910", AuthorizedAwsRegion="us-west-2"
    )

    # Verify that none are there:
    assert not client.describe_aggregation_authorizations()["AggregationAuthorizations"]

    # Try it again -- nothing should happen:
    client.delete_aggregation_authorization(
        AuthorizedAccountId="012345678910", AuthorizedAwsRegion="us-west-2"
    )


@mock_config
def test_delete_configuration_aggregator():
    client = boto3.client("config", region_name="us-west-2")
    client.put_configuration_aggregator(
        ConfigurationAggregatorName="testing",
        AccountAggregationSources=[
            {"AccountIds": ["012345678910"], "AllAwsRegions": True}
        ],
    )

    client.delete_configuration_aggregator(ConfigurationAggregatorName="testing")

    # And again to confirm that it's deleted:
    with assert_raises(ClientError) as ce:
        client.delete_configuration_aggregator(ConfigurationAggregatorName="testing")
    assert (
        "The configuration aggregator does not exist."
        in ce.exception.response["Error"]["Message"]
    )
    assert (
        ce.exception.response["Error"]["Code"]
        == "NoSuchConfigurationAggregatorException"
    )


@mock_config
def test_describe_configurations():
    client = boto3.client("config", region_name="us-west-2")

    # Without any configurations:
    result = client.describe_configuration_recorders()
    assert not result["ConfigurationRecorders"]

    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": False,
                "includeGlobalResourceTypes": False,
                "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
            },
        }
    )

    result = client.describe_configuration_recorders()["ConfigurationRecorders"]
    assert len(result) == 1
    assert result[0]["name"] == "testrecorder"
    assert result[0]["roleARN"] == "somearn"
    assert not result[0]["recordingGroup"]["allSupported"]
    assert not result[0]["recordingGroup"]["includeGlobalResourceTypes"]
    assert len(result[0]["recordingGroup"]["resourceTypes"]) == 2
    assert (
        "AWS::EC2::Volume" in result[0]["recordingGroup"]["resourceTypes"]
        and "AWS::EC2::VPC" in result[0]["recordingGroup"]["resourceTypes"]
    )

    # Specify an incorrect name:
    with assert_raises(ClientError) as ce:
        client.describe_configuration_recorders(ConfigurationRecorderNames=["wrong"])
    assert (
        ce.exception.response["Error"]["Code"] == "NoSuchConfigurationRecorderException"
    )
    assert "wrong" in ce.exception.response["Error"]["Message"]

    # And with both a good and wrong name:
    with assert_raises(ClientError) as ce:
        client.describe_configuration_recorders(
            ConfigurationRecorderNames=["testrecorder", "wrong"]
        )
    assert (
        ce.exception.response["Error"]["Code"] == "NoSuchConfigurationRecorderException"
    )
    assert "wrong" in ce.exception.response["Error"]["Message"]


@mock_config
def test_delivery_channels():
    client = boto3.client("config", region_name="us-west-2")

    # Try without a config recorder:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={})
    assert (
        ce.exception.response["Error"]["Code"]
        == "NoAvailableConfigurationRecorderException"
    )
    assert (
        ce.exception.response["Error"]["Message"]
        == "Configuration recorder is not available to "
        "put delivery channel."
    )

    # Create a config recorder to continue testing:
    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": False,
                "includeGlobalResourceTypes": False,
                "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
            },
        }
    )

    # Try without a name supplied:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={})
    assert (
        ce.exception.response["Error"]["Code"] == "InvalidDeliveryChannelNameException"
    )
    assert "is not valid, blank string." in ce.exception.response["Error"]["Message"]

    # Try with a really long name:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={"name": "a" * 257})
    assert ce.exception.response["Error"]["Code"] == "ValidationException"
    assert (
        "Member must have length less than or equal to 256"
        in ce.exception.response["Error"]["Message"]
    )

    # Without specifying a bucket name:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={"name": "testchannel"})
    assert ce.exception.response["Error"]["Code"] == "NoSuchBucketException"
    assert (
        ce.exception.response["Error"]["Message"]
        == "Cannot find a S3 bucket with an empty bucket name."
    )

    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(
            DeliveryChannel={"name": "testchannel", "s3BucketName": ""}
        )
    assert ce.exception.response["Error"]["Code"] == "NoSuchBucketException"
    assert (
        ce.exception.response["Error"]["Message"]
        == "Cannot find a S3 bucket with an empty bucket name."
    )

    # With an empty string for the S3 key prefix:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(
            DeliveryChannel={
                "name": "testchannel",
                "s3BucketName": "somebucket",
                "s3KeyPrefix": "",
            }
        )
    assert ce.exception.response["Error"]["Code"] == "InvalidS3KeyPrefixException"
    assert "empty s3 key prefix." in ce.exception.response["Error"]["Message"]

    # With an empty string for the SNS ARN:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(
            DeliveryChannel={
                "name": "testchannel",
                "s3BucketName": "somebucket",
                "snsTopicARN": "",
            }
        )
    assert ce.exception.response["Error"]["Code"] == "InvalidSNSTopicARNException"
    assert "The sns topic arn" in ce.exception.response["Error"]["Message"]

    # With an invalid delivery frequency:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(
            DeliveryChannel={
                "name": "testchannel",
                "s3BucketName": "somebucket",
                "configSnapshotDeliveryProperties": {"deliveryFrequency": "WRONG"},
            }
        )
    assert ce.exception.response["Error"]["Code"] == "InvalidDeliveryFrequency"
    assert "WRONG" in ce.exception.response["Error"]["Message"]
    assert "TwentyFour_Hours" in ce.exception.response["Error"]["Message"]

    # Create a proper one:
    client.put_delivery_channel(
        DeliveryChannel={"name": "testchannel", "s3BucketName": "somebucket"}
    )
    result = client.describe_delivery_channels()["DeliveryChannels"]
    assert len(result) == 1
    assert len(result[0].keys()) == 2
    assert result[0]["name"] == "testchannel"
    assert result[0]["s3BucketName"] == "somebucket"

    # Overwrite it with another proper configuration:
    client.put_delivery_channel(
        DeliveryChannel={
            "name": "testchannel",
            "s3BucketName": "somebucket",
            "snsTopicARN": "sometopicarn",
            "configSnapshotDeliveryProperties": {
                "deliveryFrequency": "TwentyFour_Hours"
            },
        }
    )
    result = client.describe_delivery_channels()["DeliveryChannels"]
    assert len(result) == 1
    assert len(result[0].keys()) == 4
    assert result[0]["name"] == "testchannel"
    assert result[0]["s3BucketName"] == "somebucket"
    assert result[0]["snsTopicARN"] == "sometopicarn"
    assert (
        result[0]["configSnapshotDeliveryProperties"]["deliveryFrequency"]
        == "TwentyFour_Hours"
    )

    # Can only have 1:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(
            DeliveryChannel={"name": "testchannel2", "s3BucketName": "somebucket"}
        )
    assert (
        ce.exception.response["Error"]["Code"]
        == "MaxNumberOfDeliveryChannelsExceededException"
    )
    assert (
        "because the maximum number of delivery channels: 1 is reached."
        in ce.exception.response["Error"]["Message"]
    )


@mock_config
def test_describe_delivery_channels():
    client = boto3.client("config", region_name="us-west-2")
    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": False,
                "includeGlobalResourceTypes": False,
                "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
            },
        }
    )

    # Without any channels:
    result = client.describe_delivery_channels()
    assert not result["DeliveryChannels"]

    client.put_delivery_channel(
        DeliveryChannel={"name": "testchannel", "s3BucketName": "somebucket"}
    )
    result = client.describe_delivery_channels()["DeliveryChannels"]
    assert len(result) == 1
    assert len(result[0].keys()) == 2
    assert result[0]["name"] == "testchannel"
    assert result[0]["s3BucketName"] == "somebucket"

    # Overwrite it with another proper configuration:
    client.put_delivery_channel(
        DeliveryChannel={
            "name": "testchannel",
            "s3BucketName": "somebucket",
            "snsTopicARN": "sometopicarn",
            "configSnapshotDeliveryProperties": {
                "deliveryFrequency": "TwentyFour_Hours"
            },
        }
    )
    result = client.describe_delivery_channels()["DeliveryChannels"]
    assert len(result) == 1
    assert len(result[0].keys()) == 4
    assert result[0]["name"] == "testchannel"
    assert result[0]["s3BucketName"] == "somebucket"
    assert result[0]["snsTopicARN"] == "sometopicarn"
    assert (
        result[0]["configSnapshotDeliveryProperties"]["deliveryFrequency"]
        == "TwentyFour_Hours"
    )

    # Specify an incorrect name:
    with assert_raises(ClientError) as ce:
        client.describe_delivery_channels(DeliveryChannelNames=["wrong"])
    assert ce.exception.response["Error"]["Code"] == "NoSuchDeliveryChannelException"
    assert "wrong" in ce.exception.response["Error"]["Message"]

    # And with both a good and wrong name:
    with assert_raises(ClientError) as ce:
        client.describe_delivery_channels(DeliveryChannelNames=["testchannel", "wrong"])
    assert ce.exception.response["Error"]["Code"] == "NoSuchDeliveryChannelException"
    assert "wrong" in ce.exception.response["Error"]["Message"]


@mock_config
def test_start_configuration_recorder():
    client = boto3.client("config", region_name="us-west-2")

    # Without a config recorder:
    with assert_raises(ClientError) as ce:
        client.start_configuration_recorder(ConfigurationRecorderName="testrecorder")
    assert (
        ce.exception.response["Error"]["Code"] == "NoSuchConfigurationRecorderException"
    )

    # Make the config recorder;
    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": False,
                "includeGlobalResourceTypes": False,
                "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
            },
        }
    )

    # Without a delivery channel:
    with assert_raises(ClientError) as ce:
        client.start_configuration_recorder(ConfigurationRecorderName="testrecorder")
    assert (
        ce.exception.response["Error"]["Code"] == "NoAvailableDeliveryChannelException"
    )

    # Make the delivery channel:
    client.put_delivery_channel(
        DeliveryChannel={"name": "testchannel", "s3BucketName": "somebucket"}
    )

    # Start it:
    client.start_configuration_recorder(ConfigurationRecorderName="testrecorder")

    # Verify it's enabled:
    result = client.describe_configuration_recorder_status()[
        "ConfigurationRecordersStatus"
    ]
    lower_bound = datetime.utcnow() - timedelta(minutes=5)
    assert result[0]["recording"]
    assert result[0]["lastStatus"] == "PENDING"
    assert (
        lower_bound
        < result[0]["lastStartTime"].replace(tzinfo=None)
        <= datetime.utcnow()
    )
    assert (
        lower_bound
        < result[0]["lastStatusChangeTime"].replace(tzinfo=None)
        <= datetime.utcnow()
    )


@mock_config
def test_stop_configuration_recorder():
    client = boto3.client("config", region_name="us-west-2")

    # Without a config recorder:
    with assert_raises(ClientError) as ce:
        client.stop_configuration_recorder(ConfigurationRecorderName="testrecorder")
    assert (
        ce.exception.response["Error"]["Code"] == "NoSuchConfigurationRecorderException"
    )

    # Make the config recorder;
    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": False,
                "includeGlobalResourceTypes": False,
                "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
            },
        }
    )

    # Make the delivery channel for creation:
    client.put_delivery_channel(
        DeliveryChannel={"name": "testchannel", "s3BucketName": "somebucket"}
    )

    # Start it:
    client.start_configuration_recorder(ConfigurationRecorderName="testrecorder")
    client.stop_configuration_recorder(ConfigurationRecorderName="testrecorder")

    # Verify it's disabled:
    result = client.describe_configuration_recorder_status()[
        "ConfigurationRecordersStatus"
    ]
    lower_bound = datetime.utcnow() - timedelta(minutes=5)
    assert not result[0]["recording"]
    assert result[0]["lastStatus"] == "PENDING"
    assert (
        lower_bound
        < result[0]["lastStartTime"].replace(tzinfo=None)
        <= datetime.utcnow()
    )
    assert (
        lower_bound
        < result[0]["lastStopTime"].replace(tzinfo=None)
        <= datetime.utcnow()
    )
    assert (
        lower_bound
        < result[0]["lastStatusChangeTime"].replace(tzinfo=None)
        <= datetime.utcnow()
    )


@mock_config
def test_describe_configuration_recorder_status():
    client = boto3.client("config", region_name="us-west-2")

    # Without any:
    result = client.describe_configuration_recorder_status()
    assert not result["ConfigurationRecordersStatus"]

    # Make the config recorder;
    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": False,
                "includeGlobalResourceTypes": False,
                "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
            },
        }
    )

    # Without specifying a config recorder:
    result = client.describe_configuration_recorder_status()[
        "ConfigurationRecordersStatus"
    ]
    assert len(result) == 1
    assert result[0]["name"] == "testrecorder"
    assert not result[0]["recording"]

    # With a proper name:
    result = client.describe_configuration_recorder_status(
        ConfigurationRecorderNames=["testrecorder"]
    )["ConfigurationRecordersStatus"]
    assert len(result) == 1
    assert result[0]["name"] == "testrecorder"
    assert not result[0]["recording"]

    # Invalid name:
    with assert_raises(ClientError) as ce:
        client.describe_configuration_recorder_status(
            ConfigurationRecorderNames=["testrecorder", "wrong"]
        )
    assert (
        ce.exception.response["Error"]["Code"] == "NoSuchConfigurationRecorderException"
    )
    assert "wrong" in ce.exception.response["Error"]["Message"]


@mock_config
def test_delete_configuration_recorder():
    client = boto3.client("config", region_name="us-west-2")

    # Make the config recorder;
    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": False,
                "includeGlobalResourceTypes": False,
                "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
            },
        }
    )

    # Delete it:
    client.delete_configuration_recorder(ConfigurationRecorderName="testrecorder")

    # Try again -- it should be deleted:
    with assert_raises(ClientError) as ce:
        client.delete_configuration_recorder(ConfigurationRecorderName="testrecorder")
    assert (
        ce.exception.response["Error"]["Code"] == "NoSuchConfigurationRecorderException"
    )


@mock_config
def test_delete_delivery_channel():
    client = boto3.client("config", region_name="us-west-2")

    # Need a recorder to test the constraint on recording being enabled:
    client.put_configuration_recorder(
        ConfigurationRecorder={
            "name": "testrecorder",
            "roleARN": "somearn",
            "recordingGroup": {
                "allSupported": False,
                "includeGlobalResourceTypes": False,
                "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
            },
        }
    )
    client.put_delivery_channel(
        DeliveryChannel={"name": "testchannel", "s3BucketName": "somebucket"}
    )
    client.start_configuration_recorder(ConfigurationRecorderName="testrecorder")

    # With the recorder enabled:
    with assert_raises(ClientError) as ce:
        client.delete_delivery_channel(DeliveryChannelName="testchannel")
    assert (
        ce.exception.response["Error"]["Code"]
        == "LastDeliveryChannelDeleteFailedException"
    )
    assert (
        "because there is a running configuration recorder."
        in ce.exception.response["Error"]["Message"]
    )

    # Stop recording:
    client.stop_configuration_recorder(ConfigurationRecorderName="testrecorder")

    # Try again:
    client.delete_delivery_channel(DeliveryChannelName="testchannel")

    # Verify:
    with assert_raises(ClientError) as ce:
        client.delete_delivery_channel(DeliveryChannelName="testchannel")
    assert ce.exception.response["Error"]["Code"] == "NoSuchDeliveryChannelException"


@mock_config
@mock_s3
def test_list_discovered_resource():
    """NOTE: We are only really testing the Config part. For each individual service, please add tests
             for that individual service's "list_config_service_resources" function.
    """
    client = boto3.client("config", region_name="us-west-2")

    # With nothing created yet:
    assert not client.list_discovered_resources(resourceType="AWS::S3::Bucket")[
        "resourceIdentifiers"
    ]

    # Create some S3 buckets:
    s3_client = boto3.client("s3", region_name="us-west-2")
    for x in range(0, 10):
        s3_client.create_bucket(
            Bucket="bucket{}".format(x),
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

    # And with an EU bucket -- this should not show up for the us-west-2 config backend:
    eu_client = boto3.client("s3", region_name="eu-west-1")
    eu_client.create_bucket(
        Bucket="eu-bucket",
        CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
    )

    # Now try:
    result = client.list_discovered_resources(resourceType="AWS::S3::Bucket")
    assert len(result["resourceIdentifiers"]) == 10
    for x in range(0, 10):
        assert result["resourceIdentifiers"][x] == {
            "resourceType": "AWS::S3::Bucket",
            "resourceId": "bucket{}".format(x),
            "resourceName": "bucket{}".format(x),
        }
    assert not result.get("nextToken")

    result = client.list_discovered_resources(
        resourceType="AWS::S3::Bucket", resourceName="eu-bucket"
    )
    assert not result["resourceIdentifiers"]

    # Test that pagination places a proper nextToken in the response and also that the limit works:
    result = client.list_discovered_resources(
        resourceType="AWS::S3::Bucket", limit=1, nextToken="bucket1"
    )
    assert len(result["resourceIdentifiers"]) == 1
    assert result["nextToken"] == "bucket2"

    # Try with a resource name:
    result = client.list_discovered_resources(
        resourceType="AWS::S3::Bucket", limit=1, resourceName="bucket1"
    )
    assert len(result["resourceIdentifiers"]) == 1
    assert not result.get("nextToken")

    # Try with a resource ID:
    result = client.list_discovered_resources(
        resourceType="AWS::S3::Bucket", limit=1, resourceIds=["bucket1"]
    )
    assert len(result["resourceIdentifiers"]) == 1
    assert not result.get("nextToken")

    # Try with duplicated resource IDs:
    result = client.list_discovered_resources(
        resourceType="AWS::S3::Bucket", limit=1, resourceIds=["bucket1", "bucket1"]
    )
    assert len(result["resourceIdentifiers"]) == 1
    assert not result.get("nextToken")

    # Test with an invalid resource type:
    assert not client.list_discovered_resources(
        resourceType="LOL::NOT::A::RESOURCE::TYPE"
    )["resourceIdentifiers"]

    # Test with an invalid page num > 100:
    with assert_raises(ClientError) as ce:
        client.list_discovered_resources(resourceType="AWS::S3::Bucket", limit=101)
    assert "101" in ce.exception.response["Error"]["Message"]

    # Test by supplying both resourceName and also resourceIds:
    with assert_raises(ClientError) as ce:
        client.list_discovered_resources(
            resourceType="AWS::S3::Bucket",
            resourceName="whats",
            resourceIds=["up", "doc"],
        )
    assert (
        "Both Resource ID and Resource Name cannot be specified in the request"
        in ce.exception.response["Error"]["Message"]
    )

    # More than 20 resourceIds:
    resource_ids = ["{}".format(x) for x in range(0, 21)]
    with assert_raises(ClientError) as ce:
        client.list_discovered_resources(
            resourceType="AWS::S3::Bucket", resourceIds=resource_ids
        )
    assert (
        "The specified list had more than 20 resource ID's."
        in ce.exception.response["Error"]["Message"]
    )


@mock_config
@mock_s3
def test_list_aggregate_discovered_resource():
    """NOTE: We are only really testing the Config part. For each individual service, please add tests
             for that individual service's "list_config_service_resources" function.
    """
    client = boto3.client("config", region_name="us-west-2")

    # Without an aggregator:
    with assert_raises(ClientError) as ce:
        client.list_aggregate_discovered_resources(
            ConfigurationAggregatorName="lolno", ResourceType="AWS::S3::Bucket"
        )
    assert (
        "The configuration aggregator does not exist"
        in ce.exception.response["Error"]["Message"]
    )

    # Create the aggregator:
    account_aggregation_source = {
        "AccountIds": ["012345678910", "111111111111", "222222222222"],
        "AllAwsRegions": True,
    }
    client.put_configuration_aggregator(
        ConfigurationAggregatorName="testing",
        AccountAggregationSources=[account_aggregation_source],
    )

    # With nothing created yet:
    assert not client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="testing", ResourceType="AWS::S3::Bucket"
    )["ResourceIdentifiers"]

    # Create some S3 buckets:
    s3_client = boto3.client("s3", region_name="us-west-2")
    for x in range(0, 10):
        s3_client.create_bucket(
            Bucket="bucket{}".format(x),
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

    s3_client_eu = boto3.client("s3", region_name="eu-west-1")
    for x in range(10, 12):
        s3_client_eu.create_bucket(
            Bucket="eu-bucket{}".format(x),
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )

    # Now try:
    result = client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="testing", ResourceType="AWS::S3::Bucket"
    )
    assert len(result["ResourceIdentifiers"]) == 12
    for x in range(0, 10):
        assert result["ResourceIdentifiers"][x] == {
            "SourceAccountId": ACCOUNT_ID,
            "ResourceType": "AWS::S3::Bucket",
            "ResourceId": "bucket{}".format(x),
            "ResourceName": "bucket{}".format(x),
            "SourceRegion": "us-west-2",
        }
    for x in range(11, 12):
        assert result["ResourceIdentifiers"][x] == {
            "SourceAccountId": ACCOUNT_ID,
            "ResourceType": "AWS::S3::Bucket",
            "ResourceId": "eu-bucket{}".format(x),
            "ResourceName": "eu-bucket{}".format(x),
            "SourceRegion": "eu-west-1",
        }

    assert not result.get("NextToken")

    # Test that pagination places a proper nextToken in the response and also that the limit works:
    result = client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="testing",
        ResourceType="AWS::S3::Bucket",
        Limit=1,
        NextToken="bucket1",
    )
    assert len(result["ResourceIdentifiers"]) == 1
    assert result["NextToken"] == "bucket2"

    # Try with a resource name:
    result = client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="testing",
        ResourceType="AWS::S3::Bucket",
        Limit=1,
        NextToken="bucket1",
        Filters={"ResourceName": "bucket1"},
    )
    assert len(result["ResourceIdentifiers"]) == 1
    assert not result.get("NextToken")

    # Try with a resource ID:
    result = client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="testing",
        ResourceType="AWS::S3::Bucket",
        Limit=1,
        NextToken="bucket1",
        Filters={"ResourceId": "bucket1"},
    )
    assert len(result["ResourceIdentifiers"]) == 1
    assert not result.get("NextToken")

    # Try with a region specified:
    result = client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="testing",
        ResourceType="AWS::S3::Bucket",
        Filters={"Region": "eu-west-1"},
    )
    assert len(result["ResourceIdentifiers"]) == 2
    assert result["ResourceIdentifiers"][0]["SourceRegion"] == "eu-west-1"
    assert not result.get("NextToken")

    # Try with both name and id set to the incorrect values:
    assert not client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="testing",
        ResourceType="AWS::S3::Bucket",
        Filters={"ResourceId": "bucket1", "ResourceName": "bucket2"},
    )["ResourceIdentifiers"]

    # Test with an invalid resource type:
    assert not client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="testing",
        ResourceType="LOL::NOT::A::RESOURCE::TYPE",
    )["ResourceIdentifiers"]

    # Try with correct name but incorrect region:
    assert not client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="testing",
        ResourceType="AWS::S3::Bucket",
        Filters={"ResourceId": "bucket1", "Region": "us-west-1"},
    )["ResourceIdentifiers"]

    # Test with an invalid page num > 100:
    with assert_raises(ClientError) as ce:
        client.list_aggregate_discovered_resources(
            ConfigurationAggregatorName="testing",
            ResourceType="AWS::S3::Bucket",
            Limit=101,
        )
    assert "101" in ce.exception.response["Error"]["Message"]


@mock_config
@mock_s3
def test_get_resource_config_history():
    """NOTE: We are only really testing the Config part. For each individual service, please add tests
             for that individual service's "get_config_resource" function.
    """
    client = boto3.client("config", region_name="us-west-2")

    # With an invalid resource type:
    with assert_raises(ClientError) as ce:
        client.get_resource_config_history(
            resourceType="NOT::A::RESOURCE", resourceId="notcreatedyet"
        )
    assert ce.exception.response["Error"] == {
        "Message": "Resource notcreatedyet of resourceType:NOT::A::RESOURCE is unknown or has "
        "not been discovered",
        "Code": "ResourceNotDiscoveredException",
    }

    # With nothing created yet:
    with assert_raises(ClientError) as ce:
        client.get_resource_config_history(
            resourceType="AWS::S3::Bucket", resourceId="notcreatedyet"
        )
    assert ce.exception.response["Error"] == {
        "Message": "Resource notcreatedyet of resourceType:AWS::S3::Bucket is unknown or has "
        "not been discovered",
        "Code": "ResourceNotDiscoveredException",
    }

    # Create an S3 bucket:
    s3_client = boto3.client("s3", region_name="us-west-2")
    for x in range(0, 10):
        s3_client.create_bucket(
            Bucket="bucket{}".format(x),
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

    # Now try:
    result = client.get_resource_config_history(
        resourceType="AWS::S3::Bucket", resourceId="bucket1"
    )["configurationItems"]
    assert len(result) == 1
    assert result[0]["resourceName"] == result[0]["resourceId"] == "bucket1"
    assert result[0]["arn"] == "arn:aws:s3:::bucket1"

    # Make a bucket in a different region and verify that it does not show up in the config backend:
    s3_client = boto3.client("s3", region_name="eu-west-1")
    s3_client.create_bucket(
        Bucket="eu-bucket",
        CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
    )
    with assert_raises(ClientError) as ce:
        client.get_resource_config_history(
            resourceType="AWS::S3::Bucket", resourceId="eu-bucket"
        )
    assert ce.exception.response["Error"]["Code"] == "ResourceNotDiscoveredException"


@mock_config
@mock_s3
def test_batch_get_resource_config():
    """NOTE: We are only really testing the Config part. For each individual service, please add tests
             for that individual service's "get_config_resource" function.
    """
    client = boto3.client("config", region_name="us-west-2")

    # With more than 100 resourceKeys:
    with assert_raises(ClientError) as ce:
        client.batch_get_resource_config(
            resourceKeys=[
                {"resourceType": "AWS::S3::Bucket", "resourceId": "someBucket"}
            ]
            * 101
        )
    assert (
        "Member must have length less than or equal to 100"
        in ce.exception.response["Error"]["Message"]
    )

    # With invalid resource types and resources that don't exist:
    result = client.batch_get_resource_config(
        resourceKeys=[
            {"resourceType": "NOT::A::RESOURCE", "resourceId": "NotAThing"},
            {"resourceType": "AWS::S3::Bucket", "resourceId": "NotAThing"},
        ]
    )

    assert not result["baseConfigurationItems"]
    assert not result["unprocessedResourceKeys"]

    # Create some S3 buckets:
    s3_client = boto3.client("s3", region_name="us-west-2")
    for x in range(0, 10):
        s3_client.create_bucket(
            Bucket="bucket{}".format(x),
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

    # Get them all:
    keys = [
        {"resourceType": "AWS::S3::Bucket", "resourceId": "bucket{}".format(x)}
        for x in range(0, 10)
    ]
    result = client.batch_get_resource_config(resourceKeys=keys)
    assert len(result["baseConfigurationItems"]) == 10
    buckets_missing = ["bucket{}".format(x) for x in range(0, 10)]
    for r in result["baseConfigurationItems"]:
        buckets_missing.remove(r["resourceName"])

    assert not buckets_missing

    # Make a bucket in a different region and verify that it does not show up in the config backend:
    s3_client = boto3.client("s3", region_name="eu-west-1")
    s3_client.create_bucket(
        Bucket="eu-bucket",
        CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
    )
    keys = [{"resourceType": "AWS::S3::Bucket", "resourceId": "eu-bucket"}]
    result = client.batch_get_resource_config(resourceKeys=keys)
    assert not result["baseConfigurationItems"]


@mock_config
@mock_s3
def test_batch_get_aggregate_resource_config():
    """NOTE: We are only really testing the Config part. For each individual service, please add tests
             for that individual service's "get_config_resource" function.
    """
    from moto.config.models import DEFAULT_ACCOUNT_ID

    client = boto3.client("config", region_name="us-west-2")

    # Without an aggregator:
    bad_ri = {
        "SourceAccountId": "000000000000",
        "SourceRegion": "not-a-region",
        "ResourceType": "NOT::A::RESOURCE",
        "ResourceId": "nope",
    }
    with assert_raises(ClientError) as ce:
        client.batch_get_aggregate_resource_config(
            ConfigurationAggregatorName="lolno", ResourceIdentifiers=[bad_ri]
        )
    assert (
        "The configuration aggregator does not exist"
        in ce.exception.response["Error"]["Message"]
    )

    # Create the aggregator:
    account_aggregation_source = {
        "AccountIds": ["012345678910", "111111111111", "222222222222"],
        "AllAwsRegions": True,
    }
    client.put_configuration_aggregator(
        ConfigurationAggregatorName="testing",
        AccountAggregationSources=[account_aggregation_source],
    )

    # With more than 100 items:
    with assert_raises(ClientError) as ce:
        client.batch_get_aggregate_resource_config(
            ConfigurationAggregatorName="testing", ResourceIdentifiers=[bad_ri] * 101
        )
    assert (
        "Member must have length less than or equal to 100"
        in ce.exception.response["Error"]["Message"]
    )

    # Create some S3 buckets:
    s3_client = boto3.client("s3", region_name="us-west-2")
    for x in range(0, 10):
        s3_client.create_bucket(
            Bucket="bucket{}".format(x),
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )
        s3_client.put_bucket_tagging(
            Bucket="bucket{}".format(x),
            Tagging={"TagSet": [{"Key": "Some", "Value": "Tag"}]},
        )

    s3_client_eu = boto3.client("s3", region_name="eu-west-1")
    for x in range(10, 12):
        s3_client_eu.create_bucket(
            Bucket="eu-bucket{}".format(x),
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )
        s3_client.put_bucket_tagging(
            Bucket="eu-bucket{}".format(x),
            Tagging={"TagSet": [{"Key": "Some", "Value": "Tag"}]},
        )

    # Now try with resources that exist and ones that don't:
    identifiers = [
        {
            "SourceAccountId": DEFAULT_ACCOUNT_ID,
            "SourceRegion": "us-west-2",
            "ResourceType": "AWS::S3::Bucket",
            "ResourceId": "bucket{}".format(x),
        }
        for x in range(0, 10)
    ]
    identifiers += [
        {
            "SourceAccountId": DEFAULT_ACCOUNT_ID,
            "SourceRegion": "eu-west-1",
            "ResourceType": "AWS::S3::Bucket",
            "ResourceId": "eu-bucket{}".format(x),
        }
        for x in range(10, 12)
    ]
    identifiers += [bad_ri]

    result = client.batch_get_aggregate_resource_config(
        ConfigurationAggregatorName="testing", ResourceIdentifiers=identifiers
    )
    assert len(result["UnprocessedResourceIdentifiers"]) == 1
    assert result["UnprocessedResourceIdentifiers"][0] == bad_ri

    # Verify all the buckets are there:
    assert len(result["BaseConfigurationItems"]) == 12
    missing_buckets = ["bucket{}".format(x) for x in range(0, 10)] + [
        "eu-bucket{}".format(x) for x in range(10, 12)
    ]

    for r in result["BaseConfigurationItems"]:
        missing_buckets.remove(r["resourceName"])

    assert not missing_buckets

    # Verify that 'tags' is not in the result set:
    for b in result["BaseConfigurationItems"]:
        assert not b.get("tags")
        assert json.loads(
            b["supplementaryConfiguration"]["BucketTaggingConfiguration"]
        ) == {"tagSets": [{"tags": {"Some": "Tag"}}]}

    # Verify that if the resource name and ID are correct that things are good:
    identifiers = [
        {
            "SourceAccountId": DEFAULT_ACCOUNT_ID,
            "SourceRegion": "us-west-2",
            "ResourceType": "AWS::S3::Bucket",
            "ResourceId": "bucket1",
            "ResourceName": "bucket1",
        }
    ]
    result = client.batch_get_aggregate_resource_config(
        ConfigurationAggregatorName="testing", ResourceIdentifiers=identifiers
    )
    assert not result["UnprocessedResourceIdentifiers"]
    assert (
        len(result["BaseConfigurationItems"]) == 1
        and result["BaseConfigurationItems"][0]["resourceName"] == "bucket1"
    )

    # Verify that if the resource name and ID mismatch that we don't get a result:
    identifiers = [
        {
            "SourceAccountId": DEFAULT_ACCOUNT_ID,
            "SourceRegion": "us-west-2",
            "ResourceType": "AWS::S3::Bucket",
            "ResourceId": "bucket1",
            "ResourceName": "bucket2",
        }
    ]
    result = client.batch_get_aggregate_resource_config(
        ConfigurationAggregatorName="testing", ResourceIdentifiers=identifiers
    )
    assert not result["BaseConfigurationItems"]
    assert len(result["UnprocessedResourceIdentifiers"]) == 1
    assert (
        len(result["UnprocessedResourceIdentifiers"]) == 1
        and result["UnprocessedResourceIdentifiers"][0]["ResourceName"] == "bucket2"
    )

    # Verify that if the region is incorrect that we don't get a result:
    identifiers = [
        {
            "SourceAccountId": DEFAULT_ACCOUNT_ID,
            "SourceRegion": "eu-west-1",
            "ResourceType": "AWS::S3::Bucket",
            "ResourceId": "bucket1",
        }
    ]
    result = client.batch_get_aggregate_resource_config(
        ConfigurationAggregatorName="testing", ResourceIdentifiers=identifiers
    )
    assert not result["BaseConfigurationItems"]
    assert len(result["UnprocessedResourceIdentifiers"]) == 1
    assert (
        len(result["UnprocessedResourceIdentifiers"]) == 1
        and result["UnprocessedResourceIdentifiers"][0]["SourceRegion"] == "eu-west-1"
    )


@mock_config
def test_put_evaluations():
    client = boto3.client("config", region_name="us-west-2")

    # Try without Evaluations supplied:
    with assert_raises(ClientError) as ce:
        client.put_evaluations(Evaluations=[], ResultToken="test", TestMode=True)
    assert ce.exception.response["Error"]["Code"] == "InvalidParameterValueException"
    assert (
        "The Evaluations object in your request cannot be null"
        in ce.exception.response["Error"]["Message"]
    )

    # Try without a ResultToken supplied:
    with assert_raises(ClientError) as ce:
        client.put_evaluations(
            Evaluations=[
                {
                    "ComplianceResourceType": "AWS::ApiGateway::RestApi",
                    "ComplianceResourceId": "test-api",
                    "ComplianceType": "INSUFFICIENT_DATA",
                    "OrderingTimestamp": datetime(2015, 1, 1),
                }
            ],
            ResultToken="",
            TestMode=True,
        )
    assert ce.exception.response["Error"]["Code"] == "InvalidResultTokenException"

    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "true":
        raise SkipTest("Does not work in server mode due to error in Workzeug")
    else:
        # Try without TestMode supplied:
        with assert_raises(NotImplementedError):
            client.put_evaluations(
                Evaluations=[
                    {
                        "ComplianceResourceType": "AWS::ApiGateway::RestApi",
                        "ComplianceResourceId": "test-api",
                        "ComplianceType": "INSUFFICIENT_DATA",
                        "OrderingTimestamp": datetime(2015, 1, 1),
                    }
                ],
                ResultToken="test",
            )

    # Now with proper params:
    response = client.put_evaluations(
        Evaluations=[
            {
                "ComplianceResourceType": "AWS::ApiGateway::RestApi",
                "ComplianceResourceId": "test-api",
                "ComplianceType": "INSUFFICIENT_DATA",
                "OrderingTimestamp": datetime(2015, 1, 1),
            }
        ],
        TestMode=True,
        ResultToken="test",
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {"FailedEvaluations": [], "ResponseMetadata": {"HTTPStatusCode": 200,},}
    )
