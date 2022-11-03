import datetime
import os
from urllib.parse import urlparse, parse_qs
from gzip import GzipFile
from io import BytesIO
import zlib
import pickle
import uuid

import json
import boto3
from botocore.client import ClientError
import botocore.exceptions
from botocore.handlers import disable_signing
from freezegun import freeze_time
import requests

from moto.moto_api import state_manager
from moto.s3.responses import DEFAULT_REGION_NAME
from unittest import SkipTest
import pytest

import sure  # noqa # pylint: disable=unused-import

from moto import settings, mock_s3, mock_config
import moto.s3.models as s3model
from uuid import uuid4


class MyModel(object):
    def __init__(self, name, value, metadata=None):
        self.name = name
        self.value = value
        self.metadata = metadata or {}

    def save(self):
        s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
        s3.put_object(
            Bucket="mybucket", Key=self.name, Body=self.value, Metadata=self.metadata
        )


@mock_s3
def test_keys_are_pickleable():
    """Keys must be pickleable due to boto3 implementation details."""
    key = s3model.FakeKey("name", b"data!")
    assert key.value == b"data!"

    pickled = pickle.dumps(key)
    loaded = pickle.loads(pickled)
    assert loaded.value == key.value


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
def test_object_metadata():
    """Metadata keys can contain certain special characters like dash and dot"""
    # Create Bucket so that test can run
    conn = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    conn.create_bucket(Bucket="mybucket")
    ####################################

    metadata = {"meta": "simple", "my-meta": "dash", "meta.data": "namespaced"}

    model_instance = MyModel("steve", "is awesome", metadata=metadata)
    model_instance.save()

    meta = conn.Object("mybucket", "steve").get()["Metadata"]

    assert meta == metadata


@mock_s3
def test_resource_get_object_returns_etag():
    conn = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    conn.create_bucket(Bucket="mybucket")

    model_instance = MyModel("steve", "is awesome")
    model_instance.save()

    conn.Bucket("mybucket").Object("steve").e_tag.should.equal(
        '"d32bda93738f7e03adb22e66c90fbc04"'
    )


@mock_s3
def test_key_save_to_missing_bucket():
    s3 = boto3.resource("s3")

    key = s3.Object("mybucket", "the-key")
    with pytest.raises(ClientError) as ex:
        key.put(Body=b"foobar")
    ex.value.response["Error"]["Code"].should.equal("NoSuchBucket")
    ex.value.response["Error"]["Message"].should.equal(
        "The specified bucket does not exist"
    )


@mock_s3
def test_missing_key_request():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Only test status code in non-ServerMode")
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    response = requests.get("http://foobar.s3.amazonaws.com/the-key")
    response.status_code.should.equal(404)


@mock_s3
def test_empty_key():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    key = s3.Object("foobar", "the-key")
    key.put(Body=b"")

    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp.should.have.key("ContentLength").equal(0)
    resp["Body"].read().should.equal(b"")


@mock_s3
def test_key_name_encoding_in_listing():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    name = "6T7\x159\x12\r\x08.txt"

    key = s3.Object("foobar", name)
    key.put(Body=b"")

    key_received = client.list_objects(Bucket="foobar")["Contents"][0]["Key"]
    key_received.should.equal(name)

    key_received = client.list_objects_v2(Bucket="foobar")["Contents"][0]["Key"]
    key_received.should.equal(name)

    name = "example/file.text"
    client.put_object(Bucket="foobar", Key=name, Body=b"")

    key_received = client.list_objects(
        Bucket="foobar", Prefix="example/", Delimiter="/", MaxKeys=1, EncodingType="url"
    )["Contents"][0]["Key"]
    key_received.should.equal(name)


@mock_s3
def test_empty_key_set_on_existing_key():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    key = s3.Object("foobar", "the-key")
    key.put(Body=b"some content")

    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp.should.have.key("ContentLength").equal(12)
    resp["Body"].read().should.equal(b"some content")

    key.put(Body=b"")

    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp.should.have.key("ContentLength").equal(0)
    resp["Body"].read().should.equal(b"")


@mock_s3
def test_large_key_save():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    key = s3.Object("foobar", "the-key")
    key.put(Body=b"foobar" * 100000)

    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp["Body"].read().should.equal(b"foobar" * 100000)


@mock_s3
def test_set_metadata():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    key = s3.Object("foobar", "the-key")
    key.put(Body=b"some value", Metadata={"md": "Metadatastring"})

    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp["Metadata"].should.equal({"md": "Metadatastring"})


@freeze_time("2012-01-01 12:00:00")
@mock_s3
def test_last_modified():
    # See https://github.com/boto/boto/issues/466
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    key = s3.Object("foobar", "the-key")
    key.put(Body=b"some value", Metadata={"md": "Metadatastring"})

    rs = client.list_objects_v2(Bucket="foobar")["Contents"]
    rs[0]["LastModified"].should.be.a(datetime.datetime)

    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp["LastModified"].should.be.a(datetime.datetime)
    as_header = resp["ResponseMetadata"]["HTTPHeaders"]["last-modified"]
    as_header.should.be.a(str)
    if not settings.TEST_SERVER_MODE:
        as_header.should.equal("Sun, 01 Jan 2012 12:00:00 GMT")


@mock_s3
def test_missing_bucket():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as ex:
        client.head_bucket(Bucket="mybucket")
    ex.value.response["Error"]["Code"].should.equal("404")
    ex.value.response["Error"]["Message"].should.equal("Not Found")

    with pytest.raises(ClientError) as ex:
        client.head_bucket(Bucket="dash-in-name")
    ex.value.response["Error"]["Code"].should.equal("404")
    ex.value.response["Error"]["Message"].should.equal("Not Found")


@mock_s3
def test_create_existing_bucket():
    "Trying to create a bucket that already exists should raise an Error"
    client = boto3.client("s3", region_name="us-west-2")
    kwargs = {
        "Bucket": "foobar",
        "CreateBucketConfiguration": {"LocationConstraint": "us-west-2"},
    }
    client.create_bucket(**kwargs)
    with pytest.raises(ClientError) as ex:
        client.create_bucket(**kwargs)
    ex.value.response["Error"]["Code"].should.equal("BucketAlreadyOwnedByYou")
    ex.value.response["Error"]["Message"].should.equal(
        "Your previous request to create the named bucket succeeded and you already own it."
    )


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
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")
    client.create_bucket(Bucket="foobar")


