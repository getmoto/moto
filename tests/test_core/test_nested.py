from __future__ import unicode_literals
import sure  # noqa
import unittest

from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
from boto.ec2 import EC2Connection
import boto3

from moto import mock_sqs_deprecated, mock_ec2_deprecated
from moto import mock_sqs, mock_ec2
from tests import EXAMPLE_AMI_ID


class TestNestedDecorators(unittest.TestCase):
    # Has boto3 equivalent
    @mock_sqs_deprecated
    def setup_sqs_queue(self):
        conn = SQSConnection()
        q = conn.create_queue("some-queue")

        m = Message()
        m.set_body("This is my first message.")
        q.write(m)

        self.assertEqual(q.count(), 1)

    # Has boto3 equivalent
    @mock_ec2_deprecated
    def test_nested(self):
        self.setup_sqs_queue()

        conn = EC2Connection()
        conn.run_instances(EXAMPLE_AMI_ID)


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
