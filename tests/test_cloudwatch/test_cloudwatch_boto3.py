import boto3
import pytest

from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone
from dateutil.tz import tzutc
from decimal import Decimal
from freezegun import freeze_time
from operator import itemgetter
from uuid import uuid4

from moto import mock_cloudwatch, mock_s3
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_cloudwatch
def test_put_metric_data_no_dimensions():
    conn = boto3.client("cloudwatch", region_name="us-east-1")

    conn.put_metric_data(
        Namespace="tester", MetricData=[dict(MetricName="metric", Value=1.5)]
    )

    metrics = conn.list_metrics()["Metrics"]
    assert {"Namespace": "tester", "MetricName": "metric", "Dimensions": []} in metrics


@mock_cloudwatch
def test_put_metric_data_can_not_have_nan():
    client = boto3.client("cloudwatch", region_name="us-west-2")
    utc_now = datetime.now(tz=timezone.utc)
    with pytest.raises(ClientError) as exc:
        client.put_metric_data(
            Namespace="mynamespace",
            MetricData=[
                {
                    "MetricName": "mymetric",
                    "Timestamp": utc_now,
                    "Value": Decimal("NaN"),
                    "Unit": "Count",
                }
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "The value NaN for parameter MetricData.member.1.Value is invalid."
    )


@mock_cloudwatch
def test_put_metric_data_can_not_have_value_and_values():
    client = boto3.client("cloudwatch", region_name="us-west-2")
    utc_now = datetime.now(tz=timezone.utc)
    with pytest.raises(ClientError) as exc:
        client.put_metric_data(
            Namespace="mynamespace",
            MetricData=[
                {
                    "MetricName": "mymetric",
                    "Timestamp": utc_now,
                    "Value": 1.5,
                    "Values": [1.0, 10.0],
                    "Unit": "Count",
                }
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "The parameters MetricData.member.1.Value and MetricData.member.1.Values are mutually exclusive and you have specified both."
    )


@mock_cloudwatch
def test_put_metric_data_can_not_have_and_values_mismatched_counts():
    client = boto3.client("cloudwatch", region_name="us-west-2")
    utc_now = datetime.now(tz=timezone.utc)
    with pytest.raises(ClientError) as exc:
        client.put_metric_data(
            Namespace="mynamespace",
            MetricData=[
                {
                    "MetricName": "mymetric",
                    "Timestamp": utc_now,
                    "Values": [1.0, 10.0],
                    "Counts": [2, 4, 1],
                    "Unit": "Count",
                }
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "The parameters MetricData.member.1.Values and MetricData.member.1.Counts must be of the same size."
    )


@mock_cloudwatch
def test_put_metric_data_values_and_counts():
    client = boto3.client("cloudwatch", region_name="us-west-2")
    utc_now = datetime.now(tz=timezone.utc)
    namespace = "values"
    metric = "mymetric"
    client.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": metric,
                "Timestamp": utc_now,
                "Values": [1.0, 10.0],
                "Counts": [2, 4],
            }
        ],
    )
    stats = client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric,
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
        Period=60,
        Statistics=["SampleCount", "Sum", "Maximum"],
    )
    datapoint = stats["Datapoints"][0]
    assert datapoint["SampleCount"] == 6.0
    assert datapoint["Sum"] == 42.0
    assert datapoint["Maximum"] == 10.0


@mock_cloudwatch
def test_put_metric_data_values_without_counts():
    client = boto3.client("cloudwatch", region_name="us-west-2")
    utc_now = datetime.now(tz=timezone.utc)
    namespace = "values"
    metric = "mymetric"
    client.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": metric,
                "Timestamp": utc_now,
                "Values": [1.0, 10.0, 23.45],
            }
        ],
    )
    stats = client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric,
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
        Period=60,
        Statistics=["SampleCount", "Sum", "Maximum"],
    )
    datapoint = stats["Datapoints"][0]
    assert datapoint["SampleCount"] == 3.0
    assert datapoint["Sum"] == 34.45
    assert datapoint["Maximum"] == 23.45


@mock_cloudwatch
def test_put_metric_data_value_and_statistics():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        conn.put_metric_data(
            Namespace="statistics",
            MetricData=[
                dict(
                    MetricName="stats",
                    Value=123.0,
                    StatisticValues=dict(
                        Sum=10.0, Maximum=9.0, Minimum=1.0, SampleCount=2
                    ),
                )
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "The parameters MetricData.member.1.Value and MetricData.member.1.StatisticValues are mutually exclusive and you have specified both."
    )


@mock_cloudwatch
def test_put_metric_data_with_statistics():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=timezone.utc)

    conn.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName="statmetric",
                Timestamp=utc_now,
                # no Value to test  https://github.com/getmoto/moto/issues/1615
                StatisticValues=dict(
                    SampleCount=3.0, Sum=123.0, Maximum=100.0, Minimum=12.0
                ),
                Unit="Milliseconds",
                StorageResolution=123,
            )
        ],
    )

    metrics = conn.list_metrics()["Metrics"]
    assert {
        "Namespace": "tester",
        "MetricName": "statmetric",
        "Dimensions": [],
    } in metrics

    stats = conn.get_metric_statistics(
        Namespace="tester",
        MetricName="statmetric",
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
        Period=60,
        Statistics=["SampleCount", "Sum", "Maximum", "Minimum", "Average"],
    )

    assert len(stats["Datapoints"]) == 1
    datapoint = stats["Datapoints"][0]
    assert datapoint["SampleCount"] == 3.0
    assert datapoint["Sum"] == 123.0
    assert datapoint["Minimum"] == 12.0
    assert datapoint["Maximum"] == 100.0
    assert datapoint["Average"] == 41.0

    # add single value
    conn.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName="statmetric",
                Timestamp=utc_now,
                Value=101.0,
                Unit="Milliseconds",
            )
        ],
    )
    # check stats again - should have changed, because there is one more datapoint
    stats = conn.get_metric_statistics(
        Namespace="tester",
        MetricName="statmetric",
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
        Period=60,
        Statistics=["SampleCount", "Sum", "Maximum", "Minimum", "Average"],
    )

    assert len(stats["Datapoints"]) == 1
    datapoint = stats["Datapoints"][0]
    assert datapoint["SampleCount"] == 4.0
    assert datapoint["Sum"] == 224.0
    assert datapoint["Minimum"] == 12.0
    assert datapoint["Maximum"] == 101.0
    assert datapoint["Average"] == 56.0