@mock_s3
def test_bucket_deletion():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")

    key = s3.Object("foobar", "the-key")
    key.put(Body=b"some value")

    # Try to delete a bucket that still has keys
    with pytest.raises(ClientError) as ex:
        client.delete_bucket(Bucket="foobar")
    ex.value.response["Error"]["Code"].should.equal("BucketNotEmpty")
    ex.value.response["Error"]["Message"].should.equal(
        "The bucket you tried to delete is not empty"
    )

    client.delete_object(Bucket="foobar", Key="the-key")
    client.delete_bucket(Bucket="foobar")

    # Delete non-existent bucket
    with pytest.raises(ClientError) as ex:
        client.delete_bucket(Bucket="foobar")
    ex.value.response["Error"]["Code"].should.equal("NoSuchBucket")
    ex.value.response["Error"]["Message"].should.equal(
        "The specified bucket does not exist"
    )


@mock_s3
def test_get_all_buckets():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")
    client.create_bucket(Bucket="foobar2")

    client.list_buckets()["Buckets"].should.have.length_of(2)


@mock_s3
def test_post_to_bucket():
    if settings.TEST_SERVER_MODE:
        # ServerMode does not allow unauthorized requests
        raise SkipTest()

    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")

    requests.post(
        "https://foobar.s3.amazonaws.com/", {"key": "the-key", "file": "nothing"}
    )

    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp["Body"].read().should.equal(b"nothing")


@mock_s3
def test_post_with_metadata_to_bucket():
    if settings.TEST_SERVER_MODE:
        # ServerMode does not allow unauthorized requests
        raise SkipTest()
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")

    requests.post(
        "https://foobar.s3.amazonaws.com/",
        {"key": "the-key", "file": "nothing", "x-amz-meta-test": "metadata"},
    )

    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp["Metadata"].should.equal({"test": "metadata"})


@mock_s3
def test_delete_versioned_objects():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = "test"
    key = "test"

    s3.create_bucket(Bucket=bucket)

    s3.put_object(Bucket=bucket, Key=key, Body=b"")

    s3.put_bucket_versioning(
        Bucket=bucket, VersioningConfiguration={"Status": "Enabled"}
    )

    objects = s3.list_objects_v2(Bucket=bucket).get("Contents")
    versions = s3.list_object_versions(Bucket=bucket).get("Versions")
    delete_markers = s3.list_object_versions(Bucket=bucket).get("DeleteMarkers")

    objects.should.have.length_of(1)
    versions.should.have.length_of(1)
    delete_markers.should.equal(None)

    s3.delete_object(Bucket=bucket, Key=key)

    objects = s3.list_objects_v2(Bucket=bucket).get("Contents")
    versions = s3.list_object_versions(Bucket=bucket).get("Versions")
    delete_markers = s3.list_object_versions(Bucket=bucket).get("DeleteMarkers")

    objects.should.equal(None)
    versions.should.have.length_of(1)
    delete_markers.should.have.length_of(1)

    s3.delete_object(Bucket=bucket, Key=key, VersionId=versions[0].get("VersionId"))

    objects = s3.list_objects_v2(Bucket=bucket).get("Contents")
    versions = s3.list_object_versions(Bucket=bucket).get("Versions")
    delete_markers = s3.list_object_versions(Bucket=bucket).get("DeleteMarkers")

    objects.should.equal(None)
    versions.should.equal(None)
    delete_markers.should.have.length_of(1)

    s3.delete_object(
        Bucket=bucket, Key=key, VersionId=delete_markers[0].get("VersionId")
    )

    objects = s3.list_objects_v2(Bucket=bucket).get("Contents")
    versions = s3.list_object_versions(Bucket=bucket).get("Versions")
    delete_markers = s3.list_object_versions(Bucket=bucket).get("DeleteMarkers")

    objects.should.equal(None)
    versions.should.equal(None)
    delete_markers.should.equal(None)


@mock_s3
def test_delete_missing_key():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()

    s3.Object("foobar", "key1").put(Body=b"some value")
    s3.Object("foobar", "key2").put(Body=b"some value")
    s3.Object("foobar", "key3").put(Body=b"some value")
    s3.Object("foobar", "key4").put(Body=b"some value")

    result = bucket.delete_objects(
        Delete={
            "Objects": [
                {"Key": "unknown"},
                {"Key": "key1"},
                {"Key": "key3"},
                {"Key": "typo"},
            ]
        }
    )
    result.should.have.key("Deleted").equal(
        [{"Key": "unknown"}, {"Key": "key1"}, {"Key": "key3"}, {"Key": "typo"}]
    )
    result.shouldnt.have.key("Errors")

    objects = list(bucket.objects.all())
    set([o.key for o in objects]).should.equal(set(["key2", "key4"]))


@mock_s3
def test_delete_empty_keys_list():
    with pytest.raises(ClientError) as err:
        boto3.client("s3").delete_objects(Bucket="foobar", Delete={"Objects": []})
    assert err.value.response["Error"]["Code"] == "MalformedXML"


@pytest.mark.parametrize("name", ["firstname.lastname", "with-dash"])
@mock_s3
def test_bucket_name_with_special_chars(name):
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket(name)
    bucket.create()

    s3.Object(name, "the-key").put(Body=b"some value")

    resp = client.get_object(Bucket=name, Key="the-key")
    resp["Body"].read().should.equal(b"some value")


@pytest.mark.parametrize(
    "key", ["normal", "test_list_keys_2/x?y", "/the-key-unîcode/test"]
)
@mock_s3
def test_key_with_special_characters(key):
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("testname")
    bucket.create()

    s3.Object("testname", key).put(Body=b"value")

    objects = list(bucket.objects.all())
    [o.key for o in objects].should.equal([key])

    resp = client.get_object(Bucket="testname", Key=key)
    resp["Body"].read().should.equal(b"value")


