import datetime
import json
import os
import pickle
import uuid
import zlib
from gzip import GzipFile
from io import BytesIO
from time import sleep
from unittest import SkipTest
from urllib.parse import parse_qs, urlparse

import boto3
import botocore.exceptions
import pytest
import requests
from botocore.client import ClientError
from botocore.handlers import disable_signing
from freezegun import freeze_time

import moto.s3.models as s3model
from moto import mock_aws, moto_proxy, settings
from moto.core.utils import utcnow
from moto.moto_api import state_manager
from moto.s3.models import s3_backends
from moto.s3.responses import DEFAULT_REGION_NAME
from tests import DEFAULT_ACCOUNT_ID, aws_verified

from . import s3_aws_verified


class MyModel:
    def __init__(self, name, value, metadata=None):
        self.name = name
        self.value = value
        self.metadata = metadata or {}

    def save(self, region=None):
        s3_client = boto3.client("s3", region_name=region or DEFAULT_REGION_NAME)
        s3_client.put_object(
            Bucket="mybucket", Key=self.name, Body=self.value, Metadata=self.metadata
        )


@mock_aws
def test_keys_are_pickleable():
    """Keys must be pickleable due to boto3 implementation details."""
    key = s3model.FakeKey(
        "name", b"data!", account_id=DEFAULT_ACCOUNT_ID, region_name="us-east-1"
    )
    assert key.value == b"data!"

    pickled = pickle.dumps(key)
    loaded = pickle.loads(pickled)
    assert loaded.value == key.value
    assert loaded.account_id == key.account_id


@mock_aws
@pytest.mark.parametrize(
    "region,partition",
    [("us-west-2", "aws"), ("cn-north-1", "aws-cn"), ("us-isob-east-1", "aws-iso-b")],
)
def test_my_model_save(region, partition):
    # Create Bucket so that test can run
    conn = boto3.resource("s3", region_name=region)
    conn.create_bucket(
        Bucket="mybucket", CreateBucketConfiguration={"LocationConstraint": region}
    )
    ####################################

    model_instance = MyModel("steve", "is awesome")
    model_instance.save(region)

    body = conn.Object("mybucket", "steve").get()["Body"].read().decode()

    assert body == "is awesome"


@mock_aws
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


@mock_aws
def test_resource_get_object_returns_etag():
    conn = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    conn.create_bucket(Bucket="mybucket")

    model_instance = MyModel("steve", "is awesome")
    model_instance.save()

    assert conn.Bucket("mybucket").Object("steve").e_tag == (
        '"d32bda93738f7e03adb22e66c90fbc04"'
    )


@mock_aws
def test_key_save_to_missing_bucket():
    s3_resource = boto3.resource("s3")

    key = s3_resource.Object("mybucket", "the-key")
    with pytest.raises(ClientError) as ex:
        key.put(Body=b"foobar")
    assert ex.value.response["Error"]["Code"] == "NoSuchBucket"
    assert ex.value.response["Error"]["Message"] == (
        "The specified bucket does not exist"
    )


@mock_aws
def test_missing_key_request():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Only test status code in DecoratorMode")
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="foobar")

    response = requests.get("http://foobar.s3.amazonaws.com/the-key")
    assert response.status_code == 404


@mock_aws
def test_empty_key():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    key = s3_resource.Object("foobar", "the-key")
    key.put(Body=b"")

    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert resp["ContentLength"] == 0
    assert resp["Body"].read() == b""


@mock_aws
def test_key_name_encoding_in_listing():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    name = "6T7\x159\x12\r\x08.txt"

    key = s3_resource.Object("foobar", name)
    key.put(Body=b"")

    key_received = client.list_objects(Bucket="foobar")["Contents"][0]["Key"]
    assert key_received == name

    key_received = client.list_objects_v2(Bucket="foobar")["Contents"][0]["Key"]
    assert key_received == name

    name = "example/file.text"
    client.put_object(Bucket="foobar", Key=name, Body=b"")

    key_received = client.list_objects(
        Bucket="foobar", Prefix="example/", Delimiter="/", MaxKeys=1, EncodingType="url"
    )["Contents"][0]["Key"]
    assert key_received == name


@mock_aws
def test_empty_key_set_on_existing_key():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    key = s3_resource.Object("foobar", "the-key")
    key.put(Body=b"some content")

    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert resp["ContentLength"] == 12
    assert resp["Body"].read() == b"some content"

    key.put(Body=b"")

    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert resp["ContentLength"] == 0
    assert resp["Body"].read() == b""


@mock_aws
def test_large_key_save():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    key = s3_resource.Object("foobar", "the-key")
    key.put(Body=b"foobar" * 100000)

    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert resp["Body"].read() == b"foobar" * 100000


@mock_aws
def test_set_metadata():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    key = s3_resource.Object("foobar", "the-key")
    key.put(Body=b"some value", Metadata={"md": "Metadatastring"})

    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert resp["Metadata"] == {"md": "Metadatastring"}


@freeze_time("2012-01-01 12:00:00")
@mock_aws
def test_last_modified():
    # See https://github.com/boto/boto/issues/466
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    key = s3_resource.Object("foobar", "the-key")
    key.put(Body=b"some value", Metadata={"md": "Metadatastring"})

    resp = client.list_objects_v2(Bucket="foobar")["Contents"]
    assert isinstance(resp[0]["LastModified"], datetime.datetime)

    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert isinstance(resp["LastModified"], datetime.datetime)
    as_header = resp["ResponseMetadata"]["HTTPHeaders"]["last-modified"]
    assert isinstance(as_header, str)
    if settings.TEST_DECORATOR_MODE:
        assert as_header == "Sun, 01 Jan 2012 12:00:00 GMT"


@mock_aws
def test_missing_bucket():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as ex:
        client.head_bucket(Bucket="mybucket")
    assert ex.value.response["Error"]["Code"] == "404"
    assert ex.value.response["Error"]["Message"] == "Not Found"

    with pytest.raises(ClientError) as ex:
        client.head_bucket(Bucket="dash-in-name")
    assert ex.value.response["Error"]["Code"] == "404"
    assert ex.value.response["Error"]["Message"] == "Not Found"


@mock_aws
def test_create_existing_bucket():
    """Creating a bucket that already exists should raise an Error."""
    client = boto3.client("s3", region_name="us-west-2")
    kwargs = {
        "Bucket": "foobar",
        "CreateBucketConfiguration": {"LocationConstraint": "us-west-2"},
    }
    client.create_bucket(**kwargs)
    with pytest.raises(ClientError) as ex:
        client.create_bucket(**kwargs)
    assert ex.value.response["Error"]["Code"] == "BucketAlreadyOwnedByYou"
    assert ex.value.response["Error"]["Message"] == (
        "Your previous request to create the named bucket succeeded and you already own it."
    )


@aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "constraint", ["us-east-1", "us-east-2", "eu-central-1", "us-gov-east-2"]
)
def test_create_bucket_with_wrong_location_constraint(constraint):
    client = boto3.client("s3", region_name="us-west-2")
    kwargs = {
        "Bucket": str(uuid.uuid4()),
        "CreateBucketConfiguration": {"LocationConstraint": constraint},
    }
    with pytest.raises(ClientError) as ex:
        client.create_bucket(**kwargs)
    err = ex.value.response["Error"]
    assert err["Code"] == "IllegalLocationConstraintException"
    assert (
        err["Message"]
        == f"The {constraint} location constraint is incompatible for the region specific endpoint this request was sent to."
    )


@aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize("constraint", ["us-east-2", "eu-central-1"])
def test_create_bucket_in_regions_from_us_east_1(constraint):
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = str(uuid.uuid4())
    client.create_bucket(
        Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": constraint}
    )
    assert (
        client.get_bucket_location(Bucket=bucket_name)["LocationConstraint"]
        == constraint
    )
    client.delete_bucket(Bucket=bucket_name)


@mock_aws
def test_create_existing_bucket_in_us_east_1():
    """Creating a bucket that already exists in us-east-1 returns the bucket.

    http://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html
    Your previous request to create the named bucket succeeded and you already
    own it. You get this error in all AWS regions except US Standard,
    us-east-1. In us-east-1 region, you will get 200 OK, but it is no-op (if
    bucket exists it Amazon S3 will not do anything).
    """
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")
    client.create_bucket(Bucket="foobar")


@mock_aws
def test_bucket_deletion():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")

    key = s3_resource.Object("foobar", "the-key")
    key.put(Body=b"some value")

    # Try to delete a bucket that still has keys
    with pytest.raises(ClientError) as ex:
        client.delete_bucket(Bucket="foobar")
    assert ex.value.response["Error"]["Code"] == "BucketNotEmpty"
    assert ex.value.response["Error"]["Message"] == (
        "The bucket you tried to delete is not empty"
    )

    client.delete_object(Bucket="foobar", Key="the-key")
    client.delete_bucket(Bucket="foobar")

    # Delete non-existent bucket
    with pytest.raises(ClientError) as ex:
        client.delete_bucket(Bucket="foobar")
    assert ex.value.response["Error"]["Code"] == "NoSuchBucket"
    assert ex.value.response["Error"]["Message"] == (
        "The specified bucket does not exist"
    )


@mock_aws
def test_get_all_buckets():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")
    client.create_bucket(Bucket="foobar2")

    assert len(client.list_buckets()["Buckets"]) == 2


@mock_aws
def test_post_to_bucket():
    if not settings.TEST_DECORATOR_MODE:
        # ServerMode does not allow unauthorized requests
        raise SkipTest()

    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")

    requests.post(
        "https://foobar.s3.amazonaws.com/", {"key": "the-key", "file": "nothing"}
    )

    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert resp["Body"].read() == b"nothing"


@mock_aws
def test_post_with_metadata_to_bucket():
    if not settings.TEST_DECORATOR_MODE:
        # ServerMode does not allow unauthorized requests
        raise SkipTest()
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="foobar")

    requests.post(
        "https://foobar.s3.amazonaws.com/",
        {"key": "the-key", "file": "nothing", "x-amz-meta-test": "metadata"},
    )

    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert resp["Metadata"] == {"test": "metadata"}


@mock_aws
def test_delete_versioned_objects():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = "test"
    key = "test"

    s3_client.create_bucket(Bucket=bucket)

    s3_client.put_object(Bucket=bucket, Key=key, Body=b"")

    s3_client.put_bucket_versioning(
        Bucket=bucket, VersioningConfiguration={"Status": "Enabled"}
    )

    objects = s3_client.list_objects_v2(Bucket=bucket).get("Contents")
    versions = s3_client.list_object_versions(Bucket=bucket).get("Versions")
    delete_markers = s3_client.list_object_versions(Bucket=bucket).get("DeleteMarkers")

    assert len(objects) == 1
    assert len(versions) == 1
    assert delete_markers is None

    s3_client.delete_object(Bucket=bucket, Key=key)

    objects = s3_client.list_objects_v2(Bucket=bucket).get("Contents")
    versions = s3_client.list_object_versions(Bucket=bucket).get("Versions")
    delete_markers = s3_client.list_object_versions(Bucket=bucket).get("DeleteMarkers")

    assert objects is None
    assert len(versions) == 1
    assert len(delete_markers) == 1

    s3_client.delete_object(
        Bucket=bucket, Key=key, VersionId=versions[0].get("VersionId")
    )

    objects = s3_client.list_objects_v2(Bucket=bucket).get("Contents")
    versions = s3_client.list_object_versions(Bucket=bucket).get("Versions")
    delete_markers = s3_client.list_object_versions(Bucket=bucket).get("DeleteMarkers")

    assert objects is None
    assert versions is None
    assert len(delete_markers) == 1

    s3_client.delete_object(
        Bucket=bucket, Key=key, VersionId=delete_markers[0].get("VersionId")
    )

    objects = s3_client.list_objects_v2(Bucket=bucket).get("Contents")
    versions = s3_client.list_object_versions(Bucket=bucket).get("Versions")
    delete_markers = s3_client.list_object_versions(Bucket=bucket).get("DeleteMarkers")

    assert objects is None
    assert versions is None
    assert delete_markers is None


