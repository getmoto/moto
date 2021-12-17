import boto3
import pytest
import pytz
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from dateutil.tz import tzutc
from decimal import Decimal
from freezegun import freeze_time
from operator import itemgetter
from uuid import uuid4

from moto import mock_cloudwatch, mock_s3
from moto.core import ACCOUNT_ID


@mock_cloudwatch
def test_put_metric_data_no_dimensions():
    conn = boto3.client("cloudwatch", region_name="us-east-1")

    conn.put_metric_data(
        Namespace="tester", MetricData=[dict(MetricName="metric", Value=1.5)]
    )

    metrics = conn.list_metrics()["Metrics"]
    metrics.should.have.length_of(1)
    metric = metrics[0]
    metric["Namespace"].should.equal("tester")
    metric["MetricName"].should.equal("metric")


@mock_cloudwatch
def test_put_metric_data_can_not_have_nan():
    client = boto3.client("cloudwatch", region_name="us-west-2")
    utc_now = datetime.now(tz=pytz.utc)
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The value NaN for parameter MetricData.member.1.Value is invalid."
    )


@mock_cloudwatch
def test_put_metric_data_with_statistics():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=pytz.utc)

    conn.put_metric_data(
        Namespace="tester",
        MetricData=[
            dict(
                MetricName="statmetric",
                Timestamp=utc_now,
                # no Value to test  https://github.com/spulec/moto/issues/1615
                StatisticValues=dict(
                    SampleCount=123.0, Sum=123.0, Minimum=123.0, Maximum=123.0
                ),
                Unit="Milliseconds",
                StorageResolution=123,
            )
        ],
    )

    metrics = conn.list_metrics()["Metrics"]
    metrics.should.have.length_of(1)
    metric = metrics[0]
    metric["Namespace"].should.equal("tester")
    metric["MetricName"].should.equal("statmetric")
    # TODO: test statistics - https://github.com/spulec/moto/issues/1615


@mock_cloudwatch
def test_get_metric_statistics():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=pytz.utc)

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

    stats["Datapoints"].should.have.length_of(1)
    datapoint = stats["Datapoints"][0]
    datapoint["SampleCount"].should.equal(1.0)
    datapoint["Sum"].should.equal(1.5)


@mock_cloudwatch
def test_get_metric_statistics_dimensions():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=pytz.utc)

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
        print(stats)
        stats["Datapoints"].should.have.length_of(1)
        datapoint = stats["Datapoints"][0]
        datapoint["Sum"].should.equal(params[1])
        datapoint["Average"].should.equal(params[2])