@mock_s3
def test_bucket_key_listing_order():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "test_bucket"
    bucket = s3.Bucket(bucket_name)
    bucket.create()
    prefix = "toplevel/"

    names = ["x/key", "y.key1", "y.key2", "y.key3", "x/y/key", "x/y/z/key"]

    for name in names:
        s3.Object(bucket_name, prefix + name).put(Body=b"somedata")

    delimiter = ""
    keys = [x.key for x in bucket.objects.filter(Prefix=prefix, Delimiter=delimiter)]
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
    keys = [x.key for x in bucket.objects.filter(Prefix=prefix, Delimiter=delimiter)]
    keys.should.equal(["toplevel/y.key1", "toplevel/y.key2", "toplevel/y.key3"])

    # Test delimiter with no prefix
    keys = [x.key for x in bucket.objects.filter(Delimiter=delimiter)]
    keys.should.equal([])

    prefix = "toplevel/x"
    keys = [x.key for x in bucket.objects.filter(Prefix=prefix)]
    keys.should.equal(["toplevel/x/key", "toplevel/x/y/key", "toplevel/x/y/z/key"])

    keys = [x.key for x in bucket.objects.filter(Prefix=prefix, Delimiter=delimiter)]
    keys.should.equal([])


@mock_s3
def test_key_with_reduced_redundancy():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "test_bucket"
    bucket = s3.Bucket(bucket_name)
    bucket.create()

    bucket.put_object(
        Key="test_rr_key", Body=b"somedata", StorageClass="REDUCED_REDUNDANCY"
    )

    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    [x.storage_class for x in bucket.objects.all()].should.equal(["REDUCED_REDUNDANCY"])


@freeze_time("2012-01-01 12:00:00")
@mock_s3
def test_restore_key():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()

    key = bucket.put_object(Key="the-key", Body=b"somedata", StorageClass="GLACIER")
    key.restore.should.equal(None)
    key.restore_object(RestoreRequest={"Days": 1})
    if settings.TEST_SERVER_MODE:
        key.restore.should.contain('ongoing-request="false"')
    else:
        key.restore.should.equal(
            'ongoing-request="false", expiry-date="Mon, 02 Jan 2012 12:00:00 GMT"'
        )

    key.restore_object(RestoreRequest={"Days": 2})

    if settings.TEST_SERVER_MODE:
        key.restore.should.contain('ongoing-request="false"')
    else:
        key.restore.should.equal(
            'ongoing-request="false", expiry-date="Tue, 03 Jan 2012 12:00:00 GMT"'
        )


@freeze_time("2012-01-01 12:00:00")
@mock_s3
def test_restore_key_transition():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set transition directly in ServerMode")

    state_manager.set_transition(
        model_name="s3::keyrestore", transition={"progression": "manual", "times": 1}
    )

    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()

    key = bucket.put_object(Key="the-key", Body=b"somedata", StorageClass="GLACIER")
    key.restore.should.equal(None)
    key.restore_object(RestoreRequest={"Days": 1})

    # first call: there should be an ongoing request
    key.restore.should.contain('ongoing-request="true"')

    # second call: request should be done
    key.load()
    key.restore.should.contain('ongoing-request="false"')

    # third call: request should still be done
    key.load()
    key.restore.should.contain('ongoing-request="false"')

    state_manager.unset_transition(model_name="s3::keyrestore")


@mock_s3
def test_cannot_restore_standard_class_object():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()

    key = bucket.put_object(Key="the-key", Body=b"somedata")
    with pytest.raises(Exception) as err:
        key.restore_object(RestoreRequest={"Days": 1})

    err = err.value.response["Error"]
    err["Code"].should.equal("InvalidObjectState")
    err["StorageClass"].should.equal("STANDARD")
    err["Message"].should.equal(
        "The operation is not valid for the object's storage class"
    )


@mock_s3
def test_get_versioning_status():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()

    v = s3.BucketVersioning("foobar")
    v.status.should.equal(None)

    v.enable()
    v.status.should.equal("Enabled")

    v.suspend()
    v.status.should.equal("Suspended")


@mock_s3
def test_key_version():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()
    bucket.Versioning().enable()

    versions = []

    key = bucket.put_object(Key="the-key", Body=b"somedata")
    versions.append(key.version_id)
    key.put(Body=b"some string")
    versions.append(key.version_id)
    set(versions).should.have.length_of(2)

    key = client.get_object(Bucket="foobar", Key="the-key")
    key["VersionId"].should.equal(versions[-1])


@mock_s3
def test_list_versions():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()
    bucket.Versioning().enable()

    key_versions = []

    key = bucket.put_object(Key="the-key", Body=b"Version 1")
    key_versions.append(key.version_id)
    key = bucket.put_object(Key="the-key", Body=b"Version 2")
    key_versions.append(key.version_id)
    key_versions.should.have.length_of(2)

    versions = client.list_object_versions(Bucket="foobar")["Versions"]
    versions.should.have.length_of(2)

    versions[0]["Key"].should.equal("the-key")
    versions[0]["VersionId"].should.equal(key_versions[1])
    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp["Body"].read().should.equal(b"Version 2")
    resp = client.get_object(
        Bucket="foobar", Key="the-key", VersionId=versions[0]["VersionId"]
    )
    resp["Body"].read().should.equal(b"Version 2")

    versions[1]["Key"].should.equal("the-key")
    versions[1]["VersionId"].should.equal(key_versions[0])
    resp = client.get_object(
        Bucket="foobar", Key="the-key", VersionId=versions[1]["VersionId"]
    )
    resp["Body"].read().should.equal(b"Version 1")

    bucket.put_object(Key="the2-key", Body=b"Version 1")

    list(bucket.objects.all()).should.have.length_of(2)
    versions = client.list_object_versions(Bucket="foobar", Prefix="the2")["Versions"]
    versions.should.have.length_of(1)


@mock_s3
def test_acl_setting():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()

    content = b"imafile"
    keyname = "test.txt"
    bucket.put_object(
        Key=keyname, Body=content, ContentType="text/plain", ACL="public-read"
    )

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    grants.should.contain(
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
            },
            "Permission": "READ",
        }
    )


@mock_s3
def test_acl_setting_via_headers():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()

    keyname = "test.txt"

    bucket.put_object(Key=keyname, Body=b"imafile")
    client.put_object_acl(ACL="public-read", Bucket="foobar", Key=keyname)

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    grants.should.contain(
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
            },
            "Permission": "READ",
        }
    )


@mock_s3
def test_acl_switching():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()
    keyname = "test.txt"

    bucket.put_object(Key=keyname, Body=b"asdf", ACL="public-read")
    client.put_object_acl(ACL="private", Bucket="foobar", Key=keyname)

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    grants.shouldnt.contain(
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
            },
            "Permission": "READ",
        }
    )


