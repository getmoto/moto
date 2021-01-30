# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import sys
import os
from boto3 import Session
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError
from functools import wraps
from gzip import GzipFile
from io import BytesIO
import zlib
import pickle
import uuid

import json
import boto
import boto3
from botocore.client import ClientError
import botocore.exceptions
from boto.exception import S3CreateError, S3ResponseError
from botocore.handlers import disable_signing
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from freezegun import freeze_time
import six
import requests
from moto.s3.responses import DEFAULT_REGION_NAME
from unittest import SkipTest
import pytest

import sure  # noqa

from moto import settings, mock_s3, mock_s3_deprecated, mock_config
import moto.s3.models as s3model
from moto.core.exceptions import InvalidNextTokenException
from moto.core.utils import py2_strip_unicode_keys


if settings.TEST_SERVER_MODE:
    REDUCED_PART_SIZE = s3model.UPLOAD_PART_MIN_SIZE
    EXPECTED_ETAG = '"140f92a6df9f9e415f74a1463bcee9bb-2"'
else:
    REDUCED_PART_SIZE = 256
    EXPECTED_ETAG = '"66d1a1a2ed08fd05c137f316af4ff255-2"'


def reduced_min_part_size(f):
    """speed up tests by temporarily making the multipart minimum part size
    small
    """
    orig_size = s3model.UPLOAD_PART_MIN_SIZE

    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            s3model.UPLOAD_PART_MIN_SIZE = REDUCED_PART_SIZE
            return f(*args, **kwargs)
        finally:
            s3model.UPLOAD_PART_MIN_SIZE = orig_size

    return wrapped


class MyModel(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def save(self):
        s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
        s3.put_object(Bucket="mybucket", Key=self.name, Body=self.value)


@mock_s3
def test_keys_are_pickleable():
    """Keys must be pickleable due to boto3 implementation details."""
    key = s3model.FakeKey("name", b"data!")
    assert key.value == b"data!"

    pickled = pickle.dumps(key)
    loaded = pickle.loads(pickled)
    assert loaded.value == key.value


@mock_s3
def test_append_to_value__basic():
    key = s3model.FakeKey("name", b"data!")
    assert key.value == b"data!"
    assert key.size == 5

    key.append_to_value(b" And even more data")
    assert key.value == b"data! And even more data"
    assert key.size == 24


@mock_s3
def test_append_to_value__nothing_added():
    key = s3model.FakeKey("name", b"data!")
    assert key.value == b"data!"
    assert key.size == 5

    key.append_to_value(b"")
    assert key.value == b"data!"
    assert key.size == 5


@mock_s3
def test_append_to_value__empty_key():
    key = s3model.FakeKey("name", b"")
    assert key.value == b""
    assert key.size == 0

    key.append_to_value(b"stuff")
    assert key.value == b"stuff"
    assert key.size == 5


@mock_s3
def test_my_model_save():
    # Create Bucket so that test can run
    conn = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    conn.create_bucket(Bucket="mybucket")
    ####################################

    model_instance = MyModel("steve", "is awesome")
    model_instance.save()

    body = conn.Object("mybucket", "steve").get()["Body"].read().decode()

    assert body == "is awesome"


@mock_s3
def test_key_etag():
    conn = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    conn.create_bucket(Bucket="mybucket")

    model_instance = MyModel("steve", "is awesome")
    model_instance.save()

    conn.Bucket("mybucket").Object("steve").e_tag.should.equal(
        '"d32bda93738f7e03adb22e66c90fbc04"'
    )


@mock_s3_deprecated
def test_multipart_upload_too_small():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    multipart.upload_part_from_file(BytesIO(b"hello"), 1)
    multipart.upload_part_from_file(BytesIO(b"world"), 2)
    # Multipart with total size under 5MB is refused
    multipart.complete_upload.should.throw(S3ResponseError)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # last part, can be less than 5 MB
    part2 = b"1"
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload_out_of_order():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    # last part, can be less than 5 MB
    part2 = b"1"
    multipart.upload_part_from_file(BytesIO(part2), 4)
    part1 = b"0" * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload_with_headers():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key", metadata={"foo": "bar"})
    part1 = b"0" * 10
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.complete_upload()

    key = bucket.get_key("the-key")
    key.metadata.should.equal({"foo": "bar"})


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload_with_copy_key():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "original-key"
    key.set_contents_from_string("key_value")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.copy_part_from_key("foobar", "original-key", 2, 0, 3)
    multipart.complete_upload()
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + b"key_")


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload_cancel():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.cancel_upload()
    # TODO we really need some sort of assertion here, but we don't currently
    # have the ability to list mulipart uploads for a bucket.


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_etag():
    # Create Bucket so that test can run
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("mybucket")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # last part, can be less than 5 MB
    part2 = b"1"
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key("the-key").etag.should.equal(EXPECTED_ETAG)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_invalid_order():
    # Create Bucket so that test can run
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("mybucket")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b"0" * 5242880
    etag1 = multipart.upload_part_from_file(BytesIO(part1), 1).etag
    # last part, can be less than 5 MB
    part2 = b"1"
    etag2 = multipart.upload_part_from_file(BytesIO(part2), 2).etag
    xml = "<Part><PartNumber>{0}</PartNumber><ETag>{1}</ETag></Part>"
    xml = xml.format(2, etag2) + xml.format(1, etag1)
    xml = "<CompleteMultipartUpload>{0}</CompleteMultipartUpload>".format(xml)
    bucket.complete_multipart_upload.when.called_with(
        multipart.key_name, multipart.id, xml
    ).should.throw(S3ResponseError)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_etag_quotes_stripped():
    # Create Bucket so that test can run
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("mybucket")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    etag1 = multipart.upload_part_from_file(BytesIO(part1), 1).etag
    # last part, can be less than 5 MB
    part2 = b"1"
    etag2 = multipart.upload_part_from_file(BytesIO(part2), 2).etag
    # Strip quotes from etags
    etag1 = etag1.replace('"', "")
    etag2 = etag2.replace('"', "")
    xml = "<Part><PartNumber>{0}</PartNumber><ETag>{1}</ETag></Part>"
    xml = xml.format(1, etag1) + xml.format(2, etag2)
    xml = "<CompleteMultipartUpload>{0}</CompleteMultipartUpload>".format(xml)
    bucket.complete_multipart_upload.when.called_with(
        multipart.key_name, multipart.id, xml
    ).should_not.throw(S3ResponseError)
    # we should get both parts as the key contents
    bucket.get_key("the-key").etag.should.equal(EXPECTED_ETAG)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_duplicate_upload():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # same part again
    multipart.upload_part_from_file(BytesIO(part1), 1)
    part2 = b"1" * 1024
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # We should get only one copy of part 1.
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3_deprecated
def test_list_multiparts():
    # Create Bucket so that test can run
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("mybucket")

    multipart1 = bucket.initiate_multipart_upload("one-key")
    multipart2 = bucket.initiate_multipart_upload("two-key")
    uploads = bucket.get_all_multipart_uploads()
    uploads.should.have.length_of(2)
    dict([(u.key_name, u.id) for u in uploads]).should.equal(
        {"one-key": multipart1.id, "two-key": multipart2.id}
    )
    multipart2.cancel_upload()
    uploads = bucket.get_all_multipart_uploads()
    uploads.should.have.length_of(1)
    uploads[0].key_name.should.equal("one-key")
    multipart1.cancel_upload()
    uploads = bucket.get_all_multipart_uploads()
    uploads.should.be.empty


@mock_s3_deprecated
def test_key_save_to_missing_bucket():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.get_bucket("mybucket", validate=False)

    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string.when.called_with("foobar").should.throw(
        S3ResponseError
    )


@mock_s3_deprecated
def test_missing_key():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    bucket.get_key("the-key").should.equal(None)


@mock_s3_deprecated
def test_missing_key_urllib2():
    conn = boto.connect_s3("the_key", "the_secret")
    conn.create_bucket("foobar")

    urlopen.when.called_with("http://foobar.s3.amazonaws.com/the-key").should.throw(
        HTTPError
    )


@mock_s3_deprecated
def test_empty_key():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("")

    key = bucket.get_key("the-key")
    key.size.should.equal(0)
    key.get_contents_as_string().should.equal(b"")


@mock_s3_deprecated
def test_empty_key_set_on_existing_key():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar")

    key = bucket.get_key("the-key")
    key.size.should.equal(6)
    key.get_contents_as_string().should.equal(b"foobar")

    key.set_contents_from_string("")
    bucket.get_key("the-key").get_contents_as_string().should.equal(b"")


@mock_s3_deprecated
def test_large_key_save():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar" * 100000)

    bucket.get_key("the-key").get_contents_as_string().should.equal(b"foobar" * 100000)


@mock_s3_deprecated
def test_copy_key():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key("new-key", "foobar", "the-key")

    bucket.get_key("the-key").get_contents_as_string().should.equal(b"some value")
    bucket.get_key("new-key").get_contents_as_string().should.equal(b"some value")


@pytest.mark.parametrize("key_name", ["the-unicode-💩-key", "key-with?question-mark"])
@mock_s3_deprecated
def test_copy_key_with_special_chars(key_name):
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = key_name
    key.set_contents_from_string("some value")

    bucket.copy_key("new-key", "foobar", key_name)

    bucket.get_key(key_name).get_contents_as_string().should.equal(b"some value")
    bucket.get_key("new-key").get_contents_as_string().should.equal(b"some value")


@mock_s3_deprecated
def test_copy_key_with_version():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    bucket.configure_versioning(versioning=True)
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")
    key.set_contents_from_string("another value")

    key = [key.version_id for key in bucket.get_all_versions() if not key.is_latest][0]
    bucket.copy_key("new-key", "foobar", "the-key", src_version_id=key)

    bucket.get_key("the-key").get_contents_as_string().should.equal(b"another value")
    bucket.get_key("new-key").get_contents_as_string().should.equal(b"some value")


@mock_s3_deprecated
def test_set_metadata():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_metadata("md", "Metadatastring")
    key.set_contents_from_string("Testval")

    bucket.get_key("the-key").get_metadata("md").should.equal("Metadatastring")


@mock_s3_deprecated
def test_copy_key_replace_metadata():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_metadata("md", "Metadatastring")
    key.set_contents_from_string("some value")

    bucket.copy_key(
        "new-key", "foobar", "the-key", metadata={"momd": "Mometadatastring"}
    )

    bucket.get_key("new-key").get_metadata("md").should.be.none
    bucket.get_key("new-key").get_metadata("momd").should.equal("Mometadatastring")


@freeze_time("2012-01-01 12:00:00")
@mock_s3_deprecated
def test_last_modified():
    # See https://github.com/boto/boto/issues/466
    conn = boto.connect_s3()
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    rs = bucket.get_all_keys()
    rs[0].last_modified.should.equal("2012-01-01T12:00:00.000Z")

    bucket.get_key("the-key").last_modified.should.equal(
        "Sun, 01 Jan 2012 12:00:00 GMT"
    )


@mock_s3_deprecated
def test_missing_bucket():
    conn = boto.connect_s3("the_key", "the_secret")
    conn.get_bucket.when.called_with("mybucket").should.throw(S3ResponseError)


@mock_s3_deprecated
def test_bucket_with_dash():
    conn = boto.connect_s3("the_key", "the_secret")
    conn.get_bucket.when.called_with("mybucket-test").should.throw(S3ResponseError)


@mock_s3_deprecated
def test_create_existing_bucket():
    "Trying to create a bucket that already exists should raise an Error"
    conn = boto.s3.connect_to_region("us-west-2")
    conn.create_bucket("foobar", location="us-west-2")
    with pytest.raises(S3CreateError):
        conn.create_bucket("foobar", location="us-west-2")


@mock_s3_deprecated
def test_create_existing_bucket_in_us_east_1():
    "Trying to create a bucket that already exists in us-east-1 returns the bucket"

    """"
    http://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html
    Your previous request to create the named bucket succeeded and you already
    own it. You get this error in all AWS regions except US Standard,
    us-east-1. In us-east-1 region, you will get 200 OK, but it is no-op (if
    bucket exists it Amazon S3 will not do anything).
    """
    conn = boto.s3.connect_to_region(DEFAULT_REGION_NAME)
    conn.create_bucket("foobar")
    bucket = conn.create_bucket("foobar")
    bucket.name.should.equal("foobar")


@mock_s3_deprecated
def test_other_region():
    conn = S3Connection("key", "secret", host="s3-website-ap-southeast-2.amazonaws.com")
    conn.create_bucket("foobar", location="ap-southeast-2")
    list(conn.get_bucket("foobar").get_all_keys()).should.equal([])


@mock_s3_deprecated
def test_bucket_deletion():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    # Try to delete a bucket that still has keys
    conn.delete_bucket.when.called_with("foobar").should.throw(S3ResponseError)

    bucket.delete_key("the-key")
    conn.delete_bucket("foobar")

    # Get non-existing bucket
    conn.get_bucket.when.called_with("foobar").should.throw(S3ResponseError)

    # Delete non-existent bucket
    conn.delete_bucket.when.called_with("foobar").should.throw(S3ResponseError)


@mock_s3_deprecated
def test_get_all_buckets():
    conn = boto.connect_s3("the_key", "the_secret")
    conn.create_bucket("foobar")
    conn.create_bucket("foobar2")
    buckets = conn.get_all_buckets()

    buckets.should.have.length_of(2)


@mock_s3
@mock_s3_deprecated
def test_post_to_bucket():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    requests.post(
        "https://foobar.s3.amazonaws.com/", {"key": "the-key", "file": "nothing"}
    )

    bucket.get_key("the-key").get_contents_as_string().should.equal(b"nothing")


@mock_s3
@mock_s3_deprecated
def test_post_with_metadata_to_bucket():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    requests.post(
        "https://foobar.s3.amazonaws.com/",
        {"key": "the-key", "file": "nothing", "x-amz-meta-test": "metadata"},
    )

    bucket.get_key("the-key").get_metadata("test").should.equal("metadata")


@mock_s3_deprecated
def test_delete_missing_key():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    deleted_key = bucket.delete_key("foobar")
    deleted_key.key.should.equal("foobar")


@mock_s3_deprecated
def test_delete_keys():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    Key(bucket=bucket, name="file1").set_contents_from_string("abc")
    Key(bucket=bucket, name="file2").set_contents_from_string("abc")
    Key(bucket=bucket, name="file3").set_contents_from_string("abc")
    Key(bucket=bucket, name="file4").set_contents_from_string("abc")

    result = bucket.delete_keys(["file2", "file3"])
    result.deleted.should.have.length_of(2)
    result.errors.should.have.length_of(0)
    keys = bucket.get_all_keys()
    keys.should.have.length_of(2)
    keys[0].name.should.equal("file1")


@mock_s3_deprecated
def test_delete_keys_invalid():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")

    Key(bucket=bucket, name="file1").set_contents_from_string("abc")
    Key(bucket=bucket, name="file2").set_contents_from_string("abc")
    Key(bucket=bucket, name="file3").set_contents_from_string("abc")
    Key(bucket=bucket, name="file4").set_contents_from_string("abc")

    # non-existing key case
    result = bucket.delete_keys(["abc", "file3"])

    result.deleted.should.have.length_of(1)
    result.errors.should.have.length_of(1)
    keys = bucket.get_all_keys()
    keys.should.have.length_of(3)
    keys[0].name.should.equal("file1")

    # empty keys
    result = bucket.delete_keys([])

    result.deleted.should.have.length_of(0)
    result.errors.should.have.length_of(0)


@mock_s3
def test_boto3_delete_empty_keys_list():
    with pytest.raises(ClientError) as err:
        boto3.client("s3").delete_objects(Bucket="foobar", Delete={"Objects": []})
    assert err.value.response["Error"]["Code"] == "MalformedXML"


@mock_s3_deprecated
def test_bucket_name_with_dot():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("firstname.lastname")

    k = Key(bucket, "somekey")
    k.set_contents_from_string("somedata")


@mock_s3_deprecated
def test_key_with_special_characters():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("test_bucket_name")

    key = Key(bucket, "test_list_keys_2/x?y")
    key.set_contents_from_string("value1")

    key_list = bucket.list("test_list_keys_2/", "/")
    keys = [x for x in key_list]
    keys[0].name.should.equal("test_list_keys_2/x?y")


@mock_s3_deprecated
def test_unicode_key_with_slash():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "/the-key-unîcode/test"
    key.set_contents_from_string("value")

    key = bucket.get_key("/the-key-unîcode/test")
    key.get_contents_as_string().should.equal(b"value")


@mock_s3_deprecated
def test_bucket_key_listing_order():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("test_bucket")
    prefix = "toplevel/"

    def store(name):
        k = Key(bucket, prefix + name)
        k.set_contents_from_string("somedata")

    names = ["x/key", "y.key1", "y.key2", "y.key3", "x/y/key", "x/y/z/key"]

    for name in names:
        store(name)

    delimiter = None
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal(
        [
            "toplevel/x/key",
            "toplevel/x/y/key",
            "toplevel/x/y/z/key",
            "toplevel/y.key1",
            "toplevel/y.key2",
            "toplevel/y.key3",
        ]
    )

    delimiter = "/"
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal(
        ["toplevel/y.key1", "toplevel/y.key2", "toplevel/y.key3", "toplevel/x/"]
    )

    # Test delimiter with no prefix
    delimiter = "/"
    keys = [x.name for x in bucket.list(prefix=None, delimiter=delimiter)]
    keys.should.equal(["toplevel/"])

    delimiter = None
    keys = [x.name for x in bucket.list(prefix + "x", delimiter)]
    keys.should.equal(["toplevel/x/key", "toplevel/x/y/key", "toplevel/x/y/z/key"])

    delimiter = "/"
    keys = [x.name for x in bucket.list(prefix + "x", delimiter)]
    keys.should.equal(["toplevel/x/"])


