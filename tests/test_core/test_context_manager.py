import sure  # noqa
import boto3
from moto import mock_sqs, settings


def test_context_manager_returns_mock():
    with mock_sqs() as sqs_mock:
        conn = boto3.client("sqs", region_name='us-west-1')
        conn.create_queue(QueueName="queue1")

        if not settings.TEST_SERVER_MODE:
            list(sqs_mock.backends['us-west-1'].queues.keys()).should.equal(['queue1'])
