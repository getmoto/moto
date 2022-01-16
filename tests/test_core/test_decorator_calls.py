import boto
import boto3
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import
import unittest

import pytest

from moto import mock_ec2_deprecated, mock_s3_deprecated, mock_s3

"""
Test the different ways that the decorator can be used
"""


@mock_ec2_deprecated
def test_basic_connect():
    boto.connect_ec2()


@mock_ec2_deprecated
def test_basic_decorator():
    conn = boto.connect_ec2("the_key", "the_secret")
    list(conn.get_all_reservations()).should.equal([])


@pytest.mark.network
def test_context_manager():
    conn = boto.connect_ec2("the_key", "the_secret")
    with pytest.raises(EC2ResponseError):
        conn.get_all_reservations()

    with mock_ec2_deprecated():
        conn = boto.connect_ec2("the_key", "the_secret")
        list(conn.get_all_reservations()).should.equal([])

    with pytest.raises(EC2ResponseError):
        conn = boto.connect_ec2("the_key", "the_secret")
        conn.get_all_reservations()


@pytest.mark.network
def test_decorator_start_and_stop():
    conn = boto.connect_ec2("the_key", "the_secret")
    with pytest.raises(EC2ResponseError):
        conn.get_all_reservations()

    mock = mock_ec2_deprecated()
    mock.start()
    conn = boto.connect_ec2("the_key", "the_secret")
    list(conn.get_all_reservations()).should.equal([])
    mock.stop()

    with pytest.raises(EC2ResponseError):
        conn.get_all_reservations()


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
        list(conn.get_all_reservations()).should.have.length_of(0)

    def test_still_the_same(self):
        conn = boto.connect_ec2()
        list(conn.get_all_reservations()).should.have.length_of(0)


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


@mock_s3
class TestWithSetup(unittest.TestCase):
    def setUp(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")

    def test_should_find_bucket(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        self.assertIsNotNone(s3.head_bucket(Bucket="mybucket"))

    def test_should_not_find_unknown_bucket(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ClientError):
            s3.head_bucket(Bucket="unknown_bucket")


@mock_s3
class TestWithPublicMethod(unittest.TestCase):
    def ensure_bucket_exists(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")

    def test_should_find_bucket(self):
        self.ensure_bucket_exists()

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.head_bucket(Bucket="mybucket").shouldnt.equal(None)

    def test_should_not_find_bucket(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ClientError):
            s3.head_bucket(Bucket="mybucket")


@mock_s3
class TestWithPseudoPrivateMethod(unittest.TestCase):
    def _ensure_bucket_exists(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")

    def test_should_find_bucket(self):
        self._ensure_bucket_exists()
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.head_bucket(Bucket="mybucket").shouldnt.equal(None)

    def test_should_not_find_bucket(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        with pytest.raises(ClientError):
            s3.head_bucket(Bucket="mybucket")


@mock_s3
class TestWithNestedClasses:
    class NestedClass(unittest.TestCase):
        def _ensure_bucket_exists(self):
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="bucketclass1")

        def test_should_find_bucket(self):
            self._ensure_bucket_exists()
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.head_bucket(Bucket="bucketclass1")

    class NestedClass2(unittest.TestCase):
        def _ensure_bucket_exists(self):
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="bucketclass2")

        def test_should_find_bucket(self):
            self._ensure_bucket_exists()
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.head_bucket(Bucket="bucketclass2")

        def test_should_not_find_bucket_from_different_class(self):
            s3 = boto3.client("s3", region_name="us-east-1")
            with pytest.raises(ClientError):
                s3.head_bucket(Bucket="bucketclass1")

    class TestWithSetup(unittest.TestCase):
        def setUp(self):
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="mybucket")

        def test_should_find_bucket(self):
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.head_bucket(Bucket="mybucket")

            s3.create_bucket(Bucket="bucketinsidetest")

        def test_should_not_find_bucket_from_test_method(self):
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.head_bucket(Bucket="mybucket")

            with pytest.raises(ClientError):
                s3.head_bucket(Bucket="bucketinsidetest")
