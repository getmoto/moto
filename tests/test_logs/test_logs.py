import boto3
import sure  # noqa

from moto import mock_logs, settings

_logs_region = 'us-east-1' if settings.TEST_SERVER_MODE else 'us-west-2'


@mock_logs
def test_log_group_create():
    conn = boto3.client('logs', 'us-west-2')
    log_group_name = 'dummy'
    response = conn.create_log_group(logGroupName=log_group_name)
    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_put_logs():
    conn = boto3.client('logs', 'us-west-2')
    log_group_name = 'dummy'
    log_stream_name = 'stream'
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(
        logGroupName=log_group_name,
        logStreamName=log_stream_name
    )
    messages = [
        {'timestamp': 0, 'message': 'hello'},
        {'timestamp': 0, 'message': 'world'}
    ]
    conn.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=messages
    )
    res = conn.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name
    )
    events = res['events']
    events.should.have.length_of(2)
