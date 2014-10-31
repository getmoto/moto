import boto
from boto.ec2.cloudwatch.alarm import MetricAlarm
import sure  # noqa

from moto import mock_cloudwatch


@mock_cloudwatch
def test_create_alarm():
    conn = boto.connect_cloudwatch()

    alarm = MetricAlarm(
        name='tester',
        comparison='>=',
        threshold=2.0,
        period=60,
        evaluation_periods=5,
        statistic='Average',
        description='A test',
        dimensions={'InstanceId': ['i-0123456,i-0123457']},
        alarm_actions=['arn:alarm'],
        ok_actions=['arn:ok'],
        insufficient_data_actions=['arn:insufficient'],
        unit='Seconds',
    )
    conn.create_alarm(alarm)

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(1)
    alarm = alarms[0]
    alarm.name.should.equal('tester')
    alarm.comparison.should.equal('>=')
    alarm.threshold.should.equal(2.0)
    alarm.period.should.equal(60)
    alarm.evaluation_periods.should.equal(5)
    alarm.statistic.should.equal('Average')
    alarm.description.should.equal('A test')
    dict(alarm.dimensions).should.equal({'InstanceId': ['i-0123456,i-0123457']})
    list(alarm.alarm_actions).should.equal(['arn:alarm'])
    list(alarm.ok_actions).should.equal(['arn:ok'])
    list(alarm.insufficient_data_actions).should.equal(['arn:insufficient'])
    alarm.unit.should.equal('Seconds')


@mock_cloudwatch
def test_delete_alarm():
    conn = boto.connect_cloudwatch()

    alarm = MetricAlarm(
        name='tester',
        comparison='>=',
        threshold=2.0,
        period=60,
        evaluation_periods=5,
        statistic='Average',
        description='A test',
        dimensions={'InstanceId': ['i-0123456,i-0123457']},
        alarm_actions=['arn:alarm'],
        ok_actions=['arn:ok'],
        insufficient_data_actions=['arn:insufficient'],
        unit='Seconds',
    )
    conn.create_alarm(alarm)

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(1)

    alarms[0].delete()

    alarms = conn.describe_alarms()
    alarms.should.have.length_of(0)
