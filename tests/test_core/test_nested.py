import sure  # noqa # pylint: disable=unused-import
import unittest

import boto3

from moto import mock_sqs, mock_ec2
from tests import EXAMPLE_AMI_ID


class TestNestedDecoratorsBoto3(unittest.TestCase):
    @mock_sqs
    def setup_sqs_queue(self):
        conn = boto3.resource("sqs", region_name="us-east-1")
        queue = conn.create_queue(QueueName="some-queue")

        queue.send_message(MessageBody="test message 1")

        queue.reload()
        queue.attributes["ApproximateNumberOfMessages"].should.equal("1")

    @mock_ec2
    def test_nested(self):
        self.setup_sqs_queue()

        conn = boto3.client("ec2", region_name="us-west-2")
        conn.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