@mock_cloudwatch
def test_duplicate_put_metric_data():
    conn = boto3.client("cloudwatch", region_name="us-east-1")
    utc_now = datetime.now(tz=pytz.utc)

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
    len(result).should.equal(1)

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
    len(result).should.equal(1)
    result.should.equal(
        [
            {
                "Namespace": "tester",
                "MetricName": "metric",
                "Dimensions": [{"Name": "Name", "Value": "B"}],
            }
        ]
    )

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
    result.should.equal(
        [
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
    )

    result = conn.list_metrics(
        Namespace="tester", Dimensions=[{"Name": "Name", "Value": "C"}]
    )["Metrics"]
    result.should.equal(
        [
            {
                "Namespace": "tester",
                "MetricName": "metric",
                "Dimensions": [
                    {"Name": "Name", "Value": "B"},
                    {"Name": "Name", "Value": "C"},
                ],
            }
        ]
    )


@mock_cloudwatch
@freeze_time("2020-02-10 18:44:05")
def test_custom_timestamp():
    utc_now = datetime.now(tz=pytz.utc)
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

    cw.get_metric_statistics(
        Namespace="tester",
        MetricName="metric",
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
        Period=60,
        Statistics=["SampleCount", "Sum"],
    )
    # TODO: What are we actually testing here?


@mock_cloudwatch
def test_list_metrics():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    # Verify namespace has to exist
    res = cloudwatch.list_metrics(Namespace="unknown/")["Metrics"]
    res.should.be.empty
    # Create some metrics to filter on
    create_metrics(cloudwatch, namespace="list_test_1/", metrics=4, data_points=2)
    create_metrics(cloudwatch, namespace="list_test_2/", metrics=4, data_points=2)
    # Verify we can retrieve everything
    res = cloudwatch.list_metrics()["Metrics"]
    len(res).should.equal(16)  # 2 namespaces * 4 metrics * 2 data points
    # Verify we can filter by namespace/metric name
    res = cloudwatch.list_metrics(Namespace="list_test_1/")["Metrics"]
    len(res).should.equal(8)  # 1 namespace * 4 metrics * 2 data points
    res = cloudwatch.list_metrics(Namespace="list_test_1/", MetricName="metric1")[
        "Metrics"
    ]
    len(res).should.equal(2)  # 1 namespace * 1 metrics * 2 data points
    # Verify format
    res.should.equal(
        [
            {"Namespace": "list_test_1/", "Dimensions": [], "MetricName": "metric1",},
            {"Namespace": "list_test_1/", "Dimensions": [], "MetricName": "metric1",},
        ]
    )
    # Verify unknown namespace still has no results
    res = cloudwatch.list_metrics(Namespace="unknown/")["Metrics"]
    res.should.be.empty


@mock_cloudwatch
def test_list_metrics_paginated():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    # Verify that only a single page of metrics is returned
    cloudwatch.list_metrics().shouldnt.have.key("NextToken")
    # Verify we can't pass a random NextToken
    with pytest.raises(ClientError) as e:
        cloudwatch.list_metrics(NextToken=str(uuid4()))
    e.value.response["Error"]["Message"].should.equal(
        "Request parameter NextToken is invalid"
    )
    # Add a boatload of metrics
    create_metrics(cloudwatch, namespace="test", metrics=100, data_points=1)
    # Verify that a single page is returned until we've reached 500
    first_page = cloudwatch.list_metrics()
    first_page["Metrics"].shouldnt.be.empty
    len(first_page["Metrics"]).should.equal(100)
    create_metrics(cloudwatch, namespace="test", metrics=200, data_points=2)
    first_page = cloudwatch.list_metrics()
    len(first_page["Metrics"]).should.equal(500)
    first_page.shouldnt.contain("NextToken")
    # Verify that adding more data points results in pagination
    create_metrics(cloudwatch, namespace="test", metrics=60, data_points=10)
    first_page = cloudwatch.list_metrics()
    len(first_page["Metrics"]).should.equal(500)
    first_page["NextToken"].shouldnt.be.empty
    # Retrieve second page - and verify there's more where that came from
    second_page = cloudwatch.list_metrics(NextToken=first_page["NextToken"])
    len(second_page["Metrics"]).should.equal(500)
    second_page.should.contain("NextToken")
    # Last page should only have the last 100 results, and no NextToken (indicating that pagination is finished)
    third_page = cloudwatch.list_metrics(NextToken=second_page["NextToken"])
    len(third_page["Metrics"]).should.equal(100)
    third_page.shouldnt.contain("NextToken")
    # Verify that we can't reuse an existing token
    with pytest.raises(ClientError) as e:
        cloudwatch.list_metrics(NextToken=first_page["NextToken"])
    e.value.response["Error"]["Message"].should.equal(
        "Request parameter NextToken is invalid"
    )


@mock_cloudwatch
def test_list_metrics_without_value():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    # Create some metrics to filter on
    create_metrics_with_dimensions(cloudwatch, namespace="MyNamespace", data_points=3)
    # Verify we can filter by namespace/metric name
    res = cloudwatch.list_metrics(Namespace="MyNamespace")["Metrics"]
    res.should.have.length_of(3)
    # Verify we can filter by Dimension without value
    results = cloudwatch.list_metrics(
        Namespace="MyNamespace", MetricName="MyMetric", Dimensions=[{"Name": "D1"}]
    )["Metrics"]

    results.should.have.length_of(1)
    results[0]["Namespace"].should.equals("MyNamespace")
    results[0]["MetricName"].should.equal("MyMetric")
    results[0]["Dimensions"].should.equal([{"Name": "D1", "Value": "V1"}])


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
def test_get_metric_data_within_timeframe():
    utc_now = datetime.now(tz=pytz.utc)
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
    avg["Label"].should.equal("metric1 Average")
    avg["StatusCode"].should.equal("Complete")
    [int(val) for val in avg["Values"]].should.equal([19])

    sum_ = [res for res in response["MetricDataResults"] if res["Id"] == "result_Sum"][
        0
    ]
    sum_["Label"].should.equal("metric1 Sum")
    sum_["StatusCode"].should.equal("Complete")
    [val for val in sum_["Values"]].should.equal([sum(values)])

    min_ = [
        res for res in response["MetricDataResults"] if res["Id"] == "result_Minimum"
    ][0]
    min_["Label"].should.equal("metric1 Minimum")
    min_["StatusCode"].should.equal("Complete")
    [int(val) for val in min_["Values"]].should.equal([0])

    max_ = [
        res for res in response["MetricDataResults"] if res["Id"] == "result_Maximum"
    ][0]
    max_["Label"].should.equal("metric1 Maximum")
    max_["StatusCode"].should.equal("Complete")
    [int(val) for val in max_["Values"]].should.equal([100])


@mock_cloudwatch
def test_get_metric_data_partially_within_timeframe():
    utc_now = datetime.now(tz=pytz.utc)
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
        start=yesterday - timedelta(seconds=60), end=utc_now + timedelta(seconds=60),
    )

    # Assert Last week's data is not returned
    len(response["MetricDataResults"]).should.equal(1)
    sum_ = response["MetricDataResults"][0]
    sum_["Label"].should.equal("metric1 Sum")
    sum_["StatusCode"].should.equal("Complete")
    sum_["Values"].should.equal([20.0, 10.0])
    response = get_data(
        start=yesterday - timedelta(seconds=60),
        end=utc_now + timedelta(seconds=60),
        scanBy="TimestampDescending",
    )
    response["MetricDataResults"][0]["Values"].should.equal([10.0, 20.0])

    response = get_data(
        start=last_week - timedelta(seconds=1),
        end=utc_now + timedelta(seconds=60),
        stat="Average",
    )
    # assert average
    response["MetricDataResults"][0]["Values"].should.equal([30.0, 20.0, 10.0])

    response = get_data(
        start=last_week - timedelta(seconds=1),
        end=utc_now + timedelta(seconds=60),
        stat="Maximum",
    )
    # assert maximum
    response["MetricDataResults"][0]["Values"].should.equal([50.0, 20.0, 10.0])

    response = get_data(
        start=last_week - timedelta(seconds=1),
        end=utc_now + timedelta(seconds=60),
        stat="Minimum",
    )
    # assert minimum
    response["MetricDataResults"][0]["Values"].should.equal([10.0, 20.0, 10.0])


