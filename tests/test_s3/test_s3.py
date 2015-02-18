# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError
from io import BytesIO

import boto
from urllib import quote
from boto.exception import S3CreateError, S3ResponseError
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from freezegun import freeze_time
import requests
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises

import sure  # noqa

from moto import mock_s3
from tests.helpers import requires_boto_gte


REDUCED_PART_SIZE = 256


def reduced_min_part_size(f):
    """ speed up tests by temporarily making the multipart minimum part size
        small
    """
    import moto.s3.models as s3model
    orig_size = s3model.UPLOAD_PART_MIN_SIZE

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
        conn = boto.connect_s3('the_key', 'the_secret')
        bucket = conn.get_bucket('mybucket')
        k = Key(bucket)
        k.key = self.name
        k.set_contents_from_string(self.value)


@mock_s3
def test_my_model_save():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket('mybucket')
    ####################################

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn.get_bucket('mybucket').get_key('steve').get_contents_as_string().should.equal(b'is awesome')


@mock_s3
def test_key_etag():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket('mybucket')
    ####################################

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn.get_bucket('mybucket').get_key('steve').etag.should.equal(
        '"d32bda93738f7e03adb22e66c90fbc04"')


@mock_s3
def test_multipart_upload_too_small():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    multipart.upload_part_from_file(BytesIO(b'hello'), 1)
    multipart.upload_part_from_file(BytesIO(b'world'), 2)
    # Multipart with total size under 5MB is refused
    multipart.complete_upload.should.throw(S3ResponseError)


@mock_s3
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
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3
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
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3
@reduced_min_part_size
def test_multipart_upload_with_headers():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key", metadata={"foo": "bar"})
    part1 = b'0' * 10
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.complete_upload()

    key = bucket.get_key("the-key")
    key.metadata.should.equal({"foo": "bar"})


@mock_s3
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
    multipart.copy_part_from_key("foobar", "original-key", 2)
    multipart.complete_upload()
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + b"key_value")


@mock_s3
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


@mock_s3
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
    bucket.get_key("the-key").etag.should.equal(
        '"140f92a6df9f9e415f74a1463bcee9bb-2"')


@mock_s3
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


@mock_s3
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


@mock_s3
def test_key_save_to_missing_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.get_bucket('mybucket', validate=False)

    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string.when.called_with("foobar").should.throw(S3ResponseError)


@mock_s3
def test_missing_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    bucket.get_key("the-key").should.equal(None)


@mock_s3
def test_missing_key_urllib2():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket("foobar")

    urlopen.when.called_with("http://foobar.s3.amazonaws.com/the-key").should.throw(HTTPError)


@mock_s3
def test_empty_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("")

    key = bucket.get_key("the-key")
    key.size.should.equal(0)
    key.get_contents_as_string().should.equal(b'')


@mock_s3
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


@mock_s3
def test_large_key_save():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar" * 100000)

    bucket.get_key("the-key").get_contents_as_string().should.equal(b'foobar' * 100000)


@mock_s3
def test_copy_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key')

    bucket.get_key("the-key").get_contents_as_string().should.equal(b"some value")
    bucket.get_key("new-key").get_contents_as_string().should.equal(b"some value")


@mock_s3
def test_set_metadata():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = 'the-key'
    key.set_metadata('md', 'Metadatastring')
    key.set_contents_from_string("Testval")

    bucket.get_key('the-key').get_metadata('md').should.equal('Metadatastring')


@mock_s3
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
    bucket.get_key("new-key").get_metadata('momd').should.equal('Mometadatastring')


@freeze_time("2012-01-01 12:00:00")
@mock_s3
def test_last_modified():
    # See https://github.com/boto/boto/issues/466
    conn = boto.connect_s3()
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    rs = bucket.get_all_keys()
    rs[0].last_modified.should.equal('2012-01-01T12:00:00.000Z')

    bucket.get_key("the-key").last_modified.should.equal('Sun, 01 Jan 2012 12:00:00 GMT')


@mock_s3
def test_missing_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.get_bucket.when.called_with('mybucket').should.throw(S3ResponseError)


@mock_s3
def test_bucket_with_dash():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.get_bucket.when.called_with('mybucket-test').should.throw(S3ResponseError)


@mock_s3
def test_create_existing_bucket():
    "Trying to create a bucket that already exists should raise an Error"
    conn = boto.s3.connect_to_region("us-west-2")
    conn.create_bucket("foobar")
    with assert_raises(S3CreateError):
        conn.create_bucket('foobar')


@mock_s3
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


@mock_s3
def test_other_region():
    conn = S3Connection('key', 'secret', host='s3-website-ap-southeast-2.amazonaws.com')
    conn.create_bucket("foobar")
    list(conn.get_bucket("foobar").get_all_keys()).should.equal([])


@mock_s3
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


@mock_s3
def test_get_all_buckets():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket("foobar")
    conn.create_bucket("foobar2")
    buckets = conn.get_all_buckets()

    buckets.should.have.length_of(2)


@mock_s3
def test_post_to_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://foobar.s3.amazonaws.com/", {
        'key': 'the-key',
        'file': 'nothing'
    })

    bucket.get_key('the-key').get_contents_as_string().should.equal(b'nothing')


@mock_s3
def test_post_with_metadata_to_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://foobar.s3.amazonaws.com/", {
        'key': 'the-key',
        'file': 'nothing',
        'x-amz-meta-test': 'metadata'
    })

    bucket.get_key('the-key').get_metadata('test').should.equal('metadata')


@mock_s3
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


@mock_s3
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


@mock_s3
def test_bucket_method_not_implemented():
    requests.patch.when.called_with("https://foobar.s3.amazonaws.com/").should.throw(NotImplementedError)


