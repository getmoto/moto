import time
import boto
import boto3
import datetime
import botocore
from moto import mock_s3
import os
from botocore.config import Config
from moto.s3.responses import DEFAULT_REGION_NAME
import sure


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
    except botocore.client.ClientError as e:
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
    except botocore.client.ClientError as e:
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

    s3.put_object(
        Bucket=bucket_name, Body=b"test", Key=key_name,
    )

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
    except botocore.client.ClientError as e:
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

    s3.put_object(
        Bucket=bucket_name, Body=b"test", Key=key_name,
    )

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
    except botocore.client.ClientError as e:
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
            "Rule": {"DefaultRetention": {"Mode": mode, "Days": days,}},
        },
    )

    s3.put_object(
        Bucket=bucket_name, Body=b"test", Key=key_name,
    )

    deleted = False
    versions_response = s3.list_object_versions(Bucket=bucket_name)
    version_id = versions_response["Versions"][0]["VersionId"]

    try:
        s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
        deleted = True
    except botocore.client.ClientError as e:
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