@mock_cloudwatch
def test_get_metric_data_outside_timeframe():
    utc_now = datetime.now(tz=pytz.utc)
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
    len(response["MetricDataResults"]).should.equal(1)
    response["MetricDataResults"][0]["Id"].should.equal("result")
    response["MetricDataResults"][0]["StatusCode"].should.equal("Complete")
    response["MetricDataResults"][0]["Values"].should.equal([])


@mock_cloudwatch
def test_get_metric_data_for_multiple_metrics():
    utc_now = datetime.now(tz=pytz.utc)
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
    len(response["MetricDataResults"]).should.equal(2)

    res1 = [res for res in response["MetricDataResults"] if res["Id"] == "result1"][0]
    res1["Values"].should.equal([50.0])

    res2 = [res for res in response["MetricDataResults"] if res["Id"] == "result2"][0]
    res2["Values"].should.equal([25.0])


@mock_cloudwatch
@mock_s3
def test_cloudwatch_return_s3_metrics():
    utc_now = datetime.now(tz=pytz.utc)
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
    metrics.should.have.length_of(2)
    metrics.should.contain(
        {
            "Namespace": "AWS/S3",
            "MetricName": "NumberOfObjects",
            "Dimensions": [
                {"Name": "StorageType", "Value": "AllStorageTypes"},
                {"Name": "BucketName", "Value": bucket_name},
            ],
        }
    )
    metrics.should.contain(
        {
            "Namespace": "AWS/S3",
            "MetricName": "BucketSizeBytes",
            "Dimensions": [
                {"Name": "StorageType", "Value": "StandardStorage"},
                {"Name": "BucketName", "Value": bucket_name},
            ],
        }
    )

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
    stats.should.have.key("Label").equal("BucketSizeBytes")
    stats.should.have.key("Datapoints").length_of(1)
    data_point = stats["Datapoints"][0]
    data_point.should.have.key("Average").being.above(0)
    data_point.should.have.key("Unit").being.equal("Bytes")

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
    stats.should.have.key("Label").equal("NumberOfObjects")
    stats.should.have.key("Datapoints").length_of(1)
    data_point = stats["Datapoints"][0]
    data_point.should.have.key("Average").being.equal(1)
    data_point.should.have.key("Unit").being.equal("Count")

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
    alarms.should.have.length_of(1)

    alarm = alarms[0]
    alarm["AlarmName"].should.equal(alarm_name)
    alarm["AlarmArn"].should.equal(
        f"arn:aws:cloudwatch:{region_name}:{ACCOUNT_ID}:alarm:{alarm_name}"
    )
    alarm["AlarmDescription"].should.equal("test alarm")
    alarm["AlarmConfigurationUpdatedTimestamp"].should.be.a(datetime)
    alarm["AlarmConfigurationUpdatedTimestamp"].tzinfo.should.equal(tzutc())
    alarm["ActionsEnabled"].should.be.ok
    alarm["OKActions"].should.equal([sns_topic_arn])
    alarm["AlarmActions"].should.equal([sns_topic_arn])
    alarm["InsufficientDataActions"].should.equal([sns_topic_arn])
    alarm["StateValue"].should.equal("OK")
    alarm["StateReason"].should.equal("Unchecked: Initial alarm creation")
    alarm["StateUpdatedTimestamp"].should.be.a(datetime)
    alarm["StateUpdatedTimestamp"].tzinfo.should.equal(tzutc())
    alarm["MetricName"].should.equal("5XXError")
    alarm["Namespace"].should.equal("AWS/ApiGateway")
    alarm["Statistic"].should.equal("Sum")
    sorted(alarm["Dimensions"], key=itemgetter("Name")).should.equal(
        sorted(
            [
                {"Name": "ApiName", "Value": "test-api"},
                {"Name": "Stage", "Value": "default"},
            ],
            key=itemgetter("Name"),
        )
    )
    alarm["Period"].should.equal(60)
    alarm["Unit"].should.equal("Seconds")
    alarm["EvaluationPeriods"].should.equal(1)
    alarm["DatapointsToAlarm"].should.equal(1)
    alarm["Threshold"].should.equal(1.0)
    alarm["ComparisonOperator"].should.equal("GreaterThanOrEqualToThreshold")
    alarm["TreatMissingData"].should.equal("notBreaching")


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
    alarms.should.have.length_of(1)

    alarm = alarms[0]
    alarm["AlarmName"].should.equal(alarm_name)
    alarm["AlarmArn"].should.equal(
        f"arn:aws:cloudwatch:{region_name}:{ACCOUNT_ID}:alarm:{alarm_name}"
    )
    alarm["AlarmDescription"].should.equal("test alarm")
    alarm["AlarmConfigurationUpdatedTimestamp"].should.be.a(datetime)
    alarm["AlarmConfigurationUpdatedTimestamp"].tzinfo.should.equal(tzutc())
    alarm["ActionsEnabled"].should.be.ok
    alarm["StateValue"].should.equal("OK")
    alarm["StateReason"].should.equal("Unchecked: Initial alarm creation")
    alarm["StateUpdatedTimestamp"].should.be.a(datetime)
    alarm["StateUpdatedTimestamp"].tzinfo.should.equal(tzutc())
    alarm["MetricName"].should.equal("5XXError")
    alarm["Namespace"].should.equal("AWS/ApiGateway")
    alarm["ExtendedStatistic"].should.equal("p90")
    sorted(alarm["Dimensions"], key=itemgetter("Name")).should.equal(
        sorted(
            [
                {"Name": "ApiName", "Value": "test-api"},
                {"Name": "Stage", "Value": "default"},
            ],
            key=itemgetter("Name"),
        )
    )
    alarm["Period"].should.equal(60)
    alarm["Unit"].should.equal("Seconds")
    alarm["EvaluationPeriods"].should.equal(1)
    alarm["DatapointsToAlarm"].should.equal(1)
    alarm["Threshold"].should.equal(1.0)
    alarm["ComparisonOperator"].should.equal("GreaterThanOrEqualToThreshold")
    alarm["TreatMissingData"].should.equal("notBreaching")
    alarm["EvaluateLowSampleCountPercentile"].should.equal("ignore")


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
    alarms.should.have.length_of(1)

    alarm = alarms[0]
    alarm["AlarmName"].should.equal(alarm_name)
    alarm["AlarmArn"].should.equal(
        f"arn:aws:cloudwatch:{region_name}:{ACCOUNT_ID}:alarm:{alarm_name}"
    )
    alarm["AlarmConfigurationUpdatedTimestamp"].should.be.a(datetime)
    alarm["AlarmConfigurationUpdatedTimestamp"].tzinfo.should.equal(tzutc())
    alarm["StateValue"].should.equal("OK")
    alarm["StateReason"].should.equal("Unchecked: Initial alarm creation")
    alarm["StateUpdatedTimestamp"].should.be.a(datetime)
    alarm["StateUpdatedTimestamp"].tzinfo.should.equal(tzutc())
    alarm["EvaluationPeriods"].should.equal(2)
    alarm["ComparisonOperator"].should.equal("GreaterThanOrEqualToThreshold")
    alarm["Metrics"].should.equal(metrics)
    alarm["ThresholdMetricId"].should.equal("t1")


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
    ex.operation_name.should.equal("PutMetricAlarm")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterValue")
    ex.response["Error"]["Message"].should.equal(
        "The value 90 for parameter ExtendedStatistic is not supported."
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
    ex.operation_name.should.equal("PutMetricAlarm")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationError")
    ex.response["Error"]["Message"].should.equal(
        "Option unknown is not supported. "
        "Supported options for parameter EvaluateLowSampleCountPercentile are evaluate and ignore."
    )
