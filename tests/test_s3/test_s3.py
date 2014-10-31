from __future__ import unicode_literals
import six
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError
from io import BytesIO

import boto
from boto.exception import S3CreateError, S3ResponseError
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from freezegun import freeze_time
import requests
import tests.backport_assert_raises
from nose.tools import assert_raises

import sure  # noqa

from moto import mock_s3


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
def test_multipart_upload():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * 5242880
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # last part, can be less than 5 MB
    part2 = b'1'
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3
def test_multipart_upload_with_copy_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "original-key"
    key.set_contents_from_string("key_value")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * 5242880
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.copy_part_from_key("foobar", "original-key", 2)
    multipart.complete_upload()
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + b"key_value")


@mock_s3
def test_multipart_upload_cancel():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * 5242880
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.cancel_upload()
    # TODO we really need some sort of assertion here, but we don't currently
    # have the ability to list mulipart uploads for a bucket.


@mock_s3
def test_multipart_etag():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('mybucket')

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = b'0' * 5242880
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # last part, can be less than 5 MB
    part2 = b'1'
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key("the-key").etag.should.equal(
        '"140f92a6df9f9e415f74a1463bcee9bb-2"')


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

    bucket.get_key("the-key").get_contents_as_string().should.equal(b'')


@mock_s3
def test_empty_key_set_on_existing_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar")

    bucket.get_key("the-key").get_contents_as_string().should.equal(b'foobar')

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
    rs[0].last_modified.should.equal('2012-01-01T12:00:00Z')

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
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket("foobar")
    with assert_raises(S3CreateError):
        conn.create_bucket('foobar')


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
    keys.should.equal(['toplevel'])

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