@s3_aws_verified
@pytest.mark.aws_verified
def test_delete_missing_key(bucket_name=None):
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket(bucket_name)

    s3_resource.Object(bucket_name, "key1").put(Body=b"some value")
    s3_resource.Object(bucket_name, "key2").put(Body=b"some value")
    s3_resource.Object(bucket_name, "key3").put(Body=b"some value")
    s3_resource.Object(bucket_name, "key4").put(Body=b"some value")

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
    assert len(result["Deleted"]) == 4
    assert {"Key": "unknown"} in result["Deleted"]
    assert {"Key": "key1"} in result["Deleted"]
    assert {"Key": "key3"} in result["Deleted"]
    assert {"Key": "typo"} in result["Deleted"]
    assert "Errors" not in result

    objects = list(bucket.objects.all())
    assert {o.key for o in objects} == set(["key2", "key4"])


@mock_aws
def test_delete_empty_keys_list():
    with pytest.raises(ClientError) as err:
        boto3.client("s3").delete_objects(Bucket="foobar", Delete={"Objects": []})
    assert err.value.response["Error"]["Code"] == "MalformedXML"


@pytest.mark.parametrize("name", ["firstname.lastname", "with-dash"])
@mock_aws
def test_bucket_name_with_special_chars(name):
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket(name)
    bucket.create()

    s3_resource.Object(name, "the-key").put(Body=b"some value")

    resp = client.get_object(Bucket=name, Key="the-key")
    assert resp["Body"].read() == b"some value"


@pytest.mark.parametrize(
    "key", ["normal", "test_list_keys_2/x?y", "/the-key-unîcode/test"]
)
@mock_aws
def test_key_with_special_characters(key):
    if settings.is_test_proxy_mode():
        raise SkipTest("Keys starting with a / don't work well in ProxyMode")
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("testname")
    bucket.create()

    s3_resource.Object("testname", key).put(Body=b"value")

    objects = list(bucket.objects.all())
    assert [o.key for o in objects] == [key]

    resp = client.get_object(Bucket="testname", Key=key)
    assert resp["Body"].read() == b"value"


@s3_aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize("versioned", [True, False], ids=["versioned", "not versioned"])
def test_conditional_write(versioned, bucket_name=None):
    s3 = boto3.client("s3", region_name="us-east-1")
    if versioned:
        enable_versioning(bucket_name, s3)

    s3.put_object(
        Key="test_object",
        Body="test",
        Bucket=bucket_name,
        IfNoneMatch="*",
    )

    with pytest.raises(ClientError) as exc:
        s3.put_object(
            Key="test_object",
            Body="another_test",
            Bucket=bucket_name,
            IfNoneMatch="*",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "PreconditionFailed"
    assert (
        err["Message"]
        == "At least one of the pre-conditions you specified did not hold"
    )
    assert err["Condition"] == "If-None-Match"


@mock_aws
def test_bucket_key_listing_order():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "test_bucket"
    bucket = s3_resource.Bucket(bucket_name)
    bucket.create()
    prefix = "toplevel/"

    names = ["x/key", "y.key1", "y.key2", "y.key3", "x/y/key", "x/y/z/key"]

    for name in names:
        s3_resource.Object(bucket_name, prefix + name).put(Body=b"somedata")

    delimiter = ""
    keys = [x.key for x in bucket.objects.filter(Prefix=prefix, Delimiter=delimiter)]
    assert keys == [
        "toplevel/x/key",
        "toplevel/x/y/key",
        "toplevel/x/y/z/key",
        "toplevel/y.key1",
        "toplevel/y.key2",
        "toplevel/y.key3",
    ]

    delimiter = "/"
    keys = [x.key for x in bucket.objects.filter(Prefix=prefix, Delimiter=delimiter)]
    assert keys == ["toplevel/y.key1", "toplevel/y.key2", "toplevel/y.key3"]

    # Test delimiter with no prefix
    keys = [x.key for x in bucket.objects.filter(Delimiter=delimiter)]
    assert keys == []

    prefix = "toplevel/x"
    keys = [x.key for x in bucket.objects.filter(Prefix=prefix)]
    assert keys == ["toplevel/x/key", "toplevel/x/y/key", "toplevel/x/y/z/key"]

    keys = [x.key for x in bucket.objects.filter(Prefix=prefix, Delimiter=delimiter)]
    assert keys == []


@mock_aws
@pytest.mark.parametrize(
    "region,partition",
    [("us-west-2", "aws"), ("cn-north-1", "aws-cn"), ("us-isob-east-1", "aws-iso-b")],
)
def test_key_with_reduced_redundancy(region, partition):
    s3_resource = boto3.resource("s3", region_name=region)
    bucket_name = "test_bucket"
    s3_resource.create_bucket(
        Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region}
    )
    bucket = s3_resource.Bucket(bucket_name)

    bucket.put_object(
        Key="test_rr_key", Body=b"somedata", StorageClass="REDUCED_REDUNDANCY"
    )

    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    assert [x.storage_class for x in bucket.objects.all()] == ["REDUCED_REDUNDANCY"]


@freeze_time("2012-01-01 12:00:00")
@mock_aws
def test_restore_key():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()

    key = bucket.put_object(Key="the-key", Body=b"somedata", StorageClass="GLACIER")
    assert key.restore is None
    resp = key.restore_object(RestoreRequest={"Days": 1})
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 202
    if settings.TEST_SERVER_MODE:
        assert 'ongoing-request="false"' in key.restore
    elif settings.TEST_DECORATOR_MODE:
        assert key.restore == (
            'ongoing-request="false", expiry-date="Mon, 02 Jan 2012 12:00:00 GMT"'
        )

    resp = key.restore_object(RestoreRequest={"Days": 2})
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    if settings.TEST_SERVER_MODE:
        assert 'ongoing-request="false"' in key.restore
    elif settings.TEST_DECORATOR_MODE:
        assert key.restore == (
            'ongoing-request="false", expiry-date="Tue, 03 Jan 2012 12:00:00 GMT"'
        )


@freeze_time("2012-01-01 12:00:00")
@mock_aws
def test_restore_key_transition():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't set transition directly in ServerMode")

    state_manager.set_transition(
        model_name="s3::keyrestore", transition={"progression": "manual", "times": 1}
    )

    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()

    key = bucket.put_object(Key="the-key", Body=b"somedata", StorageClass="GLACIER")
    assert key.restore is None
    key.restore_object(RestoreRequest={"Days": 1})

    # first call: there should be an ongoing request
    assert 'ongoing-request="true"' in key.restore

    # second call: request should be done
    key.load()
    assert 'ongoing-request="false"' in key.restore

    # third call: request should still be done
    key.load()
    assert 'ongoing-request="false"' in key.restore

    state_manager.unset_transition(model_name="s3::keyrestore")


@mock_aws
def test_restore_unknown_key():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="mybucket")

    with pytest.raises(ClientError) as exc:
        client.restore_object(
            Bucket="mybucket", Key="unknown", RestoreRequest={"Days": 1}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchKey"


@mock_aws
def test_cannot_restore_standard_class_object():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()

    key = bucket.put_object(Key="the-key", Body=b"somedata")
    with pytest.raises(ClientError) as exc:
        key.restore_object(RestoreRequest={"Days": 1})

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidObjectState"
    assert err["StorageClass"] == "STANDARD"
    assert err["Message"] == (
        "The operation is not valid for the object's storage class"
    )


@mock_aws
def test_restore_object_invalid_request_params():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't set transition directly in ServerMode")

    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()

    key = bucket.put_object(Key="the-key", Body=b"somedata", StorageClass="GLACIER")

    # `Days` must be provided except for select requests
    with pytest.raises(ClientError) as exc:
        key.restore_object(RestoreRequest={})
    err = exc.value.response["Error"]
    assert err["Code"] == "DaysMustProvidedExceptForSelectRequest"
    assert err["Message"] == "`Days` must be provided except for select requests"

    # `Days` must not be provided for select requests
    with pytest.raises(ClientError) as exc:
        key.restore_object(RestoreRequest={"Days": 1, "Type": "SELECT"})
    err = exc.value.response["Error"]
    assert err["Code"] == "DaysMustNotProvidedForSelectRequest"
    assert err["Message"] == "`Days` must not be provided for select requests"


@mock_aws
def test_get_versioning_status():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()

    version_info = s3_resource.BucketVersioning("foobar")
    assert version_info.status is None

    version_info.enable()
    assert version_info.status == "Enabled"

    version_info.suspend()
    assert version_info.status == "Suspended"


@mock_aws
def test_key_version():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()
    bucket.Versioning().enable()

    versions = []

    key = bucket.put_object(Key="the-key", Body=b"somedata")
    versions.append(key.version_id)
    key.put(Body=b"some string")
    versions.append(key.version_id)
    assert len(set(versions)) == 2

    key = client.get_object(Bucket="foobar", Key="the-key")
    assert key["VersionId"] == versions[-1]


@mock_aws
def test_list_versions():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()
    bucket.Versioning().enable()

    key_versions = []

    key = bucket.put_object(Key="the-key", Body=b"Version 1")
    key_versions.append(key.version_id)
    key = bucket.put_object(Key="the-key", Body=b"Version 2")
    key_versions.append(key.version_id)
    assert len(key_versions) == 2

    versions = client.list_object_versions(Bucket="foobar")["Versions"]
    assert len(versions) == 2

    assert versions[0]["Key"] == "the-key"
    assert versions[0]["VersionId"] == key_versions[1]
    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert resp["Body"].read() == b"Version 2"
    resp = client.get_object(
        Bucket="foobar", Key="the-key", VersionId=versions[0]["VersionId"]
    )
    assert resp["Body"].read() == b"Version 2"

    assert versions[1]["Key"] == "the-key"
    assert versions[1]["VersionId"] == key_versions[0]
    resp = client.get_object(
        Bucket="foobar", Key="the-key", VersionId=versions[1]["VersionId"]
    )
    assert resp["Body"].read() == b"Version 1"

    bucket.put_object(Key="the2-key", Body=b"Version 1")

    assert len(list(bucket.objects.all())) == 2
    versions = client.list_object_versions(Bucket="foobar", Prefix="the2")["Versions"]
    assert len(versions) == 1


@mock_aws
def test_acl_setting():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()

    content = b"imafile"
    keyname = "test.txt"
    bucket.put_object(
        Key=keyname, Body=content, ContentType="text/plain", ACL="public-read"
    )

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    assert {
        "Grantee": {
            "Type": "Group",
            "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
        },
        "Permission": "READ",
    } in grants


@mock_aws
def test_acl_setting_via_headers():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()

    keyname = "test.txt"

    bucket.put_object(Key=keyname, Body=b"imafile")
    client.put_object_acl(ACL="public-read", Bucket="foobar", Key=keyname)

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    assert {
        "Grantee": {
            "Type": "Group",
            "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
        },
        "Permission": "READ",
    } in grants


@mock_aws
def test_acl_switching():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()
    keyname = "test.txt"

    bucket.put_object(Key=keyname, Body=b"asdf", ACL="public-read")
    client.put_object_acl(ACL="private", Bucket="foobar", Key=keyname)

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    assert {
        "Grantee": {
            "Type": "Group",
            "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
        },
        "Permission": "READ",
    } not in grants


@mock_aws
def test_acl_switching_nonexistent_key():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    with pytest.raises(ClientError) as exc:
        s3_client.put_object_acl(Bucket="mybucket", Key="nonexistent", ACL="private")

    assert exc.value.response["Error"]["Code"] == "NoSuchKey"


@mock_aws
def test_streaming_upload_from_file_to_presigned_url():
    s3_resource = boto3.resource("s3", region_name="us-east-1")
    bucket = s3_resource.Bucket("test-bucket")
    bucket.create()
    bucket.put_object(Body=b"ABCD", Key="file.txt")

    params = {"Bucket": "test-bucket", "Key": "file.txt"}
    presigned_url = boto3.client("s3").generate_presigned_url(
        "put_object", params, ExpiresIn=900
    )
    with open(__file__, "rb") as fhandle:
        get_kwargs = {"data": fhandle}
        if settings.is_test_proxy_mode():
            add_proxy_details(get_kwargs)
        response = requests.get(presigned_url, **get_kwargs)
    assert response.status_code == 200


@mock_aws
def test_upload_from_file_to_presigned_url():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    params = {"Bucket": "mybucket", "Key": "file_upload"}
    presigned_url = boto3.client("s3").generate_presigned_url(
        "put_object", params, ExpiresIn=900
    )

    file = open("text.txt", "w", encoding="utf-8")
    file.write("test")
    file.close()
    files = {"upload_file": open("text.txt", "rb")}

    put_kwargs = {"files": files}
    if settings.is_test_proxy_mode():
        add_proxy_details(put_kwargs)
    requests.put(presigned_url, **put_kwargs)
    resp = s3_client.get_object(Bucket="mybucket", Key="file_upload")
    data = resp["Body"].read()
    assert data == b"test"
    # cleanup
    os.remove("text.txt")


@mock_aws
def test_upload_file_with_checksum_algorithm():
    random_bytes = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00"
        b"\x00\xff\n\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\n"
    )
    with open("rb.tmp", mode="wb") as fhandle:
        fhandle.write(random_bytes)
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = "mybucket"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.upload_file(
        "rb.tmp", bucket, "my_key.csv", ExtraArgs={"ChecksumAlgorithm": "SHA256"}
    )
    os.remove("rb.tmp")

    actual_content = s3_resource.Object(bucket, "my_key.csv").get()["Body"].read()
    assert random_bytes == actual_content