@mock_s3
def test_acl_switching_nonexistent_key():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    with pytest.raises(ClientError) as e:
        s3.put_object_acl(Bucket="mybucket", Key="nonexistent", ACL="private")

    e.value.response["Error"]["Code"].should.equal("NoSuchKey")


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
def test_upload_from_file_to_presigned_url():
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
def test_upload_file_with_checksum_algorithm():
    random_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\n\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\n"
    with open("rb.tmp", mode="wb") as f:
        f.write(random_bytes)
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = "mybucket"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.upload_file(
        "rb.tmp", bucket, "my_key.csv", ExtraArgs={"ChecksumAlgorithm": "SHA256"}
    )
    os.remove("rb.tmp")

    actual_content = s3.Object(bucket, "my_key.csv").get()["Body"].read()
    assert random_bytes == actual_content


@mock_s3
def test_put_chunked_with_v4_signature_in_body():
    bucket_name = "mybucket"
    file_name = "file"
    content = "CONTENT"
    content_bytes = bytes(content, encoding="utf8")
    # 'CONTENT' as received in moto, when PutObject is called in java AWS SDK v2
    chunked_body = b"7;chunk-signature=bd479c607ec05dd9d570893f74eed76a4b333dfa37ad6446f631ec47dc52e756\r\nCONTENT\r\n0;chunk-signature=d192ec4075ddfc18d2ef4da4f55a87dc762ba4417b3bd41e70c282f8bec2ece0\r\n\r\n"

    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)

    model = MyModel(file_name, content)
    model.save()

    boto_etag = s3.get_object(Bucket=bucket_name, Key=file_name)["ETag"]

    params = {"Bucket": bucket_name, "Key": file_name}
    # We'll use manipulated presigned PUT, to mimick PUT from SDK
    presigned_url = boto3.client("s3").generate_presigned_url(
        "put_object", params, ExpiresIn=900
    )
    requests.put(
        presigned_url,
        data=chunked_body,
        headers={
            "Content-Type": "application/octet-stream",
            "x-amz-content-sha256": "STREAMING-AWS4-HMAC-SHA256-PAYLOAD",
            "x-amz-decoded-content-length": str(len(content_bytes)),
        },
    )
    resp = s3.get_object(Bucket=bucket_name, Key=file_name)
    body = resp["Body"].read()
    assert body == content_bytes

    etag = resp["ETag"]
    assert etag == boto_etag


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


@mock_s3
def test_unicode_key():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("mybucket")
    bucket.create()

    key = bucket.put_object(Key="こんにちは.jpg", Body=b"Hello world!")

    [listed_key.key for listed_key in bucket.objects.all()].should.equal([key.key])
    fetched_key = s3.Object("mybucket", key.key)
    fetched_key.key.should.equal(key.key)
    fetched_key.get()["Body"].read().decode("utf-8").should.equal("Hello world!")


@mock_s3
def test_unicode_value():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("mybucket")
    bucket.create()

    bucket.put_object(Key="some_key", Body="こんにちは.jpg")

    key = s3.Object("mybucket", "some_key")
    key.get()["Body"].read().decode("utf-8").should.equal("こんにちは.jpg")


@mock_s3
def test_setting_content_encoding():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("mybucket")
    bucket.create()

    bucket.put_object(Body=b"abcdef", ContentEncoding="gzip", Key="keyname")

    key = s3.Object("mybucket", "keyname")
    key.content_encoding.should.equal("gzip")


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
    cli.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
    )
    cli.get_bucket_location(Bucket=bucket_name)["LocationConstraint"].should.equal(
        "eu-central-1"
    )


@mock_s3
def test_s3_location_should_error_outside_useast1():
    s3 = boto3.client("s3", region_name="eu-west-1")

    bucket_name = "asdfasdfsdfdsfasda"

    with pytest.raises(ClientError) as e:
        s3.create_bucket(Bucket=bucket_name)
    e.value.response["Error"]["Message"].should.equal(
        "The unspecified location constraint is incompatible for the region specific endpoint this request was sent to."
    )


@mock_s3
def test_ranged_get():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("mybucket")
    bucket.create()
    rep = b"0123456789"
    key = bucket.put_object(Key="bigkey", Body=rep * 10)

    # Implicitly bounded range requests.
    key.get(Range="bytes=0-")["Body"].read().should.equal(rep * 10)
    key.get(Range="bytes=50-")["Body"].read().should.equal(rep * 5)
    key.get(Range="bytes=99-")["Body"].read().should.equal(b"9")

    # Explicitly bounded range requests starting from the first byte.
    key.get(Range="bytes=0-0")["Body"].read().should.equal(b"0")
    key.get(Range="bytes=0-49")["Body"].read().should.equal(rep * 5)
    key.get(Range="bytes=0-99")["Body"].read().should.equal(rep * 10)
    key.get(Range="bytes=0-100")["Body"].read().should.equal(rep * 10)
    key.get(Range="bytes=0-700")["Body"].read().should.equal(rep * 10)

    # Explicitly bounded range requests starting from the / a middle byte.
    key.get(Range="bytes=50-54")["Body"].read().should.equal(rep[:5])
    key.get(Range="bytes=50-99")["Body"].read().should.equal(rep * 5)
    key.get(Range="bytes=50-100")["Body"].read().should.equal(rep * 5)
    key.get(Range="bytes=50-700")["Body"].read().should.equal(rep * 5)

    # Explicitly bounded range requests starting from the last byte.
    key.get(Range="bytes=99-99")["Body"].read().should.equal(b"9")
    key.get(Range="bytes=99-100")["Body"].read().should.equal(b"9")
    key.get(Range="bytes=99-700")["Body"].read().should.equal(b"9")

    # Suffix range requests.
    key.get(Range="bytes=-1")["Body"].read().should.equal(b"9")
    key.get(Range="bytes=-60")["Body"].read().should.equal(rep * 6)
    key.get(Range="bytes=-100")["Body"].read().should.equal(rep * 10)
    key.get(Range="bytes=-101")["Body"].read().should.equal(rep * 10)
    key.get(Range="bytes=-700")["Body"].read().should.equal(rep * 10)

    key.content_length.should.equal(100)


