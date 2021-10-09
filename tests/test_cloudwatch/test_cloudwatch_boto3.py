from datetime import datetime, timedelta
from operator import itemgetter

import boto3
from botocore.exceptions import ClientError
from dateutil.tz import tzutc
from freezegun import freeze_time
import pytest
from uuid import uuid4
import pytz
import sure  # noqa

from moto import mock_cloudwatch
from moto.cloudwatch.utils import make_arn_for_alarm
from moto.core import ACCOUNT_ID


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
        raise RuntimeError("Should have raised error")


@mock_cloudwatch
def test_create_alarm():
    region = "eu-west-1"
    cloudwatch = boto3.client("cloudwatch", region)

    name = "tester"
    cloudwatch.put_metric_alarm(
        AlarmActions=["arn:alarm"],
        AlarmDescription="A test",
        AlarmName=name,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        Dimensions=[{"Name": "InstanceId", "Value": "i-0123457"}],
        EvaluationPeriods=5,
        InsufficientDataActions=["arn:insufficient"],
        Namespace="{0}_namespace".format(name),
        MetricName="{0}_metric".format(name),
        OKActions=["arn:ok"],
        Period=60,
        Statistic="Average",
        Threshold=2,
        Unit="Seconds",
    )

    alarms = cloudwatch.describe_alarms()["MetricAlarms"]
    alarms.should.have.length_of(1)
    alarm = alarms[0]
    alarm.should.have.key("AlarmName").equal("tester")
    alarm.should.have.key("Namespace").equal("tester_namespace")
    alarm.should.have.key("MetricName").equal("tester_metric")
    alarm.should.have.key("ComparisonOperator").equal("GreaterThanOrEqualToThreshold")
    alarm.should.have.key("Threshold").equal(2.0)
    alarm.should.have.key("Period").equal(60)
    alarm.should.have.key("EvaluationPeriods").equal(5)
    alarm.should.have.key("Statistic").should.equal("Average")
    alarm.should.have.key("AlarmDescription").equal("A test")
    alarm.should.have.key("Dimensions").equal(
        [{"Name": "InstanceId", "Value": "i-0123457"}]
    )
    alarm.should.have.key("AlarmActions").equal(["arn:alarm"])
    alarm.should.have.key("OKActions").equal(["arn:ok"])
    alarm.should.have.key("InsufficientDataActions").equal(["arn:insufficient"])
    alarm.should.have.key("Unit").equal("Seconds")
    alarm.should.have.key("AlarmArn").equal(
        "arn:aws:cloudwatch:{}:{}:alarm:{}".format(region, ACCOUNT_ID, name)
    )


@mock_cloudwatch
def test_delete_alarm():
    cloudwatch = boto3.client("cloudwatch", region_name="eu-central-1")

    alarms = cloudwatch.describe_alarms()["MetricAlarms"]
    alarms.should.have.length_of(0)

    name = "tester"
    cloudwatch.put_metric_alarm(
        AlarmActions=["arn:alarm"],
        AlarmDescription="A test",
        AlarmName=name,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        Dimensions=[{"Name": "InstanceId", "Value": "i-0123457"}],
        EvaluationPeriods=5,
        InsufficientDataActions=["arn:insufficient"],
        Namespace="{0}_namespace".format(name),
        MetricName="{0}_metric".format(name),
        OKActions=["arn:ok"],
        Period=60,
        Statistic="Average",
        Threshold=2,
        Unit="Seconds",
    )

    alarms = cloudwatch.describe_alarms()["MetricAlarms"]
    alarms.should.have.length_of(1)

    cloudwatch.delete_alarms(AlarmNames=[name])

    alarms = cloudwatch.describe_alarms()["MetricAlarms"]
    alarms.should.have.length_of(0)


@mock_cloudwatch
def test_delete_alarms_without_error():
    # given
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    # when/then
    cloudwatch.delete_alarms(AlarmNames=["not-exists"])


