import boto3
from botocore.client import ClientError

from moto.s3.responses import DEFAULT_REGION_NAME
import pytest

import sure  # noqa # pylint: disable=unused-import

from moto import mock_s3, mock_kms


@pytest.mark.parametrize(
    "key_name",
    [
        "the-key",
        "the-unicode-💩-key",
        "key-with?question-mark",
        "key-with%2Fembedded%2Furl%2Fencoding",
    ],
)
@mock_s3
def test_copy_key_boto3(key_name):
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    key = s3.Object("foobar", key_name)
    key.put(Body=b"some value")

    key2 = s3.Object("foobar", "new-key")
    key2.copy_from(CopySource="foobar/{}".format(key_name))

    resp = client.get_object(Bucket="foobar", Key=key_name)
    resp["Body"].read().should.equal(b"some value")
    resp = client.get_object(Bucket="foobar", Key="new-key")
    resp["Body"].read().should.equal(b"some value")


@mock_s3
def test_copy_key_with_version_boto3():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")
    client.put_bucket_versioning(
        Bucket="foobar", VersioningConfiguration={"Status": "Enabled"}
    )

    key = s3.Object("foobar", "the-key")
    key.put(Body=b"some value")
    key.put(Body=b"another value")

    all_versions = client.list_object_versions(Bucket="foobar", Prefix="the-key")[
        "Versions"
    ]
    old_version = [v for v in all_versions if not v["IsLatest"]][0]

    key2 = s3.Object("foobar", "new-key")
    key2.copy_from(
        CopySource="foobar/the-key?versionId={}".format(old_version["VersionId"])
    )

    resp = client.get_object(Bucket="foobar", Key="the-key")
    resp["Body"].read().should.equal(b"another value")
    resp = client.get_object(Bucket="foobar", Key="new-key")
    resp["Body"].read().should.equal(b"some value")


@mock_s3
def test_copy_object_with_bucketkeyenabled_returns_the_value():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "test-copy-object-with-bucketkeyenabled"
    s3.create_bucket(Bucket=bucket_name)

    key = s3.Object(bucket_name, "the-key")
    key.put(Body=b"some value")

    key2 = s3.Object(bucket_name, "new-key")
    key2.copy_from(
        CopySource=f"{bucket_name}/the-key",
        BucketKeyEnabled=True,
        ServerSideEncryption="aws:kms",
    )

    resp = client.get_object(Bucket=bucket_name, Key="the-key")
    src_headers = resp["ResponseMetadata"]["HTTPHeaders"]
    src_headers.shouldnt.have.key("x-amz-server-side-encryption")
    src_headers.shouldnt.have.key("x-amz-server-side-encryption-aws-kms-key-id")
    src_headers.shouldnt.have.key("x-amz-server-side-encryption-bucket-key-enabled")

    resp = client.get_object(Bucket=bucket_name, Key="new-key")
    target_headers = resp["ResponseMetadata"]["HTTPHeaders"]
    target_headers.should.have.key("x-amz-server-side-encryption")
    # AWS will also return the KMS default key id - not yet implemented
    # target_headers.should.have.key("x-amz-server-side-encryption-aws-kms-key-id")
    # This field is only returned if encryption is set to 'aws:kms'
    target_headers.should.have.key("x-amz-server-side-encryption-bucket-key-enabled")
    str(
        target_headers["x-amz-server-side-encryption-bucket-key-enabled"]
    ).lower().should.equal("true")


@mock_s3
def test_copy_key_with_metadata():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    key = s3.Object("foobar", "the-key")
    metadata = {"md": "Metadatastring"}
    content_type = "application/json"
    initial = key.put(Body=b"{}", Metadata=metadata, ContentType=content_type)

    client.copy_object(Bucket="foobar", CopySource="foobar/the-key", Key="new-key")

    resp = client.get_object(Bucket="foobar", Key="new-key")
    resp["Metadata"].should.equal(metadata)
    resp["ContentType"].should.equal(content_type)
    resp["ETag"].should.equal(initial["ETag"])


@mock_s3
def test_copy_key_replace_metadata():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    key = s3.Object("foobar", "the-key")
    initial = key.put(Body=b"some value", Metadata={"md": "Metadatastring"})

    client.copy_object(
        Bucket="foobar",
        CopySource="foobar/the-key",
        Key="new-key",
        Metadata={"momd": "Mometadatastring"},
        MetadataDirective="REPLACE",
    )

    resp = client.get_object(Bucket="foobar", Key="new-key")
    resp["Metadata"].should.equal({"momd": "Mometadatastring"})
    resp["ETag"].should.equal(initial["ETag"])


