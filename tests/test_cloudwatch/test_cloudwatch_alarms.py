import boto3
import sure  # noqa

from moto import mock_cloudwatch
from moto.core import ACCOUNT_ID


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
