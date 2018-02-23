from __future__ import unicode_literals
import unittest

from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
from boto.ec2 import EC2Connection
import requests

from moto import mock_sqs_deprecated, mock_ec2_deprecated, mock_sqs, mock_sns
from moto.packages import httpretty


class TestNestedDecorators(unittest.TestCase):

    @mock_sqs_deprecated
    def setup_sqs_queue(self):
        conn = SQSConnection()
        q = conn.create_queue('some-queue')

        m = Message()
        m.set_body('This is my first message.')
        q.write(m)

        self.assertEqual(q.count(), 1)

    @mock_ec2_deprecated
    def test_nested(self):
        self.setup_sqs_queue()
        conn = EC2Connection()
        conn.run_instances('ami-123456')

    @mock_sqs
    @mock_sns
    def test_multiple_mocks_part1(self):
        pass

    @httpretty.activate
    def test_multiple_mocks_part2(self):
        httpretty.register_uri(httpretty.GET, 'http://www.google.com')
        response = requests.get('http://www.google.com')
        assert(response.status_code == 200)
        assert(response.text == 'HTTPretty :)')
