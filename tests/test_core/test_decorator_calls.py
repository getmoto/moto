from __future__ import unicode_literals
import boto
from boto.exception import EC2ResponseError
import sure  # noqa
import unittest

import pytest

from moto import mock_ec2_deprecated, mock_s3_deprecated

"""
Test the different ways that the decorator can be used
"""


@mock_ec2_deprecated
def test_basic_connect():
    boto.connect_ec2()


@mock_ec2_deprecated
def test_basic_decorator():
    conn = boto.connect_ec2("the_key", "the_secret")
    list(conn.get_all_instances()).should.equal([])


@pytest.mark.network
def test_context_manager():
    conn = boto.connect_ec2("the_key", "the_secret")
    with pytest.raises(EC2ResponseError):
        conn.get_all_instances()

    with mock_ec2_deprecated():
        conn = boto.connect_ec2("the_key", "the_secret")
        list(conn.get_all_instances()).should.equal([])

    with pytest.raises(EC2ResponseError):
        conn = boto.connect_ec2("the_key", "the_secret")
        conn.get_all_instances()


@pytest.mark.network
def test_decorator_start_and_stop():
    conn = boto.connect_ec2("the_key", "the_secret")
    with pytest.raises(EC2ResponseError):
        conn.get_all_instances()

    mock = mock_ec2_deprecated()
    mock.start()
    conn = boto.connect_ec2("the_key", "the_secret")
    list(conn.get_all_instances()).should.equal([])
    mock.stop()

    with pytest.raises(EC2ResponseError):
        conn.get_all_instances()


@mock_ec2_deprecated
def test_decorater_wrapped_gets_set():
    """
    Moto decorator's __wrapped__ should get set to the tests function
    """
    test_decorater_wrapped_gets_set.__wrapped__.__name__.should.equal(
        "test_decorater_wrapped_gets_set"
    )


@mock_ec2_deprecated
class Tester(object):
    def test_the_class(self):
        conn = boto.connect_ec2()
        list(conn.get_all_instances()).should.have.length_of(0)

    def test_still_the_same(self):
        conn = boto.connect_ec2()
        list(conn.get_all_instances()).should.have.length_of(0)


@mock_s3_deprecated
class TesterWithSetup(unittest.TestCase):
    def setUp(self):
        self.conn = boto.connect_s3()
        self.conn.create_bucket("mybucket")

    def test_still_the_same(self):
        bucket = self.conn.get_bucket("mybucket")
        bucket.name.should.equal("mybucket")


@mock_s3_deprecated
class TesterWithStaticmethod(object):
    @staticmethod
    def static(*args):
        assert not args or not isinstance(args[0], TesterWithStaticmethod)

    def test_no_instance_sent_to_staticmethod(self):
        self.static()