@mock_s3
def test_policy():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    bucket = s3.Bucket(bucket_name)
    bucket.create()

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

    with pytest.raises(ClientError) as ex:
        client.get_bucket_policy(Bucket=bucket_name)
    ex.value.response["Error"]["Code"].should.equal("NoSuchBucketPolicy")
    ex.value.response["Error"]["Message"].should.equal(
        "The bucket policy does not exist"
    )

    client.put_bucket_policy(Bucket=bucket_name, Policy=policy)

    client.get_bucket_policy(Bucket=bucket_name)["Policy"].should.equal(policy)

    client.delete_bucket_policy(Bucket=bucket_name)

    with pytest.raises(ClientError) as ex:
        client.get_bucket_policy(Bucket=bucket_name)
    ex.value.response["Error"]["Code"].should.equal("NoSuchBucketPolicy")


@mock_s3
def test_website_configuration_xml():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    bucket = s3.Bucket(bucket_name)
    bucket.create()

    client.put_bucket_website(
        Bucket=bucket_name,
        WebsiteConfiguration={
            "IndexDocument": {"Suffix": "index.html"},
            "RoutingRules": [
                {
                    "Condition": {"KeyPrefixEquals": "test/testing"},
                    "Redirect": {"ReplaceKeyWith": "test.txt"},
                }
            ],
        },
    )
    c = client.get_bucket_website(Bucket=bucket_name)
    c.should.have.key("IndexDocument").equals({"Suffix": "index.html"})
    c.should.have.key("RoutingRules")
    c["RoutingRules"].should.have.length_of(1)
    rule = c["RoutingRules"][0]
    rule.should.have.key("Condition").equals({"KeyPrefixEquals": "test/testing"})
    rule.should.have.key("Redirect").equals({"ReplaceKeyWith": "test.txt"})

    c.shouldnt.have.key("RedirectAllRequestsTo")
    c.shouldnt.have.key("ErrorDocument")


@mock_s3
def test_client_get_object_returns_etag():
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
    resp.get("WebsiteRedirectLocation").should.equal(None)

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
def test_list_objects_with_pagesize_0():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    resp = s3.list_objects(Bucket="mybucket", MaxKeys=0)
    resp["Name"].should.equal("mybucket")
    resp["MaxKeys"].should.equal(0)
    resp["IsTruncated"].should.equal(False)
    resp.shouldnt.have.key("Contents")


@mock_s3
def test_list_objects_truncated_response():
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
    assert resp["IsTruncated"] is True
    assert resp.get("Prefix") is None
    assert resp.get("Delimiter") is None
    assert "NextMarker" in resp

    next_marker = resp["NextMarker"]

    # Second list
    resp = s3.list_objects(Bucket="mybucket", MaxKeys=1, Marker=next_marker)
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "three"
    assert resp["MaxKeys"] == 1
    assert resp["IsTruncated"] is True
    assert resp.get("Prefix") is None
    assert resp.get("Delimiter") is None
    assert "NextMarker" in resp

    next_marker = resp["NextMarker"]

    # Third list
    resp = s3.list_objects(Bucket="mybucket", MaxKeys=1, Marker=next_marker)
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "two"
    assert resp["MaxKeys"] == 1
    assert resp["IsTruncated"] is False
    assert resp.get("Prefix") is None
    assert resp.get("Delimiter") is None
    assert "NextMarker" not in resp


@mock_s3
def test_list_keys_xml_escaped():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    key_name = "Q&A.txt"
    s3.put_object(Bucket="mybucket", Key=key_name, Body=b"is awesome")

    resp = s3.list_objects_v2(Bucket="mybucket", Prefix=key_name)

    assert resp["Contents"][0]["Key"] == key_name
    assert resp["KeyCount"] == 1
    assert resp["MaxKeys"] == 1000
    assert resp["Prefix"] == key_name
    assert resp["IsTruncated"] is False
    assert "Delimiter" not in resp
    assert "StartAfter" not in resp
    assert "NextContinuationToken" not in resp
    assert "Owner" not in resp["Contents"][0]


@mock_s3
def test_list_objects_v2_common_prefix_pagination():
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
def test_list_objects_v2_common_invalid_continuation_token():
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
def test_list_objects_v2_truncated_response():
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
    assert resp["IsTruncated"] is True
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
    assert resp["IsTruncated"] is True
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
    assert resp["IsTruncated"] is False
    assert "Delimiter" not in resp
    assert "Owner" not in listed_object
    assert "StartAfter" not in resp
    assert "NextContinuationToken" not in resp


@mock_s3
def test_list_objects_v2_truncated_response_start_after():
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
    assert resp["IsTruncated"] is True
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
    assert resp["IsTruncated"] is False
    # When ContinuationToken is given, StartAfter is ignored. This also means
    # AWS does not return it in the response.
    assert "StartAfter" not in resp
    assert "Delimiter" not in resp
    assert "Owner" not in listed_object


@mock_s3
def test_list_objects_v2_fetch_owner():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")
    s3.put_object(Bucket="mybucket", Key="one", Body=b"11")

    resp = s3.list_objects_v2(Bucket="mybucket", FetchOwner=True)
    owner = resp["Contents"][0]["Owner"]

    assert "ID" in owner
    assert "DisplayName" in owner
    assert len(owner.keys()) == 2


@mock_s3
def test_list_objects_v2_truncate_combined_keys_and_folders():
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
def test_bucket_create():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="blah")

    s3.Object("blah", "hello.txt").put(Body="some text")

    s3.Object("blah", "hello.txt").get()["Body"].read().decode("utf-8").should.equal(
        "some text"
    )


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
def test_bucket_create_eu_central():
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
def test_head_object():
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
def test_get_object():
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
def test_s3_content_type():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    my_bucket = s3.Bucket("my-cool-bucket")
    my_bucket.create()
    s3_path = "test_s3.py"
    s3 = boto3.resource("s3", verify=False)

    content_type = "text/python-x"
    s3.Object(my_bucket.name, s3_path).put(
        ContentType=content_type, Body=b"some python code"
    )

    s3.Object(my_bucket.name, s3_path).content_type.should.equal(content_type)


@mock_s3
def test_get_missing_object_with_part_number():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="blah")

    with pytest.raises(ClientError) as e:
        s3.Object("blah", "hello.txt").meta.client.head_object(
            Bucket="blah", Key="hello.txt", PartNumber=123
        )

    e.value.response["Error"]["Code"].should.equal("404")


@mock_s3
def test_head_object_with_versioning():
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
def test_deleted_versionings_list():
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
def test_delete_objects_for_specific_version_id():
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
def test_delete_versioned_bucket():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(Bucket="blah")
    client.put_bucket_versioning(
        Bucket="blah", VersioningConfiguration={"Status": "Enabled"}
    )

    resp = client.put_object(Bucket="blah", Key="test1", Body=b"test1")
    client.delete_object(Bucket="blah", Key="test1", VersionId=resp["VersionId"])

    client.delete_bucket(Bucket="blah")


