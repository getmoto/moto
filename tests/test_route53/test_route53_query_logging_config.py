"""Route53 unit tests specific to query_logging_config APIs."""
import pytest

import boto3
from botocore.exceptions import ClientError

from moto import mock_logs
from moto import mock_route53
from moto import settings
from moto.core import ACCOUNT_ID
from moto.core.utils import get_random_hex

# The log group must be in the us-east-1 region.
LOG_TEST_REGION = "us-east-1"
TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


@mock_route53
def create_hosted_zone_id(route53_client, hosted_zone_test_name):
    """Return ID of a newly created Route53 public hosted zone"""
    response = route53_client.create_hosted_zone(
        Name=hosted_zone_test_name,
        CallerReference=f"test_caller_ref_{get_random_hex(6)}",
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert "HostedZone" in response and response["HostedZone"]["Id"]
    return response["HostedZone"]["Id"]


@mock_logs
def create_log_group_arn(hosted_zone_test_name):
    """Return ARN of a newly created CloudWatch log group."""
    logs_client = boto3.client("logs", region_name=LOG_TEST_REGION)
    log_group_name = f"/aws/route53/{hosted_zone_test_name}"
    response = logs_client.create_log_group(logGroupName=log_group_name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    log_group_arn = None
    response = logs_client.describe_log_groups()
    for entry in response["logGroups"]:
        if entry["logGroupName"] == log_group_name:
            log_group_arn = entry["arn"]
            break
    return log_group_arn


@mock_route53
def test_create_query_logging_config_bad_args():
    """Test bad arguments to create_query_logging_config()."""
    client = boto3.client("route53", region_name=TEST_REGION)
    hosted_zone_test_name = f"route53_query_log_{get_random_hex(6)}.test"
    hosted_zone_id = create_hosted_zone_id(client, hosted_zone_test_name)
    log_group_arn = create_log_group_arn(hosted_zone_test_name)

    # Check exception:  NoSuchHostedZone
    with pytest.raises(ClientError) as exc:
        client.create_query_logging_config(
            HostedZoneId="foo", CloudWatchLogsLogGroupArn=log_group_arn,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchHostedZone"
    assert "No hosted zone found with ID: foo" in err["Message"]

    # Check exception:  InvalidInput (bad CloudWatch Logs log ARN)
    with pytest.raises(ClientError) as exc:
        client.create_query_logging_config(
            HostedZoneId=hosted_zone_id,
            CloudWatchLogsLogGroupArn=f"arn:aws:logs:{TEST_REGION}:{ACCOUNT_ID}:foo-bar:foo",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"
    assert "The ARN for the CloudWatch Logs log group is invalid" in err["Message"]

    # Check exception:  InvalidInput (CloudWatch Logs log not in us-east-1)
    with pytest.raises(ClientError) as exc:
        client.create_query_logging_config(
            HostedZoneId=hosted_zone_id,
            CloudWatchLogsLogGroupArn=log_group_arn.replace(
                LOG_TEST_REGION, "us-west-1"
            ),
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"
    assert "The ARN for the CloudWatch Logs log group is invalid" in err["Message"]

    # Check exception:  NoSuchCloudWatchLogsLogGroup
    with pytest.raises(ClientError) as exc:
        client.create_query_logging_config(
            HostedZoneId=hosted_zone_id,
            CloudWatchLogsLogGroupArn=log_group_arn.replace(
                hosted_zone_test_name, "foo"
            ),
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchCloudWatchLogsLogGroup"
    assert "The specified CloudWatch Logs log group doesn't exist" in err["Message"]

    # Check exception:  QueryLoggingConfigAlreadyExists
    client.create_query_logging_config(
        HostedZoneId=hosted_zone_id, CloudWatchLogsLogGroupArn=log_group_arn,
    )
    with pytest.raises(ClientError) as exc:
        client.create_query_logging_config(
            HostedZoneId=hosted_zone_id, CloudWatchLogsLogGroupArn=log_group_arn,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "QueryLoggingConfigAlreadyExists"
    assert (
        "A query logging configuration already exists for this hosted zone"
        in err["Message"]
    )


@mock_route53
def test_create_query_logging_config():
    """Test a valid create_logging_config() request."""
    client = boto3.client("route53", region_name=TEST_REGION)

    hosted_zone_test_name = f"route53_query_log_{get_random_hex(6)}.test"
    hosted_zone_id = create_hosted_zone_id(client, hosted_zone_test_name)
    log_group_arn = create_log_group_arn(hosted_zone_test_name)

    response = client.create_query_logging_config(
        HostedZoneId=hosted_zone_id, CloudWatchLogsLogGroupArn=log_group_arn,
    )
    config = response["QueryLoggingConfig"]
    assert config["HostedZoneId"] == hosted_zone_id.split("/")[-1]
    assert config["CloudWatchLogsLogGroupArn"] == log_group_arn
    assert config["Id"]

    location = response["Location"]
    assert (
        location
        == f"https://route53.amazonaws.com/2013-04-01/queryloggingconfig/{config['Id']}"
    )


@mock_route53
def test_delete_query_logging_config():
    """Test valid and invalid delete_query_logging_config requests."""
    client = boto3.client("route53", region_name=TEST_REGION)

    # Create a query logging config that can then be deleted.
    hosted_zone_test_name = f"route53_query_log_{get_random_hex(6)}.test"
    hosted_zone_id = create_hosted_zone_id(client, hosted_zone_test_name)
    log_group_arn = create_log_group_arn(hosted_zone_test_name)

    query_response = client.create_query_logging_config(
        HostedZoneId=hosted_zone_id, CloudWatchLogsLogGroupArn=log_group_arn,
    )

    # Test the deletion.
    query_id = query_response["QueryLoggingConfig"]["Id"]
    response = client.delete_query_logging_config(Id=query_id)
    # There is no response other than the usual ResponseMetadata.
    assert list(response.keys()) == ["ResponseMetadata"]

    # Test the deletion of a non-existent query logging config, i.e., the
    # one that was just deleted.
    with pytest.raises(ClientError) as exc:
        client.delete_query_logging_config(Id=query_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchQueryLoggingConfig"
    assert "The query logging configuration does not exist" in err["Message"]


@mock_route53
def test_get_query_logging_config():
    """Test valid and invalid get_query_logging_config requests."""
    client = boto3.client("route53", region_name=TEST_REGION)

    # Create a query logging config that can then be retrieved.
    hosted_zone_test_name = f"route53_query_log_{get_random_hex(6)}.test"
    hosted_zone_id = create_hosted_zone_id(client, hosted_zone_test_name)
    log_group_arn = create_log_group_arn(hosted_zone_test_name)

    query_response = client.create_query_logging_config(
        HostedZoneId=hosted_zone_id, CloudWatchLogsLogGroupArn=log_group_arn,
    )

    # Test the retrieval.
    query_id = query_response["QueryLoggingConfig"]["Id"]
    response = client.get_query_logging_config(Id=query_id)
    config = response["QueryLoggingConfig"]
    assert config["HostedZoneId"] == hosted_zone_id.split("/")[-1]
    assert config["CloudWatchLogsLogGroupArn"] == log_group_arn
    assert config["Id"]

    # Test the retrieval of a non-existent query logging config.
    with pytest.raises(ClientError) as exc:
        client.get_query_logging_config(Id="1234567890")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchQueryLoggingConfig"
    assert "The query logging configuration does not exist" in err["Message"]
