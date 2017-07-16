# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError
from functools import wraps
from gzip import GzipFile
from io import BytesIO
import zlib

import json
import boto
import boto3
from botocore.client import ClientError
import botocore.exceptions
from boto.exception import S3CreateError, S3ResponseError
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from freezegun import freeze_time
import six
import requests
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises

import sure  # noqa

from moto import settings, mock_s3, mock_s3_deprecated
import moto.s3.models as s3model

if settings.TEST_SERVER_MODE:
    REDUCED_PART_SIZE = s3model.UPLOAD_PART_MIN_SIZE
    EXPECTED_ETAG = '"140f92a6df9f9e415f74a1463bcee9bb-2"'
else:
    REDUCED_PART_SIZE = 256
    EXPECTED_ETAG = '"66d1a1a2ed08fd05c137f316af4ff255-2"'


def reduced_min_part_size(f):
    """ speed up tests by temporarily making the multipart minimum part size
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
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.put_object(Bucket='mybucket', Key=self.name, Body=self.value)


@mock_s3
def test_my_model_save():
    # Create Bucket so that test can run
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='mybucket')
    ####################################

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    body = conn.Object('mybucket', 'steve').get()[
        'Body'].read().decode("utf-8")

    assert body == 'is awesome'


@mock_s3
def test_key_etag():
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='mybucket')

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn.Bucket('mybucket').Object('steve').e_tag.should.equal(
        '"d32bda93738f7e03adb22e66c90fbc04"')


@mock_s3_deprecated
def test_multipart_upload_too_small():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    multipart.upload_part_from_file(BytesIO(b'hello'), 1)
    multipart.upload_part_from_file(BytesIO(b'world'), 2)
    # Multipart with total size under 5MB is refused
    multipart.complete_upload.should.throw(S3ResponseError)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # last part, can be less than 5 MB
    part2 = b'1'
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key(
        "the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload_out_of_order():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    # last part, can be less than 5 MB
    part2 = b'1'
    multipart.upload_part_from_file(BytesIO(part2), 4)
    part1 = b'0' * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key(
        "the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload_with_headers():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload(
        "the-key", metadata={"foo": "bar"})
    part1 = b'0' * 10
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.complete_upload()

    key = bucket.get_key("the-key")
    key.metadata.should.equal({"foo": "bar"})


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload_with_copy_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "original-key"
    key.set_contents_from_string("key_value")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.copy_part_from_key("foobar", "original-key", 2, 0, 3)
    multipart.complete_upload()
    bucket.get_key(
        "the-key").get_contents_as_string().should.equal(part1 + b"key_")


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_upload_cancel():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.cancel_upload()
    # TODO we really need some sort of assertion here, but we don't currently
    # have the ability to list mulipart uploads for a bucket.


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_etag():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('mybucket')

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # last part, can be less than 5 MB
    part2 = b'1'
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key("the-key").etag.should.equal(EXPECTED_ETAG)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_invalid_order():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('mybucket')

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * 5242880
    etag1 = multipart.upload_part_from_file(BytesIO(part1), 1).etag
    # last part, can be less than 5 MB
    part2 = b'1'
    etag2 = multipart.upload_part_from_file(BytesIO(part2), 2).etag
    xml = "<Part><PartNumber>{0}</PartNumber><ETag>{1}</ETag></Part>"
    xml = xml.format(2, etag2) + xml.format(1, etag1)
    xml = "<CompleteMultipartUpload>{0}</CompleteMultipartUpload>".format(xml)
    bucket.complete_multipart_upload.when.called_with(
        multipart.key_name, multipart.id, xml).should.throw(S3ResponseError)


@mock_s3_deprecated
@reduced_min_part_size
def test_multipart_duplicate_upload():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * REDUCED_PART_SIZE
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # same part again
    multipart.upload_part_from_file(BytesIO(part1), 1)
    part2 = b'1' * 1024
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # We should get only one copy of part 1.
    bucket.get_key(
        "the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3_deprecated
def test_list_multiparts():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('mybucket')

    multipart1 = bucket.initiate_multipart_upload("one-key")
    multipart2 = bucket.initiate_multipart_upload("two-key")
    uploads = bucket.get_all_multipart_uploads()
    uploads.should.have.length_of(2)
    dict([(u.key_name, u.id) for u in uploads]).should.equal(
        {'one-key': multipart1.id, 'two-key': multipart2.id})
    multipart2.cancel_upload()
    uploads = bucket.get_all_multipart_uploads()
    uploads.should.have.length_of(1)
    uploads[0].key_name.should.equal("one-key")
    multipart1.cancel_upload()
    uploads = bucket.get_all_multipart_uploads()
    uploads.should.be.empty


@mock_s3_deprecated
def test_key_save_to_missing_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.get_bucket('mybucket', validate=False)

    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string.when.called_with(
        "foobar").should.throw(S3ResponseError)


@mock_s3_deprecated
def test_missing_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    bucket.get_key("the-key").should.equal(None)


@mock_s3_deprecated
def test_missing_key_urllib2():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket("foobar")

    urlopen.when.called_with(
        "http://foobar.s3.amazonaws.com/the-key").should.throw(HTTPError)


@mock_s3_deprecated
def test_empty_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("")

    key = bucket.get_key("the-key")
    key.size.should.equal(0)
    key.get_contents_as_string().should.equal(b'')


@mock_s3_deprecated
def test_empty_key_set_on_existing_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar")

    key = bucket.get_key("the-key")
    key.size.should.equal(6)
    key.get_contents_as_string().should.equal(b'foobar')

    key.set_contents_from_string("")
    bucket.get_key("the-key").get_contents_as_string().should.equal(b'')


@mock_s3_deprecated
def test_large_key_save():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar" * 100000)

    bucket.get_key(
        "the-key").get_contents_as_string().should.equal(b'foobar' * 100000)


@mock_s3_deprecated
def test_copy_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key')

    bucket.get_key(
        "the-key").get_contents_as_string().should.equal(b"some value")
    bucket.get_key(
        "new-key").get_contents_as_string().should.equal(b"some value")


@mock_s3_deprecated
def test_copy_key_with_version():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    bucket.configure_versioning(versioning=True)
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")
    key.set_contents_from_string("another value")

    bucket.copy_key('new-key', 'foobar', 'the-key', src_version_id='0')

    bucket.get_key(
        "the-key").get_contents_as_string().should.equal(b"another value")
    bucket.get_key(
        "new-key").get_contents_as_string().should.equal(b"some value")


@mock_s3_deprecated
def test_set_metadata():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = 'the-key'
    key.set_metadata('md', 'Metadatastring')
    key.set_contents_from_string("Testval")

    bucket.get_key('the-key').get_metadata('md').should.equal('Metadatastring')


@mock_s3_deprecated
def test_copy_key_replace_metadata():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_metadata('md', 'Metadatastring')
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key',
                    metadata={'momd': 'Mometadatastring'})

    bucket.get_key("new-key").get_metadata('md').should.be.none
    bucket.get_key(
        "new-key").get_metadata('momd').should.equal('Mometadatastring')


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
    rs[0].last_modified.should.equal('2012-01-01T12:00:00.000Z')

    bucket.get_key(
        "the-key").last_modified.should.equal('Sun, 01 Jan 2012 12:00:00 GMT')


@mock_s3_deprecated
def test_missing_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.get_bucket.when.called_with('mybucket').should.throw(S3ResponseError)


@mock_s3_deprecated
def test_bucket_with_dash():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.get_bucket.when.called_with(
        'mybucket-test').should.throw(S3ResponseError)


@mock_s3_deprecated
def test_create_existing_bucket():
    "Trying to create a bucket that already exists should raise an Error"
    conn = boto.s3.connect_to_region("us-west-2")
    conn.create_bucket("foobar")
    with assert_raises(S3CreateError):
        conn.create_bucket('foobar')


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
    conn = boto.s3.connect_to_region("us-east-1")
    conn.create_bucket("foobar")
    bucket = conn.create_bucket("foobar")
    bucket.name.should.equal("foobar")


@mock_s3_deprecated
def test_other_region():
    conn = S3Connection(
        'key', 'secret', host='s3-website-ap-southeast-2.amazonaws.com')
    conn.create_bucket("foobar")
    list(conn.get_bucket("foobar").get_all_keys()).should.equal([])


@mock_s3_deprecated
def test_bucket_deletion():
    conn = boto.connect_s3('the_key', 'the_secret')
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

    # Delete non-existant bucket
    conn.delete_bucket.when.called_with("foobar").should.throw(S3ResponseError)


@mock_s3_deprecated
def test_get_all_buckets():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket("foobar")
    conn.create_bucket("foobar2")
    buckets = conn.get_all_buckets()

    buckets.should.have.length_of(2)


@mock_s3
@mock_s3_deprecated
def test_post_to_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://foobar.s3.amazonaws.com/", {
        'key': 'the-key',
        'file': 'nothing'
    })

    bucket.get_key('the-key').get_contents_as_string().should.equal(b'nothing')


@mock_s3
@mock_s3_deprecated
def test_post_with_metadata_to_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://foobar.s3.amazonaws.com/", {
        'key': 'the-key',
        'file': 'nothing',
        'x-amz-meta-test': 'metadata'
    })

    bucket.get_key('the-key').get_metadata('test').should.equal('metadata')


@mock_s3_deprecated
def test_delete_missing_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('foobar')

    deleted_key = bucket.delete_key("foobar")
    deleted_key.key.should.equal("foobar")


@mock_s3_deprecated
def test_delete_keys():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('foobar')

    Key(bucket=bucket, name='file1').set_contents_from_string('abc')
    Key(bucket=bucket, name='file2').set_contents_from_string('abc')
    Key(bucket=bucket, name='file3').set_contents_from_string('abc')
    Key(bucket=bucket, name='file4').set_contents_from_string('abc')

    result = bucket.delete_keys(['file2', 'file3'])
    result.deleted.should.have.length_of(2)
    result.errors.should.have.length_of(0)
    keys = bucket.get_all_keys()
    keys.should.have.length_of(2)
    keys[0].name.should.equal('file1')


@mock_s3_deprecated
def test_delete_keys_with_invalid():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('foobar')

    Key(bucket=bucket, name='file1').set_contents_from_string('abc')
    Key(bucket=bucket, name='file2').set_contents_from_string('abc')
    Key(bucket=bucket, name='file3').set_contents_from_string('abc')
    Key(bucket=bucket, name='file4').set_contents_from_string('abc')

    result = bucket.delete_keys(['abc', 'file3'])

    result.deleted.should.have.length_of(1)
    result.errors.should.have.length_of(1)
    keys = bucket.get_all_keys()
    keys.should.have.length_of(3)
    keys[0].name.should.equal('file1')


@mock_s3_deprecated
def test_bucket_name_with_dot():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('firstname.lastname')

    k = Key(bucket, 'somekey')
    k.set_contents_from_string('somedata')


@mock_s3_deprecated
def test_key_with_special_characters():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket_name')

    key = Key(bucket, 'test_list_keys_2/x?y')
    key.set_contents_from_string('value1')

    key_list = bucket.list('test_list_keys_2/', '/')
    keys = [x for x in key_list]
    keys[0].name.should.equal("test_list_keys_2/x?y")


@mock_s3_deprecated
def test_unicode_key_with_slash():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "/the-key-unîcode/test"
    key.set_contents_from_string("value")

    key = bucket.get_key("/the-key-unîcode/test")
    key.get_contents_as_string().should.equal(b'value')


@mock_s3_deprecated
def test_bucket_key_listing_order():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket')
    prefix = 'toplevel/'

    def store(name):
        k = Key(bucket, prefix + name)
        k.set_contents_from_string('somedata')

    names = ['x/key', 'y.key1', 'y.key2', 'y.key3', 'x/y/key', 'x/y/z/key']

    for name in names:
        store(name)

    delimiter = None
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal([
        'toplevel/x/key', 'toplevel/x/y/key', 'toplevel/x/y/z/key',
        'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3'
    ])

    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal([
        'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3', 'toplevel/x/'
    ])

    # Test delimiter with no prefix
    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix=None, delimiter=delimiter)]
    keys.should.equal(['toplevel/'])

    delimiter = None
    keys = [x.name for x in bucket.list(prefix + 'x', delimiter)]
    keys.should.equal(
        [u'toplevel/x/key', u'toplevel/x/y/key', u'toplevel/x/y/z/key'])

    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix + 'x', delimiter)]
    keys.should.equal([u'toplevel/x/'])


@mock_s3_deprecated
def test_key_with_reduced_redundancy():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket_name')

    key = Key(bucket, 'test_rr_key')
    key.set_contents_from_string('value1', reduced_redundancy=True)
    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    list(bucket)[0].storage_class.should.equal('REDUCED_REDUNDANCY')


@mock_s3_deprecated
def test_copy_key_reduced_redundancy():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key',
                    storage_class='REDUCED_REDUNDANCY')

    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    keys = dict([(k.name, k) for k in bucket])
    keys['new-key'].storage_class.should.equal("REDUCED_REDUNDANCY")
    keys['the-key'].storage_class.should.equal("STANDARD")


@freeze_time("2012-01-01 12:00:00")
@mock_s3_deprecated
def test_restore_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")
    list(bucket)[0].ongoing_restore.should.be.none
    key.restore(1)
    key = bucket.get_key('the-key')
    key.ongoing_restore.should_not.be.none
    key.ongoing_restore.should.be.false
    key.expiry_date.should.equal("Mon, 02 Jan 2012 12:00:00 GMT")
    key.restore(2)
    key = bucket.get_key('the-key')
    key.ongoing_restore.should_not.be.none
    key.ongoing_restore.should.be.false
    key.expiry_date.should.equal("Tue, 03 Jan 2012 12:00:00 GMT")


@freeze_time("2012-01-01 12:00:00")
@mock_s3_deprecated
def test_restore_key_headers():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")
    key.restore(1, headers={'foo': 'bar'})
    key = bucket.get_key('the-key')
    key.ongoing_restore.should_not.be.none
    key.ongoing_restore.should.be.false
    key.expiry_date.should.equal("Mon, 02 Jan 2012 12:00:00 GMT")


@mock_s3_deprecated
def test_get_versioning_status():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('foobar')
    d = bucket.get_versioning_status()
    d.should.be.empty

    bucket.configure_versioning(versioning=True)
    d = bucket.get_versioning_status()
    d.shouldnt.be.empty
    d.should.have.key('Versioning').being.equal('Enabled')

    bucket.configure_versioning(versioning=False)
    d = bucket.get_versioning_status()
    d.should.have.key('Versioning').being.equal('Suspended')


@mock_s3_deprecated
def test_key_version():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('foobar')
    bucket.configure_versioning(versioning=True)

    key = Key(bucket)
    key.key = 'the-key'
    key.version_id.should.be.none
    key.set_contents_from_string('some string')
    key.version_id.should.equal('0')
    key.set_contents_from_string('some string')
    key.version_id.should.equal('1')

    key = bucket.get_key('the-key')
    key.version_id.should.equal('1')


@mock_s3_deprecated
def test_list_versions():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('foobar')
    bucket.configure_versioning(versioning=True)

    key = Key(bucket, 'the-key')
    key.version_id.should.be.none
    key.set_contents_from_string("Version 1")
    key.version_id.should.equal('0')
    key.set_contents_from_string("Version 2")
    key.version_id.should.equal('1')

    versions = list(bucket.list_versions())

    versions.should.have.length_of(2)

    versions[0].name.should.equal('the-key')
    versions[0].version_id.should.equal('0')
    versions[0].get_contents_as_string().should.equal(b"Version 1")

    versions[1].name.should.equal('the-key')
    versions[1].version_id.should.equal('1')
    versions[1].get_contents_as_string().should.equal(b"Version 2")


@mock_s3_deprecated
def test_acl_setting():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('foobar')
    content = b'imafile'
    keyname = 'test.txt'

    key = Key(bucket, name=keyname)
    key.content_type = 'text/plain'
    key.set_contents_from_string(content)
    key.make_public()

    key = bucket.get_key(keyname)

    assert key.get_contents_as_string() == content

    grants = key.get_acl().acl.grants
    assert any(g.uri == 'http://acs.amazonaws.com/groups/global/AllUsers' and
               g.permission == 'READ' for g in grants), grants


@mock_s3_deprecated
def test_acl_setting_via_headers():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('foobar')
    content = b'imafile'
    keyname = 'test.txt'

    key = Key(bucket, name=keyname)
    key.content_type = 'text/plain'
    key.set_contents_from_string(content, headers={
        'x-amz-grant-full-control': 'uri="http://acs.amazonaws.com/groups/global/AllUsers"'
    })

    key = bucket.get_key(keyname)

    assert key.get_contents_as_string() == content

    grants = key.get_acl().acl.grants
    assert any(g.uri == 'http://acs.amazonaws.com/groups/global/AllUsers' and
               g.permission == 'FULL_CONTROL' for g in grants), grants


@mock_s3_deprecated
def test_acl_switching():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('foobar')
    content = b'imafile'
    keyname = 'test.txt'

    key = Key(bucket, name=keyname)
    key.content_type = 'text/plain'
    key.set_contents_from_string(content, policy='public-read')
    key.set_acl('private')

    grants = key.get_acl().acl.grants
    assert not any(g.uri == 'http://acs.amazonaws.com/groups/global/AllUsers' and
                   g.permission == 'READ' for g in grants), grants


@mock_s3_deprecated
def test_bucket_acl_setting():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('foobar')

    bucket.make_public()

    grants = bucket.get_acl().acl.grants
    assert any(g.uri == 'http://acs.amazonaws.com/groups/global/AllUsers' and
               g.permission == 'READ' for g in grants), grants


@mock_s3_deprecated
def test_bucket_acl_switching():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('foobar')
    bucket.make_public()

    bucket.set_acl('private')

    grants = bucket.get_acl().acl.grants
    assert not any(g.uri == 'http://acs.amazonaws.com/groups/global/AllUsers' and
                   g.permission == 'READ' for g in grants), grants


@mock_s3_deprecated
def test_unicode_key():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('mybucket')
    key = Key(bucket)
    key.key = u'こんにちは.jpg'
    key.set_contents_from_string('Hello world!')
    assert [listed_key.key for listed_key in bucket.list()] == [key.key]
    fetched_key = bucket.get_key(key.key)
    assert fetched_key.key == key.key
    assert fetched_key.get_contents_as_string().decode("utf-8") == 'Hello world!'


@mock_s3_deprecated
def test_unicode_value():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('mybucket')
    key = Key(bucket)
    key.key = 'some_key'
    key.set_contents_from_string(u'こんにちは.jpg')
    list(bucket.list())
    key = bucket.get_key(key.key)
    assert key.get_contents_as_string().decode("utf-8") == u'こんにちは.jpg'


@mock_s3_deprecated
def test_setting_content_encoding():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('mybucket')
    key = bucket.new_key("keyname")
    key.set_metadata("Content-Encoding", "gzip")
    compressed_data = "abcdef"
    key.set_contents_from_string(compressed_data)

    key = bucket.get_key("keyname")
    key.content_encoding.should.equal("gzip")


@mock_s3_deprecated
def test_bucket_location():
    conn = boto.s3.connect_to_region("us-west-2")
    bucket = conn.create_bucket('mybucket')
    bucket.get_location().should.equal("us-west-2")


@mock_s3_deprecated
def test_ranged_get():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('mybucket')
    key = Key(bucket)
    key.key = 'bigkey'
    rep = b"0123456789"
    key.set_contents_from_string(rep * 10)

    # Implicitly bounded range requests.
    key.get_contents_as_string(
        headers={'Range': 'bytes=0-'}).should.equal(rep * 10)
    key.get_contents_as_string(
        headers={'Range': 'bytes=50-'}).should.equal(rep * 5)
    key.get_contents_as_string(
        headers={'Range': 'bytes=99-'}).should.equal(b'9')

    # Explicitly bounded range requests starting from the first byte.
    key.get_contents_as_string(
        headers={'Range': 'bytes=0-0'}).should.equal(b'0')
    key.get_contents_as_string(
        headers={'Range': 'bytes=0-49'}).should.equal(rep * 5)
    key.get_contents_as_string(
        headers={'Range': 'bytes=0-99'}).should.equal(rep * 10)
    key.get_contents_as_string(
        headers={'Range': 'bytes=0-100'}).should.equal(rep * 10)
    key.get_contents_as_string(
        headers={'Range': 'bytes=0-700'}).should.equal(rep * 10)

    # Explicitly bounded range requests starting from the / a middle byte.
    key.get_contents_as_string(
        headers={'Range': 'bytes=50-54'}).should.equal(rep[:5])
    key.get_contents_as_string(
        headers={'Range': 'bytes=50-99'}).should.equal(rep * 5)
    key.get_contents_as_string(
        headers={'Range': 'bytes=50-100'}).should.equal(rep * 5)
    key.get_contents_as_string(
        headers={'Range': 'bytes=50-700'}).should.equal(rep * 5)

    # Explicitly bounded range requests starting from the last byte.
    key.get_contents_as_string(
        headers={'Range': 'bytes=99-99'}).should.equal(b'9')
    key.get_contents_as_string(
        headers={'Range': 'bytes=99-100'}).should.equal(b'9')
    key.get_contents_as_string(
        headers={'Range': 'bytes=99-700'}).should.equal(b'9')

    # Suffix range requests.
    key.get_contents_as_string(
        headers={'Range': 'bytes=-1'}).should.equal(b'9')
    key.get_contents_as_string(
        headers={'Range': 'bytes=-60'}).should.equal(rep * 6)
    key.get_contents_as_string(
        headers={'Range': 'bytes=-100'}).should.equal(rep * 10)
    key.get_contents_as_string(
        headers={'Range': 'bytes=-101'}).should.equal(rep * 10)
    key.get_contents_as_string(
        headers={'Range': 'bytes=-700'}).should.equal(rep * 10)

    key.size.should.equal(100)


@mock_s3_deprecated
def test_policy():
    conn = boto.connect_s3()
    bucket_name = 'mybucket'
    bucket = conn.create_bucket(bucket_name)

    policy = json.dumps({
        "Version": "2012-10-17",
        "Id": "PutObjPolicy",
        "Statement": [
            {
                "Sid": "DenyUnEncryptedObjectUploads",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:PutObject",
                "Resource": "arn:aws:s3:::{bucket_name}/*".format(bucket_name=bucket_name),
                "Condition": {
                    "StringNotEquals": {
                        "s3:x-amz-server-side-encryption": "aws:kms"
                    }
                }
            }
        ]
    })

    with assert_raises(S3ResponseError) as err:
        bucket.get_policy()

    ex = err.exception
    ex.box_usage.should.be.none
    ex.error_code.should.equal('NoSuchBucketPolicy')
    ex.message.should.equal('The bucket policy does not exist')
    ex.reason.should.equal('Not Found')
    ex.resource.should.be.none
    ex.status.should.equal(404)
    ex.body.should.contain(bucket_name)
    ex.request_id.should_not.be.none

    bucket.set_policy(policy).should.be.true

    bucket = conn.get_bucket(bucket_name)

    bucket.get_policy().decode('utf-8').should.equal(policy)

    bucket.delete_policy()

    with assert_raises(S3ResponseError) as err:
        bucket.get_policy()


@mock_s3_deprecated
def test_website_configuration_xml():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test-bucket')
    bucket.set_website_configuration_xml(TEST_XML)
    bucket.get_website_configuration_xml().should.equal(TEST_XML)


@mock_s3_deprecated
def test_key_with_trailing_slash_in_ordinary_calling_format():
    conn = boto.connect_s3(
        'access_key',
        'secret_key',
        calling_format=boto.s3.connection.OrdinaryCallingFormat()
    )
    bucket = conn.create_bucket('test_bucket_name')

    key_name = 'key_with_slash/'

    key = Key(bucket, key_name)
    key.set_contents_from_string('some value')

    [k.name for k in bucket.get_all_keys()].should.contain(key_name)


"""
boto3
"""


@mock_s3
def test_boto3_key_etag():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='mybucket')
    s3.put_object(Bucket='mybucket', Key='steve', Body=b'is awesome')
    resp = s3.get_object(Bucket='mybucket', Key='steve')
    resp['ETag'].should.equal('"d32bda93738f7e03adb22e66c90fbc04"')

@mock_s3
def test_website_redirect_location():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='mybucket')

    s3.put_object(Bucket='mybucket', Key='steve', Body=b'is awesome')
    resp = s3.get_object(Bucket='mybucket', Key='steve')
    resp.get('WebsiteRedirectLocation').should.be.none

    url = 'https://github.com/spulec/moto'
    s3.put_object(Bucket='mybucket', Key='steve', Body=b'is awesome', WebsiteRedirectLocation=url)
    resp = s3.get_object(Bucket='mybucket', Key='steve')
    resp['WebsiteRedirectLocation'].should.equal(url)

@mock_s3
def test_boto3_list_keys_xml_escaped():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='mybucket')
    key_name = 'Q&A.txt'
    s3.put_object(Bucket='mybucket', Key=key_name, Body=b'is awesome')

    resp = s3.list_objects_v2(Bucket='mybucket', Prefix=key_name)

    assert resp['Contents'][0]['Key'] == key_name
    assert resp['KeyCount'] == 1
    assert resp['MaxKeys'] == 1000
    assert resp['Prefix'] == key_name
    assert resp['IsTruncated'] == False
    assert 'Delimiter' not in resp
    assert 'StartAfter' not in resp
    assert 'NextContinuationToken' not in resp
    assert 'Owner' not in resp['Contents'][0]


@mock_s3
def test_boto3_list_objects_v2_truncated_response():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='mybucket')
    s3.put_object(Bucket='mybucket', Key='one', Body=b'1')
    s3.put_object(Bucket='mybucket', Key='two', Body=b'22')
    s3.put_object(Bucket='mybucket', Key='three', Body=b'333')

    # First list
    resp = s3.list_objects_v2(Bucket='mybucket', MaxKeys=1)
    listed_object = resp['Contents'][0]

    assert listed_object['Key'] == 'one'
    assert resp['MaxKeys'] == 1
    assert resp['Prefix'] == ''
    assert resp['KeyCount'] == 1
    assert resp['IsTruncated'] == True
    assert 'Delimiter' not in resp
    assert 'StartAfter' not in resp
    assert 'Owner' not in listed_object  # owner info was not requested

    next_token = resp['NextContinuationToken']

    # Second list
    resp = s3.list_objects_v2(
        Bucket='mybucket', MaxKeys=1, ContinuationToken=next_token)
    listed_object = resp['Contents'][0]

    assert listed_object['Key'] == 'three'
    assert resp['MaxKeys'] == 1
    assert resp['Prefix'] == ''
    assert resp['KeyCount'] == 1
    assert resp['IsTruncated'] == True
    assert 'Delimiter' not in resp
    assert 'StartAfter' not in resp
    assert 'Owner' not in listed_object

    next_token = resp['NextContinuationToken']

    # Third list
    resp = s3.list_objects_v2(
        Bucket='mybucket', MaxKeys=1, ContinuationToken=next_token)
    listed_object = resp['Contents'][0]

    assert listed_object['Key'] == 'two'
    assert resp['MaxKeys'] == 1
    assert resp['Prefix'] == ''
    assert resp['KeyCount'] == 1
    assert resp['IsTruncated'] == False
    assert 'Delimiter' not in resp
    assert 'Owner' not in listed_object
    assert 'StartAfter' not in resp
    assert 'NextContinuationToken' not in resp


@mock_s3
def test_boto3_list_objects_v2_truncated_response_start_after():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='mybucket')
    s3.put_object(Bucket='mybucket', Key='one', Body=b'1')
    s3.put_object(Bucket='mybucket', Key='two', Body=b'22')
    s3.put_object(Bucket='mybucket', Key='three', Body=b'333')

    # First list
    resp = s3.list_objects_v2(Bucket='mybucket', MaxKeys=1, StartAfter='one')
    listed_object = resp['Contents'][0]

    assert listed_object['Key'] == 'three'
    assert resp['MaxKeys'] == 1
    assert resp['Prefix'] == ''
    assert resp['KeyCount'] == 1
    assert resp['IsTruncated'] == True
    assert resp['StartAfter'] == 'one'
    assert 'Delimiter' not in resp
    assert 'Owner' not in listed_object

    next_token = resp['NextContinuationToken']

    # Second list
    # The ContinuationToken must take precedence over StartAfter.
    resp = s3.list_objects_v2(Bucket='mybucket', MaxKeys=1, StartAfter='one',
                              ContinuationToken=next_token)
    listed_object = resp['Contents'][0]

    assert listed_object['Key'] == 'two'
    assert resp['MaxKeys'] == 1
    assert resp['Prefix'] == ''
    assert resp['KeyCount'] == 1
    assert resp['IsTruncated'] == False
    # When ContinuationToken is given, StartAfter is ignored. This also means
    # AWS does not return it in the response.
    assert 'StartAfter' not in resp
    assert 'Delimiter' not in resp
    assert 'Owner' not in listed_object


@mock_s3
def test_boto3_list_objects_v2_fetch_owner():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='mybucket')
    s3.put_object(Bucket='mybucket', Key='one', Body=b'11')

    resp = s3.list_objects_v2(Bucket='mybucket', FetchOwner=True)
    owner = resp['Contents'][0]['Owner']

    assert 'ID' in owner
    assert 'DisplayName' in owner
    assert len(owner.keys()) == 2


@mock_s3
def test_boto3_bucket_create():
    s3 = boto3.resource('s3', region_name='us-east-1')
    s3.create_bucket(Bucket="blah")

    s3.Object('blah', 'hello.txt').put(Body="some text")

    s3.Object('blah', 'hello.txt').get()['Body'].read().decode(
        "utf-8").should.equal("some text")


@mock_s3
def test_bucket_create_duplicate():
    s3 = boto3.resource('s3', region_name='us-west-2')
    s3.create_bucket(Bucket="blah", CreateBucketConfiguration={
        'LocationConstraint': 'us-west-2',
    })
    with assert_raises(ClientError) as exc:
        s3.create_bucket(
            Bucket="blah",
            CreateBucketConfiguration={
                'LocationConstraint': 'us-west-2',
            }
        )
    exc.exception.response['Error']['Code'].should.equal('BucketAlreadyExists')


@mock_s3
def test_boto3_bucket_create_eu_central():
    s3 = boto3.resource('s3', region_name='eu-central-1')
    s3.create_bucket(Bucket="blah")

    s3.Object('blah', 'hello.txt').put(Body="some text")

    s3.Object('blah', 'hello.txt').get()['Body'].read().decode(
        "utf-8").should.equal("some text")


@mock_s3
def test_boto3_head_object():
    s3 = boto3.resource('s3', region_name='us-east-1')
    s3.create_bucket(Bucket="blah")

    s3.Object('blah', 'hello.txt').put(Body="some text")

    s3.Object('blah', 'hello.txt').meta.client.head_object(
        Bucket='blah', Key='hello.txt')

    with assert_raises(ClientError) as e:
        s3.Object('blah', 'hello2.txt').meta.client.head_object(
            Bucket='blah', Key='hello_bad.txt')
    e.exception.response['Error']['Code'].should.equal('404')


@mock_s3
def test_boto3_get_object():
    s3 = boto3.resource('s3', region_name='us-east-1')
    s3.create_bucket(Bucket="blah")

    s3.Object('blah', 'hello.txt').put(Body="some text")

    s3.Object('blah', 'hello.txt').meta.client.head_object(
        Bucket='blah', Key='hello.txt')

    with assert_raises(ClientError) as e:
        s3.Object('blah', 'hello2.txt').get()

    e.exception.response['Error']['Code'].should.equal('NoSuchKey')


@mock_s3
def test_boto3_head_object_with_versioning():
    s3 = boto3.resource('s3', region_name='us-east-1')
    bucket = s3.create_bucket(Bucket='blah')
    bucket.Versioning().enable()

    old_content = 'some text'
    new_content = 'some new text'
    s3.Object('blah', 'hello.txt').put(Body=old_content)
    s3.Object('blah', 'hello.txt').put(Body=new_content)

    head_object = s3.Object('blah', 'hello.txt').meta.client.head_object(
        Bucket='blah', Key='hello.txt')
    head_object['VersionId'].should.equal('1')
    head_object['ContentLength'].should.equal(len(new_content))

    old_head_object = s3.Object('blah', 'hello.txt').meta.client.head_object(
        Bucket='blah', Key='hello.txt', VersionId='0')
    old_head_object['VersionId'].should.equal('0')
    old_head_object['ContentLength'].should.equal(len(old_content))


@mock_s3
def test_boto3_head_object_if_modified_since():
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = 'hello.txt'

    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body='test'
    )

    with assert_raises(botocore.exceptions.ClientError) as err:
        s3.head_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        )
    e = err.exception
    e.response['Error'].should.equal({'Code': '304', 'Message': 'Not Modified'})


@mock_s3
@reduced_min_part_size
def test_boto3_multipart_etag():
    # Create Bucket so that test can run
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='mybucket')

    upload_id = s3.create_multipart_upload(
        Bucket='mybucket', Key='the-key')['UploadId']
    part1 = b'0' * REDUCED_PART_SIZE
    etags = []
    etags.append(
        s3.upload_part(Bucket='mybucket', Key='the-key', PartNumber=1,
                       UploadId=upload_id, Body=part1)['ETag'])
    # last part, can be less than 5 MB
    part2 = b'1'
    etags.append(
        s3.upload_part(Bucket='mybucket', Key='the-key', PartNumber=2,
                       UploadId=upload_id, Body=part2)['ETag'])
    s3.complete_multipart_upload(
        Bucket='mybucket', Key='the-key', UploadId=upload_id,
        MultipartUpload={'Parts': [{'ETag': etag, 'PartNumber': i}
                                   for i, etag in enumerate(etags, 1)]})
    # we should get both parts as the key contents
    resp = s3.get_object(Bucket='mybucket', Key='the-key')
    resp['ETag'].should.equal(EXPECTED_ETAG)


@mock_s3
def test_boto3_put_object_with_tagging():
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'mybucket'
    key = 'key-with-tags'
    s3.create_bucket(Bucket=bucket_name)

    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body='test',
        Tagging='foo=bar',
    )

    resp = s3.get_object_tagging(Bucket=bucket_name, Key=key)

    resp['TagSet'].should.contain({'Key': 'foo', 'Value': 'bar'})


@mock_s3
def test_boto3_put_object_tagging():
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'mybucket'
    key = 'key-with-tags'
    s3.create_bucket(Bucket=bucket_name)

    with assert_raises(ClientError) as err:
        s3.put_object_tagging(
            Bucket=bucket_name,
            Key=key,
            Tagging={'TagSet': [
                {'Key': 'item1', 'Value': 'foo'},
                {'Key': 'item2', 'Value': 'bar'},
            ]}
        )

    e = err.exception
    e.response['Error'].should.equal({
        'Code': 'NoSuchKey',
        'Message': 'The specified key does not exist.',
        'RequestID': '7a62c49f-347e-4fc4-9331-6e8eEXAMPLE',
    })

    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body='test'
    )

    resp = s3.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={'TagSet': [
            {'Key': 'item1', 'Value': 'foo'},
            {'Key': 'item2', 'Value': 'bar'},
        ]}
    )

    resp['ResponseMetadata']['HTTPStatusCode'].should.equal(200)


@mock_s3
def test_boto3_get_object_tagging():
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'mybucket'
    key = 'key-with-tags'
    s3.create_bucket(Bucket=bucket_name)

    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body='test'
    )

    resp = s3.get_object_tagging(Bucket=bucket_name, Key=key)
    resp['TagSet'].should.have.length_of(0)

    resp = s3.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={'TagSet': [
            {'Key': 'item1', 'Value': 'foo'},
            {'Key': 'item2', 'Value': 'bar'},
        ]}
    )
    resp = s3.get_object_tagging(Bucket=bucket_name, Key=key)

    resp['TagSet'].should.have.length_of(2)
    resp['TagSet'].should.contain({'Key': 'item1', 'Value': 'foo'})
    resp['TagSet'].should.contain({'Key': 'item2', 'Value': 'bar'})


@mock_s3
def test_boto3_list_object_versions():
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'mybucket'
    key = 'key-with-versions'
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={
            'Status': 'Enabled'
        }
    )
    items = (six.b('v1'), six.b('v2'))
    for body in items:
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=body
        )
    response = s3.list_object_versions(
        Bucket=bucket_name
    )
    # Two object versions should be returned
    len(response['Versions']).should.equal(2)
    keys = set([item['Key'] for item in response['Versions']])
    keys.should.equal({key})
    # Test latest object version is returned
    response = s3.get_object(Bucket=bucket_name, Key=key)
    response['Body'].read().should.equal(items[-1])


@mock_s3
def test_boto3_delete_markers():
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'mybucket'
    key = 'key-with-versions'
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={
            'Status': 'Enabled'
        }
    )
    items = (six.b('v1'), six.b('v2'))
    for body in items:
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=body
        )
    s3.delete_object(
        Bucket=bucket_name,
        Key=key
    )
    with assert_raises(ClientError) as e:
        s3.get_object(
            Bucket=bucket_name,
            Key=key
        )
        e.response['Error']['Code'].should.equal('404')

    s3.delete_object(
        Bucket=bucket_name,
        Key=key,
        VersionId='2'
    )
    response = s3.get_object(
        Bucket=bucket_name,
        Key=key
    )
    response['Body'].read().should.equal(items[-1])
    response = s3.list_object_versions(
        Bucket=bucket_name
    )
    response['Versions'].should.have.length_of(2)
    response['Versions'][-1]['IsLatest'].should.be.true
    response['Versions'][0]['IsLatest'].should.be.false
    [(key_metadata['Key'], key_metadata['VersionId'])
     for key_metadata in response['Versions']].should.equal(
        [('key-with-versions', '0'), ('key-with-versions', '1')]
    )


@mock_s3
def test_get_stream_gzipped():
    payload = b"this is some stuff here"

    s3_client = boto3.client("s3", region_name='us-east-1')
    s3_client.create_bucket(Bucket='moto-tests')
    buffer_ = BytesIO()
    with GzipFile(fileobj=buffer_, mode='w') as f:
        f.write(payload)
    payload_gz = buffer_.getvalue()

    s3_client.put_object(
        Bucket='moto-tests',
        Key='keyname',
        Body=payload_gz,
        ContentEncoding='gzip',
    )

    obj = s3_client.get_object(
        Bucket='moto-tests',
        Key='keyname',
    )
    res = zlib.decompress(obj['Body'].read(), 16+zlib.MAX_WBITS)
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