@mock_s3
def test_delete_versioned_bucket_returns_meta():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(Bucket="blah")
    client.put_bucket_versioning(
        Bucket="blah", VersioningConfiguration={"Status": "Enabled"}
    )

    client.put_object(Bucket="blah", Key="test1", Body=b"test1")

    # Delete the object
    del_resp = client.delete_object(Bucket="blah", Key="test1")
    assert "DeleteMarker" not in del_resp
    assert del_resp["VersionId"] is not None

    # Delete the delete marker
    del_resp2 = client.delete_object(
        Bucket="blah", Key="test1", VersionId=del_resp["VersionId"]
    )
    assert del_resp2["DeleteMarker"] is True
    assert "VersionId" not in del_resp2


@mock_s3
def test_get_object_if_modified_since():
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
def test_get_object_if_unmodified_since():
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
def test_get_object_if_match():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.get_object(Bucket=bucket_name, Key=key, IfMatch='"hello"')
    e = err.value
    e.response["Error"]["Code"].should.equal("PreconditionFailed")
    e.response["Error"]["Condition"].should.equal("If-Match")


@mock_s3
def test_get_object_if_none_match():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    etag = s3.put_object(Bucket=bucket_name, Key=key, Body="test")["ETag"]

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.get_object(Bucket=bucket_name, Key=key, IfNoneMatch=etag)
    e = err.value
    e.response["Error"].should.equal({"Code": "304", "Message": "Not Modified"})


@mock_s3
def test_head_object_if_modified_since():
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
def test_head_object_if_unmodified_since():
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
def test_head_object_if_match():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.head_object(Bucket=bucket_name, Key=key, IfMatch='"hello"')
    e = err.value
    e.response["Error"].should.equal({"Code": "412", "Message": "Precondition Failed"})


@mock_s3
def test_head_object_if_none_match():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    etag = s3.put_object(Bucket=bucket_name, Key=key, Body="test")["ETag"]

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3.head_object(Bucket=bucket_name, Key=key, IfNoneMatch=etag)
    e = err.value
    e.response["Error"].should.equal({"Code": "304", "Message": "Not Modified"})


@mock_s3
def test_put_bucket_cors():
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
def test_get_bucket_cors():
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
def test_delete_bucket_cors():
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
    for tech in ["Queue", "Topic", "LambdaFunction"]:
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
def test_put_bucket_logging():
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
def test_list_object_versions():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "000" + str(uuid4())
    key = "key-with-versions"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (b"v1", b"v2")
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
def test_list_object_versions_with_delimiter():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "000" + str(uuid4())
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    for key_index in list(range(1, 5)) + list(range(10, 14)):
        for version_index in range(1, 4):
            body = f"data-{version_index}".encode("UTF-8")
            s3.put_object(
                Bucket=bucket_name, Key=f"key{key_index}-with-data", Body=body
            )
            s3.put_object(
                Bucket=bucket_name, Key=f"key{key_index}-without-data", Body=b""
            )
    response = s3.list_object_versions(Bucket=bucket_name)
    # All object versions should be returned
    len(response["Versions"]).should.equal(
        48
    )  # 8 keys * 2 (one with, one without) * 3 versions per key

    # Use start of key as delimiter
    response = s3.list_object_versions(Bucket=bucket_name, Delimiter="key1")
    response.should.have.key("CommonPrefixes").equal([{"Prefix": "key1"}])
    response.should.have.key("Delimiter").equal("key1")
    # 3 keys that do not contain the phrase 'key1' (key2, key3, key4) * * 2 *  3
    response.should.have.key("Versions").length_of(18)

    # Use in-between key as delimiter
    response = s3.list_object_versions(Bucket=bucket_name, Delimiter="-with-")
    response.should.have.key("CommonPrefixes").equal(
        [
            {"Prefix": "key1-with-"},
            {"Prefix": "key10-with-"},
            {"Prefix": "key11-with-"},
            {"Prefix": "key12-with-"},
            {"Prefix": "key13-with-"},
            {"Prefix": "key2-with-"},
            {"Prefix": "key3-with-"},
            {"Prefix": "key4-with-"},
        ]
    )
    response.should.have.key("Delimiter").equal("-with-")
    # key(1/10/11/12/13)-without, key(2/3/4)-without
    response.should.have.key("Versions").length_of(8 * 1 * 3)

    # Use in-between key as delimiter
    response = s3.list_object_versions(Bucket=bucket_name, Delimiter="1-with-")
    response.should.have.key("CommonPrefixes").equal(
        [{"Prefix": "key1-with-"}, {"Prefix": "key11-with-"}]
    )
    response.should.have.key("Delimiter").equal("1-with-")
    response.should.have.key("Versions").length_of(42)
    all_keys = set([v["Key"] for v in response["Versions"]])
    all_keys.should.contain("key1-without-data")
    all_keys.shouldnt.contain("key1-with-data")
    all_keys.should.contain("key4-with-data")
    all_keys.should.contain("key4-without-data")

    # Use in-between key as delimiter + prefix
    response = s3.list_object_versions(
        Bucket=bucket_name, Prefix="key1", Delimiter="with-"
    )
    response.should.have.key("CommonPrefixes").equal(
        [
            {"Prefix": "key1-with-"},
            {"Prefix": "key10-with-"},
            {"Prefix": "key11-with-"},
            {"Prefix": "key12-with-"},
            {"Prefix": "key13-with-"},
        ]
    )
    response.should.have.key("Delimiter").equal("with-")
    response.should.have.key("KeyMarker").equal("")
    response.shouldnt.have.key("NextKeyMarker")
    response.should.have.key("Versions").length_of(15)
    all_keys = set([v["Key"] for v in response["Versions"]])
    all_keys.should.equal(
        {
            "key1-without-data",
            "key10-without-data",
            "key11-without-data",
            "key13-without-data",
            "key12-without-data",
        }
    )

    # Start at KeyMarker, and filter using Prefix+Delimiter for all subsequent keys
    response = s3.list_object_versions(
        Bucket=bucket_name, Prefix="key1", Delimiter="with-", KeyMarker="key11"
    )
    response.should.have.key("CommonPrefixes").equal(
        [
            {"Prefix": "key11-with-"},
            {"Prefix": "key12-with-"},
            {"Prefix": "key13-with-"},
        ]
    )
    response.should.have.key("Delimiter").equal("with-")
    response.should.have.key("KeyMarker").equal("key11")
    response.shouldnt.have.key("NextKeyMarker")
    response.should.have.key("Versions").length_of(9)
    all_keys = set([v["Key"] for v in response["Versions"]])
    all_keys.should.equal(
        {"key11-without-data", "key12-without-data", "key13-without-data"}
    )

    # Delimiter with Prefix being the entire key
    response = s3.list_object_versions(
        Bucket=bucket_name, Prefix="key1-with-data", Delimiter="-"
    )
    response.should.have.key("Versions").length_of(3)
    response.shouldnt.have.key("CommonPrefixes")

    # Delimiter without prefix
    response = s3.list_object_versions(Bucket=bucket_name, Delimiter="-with-")
    response["CommonPrefixes"].should.have.length_of(8)
    response["CommonPrefixes"].should.contain({"Prefix": "key1-with-"})
    # Should return all keys -without-data
    response.should.have.key("Versions").length_of(24)


