import boto3
import pytest

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("eu-west-1", "aws"), ("cn-north-1", "aws-cn")]
)
def test_create_alarm(region, partition):
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
        Namespace=f"{name}_namespace",
        MetricName=f"{name}_metric",
        OKActions=["arn:ok"],
        Period=60,
        Statistic="Average",
        Threshold=2,
        Unit="Seconds",
    )

    alarms = cloudwatch.describe_alarms()["MetricAlarms"]
    assert len(alarms) == 1
    alarm = alarms[0]
    assert alarm["AlarmName"] == "tester"
    assert alarm["Namespace"] == "tester_namespace"
    assert alarm["MetricName"] == "tester_metric"
    assert alarm["ComparisonOperator"] == "GreaterThanOrEqualToThreshold"
    assert alarm["Threshold"] == 2.0
    assert alarm["Period"] == 60
    assert alarm["EvaluationPeriods"] == 5
    assert alarm["Statistic"] == "Average"
    assert alarm["AlarmDescription"] == "A test"
    assert alarm["Dimensions"] == [{"Name": "InstanceId", "Value": "i-0123457"}]
    assert alarm["AlarmActions"] == ["arn:alarm"]
    assert alarm["OKActions"] == ["arn:ok"]
    assert alarm["InsufficientDataActions"] == ["arn:insufficient"]
    assert alarm["Unit"] == "Seconds"
    assert (
        alarm["AlarmArn"]
        == f"arn:{partition}:cloudwatch:{region}:{ACCOUNT_ID}:alarm:{name}"
    )
    # default value should be True
    assert alarm["ActionsEnabled"] is True


@mock_aws
def test_delete_alarm():
    cloudwatch = boto3.client("cloudwatch", region_name="eu-central-1")

    alarms = cloudwatch.describe_alarms()["MetricAlarms"]
    assert len(alarms) == 0

    name = "tester"
    cloudwatch.put_metric_alarm(
        AlarmActions=["arn:alarm"],
        AlarmDescription="A test",
        AlarmName=name,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        Dimensions=[{"Name": "InstanceId", "Value": "i-0123457"}],
        EvaluationPeriods=5,
        InsufficientDataActions=["arn:insufficient"],
        Namespace=f"{name}_namespace",
        MetricName=f"{name}_metric",
        OKActions=["arn:ok"],
        Period=60,
        Statistic="Average",
        Threshold=2,
        Unit="Seconds",
    )

    alarms = cloudwatch.describe_alarms()["MetricAlarms"]
    assert len(alarms) == 1

    cloudwatch.delete_alarms(AlarmNames=[name])

    alarms = cloudwatch.describe_alarms()["MetricAlarms"]
    assert len(alarms) == 0


@mock_aws
def test_delete_alarms_without_error():
    # given
    cloudwatch = boto3.client("cloudwatch", "eu-west-1")

    # when/then
    cloudwatch.delete_alarms(AlarmNames=["not-exists"])


@mock_aws
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
    assert len(alarms.get("MetricAlarms")) == 1
    alarm = alarms.get("MetricAlarms")[0]
    assert "testalarm1" in alarm.get("AlarmArn")
    assert alarm["ActionsEnabled"] is True


@mock_aws
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
        ActionsEnabled=False,
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
    assert len(metric_alarms) == 2
    single_metric_alarm = [
        alarm for alarm in metric_alarms if alarm["AlarmName"] == "testalarm1"
    ][0]
    multiple_metric_alarm = [
        alarm for alarm in metric_alarms if alarm["AlarmName"] == "testalarm2"
    ][0]

    assert single_metric_alarm["MetricName"] == "cpu"
    assert single_metric_alarm["Metrics"] == []
    assert single_metric_alarm["Namespace"] == "blah"
    assert single_metric_alarm["Period"] == 10
    assert single_metric_alarm["EvaluationPeriods"] == 5
    assert single_metric_alarm["Statistic"] == "Average"
    assert single_metric_alarm["ComparisonOperator"] == "GreaterThanThreshold"
    assert single_metric_alarm["Threshold"] == 2
    assert single_metric_alarm["ActionsEnabled"] is False

    assert "MetricName" not in multiple_metric_alarm
    assert multiple_metric_alarm["EvaluationPeriods"] == 1
    assert multiple_metric_alarm["DatapointsToAlarm"] == 1
    assert multiple_metric_alarm["Metrics"] == metric_data_queries
    assert multiple_metric_alarm["ComparisonOperator"] == "GreaterThanThreshold"
    assert multiple_metric_alarm["Threshold"] == 1.0
    assert multiple_metric_alarm["ActionsEnabled"] is True


@mock_aws
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
    assert len(resp["MetricAlarms"]) == 1
    assert resp["MetricAlarms"][0]["AlarmName"] == "testalarm1"
    assert resp["MetricAlarms"][0]["StateValue"] == "ALARM"
    assert resp["MetricAlarms"][0]["ActionsEnabled"] is True

    resp = client.describe_alarms(StateValue="OK")
    assert len(resp["MetricAlarms"]) == 1
    assert resp["MetricAlarms"][0]["AlarmName"] == "testalarm2"
    assert resp["MetricAlarms"][0]["StateValue"] == "OK"
    assert resp["MetricAlarms"][0]["ActionsEnabled"] is True

    # Just for sanity
    resp = client.describe_alarms()
    assert len(resp["MetricAlarms"]) == 2
