import boto
from boto.ec2.cloudwatch.alarm import MetricAlarm
import boto3
from datetime import datetime, timedelta
import pytz
import sure  # noqa

from moto import mock_cloudwatch_deprecated


def alarm_fixture(name="tester", action=None):
    action = action or ['arn:alarm']
    return MetricAlarm(
        name=name,
        namespace="{0}_namespace".format(name),
        metric="{0}_metric".format(name),
        comparison='>=',
        threshold=2.0,
        period=60,
        evaluation_periods=5,
        statistic='Average',
        description='A test',
        dimensions={'InstanceId': ['i-0123456,i-0123457']},
        alarm_actions=action,
        ok_actions=['arn:ok'],
        insufficient_data_actions=['arn:insufficient'],
        unit='Seconds',
    )


@mock_cloudwatch_deprecated
def test_create_alarm():
    conn = boto.connect_cloudwatch()

    alarm = alarm_fixture()
    conn.create_alarm(alarm)

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(1)
    alarm = alarms[0]
    alarm.name.should.equal('tester')
    alarm.namespace.should.equal('tester_namespace')
    alarm.metric.should.equal('tester_metric')
    alarm.comparison.should.equal('>=')
    alarm.threshold.should.equal(2.0)
    alarm.period.should.equal(60)
    alarm.evaluation_periods.should.equal(5)
    alarm.statistic.should.equal('Average')
    alarm.description.should.equal('A test')
    dict(alarm.dimensions).should.equal(
        {'InstanceId': ['i-0123456,i-0123457']})
    list(alarm.alarm_actions).should.equal(['arn:alarm'])
    list(alarm.ok_actions).should.equal(['arn:ok'])
    list(alarm.insufficient_data_actions).should.equal(['arn:insufficient'])
    alarm.unit.should.equal('Seconds')


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


@mock_cloudwatch_deprecated
def test_put_metric_data():
    conn = boto.connect_cloudwatch()

    conn.put_metric_data(
        namespace='tester',
        name='metric',
        value=1.5,
        dimensions={'InstanceId': ['i-0123456,i-0123457']},
    )

    metrics = conn.list_metrics()
    metrics.should.have.length_of(1)
    metric = metrics[0]
    metric.namespace.should.equal('tester')
    metric.name.should.equal('metric')
    dict(metric.dimensions).should.equal(
        {'InstanceId': ['i-0123456,i-0123457']})


@mock_cloudwatch_deprecated
def test_describe_alarms():
    conn = boto.connect_cloudwatch()

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(0)

    conn.create_alarm(alarm_fixture(name="nfoobar", action="afoobar"))
    conn.create_alarm(alarm_fixture(name="nfoobaz", action="afoobaz"))
    conn.create_alarm(alarm_fixture(name="nbarfoo", action="abarfoo"))
    conn.create_alarm(alarm_fixture(name="nbazfoo", action="abazfoo"))

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(4)
    alarms = conn.describe_alarms(alarm_name_prefix="nfoo")
    alarms.should.have.length_of(2)
    alarms = conn.describe_alarms(
        alarm_names=["nfoobar", "nbarfoo", "nbazfoo"])
    alarms.should.have.length_of(3)
    alarms = conn.describe_alarms(action_prefix="afoo")
    alarms.should.have.length_of(2)

    for alarm in conn.describe_alarms():
        alarm.delete()

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(0)
