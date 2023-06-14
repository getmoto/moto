import datetime

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
    key2.copy_from(CopySource=f"foobar/{key_name}")

    resp = client.get_object(Bucket="foobar", Key=key_name)
    resp["Body"].read().should.equal(b"some value")
    resp = client.get_object(Bucket="foobar", Key="new-key")
    resp["Body"].read().should.equal(b"some value")


@mock_s3
def test_copy_key_boto3_with_sha256_checksum():
    # Setup
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    key_name = "key"
    new_key = "new_key"
    bucket = "foobar"
    expected_hash = "qz0H8xacy9DtbEtF3iFRn5+TjHLSQSSZiquUnOg7tRs="

    s3.create_bucket(Bucket=bucket)
    key = s3.Object("foobar", key_name)
    key.put(Body=b"some value")

    # Execute
    key2 = s3.Object(bucket, new_key)
    key2.copy(
        CopySource={"Bucket": bucket, "Key": key_name},
        ExtraArgs={"ChecksumAlgorithm": "SHA256"},
    )

    # Verify
    resp = client.get_object_attributes(
        Bucket=bucket, Key=new_key, ObjectAttributes=["Checksum"]
    )

    assert "Checksum" in resp
    assert "ChecksumSHA256" in resp["Checksum"]
    assert resp["Checksum"]["ChecksumSHA256"] == expected_hash

    # Verify in place
    copy_in_place = client.copy_object(
        Bucket=bucket,
        CopySource=f"{bucket}/{new_key}",
        Key=new_key,
        ChecksumAlgorithm="SHA256",
        MetadataDirective="REPLACE",
    )

    assert "ChecksumSHA256" in copy_in_place["CopyObjectResult"]
    assert copy_in_place["CopyObjectResult"]["ChecksumSHA256"] == expected_hash


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
    key2.copy_from(CopySource=f"foobar/the-key?versionId={old_version['VersionId']}")

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
            CopySource=f"{bucket_name}/{key_name}",
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
        CopySource=f"{bucket_name}/{key_name}",
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


@mock_s3
@mock_kms
def test_copy_object_in_place_with_encryption():
    kms_client = boto3.client("kms", region_name=DEFAULT_REGION_NAME)
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    kms_key = kms_client.create_key()["KeyMetadata"]["KeyId"]
    bucket = s3.Bucket("test_bucket")
    bucket.create()
    key = "source-key"
    resp = client.put_object(
        Bucket="test_bucket",
        Key=key,
        Body=b"somedata",
        ServerSideEncryption="aws:kms",
        BucketKeyEnabled=True,
        SSEKMSKeyId=kms_key,
    )
    assert resp["BucketKeyEnabled"] is True

    # assert that you can copy in place with the same Encryption settings
    client.copy_object(
        Bucket="test_bucket",
        CopySource=f"test_bucket/{key}",
        Key=key,
        ServerSideEncryption="aws:kms",
        BucketKeyEnabled=True,
        SSEKMSKeyId=kms_key,
    )

    # assert that the BucketKeyEnabled setting is not kept in the destination key
    resp = client.copy_object(
        Bucket="test_bucket",
        CopySource=f"test_bucket/{key}",
        Key=key,
        ServerSideEncryption="aws:kms",
        SSEKMSKeyId=kms_key,
    )
    assert "BucketKeyEnabled" not in resp

    # this is an edge case, if the source object SSE was not AES256, AWS allows you to not specify any fields
    # as it will use AES256 by default and is different from the source key
    resp = client.copy_object(
        Bucket="test_bucket",
        CopySource=f"test_bucket/{key}",
        Key=key,
    )
    assert resp["ServerSideEncryption"] == "AES256"

    # check that it allows copying in the place with the same ServerSideEncryption setting as the source
    resp = client.copy_object(
        Bucket="test_bucket",
        CopySource=f"test_bucket/{key}",
        Key=key,
        ServerSideEncryption="AES256",
    )
    assert resp["ServerSideEncryption"] == "AES256"


@mock_s3
def test_copy_object_in_place_with_storage_class():
    # this test will validate that setting StorageClass (even the same as source) allows a copy in place
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "test-bucket"
    bucket = s3.Bucket(bucket_name)
    bucket.create()
    key = "source-key"
    bucket.put_object(Key=key, Body=b"somedata", StorageClass="STANDARD")
    client.copy_object(
        Bucket=bucket_name,
        CopySource=f"{bucket_name}/{key}",
        Key=key,
        StorageClass="STANDARD",
    )
    # verify that the copy worked
    resp = client.get_object_attributes(
        Bucket=bucket_name, Key=key, ObjectAttributes=["StorageClass"]
    )
    assert resp["StorageClass"] == "STANDARD"


