import unittest

import boto3

from moto import mock_aws
from tests import EXAMPLE_AMI_ID


class TestNestedDecoratorsBoto3(unittest.TestCase):
    @mock_aws
    def setup_sqs_queue(self) -> None:
        conn = boto3.resource("sqs", region_name="us-east-1")
        queue = conn.create_queue(QueueName="some-queue")

        queue.send_message(MessageBody="test message 1")

        queue.reload()
        assert queue.attributes["ApproximateNumberOfMessages"] == "1"

    @mock_aws
    def test_nested(self) -> None:
        self.setup_sqs_queue()

        conn = boto3.client("ec2", region_name="us-west-2")
        conn.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)


def test_multiple_mocks() -> None:
    with mock_aws():
        client = boto3.client("sqs", region_name="us-east-1")
        client.create_queue(QueueName="some-queue")

        # Starting another (inner) mock does not reset the data
        with mock_aws():
            assert len(client.list_queues()["QueueUrls"]) == 1

        # Ending an inner mock does not reset the data
        assert len(client.list_queues()["QueueUrls"]) == 1
