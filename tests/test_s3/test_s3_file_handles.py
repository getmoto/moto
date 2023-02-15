import boto3
import copy
import gc
import warnings
from functools import wraps
from moto import settings, mock_s3
from moto.dynamodb.models import DynamoDBBackend
from moto.s3 import models as s3model
from moto.s3.responses import S3ResponseInstance
from unittest import SkipTest, TestCase


def verify_zero_warnings(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always", ResourceWarning)  # add filter
            resp = f(*args, **kwargs)
            # Get the TestClass reference, and reset any S3Backends that we've created as part of that class
            (class_ref,) = args
            for obj in class_ref.__dict__:
                if isinstance(obj, s3model.S3Backend):
                    obj.reset()
            # Now collect garbage, which will throw any warnings if there are unclosed FileHandles
            gc.collect()
        warning_types = [type(warn.message) for warn in warning_list]
        warning_types.shouldnt.contain(ResourceWarning)
        return resp

    return wrapped


class TestS3FileHandleClosures(TestCase):
    """
    Large Uploads are written to disk for performance reasons
    These tests verifies that the filehandles are properly closed after specific actions
    """

    def setUp(self) -> None:
        if settings.TEST_SERVER_MODE:
            raise SkipTest("No point in testing ServerMode, we're not using boto3")
        self.s3 = s3model.S3Backend("us-west-1", "1234")
        self.s3.create_bucket("my-bucket", "us-west-1")
        self.s3.create_bucket("versioned-bucket", "us-west-1")
        self.s3.put_object("my-bucket", "my-key", "x" * 10_000_000)

    @verify_zero_warnings
    def test_upload_large_file(self):
        # Verify that we can create an object, as done in the setUp-method
        # Do not create any other objects, as it will taint the state that we're testing
        pass

    @verify_zero_warnings
    def test_delete_large_file(self):
        self.s3.delete_object(bucket_name="my-bucket", key_name="my-key")

    @verify_zero_warnings
    def test_overwriting_file(self):
        self.s3.put_object("my-bucket", "my-key", "b" * 10_000_000)

    @verify_zero_warnings
    def test_versioned_file(self):
        self.s3.put_bucket_versioning("my-bucket", "Enabled")
        self.s3.put_object("my-bucket", "my-key", "b" * 10_000_000)

    @verify_zero_warnings
    def test_copy_object(self):
        key = self.s3.get_object("my-bucket", "my-key")
        self.s3.copy_object(
            src_key=key, dest_bucket_name="my-bucket", dest_key_name="key-2"
        )

    @verify_zero_warnings
    def test_part_upload(self):
        multipart_id = self.s3.create_multipart_upload(
            bucket_name="my-bucket",
            key_name="mp-key",
            metadata={},
            storage_type="STANDARD",
            tags=[],
            acl=None,
            sse_encryption=None,
            kms_key_id=None,
        )
        self.s3.upload_part(
            bucket_name="my-bucket",
            multipart_id=multipart_id,
            part_id=1,
            value="b" * 10_000_000,
        )

    @verify_zero_warnings
    def test_overwriting_part_upload(self):
        multipart_id = self.s3.create_multipart_upload(
            bucket_name="my-bucket",
            key_name="mp-key",
            metadata={},
            storage_type="STANDARD",
            tags=[],
            acl=None,
            sse_encryption=None,
            kms_key_id=None,
        )
        self.s3.upload_part(
            bucket_name="my-bucket",
            multipart_id=multipart_id,
            part_id=1,
            value="b" * 10_000_000,
        )
        self.s3.upload_part(
            bucket_name="my-bucket",
            multipart_id=multipart_id,
            part_id=1,
            value="c" * 10_000_000,
        )

    @verify_zero_warnings
    def test_aborting_part_upload(self):
        multipart_id = self.s3.create_multipart_upload(
            bucket_name="my-bucket",
            key_name="mp-key",
            metadata={},
            storage_type="STANDARD",
            tags=[],
            acl=None,
            sse_encryption=None,
            kms_key_id=None,
        )
        self.s3.upload_part(
            bucket_name="my-bucket",
            multipart_id=multipart_id,
            part_id=1,
            value="b" * 10_000_000,
        )
        self.s3.abort_multipart_upload(
            bucket_name="my-bucket", multipart_id=multipart_id
        )

    @verify_zero_warnings
    def test_completing_part_upload(self):
        multipart_id = self.s3.create_multipart_upload(
            bucket_name="my-bucket",
            key_name="mp-key",
            metadata={},
            storage_type="STANDARD",
            tags=[],
            acl=None,
            sse_encryption=None,
            kms_key_id=None,
        )
        etag = self.s3.upload_part(
            bucket_name="my-bucket",
            multipart_id=multipart_id,
            part_id=1,
            value="b" * 10_000_000,
        ).etag

        mp_body = f"""<CompleteMultipartUpload xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Part><ETag>{etag}</ETag><PartNumber>1</PartNumber></Part></CompleteMultipartUpload>"""
        body = S3ResponseInstance._complete_multipart_body(mp_body)
        self.s3.complete_multipart_upload(
            bucket_name="my-bucket", multipart_id=multipart_id, body=body
        )

    @verify_zero_warnings
    def test_single_versioned_upload(self):
        self.s3.put_object("versioned-bucket", "my-key", "x" * 10_000_000)

    @verify_zero_warnings
    def test_overwrite_versioned_upload(self):
        self.s3.put_object("versioned-bucket", "my-key", "x" * 10_000_000)

    @verify_zero_warnings
    def test_multiple_versions_upload(self):
        self.s3.put_object("versioned-bucket", "my-key", "x" * 10_000_000)
        self.s3.put_object("versioned-bucket", "my-key", "y" * 10_000_000)
        self.s3.put_object("versioned-bucket", "my-key", "z" * 10_000_000)

    @verify_zero_warnings
    def test_delete_versioned_upload(self):
        self.s3.put_object("versioned-bucket", "my-key", "x" * 10_000_000)
        self.s3.put_object("versioned-bucket", "my-key", "x" * 10_000_000)
        self.s3.delete_object(bucket_name="my-bucket", key_name="my-key")

    @verify_zero_warnings
    def test_delete_specific_version(self):
        self.s3.put_object("versioned-bucket", "my-key", "x" * 10_000_000)
        key = self.s3.put_object("versioned-bucket", "my-key", "y" * 10_000_000)
        self.s3.delete_object(
            bucket_name="my-bucket", key_name="my-key", version_id=key._version_id
        )

    @verify_zero_warnings
    def test_reset_other_backend(self):
        db = DynamoDBBackend("us-west-1", "1234")
        # This used to empty the entire list of `model_instances`, which can contain FakeKey-references
        # Verify that we can reset an unrelated backend, without throwing away FakeKey-references that still need to be disposed
        db.reset()


class TestS3FileHandleClosuresUsingMocks(TestCase):
    def setUp(self) -> None:
        self.s3 = boto3.client("s3", "us-east-1")

    @verify_zero_warnings
    @mock_s3
    def test_use_decorator(self):
        self.s3.create_bucket(Bucket="foo")
        self.s3.put_object(Bucket="foo", Key="bar", Body="stuff")

    @verify_zero_warnings
    @mock_s3
    def test_use_decorator_and_context_mngt(self):
        with mock_s3():
            self.s3.create_bucket(Bucket="foo")
            self.s3.put_object(Bucket="foo", Key="bar", Body="stuff")

    @verify_zero_warnings
    def test_use_multiple_context_managers(self):
        with mock_s3():
            self.s3.create_bucket(Bucket="foo")
            self.s3.put_object(Bucket="foo", Key="bar", Body="stuff")

        with mock_s3():
            pass

    @verify_zero_warnings
    def test_create_multipart(self):
        with mock_s3():
            self.s3.create_bucket(Bucket="foo")
            self.s3.put_object(Bucket="foo", Key="k1", Body="stuff")

            mp = self.s3.create_multipart_upload(Bucket="foo", Key="key2")
            self.s3.upload_part(
                Body=b"hello",
                PartNumber=1,
                Bucket="foo",
                Key="key2",
                UploadId=mp["UploadId"],
            )

        with mock_s3():
            pass

    @verify_zero_warnings
    def test_overwrite_file(self):
        with mock_s3():
            self.s3.create_bucket(Bucket="foo")
            self.s3.put_object(Bucket="foo", Key="k1", Body="stuff")
            self.s3.put_object(Bucket="foo", Key="k1", Body="b" * 10_000_000)

        with mock_s3():
            pass


def test_verify_key_can_be_copied_after_disposing():
    # https://github.com/getmoto/moto/issues/5588
    # Multithreaded bug where:
    #  - User: calls list_object_versions
    #  - Moto creates a list of all keys
    #  - User: deletes a key
    #  - Moto iterates over the previously created list, that contains a now-deleted key, and creates a copy of it
    #
    # This test verifies the copy-operation succeeds, it will just not have any data
    key = s3model.FakeKey(name="test", bucket_name="bucket", value="sth")
    assert not key._value_buffer.closed
    key.dispose()
    assert key._value_buffer.closed

    copied_key = copy.copy(key)
    copied_key.value.should.equal(b"")
