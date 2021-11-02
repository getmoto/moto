import boto
from boto.s3.connection import OrdinaryCallingFormat

from moto import mock_s3_deprecated


def create_connection(key=None, secret=None):
    return boto.connect_s3(key, secret, calling_format=OrdinaryCallingFormat())


def test_bucketpath_combo_serial():
    @mock_s3_deprecated
    def make_bucket_path():
        conn = create_connection()
        conn.create_bucket("mybucketpath")

    @mock_s3_deprecated
    def make_bucket():
        conn = boto.connect_s3("the_key", "the_secret")
        conn.create_bucket("mybucket")

    make_bucket()
    make_bucket_path()
