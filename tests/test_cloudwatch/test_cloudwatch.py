import boto
from boto.ec2.cloudwatch.alarm import MetricAlarm
from boto.s3.key import Key
from datetime import datetime
import sure  # noqa
from moto.cloudwatch.utils import make_arn_for_alarm
from moto.core import ACCOUNT_ID

from moto import mock_cloudwatch_deprecated, mock_s3_deprecated


def alarm_fixture(name="tester", action=None):
    action = action or ["arn:alarm"]
    return MetricAlarm(
        name=name,
        namespace="{0}_namespace".format(name),
        metric="{0}_metric".format(name),
        comparison=">=",
        threshold=2.0,
        period=60,
        evaluation_periods=5,
        statistic="Average",
        description="A test",
        dimensions={"InstanceId": ["i-0123456,i-0123457"]},
        alarm_actions=action,
        ok_actions=["arn:ok"],
        insufficient_data_actions=["arn:insufficient"],
        unit="Seconds",
    )


# Has boto3 equivalent
@mock_cloudwatch_deprecated
def test_create_alarm():
    conn = boto.connect_cloudwatch()

    alarm = alarm_fixture()
    conn.create_alarm(alarm)

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(1)
    alarm = alarms[0]
    alarm.name.should.equal("tester")
    alarm.namespace.should.equal("tester_namespace")
    alarm.metric.should.equal("tester_metric")
    alarm.comparison.should.equal(">=")
    alarm.threshold.should.equal(2.0)
    alarm.period.should.equal(60)
    alarm.evaluation_periods.should.equal(5)
    alarm.statistic.should.equal("Average")
    alarm.description.should.equal("A test")
    dict(alarm.dimensions).should.equal({"InstanceId": ["i-0123456,i-0123457"]})
    list(alarm.alarm_actions).should.equal(["arn:alarm"])
    list(alarm.ok_actions).should.equal(["arn:ok"])
    list(alarm.insufficient_data_actions).should.equal(["arn:insufficient"])
    alarm.unit.should.equal("Seconds")
    assert "tester" in alarm.alarm_arn


# Has boto3 equivalent
@mock_cloudwatch_deprecated
def test_delete_alarm():
    conn = boto.connect_cloudwatch()

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(0)

    alarm = alarm_fixture()
    conn.create_alarm(alarm)

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(1)

    alarms[0].delete()

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(0)


# Has boto3 equivalent
@mock_cloudwatch_deprecated
def test_put_metric_data():
    conn = boto.connect_cloudwatch()

    conn.put_metric_data(
        namespace="tester",
        name="metric",
        value=1.5,
        dimensions={"InstanceId": ["i-0123456,i-0123457"]},
    )

    metrics = conn.list_metrics()
    metric_names = [m for m in metrics if m.name == "metric"]
    metric_names.should.have(1)
    metric = metrics[0]
    metric.namespace.should.equal("tester")
    metric.name.should.equal("metric")
    dict(metric.dimensions).should.equal({"InstanceId": ["i-0123456,i-0123457"]})


# Has boto3 equivalent
@mock_cloudwatch_deprecated
def test_describe_alarms():
    conn = boto.connect_cloudwatch()

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(0)

    conn.create_alarm(alarm_fixture(name="nfoobar", action="afoobar"))
    conn.create_alarm(alarm_fixture(name="nfoobaz", action="afoobaz"))
    conn.create_alarm(alarm_fixture(name="nbarfoo", action="abarfoo"))
    conn.create_alarm(alarm_fixture(name="nbazfoo", action="abazfoo"))

    enabled = alarm_fixture(name="enabled1", action=["abarfoo"])
    enabled.add_alarm_action("arn:alarm")
    conn.create_alarm(enabled)

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(5)
    alarms = conn.describe_alarms(alarm_name_prefix="nfoo")
    alarms.should.have.length_of(2)
    alarms = conn.describe_alarms(alarm_names=["nfoobar", "nbarfoo", "nbazfoo"])
    alarms.should.have.length_of(3)
    alarms = conn.describe_alarms(action_prefix="afoo")
    alarms.should.have.length_of(2)
    alarms = conn.describe_alarms(alarm_name_prefix="enabled")
    alarms.should.have.length_of(1)
    alarms[0].actions_enabled.should.equal("true")

    for alarm in conn.describe_alarms():
        alarm.delete()

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(0)


