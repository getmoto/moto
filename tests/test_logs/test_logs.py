import boto3
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_logs, settings
from nose.tools import assert_raises

_logs_region = 'us-east-1' if settings.TEST_SERVER_MODE else 'us-west-2'


@mock_logs
def test_log_group_create():
    conn = boto3.client('logs', 'us-west-2')
    log_group_name = 'dummy'
    response = conn.create_log_group(logGroupName=log_group_name)
    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_exceptions():
    conn = boto3.client('logs', 'us-west-2')
    log_group_name = 'dummy'
    log_stream_name = 'dummp-stream'
    conn.create_log_group(logGroupName=log_group_name)
    with assert_raises(ClientError):
        conn.create_log_group(logGroupName=log_group_name)

    # descrine_log_groups is not implemented yet

    conn.create_log_stream(
        logGroupName=log_group_name,
        logStreamName=log_stream_name
    )
    with assert_raises(ClientError):
        conn.create_log_stream(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )

    conn.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[
            {
                'timestamp': 0,
            'message': 'line'
            },
        ],
    )

    with assert_raises(ClientError):
        conn.put_log_events(
            logGroupName=log_group_name,
            logStreamName="invalid-stream",
            logEvents=[
                {
                    'timestamp': 0,
                    'message': 'line'
                },
            ],
        )