@mock_s3
def test_copy_object_does_not_copy_storage_class():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("test_bucket")
    bucket.create()
    source_key = "source-key"
    dest_key = "dest-key"
    bucket.put_object(Key=source_key, Body=b"somedata", StorageClass="STANDARD_IA")
    client.copy_object(
        Bucket="test_bucket",
        CopySource=f"test_bucket/{source_key}",
        Key=dest_key,
    )

    # Verify that the destination key does not have STANDARD_IA as StorageClass
    keys = dict([(k.key, k) for k in bucket.objects.all()])
    keys[source_key].storage_class.should.equal("STANDARD_IA")
    keys[dest_key].storage_class.should.equal("STANDARD")


@mock_s3
def test_copy_object_does_not_copy_acl():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "testbucket"
    bucket = s3.Bucket(bucket_name)
    bucket.create()
    source_key = "source-key"
    dest_key = "dest-key"
    control_key = "control-key"
    # do not set ACL for the control key to get default ACL
    bucket.put_object(Key=control_key, Body=b"somedata")
    # set ACL for the source key to check if it will get copied
    bucket.put_object(Key=source_key, Body=b"somedata", ACL="public-read")
    # copy object without specifying ACL, so it should get default ACL
    client.copy_object(
        Bucket=bucket_name,
        CopySource=f"{bucket_name}/{source_key}",
        Key=dest_key,
    )

    # Get the ACL from the all the keys
    source_acl = client.get_object_acl(Bucket=bucket_name, Key=source_key)
    dest_acl = client.get_object_acl(Bucket=bucket_name, Key=dest_key)
    default_acl = client.get_object_acl(Bucket=bucket_name, Key=control_key)
    # assert that the source key ACL are different from the destination key ACL
    assert source_acl["Grants"] != dest_acl["Grants"]
    # assert that the copied key got the default ACL like the control key
    assert default_acl["Grants"] == dest_acl["Grants"]


@mock_s3
def test_copy_object_in_place_with_metadata():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "testbucket"
    bucket = s3.Bucket(bucket_name)
    bucket.create()
    key_name = "source-key"
    bucket.put_object(Key=key_name, Body=b"somedata")

    # test that giving metadata is not enough, and should provide MetadataDirective=REPLACE on top
    with pytest.raises(ClientError) as e:
        client.copy_object(
            Bucket=bucket_name,
            CopySource=f"{bucket_name}/{key_name}",
            Key=key_name,
            Metadata={"key": "value"},
        )
        e.value.response["Error"]["Message"].should.equal(
            "This copy request is illegal because it is trying to copy an object to itself without changing the object's metadata, storage class, website redirect location or encryption attributes."
        )

    # you can only provide MetadataDirective=REPLACE and it will copy without any metadata
    client.copy_object(
        Bucket=bucket_name,
        CopySource=f"{bucket_name}/{key_name}",
        Key=key_name,
        MetadataDirective="REPLACE",
    )

    result = client.head_object(Bucket=bucket_name, Key=key_name)
    assert result["Metadata"] == {}


@mock_s3
def test_copy_objet_legal_hold():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "testbucket"
    source_key = "source-key"
    dest_key = "dest-key"
    client.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)
    client.put_object(
        Bucket=bucket_name,
        Key=source_key,
        Body=b"somedata",
        ObjectLockLegalHoldStatus="ON",
    )

    head_object = client.head_object(Bucket=bucket_name, Key=source_key)
    assert head_object["ObjectLockLegalHoldStatus"] == "ON"
    assert "VersionId" in head_object
    version_id = head_object["VersionId"]

    resp = client.copy_object(
        Bucket=bucket_name,
        CopySource=f"{bucket_name}/{source_key}",
        Key=dest_key,
    )
    assert resp["CopySourceVersionId"] == version_id
    assert resp["VersionId"] != version_id

    # the destination key did not keep the legal hold from the source key
    head_object = client.head_object(Bucket=bucket_name, Key=dest_key)
    assert "ObjectLockLegalHoldStatus" not in head_object


@mock_s3
def test_s3_copy_object_lock():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "testbucket"
    source_key = "source-key"
    dest_key = "dest-key"
    client.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)
    # manipulate a bit the datetime object for an easier comparison
    retain_until = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
        minutes=1
    )
    retain_until = retain_until.replace(microsecond=0)

    client.put_object(
        Bucket=bucket_name,
        Key=source_key,
        Body="test",
        ObjectLockMode="GOVERNANCE",
        ObjectLockRetainUntilDate=retain_until,
    )

    head_object = client.head_object(Bucket=bucket_name, Key=source_key)

    assert head_object["ObjectLockMode"] == "GOVERNANCE"
    assert head_object["ObjectLockRetainUntilDate"] == retain_until
    assert "VersionId" in head_object
    version_id = head_object["VersionId"]

    resp = client.copy_object(
        Bucket=bucket_name,
        CopySource=f"{bucket_name}/{source_key}",
        Key=dest_key,
    )
    assert resp["CopySourceVersionId"] == version_id
    assert resp["VersionId"] != version_id

    # the destination key did not keep the lock mode nor the lock until from the source key
    head_object = client.head_object(Bucket=bucket_name, Key=dest_key)
    assert "ObjectLockMode" not in head_object
    assert "ObjectLockRetainUntilDate" not in head_object