@mock_s3
def test_list_object_versions_with_delimiter_for_deleted_objects():
    bucket_name = "tests_bucket"
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    # Create bucket with versioning
    client.create_bucket(Bucket=bucket_name)
    client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"MFADelete": "Disabled", "Status": "Enabled"},
    )

    # Create a history of objects
    for pos in range(2):
        client.put_object(
            Bucket=bucket_name, Key=f"obj_{pos}", Body=f"object {pos}".encode("utf-8")
        )

    for pos in range(2):
        client.put_object(
            Bucket=bucket_name,
            Key=f"hist_obj_{pos}",
            Body=f"history object {pos}".encode("utf-8"),
        )
        for hist_pos in range(2):
            client.put_object(
                Bucket=bucket_name,
                Key=f"hist_obj_{pos}",
                Body=f"object {pos} {hist_pos}".encode("utf-8"),
            )

    for pos in range(2):
        client.put_object(
            Bucket=bucket_name,
            Key=f"del_obj_{pos}",
            Body=f"deleted object {pos}".encode("utf-8"),
        )
        client.delete_object(Bucket=bucket_name, Key=f"del_obj_{pos}")

    # Verify we only retrieve the DeleteMarkers that have this prefix
    objs = client.list_object_versions(Bucket=bucket_name)
    [dm["Key"] for dm in objs["DeleteMarkers"]].should.equal(["del_obj_0", "del_obj_1"])

    hist_objs = client.list_object_versions(Bucket=bucket_name, Prefix="hist_obj")
    hist_objs.shouldnt.have.key("DeleteMarkers")

    del_objs = client.list_object_versions(Bucket=bucket_name, Prefix="del_obj_0")
    [dm["Key"] for dm in del_objs["DeleteMarkers"]].should.equal(["del_obj_0"])


@mock_s3
def test_list_object_versions_with_versioning_disabled():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    s3.create_bucket(Bucket=bucket_name)
    items = (b"v1", b"v2")
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
def test_list_object_versions_with_versioning_enabled_late():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    s3.create_bucket(Bucket=bucket_name)
    items = (b"v1", b"v2")
    s3.put_object(Bucket=bucket_name, Key=key, Body=b"v1")
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    s3.put_object(Bucket=bucket_name, Key=key, Body=b"v2")
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
def test_bad_prefix_list_object_versions():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    bad_prefix = "key-that-does-not-exist"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (b"v1", b"v2")
    for body in items:
        s3.put_object(Bucket=bucket_name, Key=key, Body=body)
    response = s3.list_object_versions(Bucket=bucket_name, Prefix=bad_prefix)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response.should_not.contain("Versions")
    response.should_not.contain("DeleteMarkers")


@mock_s3
def test_delete_markers():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions-and-unicode-ó"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (b"v1", b"v2")
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
def test_multiple_delete_markers():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions-and-unicode-ó"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (b"v1", b"v2")
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
def test_bucket_name_too_long():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3.create_bucket(Bucket="x" * 64)
    exc.value.response["Error"]["Code"].should.equal("InvalidBucketName")


@mock_s3
def test_bucket_name_too_short():
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
def test_delete_objects_unknown_key():
    bucket_name = "test-moto-issue-1581"
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket=bucket_name)
    client.put_object(Bucket=bucket_name, Key="file1", Body="body")

    s = client.delete_objects(
        Bucket=bucket_name, Delete={"Objects": [{"Key": "file1"}, {"Key": "file2"}]}
    )
    s["Deleted"].should.have.length_of(2)
    s["Deleted"].should.contain({"Key": "file1"})
    s["Deleted"].should.contain({"Key": "file2"})
    client.delete_bucket(Bucket=bucket_name)


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

    real_key = "{file_uid}.txt".format(file_uid=file_uid)
    data = s3.generate_presigned_post(
        Bucket=bucket,
        Key=real_key,
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
    assert resp.status_code == 303
    redirect = resp.headers["Location"]
    assert redirect.startswith(success_url)
    parts = urlparse(redirect)
    args = parse_qs(parts.query)
    assert args["key"][0] == real_key
    assert args["bucket"][0] == bucket

    assert s3.get_object(Bucket=bucket, Key=real_key)["Body"].read() == fdata


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
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket)
    s3.Object(bucket, object_key).put(Body="some text")

    file = s3.Object(bucket, object_key)
    response = file.get(Range="bytes=0-1024")
    response["ContentLength"].should.equal(9)


@mock_s3
def test_request_partial_content_should_contain_actual_content_length():
    bucket = "bucket"
    object_key = "key"
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
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
    e.value.response["Error"]["Code"].should.equal("NoSuchVersion")
    e.value.response["Error"]["Message"].should.equal(
        "The specified version does not exist."
    )


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
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
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


if settings.TEST_SERVER_MODE:

    @mock_s3
    def test_upload_data_without_content_type():
        bucket = "mybucket"
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket=bucket)
        data_input = b"some data 123 321"
        req = requests.put("http://localhost:5000/mybucket/test.txt", data=data_input)
        req.status_code.should.equal(200)

        res = s3.get_object(Bucket=bucket, Key="test.txt")
        data = res["Body"].read()
        assert data == data_input


