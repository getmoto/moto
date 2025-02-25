from datetime import datetime, timedelta, timezone
from time import sleep
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core.utils import utcnow
from tests.test_cloudwatch import cloudwatch_aws_verified


@mock_aws
def test_get_metric_data__no_metric_data_or_expression():
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    with pytest.raises(ClientError) as exc:
        cloudwatch.get_metric_data(
            MetricDataQueries=[{"Id": "result1", "Label": "e1"}],
            StartTime=utc_now - timedelta(minutes=5),
            EndTime=utc_now,
            ScanBy="TimestampDescending",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "The parameter MetricDataQueries.member.1.MetricStat is required.\n"
    )


@mock_aws
def test_get_metric_data_with_simple_expression():
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace = "my_namespace/"
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": "metric",
                "Value": 25,
                "Unit": "Bytes",
            },
        ],
    )
    # get_metric_data 1
    results = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "result1",
                "Expression": "totalBytes",
                "Label": "e1",
            },
            {
                "Id": "totalBytes",
                "MetricStat": {
                    "Metric": {"Namespace": namespace, "MetricName": "metric"},
                    "Period": 60,
                    "Stat": "Sum",
                    "Unit": "Bytes",
                },
                "ReturnData": False,
            },
        ],
        StartTime=utc_now - timedelta(minutes=5),
        EndTime=utc_now + timedelta(minutes=5),
        ScanBy="TimestampDescending",
    )["MetricDataResults"]
    #
    assert len(results) == 1
    assert results[0]["Id"] == "result1"
    assert results[0]["Label"] == "e1"
    assert results[0]["Values"] == [25.0]


@cloudwatch_aws_verified
@pytest.mark.aws_verified
def test_get_metric_data_with_expressive_expression():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    my_namespace = f"Test/FakeNamespace_{str(uuid4())[0:6]}"
    cloudwatch.put_metric_data(
        Namespace=my_namespace,
        MetricData=[
            {
                "MetricName": "ApiResponse",
                "Dimensions": [
                    {"Name": "Path", "Value": "/my/path"},
                    {"Name": "Audience", "Value": "my audience"},
                ],
                "Timestamp": utcnow(),
                "StatisticValues": {
                    "Maximum": 10,
                    "Minimum": 0,
                    "Sum": 10,
                    "SampleCount": 10,
                },
            }
        ],
    )

    expression = f"SELECT SUM(ApiResponse) FROM \"{my_namespace}\" WHERE Path = '/my/path' GROUP BY Audience"
    start_time = utcnow() - timedelta(hours=1)
    end_time = utcnow() + timedelta(hours=1)

    for _ in range(60):
        result = cloudwatch.get_metric_data(
            StartTime=start_time,
            EndTime=end_time,
            MetricDataQueries=[
                {
                    "Id": "query",
                    "Period": 60,
                    "Expression": expression,
                }
            ],
        )["MetricDataResults"]
        if result:
            assert len(result) == 1
            assert result[0]["Id"] == "query"
            # If the Label is not supplied, AWS uses:
            #     the group value as the query name, if the query contains a GROUP BY clause
            #     the Id if no GROUP BY clause exists
            # But Moto doesn't understand expressions, so we always use the Id
            assert result[0]["Label"]
            assert result[0]["Values"] == [10.0]
            assert result[0]["StatusCode"] == "Complete"
            return
        else:
            sleep(5)
    assert False, "Should have found metrics within 5 minutes"