@mock_cloudwatch
def test_get_metric_statistics():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=timezone.utc)

    conn.put_metric_data(
        Namespace="tester",
        MetricData=[dict(MetricName="metric", Value=1.5, Timestamp=utc_now)],
    )

    stats = conn.get_metric_statistics(
        Namespace="tester",
        MetricName="metric",
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
        Period=60,
        Statistics=["SampleCount", "Sum"],
    )

    assert len(stats["Datapoints"]) == 1
    datapoint = stats["Datapoints"][0]
    assert datapoint["SampleCount"] == 1.0
    assert datapoint["Sum"] == 1.5


@mock_cloudwatch
def test_get_metric_invalid_parameter_combination():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=timezone.utc)

    conn.put_metric_data(
        Namespace="tester",
        MetricData=[dict(MetricName="metric", Value=1.5, Timestamp=utc_now)],
    )

    with pytest.raises(ClientError) as exc:
        # make request without both statistics or extended statistics parameters
        conn.get_metric_statistics(
            Namespace="tester",
            MetricName="metric",
            StartTime=utc_now - timedelta(seconds=60),
            EndTime=utc_now + timedelta(seconds=60),
            Period=60,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert err["Message"] == "Must specify either Statistics or ExtendedStatistics"


@mock_cloudwatch
def test_get_metric_statistics_dimensions():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=timezone.utc)

    # put metric data with different dimensions
    dimensions1 = [{"Name": "dim1", "Value": "v1"}]
    dimensions2 = dimensions1 + [{"Name": "dim2", "Value": "v2"}]
    metric_name = "metr-stats-dims"
    conn.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName=metric_name,
                Value=1,
                Timestamp=utc_now,
                Dimensions=dimensions1,
            )
        ],
    )
    conn.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName=metric_name,
                Value=2,
                Timestamp=utc_now,
                Dimensions=dimensions1,
            )
        ],
    )
    conn.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName=metric_name,
                Value=6,
                Timestamp=utc_now,
                Dimensions=dimensions2,
            )
        ],
    )

    # list of (<kwargs>, <expectedSum>, <expectedAverage>)
    params_list = (
        # get metric stats with no restriction on dimensions
        ({}, 9, 3),
        # get metric stats for dimensions1 (should also cover dimensions2)
        ({"Dimensions": dimensions1}, 9, 3),
        # get metric stats for dimensions2 only
        ({"Dimensions": dimensions2}, 6, 6),
    )

    for params in params_list:
        stats = conn.get_metric_statistics(
            Namespace="tester",
            MetricName=metric_name,
            StartTime=utc_now - timedelta(seconds=60),
            EndTime=utc_now + timedelta(seconds=60),
            Period=60,
            Statistics=["Average", "Sum"],
            **params[0],
        )
        assert len(stats["Datapoints"]) == 1
        datapoint = stats["Datapoints"][0]
        assert datapoint["Sum"] == params[1]
        assert datapoint["Average"] == params[2]


@mock_cloudwatch
def test_get_metric_statistics_endtime_sooner_than_starttime():
    # given
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    # when
    with pytest.raises(ClientError) as e:
        # get_metric_statistics
        cloudwatch.get_metric_statistics(
            Namespace="tester",
            MetricName="metric",
            StartTime=utc_now + timedelta(seconds=1),
            EndTime=utc_now,
            Period=60,
            Statistics=["SampleCount"],
        )

    # then
    ex = e.value
    assert ex.operation_name == "GetMetricStatistics"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterValue"
    assert (
        ex.response["Error"]["Message"]
        == "The parameter StartTime must be less than the parameter EndTime."
    )


@mock_cloudwatch
def test_get_metric_statistics_starttime_endtime_equals():
    # given
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    # when
    with pytest.raises(ClientError) as e:
        # get_metric_statistics
        cloudwatch.get_metric_statistics(
            Namespace="tester",
            MetricName="metric",
            StartTime=utc_now,
            EndTime=utc_now,
            Period=60,
            Statistics=["SampleCount"],
        )

    # then
    ex = e.value
    assert ex.operation_name == "GetMetricStatistics"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterValue"
    assert (
        ex.response["Error"]["Message"]
        == "The parameter StartTime must be less than the parameter EndTime."
    )


@mock_cloudwatch
def test_get_metric_statistics_starttime_endtime_within_1_second():
    # given
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    # when
    with pytest.raises(ClientError) as e:
        # get_metric_statistics
        cloudwatch.get_metric_statistics(
            Namespace="tester",
            MetricName="metric",
            StartTime=utc_now.replace(microsecond=20 * 1000),
            EndTime=utc_now.replace(microsecond=987 * 1000),
            Period=60,
            Statistics=["SampleCount"],
        )

    # then
    ex = e.value
    assert ex.operation_name == "GetMetricStatistics"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterValue"
    assert (
        ex.response["Error"]["Message"]
        == "The parameter StartTime must be less than the parameter EndTime."
    )


@mock_cloudwatch
def test_get_metric_statistics_starttime_endtime_ignore_miliseconds():
    cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=timezone.utc)

    cloudwatch.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName="metric",
                Value=1.5,
                Timestamp=utc_now.replace(microsecond=200 * 1000),
            )
        ],
    )

    stats = cloudwatch.get_metric_statistics(
        Namespace="tester",
        MetricName="metric",
        StartTime=utc_now.replace(microsecond=999 * 1000),
        EndTime=utc_now + timedelta(seconds=1),
        Period=60,
        Statistics=["SampleCount", "Sum"],
    )

    assert len(stats["Datapoints"]) == 1
    datapoint = stats["Datapoints"][0]
    assert datapoint["SampleCount"] == 1.0
    assert datapoint["Sum"] == 1.5


