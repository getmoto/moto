'''
Test the different ways that the decorator can be used
'''
from __future__ import unicode_literals
import unittest
import mock

import boto
from boto.exception import EC2ResponseError
import sure  # noqa
from nose.tools import assert_raises

from moto import mock_ec2, mock_s3
import tests.backport_assert_raises  # noqa


class MockHttpResponse(mock.Mock):
    status = 42
    body = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Errors><Error><Code>AuthFailure</Code><Message>AWS was not able to validate the provided access credentials</Message></Error></Errors><RequestID>817844cd-ee50-4abc-ae2a-79118981df3c</RequestID></Response>"""

    def read(self):
        return self.body

@mock_ec2
def test_basic_connect():
    boto.connect_ec2()


@mock_ec2
def test_basic_decorator():
    conn = boto.connect_ec2('the_key', 'the_secret')
    list(conn.get_all_instances()).should.equal([])


def test_context_manager(*args):
    conn = boto.connect_ec2('the_key', 'the_secret')
    with mock.patch('boto.connection.AWSQueryConnection.make_request', return_value=MockHttpResponse()):
        with assert_raises(EC2ResponseError):
            conn.get_all_instances()

    with mock_ec2():
        conn = boto.connect_ec2('the_key', 'the_secret')
        list(conn.get_all_instances()).should.equal([])

    with mock.patch('boto.connection.AWSQueryConnection.make_request', return_value=MockHttpResponse()):
        with assert_raises(EC2ResponseError):
            conn = boto.connect_ec2('the_key', 'the_secret')
            conn.get_all_instances()


def test_decorator_start_and_stop(*args):
    conn = boto.connect_ec2('the_key', 'the_secret')
    with mock.patch('boto.connection.AWSQueryConnection.make_request', return_value=MockHttpResponse()):
        with assert_raises(EC2ResponseError):
            conn.get_all_instances()

    mock_obj = mock_ec2()
    mock_obj.start()
    conn = boto.connect_ec2('the_key', 'the_secret')
    list(conn.get_all_instances()).should.equal([])
    mock_obj.stop()

    with mock.patch('boto.connection.AWSQueryConnection.make_request', return_value=MockHttpResponse()):
        with assert_raises(EC2ResponseError):
            conn.get_all_instances()


@mock_ec2
def test_decorater_wrapped_gets_set():
    """
    Moto decorator's __wrapped__ should get set to the tests function
    """
    test_decorater_wrapped_gets_set.__wrapped__.__name__.should.equal('test_decorater_wrapped_gets_set')


@mock_ec2
class Tester(object):
    def test_the_class(self):
        conn = boto.connect_ec2()
        list(conn.get_all_instances()).should.have.length_of(0)

    def test_still_the_same(self):
        conn = boto.connect_ec2()
        list(conn.get_all_instances()).should.have.length_of(0)


@mock_s3
class TesterWithSetup(unittest.TestCase):
    def setUp(self):
        self.conn = boto.connect_s3()
        self.conn.create_bucket('mybucket')

    def test_still_the_same(self):
        bucket = self.conn.get_bucket('mybucket')
        bucket.name.should.equal("mybucket")
