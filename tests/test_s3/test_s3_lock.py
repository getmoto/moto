import time
import boto3
import datetime
import pytest
from moto import mock_s3
from botocore.config import Config
from botocore.client import ClientError
from moto.s3.responses import DEFAULT_REGION_NAME
import sure  # noqa # pylint: disable=unused-import


@mock_s3
def test_locked_object():
    s3 = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))

    bucket_name = "locked-bucket-test"
    key_name = "file.txt"
    seconds_lock = 2

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    until = datetime.datetime.utcnow() + datetime.timedelta(0, seconds_lock)
    s3.put_object(
        Bucket=bucket_name,
        Body=b"test",
        Key=key_name,
        ObjectLockMode="COMPLIANCE",
        ObjectLockRetainUntilDate=until,
    )

    versions_response = s3.list_object_versions(Bucket=bucket_name)
    version_id = versions_response["Versions"][0]["VersionId"]

    deleted = False
    try:
        s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
        deleted = True
    except ClientError as e:
        e.response["Error"]["Code"].should.equal("AccessDenied")

    deleted.should.equal(False)

    # cleaning
    time.sleep(seconds_lock)
    s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
    s3.delete_bucket(Bucket=bucket_name)


@mock_s3
def test_fail_locked_object():
    bucket_name = "locked-bucket2"
    key_name = "file.txt"
    seconds_lock = 2

    s3 = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=False)
    until = datetime.datetime.utcnow() + datetime.timedelta(0, seconds_lock)
    failed = False
    try:
        s3.put_object(
            Bucket=bucket_name,
            Body=b"test",
            Key=key_name,
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=until,
        )
    except ClientError as e:
        e.response["Error"]["Code"].should.equal("InvalidRequest")
        failed = True

    failed.should.equal(True)
    s3.delete_bucket(Bucket=bucket_name)


@mock_s3
def test_put_object_lock():
    s3 = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))

    bucket_name = "put-lock-bucket-test"
    key_name = "file.txt"
    seconds_lock = 2

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    s3.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)

    versions_response = s3.list_object_versions(Bucket=bucket_name)
    version_id = versions_response["Versions"][0]["VersionId"]
    until = datetime.datetime.utcnow() + datetime.timedelta(0, seconds_lock)

    s3.put_object_retention(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id,
        Retention={"Mode": "COMPLIANCE", "RetainUntilDate": until},
    )

    deleted = False
    try:
        s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
        deleted = True
    except ClientError as e:
        e.response["Error"]["Code"].should.equal("AccessDenied")

    deleted.should.equal(False)

    # cleaning
    time.sleep(seconds_lock)
    s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
    s3.delete_bucket(Bucket=bucket_name)


@mock_s3
def test_put_object_legal_hold():
    s3 = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))

    bucket_name = "put-legal-bucket"
    key_name = "file.txt"

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    s3.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)

    versions_response = s3.list_object_versions(Bucket=bucket_name)
    version_id = versions_response["Versions"][0]["VersionId"]

    s3.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id,
        LegalHold={"Status": "ON"},
    )

    deleted = False
    try:
        s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
        deleted = True
    except ClientError as e:
        e.response["Error"]["Code"].should.equal("AccessDenied")

    deleted.should.equal(False)

    # cleaning
    s3.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id,
        LegalHold={"Status": "OFF"},
    )
    s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
    s3.delete_bucket(Bucket=bucket_name)


@mock_s3
def test_put_default_lock():
    # do not run this test in aws, it will block the deletion for a whole day

    s3 = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))
    bucket_name = "put-default-lock-bucket"
    key_name = "file.txt"

    days = 1
    mode = "COMPLIANCE"
    enabled = "Enabled"

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)
    s3.put_object_lock_configuration(
        Bucket=bucket_name,
        ObjectLockConfiguration={
            "ObjectLockEnabled": enabled,
            "Rule": {"DefaultRetention": {"Mode": mode, "Days": days}},
        },
    )

    s3.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)

    deleted = False
    versions_response = s3.list_object_versions(Bucket=bucket_name)
    version_id = versions_response["Versions"][0]["VersionId"]

    try:
        s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
        deleted = True
    except ClientError as e:
        e.response["Error"]["Code"].should.equal("AccessDenied")

    deleted.should.equal(False)

    response = s3.get_object_lock_configuration(Bucket=bucket_name)
    response["ObjectLockConfiguration"]["ObjectLockEnabled"].should.equal(enabled)
    response["ObjectLockConfiguration"]["Rule"]["DefaultRetention"][
        "Mode"
    ].should.equal(mode)
    response["ObjectLockConfiguration"]["Rule"]["DefaultRetention"][
        "Days"
    ].should.equal(days)


@mock_s3
def test_put_object_legal_hold_with_versions():
    s3 = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))

    bucket_name = "put-legal-bucket"
    key_name = "file.txt"

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    put_obj_1 = s3.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)
    version_id_1 = put_obj_1["VersionId"]
    # lock the object with the version, locking the version 1
    s3.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_1,
        LegalHold={"Status": "ON"},
    )

    # put an object on the same key, effectively creating a version 2 of the object
    put_obj_2 = s3.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)
    version_id_2 = put_obj_2["VersionId"]
    # also lock the version 2 of the object
    s3.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_2,
        LegalHold={"Status": "ON"},
    )

    # assert that the version 1 is locked
    head_obj_1 = s3.head_object(
        Bucket=bucket_name, Key=key_name, VersionId=version_id_1
    )
    assert head_obj_1["ObjectLockLegalHoldStatus"] == "ON"

    # remove the lock from the version 1 of the object
    s3.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_1,
        LegalHold={"Status": "OFF"},
    )

    # assert that you can now delete the version 1 of the object
    s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_1)

    with pytest.raises(ClientError) as e:
        s3.head_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_1)
    assert e.value.response["Error"]["Code"] == "404"

    # cleaning
    s3.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_2,
        LegalHold={"Status": "OFF"},
    )
    s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_2)
    s3.delete_bucket(Bucket=bucket_name)


@mock_s3
def test_put_object_lock_with_versions():
    s3 = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))

    bucket_name = "put-lock-bucket-test"
    key_name = "file.txt"
    seconds_lock = 2

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    put_obj_1 = s3.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)
    version_id_1 = put_obj_1["VersionId"]
    put_obj_2 = s3.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)
    version_id_2 = put_obj_2["VersionId"]

    until = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds_lock)

    s3.put_object_retention(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_1,
        Retention={"Mode": "COMPLIANCE", "RetainUntilDate": until},
    )

    # assert that you can delete the locked version 1 of the object
    deleted = False
    try:
        s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_1)
        deleted = True
    except ClientError as e:
        e.response["Error"]["Code"].should.equal("AccessDenied")

    deleted.should.equal(False)

    # assert that you can delete the version 2 of the object, not concerned by the lock
    s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_2)
    with pytest.raises(ClientError) as e:
        s3.head_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_2)
    assert e.value.response["Error"]["Code"] == "404"

    # cleaning
    time.sleep(seconds_lock)
    s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_1)
    s3.delete_bucket(Bucket=bucket_name)