@mock_cloudwatch
def test_duplicate_put_metric_data():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=timezone.utc)

    conn.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName="metric",
                Dimensions=[{"Name": "Name", "Value": "B"}],
                Value=1.5,
                Timestamp=utc_now,
            )
        ],
    )

    result = conn.list_metrics(
        Namespace="tester", Dimensions=[{"Name": "Name", "Value": "B"}]
    )["Metrics"]
    assert len(result) == 1

    conn.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName="metric",
                Dimensions=[{"Name": "Name", "Value": "B"}],
                Value=1.5,
                Timestamp=utc_now,
            )
        ],
    )

    result = conn.list_metrics(
        Namespace="tester", Dimensions=[{"Name": "Name", "Value": "B"}]
    )["Metrics"]
    assert len(result) == 1
    assert result == [
        {
            "Namespace": "tester",
            "MetricName": "metric",
            "Dimensions": [{"Name": "Name", "Value": "B"}],
        }
    ]

    conn.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName="metric",
                Dimensions=[
                    {"Name": "Name", "Value": "B"},
                    {"Name": "Name", "Value": "C"},
                ],
                Value=1.5,
                Timestamp=utc_now,
            )
        ],
    )

    result = conn.list_metrics(
        Namespace="tester", Dimensions=[{"Name": "Name", "Value": "B"}]
    )["Metrics"]
    assert result == [
        {
            "Namespace": "tester",
            "MetricName": "metric",
            "Dimensions": [{"Name": "Name", "Value": "B"}],
        },
        {
            "Namespace": "tester",
            "MetricName": "metric",
            "Dimensions": [
                {"Name": "Name", "Value": "B"},
                {"Name": "Name", "Value": "C"},
            ],
        },
    ]

    result = conn.list_metrics(
        Namespace="tester", Dimensions=[{"Name": "Name", "Value": "C"}]
    )["Metrics"]
    assert result == [
        {
            "Namespace": "tester",
            "MetricName": "metric",
            "Dimensions": [
                {"Name": "Name", "Value": "B"},
                {"Name": "Name", "Value": "C"},
            ],
        }
    ]


@mock_cloudwatch
@freeze_time("2020-02-10 18:44:05")
def test_custom_timestamp():
    utc_now = datetime.now(tz=timezone.utc)
    time = "2020-02-10T18:44:09Z"
    cw = boto3.client("cloudwatch", "eu-west-1")

    cw.put_metric_data(
        Namespace="tester",
        MetricData=[dict(MetricName="metric1", Value=1.5, Timestamp=time)],
    )

    cw.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(MetricName="metric2", Value=1.5, Timestamp=datetime(2020, 2, 10))
        ],
    )

    resp = cw.get_metric_statistics(
        Namespace="tester",
        MetricName="metric",
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
        Period=60,
        Statistics=["SampleCount", "Sum"],
    )
    assert resp["Datapoints"] == []


@mock_cloudwatch
def test_list_metrics():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    # Verify namespace has to exist
    res = cloudwatch.list_metrics(Namespace="unknown/")["Metrics"]
    assert res == []
    # Create some metrics to filter on
    create_metrics(cloudwatch, namespace="list_test_1/", metrics=4, data_points=2)
    create_metrics(cloudwatch, namespace="list_test_2/", metrics=4, data_points=2)
    # Verify we can retrieve everything
    res = cloudwatch.list_metrics()["Metrics"]
    assert len(res) >= 16  # 2 namespaces * 4 metrics * 2 data points
    # Verify we can filter by namespace/metric name
    res = cloudwatch.list_metrics(Namespace="list_test_1/")["Metrics"]
    assert len(res) == 8  # 1 namespace * 4 metrics * 2 data points
    res = cloudwatch.list_metrics(Namespace="list_test_1/", MetricName="metric1")[
        "Metrics"
    ]
    assert len(res) == 2  # 1 namespace * 1 metrics * 2 data points
    # Verify format
    assert res == [
        {"Namespace": "list_test_1/", "Dimensions": [], "MetricName": "metric1"},
        {"Namespace": "list_test_1/", "Dimensions": [], "MetricName": "metric1"},
    ]
    # Verify unknown namespace still has no results
    res = cloudwatch.list_metrics(Namespace="unknown/")["Metrics"]
    assert res == []


@mock_cloudwatch
def test_list_metrics_paginated():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    # Verify that only a single page of metrics is returned
    assert "NextToken" not in cloudwatch.list_metrics()

    # Verify we can't pass a random NextToken
    with pytest.raises(ClientError) as e:
        cloudwatch.list_metrics(NextToken=str(uuid4()))
    assert (
        e.value.response["Error"]["Message"] == "Request parameter NextToken is invalid"
    )

    # Add a boatload of metrics
    create_metrics(cloudwatch, namespace="test", metrics=100, data_points=1)
    # Verify that a single page is returned until we've reached 500
    first_page = cloudwatch.list_metrics(Namespace="test")
    assert len(first_page["Metrics"]) == 100

    assert len(first_page["Metrics"]) == 100
    create_metrics(cloudwatch, namespace="test", metrics=200, data_points=2)
    first_page = cloudwatch.list_metrics(Namespace="test")
    assert len(first_page["Metrics"]) == 500
    assert "NextToken" not in first_page
    # Verify that adding more data points results in pagination
    create_metrics(cloudwatch, namespace="test", metrics=60, data_points=10)
    first_page = cloudwatch.list_metrics(Namespace="test")
    assert len(first_page["Metrics"]) == 500

    # Retrieve second page - and verify there's more where that came from
    second_page = cloudwatch.list_metrics(
        Namespace="test", NextToken=first_page["NextToken"]
    )
    assert len(second_page["Metrics"]) == 500

    # Last page should only have the last 100 results, and no NextToken (indicating that pagination is finished)
    third_page = cloudwatch.list_metrics(
        Namespace="test", NextToken=second_page["NextToken"]
    )
    assert len(third_page["Metrics"]) == 100
    assert "NextToken" not in third_page
    # Verify that we can't reuse an existing token
    with pytest.raises(ClientError) as e:
        cloudwatch.list_metrics(Namespace="test", NextToken=first_page["NextToken"])
    assert (
        e.value.response["Error"]["Message"] == "Request parameter NextToken is invalid"
    )