@mock_s3
def test_copy_object_in_place_website_redirect_location():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "testbucket"
    key = "source-key"
    client.create_bucket(Bucket=bucket_name)
    # this test will validate that setting WebsiteRedirectLocation (even the same as source) allows a copy in place

    client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body="test",
        WebsiteRedirectLocation="/test/direct",
    )

    head_object = client.head_object(Bucket=bucket_name, Key=key)
    assert head_object["WebsiteRedirectLocation"] == "/test/direct"

    # copy the object with the same WebsiteRedirectLocation as the source object
    client.copy_object(
        Bucket=bucket_name,
        CopySource=f"{bucket_name}/{key}",
        Key=key,
        WebsiteRedirectLocation="/test/direct",
    )

    head_object = client.head_object(Bucket=bucket_name, Key=key)
    assert head_object["WebsiteRedirectLocation"] == "/test/direct"


@mock_s3
def test_copy_object_in_place_with_bucket_encryption():
    # If a bucket has encryption configured, it will allow copy in place per default
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "test-bucket"
    client.create_bucket(Bucket=bucket_name)
    key = "source-key"

    response = client.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                    "BucketKeyEnabled": False,
                },
            ]
        },
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.put_object(
        Body=b"",
        Bucket=bucket_name,
        Key=key,
    )
    assert response["ServerSideEncryption"] == "AES256"

    response = client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": key},
        Key=key,
    )
    assert response["ServerSideEncryption"] == "AES256"


@mock_s3
@pytest.mark.parametrize(
    "algorithm",
    ["CRC32", "SHA1", "SHA256"],
)
def test_copy_key_boto3_with_both_sha256_checksum(algorithm):
    # This test will validate that moto S3 checksum calculations are correct
    # We first create an object with a Checksum calculated by boto, by specifying ChecksumAlgorithm="SHA256"
    # we then retrieve the right checksum from this request
    # we copy the object while requesting moto to recalculate the checksum for that key
    # we verify that both checksums are equal
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    source_key = "source-key"
    dest_key = "dest-key"
    bucket = "foobar"
    body = b"checksum-test"
    client.create_bucket(Bucket=bucket)

    checksum_key = f"Checksum{algorithm}"

    resp = client.put_object(
        Bucket=bucket,
        Key=source_key,
        Body=body,
        ChecksumAlgorithm=algorithm,
    )
    assert checksum_key in resp
    checksum_by_boto = resp[checksum_key]

    resp = client.copy_object(
        Bucket=bucket,
        CopySource=f"{bucket}/{source_key}",
        Key=dest_key,
        ChecksumAlgorithm=algorithm,
    )

    assert checksum_key in resp["CopyObjectResult"]
    assert resp["CopyObjectResult"][checksum_key] == checksum_by_boto


@mock_s3
@pytest.mark.parametrize(
    "algorithm, checksum",
    [
        ("CRC32", "lVk/nw=="),
        ("SHA1", "jbXkHAsXUrubtL3dqDQ4w+7WXc0="),
        ("SHA256", "1YQo81vx2VFUl0q5ccWISq8AkSBQQ0WO80S82TmfdIQ="),
    ],
)
def test_copy_object_calculates_checksum(algorithm, checksum):
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    source_key = "source-key"
    dest_key = "dest-key"
    bucket = "foobar"
    body = b"test-checksum"
    client.create_bucket(Bucket=bucket)

    checksum_key = f"Checksum{algorithm}"

    resp = client.put_object(
        Bucket=bucket,
        Key=source_key,
        Body=body,
    )
    assert checksum_key not in resp

    resp = client.copy_object(
        Bucket=bucket,
        CopySource=f"{bucket}/{source_key}",
        Key=dest_key,
        ChecksumAlgorithm=algorithm,
    )

    assert checksum_key in resp["CopyObjectResult"]
    assert resp["CopyObjectResult"][checksum_key] == checksum


@mock_s3
def test_copy_object_keeps_checksum():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    source_key = "source-key"
    dest_key = "dest-key"
    bucket = "foobar"
    body = b"test-checksum"
    expected_checksum = "1YQo81vx2VFUl0q5ccWISq8AkSBQQ0WO80S82TmfdIQ="
    client.create_bucket(Bucket=bucket)

    # put an object with a checksum
    resp = client.put_object(
        Bucket=bucket,
        Key=source_key,
        Body=body,
        ChecksumAlgorithm="SHA256",
    )
    assert "ChecksumSHA256" in resp
    assert resp["ChecksumSHA256"] == expected_checksum

    # do not specify the checksum
    resp = client.copy_object(
        Bucket=bucket,
        CopySource=f"{bucket}/{source_key}",
        Key=dest_key,
    )

    # assert that it kept the checksum from the source key
    assert "ChecksumSHA256" in resp["CopyObjectResult"]
    assert resp["CopyObjectResult"]["ChecksumSHA256"] == expected_checksum