@mock_aws
def test_put_large_with_checksum_algorithm():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = "mybucket"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.put_object(
        Bucket=bucket,
        Key="the-key",
        Body=b"test" * 1000000,
        ChecksumAlgorithm="SHA256",
    )

    resp = s3_client.get_object(Bucket="mybucket", Key="the-key")
    assert resp["Body"].read() == b"test" * 1000000


@mock_aws
def test_put_chunked_with_v4_signature_in_body():
    bucket_name = "mybucket"
    file_name = "file"
    content = "CONTENT"
    content_bytes = bytes(content, encoding="utf8")
    # 'CONTENT' as received in moto, when PutObject is called in java AWS SDK v2
    chunked_body = (
        b"7;chunk-signature=bd479c607ec05dd9d570893f74eed76a4b333dfa37ad"
        b"6446f631ec47dc52e756\r\nCONTENT\r\n"
        b"0;chunk-signature=d192ec4075ddfc18d2ef4da4f55a87dc762ba4417b3b"
        b"d41e70c282f8bec2ece0\r\n\r\n"
    )

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)

    model = MyModel(file_name, content)
    model.save()

    boto_etag = s3_client.get_object(Bucket=bucket_name, Key=file_name)["ETag"]

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
    resp = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    body = resp["Body"].read()
    assert body == content_bytes

    etag = resp["ETag"]
    assert etag == boto_etag


@mock_aws
def test_s3_object_in_private_bucket():
    s3_resource = boto3.resource("s3", "us-east-1")
    bucket = s3_resource.Bucket("test-bucket")
    bucket.create(ACL="private")
    bucket.put_object(ACL="private", Body=b"ABCD", Key="file.txt")

    s3_anonymous = boto3.resource("s3")
    s3_anonymous.meta.client.meta.events.register("choose-signer.s3.*", disable_signing)

    with pytest.raises(ClientError) as exc:
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket").get()
    assert exc.value.response["Error"]["Code"] == "403"

    bucket.put_object(ACL="public-read", Body=b"ABCD", Key="file.txt")
    contents = (
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket")
        .get()["Body"]
        .read()
    )
    assert contents == b"ABCD"


@mock_aws
def test_unicode_key():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("mybucket")
    bucket.create()

    key = bucket.put_object(Key="こんにちは.jpg", Body=b"Hello world!")

    assert [listed_key.key for listed_key in bucket.objects.all()] == [key.key]
    fetched_key = s3_resource.Object("mybucket", key.key)
    assert fetched_key.key == key.key
    assert fetched_key.get()["Body"].read().decode("utf-8") == "Hello world!"


@mock_aws
def test_unicode_value():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("mybucket")
    bucket.create()

    bucket.put_object(Key="some_key", Body="こんにちは.jpg")

    key = s3_resource.Object("mybucket", "some_key")
    assert key.get()["Body"].read().decode("utf-8") == "こんにちは.jpg"


@mock_aws
def test_setting_content_encoding():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("mybucket")
    bucket.create()

    bucket.put_object(Body=b"abcdef", ContentEncoding="gzip", Key="keyname")

    key = s3_resource.Object("mybucket", "keyname")
    assert key.content_encoding == "gzip"


@mock_aws
def test_bucket_location_default():
    cli = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    # No LocationConstraint ==> us-east-1
    cli.create_bucket(Bucket=bucket_name)
    assert cli.get_bucket_location(Bucket=bucket_name)["LocationConstraint"] is None


@mock_aws
def test_bucket_location_nondefault():
    cli = boto3.client("s3", region_name="eu-central-1")
    bucket_name = "mybucket"
    # LocationConstraint set for non default regions
    cli.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
    )
    assert (
        cli.get_bucket_location(Bucket=bucket_name)["LocationConstraint"]
        == "eu-central-1"
    )


@mock_aws
def test_s3_location_should_error_outside_useast1():
    s3_client = boto3.client("s3", region_name="eu-west-1")

    bucket_name = "asdfasdfsdfdsfasda"

    with pytest.raises(ClientError) as exc:
        s3_client.create_bucket(Bucket=bucket_name)
    assert exc.value.response["Error"]["Message"] == (
        "The unspecified location constraint is incompatible for the "
        "region specific endpoint this request was sent to."
    )