@mock_cloudwatch
def test_list_metrics_without_value():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    # Create some metrics to filter on
    create_metrics_with_dimensions(cloudwatch, namespace="MyNamespace", data_points=3)
    # Verify we can filter by namespace/metric name
    res = cloudwatch.list_metrics(Namespace="MyNamespace")["Metrics"]
    assert len(res) == 3
    # Verify we can filter by Dimension without value
    results = cloudwatch.list_metrics(
        Namespace="MyNamespace", MetricName="MyMetric", Dimensions=[{"Name": "D1"}]
    )["Metrics"]

    assert len(results) == 1
    assert results[0]["Namespace"] == "MyNamespace"
    assert results[0]["MetricName"] == "MyMetric"
    assert results[0]["Dimensions"] == [{"Name": "D1", "Value": "V1"}]


@mock_cloudwatch
def test_list_metrics_with_same_dimensions_different_metric_name():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    # create metrics with same namespace and dimensions but different metric names
    cloudwatch.put_metric_data(
        Namespace="unique/",
        MetricData=[
            {
                "MetricName": "metric1",
                "Dimensions": [{"Name": "D1", "Value": "V1"}],
                "Unit": "Seconds",
            }
        ],
    )

    cloudwatch.put_metric_data(
        Namespace="unique/",
        MetricData=[
            {
                "MetricName": "metric2",
                "Dimensions": [{"Name": "D1", "Value": "V1"}],
                "Unit": "Seconds",
            }
        ],
    )

    results = cloudwatch.list_metrics(Namespace="unique/")["Metrics"]
    assert len(results) == 2

    # duplicating existing metric
    cloudwatch.put_metric_data(
        Namespace="unique/",
        MetricData=[
            {
                "MetricName": "metric1",
                "Dimensions": [{"Name": "D1", "Value": "V1"}],
                "Unit": "Seconds",
            }
        ],
    )

    # asserting only unique values are returned
    results = cloudwatch.list_metrics(Namespace="unique/")["Metrics"]
    assert len(results) == 2


def create_metrics(cloudwatch, namespace, metrics=5, data_points=5):
    for i in range(0, metrics):
        metric_name = "metric" + str(i)
        for j in range(0, data_points):
            cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=[{"MetricName": metric_name, "Value": j, "Unit": "Seconds"}],
            )


def create_metrics_with_dimensions(cloudwatch, namespace, data_points=5):
    for j in range(0, data_points):
        cloudwatch.put_metric_data(
            Namespace=namespace,
            MetricData=[
                {
                    "MetricName": "MyMetric",
                    "Dimensions": [{"Name": f"D{j}", "Value": f"V{j}"}],
                    "Unit": "Seconds",
                }
            ],
        )


@mock_cloudwatch
def test_get_metric_data_for_multiple_metrics_w_same_dimensions():
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace = "my_namespace/"
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": "metric1",
                "Dimensions": [{"Name": "Name", "Value": "B"}],
                "Value": 50,
            },
            {
                "MetricName": "metric2",
                "Dimensions": [{"Name": "Name", "Value": "B"}],
                "Value": 25,
                "Unit": "Microseconds",
            },
        ],
    )
    # get_metric_data 1
    response1 = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "result1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric1",
                        "Dimensions": [{"Name": "Name", "Value": "B"}],
                    },
                    "Period": 60,
                    "Stat": "Sum",
                },
            },
        ],
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
    )
    #
    assert len(response1["MetricDataResults"]) == 1

    res1 = response1["MetricDataResults"][0]
    assert res1["Values"] == [50.0]

    # get_metric_data 2
    response2 = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "result2",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric2",
                        "Dimensions": [{"Name": "Name", "Value": "B"}],
                    },
                    "Period": 60,
                    "Stat": "Sum",
                },
            },
        ],
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
    )
    #
    assert len(response2["MetricDataResults"]) == 1

    res2 = response2["MetricDataResults"][0]
    assert res2["Values"] == [25.0]


@mock_cloudwatch
def test_get_metric_data_within_timeframe():
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace1 = "my_namespace/"
    # put metric data
    values = [0, 2, 4, 3.5, 7, 100]
    cloudwatch.put_metric_data(
        Namespace=namespace1,
        MetricData=[
            {"MetricName": "metric1", "Value": val, "Unit": "Seconds"} for val in values
        ],
    )
    # get_metric_data
    stats = ["Average", "Sum", "Minimum", "Maximum"]
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "result_" + stat,
                "MetricStat": {
                    "Metric": {"Namespace": namespace1, "MetricName": "metric1"},
                    "Period": 60,
                    "Stat": stat,
                },
            }
            for stat in stats
        ],
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
    )
    #
    # Assert Average/Min/Max/Sum is returned as expected
    avg = [
        res for res in response["MetricDataResults"] if res["Id"] == "result_Average"
    ][0]
    assert avg["Label"] == "metric1 Average"
    assert avg["StatusCode"] == "Complete"
    assert [int(val) for val in avg["Values"]] == [19]

    sum_ = [res for res in response["MetricDataResults"] if res["Id"] == "result_Sum"][
        0
    ]
    assert sum_["Label"] == "metric1 Sum"
    assert sum_["StatusCode"] == "Complete"
    assert [val for val in sum_["Values"]] == [sum(values)]

    min_ = [
        res for res in response["MetricDataResults"] if res["Id"] == "result_Minimum"
    ][0]
    assert min_["Label"] == "metric1 Minimum"
    assert min_["StatusCode"] == "Complete"
    assert [int(val) for val in min_["Values"]] == [0]

    max_ = [
        res for res in response["MetricDataResults"] if res["Id"] == "result_Maximum"
    ][0]
    assert max_["Label"] == "metric1 Maximum"
    assert max_["StatusCode"] == "Complete"
    assert [int(val) for val in max_["Values"]] == [100]