@mock_s3_deprecated
def test_key_with_reduced_redundancy():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("test_bucket_name")

    key = Key(bucket, "test_rr_key")
    key.set_contents_from_string("value1", reduced_redundancy=True)
    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    list(bucket)[0].storage_class.should.equal("REDUCED_REDUNDANCY")


@mock_s3_deprecated
def test_copy_key_reduced_redundancy():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key("new-key", "foobar", "the-key", storage_class="REDUCED_REDUNDANCY")

    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    keys = dict([(k.name, k) for k in bucket])
    keys["new-key"].storage_class.should.equal("REDUCED_REDUNDANCY")
    keys["the-key"].storage_class.should.equal("STANDARD")


@freeze_time("2012-01-01 12:00:00")
@mock_s3_deprecated
def test_restore_key():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")
    list(bucket)[0].ongoing_restore.should.be.none
    key.restore(1)
    key = bucket.get_key("the-key")
    key.ongoing_restore.should_not.be.none
    key.ongoing_restore.should.be.false
    key.expiry_date.should.equal("Mon, 02 Jan 2012 12:00:00 GMT")
    key.restore(2)
    key = bucket.get_key("the-key")
    key.ongoing_restore.should_not.be.none
    key.ongoing_restore.should.be.false
    key.expiry_date.should.equal("Tue, 03 Jan 2012 12:00:00 GMT")


@freeze_time("2012-01-01 12:00:00")
@mock_s3_deprecated
def test_restore_key_headers():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")
    key.restore(1, headers={"foo": "bar"})
    key = bucket.get_key("the-key")
    key.ongoing_restore.should_not.be.none
    key.ongoing_restore.should.be.false
    key.expiry_date.should.equal("Mon, 02 Jan 2012 12:00:00 GMT")


@mock_s3_deprecated
def test_get_versioning_status():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    d = bucket.get_versioning_status()
    d.should.be.empty

    bucket.configure_versioning(versioning=True)
    d = bucket.get_versioning_status()
    d.shouldnt.be.empty
    d.should.have.key("Versioning").being.equal("Enabled")

    bucket.configure_versioning(versioning=False)
    d = bucket.get_versioning_status()
    d.should.have.key("Versioning").being.equal("Suspended")


@mock_s3_deprecated
def test_key_version():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    bucket.configure_versioning(versioning=True)

    versions = []

    key = Key(bucket)
    key.key = "the-key"
    key.version_id.should.be.none
    key.set_contents_from_string("some string")
    versions.append(key.version_id)
    key.set_contents_from_string("some string")
    versions.append(key.version_id)
    set(versions).should.have.length_of(2)

    key = bucket.get_key("the-key")
    key.version_id.should.equal(versions[-1])


@mock_s3_deprecated
def test_list_versions():
    conn = boto.connect_s3("the_key", "the_secret")
    bucket = conn.create_bucket("foobar")
    bucket.configure_versioning(versioning=True)

    key_versions = []

    key = Key(bucket, "the-key")
    key.version_id.should.be.none
    key.set_contents_from_string("Version 1")
    key_versions.append(key.version_id)
    key.set_contents_from_string("Version 2")
    key_versions.append(key.version_id)
    key_versions.should.have.length_of(2)

    versions = list(bucket.list_versions())
    versions.should.have.length_of(2)

    versions[0].name.should.equal("the-key")
    versions[0].version_id.should.equal(key_versions[1])
    versions[0].get_contents_as_string().should.equal(b"Version 2")

    versions[1].name.should.equal("the-key")
    versions[1].version_id.should.equal(key_versions[0])
    versions[1].get_contents_as_string().should.equal(b"Version 1")

    key = Key(bucket, "the2-key")
    key.set_contents_from_string("Version 1")

    keys = list(bucket.list())
    keys.should.have.length_of(2)
    versions = list(bucket.list_versions(prefix="the2-"))
    versions.should.have.length_of(1)


@mock_s3_deprecated
def test_acl_setting():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("foobar")
    content = b"imafile"
    keyname = "test.txt"

    key = Key(bucket, name=keyname)
    key.content_type = "text/plain"
    key.set_contents_from_string(content)
    key.make_public()

    key = bucket.get_key(keyname)

    assert key.get_contents_as_string() == content

    grants = key.get_acl().acl.grants
    assert any(
        g.uri == "http://acs.amazonaws.com/groups/global/AllUsers"
        and g.permission == "READ"
        for g in grants
    ), grants


@mock_s3_deprecated
def test_acl_setting_via_headers():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("foobar")
    content = b"imafile"
    keyname = "test.txt"

    key = Key(bucket, name=keyname)
    key.content_type = "text/plain"
    key.set_contents_from_string(
        content,
        headers={
            "x-amz-grant-full-control": 'uri="http://acs.amazonaws.com/groups/global/AllUsers"'
        },
    )

    key = bucket.get_key(keyname)

    assert key.get_contents_as_string() == content

    grants = key.get_acl().acl.grants
    assert any(
        g.uri == "http://acs.amazonaws.com/groups/global/AllUsers"
        and g.permission == "FULL_CONTROL"
        for g in grants
    ), grants


@mock_s3_deprecated
def test_acl_switching():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("foobar")
    content = b"imafile"
    keyname = "test.txt"

    key = Key(bucket, name=keyname)
    key.content_type = "text/plain"
    key.set_contents_from_string(content, policy="public-read")
    key.set_acl("private")

    grants = key.get_acl().acl.grants
    assert not any(
        g.uri == "http://acs.amazonaws.com/groups/global/AllUsers"
        and g.permission == "READ"
        for g in grants
    ), grants


@mock_s3_deprecated
def test_bucket_acl_setting():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("foobar")

    bucket.make_public()

    grants = bucket.get_acl().acl.grants
    assert any(
        g.uri == "http://acs.amazonaws.com/groups/global/AllUsers"
        and g.permission == "READ"
        for g in grants
    ), grants


@mock_s3_deprecated
def test_bucket_acl_switching():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("foobar")
    bucket.make_public()

    bucket.set_acl("private")

    grants = bucket.get_acl().acl.grants
    assert not any(
        g.uri == "http://acs.amazonaws.com/groups/global/AllUsers"
        and g.permission == "READ"
        for g in grants
    ), grants


@mock_s3
def test_s3_object_in_public_bucket():
    s3 = boto3.resource("s3")
    bucket = s3.Bucket("test-bucket")
    bucket.create(
        ACL="public-read", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )
    bucket.put_object(Body=b"ABCD", Key="file.txt")

    s3_anonymous = boto3.resource("s3")
    s3_anonymous.meta.client.meta.events.register("choose-signer.s3.*", disable_signing)

    contents = (
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket")
        .get()["Body"]
        .read()
    )
    contents.should.equal(b"ABCD")

    bucket.put_object(ACL="private", Body=b"ABCD", Key="file.txt")

    with pytest.raises(ClientError) as exc:
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket").get()
    exc.value.response["Error"]["Code"].should.equal("403")


@mock_s3
def test_s3_object_in_public_bucket_using_multiple_presigned_urls():
    s3 = boto3.resource("s3")
    bucket = s3.Bucket("test-bucket")
    bucket.create(
        ACL="public-read", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )
    bucket.put_object(Body=b"ABCD", Key="file.txt")

    params = {"Bucket": "test-bucket", "Key": "file.txt"}
    presigned_url = boto3.client("s3").generate_presigned_url(
        "get_object", params, ExpiresIn=900
    )
    for i in range(1, 10):
        response = requests.get(presigned_url)
        assert response.status_code == 200, "Failed on req number {}".format(i)


@mock_s3
def test_streaming_upload_from_file_to_presigned_url():
    s3 = boto3.resource("s3", region_name="us-east-1")
    bucket = s3.Bucket("test-bucket")
    bucket.create()
    bucket.put_object(Body=b"ABCD", Key="file.txt")

    params = {"Bucket": "test-bucket", "Key": "file.txt"}
    presigned_url = boto3.client("s3").generate_presigned_url(
        "put_object", params, ExpiresIn=900
    )
    with open(__file__, "rb") as f:
        response = requests.get(presigned_url, data=f)
    assert response.status_code == 200


@mock_s3
def test_multipart_upload_from_file_to_presigned_url():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    params = {"Bucket": "mybucket", "Key": "file_upload"}
    presigned_url = boto3.client("s3").generate_presigned_url(
        "put_object", params, ExpiresIn=900
    )

    file = open("text.txt", "w")
    file.write("test")
    file.close()
    files = {"upload_file": open("text.txt", "rb")}

    requests.put(presigned_url, files=files)
    resp = s3.get_object(Bucket="mybucket", Key="file_upload")
    data = resp["Body"].read()
    assert data == b"test"
    # cleanup
    os.remove("text.txt")


@mock_s3
def test_s3_object_in_private_bucket():
    s3 = boto3.resource("s3")
    bucket = s3.Bucket("test-bucket")
    bucket.create(
        ACL="private", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )
    bucket.put_object(ACL="private", Body=b"ABCD", Key="file.txt")

    s3_anonymous = boto3.resource("s3")
    s3_anonymous.meta.client.meta.events.register("choose-signer.s3.*", disable_signing)

    with pytest.raises(ClientError) as exc:
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket").get()
    exc.value.response["Error"]["Code"].should.equal("403")

    bucket.put_object(ACL="public-read", Body=b"ABCD", Key="file.txt")
    contents = (
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket")
        .get()["Body"]
        .read()
    )
    contents.should.equal(b"ABCD")


@mock_s3_deprecated
def test_unicode_key():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("mybucket")
    key = Key(bucket)
    key.key = "こんにちは.jpg"
    key.set_contents_from_string("Hello world!")
    assert [listed_key.key for listed_key in bucket.list()] == [key.key]
    fetched_key = bucket.get_key(key.key)
    assert fetched_key.key == key.key
    assert fetched_key.get_contents_as_string().decode("utf-8") == "Hello world!"


@mock_s3_deprecated
def test_unicode_value():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("mybucket")
    key = Key(bucket)
    key.key = "some_key"
    key.set_contents_from_string("こんにちは.jpg")
    list(bucket.list())
    key = bucket.get_key(key.key)
    assert key.get_contents_as_string().decode("utf-8") == "こんにちは.jpg"


@mock_s3_deprecated
def test_setting_content_encoding():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("mybucket")
    key = bucket.new_key("keyname")
    key.set_metadata("Content-Encoding", "gzip")
    compressed_data = "abcdef"
    key.set_contents_from_string(compressed_data)

    key = bucket.get_key("keyname")
    key.content_encoding.should.equal("gzip")


@mock_s3_deprecated
def test_bucket_location():
    conn = boto.s3.connect_to_region("us-west-2")
    bucket = conn.create_bucket("mybucket", location="us-west-2")
    bucket.get_location().should.equal("us-west-2")


@mock_s3
def test_bucket_location_default():
    cli = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    # No LocationConstraint ==> us-east-1
    cli.create_bucket(Bucket=bucket_name)
    cli.get_bucket_location(Bucket=bucket_name)["LocationConstraint"].should.equal(None)


@mock_s3
def test_bucket_location_nondefault():
    cli = boto3.client("s3", region_name="eu-central-1")
    bucket_name = "mybucket"
    # LocationConstraint set for non default regions
    resp = cli.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
    )
    cli.get_bucket_location(Bucket=bucket_name)["LocationConstraint"].should.equal(
        "eu-central-1"
    )