@mock_s3
@pytest.mark.parametrize("prefix", ["file", "file+else", "file&another"])
def test_get_object_versions_with_prefix(prefix):
    bucket_name = "testbucket-3113"
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)
    bucket_versioning = s3_resource.BucketVersioning(bucket_name)
    bucket_versioning.enable()
    s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=f"{prefix}.txt")
    s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=f"{prefix}.txt")
    s3_client.put_object(Bucket=bucket_name, Body=b"alttest", Key=f"alt{prefix}.txt")
    s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=f"{prefix}.txt")

    versions = s3_client.list_object_versions(Bucket=bucket_name, Prefix=prefix)
    versions["Versions"].should.have.length_of(3)
    versions["Prefix"].should.equal(prefix)


@mock_s3
def test_create_bucket_duplicate():
    bucket_name = "same-bucket-test-1371"
    alternate_region = "eu-north-1"
    # Create it in the default region
    default_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    default_client.create_bucket(Bucket=bucket_name)

    # Create it again in the same region - should just return that same bucket
    default_client.create_bucket(Bucket=bucket_name)

    # Create the bucket in a different region - should return an error
    diff_client = boto3.client("s3", region_name=alternate_region)
    with pytest.raises(ClientError) as ex:
        diff_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": alternate_region},
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BucketAlreadyOwnedByYou")
    err["Message"].should.equal(
        "Your previous request to create the named bucket succeeded and you already own it."
    )
    err["BucketName"].should.equal(bucket_name)

    # Try this again - but creating the bucket in a non-default region in the first place
    bucket_name = "same-bucket-nondefault-region-test-1371"
    diff_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": alternate_region},
    )

    # Recreating the bucket in the same non-default region should fail
    with pytest.raises(ClientError) as ex:
        diff_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": alternate_region},
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BucketAlreadyOwnedByYou")
    err["Message"].should.equal(
        "Your previous request to create the named bucket succeeded and you already own it."
    )
    err["BucketName"].should.equal(bucket_name)

    # Recreating the bucket in the default region should fail
    diff_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as ex:
        diff_client.create_bucket(Bucket=bucket_name)
    err = ex.value.response["Error"]
    err["Code"].should.equal("BucketAlreadyOwnedByYou")
    err["Message"].should.equal(
        "Your previous request to create the named bucket succeeded and you already own it."
    )
    err["BucketName"].should.equal(bucket_name)

    # Recreating the bucket in a third region should fail
    diff_client = boto3.client("s3", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        diff_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"},
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BucketAlreadyOwnedByYou")
    err["Message"].should.equal(
        "Your previous request to create the named bucket succeeded and you already own it."
    )
    err["BucketName"].should.equal(bucket_name)


@mock_s3
def test_delete_objects_with_empty_keyname():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "testbucket-4077"
    bucket = resource.create_bucket(Bucket=bucket_name)
    key_name = " "
    bucket.put_object(Key=key_name, Body=b"")
    client.list_objects(Bucket=bucket_name).should.have.key("Contents").length_of(1)

    bucket.delete_objects(Delete={"Objects": [{"Key": key_name}]})
    client.list_objects(Bucket=bucket_name).shouldnt.have.key("Contents")

    bucket.put_object(Key=key_name, Body=b"")

    client.delete_object(Bucket=bucket_name, Key=key_name)
    client.list_objects(Bucket=bucket_name).shouldnt.have.key("Contents")


@mock_s3
def test_head_object_should_return_default_content_type():
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="testbucket")
    s3.Bucket("testbucket").upload_fileobj(BytesIO(b"foobar"), Key="testobject")
    s3_client = boto3.client("s3", region_name="us-east-1")
    resp = s3_client.head_object(Bucket="testbucket", Key="testobject")

    resp["ContentType"].should.equal("binary/octet-stream")
    resp["ResponseMetadata"]["HTTPHeaders"]["content-type"].should.equal(
        "binary/octet-stream"
    )

    s3.Object("testbucket", "testobject").content_type.should.equal(
        "binary/octet-stream"
    )


@mock_s3
def test_request_partial_content_should_contain_all_metadata():
    # github.com/spulec/moto/issues/4203
    bucket = "bucket"
    object_key = "key"
    body = "some text"
    query_range = "0-3"

    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket)
    obj = boto3.resource("s3").Object(bucket, object_key)
    obj.put(Body=body)

    response = obj.get(Range="bytes={}".format(query_range))

    assert response["ETag"] == obj.e_tag
    assert response["LastModified"] == obj.last_modified
    assert response["ContentLength"] == 4
    assert response["ContentRange"] == "bytes {}/{}".format(query_range, len(body))


@mock_s3
def test_head_versioned_key_in_not_versioned_bucket():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="simple-bucked")

    with pytest.raises(ClientError) as ex:
        client.head_object(
            Bucket="simple-bucked", Key="file.txt", VersionId="noVersion"
        )

    response = ex.value.response
    assert response["Error"]["Code"] == "400"


@mock_s3
def test_prefix_encoding():
    bucket_name = "encoding-bucket"
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket=bucket_name)

    client.put_object(Bucket=bucket_name, Key="foo%2Fbar/data", Body=b"")

    data = client.list_objects_v2(Bucket=bucket_name, Prefix="foo%2Fbar")
    assert data["Contents"][0]["Key"].startswith(data["Prefix"])

    data = client.list_objects_v2(Bucket=bucket_name, Prefix="foo%2Fbar", Delimiter="/")
    assert data["CommonPrefixes"] == [{"Prefix": "foo%2Fbar/"}]

    client.put_object(Bucket=bucket_name, Key="foo/bar/data", Body=b"")

    data = client.list_objects_v2(Bucket=bucket_name, Delimiter="/")
    folders = list(
        map(lambda common_prefix: common_prefix["Prefix"], data["CommonPrefixes"])
    )
    assert ["foo%2Fbar/", "foo/"] == folders


@mock_s3
@pytest.mark.parametrize("algorithm", ["CRC32", "CRC32C", "SHA1", "SHA256"])
def test_checksum_response(algorithm):
    bucket_name = "checksum-bucket"
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket=bucket_name)
    if (
        algorithm != "CRC32C"
    ):  # awscrt is required to allow botocore checksum with CRC32C
        response = client.put_object(
            Bucket=bucket_name,
            Key="test-key",
            Body=b"data",
            ChecksumAlgorithm=algorithm,
        )
        assert f"Checksum{algorithm}" in response
