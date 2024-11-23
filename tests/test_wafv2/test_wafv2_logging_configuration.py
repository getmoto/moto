import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_logging_configuration_crud():
    wafv2_client = boto3.client("wafv2", region_name="us-east-1")
    create_web_acl_response = wafv2_client.create_web_acl(
        Name="TestWebACL",
        Scope="REGIONAL",
        DefaultAction={"Allow": {}},
        VisibilityConfig={
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "TestWebACLMetric",
        },
        Rules=[],
    )
    web_acl_arn = create_web_acl_response["Summary"]["ARN"]

    # Create log groups
    logs_client = boto3.client("logs", region_name="us-east-1")
    logs_client.create_log_group(logGroupName="aws-waf-logs-test")
    log_group = logs_client.describe_log_groups(logGroupNamePrefix="aws-waf-logs-test")[
        "logGroups"
    ][0]

    create_response = wafv2_client.put_logging_configuration(
        LoggingConfiguration={
            "ResourceArn": web_acl_arn,
            "LogDestinationConfigs": [log_group["arn"]],
        }
    )

    assert "LoggingConfiguration" in create_response
    logging_configuration = create_response["LoggingConfiguration"]
    assert logging_configuration["ResourceArn"]

    get_response = wafv2_client.get_logging_configuration(
        ResourceArn=logging_configuration["ResourceArn"]
    )
    assert "LoggingConfiguration" in get_response

    wafv2_client.delete_logging_configuration(
        ResourceArn=logging_configuration["ResourceArn"],
    )

    with pytest.raises(ClientError) as e:
        wafv2_client.get_logging_configuration(
            ResourceArn=logging_configuration["ResourceArn"]
        )
    assert e.value.response["Error"]["Code"] == "WAFNonexistentItemException"


@mock_aws
def test_list_logging_config_pagination():
    wafv2_client = boto3.client("wafv2", region_name="us-east-1")

    for idx in range(10):
        web_acl_arn = wafv2_client.create_web_acl(
            Name=f"TestWebACL{idx}",
            Scope="REGIONAL",
            DefaultAction={"Allow": {}},
            VisibilityConfig={
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": "TestWebACLMetric",
            },
            Rules=[],
        )["Summary"]["ARN"]
        wafv2_client.put_logging_configuration(
            LoggingConfiguration={
                "ResourceArn": web_acl_arn,
                "LogDestinationConfigs": ["arn:aws:us-east-1:logs:arn"],
            }
        )

    list_all = wafv2_client.list_logging_configurations(Scope="REGIONAL")
    assert len(list_all["LoggingConfigurations"]) == 10

    page1 = wafv2_client.list_logging_configurations(Scope="REGIONAL", Limit=2)
    assert len(page1["LoggingConfigurations"]) == 2

    page2 = wafv2_client.list_logging_configurations(
        Scope="REGIONAL", Limit=3, NextMarker=page1["NextMarker"]
    )
    assert len(page2["LoggingConfigurations"]) == 3

    page3 = wafv2_client.list_logging_configurations(
        Scope="REGIONAL", NextMarker=page2["NextMarker"]
    )
    assert len(page3["LoggingConfigurations"]) == 5