@mock_aws
def test_ranged_get():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("mybucket")
    bucket.create()
    rep = b"0123456789"
    key = bucket.put_object(Key="bigkey", Body=rep * 10)

    # Implicitly bounded range requests.
    assert key.get(Range="bytes=0-")["Body"].read() == rep * 10
    assert key.get(Range="bytes=50-")["Body"].read() == rep * 5
    assert key.get(Range="bytes=99-")["Body"].read() == b"9"

    # Explicitly bounded range requests starting from the first byte.
    assert key.get(Range="bytes=0-0")["Body"].read() == b"0"
    assert key.get(Range="bytes=0-49")["Body"].read() == rep * 5
    assert key.get(Range="bytes=0-99")["Body"].read() == rep * 10
    assert key.get(Range="bytes=0-100")["Body"].read() == rep * 10
    assert key.get(Range="bytes=0-700")["Body"].read() == rep * 10

    # Explicitly bounded range requests starting from the / a middle byte.
    assert key.get(Range="bytes=50-54")["Body"].read() == rep[:5]
    assert key.get(Range="bytes=50-99")["Body"].read() == rep * 5
    assert key.get(Range="bytes=50-100")["Body"].read() == rep * 5
    assert key.get(Range="bytes=50-700")["Body"].read() == rep * 5

    # Explicitly bounded range requests starting from the last byte.
    assert key.get(Range="bytes=99-99")["Body"].read() == b"9"
    assert key.get(Range="bytes=99-100")["Body"].read() == b"9"
    assert key.get(Range="bytes=99-700")["Body"].read() == b"9"

    # Suffix range requests.
    assert key.get(Range="bytes=-1")["Body"].read() == b"9"
    assert key.get(Range="bytes=-60")["Body"].read() == rep * 6
    assert key.get(Range="bytes=-100")["Body"].read() == rep * 10
    assert key.get(Range="bytes=-101")["Body"].read() == rep * 10
    assert key.get(Range="bytes=-700")["Body"].read() == rep * 10

    assert key.content_length == 100

    assert key.get(Range="bytes=0-0")["Body"].read() == b"0"
    assert key.get(Range="bytes=1-1")["Body"].read() == b"1"

    range_req = key.get(Range="bytes=1-0")
    assert range_req["Body"].read() == rep * 10
    # assert that the request was not treated as a range request
    assert range_req["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "ContentRange" not in range_req

    range_req = key.get(Range="bytes=-1-")
    assert range_req["Body"].read() == rep * 10
    assert range_req["ResponseMetadata"]["HTTPStatusCode"] == 200

    range_req = key.get(Range="bytes=0--1")
    assert range_req["Body"].read() == rep * 10
    assert range_req["ResponseMetadata"]["HTTPStatusCode"] == 200

    range_req = key.get(Range="bytes=0-1,3-4,7-9")
    assert range_req["Body"].read() == rep * 10
    assert range_req["ResponseMetadata"]["HTTPStatusCode"] == 200

    range_req = key.get(Range="bytes=-")
    assert range_req["Body"].read() == rep * 10
    assert range_req["ResponseMetadata"]["HTTPStatusCode"] == 200

    with pytest.raises(ClientError) as ex:
        key.get(Range="bytes=-0")
    assert ex.value.response["Error"]["Code"] == "InvalidRange"
    assert (
        ex.value.response["Error"]["Message"]
        == "The requested range is not satisfiable"
    )
    assert ex.value.response["Error"]["ActualObjectSize"] == "100"
    assert ex.value.response["Error"]["RangeRequested"] == "bytes=-0"

    with pytest.raises(ClientError) as ex:
        key.get(Range="bytes=101-200")
    assert ex.value.response["Error"]["Code"] == "InvalidRange"
    assert (
        ex.value.response["Error"]["Message"]
        == "The requested range is not satisfiable"
    )
    assert ex.value.response["Error"]["ActualObjectSize"] == "100"
    assert ex.value.response["Error"]["RangeRequested"] == "bytes=101-200"


@mock_aws
def test_policy():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    bucket = s3_resource.Bucket(bucket_name)
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
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
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
    assert ex.value.response["Error"]["Code"] == "NoSuchBucketPolicy"
    assert ex.value.response["Error"]["Message"] == "The bucket policy does not exist"

    client.put_bucket_policy(Bucket=bucket_name, Policy=policy)

    assert client.get_bucket_policy(Bucket=bucket_name)["Policy"] == policy

    client.delete_bucket_policy(Bucket=bucket_name)

    with pytest.raises(ClientError) as ex:
        client.get_bucket_policy(Bucket=bucket_name)
    assert ex.value.response["Error"]["Code"] == "NoSuchBucketPolicy"


@mock_aws
def test_website_configuration_xml():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    bucket = s3_resource.Bucket(bucket_name)
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
    site_info = client.get_bucket_website(Bucket=bucket_name)
    assert site_info["IndexDocument"] == {"Suffix": "index.html"}
    assert "RoutingRules" in site_info
    assert len(site_info["RoutingRules"]) == 1
    rule = site_info["RoutingRules"][0]
    assert rule["Condition"] == {"KeyPrefixEquals": "test/testing"}
    assert rule["Redirect"] == {"ReplaceKeyWith": "test.txt"}

    assert "RedirectAllRequestsTo" not in site_info
    assert "ErrorDocument" not in site_info


@mock_aws
def test_client_get_object_returns_etag():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    s3_client.put_object(Bucket="mybucket", Key="steve", Body=b"is awesome")
    resp = s3_client.get_object(Bucket="mybucket", Key="steve")
    assert resp["ETag"] == '"d32bda93738f7e03adb22e66c90fbc04"'


@mock_aws
def test_website_redirect_location():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    s3_client.put_object(Bucket="mybucket", Key="steve", Body=b"is awesome")
    resp = s3_client.get_object(Bucket="mybucket", Key="steve")
    assert resp.get("WebsiteRedirectLocation") is None

    url = "https://github.com/getmoto/moto"
    s3_client.put_object(
        Bucket="mybucket", Key="steve", Body=b"is awesome", WebsiteRedirectLocation=url
    )
    resp = s3_client.get_object(Bucket="mybucket", Key="steve")
    assert resp["WebsiteRedirectLocation"] == url


@mock_aws
def test_delimiter_optional_in_response():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    s3_client.put_object(Bucket="mybucket", Key="one", Body=b"1")
    resp = s3_client.list_objects(Bucket="mybucket", MaxKeys=1)
    assert resp.get("Delimiter") is None
    resp = s3_client.list_objects(Bucket="mybucket", MaxKeys=1, Delimiter="/")
    assert resp.get("Delimiter") == "/"


@mock_aws
def test_list_objects_with_pagesize_0():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    resp = s3_client.list_objects(Bucket="mybucket", MaxKeys=0)
    assert resp["Name"] == "mybucket"
    assert resp["MaxKeys"] == 0
    assert resp["IsTruncated"] is False
    assert "Contents" not in resp


@mock_aws
def test_list_objects_truncated_response():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    s3_client.put_object(Bucket="mybucket", Key="one", Body=b"1")
    s3_client.put_object(Bucket="mybucket", Key="two", Body=b"22")
    s3_client.put_object(Bucket="mybucket", Key="three", Body=b"333")

    # First list
    resp = s3_client.list_objects(Bucket="mybucket", MaxKeys=1)
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "one"
    assert resp["MaxKeys"] == 1
    assert resp["IsTruncated"] is True
    assert resp.get("Prefix") is None
    assert resp.get("Delimiter") is None
    assert "NextMarker" in resp

    next_marker = resp["NextMarker"]

    # Second list
    resp = s3_client.list_objects(Bucket="mybucket", MaxKeys=1, Marker=next_marker)
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "three"
    assert resp["MaxKeys"] == 1
    assert resp["IsTruncated"] is True
    assert resp.get("Prefix") is None
    assert resp.get("Delimiter") is None
    assert "NextMarker" in resp

    next_marker = resp["NextMarker"]

    # Third list
    resp = s3_client.list_objects(Bucket="mybucket", MaxKeys=1, Marker=next_marker)
    listed_object = resp["Contents"][0]

    assert listed_object["Key"] == "two"
    assert resp["MaxKeys"] == 1
    assert resp["IsTruncated"] is False
    assert resp.get("Prefix") is None
    assert resp.get("Delimiter") is None
    assert "NextMarker" not in resp


@mock_aws
def test_list_keys_xml_escaped():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    key_name = "Q&A.txt"
    s3_client.put_object(Bucket="mybucket", Key=key_name, Body=b"is awesome")

    resp = s3_client.list_objects_v2(Bucket="mybucket", Prefix=key_name)

    assert resp["Contents"][0]["Key"] == key_name
    assert resp["KeyCount"] == 1
    assert resp["MaxKeys"] == 1000
    assert resp["Prefix"] == key_name
    assert resp["IsTruncated"] is False
    assert "Delimiter" not in resp
    assert "StartAfter" not in resp
    assert "NextContinuationToken" not in resp
    assert "Owner" not in resp["Contents"][0]


@mock_aws
def test_list_objects_v2_common_prefix_pagination():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    max_keys = 1
    keys = [f"test/{i}/{i}" for i in range(3)]
    for key in keys:
        s3_client.put_object(Bucket="mybucket", Key=key, Body=b"v")

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
        resp = s3_client.list_objects_v2(**args)
        if "CommonPrefixes" in resp:
            assert len(resp["CommonPrefixes"]) == max_keys
            prefixes.extend(i["Prefix"] for i in resp["CommonPrefixes"])

    assert prefixes == [k[: k.rindex("/") + 1] for k in keys]


@mock_aws
def test_list_objects_v2_common_invalid_continuation_token():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    max_keys = 1
    keys = [f"test/{i}/{i}" for i in range(3)]
    for key in keys:
        s3_client.put_object(Bucket="mybucket", Key=key, Body=b"v")

    args = {
        "Bucket": "mybucket",
        "Delimiter": "/",
        "Prefix": "test/",
        "MaxKeys": max_keys,
        "ContinuationToken": "",
    }

    with pytest.raises(botocore.exceptions.ClientError) as exc:
        s3_client.list_objects_v2(**args)
    assert exc.value.response["Error"]["Code"] == "InvalidArgument"
    assert exc.value.response["Error"]["Message"] == (
        "The continuation token provided is incorrect"
    )


@mock_aws
def test_list_objects_v2_truncated_response():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    s3_client.put_object(Bucket="mybucket", Key="one", Body=b"1")
    s3_client.put_object(Bucket="mybucket", Key="two", Body=b"22")
    s3_client.put_object(Bucket="mybucket", Key="three", Body=b"333")

    # First list
    resp = s3_client.list_objects_v2(Bucket="mybucket", MaxKeys=1)
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
    resp = s3_client.list_objects_v2(
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
    resp = s3_client.list_objects_v2(
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


@mock_aws
def test_list_objects_v2_truncated_response_start_after():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    s3_client.put_object(Bucket="mybucket", Key="one", Body=b"1")
    s3_client.put_object(Bucket="mybucket", Key="two", Body=b"22")
    s3_client.put_object(Bucket="mybucket", Key="three", Body=b"333")

    # First list
    resp = s3_client.list_objects_v2(Bucket="mybucket", MaxKeys=1, StartAfter="one")
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
    resp = s3_client.list_objects_v2(
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


@mock_aws
def test_list_objects_v2_fetch_owner():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    s3_client.put_object(Bucket="mybucket", Key="one", Body=b"11")

    resp = s3_client.list_objects_v2(Bucket="mybucket", FetchOwner=True)
    owner = resp["Contents"][0]["Owner"]

    assert "ID" in owner
    assert "DisplayName" in owner
    assert len(owner.keys()) == 2


@mock_aws
def test_list_objects_v2_truncate_combined_keys_and_folders():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    s3_client.put_object(Bucket="mybucket", Key="1/2", Body="")
    s3_client.put_object(Bucket="mybucket", Key="2", Body="")
    s3_client.put_object(Bucket="mybucket", Key="3/4", Body="")
    s3_client.put_object(Bucket="mybucket", Key="4", Body="")

    resp = s3_client.list_objects_v2(
        Bucket="mybucket", Prefix="", MaxKeys=2, Delimiter="/"
    )
    assert "Delimiter" in resp
    assert resp["IsTruncated"] is True
    assert resp["KeyCount"] == 2
    assert len(resp["Contents"]) == 1
    assert resp["Contents"][0]["Key"] == "2"
    assert len(resp["CommonPrefixes"]) == 1
    assert resp["CommonPrefixes"][0]["Prefix"] == "1/"

    last_tail = resp["Contents"][-1]["Key"]
    resp = s3_client.list_objects_v2(
        Bucket="mybucket", MaxKeys=2, Prefix="", Delimiter="/", StartAfter=last_tail
    )
    assert resp["KeyCount"] == 2
    assert resp["IsTruncated"] is False
    assert len(resp["Contents"]) == 1
    assert resp["Contents"][0]["Key"] == "4"
    assert len(resp["CommonPrefixes"]) == 1
    assert resp["CommonPrefixes"][0]["Prefix"] == "3/"


@mock_aws
def test_list_objects_v2__more_than_1000():
    # Verify that the default pagination size (1000) works
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Accessing backends directly")
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    # Uploading >1000 files using boto3 takes ages, so let's just use the backend directly
    backend = s3_backends[DEFAULT_ACCOUNT_ID]["global"]
    for i in range(1100):
        backend.put_object(bucket_name="mybucket", key_name=f"{i}", value=b"")

    # Page 1
    resp = s3_client.list_objects_v2(Bucket="mybucket", Delimiter="/")
    assert resp["KeyCount"] == 1000
    assert len(resp["Contents"]) == 1000
    assert resp["IsTruncated"] is True

    # Page2
    tail = resp["Contents"][-1]["Key"]
    resp = s3_client.list_objects_v2(Bucket="mybucket", Delimiter="/", StartAfter=tail)
    assert resp["KeyCount"] == 100
    assert len(resp["Contents"]) == 100
    assert resp["IsTruncated"] is False


@mock_aws
def test_list_objects_v2_checksum_algo():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")
    resp = s3_client.put_object(Bucket="mybucket", Key="0", Body="a")
    assert "ChecksumCRC32" not in resp
    assert "x-amz-sdk-checksum-algorithm" not in resp["ResponseMetadata"]["HTTPHeaders"]
    resp = s3_client.put_object(
        Bucket="mybucket", Key="1", Body="a", ChecksumAlgorithm="CRC32"
    )
    assert "ChecksumCRC32" in resp
    assert (
        resp["ResponseMetadata"]["HTTPHeaders"]["x-amz-sdk-checksum-algorithm"]
        == "CRC32"
    )
    resp = s3_client.put_object(
        Bucket="mybucket", Key="2", Body="b", ChecksumAlgorithm="SHA256"
    )
    assert "ChecksumSHA256" in resp
    assert (
        resp["ResponseMetadata"]["HTTPHeaders"]["x-amz-sdk-checksum-algorithm"]
        == "SHA256"
    )

    resp = s3_client.list_objects_v2(Bucket="mybucket")["Contents"]
    assert "ChecksumAlgorithm" not in resp[0]
    assert resp[1]["ChecksumAlgorithm"] == ["CRC32"]
    assert resp[2]["ChecksumAlgorithm"] == ["SHA256"]


@mock_aws
def test_bucket_create():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="blah")

    s3_resource.Object("blah", "hello.txt").put(Body="some text")

    assert (
        s3_resource.Object("blah", "hello.txt").get()["Body"].read().decode("utf-8")
        == "some text"
    )


@aws_verified
@pytest.mark.aws_verified
def test_bucket_create_force_us_east_1():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3_resource.create_bucket(
            Bucket="blah",
            CreateBucketConfiguration={"LocationConstraint": DEFAULT_REGION_NAME},
        )
    assert exc.value.response["Error"]["Code"] == "InvalidLocationConstraint"
    assert (
        exc.value.response["Error"]["Message"]
        == "The specified location-constraint is not valid"
    )


@mock_aws
def test_bucket_create_eu_central():
    s3_resource = boto3.resource("s3", region_name="eu-central-1")
    s3_resource.create_bucket(
        Bucket="blah", CreateBucketConfiguration={"LocationConstraint": "eu-central-1"}
    )

    s3_resource.Object("blah", "hello.txt").put(Body="some text")

    assert (
        s3_resource.Object("blah", "hello.txt").get()["Body"].read().decode("utf-8")
        == "some text"
    )


@mock_aws
def test_bucket_create_empty_bucket_configuration_should_return_malformed_xml_error():
    s3_resource = boto3.resource("s3", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        s3_resource.create_bucket(Bucket="whatever", CreateBucketConfiguration={})
    assert exc.value.response["Error"]["Code"] == "MalformedXML"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@s3_aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize("size", [10, 10000000])
def test_head_object(size, bucket_name=None):
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3_resource.Object(bucket_name, "hello.txt").put(Body="x" * size)

    resp = client.head_object(Bucket=bucket_name, Key="hello.txt")
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "content-range" not in resp["ResponseMetadata"]["HTTPHeaders"]
    assert resp["ContentLength"] == size
    assert resp["AcceptRanges"] == "bytes"

    resp = client.head_object(Bucket=bucket_name, Key="hello.txt", PartNumber=1)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 206
    assert (
        resp["ResponseMetadata"]["HTTPHeaders"]["content-range"]
        == f"bytes 0-{size-1}/{size}"
    )
    assert resp["ContentLength"] == size
    assert resp["AcceptRanges"] == "bytes"

    with pytest.raises(ClientError) as exc:
        client.head_object(Bucket=bucket_name, Key="hello.txt", PartNumber=2)
    err = exc.value.response["Error"]
    assert err["Code"] == "416"
    assert err["Message"] == "Requested Range Not Satisfiable"

    with pytest.raises(ClientError) as exc:
        client.head_object(Bucket=bucket_name, Key="hello_bad.txt")
    assert exc.value.response["Error"]["Code"] == "404"


@s3_aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize("size", [10, 10000000])
def test_get_object(size, bucket_name=None):
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3_resource.Object(bucket_name, "hello.txt").put(Body="x" * size)

    resp = client.get_object(Bucket=bucket_name, Key="hello.txt")
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "content-range" not in resp["ResponseMetadata"]["HTTPHeaders"]
    assert resp["ContentLength"] == size
    assert resp["AcceptRanges"] == "bytes"

    resp = client.get_object(Bucket=bucket_name, Key="hello.txt", PartNumber=1)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 206
    assert (
        resp["ResponseMetadata"]["HTTPHeaders"]["content-range"]
        == f"bytes 0-{size - 1}/{size}"
    )
    assert resp["ContentLength"] == size
    assert resp["AcceptRanges"] == "bytes"

    with pytest.raises(ClientError) as exc:
        client.head_object(Bucket=bucket_name, Key="hello.txt", PartNumber=2)
    err = exc.value.response["Error"]
    assert err["Code"] == "416"
    assert err["Message"] == "Requested Range Not Satisfiable"

    with pytest.raises(ClientError) as exc:
        s3_resource.Object(bucket_name, "hello2.txt").get()

    assert exc.value.response["Error"]["Code"] == "NoSuchKey"


@mock_aws
def test_s3_content_type():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    my_bucket = s3_resource.Bucket("my-cool-bucket")
    my_bucket.create()
    s3_path = "test_s3.py"
    s3_resource = boto3.resource("s3", verify=False)

    content_type = "text/python-x"
    s3_resource.Object(my_bucket.name, s3_path).put(
        ContentType=content_type, Body=b"some python code"
    )

    assert s3_resource.Object(my_bucket.name, s3_path).content_type == content_type


@mock_aws
def test_get_missing_object_with_part_number():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="blah")

    with pytest.raises(ClientError) as exc:
        s3_resource.Object("blah", "hello.txt").meta.client.head_object(
            Bucket="blah", Key="hello.txt", PartNumber=123
        )

    assert exc.value.response["Error"]["Code"] == "404"


@mock_aws
def test_head_object_with_versioning():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.create_bucket(Bucket="blah")
    bucket.Versioning().enable()

    old_content = "some text"
    new_content = "some new text"
    s3_resource.Object("blah", "hello.txt").put(Body=old_content)
    s3_resource.Object("blah", "hello.txt").put(Body=new_content)

    versions = list(s3_resource.Bucket("blah").object_versions.all())
    latest = list(filter(lambda item: item.is_latest, versions))[0]
    oldest = list(filter(lambda item: not item.is_latest, versions))[0]

    head_object = s3_resource.Object("blah", "hello.txt").meta.client.head_object(
        Bucket="blah", Key="hello.txt"
    )
    assert head_object["VersionId"] == latest.id
    assert head_object["ContentLength"] == len(new_content)

    old_head_object = s3_resource.Object("blah", "hello.txt").meta.client.head_object(
        Bucket="blah", Key="hello.txt", VersionId=oldest.id
    )
    assert old_head_object["VersionId"] == oldest.id
    assert old_head_object["ContentLength"] == len(old_content)

    assert old_head_object["VersionId"] != head_object["VersionId"]


@mock_aws
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


@s3_aws_verified
@pytest.mark.aws_verified
def test_delete_objects_for_specific_version_id(bucket_name=None):
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    enable_versioning(bucket_name, client)

    client.put_object(Bucket=bucket_name, Key="test1", Body=b"test1a")
    client.put_object(Bucket=bucket_name, Key="test1", Body=b"test1b")

    response = client.list_object_versions(Bucket=bucket_name, Prefix="test1")
    id_to_delete = [v["VersionId"] for v in response["Versions"] if v["IsLatest"]][0]

    response = client.delete_objects(
        Bucket=bucket_name,
        Delete={"Objects": [{"Key": "test1", "VersionId": id_to_delete}]},
    )
    assert response["Deleted"] == [{"Key": "test1", "VersionId": id_to_delete}]

    listed = client.list_objects_v2(Bucket=bucket_name)
    assert len(listed["Contents"]) == 1

    # DeleteObjects without specifying VersionId
    response = client.delete_objects(
        Bucket=bucket_name, Delete={"Objects": [{"Key": "test1"}]}
    )
    assert "Deleted" in response
    assert response["Deleted"][0]["DeleteMarker"] is True
    assert response["Deleted"][0]["DeleteMarkerVersionId"]
    assert response["Deleted"][0]["Key"] == "test1"


@mock_aws
def test_delete_versioned_bucket():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(Bucket="blah")
    client.put_bucket_versioning(
        Bucket="blah", VersioningConfiguration={"Status": "Enabled"}
    )

    resp = client.put_object(Bucket="blah", Key="test1", Body=b"test1")
    client.delete_object(Bucket="blah", Key="test1", VersionId=resp["VersionId"])

    client.delete_bucket(Bucket="blah")


@pytest.mark.aws_verified
@s3_aws_verified
def test_delete_versioned_bucket_returns_metadata(bucket_name=None):
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = resource.Bucket(bucket_name)
    versions = bucket.object_versions

    enable_versioning(bucket_name, client)

    client.put_object(Bucket=bucket_name, Key="test1", Body=b"test1")

    # We now have zero delete markers
    assert "DeleteMarkers" not in client.list_object_versions(Bucket=bucket_name)

    # Delete the object
    del_file = client.delete_object(Bucket=bucket_name, Key="test1")
    deleted_version_id = del_file["VersionId"]
    assert del_file["DeleteMarker"] is True
    assert deleted_version_id is not None

    # We now have one DeleteMarker
    assert len(client.list_object_versions(Bucket=bucket_name)["DeleteMarkers"]) == 1

    # list_object_versions returns the object itself, and a DeleteMarker
    # object.head() returns a 'x-amz-delete-marker' header
    # delete_marker_version.head() returns a 405
    for version in versions.filter(Prefix="test1"):
        if version.version_id == deleted_version_id:
            with pytest.raises(ClientError) as exc:
                version.head()
            err = exc.value.response
            assert err["Error"] == {"Code": "405", "Message": "Method Not Allowed"}
            assert err["ResponseMetadata"]["HTTPStatusCode"] == 405
            assert (
                err["ResponseMetadata"]["HTTPHeaders"]["x-amz-delete-marker"] == "true"
            )
            assert err["ResponseMetadata"]["HTTPHeaders"]["allow"] == "DELETE"
        else:
            assert version.head()["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Note that delete_marker.head() returns a regular 404
    # i.e., without specifying the versionId
    with pytest.raises(ClientError) as exc:
        client.head_object(Bucket=bucket_name, Key="test1")
    err = exc.value.response
    assert err["Error"] == {"Code": "404", "Message": "Not Found"}
    assert err["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert err["ResponseMetadata"]["HTTPHeaders"]["x-amz-delete-marker"] == "true"
    assert (
        err["ResponseMetadata"]["HTTPHeaders"]["x-amz-version-id"] == deleted_version_id
    )

    # Delete the same object gives a new version id
    del_mrk1 = client.delete_object(Bucket=bucket_name, Key="test1")
    assert del_mrk1["DeleteMarker"] is True
    assert del_mrk1["VersionId"] != del_file["VersionId"]

    # We now have two DeleteMarkers
    assert len(client.list_object_versions(Bucket=bucket_name)["DeleteMarkers"]) == 2

    # Delete the delete marker
    del_mrk2 = client.delete_object(
        Bucket=bucket_name, Key="test1", VersionId=del_mrk1["VersionId"]
    )
    assert del_mrk2["DeleteMarker"] is True
    assert del_mrk2["VersionId"] == del_mrk1["VersionId"]

    for version in versions.filter(Prefix="test1"):
        if version.version_id == deleted_version_id:
            with pytest.raises(ClientError) as exc:
                version.head()
            err = exc.value.response
            assert err["Error"] == {"Code": "405", "Message": "Method Not Allowed"}
            assert err["ResponseMetadata"]["HTTPStatusCode"] == 405
            assert (
                err["ResponseMetadata"]["HTTPHeaders"]["x-amz-delete-marker"] == "true"
            )
            assert err["ResponseMetadata"]["HTTPHeaders"]["allow"] == "DELETE"
        else:
            assert version.head()["ResponseMetadata"]["HTTPStatusCode"] == 200

    # We now have only one DeleteMarker
    assert len(client.list_object_versions(Bucket=bucket_name)["DeleteMarkers"]) == 1

    # Delete the actual file
    actual_version = client.list_object_versions(Bucket=bucket_name)["Versions"][0]
    del_mrk3 = client.delete_object(
        Bucket=bucket_name, Key="test1", VersionId=actual_version["VersionId"]
    )
    assert "DeleteMarker" not in del_mrk3
    assert del_mrk3["VersionId"] == actual_version["VersionId"]

    # We still have one DeleteMarker, but zero objects
    assert len(client.list_object_versions(Bucket=bucket_name)["DeleteMarkers"]) == 1
    assert "Versions" not in client.list_object_versions(Bucket=bucket_name)

    # Because we only have DeleteMarkers, we can not call `head()` on any of othem
    for version in versions.filter(Prefix="test1"):
        with pytest.raises(ClientError) as exc:
            version.head()
        err = exc.value.response
        assert err["Error"] == {"Code": "405", "Message": "Method Not Allowed"}

    # Delete the last marker
    del_mrk4 = client.delete_object(
        Bucket=bucket_name, Key="test1", VersionId=del_mrk2["VersionId"]
    )
    assert "DeleteMarker" not in del_mrk4
    assert del_mrk4["VersionId"] == del_mrk2["VersionId"]


@mock_aws
def test_get_object_if_modified_since_refresh():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    response = s3_client.get_object(Bucket=bucket_name, Key=key)

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=response["LastModified"],
        )
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_get_object_if_modified_since():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=utcnow() + datetime.timedelta(hours=1),
        )
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_get_object_if_unmodified_since():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(
            Bucket=bucket_name,
            Key=key,
            IfUnmodifiedSince=utcnow() - datetime.timedelta(hours=1),
        )
    err_value = err.value
    assert err_value.response["Error"]["Code"] == "PreconditionFailed"
    assert err_value.response["Error"]["Condition"] == "If-Unmodified-Since"


@mock_aws
def test_get_object_if_match():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(Bucket=bucket_name, Key=key, IfMatch='"hello"')
    err_value = err.value
    assert err_value.response["Error"]["Code"] == "PreconditionFailed"
    assert err_value.response["Error"]["Condition"] == "If-Match"


@mock_aws
def test_get_object_if_none_match():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    etag = s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")["ETag"]

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(Bucket=bucket_name, Key=key, IfNoneMatch=etag)
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_head_object_if_modified_since():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=utcnow() + datetime.timedelta(hours=1),
        )
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_head_object_if_modified_since_refresh():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    response = s3_client.head_object(Bucket=bucket_name, Key=key)

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=response["LastModified"],
        )
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_head_object_if_unmodified_since():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(
            Bucket=bucket_name,
            Key=key,
            IfUnmodifiedSince=utcnow() - datetime.timedelta(hours=1),
        )
    err_value = err.value
    assert err_value.response["Error"] == {
        "Code": "412",
        "Message": "Precondition Failed",
    }


@mock_aws
def test_head_object_if_match():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(Bucket=bucket_name, Key=key, IfMatch='"hello"')
    err_value = err.value
    assert err_value.response["Error"] == {
        "Code": "412",
        "Message": "Precondition Failed",
    }


@mock_aws
def test_head_object_if_none_match():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    etag = s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")["ETag"]

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(Bucket=bucket_name, Key=key, IfNoneMatch=etag)
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_put_bucket_cors():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    s3_client.create_bucket(Bucket=bucket_name)

    resp = s3_client.put_bucket_cors(
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

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration={
                "CORSRules": [
                    {"AllowedOrigins": ["*"], "AllowedMethods": ["NOTREAL", "POST"]}
                ]
            },
        )
    err_value = err.value
    assert err_value.response["Error"]["Code"] == "InvalidRequest"
    assert err_value.response["Error"]["Message"] == (
        "Found unsupported HTTP method in CORS config. " "Unsupported method is NOTREAL"
    )

    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_cors(
            Bucket=bucket_name, CORSConfiguration={"CORSRules": []}
        )
    err_value = err.value
    assert err_value.response["Error"]["Code"] == "MalformedXML"

    # And 101:
    many_rules = [{"AllowedOrigins": ["*"], "AllowedMethods": ["GET"]}] * 101
    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_cors(
            Bucket=bucket_name, CORSConfiguration={"CORSRules": many_rules}
        )
    err_value = err.value
    assert err_value.response["Error"]["Code"] == "MalformedXML"


@mock_aws
def test_get_bucket_cors():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    s3_client.create_bucket(Bucket=bucket_name)

    # Without CORS:
    with pytest.raises(ClientError) as err:
        s3_client.get_bucket_cors(Bucket=bucket_name)

    err_value = err.value
    assert err_value.response["Error"]["Code"] == "NoSuchCORSConfiguration"
    assert (
        err_value.response["Error"]["Message"]
        == "The CORS configuration does not exist"
    )

    s3_client.put_bucket_cors(
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

    resp = s3_client.get_bucket_cors(Bucket=bucket_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp["CORSRules"]) == 2


@pytest.mark.aws_verified
@s3_aws_verified
def test_delete_bucket_cors(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3_client.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration={
            "CORSRules": [{"AllowedOrigins": ["*"], "AllowedMethods": ["GET"]}]
        },
    )

    resp = s3_client.delete_bucket_cors(Bucket=bucket_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204

    # Verify deletion:
    with pytest.raises(ClientError) as err:
        s3_client.get_bucket_cors(Bucket=bucket_name)

    err_value = err.value
    assert err_value.response["Error"]["Code"] == "NoSuchCORSConfiguration"
    assert (
        err_value.response["Error"]["Message"]
        == "The CORS configuration does not exist"
    )


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("us-west-2", "aws"), ("cn-north-1", "aws-cn")]
)
def test_put_bucket_notification(region, partition):
    s3_client = boto3.client("s3", region_name=region)
    s3_client.create_bucket(
        Bucket="bucket", CreateBucketConfiguration={"LocationConstraint": region}
    )

    # With no configuration:
    result = s3_client.get_bucket_notification(Bucket="bucket")
    assert not result.get("TopicConfigurations")
    assert not result.get("QueueConfigurations")
    assert not result.get("LambdaFunctionConfigurations")

    # Place proper topic configuration:
    s3_client.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "TopicConfigurations": [
                {
                    "TopicArn": f"arn:{partition}:sns:{region}:012345678910:mytopic",
                    "Events": ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
                },
                {
                    "TopicArn": f"arn:{partition}:sns:{region}:012345678910:myothertopic",
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
    result = s3_client.get_bucket_notification_configuration(Bucket="bucket")
    assert len(result["TopicConfigurations"]) == 2
    assert not result.get("QueueConfigurations")
    assert not result.get("LambdaFunctionConfigurations")
    assert (
        result["TopicConfigurations"][0]["TopicArn"]
        == f"arn:{partition}:sns:{region}:012345678910:mytopic"
    )
    assert (
        result["TopicConfigurations"][1]["TopicArn"]
        == f"arn:{partition}:sns:{region}:012345678910:myothertopic"
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
    s3_client.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "QueueConfigurations": [
                {
                    "Id": "SomeID",
                    "QueueArn": f"arn:{partition}:sqs:{region}:012345678910:myQueue",
                    "Events": ["s3:ObjectCreated:*"],
                    "Filter": {
                        "Key": {"FilterRules": [{"Name": "prefix", "Value": "images/"}]}
                    },
                }
            ]
        },
    )
    result = s3_client.get_bucket_notification_configuration(Bucket="bucket")
    assert len(result["QueueConfigurations"]) == 1
    assert not result.get("TopicConfigurations")
    assert not result.get("LambdaFunctionConfigurations")
    assert result["QueueConfigurations"][0]["Id"] == "SomeID"
    assert (
        result["QueueConfigurations"][0]["QueueArn"]
        == f"arn:{partition}:sqs:{region}:012345678910:myQueue"
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
    s3_client.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [
                {
                    "LambdaFunctionArn": f"arn:{partition}:lambda:{region}:012345678910:function:lambda",
                    "Events": ["s3:ObjectCreated:*"],
                    "Filter": {
                        "Key": {"FilterRules": [{"Name": "prefix", "Value": "images/"}]}
                    },
                }
            ]
        },
    )
    result = s3_client.get_bucket_notification_configuration(Bucket="bucket")
    assert len(result["LambdaFunctionConfigurations"]) == 1
    assert not result.get("TopicConfigurations")
    assert not result.get("QueueConfigurations")
    assert result["LambdaFunctionConfigurations"][0]["Id"]
    assert (
        result["LambdaFunctionConfigurations"][0]["LambdaFunctionArn"]
        == f"arn:{partition}:lambda:{region}:012345678910:function:lambda"
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
    s3_client.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "TopicConfigurations": [
                {
                    "TopicArn": f"arn:{partition}:sns:{region}:012345678910:mytopic",
                    "Events": ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
                }
            ],
            "LambdaFunctionConfigurations": [
                {
                    "LambdaFunctionArn": f"arn:{partition}:lambda:{region}:012345678910:function:lambda",
                    "Events": ["s3:ObjectCreated:*"],
                }
            ],
            "QueueConfigurations": [
                {
                    "QueueArn": f"arn:{partition}:sqs:{region}:012345678910:myQueue",
                    "Events": ["s3:ObjectCreated:*"],
                }
            ],
        },
    )
    result = s3_client.get_bucket_notification_configuration(Bucket="bucket")
    assert len(result["LambdaFunctionConfigurations"]) == 1
    assert len(result["TopicConfigurations"]) == 1
    assert len(result["QueueConfigurations"]) == 1

    # And clear it out:
    s3_client.put_bucket_notification_configuration(
        Bucket="bucket", NotificationConfiguration={}
    )
    result = s3_client.get_bucket_notification_configuration(Bucket="bucket")
    assert not result.get("TopicConfigurations")
    assert not result.get("QueueConfigurations")
    assert not result.get("LambdaFunctionConfigurations")


