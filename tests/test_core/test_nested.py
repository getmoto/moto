from __future__ import unicode_literals
import unittest

from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
from boto.ec2 import EC2Connection

from moto import mock_sqs_deprecated, mock_ec2_deprecated
from tests import EXAMPLE_AMI_ID


class TestNestedDecorators(unittest.TestCase):
    @mock_sqs_deprecated
    def setup_sqs_queue(self):
        conn = SQSConnection()
        q = conn.create_queue("some-queue")

        m = Message()
        m.set_body("This is my first message.")
        q.write(m)

        self.assertEqual(q.count(), 1)

    @mock_ec2_deprecated
    def test_nested(self):
        self.setup_sqs_queue()

        conn = EC2Connection()
        conn.run_instances(EXAMPLE_AMI_ID)