@mock_s3
def test_copy_key_without_changes_should_error():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "my_bucket"
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    key_name = "my_key"
    key = s3.Object(bucket_name, key_name)

    s3.create_bucket(Bucket=bucket_name)
    key.put(Body=b"some value")

    with pytest.raises(ClientError) as e:
        client.copy_object(
            Bucket=bucket_name,
            CopySource="{}/{}".format(bucket_name, key_name),
            Key=key_name,
        )
        e.value.response["Error"]["Message"].should.equal(
            "This copy request is illegal because it is trying to copy an object to itself without changing the object's metadata, storage class, website redirect location or encryption attributes."
        )


@mock_s3
def test_copy_key_without_changes_should_not_error():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "my_bucket"
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    key_name = "my_key"
    key = s3.Object(bucket_name, key_name)

    s3.create_bucket(Bucket=bucket_name)
    key.put(Body=b"some value")

    client.copy_object(
        Bucket=bucket_name,
        CopySource="{}/{}".format(bucket_name, key_name),
        Key=key_name,
        Metadata={"some-key": "some-value"},
        MetadataDirective="REPLACE",
    )

    new_object = client.get_object(Bucket=bucket_name, Key=key_name)

    assert new_object["Metadata"] == {"some-key": "some-value"}


@mock_s3
def test_copy_key_reduced_redundancy():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("test_bucket")
    bucket.create()

    bucket.put_object(Key="the-key", Body=b"somedata")

    client.copy_object(
        Bucket="test_bucket",
        CopySource="test_bucket/the-key",
        Key="new-key",
        StorageClass="REDUCED_REDUNDANCY",
    )

    keys = dict([(k.key, k) for k in bucket.objects.all()])
    keys["new-key"].storage_class.should.equal("REDUCED_REDUNDANCY")
    keys["the-key"].storage_class.should.equal("STANDARD")


@mock_s3
def test_copy_non_existing_file():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    src = "srcbucket"
    target = "target"
    s3.create_bucket(Bucket=src)
    s3.create_bucket(Bucket=target)

    s3_client = boto3.client("s3")
    with pytest.raises(ClientError) as exc:
        s3_client.copy_object(
            Bucket=target, CopySource={"Bucket": src, "Key": "foofoofoo"}, Key="newkey"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchKey")
    err["Message"].should.equal("The specified key does not exist.")
    err["Key"].should.equal("foofoofoo")


@mock_s3
def test_copy_object_with_versioning():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(
        Bucket="blah", CreateBucketConfiguration={"LocationConstraint": "eu-west-1"}
    )
    client.put_bucket_versioning(
        Bucket="blah", VersioningConfiguration={"Status": "Enabled"}
    )

    client.put_object(Bucket="blah", Key="test1", Body=b"test1")
    client.put_object(Bucket="blah", Key="test2", Body=b"test2")

    client.get_object(Bucket="blah", Key="test1")["VersionId"]
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
    e.value.response["Error"]["Code"].should.equal("NoSuchKey")

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
def test_copy_object_from_unversioned_to_versioned_bucket():
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
def test_copy_object_with_replacement_tagging():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="mybucket")
    client.put_object(
        Bucket="mybucket", Key="original", Body=b"test", Tagging="tag=old"
    )

    # using system tags will fail
    with pytest.raises(ClientError) as err:
        client.copy_object(
            CopySource={"Bucket": "mybucket", "Key": "original"},
            Bucket="mybucket",
            Key="copy1",
            TaggingDirective="REPLACE",
            Tagging="aws:tag=invalid_key",
        )

    e = err.value
    e.response["Error"]["Code"].should.equal("InvalidTag")

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
@mock_kms
def test_copy_object_with_kms_encryption():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    kms_client = boto3.client("kms", region_name=DEFAULT_REGION_NAME)
    kms_key = kms_client.create_key()["KeyMetadata"]["KeyId"]

    client.create_bucket(
        Bucket="blah", CreateBucketConfiguration={"LocationConstraint": "eu-west-1"}
    )

    client.put_object(Bucket="blah", Key="test1", Body=b"test1")

    client.copy_object(
        CopySource={"Bucket": "blah", "Key": "test1"},
        Bucket="blah",
        Key="test2",
        SSEKMSKeyId=kms_key,
        ServerSideEncryption="aws:kms",
    )
    result = client.head_object(Bucket="blah", Key="test2")
    assert result["SSEKMSKeyId"] == kms_key
    assert result["ServerSideEncryption"] == "aws:kms"