@mock_s3
def test_key_method_not_implemented():
    requests.post.when.called_with("https://foobar.s3.amazonaws.com/foo").should.throw(NotImplementedError)


@mock_s3
def test_bucket_name_with_dot():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('firstname.lastname')

    k = Key(bucket, 'somekey')
    k.set_contents_from_string('somedata')


@mock_s3
def test_key_with_special_characters():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket_name')

    key = Key(bucket, 'test_list_keys_2/x?y')
    key.set_contents_from_string('value1')

    key_list = bucket.list('test_list_keys_2/', '/')
    keys = [x for x in key_list]
    keys[0].name.should.equal("test_list_keys_2/x?y")


@mock_s3
def test_bucket_list_no_quote():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket')

    # test characters which should not be url encoded
    key_name = 'validchars\n'
    k = Key(bucket, key_name)
    k.set_contents_from_string('somedata')
    keys = [x.name for x in bucket.list()]
    keys.should.equal([key_name])


@requires_boto_gte('2.21.0')
@mock_s3
def test_bucket_list_unicode():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket')

    # test with unicode
    key_name = u'έγκυροι χαρακτήρες'
    k = Key(bucket, key_name.encode('utf-8'))
    k.set_contents_from_string('somedata')
    keys = [x.name for x in bucket.list()]
    keys.should.equal([key_name])

    # test with unicode when url encoding
    keys = [x.name for x in bucket.list(encoding_type='url')]
    keys.should.equal([quote(key_name.encode('utf-8'))])


@requires_boto_gte('2.21.0')
@mock_s3
def test_bucket_list_quote_invalid():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket')

    # test with characters which are invalid xml
    key_name = 'validunicode\x01invalidxml'
    k = Key(bucket, key_name)
    k.set_contents_from_string('somedata')
    keys = [x.name for x in bucket.list(encoding_type='url')]
    keys.should.equal([quote(key_name)])


@requires_boto_gte('2.21.0')
@mock_s3
def test_bucket_list_quote_folders():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket')

    # test with unicode in common prefixes
    folder_name = 'validunicode\x01invalidxmlfolder'
    k = Key(bucket, folder_name+"/lala")
    k.set_contents_from_string('somedata')
    keys = [x.name for x in bucket.list(encoding_type='url', delimiter='/')]
    keys.should.equal([quote(folder_name)])


@mock_s3
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
    keys.should.equal([u'toplevel/x/key', u'toplevel/x/y/key', u'toplevel/x/y/z/key'])

    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix + 'x', delimiter)]
    keys.should.equal([u'toplevel/x/'])


@mock_s3
def test_key_with_reduced_redundancy():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket_name')

    key = Key(bucket, 'test_rr_key')
    key.set_contents_from_string('value1', reduced_redundancy=True)
    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    list(bucket)[0].storage_class.should.equal('REDUCED_REDUNDANCY')


@mock_s3
def test_copy_key_reduced_redundancy():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key', storage_class='REDUCED_REDUNDANCY')

    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    keys = dict([(k.name, k) for k in bucket])
    keys['new-key'].storage_class.should.equal("REDUCED_REDUNDANCY")
    keys['the-key'].storage_class.should.equal("STANDARD")


@freeze_time("2012-01-01 12:00:00")
@mock_s3
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
@mock_s3
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


@mock_s3
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


@mock_s3
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


@mock_s3
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


@mock_s3
def test_acl_is_ignored_for_now():
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


@mock_s3
def test_unicode_key():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('mybucket')
    key = Key(bucket)
    key.key = u'こんにちは.jpg'
    key.set_contents_from_string('Hello world!')
    list(bucket.list())
    key = bucket.get_key(key.key)
    assert key.get_contents_as_string().decode("utf-8") == 'Hello world!'


@mock_s3
def test_unicode_value():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('mybucket')
    key = Key(bucket)
    key.key = 'some_key'
    key.set_contents_from_string(u'こんにちは.jpg')
    list(bucket.list())
    key = bucket.get_key(key.key)
    assert key.get_contents_as_string().decode("utf-8") == u'こんにちは.jpg'


@mock_s3
def test_setting_content_encoding():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('mybucket')
    key = bucket.new_key("keyname")
    key.set_metadata("Content-Encoding", "gzip")
    compressed_data = "abcdef"
    key.set_contents_from_string(compressed_data)

    key = bucket.get_key("keyname")
    key.content_encoding.should.equal("gzip")


@mock_s3
def test_bucket_location():
    conn = boto.s3.connect_to_region("us-west-2")
    bucket = conn.create_bucket('mybucket')
    bucket.get_location().should.equal("us-west-2")


@mock_s3
def test_ranged_get():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('mybucket')
    key = Key(bucket)
    key.key = 'bigkey'
    rep = b"0123456789"
    key.set_contents_from_string(rep * 10)
    key.get_contents_as_string(headers={'Range': 'bytes=0-'}).should.equal(rep * 10)
    key.get_contents_as_string(headers={'Range': 'bytes=0-99'}).should.equal(rep * 10)
    key.get_contents_as_string(headers={'Range': 'bytes=0-0'}).should.equal(b'0')
    key.get_contents_as_string(headers={'Range': 'bytes=99-99'}).should.equal(b'9')
    key.get_contents_as_string(headers={'Range': 'bytes=50-54'}).should.equal(rep[:5])
    key.get_contents_as_string(headers={'Range': 'bytes=50-'}).should.equal(rep * 5)
    key.get_contents_as_string(headers={'Range': 'bytes=-60'}).should.equal(rep * 6)
    key.size.should.equal(100)