@mock_cloudwatch
def test_get_metric_data_partially_within_timeframe():
    utc_now = datetime.now(tz=timezone.utc)
    yesterday = utc_now - timedelta(days=1)
    last_week = utc_now - timedelta(days=7)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace1 = "my_namespace/"
    # put metric data
    cloudwatch.put_metric_data(
        Namespace=namespace1,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": 10,
                "Unit": "Seconds",
                "Timestamp": utc_now,
            }
        ],
    )
    cloudwatch.put_metric_data(
        Namespace=namespace1,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": 20,
                "Unit": "Seconds",
                "Timestamp": yesterday,
            }
        ],
    )

    cloudwatch.put_metric_data(
        Namespace=namespace1,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": 50,
                "Unit": "Seconds",
                "Timestamp": last_week,
            },
            {
                "MetricName": "metric1",
                "Value": 10,
                "Unit": "Seconds",
                "Timestamp": last_week + timedelta(seconds=10),
            },
            {
                "MetricName": "metric1",
                "Value": 20,
                "Unit": "Seconds",
                "Timestamp": last_week + timedelta(seconds=15),
            },
            {
                "MetricName": "metric1",
                "Value": 40,
                "Unit": "Seconds",
                "Timestamp": last_week + timedelta(seconds=30),
            },
        ],
    )

    # data for average, min, max

    def get_data(start, end, stat="Sum", scanBy="TimestampAscending"):
        # get_metric_data
        response = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    "Id": "result",
                    "MetricStat": {
                        "Metric": {"Namespace": namespace1, "MetricName": "metric1"},
                        "Period": 60,
                        "Stat": stat,
                    },
                }
            ],
            StartTime=start,
            EndTime=end,
            ScanBy=scanBy,
        )
        return response

    response = get_data(
        start=yesterday - timedelta(seconds=60), end=utc_now + timedelta(seconds=60)
    )

    # Assert Last week's data is not returned
    assert len(response["MetricDataResults"]) == 1
    sum_ = response["MetricDataResults"][0]
    assert sum_["Label"] == "metric1 Sum"
    assert sum_["StatusCode"] == "Complete"
    assert sum_["Values"] == [20.0, 10.0]
    response = get_data(
        start=yesterday - timedelta(seconds=60),
        end=utc_now + timedelta(seconds=60),
        scanBy="TimestampDescending",
    )
    assert response["MetricDataResults"][0]["Values"] == [10.0, 20.0]

    response = get_data(
        start=last_week - timedelta(seconds=1),
        end=utc_now + timedelta(seconds=60),
        stat="Average",
    )
    # assert average
    assert response["MetricDataResults"][0]["Values"] == [30.0, 20.0, 10.0]

    response = get_data(
        start=last_week - timedelta(seconds=1),
        end=utc_now + timedelta(seconds=60),
        stat="Maximum",
    )
    # assert maximum
    assert response["MetricDataResults"][0]["Values"] == [50.0, 20.0, 10.0]

    response = get_data(
        start=last_week - timedelta(seconds=1),
        end=utc_now + timedelta(seconds=60),
        stat="Minimum",
    )
    # assert minimum
    assert response["MetricDataResults"][0]["Values"] == [10.0, 20.0, 10.0]


@mock_cloudwatch
def test_get_metric_data_outside_timeframe():
    utc_now = datetime.now(tz=timezone.utc)
    last_week = utc_now - timedelta(days=7)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace1 = "my_namespace/"
    # put metric data
    cloudwatch.put_metric_data(
        Namespace=namespace1,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": 50,
                "Unit": "Seconds",
                "Timestamp": last_week,
            }
        ],
    )
    # get_metric_data
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "result",
                "MetricStat": {
                    "Metric": {"Namespace": namespace1, "MetricName": "metric1"},
                    "Period": 60,
                    "Stat": "Sum",
                },
            }
        ],
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
    )
    #
    # Assert Last week's data is not returned
    assert len(response["MetricDataResults"]) == 1
    assert response["MetricDataResults"][0]["Id"] == "result"
    assert response["MetricDataResults"][0]["StatusCode"] == "Complete"
    assert response["MetricDataResults"][0]["Values"] == []


@mock_cloudwatch
def test_get_metric_data_for_multiple_metrics():
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace = "my_namespace/"
    # put metric data
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": 50,
                "Unit": "Seconds",
                "Timestamp": utc_now,
            }
        ],
    )
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": "metric2",
                "Value": 25,
                "Unit": "Seconds",
                "Timestamp": utc_now,
            }
        ],
    )
    # get_metric_data
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "result1",
                "MetricStat": {
                    "Metric": {"Namespace": namespace, "MetricName": "metric1"},
                    "Period": 60,
                    "Stat": "Sum",
                },
            },
            {
                "Id": "result2",
                "MetricStat": {
                    "Metric": {"Namespace": namespace, "MetricName": "metric2"},
                    "Period": 60,
                    "Stat": "Sum",
                },
            },
        ],
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
    )
    #
    assert len(response["MetricDataResults"]) == 2

    res1 = [res for res in response["MetricDataResults"] if res["Id"] == "result1"][0]
    assert res1["Values"] == [50.0]

    res2 = [res for res in response["MetricDataResults"] if res["Id"] == "result2"][0]
    assert res2["Values"] == [25.0]