# Test uses current Region to determine whether to throw an error
# Region is retrieved based on current URL
# URL will always be localhost in Server Mode, so can't run it there
if not settings.TEST_SERVER_MODE:

    @mock_s3
    def test_s3_location_should_error_outside_useast1():
        s3 = boto3.client("s3", region_name="eu-west-1")

        bucket_name = "asdfasdfsdfdsfasda"

        with pytest.raises(ClientError) as e:
            s3.create_bucket(Bucket=bucket_name)
        e.value.response["Error"]["Message"].should.equal(
            "The unspecified location constraint is incompatible for the region specific endpoint this request was sent to."
        )

    # All tests for s3-control cannot be run under the server without a modification of the
    # hosts file on your system. This is due to the fact that the URL to the host is in the form of:
    # ACCOUNT_ID.s3-control.amazonaws.com <-- That Account ID part is the problem. If you want to
    # make use of the moto server, update your hosts file for `THE_ACCOUNT_ID_FOR_MOTO.localhost`
    # and this will work fine.

    @mock_s3
    def test_get_public_access_block_for_account():
        from moto.s3.models import ACCOUNT_ID

        client = boto3.client("s3control", region_name="us-west-2")

        # With an invalid account ID:
        with pytest.raises(ClientError) as ce:
            client.get_public_access_block(AccountId="111111111111")
        assert ce.value.response["Error"]["Code"] == "AccessDenied"

        # Without one defined:
        with pytest.raises(ClientError) as ce:
            client.get_public_access_block(AccountId=ACCOUNT_ID)
        assert (
            ce.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"
        )

        # Put a with an invalid account ID:
        with pytest.raises(ClientError) as ce:
            client.put_public_access_block(
                AccountId="111111111111",
                PublicAccessBlockConfiguration={"BlockPublicAcls": True},
            )
        assert ce.value.response["Error"]["Code"] == "AccessDenied"

        # Put with an invalid PAB:
        with pytest.raises(ClientError) as ce:
            client.put_public_access_block(
                AccountId=ACCOUNT_ID, PublicAccessBlockConfiguration={}
            )
        assert ce.value.response["Error"]["Code"] == "InvalidRequest"
        assert (
            "Must specify at least one configuration."
            in ce.value.response["Error"]["Message"]
        )

        # Correct PAB:
        client.put_public_access_block(
            AccountId=ACCOUNT_ID,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Get the correct PAB (for all regions):
        for region in Session().get_available_regions("s3control"):
            region_client = boto3.client("s3control", region_name=region)
            assert region_client.get_public_access_block(AccountId=ACCOUNT_ID)[
                "PublicAccessBlockConfiguration"
            ] == {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }

        # Delete with an invalid account ID:
        with pytest.raises(ClientError) as ce:
            client.delete_public_access_block(AccountId="111111111111")
        assert ce.value.response["Error"]["Code"] == "AccessDenied"

        # Delete successfully:
        client.delete_public_access_block(AccountId=ACCOUNT_ID)

        # Confirm that it's deleted:
        with pytest.raises(ClientError) as ce:
            client.get_public_access_block(AccountId=ACCOUNT_ID)
        assert (
            ce.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"
        )

    @mock_s3
    @mock_config
    def test_config_list_account_pab():
        from moto.s3.models import ACCOUNT_ID

        client = boto3.client("s3control", region_name="us-west-2")
        config_client = boto3.client("config", region_name="us-west-2")

        # Create the aggregator:
        account_aggregation_source = {
            "AccountIds": [ACCOUNT_ID],
            "AllAwsRegions": True,
        }
        config_client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[account_aggregation_source],
        )

        # Without a PAB in place:
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock"
        )
        assert not result["resourceIdentifiers"]
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
        )
        assert not result["ResourceIdentifiers"]

        # Create a PAB:
        client.put_public_access_block(
            AccountId=ACCOUNT_ID,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Test that successful queries work (non-aggregated):
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock"
        )
        assert result["resourceIdentifiers"] == [
            {
                "resourceType": "AWS::S3::AccountPublicAccessBlock",
                "resourceId": ACCOUNT_ID,
            }
        ]
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock",
            resourceIds=[ACCOUNT_ID, "nope"],
        )
        assert result["resourceIdentifiers"] == [
            {
                "resourceType": "AWS::S3::AccountPublicAccessBlock",
                "resourceId": ACCOUNT_ID,
            }
        ]
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock", resourceName=""
        )
        assert result["resourceIdentifiers"] == [
            {
                "resourceType": "AWS::S3::AccountPublicAccessBlock",
                "resourceId": ACCOUNT_ID,
            }
        ]

        # Test that successful queries work (aggregated):
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
        )
        regions = {region for region in Session().get_available_regions("config")}
        for r in result["ResourceIdentifiers"]:
            regions.remove(r.pop("SourceRegion"))
            assert r == {
                "ResourceType": "AWS::S3::AccountPublicAccessBlock",
                "SourceAccountId": ACCOUNT_ID,
                "ResourceId": ACCOUNT_ID,
            }

        # Just check that the len is the same -- this should be reasonable
        regions = {region for region in Session().get_available_regions("config")}
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"ResourceName": ""},
        )
        assert len(regions) == len(result["ResourceIdentifiers"])
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"ResourceName": "", "ResourceId": ACCOUNT_ID},
        )
        assert len(regions) == len(result["ResourceIdentifiers"])
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={
                "ResourceName": "",
                "ResourceId": ACCOUNT_ID,
                "Region": "us-west-2",
            },
        )
        assert (
            result["ResourceIdentifiers"][0]["SourceRegion"] == "us-west-2"
            and len(result["ResourceIdentifiers"]) == 1
        )

        # Test aggregator pagination:
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Limit=1,
        )
        regions = sorted(
            [region for region in Session().get_available_regions("config")]
        )
        assert result["ResourceIdentifiers"][0] == {
            "ResourceType": "AWS::S3::AccountPublicAccessBlock",
            "SourceAccountId": ACCOUNT_ID,
            "ResourceId": ACCOUNT_ID,
            "SourceRegion": regions[0],
        }
        assert result["NextToken"] == regions[1]

        # Get the next region:
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Limit=1,
            NextToken=regions[1],
        )
        assert result["ResourceIdentifiers"][0] == {
            "ResourceType": "AWS::S3::AccountPublicAccessBlock",
            "SourceAccountId": ACCOUNT_ID,
            "ResourceId": ACCOUNT_ID,
            "SourceRegion": regions[1],
        }

        # Non-aggregated with incorrect info:
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock", resourceName="nope"
        )
        assert not result["resourceIdentifiers"]
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock", resourceIds=["nope"]
        )
        assert not result["resourceIdentifiers"]

        # Aggregated with incorrect info:
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"ResourceName": "nope"},
        )
        assert not result["ResourceIdentifiers"]
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"ResourceId": "nope"},
        )
        assert not result["ResourceIdentifiers"]
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"Region": "Nope"},
        )
        assert not result["ResourceIdentifiers"]

    @mock_s3
    @mock_config
    def test_config_get_account_pab():
        from moto.s3.models import ACCOUNT_ID

        client = boto3.client("s3control", region_name="us-west-2")
        config_client = boto3.client("config", region_name="us-west-2")

        # Create the aggregator:
        account_aggregation_source = {
            "AccountIds": [ACCOUNT_ID],
            "AllAwsRegions": True,
        }
        config_client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[account_aggregation_source],
        )

        # Without a PAB in place:
        with pytest.raises(ClientError) as ce:
            config_client.get_resource_config_history(
                resourceType="AWS::S3::AccountPublicAccessBlock", resourceId=ACCOUNT_ID
            )
        assert ce.value.response["Error"]["Code"] == "ResourceNotDiscoveredException"
        # aggregate
        result = config_client.batch_get_resource_config(
            resourceKeys=[
                {
                    "resourceType": "AWS::S3::AccountPublicAccessBlock",
                    "resourceId": "ACCOUNT_ID",
                }
            ]
        )
        assert not result["baseConfigurationItems"]
        result = config_client.batch_get_aggregate_resource_config(
            ConfigurationAggregatorName="testing",
            ResourceIdentifiers=[
                {
                    "SourceAccountId": ACCOUNT_ID,
                    "SourceRegion": "us-west-2",
                    "ResourceId": ACCOUNT_ID,
                    "ResourceType": "AWS::S3::AccountPublicAccessBlock",
                    "ResourceName": "",
                }
            ],
        )
        assert not result["BaseConfigurationItems"]

        # Create a PAB:
        client.put_public_access_block(
            AccountId=ACCOUNT_ID,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Get the proper config:
        proper_config = {
            "blockPublicAcls": True,
            "ignorePublicAcls": True,
            "blockPublicPolicy": True,
            "restrictPublicBuckets": True,
        }
        result = config_client.get_resource_config_history(
            resourceType="AWS::S3::AccountPublicAccessBlock", resourceId=ACCOUNT_ID
        )
        assert (
            json.loads(result["configurationItems"][0]["configuration"])
            == proper_config
        )
        assert (
            result["configurationItems"][0]["accountId"]
            == result["configurationItems"][0]["resourceId"]
            == ACCOUNT_ID
        )
        result = config_client.batch_get_resource_config(
            resourceKeys=[
                {
                    "resourceType": "AWS::S3::AccountPublicAccessBlock",
                    "resourceId": ACCOUNT_ID,
                }
            ]
        )
        assert len(result["baseConfigurationItems"]) == 1
        assert (
            json.loads(result["baseConfigurationItems"][0]["configuration"])
            == proper_config
        )
        assert (
            result["baseConfigurationItems"][0]["accountId"]
            == result["baseConfigurationItems"][0]["resourceId"]
            == ACCOUNT_ID
        )

        for region in Session().get_available_regions("s3control"):
            result = config_client.batch_get_aggregate_resource_config(
                ConfigurationAggregatorName="testing",
                ResourceIdentifiers=[
                    {
                        "SourceAccountId": ACCOUNT_ID,
                        "SourceRegion": region,
                        "ResourceId": ACCOUNT_ID,
                        "ResourceType": "AWS::S3::AccountPublicAccessBlock",
                        "ResourceName": "",
                    }
                ],
            )
            assert len(result["BaseConfigurationItems"]) == 1
            assert (
                json.loads(result["BaseConfigurationItems"][0]["configuration"])
                == proper_config
            )


@mock_s3_deprecated
def test_ranged_get():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("mybucket")
    key = Key(bucket)
    key.key = "bigkey"
    rep = b"0123456789"
    key.set_contents_from_string(rep * 10)

    # Implicitly bounded range requests.
    key.get_contents_as_string(headers={"Range": "bytes=0-"}).should.equal(rep * 10)
    key.get_contents_as_string(headers={"Range": "bytes=50-"}).should.equal(rep * 5)
    key.get_contents_as_string(headers={"Range": "bytes=99-"}).should.equal(b"9")

    # Explicitly bounded range requests starting from the first byte.
    key.get_contents_as_string(headers={"Range": "bytes=0-0"}).should.equal(b"0")
    key.get_contents_as_string(headers={"Range": "bytes=0-49"}).should.equal(rep * 5)
    key.get_contents_as_string(headers={"Range": "bytes=0-99"}).should.equal(rep * 10)
    key.get_contents_as_string(headers={"Range": "bytes=0-100"}).should.equal(rep * 10)
    key.get_contents_as_string(headers={"Range": "bytes=0-700"}).should.equal(rep * 10)

    # Explicitly bounded range requests starting from the / a middle byte.
    key.get_contents_as_string(headers={"Range": "bytes=50-54"}).should.equal(rep[:5])
    key.get_contents_as_string(headers={"Range": "bytes=50-99"}).should.equal(rep * 5)
    key.get_contents_as_string(headers={"Range": "bytes=50-100"}).should.equal(rep * 5)
    key.get_contents_as_string(headers={"Range": "bytes=50-700"}).should.equal(rep * 5)

    # Explicitly bounded range requests starting from the last byte.
    key.get_contents_as_string(headers={"Range": "bytes=99-99"}).should.equal(b"9")
    key.get_contents_as_string(headers={"Range": "bytes=99-100"}).should.equal(b"9")
    key.get_contents_as_string(headers={"Range": "bytes=99-700"}).should.equal(b"9")

    # Suffix range requests.
    key.get_contents_as_string(headers={"Range": "bytes=-1"}).should.equal(b"9")
    key.get_contents_as_string(headers={"Range": "bytes=-60"}).should.equal(rep * 6)
    key.get_contents_as_string(headers={"Range": "bytes=-100"}).should.equal(rep * 10)
    key.get_contents_as_string(headers={"Range": "bytes=-101"}).should.equal(rep * 10)
    key.get_contents_as_string(headers={"Range": "bytes=-700"}).should.equal(rep * 10)

    key.size.should.equal(100)


@mock_s3_deprecated
def test_policy():
    conn = boto.connect_s3()
    bucket_name = "mybucket"
    bucket = conn.create_bucket(bucket_name)

    policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Id": "PutObjPolicy",
            "Statement": [
                {
                    "Sid": "DenyUnEncryptedObjectUploads",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::{bucket_name}/*".format(
                        bucket_name=bucket_name
                    ),
                    "Condition": {
                        "StringNotEquals": {
                            "s3:x-amz-server-side-encryption": "aws:kms"
                        }
                    },
                }
            ],
        }
    )

    with pytest.raises(S3ResponseError) as err:
        bucket.get_policy()

    ex = err.value
    ex.box_usage.should.be.none
    ex.error_code.should.equal("NoSuchBucketPolicy")
    ex.message.should.equal("The bucket policy does not exist")
    ex.reason.should.equal("Not Found")
    ex.resource.should.be.none
    ex.status.should.equal(404)
    ex.body.should.contain(bucket_name)
    ex.request_id.should_not.be.none

    bucket.set_policy(policy).should.be.true

    bucket = conn.get_bucket(bucket_name)

    bucket.get_policy().decode("utf-8").should.equal(policy)

    bucket.delete_policy()

    with pytest.raises(S3ResponseError) as err:
        bucket.get_policy()


@mock_s3_deprecated
def test_website_configuration_xml():
    conn = boto.connect_s3()
    bucket = conn.create_bucket("test-bucket")
    bucket.set_website_configuration_xml(TEST_XML)
    bucket.get_website_configuration_xml().should.equal(TEST_XML)


@mock_s3_deprecated
def test_key_with_trailing_slash_in_ordinary_calling_format():
    conn = boto.connect_s3(
        "access_key",
        "secret_key",
        calling_format=boto.s3.connection.OrdinaryCallingFormat(),
    )
    bucket = conn.create_bucket("test_bucket_name")

    key_name = "key_with_slash/"

    key = Key(bucket, key_name)
    key.set_contents_from_string("some value")

    [k.name for k in bucket.get_all_keys()].should.contain(key_name)


@mock_s3
def test_boto3_key_etag():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    s3.put_object(Bucket="mybucket", Key="steve", Body=b"is awesome")
    resp = s3.get_object(Bucket="mybucket", Key="steve")
    resp["ETag"].should.equal('"d32bda93738f7e03adb22e66c90fbc04"')


@mock_s3
def test_website_redirect_location():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    s3.put_object(Bucket="mybucket", Key="steve", Body=b"is awesome")
    resp = s3.get_object(Bucket="mybucket", Key="steve")
    resp.get("WebsiteRedirectLocation").should.be.none

    url = "https://github.com/spulec/moto"
    s3.put_object(
        Bucket="mybucket", Key="steve", Body=b"is awesome", WebsiteRedirectLocation=url
    )
    resp = s3.get_object(Bucket="mybucket", Key="steve")
    resp["WebsiteRedirectLocation"].should.equal(url)


@mock_s3
def test_delimiter_optional_in_response():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    s3.put_object(Bucket="mybucket", Key="one", Body=b"1")
    resp = s3.list_objects(Bucket="mybucket", MaxKeys=1)
    assert resp.get("Delimiter") is None
    resp = s3.list_objects(Bucket="mybucket", MaxKeys=1, Delimiter="/")
    assert resp.get("Delimiter") == "/"


@mock_s3
def test_boto3_list_objects_truncated_response():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    s3.put_object(Bucket="mybucket", Key="one", Body=b"1")
    s3.put_object(Bucket="mybucket", Key="two", Body=b"22")
    s3.put_object(Bucket="mybucket", Key="three", Body=b"333")

    # First list
    resp = s3.list_objects(Bucket="mybucket", MaxKeys=1)
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "one"
    assert resp["MaxKeys"] == 1
    assert resp["IsTruncated"] == True
    assert resp.get("Prefix") is None
    assert resp.get("Delimiter") is None
    assert "NextMarker" in resp

    next_marker = resp["NextMarker"]

    # Second list
    resp = s3.list_objects(Bucket="mybucket", MaxKeys=1, Marker=next_marker)
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "three"
    assert resp["MaxKeys"] == 1
    assert resp["IsTruncated"] == True
    assert resp.get("Prefix") is None
    assert resp.get("Delimiter") is None
    assert "NextMarker" in resp

    next_marker = resp["NextMarker"]

    # Third list
    resp = s3.list_objects(Bucket="mybucket", MaxKeys=1, Marker=next_marker)
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "two"
    assert resp["MaxKeys"] == 1
    assert resp["IsTruncated"] == False
    assert resp.get("Prefix") is None
    assert resp.get("Delimiter") is None
    assert "NextMarker" not in resp


@mock_s3
def test_boto3_list_keys_xml_escaped():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    key_name = "Q&A.txt"
    s3.put_object(Bucket="mybucket", Key=key_name, Body=b"is awesome")

    resp = s3.list_objects_v2(Bucket="mybucket", Prefix=key_name)

    assert resp["Contents"][0]["Key"] == key_name
    assert resp["KeyCount"] == 1
    assert resp["MaxKeys"] == 1000
    assert resp["Prefix"] == key_name
    assert resp["IsTruncated"] == False
    assert "Delimiter" not in resp
    assert "StartAfter" not in resp
    assert "NextContinuationToken" not in resp
    assert "Owner" not in resp["Contents"][0]


@mock_s3
def test_boto3_list_objects_v2_common_prefix_pagination():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    max_keys = 1
    keys = ["test/{i}/{i}".format(i=i) for i in range(3)]
    for key in keys:
        s3.put_object(Bucket="mybucket", Key=key, Body=b"v")

    prefixes = []
    args = {
        "Bucket": "mybucket",
        "Delimiter": "/",
        "Prefix": "test/",
        "MaxKeys": max_keys,
    }
    resp = {"IsTruncated": True}
    while resp.get("IsTruncated", False):
        if "NextContinuationToken" in resp:
            args["ContinuationToken"] = resp["NextContinuationToken"]
        resp = s3.list_objects_v2(**args)
        if "CommonPrefixes" in resp:
            assert len(resp["CommonPrefixes"]) == max_keys
            prefixes.extend(i["Prefix"] for i in resp["CommonPrefixes"])

    assert prefixes == [k[: k.rindex("/") + 1] for k in keys]


@mock_s3
def test_boto3_list_objects_v2_common_invalid_continuation_token():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    max_keys = 1
    keys = ["test/{i}/{i}".format(i=i) for i in range(3)]
    for key in keys:
        s3.put_object(Bucket="mybucket", Key=key, Body=b"v")

    args = {
        "Bucket": "mybucket",
        "Delimiter": "/",
        "Prefix": "test/",
        "MaxKeys": max_keys,
        "ContinuationToken": "",
    }

    with pytest.raises(botocore.exceptions.ClientError) as exc:
        s3.list_objects_v2(**args)
    exc.value.response["Error"]["Code"].should.equal("InvalidArgument")
    exc.value.response["Error"]["Message"].should.equal(
        "The continuation token provided is incorrect"
    )


@mock_s3
def test_boto3_list_objects_v2_truncated_response():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    s3.put_object(Bucket="mybucket", Key="one", Body=b"1")
    s3.put_object(Bucket="mybucket", Key="two", Body=b"22")
    s3.put_object(Bucket="mybucket", Key="three", Body=b"333")

    # First list
    resp = s3.list_objects_v2(Bucket="mybucket", MaxKeys=1)
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "one"
    assert resp["MaxKeys"] == 1
    assert resp["Prefix"] == ""
    assert resp["KeyCount"] == 1
    assert resp["IsTruncated"] == True
    assert "Delimiter" not in resp
    assert "StartAfter" not in resp
    assert "Owner" not in listed_object  # owner info was not requested

    next_token = resp["NextContinuationToken"]

    # Second list
    resp = s3.list_objects_v2(
        Bucket="mybucket", MaxKeys=1, ContinuationToken=next_token
    )
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "three"
    assert resp["MaxKeys"] == 1
    assert resp["Prefix"] == ""
    assert resp["KeyCount"] == 1
    assert resp["IsTruncated"] == True
    assert "Delimiter" not in resp
    assert "StartAfter" not in resp
    assert "Owner" not in listed_object

    next_token = resp["NextContinuationToken"]

    # Third list
    resp = s3.list_objects_v2(
        Bucket="mybucket", MaxKeys=1, ContinuationToken=next_token
    )
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "two"
    assert resp["MaxKeys"] == 1
    assert resp["Prefix"] == ""
    assert resp["KeyCount"] == 1
    assert resp["IsTruncated"] == False
    assert "Delimiter" not in resp
    assert "Owner" not in listed_object
    assert "StartAfter" not in resp
    assert "NextContinuationToken" not in resp


@mock_s3
def test_boto3_list_objects_v2_truncated_response_start_after():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    s3.put_object(Bucket="mybucket", Key="one", Body=b"1")
    s3.put_object(Bucket="mybucket", Key="two", Body=b"22")
    s3.put_object(Bucket="mybucket", Key="three", Body=b"333")

    # First list
    resp = s3.list_objects_v2(Bucket="mybucket", MaxKeys=1, StartAfter="one")
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "three"
    assert resp["MaxKeys"] == 1
    assert resp["Prefix"] == ""
    assert resp["KeyCount"] == 1
    assert resp["IsTruncated"] == True
    assert resp["StartAfter"] == "one"
    assert "Delimiter" not in resp
    assert "Owner" not in listed_object

    next_token = resp["NextContinuationToken"]

    # Second list
    # The ContinuationToken must take precedence over StartAfter.
    resp = s3.list_objects_v2(
        Bucket="mybucket", MaxKeys=1, StartAfter="one", ContinuationToken=next_token
    )
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "two"
    assert resp["MaxKeys"] == 1
    assert resp["Prefix"] == ""
    assert resp["KeyCount"] == 1
    assert resp["IsTruncated"] == False
    # When ContinuationToken is given, StartAfter is ignored. This also means
    # AWS does not return it in the response.
    assert "StartAfter" not in resp
    assert "Delimiter" not in resp
    assert "Owner" not in listed_object


@mock_s3
def test_boto3_list_objects_v2_fetch_owner():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    s3.put_object(Bucket="mybucket", Key="one", Body=b"11")

    resp = s3.list_objects_v2(Bucket="mybucket", FetchOwner=True)
    owner = resp["Contents"][0]["Owner"]

    assert "ID" in owner
    assert "DisplayName" in owner
    assert len(owner.keys()) == 2


@mock_s3
def test_boto3_list_objects_v2_truncate_combined_keys_and_folders():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    s3.put_object(Bucket="mybucket", Key="1/2", Body="")
    s3.put_object(Bucket="mybucket", Key="2", Body="")
    s3.put_object(Bucket="mybucket", Key="3/4", Body="")
    s3.put_object(Bucket="mybucket", Key="4", Body="")

    resp = s3.list_objects_v2(Bucket="mybucket", Prefix="", MaxKeys=2, Delimiter="/")
    assert "Delimiter" in resp
    assert resp["IsTruncated"] is True
    assert resp["KeyCount"] == 2
    assert len(resp["Contents"]) == 1
    assert resp["Contents"][0]["Key"] == "2"
    assert len(resp["CommonPrefixes"]) == 1
    assert resp["CommonPrefixes"][0]["Prefix"] == "1/"

    last_tail = resp["NextContinuationToken"]
    resp = s3.list_objects_v2(
        Bucket="mybucket", MaxKeys=2, Prefix="", Delimiter="/", StartAfter=last_tail
    )
    assert resp["KeyCount"] == 2
    assert resp["IsTruncated"] is False
    assert len(resp["Contents"]) == 1
    assert resp["Contents"][0]["Key"] == "4"
    assert len(resp["CommonPrefixes"]) == 1
    assert resp["CommonPrefixes"][0]["Prefix"] == "3/"


@mock_s3
def test_boto3_bucket_create():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="blah")

    s3.Object("blah", "hello.txt").put(Body="some text")

    s3.Object("blah", "hello.txt").get()["Body"].read().decode("utf-8").should.equal(
        "some text"
    )


@mock_s3
def test_bucket_create_duplicate():
    s3 = boto3.resource("s3", region_name="us-west-2")
    s3.create_bucket(
        Bucket="blah", CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
    )
    with pytest.raises(ClientError) as exc:
        s3.create_bucket(
            Bucket="blah", CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
        )
    exc.value.response["Error"]["Code"].should.equal("BucketAlreadyExists")


@mock_s3
def test_bucket_create_force_us_east_1():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3.create_bucket(
            Bucket="blah",
            CreateBucketConfiguration={"LocationConstraint": DEFAULT_REGION_NAME},
        )
    exc.value.response["Error"]["Code"].should.equal("InvalidLocationConstraint")


@mock_s3
def test_boto3_bucket_create_eu_central():
    s3 = boto3.resource("s3", region_name="eu-central-1")
    s3.create_bucket(
        Bucket="blah", CreateBucketConfiguration={"LocationConstraint": "eu-central-1"}
    )

    s3.Object("blah", "hello.txt").put(Body="some text")

    s3.Object("blah", "hello.txt").get()["Body"].read().decode("utf-8").should.equal(
        "some text"
    )


@mock_s3
def test_bucket_create_empty_bucket_configuration_should_return_malformed_xml_error():
    s3 = boto3.resource("s3", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        s3.create_bucket(Bucket="whatever", CreateBucketConfiguration={})
    e.value.response["Error"]["Code"].should.equal("MalformedXML")
    e.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_s3
def test_boto3_head_object():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="blah")

    s3.Object("blah", "hello.txt").put(Body="some text")

    s3.Object("blah", "hello.txt").meta.client.head_object(
        Bucket="blah", Key="hello.txt"
    )

    with pytest.raises(ClientError) as e:
        s3.Object("blah", "hello2.txt").meta.client.head_object(
            Bucket="blah", Key="hello_bad.txt"
        )
    e.value.response["Error"]["Code"].should.equal("404")


@mock_s3
def test_boto3_bucket_deletion():
    cli = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    cli.create_bucket(Bucket="foobar")

    cli.put_object(Bucket="foobar", Key="the-key", Body="some value")

    # Try to delete a bucket that still has keys
    cli.delete_bucket.when.called_with(Bucket="foobar").should.throw(
        cli.exceptions.ClientError,
        (
            "An error occurred (BucketNotEmpty) when calling the DeleteBucket operation: "
            "The bucket you tried to delete is not empty"
        ),
    )

    cli.delete_object(Bucket="foobar", Key="the-key")
    cli.delete_bucket(Bucket="foobar")

    # Get non-existing bucket
    cli.head_bucket.when.called_with(Bucket="foobar").should.throw(
        cli.exceptions.ClientError,
        "An error occurred (404) when calling the HeadBucket operation: Not Found",
    )

    # Delete non-existing bucket
    cli.delete_bucket.when.called_with(Bucket="foobar").should.throw(
        cli.exceptions.NoSuchBucket
    )


@mock_s3
def test_boto3_get_object():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="blah")

    s3.Object("blah", "hello.txt").put(Body="some text")

    s3.Object("blah", "hello.txt").meta.client.head_object(
        Bucket="blah", Key="hello.txt"
    )

    with pytest.raises(ClientError) as e:
        s3.Object("blah", "hello2.txt").get()

    e.value.response["Error"]["Code"].should.equal("NoSuchKey")


@mock_s3
def test_boto3_s3_content_type():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    my_bucket = s3.Bucket("my-cool-bucket")
    my_bucket.create()
    s3_path = "test_s3.py"
    s3 = boto3.resource("s3", verify=False)

    content_type = "text/python-x"
    s3.Object(my_bucket.name, s3_path).put(
        ContentType=content_type, Body=b"some python code", ACL="public-read"
    )

    s3.Object(my_bucket.name, s3_path).content_type.should.equal(content_type)


@mock_s3
def test_boto3_get_missing_object_with_part_number():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="blah")

    with pytest.raises(ClientError) as e:
        s3.Object("blah", "hello.txt").meta.client.head_object(
            Bucket="blah", Key="hello.txt", PartNumber=123
        )

    e.value.response["Error"]["Code"].should.equal("404")


@mock_s3
def test_boto3_head_object_with_versioning():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.create_bucket(Bucket="blah")
    bucket.Versioning().enable()

    old_content = "some text"
    new_content = "some new text"
    s3.Object("blah", "hello.txt").put(Body=old_content)
    s3.Object("blah", "hello.txt").put(Body=new_content)

    versions = list(s3.Bucket("blah").object_versions.all())
    latest = list(filter(lambda item: item.is_latest, versions))[0]
    oldest = list(filter(lambda item: not item.is_latest, versions))[0]

    head_object = s3.Object("blah", "hello.txt").meta.client.head_object(
        Bucket="blah", Key="hello.txt"
    )
    head_object["VersionId"].should.equal(latest.id)
    head_object["ContentLength"].should.equal(len(new_content))

    old_head_object = s3.Object("blah", "hello.txt").meta.client.head_object(
        Bucket="blah", Key="hello.txt", VersionId=oldest.id
    )
    old_head_object["VersionId"].should.equal(oldest.id)
    old_head_object["ContentLength"].should.equal(len(old_content))

    old_head_object["VersionId"].should_not.equal(head_object["VersionId"])


@mock_s3
def test_boto3_copy_object_with_versioning():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(
        Bucket="blah", CreateBucketConfiguration={"LocationConstraint": "eu-west-1"}
    )
    client.put_bucket_versioning(
        Bucket="blah", VersioningConfiguration={"Status": "Enabled"}
    )

    client.put_object(Bucket="blah", Key="test1", Body=b"test1")
    client.put_object(Bucket="blah", Key="test2", Body=b"test2")

    obj1_version = client.get_object(Bucket="blah", Key="test1")["VersionId"]
    obj2_version = client.get_object(Bucket="blah", Key="test2")["VersionId"]

    client.copy_object(
        CopySource={"Bucket": "blah", "Key": "test1"}, Bucket="blah", Key="test2"
    )
    obj2_version_new = client.get_object(Bucket="blah", Key="test2")["VersionId"]

    # Version should be different to previous version
    obj2_version_new.should_not.equal(obj2_version)

    client.copy_object(
        CopySource={"Bucket": "blah", "Key": "test2", "VersionId": obj2_version},
        Bucket="blah",
        Key="test3",
    )
    obj3_version_new = client.get_object(Bucket="blah", Key="test3")["VersionId"]
    obj3_version_new.should_not.equal(obj2_version_new)

    # Copy file that doesn't exist
    with pytest.raises(ClientError) as e:
        client.copy_object(
            CopySource={"Bucket": "blah", "Key": "test4", "VersionId": obj2_version},
            Bucket="blah",
            Key="test5",
        )
    e.value.response["Error"]["Code"].should.equal("404")

    response = client.create_multipart_upload(Bucket="blah", Key="test4")
    upload_id = response["UploadId"]
    response = client.upload_part_copy(
        Bucket="blah",
        Key="test4",
        CopySource={"Bucket": "blah", "Key": "test3", "VersionId": obj3_version_new},
        UploadId=upload_id,
        PartNumber=1,
    )
    etag = response["CopyPartResult"]["ETag"]
    client.complete_multipart_upload(
        Bucket="blah",
        Key="test4",
        UploadId=upload_id,
        MultipartUpload={"Parts": [{"ETag": etag, "PartNumber": 1}]},
    )

    response = client.get_object(Bucket="blah", Key="test4")
    data = response["Body"].read()
    data.should.equal(b"test2")


@mock_s3
def test_s3_abort_multipart_data_with_invalid_upload_and_key():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(Bucket="blah")

    with pytest.raises(Exception) as err:
        client.abort_multipart_upload(
            Bucket="blah", Key="foobar", UploadId="dummy_upload_id"
        )
    err.value.response["Error"]["Code"].should.equal("NoSuchUpload")


@mock_s3
def test_boto3_copy_object_from_unversioned_to_versioned_bucket():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(
        Bucket="src", CreateBucketConfiguration={"LocationConstraint": "eu-west-1"}
    )
    client.create_bucket(
        Bucket="dest", CreateBucketConfiguration={"LocationConstraint": "eu-west-1"}
    )
    client.put_bucket_versioning(
        Bucket="dest", VersioningConfiguration={"Status": "Enabled"}
    )

    client.put_object(Bucket="src", Key="test", Body=b"content")

    obj2_version_new = client.copy_object(
        CopySource={"Bucket": "src", "Key": "test"}, Bucket="dest", Key="test"
    ).get("VersionId")

    # VersionId should be present in the response
    obj2_version_new.should_not.equal(None)


@mock_s3
def test_boto3_copy_object_with_replacement_tagging():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="mybucket")
    client.put_object(
        Bucket="mybucket", Key="original", Body=b"test", Tagging="tag=old"
    )

    client.copy_object(
        CopySource={"Bucket": "mybucket", "Key": "original"},
        Bucket="mybucket",
        Key="copy1",
        TaggingDirective="REPLACE",
        Tagging="tag=new",
    )
    client.copy_object(
        CopySource={"Bucket": "mybucket", "Key": "original"},
        Bucket="mybucket",
        Key="copy2",
        TaggingDirective="COPY",
    )

    tags1 = client.get_object_tagging(Bucket="mybucket", Key="copy1")["TagSet"]
    tags1.should.equal([{"Key": "tag", "Value": "new"}])
    tags2 = client.get_object_tagging(Bucket="mybucket", Key="copy2")["TagSet"]
    tags2.should.equal([{"Key": "tag", "Value": "old"}])


@mock_s3
def test_boto3_deleted_versionings_list():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(Bucket="blah")
    client.put_bucket_versioning(
        Bucket="blah", VersioningConfiguration={"Status": "Enabled"}
    )

    client.put_object(Bucket="blah", Key="test1", Body=b"test1")
    client.put_object(Bucket="blah", Key="test2", Body=b"test2")
    client.delete_objects(Bucket="blah", Delete={"Objects": [{"Key": "test1"}]})

    listed = client.list_objects_v2(Bucket="blah")
    assert len(listed["Contents"]) == 1


@mock_s3
def test_boto3_delete_objects_for_specific_version_id():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="blah")
    client.put_bucket_versioning(
        Bucket="blah", VersioningConfiguration={"Status": "Enabled"}
    )

    client.put_object(Bucket="blah", Key="test1", Body=b"test1a")
    client.put_object(Bucket="blah", Key="test1", Body=b"test1b")

    response = client.list_object_versions(Bucket="blah", Prefix="test1")
    id_to_delete = [v["VersionId"] for v in response["Versions"] if v["IsLatest"]][0]

    response = client.delete_objects(
        Bucket="blah", Delete={"Objects": [{"Key": "test1", "VersionId": id_to_delete}]}
    )
    assert response["Deleted"] == [{"Key": "test1", "VersionId": id_to_delete}]

    listed = client.list_objects_v2(Bucket="blah")
    assert len(listed["Contents"]) == 1


@mock_s3
def test_boto3_delete_versioned_bucket():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(Bucket="blah")
    client.put_bucket_versioning(
        Bucket="blah", VersioningConfiguration={"Status": "Enabled"}
    )

    resp = client.put_object(Bucket="blah", Key="test1", Body=b"test1")
    client.delete_object(Bucket="blah", Key="test1", VersionId=resp["VersionId"])

    client.delete_bucket(Bucket="blah")


@mock_s3
def test_boto3_delete_versioned_bucket_returns_meta():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(Bucket="blah")
    client.put_bucket_versioning(
        Bucket="blah", VersioningConfiguration={"Status": "Enabled"}
    )

    put_resp = client.put_object(Bucket="blah", Key="test1", Body=b"test1")

    # Delete the object
    del_resp = client.delete_object(Bucket="blah", Key="test1")
    assert "DeleteMarker" not in del_resp
    assert del_resp["VersionId"] is not None

    # Delete the delete marker
    del_resp2 = client.delete_object(
        Bucket="blah", Key="test1", VersionId=del_resp["VersionId"]
    )
    assert del_resp2["DeleteMarker"] == True
    assert "VersionId" not in del_resp2


@mock_s3
def test_boto3_get_object_if_modified_since():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.get_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        )
    e = err.value
    e.response["Error"].should.equal({"Code": "304", "Message": "Not Modified"})


@mock_s3
def test_boto3_get_object_if_unmodified_since():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.get_object(
            Bucket=bucket_name,
            Key=key,
            IfUnmodifiedSince=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
        )
    e = err.value
    e.response["Error"]["Code"].should.equal("PreconditionFailed")
    e.response["Error"]["Condition"].should.equal("If-Unmodified-Since")


@mock_s3
def test_boto3_get_object_if_match():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.get_object(
            Bucket=bucket_name, Key=key, IfMatch='"hello"',
        )
    e = err.value
    e.response["Error"]["Code"].should.equal("PreconditionFailed")
    e.response["Error"]["Condition"].should.equal("If-Match")


@mock_s3
def test_boto3_get_object_if_none_match():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    etag = s3.put_object(Bucket=bucket_name, Key=key, Body="test")["ETag"]

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.get_object(
            Bucket=bucket_name, Key=key, IfNoneMatch=etag,
        )
    e = err.value
    e.response["Error"].should.equal({"Code": "304", "Message": "Not Modified"})


@mock_s3
def test_boto3_head_object_if_modified_since():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.head_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        )
    e = err.value
    e.response["Error"].should.equal({"Code": "304", "Message": "Not Modified"})


@mock_s3
def test_boto3_head_object_if_unmodified_since():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.head_object(
            Bucket=bucket_name,
            Key=key,
            IfUnmodifiedSince=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
        )
    e = err.value
    e.response["Error"].should.equal({"Code": "412", "Message": "Precondition Failed"})


@mock_s3
def test_boto3_head_object_if_match():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.head_object(
            Bucket=bucket_name, Key=key, IfMatch='"hello"',
        )
    e = err.value
    e.response["Error"].should.equal({"Code": "412", "Message": "Precondition Failed"})


@mock_s3
def test_boto3_head_object_if_none_match():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    etag = s3.put_object(Bucket=bucket_name, Key=key, Body="test")["ETag"]

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.head_object(
            Bucket=bucket_name, Key=key, IfNoneMatch=etag,
        )
    e = err.value
    e.response["Error"].should.equal({"Code": "304", "Message": "Not Modified"})


@mock_s3
@reduced_min_part_size
def test_boto3_multipart_etag():
    # Create Bucket so that test can run
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    upload_id = s3.create_multipart_upload(Bucket="mybucket", Key="the-key")["UploadId"]
    part1 = b"0" * REDUCED_PART_SIZE
    etags = []
    etags.append(
        s3.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=1,
            UploadId=upload_id,
            Body=part1,
        )["ETag"]
    )
    # last part, can be less than 5 MB
    part2 = b"1"
    etags.append(
        s3.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=2,
            UploadId=upload_id,
            Body=part2,
        )["ETag"]
    )
    s3.complete_multipart_upload(
        Bucket="mybucket",
        Key="the-key",
        UploadId=upload_id,
        MultipartUpload={
            "Parts": [
                {"ETag": etag, "PartNumber": i} for i, etag in enumerate(etags, 1)
            ]
        },
    )
    # we should get both parts as the key contents
    resp = s3.get_object(Bucket="mybucket", Key="the-key")
    resp["ETag"].should.equal(EXPECTED_ETAG)


@mock_s3
@reduced_min_part_size
def test_boto3_multipart_part_size():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    mpu = s3.create_multipart_upload(Bucket="mybucket", Key="the-key")
    mpu_id = mpu["UploadId"]

    parts = []
    n_parts = 10
    for i in range(1, n_parts + 1):
        part_size = REDUCED_PART_SIZE + i
        body = b"1" * part_size
        part = s3.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=i,
            UploadId=mpu_id,
            Body=body,
            ContentLength=len(body),
        )
        parts.append({"PartNumber": i, "ETag": part["ETag"]})

    s3.complete_multipart_upload(
        Bucket="mybucket",
        Key="the-key",
        UploadId=mpu_id,
        MultipartUpload={"Parts": parts},
    )

    for i in range(1, n_parts + 1):
        obj = s3.head_object(Bucket="mybucket", Key="the-key", PartNumber=i)
        assert obj["ContentLength"] == REDUCED_PART_SIZE + i


@mock_s3
def test_boto3_put_object_with_tagging():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3.create_bucket(Bucket=bucket_name)

    s3.put_object(Bucket=bucket_name, Key=key, Body="test", Tagging="foo=bar")

    s3.get_object_tagging(Bucket=bucket_name, Key=key)["TagSet"].should.contain(
        {"Key": "foo", "Value": "bar"}
    )

    s3.delete_object_tagging(Bucket=bucket_name, Key=key)

    s3.get_object_tagging(Bucket=bucket_name, Key=key)["TagSet"].should.equal([])


@mock_s3
def test_boto3_put_bucket_tagging():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    s3.create_bucket(Bucket=bucket_name)

    # With 1 tag:
    resp = s3.put_bucket_tagging(
        Bucket=bucket_name, Tagging={"TagSet": [{"Key": "TagOne", "Value": "ValueOne"}]}
    )
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # With multiple tags:
    resp = s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            "TagSet": [
                {"Key": "TagOne", "Value": "ValueOne"},
                {"Key": "TagTwo", "Value": "ValueTwo"},
            ]
        },
    )

    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # No tags is also OK:
    resp = s3.put_bucket_tagging(Bucket=bucket_name, Tagging={"TagSet": []})
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # With duplicate tag keys:
    with pytest.raises(ClientError) as err:
        resp = s3.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={
                "TagSet": [
                    {"Key": "TagOne", "Value": "ValueOne"},
                    {"Key": "TagOne", "Value": "ValueOneAgain"},
                ]
            },
        )
    e = err.value
    e.response["Error"]["Code"].should.equal("InvalidTag")
    e.response["Error"]["Message"].should.equal(
        "Cannot provide multiple Tags with the same key"
    )

    # Cannot put tags that are "system" tags - i.e. tags that start with "aws:"
    with pytest.raises(ClientError) as ce:
        s3.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={"TagSet": [{"Key": "aws:sometag", "Value": "nope"}]},
        )
    e = ce.value
    e.response["Error"]["Code"].should.equal("InvalidTag")
    e.response["Error"]["Message"].should.equal(
        "System tags cannot be added/updated by requester"
    )

    # This is OK though:
    s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={"TagSet": [{"Key": "something:aws:stuff", "Value": "this is fine"}]},
    )


@mock_s3
def test_boto3_get_bucket_tagging():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            "TagSet": [
                {"Key": "TagOne", "Value": "ValueOne"},
                {"Key": "TagTwo", "Value": "ValueTwo"},
            ]
        },
    )

    # Get the tags for the bucket:
    resp = s3.get_bucket_tagging(Bucket=bucket_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(resp["TagSet"]).should.equal(2)

    # With no tags:
    s3.put_bucket_tagging(Bucket=bucket_name, Tagging={"TagSet": []})

    with pytest.raises(ClientError) as err:
        s3.get_bucket_tagging(Bucket=bucket_name)

    e = err.value
    e.response["Error"]["Code"].should.equal("NoSuchTagSet")
    e.response["Error"]["Message"].should.equal("The TagSet does not exist")


@mock_s3
def test_boto3_delete_bucket_tagging():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    s3.create_bucket(Bucket=bucket_name)

    s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            "TagSet": [
                {"Key": "TagOne", "Value": "ValueOne"},
                {"Key": "TagTwo", "Value": "ValueTwo"},
            ]
        },
    )

    resp = s3.delete_bucket_tagging(Bucket=bucket_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(204)

    with pytest.raises(ClientError) as err:
        s3.get_bucket_tagging(Bucket=bucket_name)

    e = err.value
    e.response["Error"]["Code"].should.equal("NoSuchTagSet")
    e.response["Error"]["Message"].should.equal("The TagSet does not exist")


@mock_s3
def test_boto3_put_bucket_cors():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    s3.create_bucket(Bucket=bucket_name)

    resp = s3.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedOrigins": ["*"],
                    "AllowedMethods": ["GET", "POST"],
                    "AllowedHeaders": ["Authorization"],
                    "ExposeHeaders": ["x-amz-request-id"],
                    "MaxAgeSeconds": 123,
                },
                {
                    "AllowedOrigins": ["*"],
                    "AllowedMethods": ["PUT"],
                    "AllowedHeaders": ["Authorization"],
                    "ExposeHeaders": ["x-amz-request-id"],
                    "MaxAgeSeconds": 123,
                },
            ]
        },
    )

    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    with pytest.raises(ClientError) as err:
        s3.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration={
                "CORSRules": [
                    {"AllowedOrigins": ["*"], "AllowedMethods": ["NOTREAL", "POST"]}
                ]
            },
        )
    e = err.value
    e.response["Error"]["Code"].should.equal("InvalidRequest")
    e.response["Error"]["Message"].should.equal(
        "Found unsupported HTTP method in CORS config. " "Unsupported method is NOTREAL"
    )

    with pytest.raises(ClientError) as err:
        s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration={"CORSRules": []})
    e = err.value
    e.response["Error"]["Code"].should.equal("MalformedXML")

    # And 101:
    many_rules = [{"AllowedOrigins": ["*"], "AllowedMethods": ["GET"]}] * 101
    with pytest.raises(ClientError) as err:
        s3.put_bucket_cors(
            Bucket=bucket_name, CORSConfiguration={"CORSRules": many_rules}
        )
    e = err.value
    e.response["Error"]["Code"].should.equal("MalformedXML")


@mock_s3
def test_boto3_get_bucket_cors():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    s3.create_bucket(Bucket=bucket_name)

    # Without CORS:
    with pytest.raises(ClientError) as err:
        s3.get_bucket_cors(Bucket=bucket_name)

    e = err.value
    e.response["Error"]["Code"].should.equal("NoSuchCORSConfiguration")
    e.response["Error"]["Message"].should.equal("The CORS configuration does not exist")

    s3.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedOrigins": ["*"],
                    "AllowedMethods": ["GET", "POST"],
                    "AllowedHeaders": ["Authorization"],
                    "ExposeHeaders": ["x-amz-request-id"],
                    "MaxAgeSeconds": 123,
                },
                {
                    "AllowedOrigins": ["*"],
                    "AllowedMethods": ["PUT"],
                    "AllowedHeaders": ["Authorization"],
                    "ExposeHeaders": ["x-amz-request-id"],
                    "MaxAgeSeconds": 123,
                },
            ]
        },
    )

    resp = s3.get_bucket_cors(Bucket=bucket_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(resp["CORSRules"]).should.equal(2)


@mock_s3
def test_boto3_delete_bucket_cors():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration={
            "CORSRules": [{"AllowedOrigins": ["*"], "AllowedMethods": ["GET"]}]
        },
    )

    resp = s3.delete_bucket_cors(Bucket=bucket_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(204)

    # Verify deletion:
    with pytest.raises(ClientError) as err:
        s3.get_bucket_cors(Bucket=bucket_name)

    e = err.value
    e.response["Error"]["Code"].should.equal("NoSuchCORSConfiguration")
    e.response["Error"]["Message"].should.equal("The CORS configuration does not exist")


@mock_s3
def test_put_bucket_acl_body():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="bucket")
    bucket_owner = s3.get_bucket_acl(Bucket="bucket")["Owner"]
    s3.put_bucket_acl(
        Bucket="bucket",
        AccessControlPolicy={
            "Grants": [
                {
                    "Grantee": {
                        "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                        "Type": "Group",
                    },
                    "Permission": "WRITE",
                },
                {
                    "Grantee": {
                        "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                        "Type": "Group",
                    },
                    "Permission": "READ_ACP",
                },
            ],
            "Owner": bucket_owner,
        },
    )

    result = s3.get_bucket_acl(Bucket="bucket")
    assert len(result["Grants"]) == 2
    for g in result["Grants"]:
        assert g["Grantee"]["URI"] == "http://acs.amazonaws.com/groups/s3/LogDelivery"
        assert g["Grantee"]["Type"] == "Group"
        assert g["Permission"] in ["WRITE", "READ_ACP"]

    # With one:
    s3.put_bucket_acl(
        Bucket="bucket",
        AccessControlPolicy={
            "Grants": [
                {
                    "Grantee": {
                        "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                        "Type": "Group",
                    },
                    "Permission": "WRITE",
                }
            ],
            "Owner": bucket_owner,
        },
    )
    result = s3.get_bucket_acl(Bucket="bucket")
    assert len(result["Grants"]) == 1

    # With no owner:
    with pytest.raises(ClientError) as err:
        s3.put_bucket_acl(
            Bucket="bucket",
            AccessControlPolicy={
                "Grants": [
                    {
                        "Grantee": {
                            "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                            "Type": "Group",
                        },
                        "Permission": "WRITE",
                    }
                ]
            },
        )
    assert err.value.response["Error"]["Code"] == "MalformedACLError"

    # With incorrect permission:
    with pytest.raises(ClientError) as err:
        s3.put_bucket_acl(
            Bucket="bucket",
            AccessControlPolicy={
                "Grants": [
                    {
                        "Grantee": {
                            "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                            "Type": "Group",
                        },
                        "Permission": "lskjflkasdjflkdsjfalisdjflkdsjf",
                    }
                ],
                "Owner": bucket_owner,
            },
        )
    assert err.value.response["Error"]["Code"] == "MalformedACLError"

    # Clear the ACLs:
    result = s3.put_bucket_acl(
        Bucket="bucket", AccessControlPolicy={"Grants": [], "Owner": bucket_owner}
    )
    assert not result.get("Grants")


@mock_s3
def test_object_acl_with_presigned_post():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    bucket_name = "imageS3Bucket"
    object_name = "text.txt"
    fields = {"acl": "public-read"}
    file = open("text.txt", "w")
    file.write("test")
    file.close()

    s3.create_bucket(Bucket=bucket_name)
    response = s3.generate_presigned_post(
        bucket_name, object_name, Fields=fields, ExpiresIn=60000
    )

    with open(object_name, "rb") as f:
        files = {"file": (object_name, f)}
        requests.post(response["url"], data=response["fields"], files=files)

    response = s3.get_object_acl(Bucket=bucket_name, Key=object_name)

    assert "Grants" in response
    assert len(response["Grants"]) == 2
    assert response["Grants"][1]["Permission"] == "READ"

    response = s3.get_object(Bucket=bucket_name, Key=object_name)

    assert "ETag" in response
    assert "Body" in response
    os.remove("text.txt")


@mock_s3
def test_put_bucket_notification():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="bucket")

    # With no configuration:
    result = s3.get_bucket_notification(Bucket="bucket")
    assert not result.get("TopicConfigurations")
    assert not result.get("QueueConfigurations")
    assert not result.get("LambdaFunctionConfigurations")

    # Place proper topic configuration:
    s3.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "TopicConfigurations": [
                {
                    "TopicArn": "arn:aws:sns:us-east-1:012345678910:mytopic",
                    "Events": ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
                },
                {
                    "TopicArn": "arn:aws:sns:us-east-1:012345678910:myothertopic",
                    "Events": ["s3:ObjectCreated:*"],
                    "Filter": {
                        "Key": {
                            "FilterRules": [
                                {"Name": "prefix", "Value": "images/"},
                                {"Name": "suffix", "Value": "png"},
                            ]
                        }
                    },
                },
            ]
        },
    )

    # Verify to completion:
    result = s3.get_bucket_notification_configuration(Bucket="bucket")
    assert len(result["TopicConfigurations"]) == 2
    assert not result.get("QueueConfigurations")
    assert not result.get("LambdaFunctionConfigurations")
    assert (
        result["TopicConfigurations"][0]["TopicArn"]
        == "arn:aws:sns:us-east-1:012345678910:mytopic"
    )
    assert (
        result["TopicConfigurations"][1]["TopicArn"]
        == "arn:aws:sns:us-east-1:012345678910:myothertopic"
    )
    assert len(result["TopicConfigurations"][0]["Events"]) == 2
    assert len(result["TopicConfigurations"][1]["Events"]) == 1
    assert result["TopicConfigurations"][0]["Events"][0] == "s3:ObjectCreated:*"
    assert result["TopicConfigurations"][0]["Events"][1] == "s3:ObjectRemoved:*"
    assert result["TopicConfigurations"][1]["Events"][0] == "s3:ObjectCreated:*"
    assert result["TopicConfigurations"][0]["Id"]
    assert result["TopicConfigurations"][1]["Id"]
    assert not result["TopicConfigurations"][0].get("Filter")
    assert len(result["TopicConfigurations"][1]["Filter"]["Key"]["FilterRules"]) == 2
    assert (
        result["TopicConfigurations"][1]["Filter"]["Key"]["FilterRules"][0]["Name"]
        == "prefix"
    )
    assert (
        result["TopicConfigurations"][1]["Filter"]["Key"]["FilterRules"][0]["Value"]
        == "images/"
    )
    assert (
        result["TopicConfigurations"][1]["Filter"]["Key"]["FilterRules"][1]["Name"]
        == "suffix"
    )
    assert (
        result["TopicConfigurations"][1]["Filter"]["Key"]["FilterRules"][1]["Value"]
        == "png"
    )

    # Place proper queue configuration:
    s3.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "QueueConfigurations": [
                {
                    "Id": "SomeID",
                    "QueueArn": "arn:aws:sqs:us-east-1:012345678910:myQueue",
                    "Events": ["s3:ObjectCreated:*"],
                    "Filter": {
                        "Key": {"FilterRules": [{"Name": "prefix", "Value": "images/"}]}
                    },
                }
            ]
        },
    )
    result = s3.get_bucket_notification_configuration(Bucket="bucket")
    assert len(result["QueueConfigurations"]) == 1
    assert not result.get("TopicConfigurations")
    assert not result.get("LambdaFunctionConfigurations")
    assert result["QueueConfigurations"][0]["Id"] == "SomeID"
    assert (
        result["QueueConfigurations"][0]["QueueArn"]
        == "arn:aws:sqs:us-east-1:012345678910:myQueue"
    )
    assert result["QueueConfigurations"][0]["Events"][0] == "s3:ObjectCreated:*"
    assert len(result["QueueConfigurations"][0]["Events"]) == 1
    assert len(result["QueueConfigurations"][0]["Filter"]["Key"]["FilterRules"]) == 1
    assert (
        result["QueueConfigurations"][0]["Filter"]["Key"]["FilterRules"][0]["Name"]
        == "prefix"
    )
    assert (
        result["QueueConfigurations"][0]["Filter"]["Key"]["FilterRules"][0]["Value"]
        == "images/"
    )

    # Place proper Lambda configuration:
    s3.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [
                {
                    "LambdaFunctionArn": "arn:aws:lambda:us-east-1:012345678910:function:lambda",
                    "Events": ["s3:ObjectCreated:*"],
                    "Filter": {
                        "Key": {"FilterRules": [{"Name": "prefix", "Value": "images/"}]}
                    },
                }
            ]
        },
    )
    result = s3.get_bucket_notification_configuration(Bucket="bucket")
    assert len(result["LambdaFunctionConfigurations"]) == 1
    assert not result.get("TopicConfigurations")
    assert not result.get("QueueConfigurations")
    assert result["LambdaFunctionConfigurations"][0]["Id"]
    assert (
        result["LambdaFunctionConfigurations"][0]["LambdaFunctionArn"]
        == "arn:aws:lambda:us-east-1:012345678910:function:lambda"
    )
    assert (
        result["LambdaFunctionConfigurations"][0]["Events"][0] == "s3:ObjectCreated:*"
    )
    assert len(result["LambdaFunctionConfigurations"][0]["Events"]) == 1
    assert (
        len(result["LambdaFunctionConfigurations"][0]["Filter"]["Key"]["FilterRules"])
        == 1
    )
    assert (
        result["LambdaFunctionConfigurations"][0]["Filter"]["Key"]["FilterRules"][0][
            "Name"
        ]
        == "prefix"
    )
    assert (
        result["LambdaFunctionConfigurations"][0]["Filter"]["Key"]["FilterRules"][0][
            "Value"
        ]
        == "images/"
    )

    # And with all 3 set:
    s3.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "TopicConfigurations": [
                {
                    "TopicArn": "arn:aws:sns:us-east-1:012345678910:mytopic",
                    "Events": ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
                }
            ],
            "LambdaFunctionConfigurations": [
                {
                    "LambdaFunctionArn": "arn:aws:lambda:us-east-1:012345678910:function:lambda",
                    "Events": ["s3:ObjectCreated:*"],
                }
            ],
            "QueueConfigurations": [
                {
                    "QueueArn": "arn:aws:sqs:us-east-1:012345678910:myQueue",
                    "Events": ["s3:ObjectCreated:*"],
                }
            ],
        },
    )
    result = s3.get_bucket_notification_configuration(Bucket="bucket")
    assert len(result["LambdaFunctionConfigurations"]) == 1
    assert len(result["TopicConfigurations"]) == 1
    assert len(result["QueueConfigurations"]) == 1

    # And clear it out:
    s3.put_bucket_notification_configuration(
        Bucket="bucket", NotificationConfiguration={}
    )
    result = s3.get_bucket_notification_configuration(Bucket="bucket")
    assert not result.get("TopicConfigurations")
    assert not result.get("QueueConfigurations")
    assert not result.get("LambdaFunctionConfigurations")


@mock_s3
def test_put_bucket_notification_errors():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="bucket")

    # With incorrect ARNs:
    for tech, arn in [("Queue", "sqs"), ("Topic", "sns"), ("LambdaFunction", "lambda")]:
        with pytest.raises(ClientError) as err:
            s3.put_bucket_notification_configuration(
                Bucket="bucket",
                NotificationConfiguration={
                    "{}Configurations".format(tech): [
                        {
                            "{}Arn".format(
                                tech
                            ): "arn:aws:{}:us-east-1:012345678910:lksajdfkldskfj",
                            "Events": ["s3:ObjectCreated:*"],
                        }
                    ]
                },
            )

        assert err.value.response["Error"]["Code"] == "InvalidArgument"
        assert err.value.response["Error"]["Message"] == "The ARN is not well formed"

    # Region not the same as the bucket:
    with pytest.raises(ClientError) as err:
        s3.put_bucket_notification_configuration(
            Bucket="bucket",
            NotificationConfiguration={
                "QueueConfigurations": [
                    {
                        "QueueArn": "arn:aws:sqs:us-west-2:012345678910:lksajdfkldskfj",
                        "Events": ["s3:ObjectCreated:*"],
                    }
                ]
            },
        )

    assert err.value.response["Error"]["Code"] == "InvalidArgument"
    assert (
        err.value.response["Error"]["Message"]
        == "The notification destination service region is not valid for the bucket location constraint"
    )

    # Invalid event name:
    with pytest.raises(ClientError) as err:
        s3.put_bucket_notification_configuration(
            Bucket="bucket",
            NotificationConfiguration={
                "QueueConfigurations": [
                    {
                        "QueueArn": "arn:aws:sqs:us-east-1:012345678910:lksajdfkldskfj",
                        "Events": ["notarealeventname"],
                    }
                ]
            },
        )
    assert err.value.response["Error"]["Code"] == "InvalidArgument"
    assert (
        err.value.response["Error"]["Message"]
        == "The event is not supported for notifications"
    )


@mock_s3
def test_boto3_put_bucket_logging():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    log_bucket = "logbucket"
    wrong_region_bucket = "wrongregionlogbucket"
    s3.create_bucket(Bucket=bucket_name)
    s3.create_bucket(Bucket=log_bucket)  # Adding the ACL for log-delivery later...
    s3.create_bucket(
        Bucket=wrong_region_bucket,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # No logging config:
    result = s3.get_bucket_logging(Bucket=bucket_name)
    assert not result.get("LoggingEnabled")

    # A log-bucket that doesn't exist:
    with pytest.raises(ClientError) as err:
        s3.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {"TargetBucket": "IAMNOTREAL", "TargetPrefix": ""}
            },
        )
    assert err.value.response["Error"]["Code"] == "InvalidTargetBucketForLogging"

    # A log-bucket that's missing the proper ACLs for LogDelivery:
    with pytest.raises(ClientError) as err:
        s3.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {"TargetBucket": log_bucket, "TargetPrefix": ""}
            },
        )
    assert err.value.response["Error"]["Code"] == "InvalidTargetBucketForLogging"
    assert "log-delivery" in err.value.response["Error"]["Message"]

    # Add the proper "log-delivery" ACL to the log buckets:
    bucket_owner = s3.get_bucket_acl(Bucket=log_bucket)["Owner"]
    for bucket in [log_bucket, wrong_region_bucket]:
        s3.put_bucket_acl(
            Bucket=bucket,
            AccessControlPolicy={
                "Grants": [
                    {
                        "Grantee": {
                            "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                            "Type": "Group",
                        },
                        "Permission": "WRITE",
                    },
                    {
                        "Grantee": {
                            "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                            "Type": "Group",
                        },
                        "Permission": "READ_ACP",
                    },
                    {
                        "Grantee": {"Type": "CanonicalUser", "ID": bucket_owner["ID"]},
                        "Permission": "FULL_CONTROL",
                    },
                ],
                "Owner": bucket_owner,
            },
        )

    # A log-bucket that's in the wrong region:
    with pytest.raises(ClientError) as err:
        s3.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {
                    "TargetBucket": wrong_region_bucket,
                    "TargetPrefix": "",
                }
            },
        )
    assert err.value.response["Error"]["Code"] == "CrossLocationLoggingProhibitted"

    # Correct logging:
    s3.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {
                "TargetBucket": log_bucket,
                "TargetPrefix": "{}/".format(bucket_name),
            }
        },
    )
    result = s3.get_bucket_logging(Bucket=bucket_name)
    assert result["LoggingEnabled"]["TargetBucket"] == log_bucket
    assert result["LoggingEnabled"]["TargetPrefix"] == "{}/".format(bucket_name)
    assert not result["LoggingEnabled"].get("TargetGrants")

    # And disabling:
    s3.put_bucket_logging(Bucket=bucket_name, BucketLoggingStatus={})
    assert not s3.get_bucket_logging(Bucket=bucket_name).get("LoggingEnabled")

    # And enabling with multiple target grants:
    s3.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {
                "TargetBucket": log_bucket,
                "TargetPrefix": "{}/".format(bucket_name),
                "TargetGrants": [
                    {
                        "Grantee": {
                            "ID": "SOMEIDSTRINGHERE9238748923734823917498237489237409123840983274",
                            "Type": "CanonicalUser",
                        },
                        "Permission": "READ",
                    },
                    {
                        "Grantee": {
                            "ID": "SOMEIDSTRINGHERE9238748923734823917498237489237409123840983274",
                            "Type": "CanonicalUser",
                        },
                        "Permission": "WRITE",
                    },
                ],
            }
        },
    )

    result = s3.get_bucket_logging(Bucket=bucket_name)
    assert len(result["LoggingEnabled"]["TargetGrants"]) == 2
    assert (
        result["LoggingEnabled"]["TargetGrants"][0]["Grantee"]["ID"]
        == "SOMEIDSTRINGHERE9238748923734823917498237489237409123840983274"
    )

    # Test with just 1 grant:
    s3.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {
                "TargetBucket": log_bucket,
                "TargetPrefix": "{}/".format(bucket_name),
                "TargetGrants": [
                    {
                        "Grantee": {
                            "ID": "SOMEIDSTRINGHERE9238748923734823917498237489237409123840983274",
                            "Type": "CanonicalUser",
                        },
                        "Permission": "READ",
                    }
                ],
            }
        },
    )
    result = s3.get_bucket_logging(Bucket=bucket_name)
    assert len(result["LoggingEnabled"]["TargetGrants"]) == 1

    # With an invalid grant:
    with pytest.raises(ClientError) as err:
        s3.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {
                    "TargetBucket": log_bucket,
                    "TargetPrefix": "{}/".format(bucket_name),
                    "TargetGrants": [
                        {
                            "Grantee": {
                                "ID": "SOMEIDSTRINGHERE9238748923734823917498237489237409123840983274",
                                "Type": "CanonicalUser",
                            },
                            "Permission": "NOTAREALPERM",
                        }
                    ],
                }
            },
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"


@mock_s3
def test_boto3_put_object_tagging():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3.create_bucket(Bucket=bucket_name)

    with pytest.raises(ClientError) as err:
        s3.put_object_tagging(
            Bucket=bucket_name,
            Key=key,
            Tagging={
                "TagSet": [
                    {"Key": "item1", "Value": "foo"},
                    {"Key": "item2", "Value": "bar"},
                ]
            },
        )

    e = err.value
    e.response["Error"].should.equal(
        {
            "Code": "NoSuchKey",
            "Message": "The specified key does not exist.",
            "RequestID": "7a62c49f-347e-4fc4-9331-6e8eEXAMPLE",
        }
    )

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    resp = s3.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "foo"},
                {"Key": "item2", "Value": "bar"},
            ]
        },
    )

    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_s3
def test_boto3_put_object_tagging_on_earliest_version():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3.create_bucket(Bucket=bucket_name)
    s3_resource = boto3.resource("s3")
    bucket_versioning = s3_resource.BucketVersioning(bucket_name)
    bucket_versioning.enable()
    bucket_versioning.status.should.equal("Enabled")

    with pytest.raises(ClientError) as err:
        s3.put_object_tagging(
            Bucket=bucket_name,
            Key=key,
            Tagging={
                "TagSet": [
                    {"Key": "item1", "Value": "foo"},
                    {"Key": "item2", "Value": "bar"},
                ]
            },
        )

    e = err.value
    e.response["Error"].should.equal(
        {
            "Code": "NoSuchKey",
            "Message": "The specified key does not exist.",
            "RequestID": "7a62c49f-347e-4fc4-9331-6e8eEXAMPLE",
        }
    )

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")
    s3.put_object(Bucket=bucket_name, Key=key, Body="test_updated")

    object_versions = list(s3_resource.Bucket(bucket_name).object_versions.all())
    first_object = object_versions[0]
    second_object = object_versions[1]

    resp = s3.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "foo"},
                {"Key": "item2", "Value": "bar"},
            ]
        },
        VersionId=first_object.id,
    )

    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # Older version has tags while the most recent does not
    resp = s3.get_object_tagging(Bucket=bucket_name, Key=key, VersionId=first_object.id)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    sorted_tagset = sorted(resp["TagSet"], key=lambda t: t["Key"])
    sorted_tagset.should.equal(
        [{"Key": "item1", "Value": "foo"}, {"Key": "item2", "Value": "bar"}]
    )

    resp = s3.get_object_tagging(
        Bucket=bucket_name, Key=key, VersionId=second_object.id
    )
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    resp["TagSet"].should.equal([])


@mock_s3
def test_boto3_put_object_tagging_on_both_version():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3.create_bucket(Bucket=bucket_name)
    s3_resource = boto3.resource("s3")
    bucket_versioning = s3_resource.BucketVersioning(bucket_name)
    bucket_versioning.enable()
    bucket_versioning.status.should.equal("Enabled")

    with pytest.raises(ClientError) as err:
        s3.put_object_tagging(
            Bucket=bucket_name,
            Key=key,
            Tagging={
                "TagSet": [
                    {"Key": "item1", "Value": "foo"},
                    {"Key": "item2", "Value": "bar"},
                ]
            },
        )

    e = err.value
    e.response["Error"].should.equal(
        {
            "Code": "NoSuchKey",
            "Message": "The specified key does not exist.",
            "RequestID": "7a62c49f-347e-4fc4-9331-6e8eEXAMPLE",
        }
    )

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")
    s3.put_object(Bucket=bucket_name, Key=key, Body="test_updated")

    object_versions = list(s3_resource.Bucket(bucket_name).object_versions.all())
    first_object = object_versions[0]
    second_object = object_versions[1]

    resp = s3.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "foo"},
                {"Key": "item2", "Value": "bar"},
            ]
        },
        VersionId=first_object.id,
    )
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    resp = s3.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "baz"},
                {"Key": "item2", "Value": "bin"},
            ]
        },
        VersionId=second_object.id,
    )
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    resp = s3.get_object_tagging(Bucket=bucket_name, Key=key, VersionId=first_object.id)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    sorted_tagset = sorted(resp["TagSet"], key=lambda t: t["Key"])
    sorted_tagset.should.equal(
        [{"Key": "item1", "Value": "foo"}, {"Key": "item2", "Value": "bar"}]
    )

    resp = s3.get_object_tagging(
        Bucket=bucket_name, Key=key, VersionId=second_object.id
    )
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    sorted_tagset = sorted(resp["TagSet"], key=lambda t: t["Key"])
    sorted_tagset.should.equal(
        [{"Key": "item1", "Value": "baz"}, {"Key": "item2", "Value": "bin"}]
    )


@mock_s3
def test_boto3_put_object_tagging_with_single_tag():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3.create_bucket(Bucket=bucket_name)

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    resp = s3.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={"TagSet": [{"Key": "item1", "Value": "foo"}]},
    )

    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_s3
def test_boto3_get_object_tagging():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3.create_bucket(Bucket=bucket_name)

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    resp = s3.get_object_tagging(Bucket=bucket_name, Key=key)
    resp["TagSet"].should.have.length_of(0)

    resp = s3.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "foo"},
                {"Key": "item2", "Value": "bar"},
            ]
        },
    )
    resp = s3.get_object_tagging(Bucket=bucket_name, Key=key)

    resp["TagSet"].should.have.length_of(2)
    resp["TagSet"].should.contain({"Key": "item1", "Value": "foo"})
    resp["TagSet"].should.contain({"Key": "item2", "Value": "bar"})


@mock_s3
def test_boto3_list_object_versions():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (six.b("v1"), six.b("v2"))
    for body in items:
        s3.put_object(Bucket=bucket_name, Key=key, Body=body)
    response = s3.list_object_versions(Bucket=bucket_name)
    # Two object versions should be returned
    len(response["Versions"]).should.equal(2)
    keys = set([item["Key"] for item in response["Versions"]])
    keys.should.equal({key})

    # the first item in the list should be the latest
    response["Versions"][0]["IsLatest"].should.equal(True)

    # Test latest object version is returned
    response = s3.get_object(Bucket=bucket_name, Key=key)
    response["Body"].read().should.equal(items[-1])


@mock_s3
def test_boto3_list_object_versions_with_versioning_disabled():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    s3.create_bucket(Bucket=bucket_name)
    items = (six.b("v1"), six.b("v2"))
    for body in items:
        s3.put_object(Bucket=bucket_name, Key=key, Body=body)
    response = s3.list_object_versions(Bucket=bucket_name)

    # One object version should be returned
    len(response["Versions"]).should.equal(1)
    response["Versions"][0]["Key"].should.equal(key)

    # The version id should be the string null
    response["Versions"][0]["VersionId"].should.equal("null")

    # Test latest object version is returned
    response = s3.get_object(Bucket=bucket_name, Key=key)
    response["Body"].read().should.equal(items[-1])


@mock_s3
def test_boto3_list_object_versions_with_versioning_enabled_late():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    s3.create_bucket(Bucket=bucket_name)
    items = (six.b("v1"), six.b("v2"))
    s3.put_object(Bucket=bucket_name, Key=key, Body=six.b("v1"))
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    s3.put_object(Bucket=bucket_name, Key=key, Body=six.b("v2"))
    response = s3.list_object_versions(Bucket=bucket_name)

    # Two object versions should be returned
    len(response["Versions"]).should.equal(2)
    keys = set([item["Key"] for item in response["Versions"]])
    keys.should.equal({key})

    # There should still be a null version id.
    versionsId = set([item["VersionId"] for item in response["Versions"]])
    versionsId.should.contain("null")

    # Test latest object version is returned
    response = s3.get_object(Bucket=bucket_name, Key=key)
    response["Body"].read().should.equal(items[-1])


@mock_s3
def test_boto3_bad_prefix_list_object_versions():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    bad_prefix = "key-that-does-not-exist"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (six.b("v1"), six.b("v2"))
    for body in items:
        s3.put_object(Bucket=bucket_name, Key=key, Body=body)
    response = s3.list_object_versions(Bucket=bucket_name, Prefix=bad_prefix)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response.should_not.contain("Versions")
    response.should_not.contain("DeleteMarkers")


@mock_s3
def test_boto3_delete_markers():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions-and-unicode-ó"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (six.b("v1"), six.b("v2"))
    for body in items:
        s3.put_object(Bucket=bucket_name, Key=key, Body=body)

    s3.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": key}]})

    with pytest.raises(ClientError) as e:
        s3.get_object(Bucket=bucket_name, Key=key)
    e.value.response["Error"]["Code"].should.equal("NoSuchKey")

    response = s3.list_object_versions(Bucket=bucket_name)
    response["Versions"].should.have.length_of(2)
    response["DeleteMarkers"].should.have.length_of(1)

    s3.delete_object(
        Bucket=bucket_name, Key=key, VersionId=response["DeleteMarkers"][0]["VersionId"]
    )
    response = s3.get_object(Bucket=bucket_name, Key=key)
    response["Body"].read().should.equal(items[-1])

    response = s3.list_object_versions(Bucket=bucket_name)
    response["Versions"].should.have.length_of(2)

    # We've asserted there is only 2 records so one is newest, one is oldest
    latest = list(filter(lambda item: item["IsLatest"], response["Versions"]))[0]
    oldest = list(filter(lambda item: not item["IsLatest"], response["Versions"]))[0]
    # Double check ordering of version ID's
    latest["VersionId"].should_not.equal(oldest["VersionId"])

    # Double check the name is still unicode
    latest["Key"].should.equal("key-with-versions-and-unicode-ó")
    oldest["Key"].should.equal("key-with-versions-and-unicode-ó")


@mock_s3
def test_boto3_multiple_delete_markers():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions-and-unicode-ó"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (six.b("v1"), six.b("v2"))
    for body in items:
        s3.put_object(Bucket=bucket_name, Key=key, Body=body)

    # Delete the object twice to add multiple delete markers
    s3.delete_object(Bucket=bucket_name, Key=key)
    s3.delete_object(Bucket=bucket_name, Key=key)

    response = s3.list_object_versions(Bucket=bucket_name)
    response["DeleteMarkers"].should.have.length_of(2)

    with pytest.raises(ClientError) as e:
        s3.get_object(Bucket=bucket_name, Key=key)
        e.response["Error"]["Code"].should.equal("404")

    # Remove both delete markers to restore the object
    s3.delete_object(
        Bucket=bucket_name, Key=key, VersionId=response["DeleteMarkers"][0]["VersionId"]
    )
    s3.delete_object(
        Bucket=bucket_name, Key=key, VersionId=response["DeleteMarkers"][1]["VersionId"]
    )

    response = s3.get_object(Bucket=bucket_name, Key=key)
    response["Body"].read().should.equal(items[-1])
    response = s3.list_object_versions(Bucket=bucket_name)
    response["Versions"].should.have.length_of(2)

    # We've asserted there is only 2 records so one is newest, one is oldest
    latest = list(filter(lambda item: item["IsLatest"], response["Versions"]))[0]
    oldest = list(filter(lambda item: not item["IsLatest"], response["Versions"]))[0]

    # Double check ordering of version ID's
    latest["VersionId"].should_not.equal(oldest["VersionId"])

    # Double check the name is still unicode
    latest["Key"].should.equal("key-with-versions-and-unicode-ó")
    oldest["Key"].should.equal("key-with-versions-and-unicode-ó")


@mock_s3
def test_get_stream_gzipped():
    payload = b"this is some stuff here"

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="moto-tests")
    buffer_ = BytesIO()
    with GzipFile(fileobj=buffer_, mode="w") as f:
        f.write(payload)
    payload_gz = buffer_.getvalue()

    s3_client.put_object(
        Bucket="moto-tests", Key="keyname", Body=payload_gz, ContentEncoding="gzip"
    )

    obj = s3_client.get_object(Bucket="moto-tests", Key="keyname")
    res = zlib.decompress(obj["Body"].read(), 16 + zlib.MAX_WBITS)
    assert res == payload


TEST_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<ns0:WebsiteConfiguration xmlns:ns0="http://s3.amazonaws.com/doc/2006-03-01/">
    <ns0:IndexDocument>
        <ns0:Suffix>index.html</ns0:Suffix>
    </ns0:IndexDocument>
    <ns0:RoutingRules>
        <ns0:RoutingRule>
            <ns0:Condition>
                <ns0:KeyPrefixEquals>test/testing</ns0:KeyPrefixEquals>
            </ns0:Condition>
            <ns0:Redirect>
                <ns0:ReplaceKeyWith>test.txt</ns0:ReplaceKeyWith>
            </ns0:Redirect>
        </ns0:RoutingRule>
    </ns0:RoutingRules>
</ns0:WebsiteConfiguration>
"""


@mock_s3
def test_boto3_bucket_name_too_long():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3.create_bucket(Bucket="x" * 64)
    exc.value.response["Error"]["Code"].should.equal("InvalidBucketName")


@mock_s3
def test_boto3_bucket_name_too_short():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3.create_bucket(Bucket="x" * 2)
    exc.value.response["Error"]["Code"].should.equal("InvalidBucketName")


@mock_s3
def test_accelerated_none_when_unspecified():
    bucket_name = "some_bucket"
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)
    resp = s3.get_bucket_accelerate_configuration(Bucket=bucket_name)
    resp.shouldnt.have.key("Status")


@mock_s3
def test_can_enable_bucket_acceleration():
    bucket_name = "some_bucket"
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)
    resp = s3.put_bucket_accelerate_configuration(
        Bucket=bucket_name, AccelerateConfiguration={"Status": "Enabled"}
    )
    resp.keys().should.have.length_of(
        1
    )  # Response contains nothing (only HTTP headers)
    resp = s3.get_bucket_accelerate_configuration(Bucket=bucket_name)
    resp.should.have.key("Status")
    resp["Status"].should.equal("Enabled")


@mock_s3
def test_can_suspend_bucket_acceleration():
    bucket_name = "some_bucket"
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)
    resp = s3.put_bucket_accelerate_configuration(
        Bucket=bucket_name, AccelerateConfiguration={"Status": "Enabled"}
    )
    resp = s3.put_bucket_accelerate_configuration(
        Bucket=bucket_name, AccelerateConfiguration={"Status": "Suspended"}
    )
    resp.keys().should.have.length_of(
        1
    )  # Response contains nothing (only HTTP headers)
    resp = s3.get_bucket_accelerate_configuration(Bucket=bucket_name)
    resp.should.have.key("Status")
    resp["Status"].should.equal("Suspended")


@mock_s3
def test_suspending_acceleration_on_not_configured_bucket_does_nothing():
    bucket_name = "some_bucket"
    s3 = boto3.client("s3")
    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )
    resp = s3.put_bucket_accelerate_configuration(
        Bucket=bucket_name, AccelerateConfiguration={"Status": "Suspended"}
    )
    resp.keys().should.have.length_of(
        1
    )  # Response contains nothing (only HTTP headers)
    resp = s3.get_bucket_accelerate_configuration(Bucket=bucket_name)
    resp.shouldnt.have.key("Status")


@mock_s3
def test_accelerate_configuration_status_validation():
    bucket_name = "some_bucket"
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)
    with pytest.raises(ClientError) as exc:
        s3.put_bucket_accelerate_configuration(
            Bucket=bucket_name, AccelerateConfiguration={"Status": "bad_status"}
        )
    exc.value.response["Error"]["Code"].should.equal("MalformedXML")


@mock_s3
def test_accelerate_configuration_is_not_supported_when_bucket_name_has_dots():
    bucket_name = "some.bucket.with.dots"
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)
    with pytest.raises(ClientError) as exc:
        s3.put_bucket_accelerate_configuration(
            Bucket=bucket_name, AccelerateConfiguration={"Status": "Enabled"}
        )
    exc.value.response["Error"]["Code"].should.equal("InvalidRequest")


def store_and_read_back_a_key(key):
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    body = b"Some body"

    s3.create_bucket(Bucket=bucket_name)
    s3.put_object(Bucket=bucket_name, Key=key, Body=body)

    response = s3.get_object(Bucket=bucket_name, Key=key)
    response["Body"].read().should.equal(body)


@mock_s3
def test_paths_with_leading_slashes_work():
    store_and_read_back_a_key("/a-key")


@mock_s3
def test_root_dir_with_empty_name_works():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Does not work in server mode due to error in Workzeug")
    store_and_read_back_a_key("/")


@pytest.mark.parametrize("bucket_name", ["mybucket", "my.bucket"])
@mock_s3
def test_leading_slashes_not_removed(bucket_name):
    """Make sure that leading slashes are not removed internally."""
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)

    uploaded_key = "/key"
    invalid_key_1 = "key"
    invalid_key_2 = "//key"

    s3.put_object(Bucket=bucket_name, Key=uploaded_key, Body=b"Some body")

    with pytest.raises(ClientError) as e:
        s3.get_object(Bucket=bucket_name, Key=invalid_key_1)
    e.value.response["Error"]["Code"].should.equal("NoSuchKey")

    with pytest.raises(ClientError) as e:
        s3.get_object(Bucket=bucket_name, Key=invalid_key_2)
    e.value.response["Error"]["Code"].should.equal("NoSuchKey")


@pytest.mark.parametrize(
    "key", ["foo/bar/baz", "foo", "foo/run_dt%3D2019-01-01%252012%253A30%253A00"]
)
@mock_s3
def test_delete_objects_with_url_encoded_key(key):
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    body = b"Some body"

    s3.create_bucket(Bucket=bucket_name)

    def put_object():
        s3.put_object(Bucket=bucket_name, Key=key, Body=body)

    def assert_deleted():
        with pytest.raises(ClientError) as e:
            s3.get_object(Bucket=bucket_name, Key=key)

        e.value.response["Error"]["Code"].should.equal("NoSuchKey")

    put_object()
    s3.delete_object(Bucket=bucket_name, Key=key)
    assert_deleted()

    put_object()
    s3.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": key}]})
    assert_deleted()


@mock_s3
@mock_config
def test_public_access_block():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="mybucket")

    # Try to get the public access block (should not exist by default)
    with pytest.raises(ClientError) as ce:
        client.get_public_access_block(Bucket="mybucket")

    assert ce.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"
    assert (
        ce.value.response["Error"]["Message"]
        == "The public access block configuration was not found"
    )
    assert ce.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404

    # Put a public block in place:
    test_map = {
        "BlockPublicAcls": False,
        "IgnorePublicAcls": False,
        "BlockPublicPolicy": False,
        "RestrictPublicBuckets": False,
    }

    for field in test_map.keys():
        # Toggle:
        test_map[field] = True

        client.put_public_access_block(
            Bucket="mybucket", PublicAccessBlockConfiguration=test_map
        )

        # Test:
        assert (
            test_map
            == client.get_public_access_block(Bucket="mybucket")[
                "PublicAccessBlockConfiguration"
            ]
        )

    # Assume missing values are default False:
    client.put_public_access_block(
        Bucket="mybucket", PublicAccessBlockConfiguration={"BlockPublicAcls": True}
    )
    assert client.get_public_access_block(Bucket="mybucket")[
        "PublicAccessBlockConfiguration"
    ] == {
        "BlockPublicAcls": True,
        "IgnorePublicAcls": False,
        "BlockPublicPolicy": False,
        "RestrictPublicBuckets": False,
    }

    # Test with a blank PublicAccessBlockConfiguration:
    with pytest.raises(ClientError) as ce:
        client.put_public_access_block(
            Bucket="mybucket", PublicAccessBlockConfiguration={}
        )

    assert ce.value.response["Error"]["Code"] == "InvalidRequest"
    assert (
        ce.value.response["Error"]["Message"]
        == "Must specify at least one configuration."
    )
    assert ce.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Test that things work with AWS Config:
    config_client = boto3.client("config", region_name=DEFAULT_REGION_NAME)
    result = config_client.get_resource_config_history(
        resourceType="AWS::S3::Bucket", resourceId="mybucket"
    )
    pub_block_config = json.loads(
        result["configurationItems"][0]["supplementaryConfiguration"][
            "PublicAccessBlockConfiguration"
        ]
    )

    assert pub_block_config == {
        "blockPublicAcls": True,
        "ignorePublicAcls": False,
        "blockPublicPolicy": False,
        "restrictPublicBuckets": False,
    }

    # Delete:
    client.delete_public_access_block(Bucket="mybucket")

    with pytest.raises(ClientError) as ce:
        client.get_public_access_block(Bucket="mybucket")
    assert ce.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"


@mock_s3
def test_s3_public_access_block_to_config_dict():
    from moto.s3.config import s3_config_query

    # With 1 bucket in us-west-2:
    s3_config_query.backends["global"].create_bucket("bucket1", "us-west-2")

    public_access_block = {
        "BlockPublicAcls": "True",
        "IgnorePublicAcls": "False",
        "BlockPublicPolicy": "True",
        "RestrictPublicBuckets": "False",
    }

    # Python 2 unicode issues:
    if sys.version_info[0] < 3:
        public_access_block = py2_strip_unicode_keys(public_access_block)

    # Add a public access block:
    s3_config_query.backends["global"].put_bucket_public_access_block(
        "bucket1", public_access_block
    )

    result = (
        s3_config_query.backends["global"]
        .buckets["bucket1"]
        .public_access_block.to_config_dict()
    )

    convert_bool = lambda x: x == "True"
    for key, value in public_access_block.items():
        assert result[
            "{lowercase}{rest}".format(lowercase=key[0].lower(), rest=key[1:])
        ] == convert_bool(value)

    # Verify that this resides in the full bucket's to_config_dict:
    full_result = s3_config_query.backends["global"].buckets["bucket1"].to_config_dict()
    assert (
        json.loads(
            full_result["supplementaryConfiguration"]["PublicAccessBlockConfiguration"]
        )
        == result
    )


@mock_s3
def test_list_config_discovered_resources():
    from moto.s3.config import s3_config_query

    # Without any buckets:
    assert s3_config_query.list_config_service_resources(
        "global", "global", None, None, 100, None
    ) == ([], None)

    # With 10 buckets in us-west-2:
    for x in range(0, 10):
        s3_config_query.backends["global"].create_bucket(
            "bucket{}".format(x), "us-west-2"
        )

    # With 2 buckets in eu-west-1:
    for x in range(10, 12):
        s3_config_query.backends["global"].create_bucket(
            "eu-bucket{}".format(x), "eu-west-1"
        )

    result, next_token = s3_config_query.list_config_service_resources(
        None, None, 100, None
    )
    assert not next_token
    assert len(result) == 12
    for x in range(0, 10):
        assert result[x] == {
            "type": "AWS::S3::Bucket",
            "id": "bucket{}".format(x),
            "name": "bucket{}".format(x),
            "region": "us-west-2",
        }
    for x in range(10, 12):
        assert result[x] == {
            "type": "AWS::S3::Bucket",
            "id": "eu-bucket{}".format(x),
            "name": "eu-bucket{}".format(x),
            "region": "eu-west-1",
        }

    # With a name:
    result, next_token = s3_config_query.list_config_service_resources(
        None, "bucket0", 100, None
    )
    assert len(result) == 1 and result[0]["name"] == "bucket0" and not next_token

    # With a region:
    result, next_token = s3_config_query.list_config_service_resources(
        None, None, 100, None, resource_region="eu-west-1"
    )
    assert len(result) == 2 and not next_token and result[1]["name"] == "eu-bucket11"

    # With resource ids:
    result, next_token = s3_config_query.list_config_service_resources(
        ["bucket0", "bucket1"], None, 100, None
    )
    assert (
        len(result) == 2
        and result[0]["name"] == "bucket0"
        and result[1]["name"] == "bucket1"
        and not next_token
    )

    # With duplicated resource ids:
    result, next_token = s3_config_query.list_config_service_resources(
        ["bucket0", "bucket0"], None, 100, None
    )
    assert len(result) == 1 and result[0]["name"] == "bucket0" and not next_token

    # Pagination:
    result, next_token = s3_config_query.list_config_service_resources(
        None, None, 1, None
    )
    assert (
        len(result) == 1 and result[0]["name"] == "bucket0" and next_token == "bucket1"
    )

    # Last Page:
    result, next_token = s3_config_query.list_config_service_resources(
        None, None, 1, "eu-bucket11", resource_region="eu-west-1"
    )
    assert len(result) == 1 and result[0]["name"] == "eu-bucket11" and not next_token

    # With a list of buckets:
    result, next_token = s3_config_query.list_config_service_resources(
        ["bucket0", "bucket1"], None, 1, None
    )
    assert (
        len(result) == 1 and result[0]["name"] == "bucket0" and next_token == "bucket1"
    )

    # With an invalid page:
    with pytest.raises(InvalidNextTokenException) as inte:
        s3_config_query.list_config_service_resources(None, None, 1, "notabucket")

    assert "The nextToken provided is invalid" in inte.value.message


@mock_s3
def test_s3_lifecycle_config_dict():
    from moto.s3.config import s3_config_query

    # With 1 bucket in us-west-2:
    s3_config_query.backends["global"].create_bucket("bucket1", "us-west-2")

    # And a lifecycle policy
    lifecycle = [
        {
            "ID": "rule1",
            "Status": "Enabled",
            "Filter": {"Prefix": ""},
            "Expiration": {"Days": 1},
        },
        {
            "ID": "rule2",
            "Status": "Enabled",
            "Filter": {
                "And": {
                    "Prefix": "some/path",
                    "Tag": [{"Key": "TheKey", "Value": "TheValue"}],
                }
            },
            "Expiration": {"Days": 1},
        },
        {"ID": "rule3", "Status": "Enabled", "Filter": {}, "Expiration": {"Days": 1}},
        {
            "ID": "rule4",
            "Status": "Enabled",
            "Filter": {"Prefix": ""},
            "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
        },
    ]
    s3_config_query.backends["global"].set_bucket_lifecycle("bucket1", lifecycle)

    # Get the rules for this:
    lifecycles = [
        rule.to_config_dict()
        for rule in s3_config_query.backends["global"].buckets["bucket1"].rules
    ]

    # Verify the first:
    assert lifecycles[0] == {
        "id": "rule1",
        "prefix": None,
        "status": "Enabled",
        "expirationInDays": 1,
        "expiredObjectDeleteMarker": None,
        "noncurrentVersionExpirationInDays": -1,
        "expirationDate": None,
        "transitions": None,
        "noncurrentVersionTransitions": None,
        "abortIncompleteMultipartUpload": None,
        "filter": {"predicate": {"type": "LifecyclePrefixPredicate", "prefix": ""}},
    }

    # Verify the second:
    assert lifecycles[1] == {
        "id": "rule2",
        "prefix": None,
        "status": "Enabled",
        "expirationInDays": 1,
        "expiredObjectDeleteMarker": None,
        "noncurrentVersionExpirationInDays": -1,
        "expirationDate": None,
        "transitions": None,
        "noncurrentVersionTransitions": None,
        "abortIncompleteMultipartUpload": None,
        "filter": {
            "predicate": {
                "type": "LifecycleAndOperator",
                "operands": [
                    {"type": "LifecyclePrefixPredicate", "prefix": "some/path"},
                    {
                        "type": "LifecycleTagPredicate",
                        "tag": {"key": "TheKey", "value": "TheValue"},
                    },
                ],
            }
        },
    }

    # And the third:
    assert lifecycles[2] == {
        "id": "rule3",
        "prefix": None,
        "status": "Enabled",
        "expirationInDays": 1,
        "expiredObjectDeleteMarker": None,
        "noncurrentVersionExpirationInDays": -1,
        "expirationDate": None,
        "transitions": None,
        "noncurrentVersionTransitions": None,
        "abortIncompleteMultipartUpload": None,
        "filter": {"predicate": None},
    }

    # And the last:
    assert lifecycles[3] == {
        "id": "rule4",
        "prefix": None,
        "status": "Enabled",
        "expirationInDays": None,
        "expiredObjectDeleteMarker": None,
        "noncurrentVersionExpirationInDays": -1,
        "expirationDate": None,
        "transitions": None,
        "noncurrentVersionTransitions": None,
        "abortIncompleteMultipartUpload": {"daysAfterInitiation": 1},
        "filter": {"predicate": {"type": "LifecyclePrefixPredicate", "prefix": ""}},
    }


@mock_s3
def test_s3_notification_config_dict():
    from moto.s3.config import s3_config_query

    # With 1 bucket in us-west-2:
    s3_config_query.backends["global"].create_bucket("bucket1", "us-west-2")

    # And some notifications:
    notifications = {
        "TopicConfiguration": [
            {
                "Id": "Topic",
                "Topic": "arn:aws:sns:us-west-2:012345678910:mytopic",
                "Event": [
                    "s3:ReducedRedundancyLostObject",
                    "s3:ObjectRestore:Completed",
                ],
            }
        ],
        "QueueConfiguration": [
            {
                "Id": "Queue",
                "Queue": "arn:aws:sqs:us-west-2:012345678910:myqueue",
                "Event": ["s3:ObjectRemoved:Delete"],
                "Filter": {
                    "S3Key": {
                        "FilterRule": [{"Name": "prefix", "Value": "stuff/here/"}]
                    }
                },
            }
        ],
        "CloudFunctionConfiguration": [
            {
                "Id": "Lambda",
                "CloudFunction": "arn:aws:lambda:us-west-2:012345678910:function:mylambda",
                "Event": [
                    "s3:ObjectCreated:Post",
                    "s3:ObjectCreated:Copy",
                    "s3:ObjectCreated:Put",
                ],
                "Filter": {
                    "S3Key": {"FilterRule": [{"Name": "suffix", "Value": ".png"}]}
                },
            }
        ],
    }

    s3_config_query.backends["global"].put_bucket_notification_configuration(
        "bucket1", notifications
    )

    # Get the notifications for this:
    notifications = (
        s3_config_query.backends["global"]
        .buckets["bucket1"]
        .notification_configuration.to_config_dict()
    )

    # Verify it all:
    assert notifications == {
        "configurations": {
            "Topic": {
                "events": [
                    "s3:ReducedRedundancyLostObject",
                    "s3:ObjectRestore:Completed",
                ],
                "filter": None,
                "objectPrefixes": [],
                "topicARN": "arn:aws:sns:us-west-2:012345678910:mytopic",
                "type": "TopicConfiguration",
            },
            "Queue": {
                "events": ["s3:ObjectRemoved:Delete"],
                "filter": {
                    "s3KeyFilter": {
                        "filterRules": [{"name": "prefix", "value": "stuff/here/"}]
                    }
                },
                "objectPrefixes": [],
                "queueARN": "arn:aws:sqs:us-west-2:012345678910:myqueue",
                "type": "QueueConfiguration",
            },
            "Lambda": {
                "events": [
                    "s3:ObjectCreated:Post",
                    "s3:ObjectCreated:Copy",
                    "s3:ObjectCreated:Put",
                ],
                "filter": {
                    "s3KeyFilter": {
                        "filterRules": [{"name": "suffix", "value": ".png"}]
                    }
                },
                "objectPrefixes": [],
                "queueARN": "arn:aws:lambda:us-west-2:012345678910:function:mylambda",
                "type": "LambdaConfiguration",
            },
        }
    }


@mock_s3
def test_s3_acl_to_config_dict():
    from moto.s3.config import s3_config_query
    from moto.s3.models import FakeAcl, FakeGrant, FakeGrantee, OWNER

    # With 1 bucket in us-west-2:
    s3_config_query.backends["global"].create_bucket("logbucket", "us-west-2")

    # Get the config dict with nothing other than the owner details:
    acls = s3_config_query.backends["global"].buckets["logbucket"].acl.to_config_dict()
    assert acls == {"grantSet": None, "owner": {"displayName": None, "id": OWNER}}

    # Add some Log Bucket ACLs:
    log_acls = FakeAcl(
        [
            FakeGrant(
                [FakeGrantee(uri="http://acs.amazonaws.com/groups/s3/LogDelivery")],
                "WRITE",
            ),
            FakeGrant(
                [FakeGrantee(uri="http://acs.amazonaws.com/groups/s3/LogDelivery")],
                "READ_ACP",
            ),
            FakeGrant([FakeGrantee(id=OWNER)], "FULL_CONTROL"),
        ]
    )
    s3_config_query.backends["global"].set_bucket_acl("logbucket", log_acls)

    acls = s3_config_query.backends["global"].buckets["logbucket"].acl.to_config_dict()
    assert acls == {
        "grantSet": None,
        "grantList": [
            {"grantee": "LogDelivery", "permission": "Write"},
            {"grantee": "LogDelivery", "permission": "ReadAcp"},
        ],
        "owner": {"displayName": None, "id": OWNER},
    }

    # Give the owner less than full_control permissions:
    log_acls = FakeAcl(
        [
            FakeGrant([FakeGrantee(id=OWNER)], "READ_ACP"),
            FakeGrant([FakeGrantee(id=OWNER)], "WRITE_ACP"),
        ]
    )
    s3_config_query.backends["global"].set_bucket_acl("logbucket", log_acls)
    acls = s3_config_query.backends["global"].buckets["logbucket"].acl.to_config_dict()
    assert acls == {
        "grantSet": None,
        "grantList": [
            {"grantee": {"id": OWNER, "displayName": None}, "permission": "ReadAcp"},
            {"grantee": {"id": OWNER, "displayName": None}, "permission": "WriteAcp"},
        ],
        "owner": {"displayName": None, "id": OWNER},
    }


@mock_s3
def test_s3_config_dict():
    from moto.s3.config import s3_config_query
    from moto.s3.models import (
        FakeAcl,
        FakeGrant,
        FakeGrantee,
        OWNER,
    )

    # Without any buckets:
    assert not s3_config_query.get_config_resource("some_bucket")

    tags = {"someTag": "someValue", "someOtherTag": "someOtherValue"}

    # With 1 bucket in us-west-2:
    s3_config_query.backends["global"].create_bucket("bucket1", "us-west-2")
    s3_config_query.backends["global"].put_bucket_tagging("bucket1", tags)

    # With a log bucket:
    s3_config_query.backends["global"].create_bucket("logbucket", "us-west-2")
    log_acls = FakeAcl(
        [
            FakeGrant(
                [FakeGrantee(uri="http://acs.amazonaws.com/groups/s3/LogDelivery")],
                "WRITE",
            ),
            FakeGrant(
                [FakeGrantee(uri="http://acs.amazonaws.com/groups/s3/LogDelivery")],
                "READ_ACP",
            ),
            FakeGrant([FakeGrantee(id=OWNER)], "FULL_CONTROL"),
        ]
    )

    s3_config_query.backends["global"].set_bucket_acl("logbucket", log_acls)
    s3_config_query.backends["global"].put_bucket_logging(
        "bucket1", {"TargetBucket": "logbucket", "TargetPrefix": ""}
    )

    policy = json.dumps(
        {
            "Statement": [
                {
                    "Effect": "Deny",
                    "Action": "s3:DeleteObject",
                    "Principal": "*",
                    "Resource": "arn:aws:s3:::bucket1/*",
                }
            ]
        }
    )

    # The policy is a byte array -- need to encode in Python 3 -- for Python 2 just pass the raw string in:
    if sys.version_info[0] > 2:
        pass_policy = bytes(policy, "utf-8")
    else:
        pass_policy = policy
    s3_config_query.backends["global"].set_bucket_policy("bucket1", pass_policy)

    # Get the us-west-2 bucket and verify that it works properly:
    bucket1_result = s3_config_query.get_config_resource("bucket1")

    # Just verify a few things:
    assert bucket1_result["arn"] == "arn:aws:s3:::bucket1"
    assert bucket1_result["awsRegion"] == "us-west-2"
    assert bucket1_result["resourceName"] == bucket1_result["resourceId"] == "bucket1"
    assert bucket1_result["tags"] == {
        "someTag": "someValue",
        "someOtherTag": "someOtherValue",
    }
    assert json.loads(
        bucket1_result["supplementaryConfiguration"]["BucketTaggingConfiguration"]
    ) == {"tagSets": [{"tags": bucket1_result["tags"]}]}
    assert isinstance(bucket1_result["configuration"], str)
    exist_list = [
        "AccessControlList",
        "BucketAccelerateConfiguration",
        "BucketLoggingConfiguration",
        "BucketPolicy",
        "IsRequesterPaysEnabled",
        "BucketNotificationConfiguration",
    ]
    for exist in exist_list:
        assert isinstance(bucket1_result["supplementaryConfiguration"][exist], str)

    # Verify the logging config:
    assert json.loads(
        bucket1_result["supplementaryConfiguration"]["BucketLoggingConfiguration"]
    ) == {"destinationBucketName": "logbucket", "logFilePrefix": ""}

    # Verify that the AccessControlList is a double-wrapped JSON string:
    assert json.loads(
        json.loads(bucket1_result["supplementaryConfiguration"]["AccessControlList"])
    ) == {
        "grantSet": None,
        "owner": {
            "displayName": None,
            "id": "75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a",
        },
    }

    # Verify the policy:
    assert json.loads(bucket1_result["supplementaryConfiguration"]["BucketPolicy"]) == {
        "policyText": policy
    }

    # Filter by correct region:
    assert bucket1_result == s3_config_query.get_config_resource(
        "bucket1", resource_region="us-west-2"
    )

    # By incorrect region:
    assert not s3_config_query.get_config_resource(
        "bucket1", resource_region="eu-west-1"
    )

    # With correct resource ID and name:
    assert bucket1_result == s3_config_query.get_config_resource(
        "bucket1", resource_name="bucket1"
    )

    # With an incorrect resource name:
    assert not s3_config_query.get_config_resource(
        "bucket1", resource_name="eu-bucket-1"
    )

    # Verify that no bucket policy returns the proper value:
    logging_bucket = s3_config_query.get_config_resource("logbucket")
    assert json.loads(logging_bucket["supplementaryConfiguration"]["BucketPolicy"]) == {
        "policyText": None
    }
    assert not logging_bucket["tags"]
    assert not logging_bucket["supplementaryConfiguration"].get(
        "BucketTaggingConfiguration"
    )


@mock_s3
def test_creating_presigned_post():
    bucket = "presigned-test"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket)
    success_url = "http://localhost/completed"
    fdata = b"test data\n"
    file_uid = uuid.uuid4()
    conditions = [
        {"Content-Type": "text/plain"},
        {"x-amz-server-side-encryption": "AES256"},
        {"success_action_redirect": success_url},
    ]
    conditions.append(["content-length-range", 1, 30])
    data = s3.generate_presigned_post(
        Bucket=bucket,
        Key="{file_uid}.txt".format(file_uid=file_uid),
        Fields={
            "content-type": "text/plain",
            "success_action_redirect": success_url,
            "x-amz-server-side-encryption": "AES256",
        },
        Conditions=conditions,
        ExpiresIn=1000,
    )
    resp = requests.post(
        data["url"], data=data["fields"], files={"file": fdata}, allow_redirects=False
    )
    assert resp.headers["Location"] == success_url
    assert resp.status_code == 303
    assert (
        s3.get_object(Bucket=bucket, Key="{file_uid}.txt".format(file_uid=file_uid))[
            "Body"
        ].read()
        == fdata
    )


@mock_s3
def test_encryption():
    # Create Bucket so that test can run
    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="mybucket")

    with pytest.raises(ClientError) as exc:
        conn.get_bucket_encryption(Bucket="mybucket")

    sse_config = {
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                    "KMSMasterKeyID": "12345678",
                }
            }
        ]
    }

    conn.put_bucket_encryption(
        Bucket="mybucket", ServerSideEncryptionConfiguration=sse_config
    )

    resp = conn.get_bucket_encryption(Bucket="mybucket")
    assert "ServerSideEncryptionConfiguration" in resp
    assert resp["ServerSideEncryptionConfiguration"] == sse_config

    conn.delete_bucket_encryption(Bucket="mybucket")
    with pytest.raises(ClientError) as exc:
        conn.get_bucket_encryption(Bucket="mybucket")


@mock_s3
def test_presigned_put_url_with_approved_headers():
    bucket = str(uuid.uuid4())
    key = "file.txt"
    content = b"filecontent"
    expected_contenttype = "app/sth"
    conn = boto3.resource("s3", region_name="us-east-1")
    conn.create_bucket(Bucket=bucket)
    s3 = boto3.client("s3", region_name="us-east-1")

    # Create a pre-signed url with some metadata.
    url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": expected_contenttype},
    )

    # Verify S3 throws an error when the header is not provided
    response = requests.put(url, data=content)
    response.status_code.should.equal(403)
    str(response.content).should.contain("<Code>SignatureDoesNotMatch</Code>")
    str(response.content).should.contain(
        "<Message>The request signature we calculated does not match the signature you provided. Check your key and signing method.</Message>"
    )

    # Verify S3 throws an error when the header has the wrong value
    response = requests.put(
        url, data=content, headers={"Content-Type": "application/unknown"}
    )
    response.status_code.should.equal(403)
    str(response.content).should.contain("<Code>SignatureDoesNotMatch</Code>")
    str(response.content).should.contain(
        "<Message>The request signature we calculated does not match the signature you provided. Check your key and signing method.</Message>"
    )

    # Verify S3 uploads correctly when providing the meta data
    response = requests.put(
        url, data=content, headers={"Content-Type": expected_contenttype}
    )
    response.status_code.should.equal(200)

    # Assert the object exists
    obj = s3.get_object(Bucket=bucket, Key=key)
    obj["ContentType"].should.equal(expected_contenttype)
    obj["ContentLength"].should.equal(11)
    obj["Body"].read().should.equal(content)
    obj["Metadata"].should.equal({})

    s3.delete_object(Bucket=bucket, Key=key)
    s3.delete_bucket(Bucket=bucket)


@mock_s3
def test_presigned_put_url_with_custom_headers():
    bucket = str(uuid.uuid4())
    key = "file.txt"
    content = b"filecontent"
    conn = boto3.resource("s3", region_name="us-east-1")
    conn.create_bucket(Bucket=bucket)
    s3 = boto3.client("s3", region_name="us-east-1")

    # Create a pre-signed url with some metadata.
    url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": bucket, "Key": key, "Metadata": {"venue": "123"}},
    )

    # Verify S3 uploads correctly when providing the meta data
    response = requests.put(url, data=content)
    response.status_code.should.equal(200)

    # Assert the object exists
    obj = s3.get_object(Bucket=bucket, Key=key)
    obj["ContentLength"].should.equal(11)
    obj["Body"].read().should.equal(content)
    obj["Metadata"].should.equal({"venue": "123"})

    s3.delete_object(Bucket=bucket, Key=key)
    s3.delete_bucket(Bucket=bucket)


@mock_s3
def test_request_partial_content_should_contain_content_length():
    bucket = "bucket"
    object_key = "key"
    s3 = boto3.resource("s3")
    s3.create_bucket(Bucket=bucket)
    s3.Object(bucket, object_key).put(Body="some text")

    file = s3.Object(bucket, object_key)
    response = file.get(Range="bytes=0-1024")
    response["ContentLength"].should.equal(9)


@mock_s3
def test_request_partial_content_should_contain_actual_content_length():
    bucket = "bucket"
    object_key = "key"
    s3 = boto3.resource("s3")
    s3.create_bucket(Bucket=bucket)
    s3.Object(bucket, object_key).put(Body="some text")

    file = s3.Object(bucket, object_key)
    requested_range = "bytes=1024-"
    try:
        file.get(Range=requested_range)
    except botocore.client.ClientError as e:
        e.response["Error"]["Code"].should.equal("InvalidRange")
        e.response["Error"]["Message"].should.equal(
            "The requested range is not satisfiable"
        )
        e.response["Error"]["ActualObjectSize"].should.equal("9")
        e.response["Error"]["RangeRequested"].should.equal(requested_range)


@mock_s3
def test_get_unknown_version_should_throw_specific_error():
    bucket_name = "my_bucket"
    object_key = "hello.txt"
    s3 = boto3.resource("s3", region_name="us-east-1")
    client = boto3.client("s3", region_name="us-east-1")
    bucket = s3.create_bucket(Bucket=bucket_name)
    bucket.Versioning().enable()
    content = "some text"
    s3.Object(bucket_name, object_key).put(Body=content)

    with pytest.raises(ClientError) as e:
        client.get_object(Bucket=bucket_name, Key=object_key, VersionId="unknown")
    e.value.response["Error"]["Code"].should.equal("InvalidArgument")
    e.value.response["Error"]["Message"].should.equal("Invalid version id specified")
    e.value.response["Error"]["ArgumentName"].should.equal("versionId")
    e.value.response["Error"]["ArgumentValue"].should.equal("unknown")


@mock_s3
def test_request_partial_content_without_specifying_range_should_return_full_object():
    bucket = "bucket"
    object_key = "key"
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket)
    s3.Object(bucket, object_key).put(Body="some text that goes a long way")

    file = s3.Object(bucket, object_key)
    response = file.get(Range="")
    response["ContentLength"].should.equal(30)


@mock_s3
def test_object_headers():
    bucket = "my-bucket"
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=bucket)

    res = s3.put_object(
        Bucket=bucket,
        Body=b"test",
        Key="file.txt",
        ServerSideEncryption="aws:kms",
        SSEKMSKeyId="test",
        BucketKeyEnabled=True,
    )
    res.should.have.key("ETag")
    res.should.have.key("ServerSideEncryption")
    res.should.have.key("SSEKMSKeyId")
    res.should.have.key("BucketKeyEnabled")

    res = s3.get_object(Bucket=bucket, Key="file.txt")
    res.should.have.key("ETag")
    res.should.have.key("ServerSideEncryption")
    res.should.have.key("SSEKMSKeyId")
    res.should.have.key("BucketKeyEnabled")
