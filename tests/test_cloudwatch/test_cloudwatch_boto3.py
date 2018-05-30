from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import pytz
import sure   # noqa

from moto import mock_cloudwatch


@mock_cloudwatch
def test_put_list_dashboard():
    client = boto3.client('cloudwatch', region_name='eu-central-1')
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName='test1', DashboardBody=widget)
    resp = client.list_dashboards()

    len(resp['DashboardEntries']).should.equal(1)


@mock_cloudwatch
def test_put_list_prefix_nomatch_dashboard():
    client = boto3.client('cloudwatch', region_name='eu-central-1')
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName='test1', DashboardBody=widget)
    resp = client.list_dashboards(DashboardNamePrefix='nomatch')

    len(resp['DashboardEntries']).should.equal(0)


@mock_cloudwatch
def test_delete_dashboard():
    client = boto3.client('cloudwatch', region_name='eu-central-1')
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName='test1', DashboardBody=widget)
    client.put_dashboard(DashboardName='test2', DashboardBody=widget)
    client.put_dashboard(DashboardName='test3', DashboardBody=widget)
    client.delete_dashboards(DashboardNames=['test2', 'test1'])

    resp = client.list_dashboards(DashboardNamePrefix='test3')
    len(resp['DashboardEntries']).should.equal(1)


@mock_cloudwatch
def test_delete_dashboard_fail():
    client = boto3.client('cloudwatch', region_name='eu-central-1')
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName='test1', DashboardBody=widget)
    client.put_dashboard(DashboardName='test2', DashboardBody=widget)
    client.put_dashboard(DashboardName='test3', DashboardBody=widget)
    # Doesnt delete anything if all dashboards to be deleted do not exist
    try:
        client.delete_dashboards(DashboardNames=['test2', 'test1', 'test_no_match'])
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFound')
    else:
        raise RuntimeError('Should of raised error')

    resp = client.list_dashboards()
    len(resp['DashboardEntries']).should.equal(3)


@mock_cloudwatch
def test_get_dashboard():
    client = boto3.client('cloudwatch', region_name='eu-central-1')
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'
    client.put_dashboard(DashboardName='test1', DashboardBody=widget)

    resp = client.get_dashboard(DashboardName='test1')
    resp.should.contain('DashboardArn')
    resp.should.contain('DashboardBody')
    resp['DashboardName'].should.equal('test1')


@mock_cloudwatch
def test_get_dashboard_fail():
    client = boto3.client('cloudwatch', region_name='eu-central-1')

    try:
        client.get_dashboard(DashboardName='test1')
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFound')
    else:
        raise RuntimeError('Should of raised error')


@mock_cloudwatch
def test_alarm_state():
    client = boto3.client('cloudwatch', region_name='eu-central-1')

    client.put_metric_alarm(
        AlarmName='testalarm1',
        MetricName='cpu',
        Namespace='blah',
        Period=10,
        EvaluationPeriods=5,
        Statistic='Average',
        Threshold=2,
        ComparisonOperator='GreaterThanThreshold',
    )
    client.put_metric_alarm(
        AlarmName='testalarm2',
        MetricName='cpu',
        Namespace='blah',
        Period=10,
        EvaluationPeriods=5,
        Statistic='Average',
        Threshold=2,
        ComparisonOperator='GreaterThanThreshold',
    )

    # This is tested implicitly as if it doesnt work the rest will die
    client.set_alarm_state(
        AlarmName='testalarm1',
        StateValue='ALARM',
        StateReason='testreason',
        StateReasonData='{"some": "json_data"}'
    )

    resp = client.describe_alarms(
        StateValue='ALARM'
    )
    len(resp['MetricAlarms']).should.equal(1)
    resp['MetricAlarms'][0]['AlarmName'].should.equal('testalarm1')
    resp['MetricAlarms'][0]['StateValue'].should.equal('ALARM')

    resp = client.describe_alarms(
        StateValue='OK'
    )
    len(resp['MetricAlarms']).should.equal(1)
    resp['MetricAlarms'][0]['AlarmName'].should.equal('testalarm2')
    resp['MetricAlarms'][0]['StateValue'].should.equal('OK')

    # Just for sanity
    resp = client.describe_alarms()
    len(resp['MetricAlarms']).should.equal(2)


@mock_cloudwatch
def test_put_metric_data_no_dimensions():
    conn = boto3.client('cloudwatch', region_name='us-east-1')

    conn.put_metric_data(
        Namespace='tester',
        MetricData=[
            dict(
                MetricName='metric',
                Value=1.5,
            )
        ]
    )

    metrics = conn.list_metrics()['Metrics']
    metrics.should.have.length_of(1)
    metric = metrics[0]
    metric['Namespace'].should.equal('tester')
    metric['MetricName'].should.equal('metric')



@mock_cloudwatch
def test_put_metric_data_with_statistics():
    conn = boto3.client('cloudwatch', region_name='us-east-1')

    conn.put_metric_data(
        Namespace='tester',
        MetricData=[
            dict(
                MetricName='statmetric',
                Timestamp=datetime(2015, 1, 1),
                # no Value to test  https://github.com/spulec/moto/issues/1615
                StatisticValues=dict(
                    SampleCount=123.0,
                    Sum=123.0,
                    Minimum=123.0,
                    Maximum=123.0
                ),
                Unit='Milliseconds',
                StorageResolution=123
            )
        ]
    )

    metrics = conn.list_metrics()['Metrics']
    metrics.should.have.length_of(1)
    metric = metrics[0]
    metric['Namespace'].should.equal('tester')
    metric['MetricName'].should.equal('statmetric')
    # TODO: test statistics - https://github.com/spulec/moto/issues/1615

@mock_cloudwatch
def test_get_metric_statistics():
    conn = boto3.client('cloudwatch', region_name='us-east-1')
    utc_now = datetime.now(tz=pytz.utc)

    conn.put_metric_data(
        Namespace='tester',
        MetricData=[
            dict(
                MetricName='metric',
                Value=1.5,
                Timestamp=utc_now
            )
        ]
    )

    stats = conn.get_metric_statistics(
        Namespace='tester',
        MetricName='metric',
        StartTime=utc_now - timedelta(seconds=60),
        EndTime=utc_now + timedelta(seconds=60),
        Period=60,
        Statistics=['SampleCount', 'Sum']
    )

    stats['Datapoints'].should.have.length_of(1)
    datapoint = stats['Datapoints'][0]
    datapoint['SampleCount'].should.equal(1.0)
    datapoint['Sum'].should.equal(1.5)