@mock_cloudwatch
def test_get_metric_data_for_dimensions():
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace = "my_namespace/"

    # If the metric is created with multiple dimensions, then the data points for that metric can be retrieved only by specifying all the configured dimensions.
    # https://aws.amazon.com/premiumsupport/knowledge-center/cloudwatch-getmetricstatistics-data/
    server_prod = {"Name": "Server", "Value": "Prod"}
    dimension_berlin = [server_prod, {"Name": "Domain", "Value": "Berlin"}]
    dimension_frankfurt = [server_prod, {"Name": "Domain", "Value": "Frankfurt"}]

    # put metric data
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": 50,
                "Dimensions": dimension_berlin,
                "Unit": "Seconds",
                "Timestamp": utc_now,
            }
        ],
    )
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": 25,
                "Unit": "Seconds",
                "Dimensions": dimension_frankfurt,
                "Timestamp": utc_now,
            }
        ],
    )
    # get_metric_data
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "result1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric1",
                        "Dimensions": dimension_frankfurt,
                    },
                    "Period": 60,
                    "Stat": "SampleCount",
                },
            },
            {
                "Id": "result2",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric1",
                        "Dimensions": dimension_berlin,
                    },
                    "Period": 60,
                    "Stat": "Sum",
                },
            },
            {
                "Id": "result3",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric1",
                        "Dimensions": [server_prod],
                    },
                    "Period": 60,
                    "Stat": "Sum",
                },
            },
            {
                "Id": "result4",
                "MetricStat": {
                    "Metric": {"Namespace": namespace, "MetricName": "metric1"},
                    "Period": 60,
                    "Stat": "Sum",
                },
            },
        ],
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
    )
    #
    assert len(response["MetricDataResults"]) == 4

    res1 = [res for res in response["MetricDataResults"] if res["Id"] == "result1"][0]
    # expect sample count for dimension_frankfurt
    assert res1["Values"] == [1.0]

    res2 = [res for res in response["MetricDataResults"] if res["Id"] == "result2"][0]
    # expect sum for dimension_berlin
    assert res2["Values"] == [50.0]

    res3 = [res for res in response["MetricDataResults"] if res["Id"] == "result3"][0]
    # expect no result, as server_prod is only a part of other dimensions, e.g. there is no match
    assert res3["Values"] == []

    res4 = [res for res in response["MetricDataResults"] if res["Id"] == "result4"][0]
    # expect sum of both metrics, as we did not filter for dimensions
    assert res4["Values"] == [75.0]


@mock_cloudwatch
def test_get_metric_data_for_unit():
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace = "my_namespace/"

    unit = "Seconds"

    # put metric data
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": 50,
                "Unit": unit,
                "Timestamp": utc_now,
            },
            {
                "MetricName": "metric1",
                "Value": -50,
                "Timestamp": utc_now,
            },
        ],
    )
    # get_metric_data
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "result_without_unit",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric1",
                    },
                    "Period": 60,
                    "Stat": "SampleCount",
                },
            },
            {
                "Id": "result_with_unit",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric1",
                    },
                    "Period": 60,
                    "Stat": "SampleCount",
                    "Unit": unit,
                },
            },
        ],
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
    )

    expected_values = {
        "result_without_unit": 2.0,
        "result_with_unit": 1.0,
    }

    for id_, expected_value in expected_values.items():
        metric_result_data = list(
            filter(
                lambda result_data: result_data["Id"] == id_,
                response["MetricDataResults"],
            )
        )
        assert len(metric_result_data) == 1
        assert metric_result_data[0]["Values"][0] == expected_value


@mock_cloudwatch
def test_get_metric_data_endtime_sooner_than_starttime():
    # given
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    # when
    with pytest.raises(ClientError) as e:
        # get_metric_data
        cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    "Id": "test",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "my_namespace/",
                            "MetricName": "metric1",
                        },
                        "Period": 60,
                        "Stat": "SampleCount",
                    },
                },
            ],
            StartTime=utc_now + timedelta(seconds=1),
            EndTime=utc_now,
        )

    # then
    ex = e.value
    assert ex.operation_name == "GetMetricData"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    err = ex.response["Error"]
    assert err["Code"] == "ValidationError"
    assert err["Message"] == "The parameter EndTime must be greater than StartTime."


@mock_cloudwatch
def test_get_metric_data_starttime_endtime_equals():
    # given
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    # when
    with pytest.raises(ClientError) as e:
        # get_metric_data
        cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    "Id": "test",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "my_namespace/",
                            "MetricName": "metric1",
                        },
                        "Period": 60,
                        "Stat": "SampleCount",
                    },
                },
            ],
            StartTime=utc_now,
            EndTime=utc_now,
        )

    # then
    ex = e.value
    assert ex.operation_name == "GetMetricData"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    err = ex.response["Error"]
    assert err["Code"] == "ValidationError"
    assert err["Message"] == "The parameter StartTime must not equal parameter EndTime."


@mock_cloudwatch
def test_get_metric_data_starttime_endtime_within_1_second():
    # given
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    # when
    with pytest.raises(ClientError) as e:
        # get_metric_data
        cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    "Id": "test",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "my_namespace/",
                            "MetricName": "metric1",
                        },
                        "Period": 60,
                        "Stat": "SampleCount",
                    },
                },
            ],
            StartTime=utc_now.replace(microsecond=20 * 1000),
            EndTime=utc_now.replace(microsecond=987 * 1000),
        )

    # then
    ex = e.value
    assert ex.operation_name == "GetMetricData"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ValidationError"
    assert (
        ex.response["Error"]["Message"]
        == "The parameter StartTime must not equal parameter EndTime."
    )


@mock_cloudwatch
def test_get_metric_data_starttime_endtime_ignore_miliseconds():
    utc_now = datetime.now(tz=timezone.utc).replace(microsecond=200 * 1000)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace = "my_namespace/"

    # put metric data
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": -50,
                "Timestamp": utc_now,
            },
        ],
    )
    # get_metric_data
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "test",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric1",
                    },
                    "Period": 60,
                    "Stat": "SampleCount",
                },
            },
        ],
        StartTime=utc_now.replace(microsecond=999 * 1000),
        EndTime=(utc_now + timedelta(seconds=1)).replace(microsecond=0),
    )

    assert len(response["MetricDataResults"]) == 1
    assert response["MetricDataResults"][0]["Id"] == "test"
    assert response["MetricDataResults"][0]["Values"][0] == 1.0


