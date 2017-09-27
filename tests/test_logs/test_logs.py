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