@mock_cloudwatch
def test_describe_alarms_for_metric():
    conn = boto3.client("cloudwatch", region_name="eu-central-1")
    conn.put_metric_alarm(
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
    alarms = conn.describe_alarms_for_metric(MetricName="cpu", Namespace="blah")
    alarms.get("MetricAlarms").should.have.length_of(1)

    assert "testalarm1" in alarms.get("MetricAlarms")[0].get("AlarmArn")


@mock_cloudwatch
def test_describe_alarms():
    conn = boto3.client("cloudwatch", region_name="eu-central-1")
    conn.put_metric_alarm(
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
    metric_data_queries = [
        {
            "Id": "metricA",
            "Expression": "metricB + metricC",
            "Label": "metricA",
            "ReturnData": True,
        },
        {
            "Id": "metricB",
            "MetricStat": {
                "Metric": {
                    "Namespace": "ns",
                    "MetricName": "metricB",
                    "Dimensions": [{"Name": "Name", "Value": "B"}],
                },
                "Period": 60,
                "Stat": "Sum",
            },
            "ReturnData": False,
        },
        {
            "Id": "metricC",
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/Lambda",
                    "MetricName": "metricC",
                    "Dimensions": [{"Name": "Name", "Value": "C"}],
                },
                "Period": 60,
                "Stat": "Sum",
                "Unit": "Seconds",
            },
            "ReturnData": False,
        },
    ]
    conn.put_metric_alarm(
        AlarmName="testalarm2",
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Metrics=metric_data_queries,
        ComparisonOperator="GreaterThanThreshold",
        Threshold=1.0,
    )
    alarms = conn.describe_alarms()
    metric_alarms = alarms.get("MetricAlarms")
    metric_alarms.should.have.length_of(2)
    single_metric_alarm = [
        alarm for alarm in metric_alarms if alarm["AlarmName"] == "testalarm1"
    ][0]
    multiple_metric_alarm = [
        alarm for alarm in metric_alarms if alarm["AlarmName"] == "testalarm2"
    ][0]

    single_metric_alarm["MetricName"].should.equal("cpu")
    single_metric_alarm.shouldnt.have.property("Metrics")
    single_metric_alarm["Namespace"].should.equal("blah")
    single_metric_alarm["Period"].should.equal(10)
    single_metric_alarm["EvaluationPeriods"].should.equal(5)
    single_metric_alarm["Statistic"].should.equal("Average")
    single_metric_alarm["ComparisonOperator"].should.equal("GreaterThanThreshold")
    single_metric_alarm["Threshold"].should.equal(2)

    multiple_metric_alarm.shouldnt.have.property("MetricName")
    multiple_metric_alarm["EvaluationPeriods"].should.equal(1)
    multiple_metric_alarm["DatapointsToAlarm"].should.equal(1)
    multiple_metric_alarm["Metrics"].should.equal(metric_data_queries)
    multiple_metric_alarm["ComparisonOperator"].should.equal("GreaterThanThreshold")
    multiple_metric_alarm["Threshold"].should.equal(1.0)


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
    cloudwatch.list_metrics()["Metrics"].should.be.empty
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


@mock_cloudwatch
def test_list_tags_for_resource():
    # given
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    alarm_name = "test-alarm"
    client.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription="test alarm",
        ActionsEnabled=True,
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
        Tags=[{"Key": "key-1", "Value": "value-1"}],
    )
    arn = client.describe_alarms(AlarmNames=[alarm_name])["MetricAlarms"][0]["AlarmArn"]

    # when
    response = client.list_tags_for_resource(ResourceARN=arn)

    # then
    response["Tags"].should.equal([{"Key": "key-1", "Value": "value-1"}])


@mock_cloudwatch
def test_list_tags_for_resource_with_unknown_resource():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)

    # when
    response = client.list_tags_for_resource(
        ResourceARN=make_arn_for_alarm(
            region=region_name, account_id=ACCOUNT_ID, alarm_name="unknown"
        )
    )

    # then
    response["Tags"].should.be.empty


@mock_cloudwatch
def test_tag_resource():
    # given
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    alarm_name = "test-alarm"
    client.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription="test alarm",
        ActionsEnabled=True,
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
        Tags=[{"Key": "key-1", "Value": "value-1"}],
    )
    arn = client.describe_alarms(AlarmNames=[alarm_name])["MetricAlarms"][0]["AlarmArn"]

    # when
    client.tag_resource(ResourceARN=arn, Tags=[{"Key": "key-2", "Value": "value-2"}])

    # then
    response = client.list_tags_for_resource(ResourceARN=arn)
    sorted(response["Tags"], key=itemgetter("Key")).should.equal(
        sorted(
            [
                {"Key": "key-1", "Value": "value-1"},
                {"Key": "key-2", "Value": "value-2"},
            ],
            key=itemgetter("Key"),
        )
    )


@mock_cloudwatch
def test_tag_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.tag_resource(
            ResourceARN=make_arn_for_alarm(
                region=region_name, account_id=ACCOUNT_ID, alarm_name="unknown"
            ),
            Tags=[{"Key": "key-1", "Value": "value-1"},],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("TagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal("Unknown")


@mock_cloudwatch
def test_untag_resource():
    # given
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    alarm_name = "test-alarm"
    client.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription="test alarm",
        ActionsEnabled=True,
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
        Tags=[
            {"Key": "key-1", "Value": "value-1"},
            {"Key": "key-2", "Value": "value-2"},
        ],
    )
    arn = client.describe_alarms(AlarmNames=[alarm_name])["MetricAlarms"][0]["AlarmArn"]

    # when
    client.untag_resource(ResourceARN=arn, TagKeys=["key-2"])

    # then
    response = client.list_tags_for_resource(ResourceARN=arn)
    response["Tags"].should.equal([{"Key": "key-1", "Value": "value-1"}])


@mock_cloudwatch
def test_untag_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("cloudwatch", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.untag_resource(
            ResourceARN=make_arn_for_alarm(
                region=region_name, account_id=ACCOUNT_ID, alarm_name="unknown"
            ),
            TagKeys=["key-1"],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("UntagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal("Unknown")