@mock_cloudwatch
@mock_s3
def test_cloudwatch_return_s3_metrics():
    utc_now = datetime.now(tz=timezone.utc)
    bucket_name = "examplebucket"
    cloudwatch = boto3.client("cloudwatch", "eu-west-3")

    # given
    s3 = boto3.resource("s3")
    s3_client = boto3.client("s3")
    bucket = s3.Bucket(bucket_name)
    bucket.create(CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
    bucket.put_object(Body=b"ABCD", Key="file.txt")

    # when
    metrics = cloudwatch.list_metrics(
        Dimensions=[{"Name": "BucketName", "Value": bucket_name}]
    )["Metrics"]

    # then
    assert len(metrics) == 2
    assert {
        "Namespace": "AWS/S3",
        "MetricName": "NumberOfObjects",
        "Dimensions": [
            {"Name": "StorageType", "Value": "AllStorageTypes"},
            {"Name": "BucketName", "Value": bucket_name},
        ],
    } in metrics
    assert {
        "Namespace": "AWS/S3",
        "MetricName": "BucketSizeBytes",
        "Dimensions": [
            {"Name": "StorageType", "Value": "StandardStorage"},
            {"Name": "BucketName", "Value": bucket_name},
        ],
    } in metrics

    # when
    stats = cloudwatch.get_metric_statistics(
        Namespace="AWS/S3",
        MetricName="BucketSizeBytes",
        Dimensions=[
            {"Name": "BucketName", "Value": bucket_name},
            {"Name": "StorageType", "Value": "StandardStorage"},
        ],
        StartTime=utc_now - timedelta(days=2),
        EndTime=utc_now,
        Period=86400,
        Statistics=["Average"],
        Unit="Bytes",
    )

    # then
    assert stats["Label"] == "BucketSizeBytes"
    assert len(stats["Datapoints"]) == 1
    data_point = stats["Datapoints"][0]
    assert data_point["Average"] > 0
    assert data_point["Unit"] == "Bytes"

    # when
    stats = cloudwatch.get_metric_statistics(
        Namespace="AWS/S3",
        MetricName="NumberOfObjects",
        Dimensions=[
            {"Name": "BucketName", "Value": bucket_name},
            {"Name": "StorageType", "Value": "AllStorageTypes"},
        ],
        StartTime=utc_now - timedelta(days=2),
        EndTime=utc_now,
        Period=86400,
        Statistics=["Average"],
    )

    # then
    assert stats["Label"] == "NumberOfObjects"
    assert len(stats["Datapoints"]) == 1
    data_point = stats["Datapoints"][0]
    assert data_point["Average"] == 1
    assert data_point["Unit"] == "Count"

    s3_client.delete_object(Bucket=bucket_name, Key="file.txt")
    s3_client.delete_bucket(Bucket=bucket_name)


@mock_cloudwatch
def test_put_metric_alarm():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)
    alarm_name = "test-alarm"
    sns_topic_arn = f"arn:aws:sns:${region_name}:${ACCOUNT_ID}:test-topic"

    # when
    client.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription="test alarm",
        ActionsEnabled=True,
        OKActions=[sns_topic_arn],
        AlarmActions=[sns_topic_arn],
        InsufficientDataActions=[sns_topic_arn],
        MetricName="5XXError",
        Namespace="AWS/ApiGateway",
        Statistic="Sum",
        Dimensions=[
            {"Name": "ApiName", "Value": "test-api"},
            {"Name": "Stage", "Value": "default"},
        ],
        Period=60,
        Unit="Seconds",
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",
        Tags=[{"Key": "key-1", "Value": "value-1"}],
    )

    # then
    alarms = client.describe_alarms(AlarmNames=[alarm_name])["MetricAlarms"]
    assert len(alarms) == 1

    alarm = alarms[0]
    assert alarm["AlarmName"] == alarm_name
    assert (
        alarm["AlarmArn"]
        == f"arn:aws:cloudwatch:{region_name}:{ACCOUNT_ID}:alarm:{alarm_name}"
    )
    assert alarm["AlarmDescription"] == "test alarm"
    assert alarm["AlarmConfigurationUpdatedTimestamp"].tzinfo == tzutc()
    assert alarm["ActionsEnabled"] is True
    assert alarm["OKActions"] == [sns_topic_arn]
    assert alarm["AlarmActions"] == [sns_topic_arn]
    assert alarm["InsufficientDataActions"] == [sns_topic_arn]
    assert alarm["StateValue"] == "OK"
    assert alarm["StateReason"] == "Unchecked: Initial alarm creation"
    assert alarm["StateUpdatedTimestamp"].tzinfo == tzutc()
    assert alarm["MetricName"] == "5XXError"
    assert alarm["Namespace"] == "AWS/ApiGateway"
    assert alarm["Statistic"] == "Sum"
    assert sorted(alarm["Dimensions"], key=itemgetter("Name")) == [
        {"Name": "ApiName", "Value": "test-api"},
        {"Name": "Stage", "Value": "default"},
    ]
    assert alarm["Period"] == 60
    assert alarm["Unit"] == "Seconds"
    assert alarm["EvaluationPeriods"] == 1
    assert alarm["DatapointsToAlarm"] == 1
    assert alarm["Threshold"] == 1.0
    assert alarm["ComparisonOperator"] == "GreaterThanOrEqualToThreshold"
    assert alarm["TreatMissingData"] == "notBreaching"


@mock_cloudwatch
def test_put_metric_alarm_with_percentile():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)
    alarm_name = "test-alarm"

    # when
    client.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription="test alarm",
        ActionsEnabled=True,
        MetricName="5XXError",
        Namespace="AWS/ApiGateway",
        ExtendedStatistic="p90",
        Dimensions=[
            {"Name": "ApiName", "Value": "test-api"},
            {"Name": "Stage", "Value": "default"},
        ],
        Period=60,
        Unit="Seconds",
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",
        EvaluateLowSampleCountPercentile="ignore",
    )

    # then
    alarms = client.describe_alarms(AlarmNames=[alarm_name])["MetricAlarms"]
    assert len(alarms) == 1

    alarm = alarms[0]
    assert alarm["AlarmName"] == alarm_name
    assert (
        alarm["AlarmArn"]
        == f"arn:aws:cloudwatch:{region_name}:{ACCOUNT_ID}:alarm:{alarm_name}"
    )
    assert alarm["AlarmDescription"] == "test alarm"
    assert alarm["AlarmConfigurationUpdatedTimestamp"].tzinfo == tzutc()
    assert alarm["ActionsEnabled"] is True
    assert alarm["StateValue"] == "OK"
    assert alarm["StateReason"] == "Unchecked: Initial alarm creation"
    assert alarm["StateUpdatedTimestamp"].tzinfo == tzutc()
    assert alarm["MetricName"] == "5XXError"
    assert alarm["Namespace"] == "AWS/ApiGateway"
    assert alarm["ExtendedStatistic"] == "p90"
    assert sorted(alarm["Dimensions"], key=itemgetter("Name")) == [
        {"Name": "ApiName", "Value": "test-api"},
        {"Name": "Stage", "Value": "default"},
    ]
    assert alarm["Period"] == 60
    assert alarm["Unit"] == "Seconds"
    assert alarm["EvaluationPeriods"] == 1
    assert alarm["DatapointsToAlarm"] == 1
    assert alarm["Threshold"] == 1.0
    assert alarm["ComparisonOperator"] == "GreaterThanOrEqualToThreshold"
    assert alarm["TreatMissingData"] == "notBreaching"
    assert alarm["EvaluateLowSampleCountPercentile"] == "ignore"