@mock_aws
def test_put_bucket_notification_errors():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="bucket")

    # With incorrect ARNs:
    for tech in ["Queue", "Topic", "LambdaFunction"]:
        with pytest.raises(ClientError) as err:
            s3_client.put_bucket_notification_configuration(
                Bucket="bucket",
                NotificationConfiguration={
                    f"{tech}Configurations": [
                        {
                            f"{tech}Arn": "arn:aws:{}:us-east-1:012345678910:lksajdfkldskfj",
                            "Events": ["s3:ObjectCreated:*"],
                        }
                    ]
                },
            )

        assert err.value.response["Error"]["Code"] == "InvalidArgument"
        assert err.value.response["Error"]["Message"] == "The ARN is not well formed"

    # Region not the same as the bucket:
    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_notification_configuration(
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
    assert err.value.response["Error"]["Message"] == (
        "The notification destination service region is not valid for "
        "the bucket location constraint"
    )

    # Invalid event name:
    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_notification_configuration(
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
        == "The event 'notarealeventname' is not supported for notifications. Supported events are as follows: ['s3:IntelligentTiering', 's3:LifecycleExpiration:*', 's3:LifecycleExpiration:Delete', 's3:LifecycleExpiration:DeleteMarkerCreated', 's3:LifecycleTransition', 's3:ObjectAcl:Put', 's3:ObjectCreated:*', 's3:ObjectCreated:CompleteMultipartUpload', 's3:ObjectCreated:Copy', 's3:ObjectCreated:Post', 's3:ObjectCreated:Put', 's3:ObjectRemoved:*', 's3:ObjectRemoved:Delete', 's3:ObjectRemoved:DeleteMarkerCreated', 's3:ObjectRestore:*', 's3:ObjectRestore:Completed', 's3:ObjectRestore:Delete', 's3:ObjectRestore:Post', 's3:ObjectTagging:*', 's3:ObjectTagging:Delete', 's3:ObjectTagging:Put', 's3:ReducedRedundancyLostObject', 's3:Replication:*', 's3:Replication:OperationFailedReplication', 's3:Replication:OperationMissedThreshold', 's3:Replication:OperationNotTracked', 's3:Replication:OperationReplicatedAfterThreshold']"
    )


@mock_aws
def test_delete_markers():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions-and-unicode-ó"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (b"v1", b"v2")
    for body in items:
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=body)

    s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": key}]})

    with pytest.raises(ClientError) as exc:
        s3_client.get_object(Bucket=bucket_name, Key=key)
    assert exc.value.response["Error"]["Code"] == "NoSuchKey"

    response = s3_client.list_object_versions(Bucket=bucket_name)
    assert len(response["Versions"]) == 2
    assert len(response["DeleteMarkers"]) == 1

    s3_client.delete_object(
        Bucket=bucket_name, Key=key, VersionId=response["DeleteMarkers"][0]["VersionId"]
    )
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    assert response["Body"].read() == items[-1]

    response = s3_client.list_object_versions(Bucket=bucket_name)
    assert len(response["Versions"]) == 2

    # We've asserted there is only 2 records so one is newest, one is oldest
    latest = list(filter(lambda item: item["IsLatest"], response["Versions"]))[0]
    oldest = list(filter(lambda item: not item["IsLatest"], response["Versions"]))[0]
    # Double check ordering of version ID's
    assert latest["VersionId"] != oldest["VersionId"]

    # Double check the name is still unicode
    assert latest["Key"] == "key-with-versions-and-unicode-ó"
    assert oldest["Key"] == "key-with-versions-and-unicode-ó"


