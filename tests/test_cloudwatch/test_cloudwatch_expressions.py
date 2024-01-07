from datetime import datetime, timedelta, timezone

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


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