@mock_cloudwatch
def test_put_metric_alarm_with_anomaly_detection():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)
    alarm_name = "test-alarm"
    metrics = [
        {
            "Id": "m1",
            "ReturnData": True,
            "MetricStat": {
                "Metric": {
                    "MetricName": "CPUUtilization",
                    "Namespace": "AWS/EC2",
                    "Dimensions": [
                        {"Name": "instanceId", "Value": "i-1234567890abcdef0"}
                    ],
                },
                "Stat": "Average",
                "Period": 60,
            },
        },
        {
            "Id": "t1",
            "ReturnData": False,
            "Expression": "ANOMALY_DETECTION_BAND(m1, 3)",
        },
    ]

    # when
    client.put_metric_alarm(
        AlarmName=alarm_name,
        ActionsEnabled=True,
        Metrics=metrics,
        EvaluationPeriods=2,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        ThresholdMetricId="t1",
    )

    # then
    alarms = client.describe_alarms(AlarmNames=[alarm_name])["MetricAlarms"]
    assert len(alarms) == 1

    alarm = alarms[0]
    assert alarm["AlarmName"] == alarm_name
    assert (
        alarm["AlarmArn"]
        == f"arn:aws:cloudwatch:{region_name}:{ACCOUNT_ID}:alarm:{alarm_name}"
    )
    assert alarm["AlarmConfigurationUpdatedTimestamp"].tzinfo == tzutc()
    assert alarm["StateValue"] == "OK"
    assert alarm["StateReason"] == "Unchecked: Initial alarm creation"
    assert alarm["StateUpdatedTimestamp"].tzinfo == tzutc()
    assert alarm["EvaluationPeriods"] == 2
    assert alarm["ComparisonOperator"] == "GreaterThanOrEqualToThreshold"
    assert alarm["Metrics"] == metrics
    assert alarm["ThresholdMetricId"] == "t1"


@mock_cloudwatch
def test_put_metric_alarm_error_extended_statistic():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)
    alarm_name = "test-alarm"

    # when
    with pytest.raises(ClientError) as e:
        client.put_metric_alarm(
            AlarmName=alarm_name,
            ActionsEnabled=True,
            MetricName="5XXError",
            Namespace="AWS/ApiGateway",
            ExtendedStatistic="90",
            Dimensions=[
                {"Name": "ApiName", "Value": "test-api"},
                {"Name": "Stage", "Value": "default"},
            ],
            Period=60,
            Unit="Seconds",
            EvaluationPeriods=1,
            DatapointsToAlarm=1,
            Threshold=1.0,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
            TreatMissingData="notBreaching",
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutMetricAlarm"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterValue"
    assert (
        ex.response["Error"]["Message"]
        == "The value 90 for parameter ExtendedStatistic is not supported."
    )


@mock_cloudwatch
def test_put_metric_alarm_error_evaluate_low_sample_count_percentile():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)
    alarm_name = "test-alarm"

    # when
    with pytest.raises(ClientError) as e:
        client.put_metric_alarm(
            AlarmName=alarm_name,
            ActionsEnabled=True,
            MetricName="5XXError",
            Namespace="AWS/ApiGateway",
            ExtendedStatistic="p90",
            Dimensions=[
                {"Name": "ApiName", "Value": "test-api"},
                {"Name": "Stage", "Value": "default"},
            ],
            Period=60,
            Unit="Seconds",
            EvaluationPeriods=1,
            DatapointsToAlarm=1,
            Threshold=1.0,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
            TreatMissingData="notBreaching",
            EvaluateLowSampleCountPercentile="unknown",
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutMetricAlarm"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    err = ex.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"] == "Option unknown is not supported. "
        "Supported options for parameter EvaluateLowSampleCountPercentile are evaluate and ignore."
    )


@mock_cloudwatch
def test_get_metric_data_with_custom_label():
    utc_now = datetime.now(tz=timezone.utc)
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    namespace = "my_namespace/"

    label = "MyCustomLabel"

    # put metric data
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": "metric1",
                "Value": 50,
                "Timestamp": utc_now,
            },
            {
                "MetricName": "metric1",
                "Value": -50,
                "Timestamp": utc_now,
            },
        ],
    )
    # get_metric_data
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "result_without_custom_label",
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric1",
                    },
                    "Period": 60,
                    "Stat": "SampleCount",
                },
            },
            {
                "Id": "result_with_custom_label",
                "Label": label,
                "MetricStat": {
                    "Metric": {
                        "Namespace": namespace,
                        "MetricName": "metric1",
                    },
                    "Period": 60,
                    "Stat": "SampleCount",
                },
            },
        ],
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
    )

    expected_values = {
        "result_without_custom_label": "metric1 SampleCount",
        "result_with_custom_label": label,
    }

    for id_, expected_value in expected_values.items():
        metric_result_data = list(
            filter(
                lambda result_data: result_data["Id"] == id_,
                response["MetricDataResults"],
            )
        )
        assert len(metric_result_data) == 1
        assert metric_result_data[0]["Label"] == expected_value