# Has boto3 equivalent
@mock_cloudwatch_deprecated
def test_describe_alarms_for_metric():
    conn = boto.connect_cloudwatch()

    conn.create_alarm(alarm_fixture(name="nfoobar", action="afoobar"))
    conn.create_alarm(alarm_fixture(name="nfoobaz", action="afoobaz"))
    conn.create_alarm(alarm_fixture(name="nbarfoo", action="abarfoo"))
    conn.create_alarm(alarm_fixture(name="nbazfoo", action="abazfoo"))

    alarms = conn.describe_alarms_for_metric("nbarfoo_metric", "nbarfoo_namespace")
    alarms.should.have.length_of(1)

    alarms = conn.describe_alarms_for_metric("nbazfoo_metric", "nbazfoo_namespace")
    alarms.should.have.length_of(1)


# Has boto3 equivalent
@mock_cloudwatch_deprecated
def test_get_metric_statistics():
    conn = boto.connect_cloudwatch()

    metric_timestamp = datetime(2018, 4, 9, 13, 0, 0, 0)

    conn.put_metric_data(
        namespace="tester",
        name="metric",
        value=1.5,
        dimensions={"InstanceId": ["i-0123456,i-0123457"]},
        timestamp=metric_timestamp,
        unit="Count",
    )

    metric_kwargs = dict(
        namespace="tester",
        metric_name="metric",
        start_time=metric_timestamp,
        end_time=datetime.now(),
        period=3600,
        statistics=["Minimum"],
        unit="Count",
    )

    datapoints = conn.get_metric_statistics(**metric_kwargs)
    datapoints.should.have.length_of(1)
    datapoint = datapoints[0]
    datapoint.should.have.key("Minimum").which.should.equal(1.5)
    datapoint.should.have.key("Timestamp").which.should.equal(metric_timestamp)

    metric_kwargs = dict(
        namespace="tester",
        metric_name="metric",
        start_time=metric_timestamp,
        end_time=datetime.now(),
        period=3600,
        statistics=["Minimum"],
        unit="Percent",
    )

    datapoints = conn.get_metric_statistics(**metric_kwargs)
    datapoints.should.have.length_of(0)


# TODO: THIS IS CURRENTLY BROKEN!
# @mock_s3_deprecated
# @mock_cloudwatch_deprecated
# def test_cloudwatch_return_s3_metrics():
#
#     region = "us-east-1"
#
#     cw = boto.ec2.cloudwatch.connect_to_region(region)
#     s3 = boto.s3.connect_to_region(region)
#
#     bucket_name_1 = "test-bucket-1"
#     bucket_name_2 = "test-bucket-2"
#
#     bucket1 = s3.create_bucket(bucket_name=bucket_name_1)
#     key = Key(bucket1)
#     key.key = "the-key"
#     key.set_contents_from_string("foobar" * 4)
#     s3.create_bucket(bucket_name=bucket_name_2)
#
#     metrics_s3_bucket_1 = cw.list_metrics(dimensions={"BucketName": bucket_name_1})
#     # Verify that the OOTB S3 metrics are available for the created buckets
#     len(metrics_s3_bucket_1).should.be(2)
#     metric_names = [m.name for m in metrics_s3_bucket_1]
#     sorted(metric_names).should.equal(
#         ["Metric:BucketSizeBytes", "Metric:NumberOfObjects"]
#     )
#
#     # Explicit clean up - the metrics for these buckets are messing with subsequent tests
#     key.delete()
#     s3.delete_bucket(bucket_name_1)
#     s3.delete_bucket(bucket_name_2)