@mock_aws
def test_multiple_delete_markers():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions-and-unicode-ó"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (b"v1", b"v2")
    for body in items:
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=body)

    # Delete the object twice to add multiple delete markers
    s3_client.delete_object(Bucket=bucket_name, Key=key)
    s3_client.delete_object(Bucket=bucket_name, Key=key)

    response = s3_client.list_object_versions(Bucket=bucket_name)
    assert len(response["DeleteMarkers"]) == 2

    with pytest.raises(ClientError) as exc:
        s3_client.get_object(Bucket=bucket_name, Key=key)
        assert exc.response["Error"]["Code"] == "404"

    # Remove both delete markers to restore the object
    s3_client.delete_object(
        Bucket=bucket_name, Key=key, VersionId=response["DeleteMarkers"][0]["VersionId"]
    )
    s3_client.delete_object(
        Bucket=bucket_name, Key=key, VersionId=response["DeleteMarkers"][1]["VersionId"]
    )

    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    assert response["Body"].read() == items[-1]
    response = s3_client.list_object_versions(Bucket=bucket_name)
    assert len(response["Versions"]) == 2

    # We've asserted there is only 2 records so one is newest, one is oldest
    latest = list(filter(lambda item: item["IsLatest"], response["Versions"]))[0]
    oldest = list(filter(lambda item: not item["IsLatest"], response["Versions"]))[0]

    # Double check ordering of version ID's
    assert latest["VersionId"] != oldest["VersionId"]

    # Double check the name is still unicode
    assert latest["Key"] == "key-with-versions-and-unicode-ó"
    assert oldest["Key"] == "key-with-versions-and-unicode-ó"


