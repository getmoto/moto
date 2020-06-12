# from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from freezegun import freeze_time
from nose.tools import assert_raises
from uuid import uuid4
import pytz
import sure  # noqa

from moto import mock_cloudwatch


@mock_cloudwatch
def test_put_list_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    resp = client.list_dashboards()

    len(resp["DashboardEntries"]).should.equal(1)


@mock_cloudwatch
def test_put_list_prefix_nomatch_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    resp = client.list_dashboards(DashboardNamePrefix="nomatch")

    len(resp["DashboardEntries"]).should.equal(0)


@mock_cloudwatch
def test_delete_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    client.put_dashboard(DashboardName="test2", DashboardBody=widget)
    client.put_dashboard(DashboardName="test3", DashboardBody=widget)
    client.delete_dashboards(DashboardNames=["test2", "test1"])

    resp = client.list_dashboards(DashboardNamePrefix="test3")
    len(resp["DashboardEntries"]).should.equal(1)


@mock_cloudwatch
def test_delete_dashboard_fail():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    client.put_dashboard(DashboardName="test2", DashboardBody=widget)
    client.put_dashboard(DashboardName="test3", DashboardBody=widget)
    # Doesnt delete anything if all dashboards to be deleted do not exist
    try:
        client.delete_dashboards(DashboardNames=["test2", "test1", "test_no_match"])
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFound")
    else:
        raise RuntimeError("Should of raised error")

    resp = client.list_dashboards()
    len(resp["DashboardEntries"]).should.equal(3)


@mock_cloudwatch
def test_get_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'
    client.put_dashboard(DashboardName="test1", DashboardBody=widget)

    resp = client.get_dashboard(DashboardName="test1")
    resp.should.contain("DashboardArn")
    resp.should.contain("DashboardBody")
    resp["DashboardName"].should.equal("test1")


@mock_cloudwatch
def test_get_dashboard_fail():
    client = boto3.client("cloudwatch", region_name="eu-central-1")

    try:
        client.get_dashboard(DashboardName="test1")
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFound")
    else:
        raise RuntimeError("Should of raised error")


@mock_cloudwatch
def test_delete_invalid_alarm():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    cloudwatch.put_metric_alarm(
        AlarmName="testalarm1",
        MetricName="cpu",
        Namespace="blah",
        Period=10,
        EvaluationPeriods=5,
        Statistic="Average",
        Threshold=2,
        ComparisonOperator="GreaterThanThreshold",
        ActionsEnabled=True,
    )

    # trying to delete an alarm which is not created along with valid alarm.
    with assert_raises(ClientError) as e:
        cloudwatch.delete_alarms(AlarmNames=["InvalidAlarmName", "testalarm1"])
    e.exception.response["Error"]["Code"].should.equal("ResourceNotFound")

    resp = cloudwatch.describe_alarms(AlarmNames=["testalarm1"])
    # making sure other alarms are not deleted in case of an error.
    len(resp["MetricAlarms"]).should.equal(1)

    # test to check if the error raises if only one invalid alarm is tried to delete.
    with assert_raises(ClientError) as e:
        cloudwatch.delete_alarms(AlarmNames=["InvalidAlarmName"])
    e.exception.response["Error"]["Code"].should.equal("ResourceNotFound")


@mock_cloudwatch
def test_alarm_state():
    client = boto3.client("cloudwatch", region_name="eu-central-1")

    client.put_metric_alarm(
        AlarmName="testalarm1",
        MetricName="cpu",
        Namespace="blah",
        Period=10,
        EvaluationPeriods=5,
        Statistic="Average",
        Threshold=2,
        ComparisonOperator="GreaterThanThreshold",
        ActionsEnabled=True,
    )
    client.put_metric_alarm(
        AlarmName="testalarm2",
        MetricName="cpu",
        Namespace="blah",
        Period=10,
        EvaluationPeriods=5,
        Statistic="Average",
        Threshold=2,
        ComparisonOperator="GreaterThanThreshold",
    )

    # This is tested implicitly as if it doesnt work the rest will die
    client.set_alarm_state(
        AlarmName="testalarm1",
        StateValue="ALARM",
        StateReason="testreason",
        StateReasonData='{"some": "json_data"}',
    )

    resp = client.describe_alarms(StateValue="ALARM")
    len(resp["MetricAlarms"]).should.equal(1)
    resp["MetricAlarms"][0]["AlarmName"].should.equal("testalarm1")
    resp["MetricAlarms"][0]["StateValue"].should.equal("ALARM")
    resp["MetricAlarms"][0]["ActionsEnabled"].should.equal(True)

    resp = client.describe_alarms(StateValue="OK")
    len(resp["MetricAlarms"]).should.equal(1)
    resp["MetricAlarms"][0]["AlarmName"].should.equal("testalarm2")
    resp["MetricAlarms"][0]["StateValue"].should.equal("OK")
    resp["MetricAlarms"][0]["ActionsEnabled"].should.equal(False)

    # Just for sanity
    resp = client.describe_alarms()
    len(resp["MetricAlarms"]).should.equal(2)


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

    stats = cw.get_metric_statistics(
        Namespace="tester",
        MetricName="metric",
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
        Period=60,
        Statistics=["SampleCount", "Sum"],
    )


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
            {
                u"Namespace": "list_test_1/",
                u"Dimensions": [],
                u"MetricName": "metric1",
            },
            {
                u"Namespace": "list_test_1/",
                u"Dimensions": [],
                u"MetricName": "metric1",
            },
        ]
    )
    # Verify unknown namespace still has no results
    res = cloudwatch.list_metrics(Namespace="unknown/")["Metrics"]
    res.should.be.empty


@mock_cloudwatch
def test_list_metrics_paginated():
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")
    # Verify that only a single page of metrics is returned
    cloudwatch.list_metrics()["Metrics"].should.be.empty
    # Verify we can't pass a random NextToken
    with assert_raises(ClientError) as e:
        cloudwatch.list_metrics(NextToken=str(uuid4()))
    e.exception.response["Error"]["Message"].should.equal(
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
    with assert_raises(ClientError) as e:
        cloudwatch.list_metrics(NextToken=first_page["NextToken"])
    e.exception.response["Error"]["Message"].should.equal(
        "Request parameter NextToken is invalid"
    )


def create_metrics(cloudwatch, namespace, metrics=5, data_points=5):
    for i in range(0, metrics):
        metric_name = "metric" + str(i)
        for j in range(0, data_points):
            cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=[{"MetricName": metric_name, "Value": j, "Unit": "Seconds"}],
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
    values = [0, 2, 4, 3.5, 7, 100]
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
        StartTime=yesterday - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
    )
    #
    # Assert Last week's data is not returned
    len(response["MetricDataResults"]).should.equal(1)
    sum_ = response["MetricDataResults"][0]
    sum_["Label"].should.equal("metric1 Sum")
    sum_["StatusCode"].should.equal("Complete")
    sum_["Values"].should.equal([30.0])


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
