import sure  # noqa # pylint: disable=unused-import
import boto3
from moto import mock_sqs, settings
from tests import DEFAULT_ACCOUNT_ID


def test_context_manager_returns_mock():
    with mock_sqs() as sqs_mock:
        conn = boto3.client("sqs", region_name="us-west-1")
        conn.create_queue(QueueName="queue1")

        if not settings.TEST_SERVER_MODE:
            backend = sqs_mock.backends[DEFAULT_ACCOUNT_ID]["us-west-1"]
            list(backend.queues.keys()).should.equal(["queue1"])