@mock_aws
def test_get_stream_gzipped():
    payload = b"this is some stuff here"

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="moto-tests")
    buffer_ = BytesIO()
    with GzipFile(fileobj=buffer_, mode="w") as fhandle:
        fhandle.write(payload)
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


@mock_aws
def test_bucket_name_too_long():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3_client.create_bucket(Bucket="x" * 64)
    assert exc.value.response["Error"]["Code"] == "InvalidBucketName"


@mock_aws
def test_bucket_name_too_short():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3_client.create_bucket(Bucket="x" * 2)
    assert exc.value.response["Error"]["Code"] == "InvalidBucketName"


@mock_aws
def test_accelerated_none_when_unspecified():
    bucket_name = "some_bucket"
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)
    resp = s3_client.get_bucket_accelerate_configuration(Bucket=bucket_name)
    assert "Status" not in resp


@mock_aws
def test_can_enable_bucket_acceleration():
    bucket_name = "some_bucket"
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)
    resp = s3_client.put_bucket_accelerate_configuration(
        Bucket=bucket_name, AccelerateConfiguration={"Status": "Enabled"}
    )
    assert len(resp.keys()) == 1  # Response contains nothing (only HTTP headers)
    resp = s3_client.get_bucket_accelerate_configuration(Bucket=bucket_name)
    assert "Status" in resp
    assert resp["Status"] == "Enabled"


@mock_aws
def test_can_suspend_bucket_acceleration():
    bucket_name = "some_bucket"
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)
    resp = s3_client.put_bucket_accelerate_configuration(
        Bucket=bucket_name, AccelerateConfiguration={"Status": "Enabled"}
    )
    resp = s3_client.put_bucket_accelerate_configuration(
        Bucket=bucket_name, AccelerateConfiguration={"Status": "Suspended"}
    )
    assert len(resp.keys()) == 1  # Response contains nothing (only HTTP headers)
    resp = s3_client.get_bucket_accelerate_configuration(Bucket=bucket_name)
    assert "Status" in resp
    assert resp["Status"] == "Suspended"


@mock_aws
def test_suspending_acceleration_on_not_configured_bucket_does_nothing():
    bucket_name = "some_bucket"
    s3_client = boto3.client("s3", DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)
    resp = s3_client.put_bucket_accelerate_configuration(
        Bucket=bucket_name, AccelerateConfiguration={"Status": "Suspended"}
    )
    assert len(resp.keys()) == 1  # Response contains nothing (only HTTP headers)
    resp = s3_client.get_bucket_accelerate_configuration(Bucket=bucket_name)
    assert "Status" not in resp


@mock_aws
def test_accelerate_configuration_status_validation():
    bucket_name = "some_bucket"
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)
    with pytest.raises(ClientError) as exc:
        s3_client.put_bucket_accelerate_configuration(
            Bucket=bucket_name, AccelerateConfiguration={"Status": "bad_status"}
        )
    assert exc.value.response["Error"]["Code"] == "MalformedXML"


@mock_aws
def test_accelerate_configuration_is_not_supported_when_bucket_name_has_dots():
    bucket_name = "some.bucket.with.dots"
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)
    with pytest.raises(ClientError) as exc:
        s3_client.put_bucket_accelerate_configuration(
            Bucket=bucket_name, AccelerateConfiguration={"Status": "Enabled"}
        )
    assert exc.value.response["Error"]["Code"] == "InvalidRequest"


def store_and_read_back_a_key(key):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    body = b"Some body"

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=body)

    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    assert response["Body"].read() == body


@mock_aws
def test_paths_with_leading_slashes_work():
    store_and_read_back_a_key("/a-key")


@mock_aws
def test_root_dir_with_empty_name_works():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Does not work in server mode due to error in Workzeug")
    store_and_read_back_a_key("/")


@pytest.mark.parametrize("bucket_name", ["mybucket", "my.bucket"])
@mock_aws
def test_leading_slashes_not_removed(bucket_name):
    """Make sure that leading slashes are not removed internally."""
    if settings.is_test_proxy_mode():
        raise SkipTest("Doesn't quite work right with the Proxy")
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)

    uploaded_key = "/key"
    invalid_key_1 = "key"
    invalid_key_2 = "//key"

    s3_client.put_object(Bucket=bucket_name, Key=uploaded_key, Body=b"Some body")

    with pytest.raises(ClientError) as exc:
        s3_client.get_object(Bucket=bucket_name, Key=invalid_key_1)
    assert exc.value.response["Error"]["Code"] == "NoSuchKey"

    with pytest.raises(ClientError) as exc:
        s3_client.get_object(Bucket=bucket_name, Key=invalid_key_2)
    assert exc.value.response["Error"]["Code"] == "NoSuchKey"


@pytest.mark.parametrize(
    "key", ["foo/bar/baz", "foo", "foo/run_dt%3D2019-01-01%252012%253A30%253A00"]
)
@mock_aws
def test_delete_objects_with_url_encoded_key(key):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    body = b"Some body"

    s3_client.create_bucket(Bucket=bucket_name)

    def put_object():
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=body)

    def assert_deleted():
        with pytest.raises(ClientError) as exc:
            s3_client.get_object(Bucket=bucket_name, Key=key)

        assert exc.value.response["Error"]["Code"] == "NoSuchKey"

    put_object()
    s3_client.delete_object(Bucket=bucket_name, Key=key)
    assert_deleted()

    put_object()
    s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": key}]})
    assert_deleted()


@mock_aws
def test_delete_objects_unknown_key():
    bucket_name = "test-moto-issue-1581"
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket=bucket_name)
    client.put_object(Bucket=bucket_name, Key="file1", Body="body")

    objs = client.delete_objects(
        Bucket=bucket_name, Delete={"Objects": [{"Key": "file1"}, {"Key": "file2"}]}
    )
    assert len(objs["Deleted"]) == 2
    assert {"Key": "file1"} in objs["Deleted"]
    assert {"Key": "file2"} in objs["Deleted"]
    client.delete_bucket(Bucket=bucket_name)


@mock_aws
def test_public_access_block():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="mybucket")

    # Try to get the public access block (should not exist by default)
    with pytest.raises(ClientError) as exc:
        client.get_public_access_block(Bucket="mybucket")

    assert exc.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"
    assert (
        exc.value.response["Error"]["Message"]
        == "The public access block configuration was not found"
    )
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404

    # Put a public block in place:
    test_map = {
        "BlockPublicAcls": False,
        "IgnorePublicAcls": False,
        "BlockPublicPolicy": False,
        "RestrictPublicBuckets": False,
    }

    for field in test_map:
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
    with pytest.raises(ClientError) as exc:
        client.put_public_access_block(
            Bucket="mybucket", PublicAccessBlockConfiguration={}
        )

    assert exc.value.response["Error"]["Code"] == "InvalidRequest"
    assert (
        exc.value.response["Error"]["Message"]
        == "Must specify at least one configuration."
    )
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

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

    with pytest.raises(ClientError) as exc:
        client.get_public_access_block(Bucket="mybucket")
    assert exc.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"


@mock_aws
def test_creating_presigned_post():
    bucket = "presigned-test"
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=bucket)
    success_url = "http://localhost/completed"
    fdata = b"test data\n"
    file_uid = uuid.uuid4()
    conditions = [
        {"Content-Type": "text/plain"},
        {"x-amz-server-side-encryption": "AES256"},
        {"success_action_redirect": success_url},
    ]
    conditions.append(["content-length-range", 1, 30])

    real_key = f"{file_uid}.txt"
    data = s3_client.generate_presigned_post(
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
    kwargs = {
        "data": data["fields"],
        "files": {"file": fdata},
        "allow_redirects": False,
    }
    if settings.is_test_proxy_mode():
        add_proxy_details(kwargs)
    resp = requests.post(data["url"], **kwargs)
    assert resp.status_code == 303
    redirect = resp.headers["Location"]
    assert redirect.startswith(success_url)
    parts = urlparse(redirect)
    args = parse_qs(parts.query)
    assert args["key"][0] == real_key
    assert args["bucket"][0] == bucket

    assert s3_client.get_object(Bucket=bucket, Key=real_key)["Body"].read() == fdata


@mock_aws
def test_presigned_put_url_with_approved_headers():
    bucket = str(uuid.uuid4())
    key = "file.txt"
    content = b"filecontent"
    expected_contenttype = "app/sth"
    conn = boto3.resource("s3", region_name="us-east-1")
    conn.create_bucket(Bucket=bucket)
    s3_client = boto3.client("s3", region_name="us-east-1")

    # Create a pre-signed url with some metadata.
    url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": expected_contenttype},
    )

    # Verify S3 throws an error when the header is not provided
    kwargs = {"data": content}
    if settings.is_test_proxy_mode():
        add_proxy_details(kwargs)
    response = requests.put(url, **kwargs)
    assert response.status_code == 403
    assert "<Code>SignatureDoesNotMatch</Code>" in str(response.content)
    assert (
        "<Message>The request signature we calculated does not match the "
        "signature you provided. Check your key and signing method.</Message>"
    ) in str(response.content)

    # Verify S3 throws an error when the header has the wrong value
    kwargs = {"data": content, "headers": {"Content-Type": "application/unknown"}}
    if settings.is_test_proxy_mode():
        add_proxy_details(kwargs)
    response = requests.put(url, **kwargs)
    assert response.status_code == 403
    assert "<Code>SignatureDoesNotMatch</Code>" in str(response.content)
    assert (
        "<Message>The request signature we calculated does not match the "
        "signature you provided. Check your key and signing method.</Message>"
    ) in str(response.content)

    # Verify S3 uploads correctly when providing the meta data
    kwargs = {"data": content, "headers": {"Content-Type": expected_contenttype}}
    if settings.is_test_proxy_mode():
        add_proxy_details(kwargs)
    response = requests.put(url, **kwargs)
    assert response.status_code == 200

    # Assert the object exists
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    assert obj["ContentType"] == expected_contenttype
    assert obj["ContentLength"] == 11
    assert obj["Body"].read() == content
    assert obj["Metadata"] == {}

    s3_client.delete_object(Bucket=bucket, Key=key)
    s3_client.delete_bucket(Bucket=bucket)


@mock_aws
def test_presigned_put_url_with_custom_headers():
    bucket = str(uuid.uuid4())
    key = "file.txt"
    content = b"filecontent"
    conn = boto3.resource("s3", region_name="us-east-1")
    conn.create_bucket(Bucket=bucket)
    s3_client = boto3.client("s3", region_name="us-east-1")

    # Create a pre-signed url with some metadata.
    url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": bucket, "Key": key, "Metadata": {"venue": "123"}},
    )

    # Verify S3 uploads correctly when providing the meta data
    kwargs = {"data": content}
    if settings.is_test_proxy_mode():
        add_proxy_details(kwargs)
    response = requests.put(url, **kwargs)
    assert response.status_code == 200

    # Assert the object exists
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    assert obj["ContentLength"] == 11
    assert obj["Body"].read() == content
    assert obj["Metadata"] == {"venue": "123"}

    s3_client.delete_object(Bucket=bucket, Key=key)
    s3_client.delete_bucket(Bucket=bucket)


@mock_aws
def test_request_partial_content_should_contain_content_length():
    bucket = "bucket"
    object_key = "key"
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket=bucket)
    s3_resource.Object(bucket, object_key).put(Body="some text")

    file = s3_resource.Object(bucket, object_key)
    response = file.get(Range="bytes=0-1024")
    assert response["ContentLength"] == 9


@mock_aws
def test_request_partial_content_should_contain_actual_content_length():
    bucket = "bucket"
    object_key = "key"
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket=bucket)
    s3_resource.Object(bucket, object_key).put(Body="some text")

    file = s3_resource.Object(bucket, object_key)
    requested_range = "bytes=1024-"
    try:
        file.get(Range=requested_range)
    except botocore.client.ClientError as exc:
        assert exc.response["Error"]["Code"] == "InvalidRange"
        assert (
            exc.response["Error"]["Message"] == "The requested range is not satisfiable"
        )
        assert exc.response["Error"]["ActualObjectSize"] == "9"
        assert exc.response["Error"]["RangeRequested"] == requested_range


@mock_aws
def test_get_unknown_version_should_throw_specific_error():
    bucket_name = "my_bucket"
    object_key = "hello.txt"
    s3_resource = boto3.resource("s3", region_name="us-east-1")
    client = boto3.client("s3", region_name="us-east-1")
    bucket = s3_resource.create_bucket(Bucket=bucket_name)
    bucket.Versioning().enable()
    content = "some text"
    s3_resource.Object(bucket_name, object_key).put(Body=content)

    with pytest.raises(ClientError) as exc:
        client.get_object(Bucket=bucket_name, Key=object_key, VersionId="unknown")
    assert exc.value.response["Error"]["Code"] == "NoSuchVersion"
    assert exc.value.response["Error"]["Message"] == (
        "The specified version does not exist."
    )


@mock_aws
def test_request_partial_content_without_specifying_range_should_return_full_object():
    bucket = "bucket"
    object_key = "key"
    s3_resource = boto3.resource("s3", region_name="us-east-1")
    s3_resource.create_bucket(Bucket=bucket)
    s3_resource.Object(bucket, object_key).put(Body="some text that goes a long way")

    file = s3_resource.Object(bucket, object_key)
    response = file.get(Range="")
    assert response["ContentLength"] == 30


@mock_aws
def test_object_headers():
    bucket = "my-bucket"
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket)

    res = s3_client.put_object(
        Bucket=bucket,
        Body=b"test",
        Key="file.txt",
        ServerSideEncryption="aws:kms",
        SSEKMSKeyId="test",
        BucketKeyEnabled=True,
    )
    assert "ETag" in res
    assert "ServerSideEncryption" in res
    assert "SSEKMSKeyId" in res
    assert "BucketKeyEnabled" in res

    res = s3_client.get_object(Bucket=bucket, Key="file.txt")
    assert "ETag" in res
    assert "ServerSideEncryption" in res
    assert "SSEKMSKeyId" in res
    assert "BucketKeyEnabled" in res


if settings.TEST_SERVER_MODE:

    @mock_aws
    def test_upload_data_without_content_type():
        bucket = "mybucket"
        s3_client = boto3.client("s3")
        s3_client.create_bucket(Bucket=bucket)
        data_input = b"some data 123 321"
        req = requests.put("http://localhost:5000/mybucket/test.txt", data=data_input)
        assert req.status_code == 200

        res = s3_client.get_object(Bucket=bucket, Key="test.txt")
        data = res["Body"].read()
        assert data == data_input


@mock_aws
@pytest.mark.parametrize(
    "prefix", ["file", "file+else", "file&another", "file another"]
)
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
    assert len(versions["Versions"]) == 3
    assert versions["Prefix"] == prefix


@mock_aws
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
    assert err["Code"] == "BucketAlreadyOwnedByYou"
    assert err["Message"] == (
        "Your previous request to create the named bucket succeeded and you already own it."
    )
    assert err["BucketName"] == bucket_name

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
    assert err["Code"] == "BucketAlreadyOwnedByYou"
    assert err["Message"] == (
        "Your previous request to create the named bucket succeeded and you already own it."
    )
    assert err["BucketName"] == bucket_name

    # Recreating the bucket in the default region should fail
    diff_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as ex:
        diff_client.create_bucket(Bucket=bucket_name)
    err = ex.value.response["Error"]
    assert err["Code"] == "BucketAlreadyOwnedByYou"
    assert err["Message"] == (
        "Your previous request to create the named bucket succeeded and you already own it."
    )
    assert err["BucketName"] == bucket_name

    # Recreating the bucket in a third region should fail
    diff_client = boto3.client("s3", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        diff_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"},
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "BucketAlreadyOwnedByYou"
    assert err["Message"] == (
        "Your previous request to create the named bucket succeeded and you already own it."
    )
    assert err["BucketName"] == bucket_name


@mock_aws
def test_delete_objects_with_empty_keyname():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "testbucket-4077"
    bucket = resource.create_bucket(Bucket=bucket_name)
    key_name = " "
    bucket.put_object(Key=key_name, Body=b"")
    assert len(client.list_objects(Bucket=bucket_name)["Contents"]) == 1

    bucket.delete_objects(Delete={"Objects": [{"Key": key_name}]})
    assert "Contents" not in client.list_objects(Bucket=bucket_name)

    bucket.put_object(Key=key_name, Body=b"")

    client.delete_object(Bucket=bucket_name, Key=key_name)
    assert "Contents" not in client.list_objects(Bucket=bucket_name)


@pytest.mark.aws_verified
@s3_aws_verified
def test_delete_objects_percent_encoded(bucket_name=None):
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    object_key_1 = "a%2Fb"
    object_key_2 = "a/%F0%9F%98%80"
    client.put_object(Bucket=bucket_name, Key=object_key_1, Body="percent encoding")
    client.put_object(
        Bucket=bucket_name, Key=object_key_2, Body="percent encoded emoji"
    )
    list_objs = client.list_objects(Bucket=bucket_name)
    assert len(list_objs["Contents"]) == 2
    keys = [o["Key"] for o in list_objs["Contents"]]
    assert object_key_1 in keys
    assert object_key_2 in keys

    delete_objects = client.delete_objects(
        Bucket=bucket_name,
        Delete={
            "Objects": [
                {"Key": object_key_1},
                {"Key": object_key_2},
            ],
        },
    )
    assert len(delete_objects["Deleted"]) == 2
    deleted_keys = [o for o in delete_objects["Deleted"]]
    assert {"Key": object_key_1} in deleted_keys
    assert {"Key": object_key_2} in deleted_keys
    assert "Contents" not in client.list_objects(Bucket=bucket_name)


@mock_aws
def test_head_object_should_return_default_content_type():
    s3_resource = boto3.resource("s3", region_name="us-east-1")
    s3_resource.create_bucket(Bucket="testbucket")
    s3_resource.Bucket("testbucket").upload_fileobj(
        BytesIO(b"foobar"), Key="testobject"
    )
    s3_client = boto3.client("s3", region_name="us-east-1")
    resp = s3_client.head_object(Bucket="testbucket", Key="testobject")

    assert resp["ContentType"] == "binary/octet-stream"
    assert resp["ResponseMetadata"]["HTTPHeaders"]["content-type"] == (
        "binary/octet-stream"
    )

    assert (
        s3_resource.Object("testbucket", "testobject").content_type
        == "binary/octet-stream"
    )


@mock_aws
def test_request_partial_content_should_contain_all_metadata():
    # github.com/getmoto/moto/issues/4203
    bucket = "bucket"
    object_key = "key"
    body = "some text"
    query_range = "0-3"

    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket=bucket)
    obj = boto3.resource("s3").Object(bucket, object_key)
    obj.put(Body=body)

    response = obj.get(Range=f"bytes={query_range}")

    assert response["ETag"] == obj.e_tag
    assert response["LastModified"] == obj.last_modified
    assert response["ContentLength"] == 4
    assert response["ContentRange"] == f"bytes {query_range}/{len(body)}"


@mock_aws
def test_head_versioned_key_in_not_versioned_bucket():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="simple-bucked")

    with pytest.raises(ClientError) as ex:
        client.head_object(
            Bucket="simple-bucked", Key="file.txt", VersionId="noVersion"
        )

    response = ex.value.response
    assert response["Error"]["Code"] == "400"


@s3_aws_verified
@pytest.mark.aws_verified
def test_head_object_with_range_header(bucket_name=None):
    # HeadObject returns only the metadata for an object.
    # If the Range is satisfiable, only the ContentLength is affected in the response.
    # If the Range is not satisfiable, S3 returns a 416 - Requested Range Not Satisfiable error.
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.put_object(Bucket=bucket_name, Key="f1", Body="f1")

    for valid in ["0-9", "0-"]:
        resp = client.head_object(Bucket=bucket_name, Key="f1", Range=f"bytes={valid}")
        headers = resp["ResponseMetadata"]["HTTPHeaders"]
        assert headers["content-range"] == "bytes 0-1/2"
        assert headers["content-length"] == "2"

    for valid in ["-1", "1-1"]:
        resp = client.head_object(Bucket=bucket_name, Key="f1", Range=f"bytes={valid}")
        headers = resp["ResponseMetadata"]["HTTPHeaders"]
        assert headers["content-range"] == "bytes 1-1/2"
        assert headers["content-length"] == "1"

    for valid in ["1-0"]:
        resp = client.head_object(Bucket=bucket_name, Key="f1", Range=f"bytes={valid}")
        headers = resp["ResponseMetadata"]["HTTPHeaders"]
        assert "content-range" not in headers
        assert headers["content-length"] == "2"

    for invalid in ["5-9", "100-"]:
        with pytest.raises(ClientError) as exc:
            client.head_object(Bucket=bucket_name, Key="f1", Range=f"bytes={invalid}")
        err = exc.value.response["Error"]
        assert err["Code"] == "416"
        assert "Range Not Satisfiable" in err["Message"]


@mock_aws
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


@mock_aws
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


def add_proxy_details(kwargs):
    kwargs["proxies"] = {"https": "http://localhost:5005"}
    kwargs["verify"] = moto_proxy.__file__.replace("__init__.py", "ca.crt")


def enable_versioning(bucket_name, s3_client):
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    # Versioning is not active immediately, so wait until we have confirmation the change has gone through
    resp = {}
    while resp.get("Status") != "Enabled":
        sleep(0.1)
        resp = s3_client.get_bucket_versioning(Bucket=bucket_name)
