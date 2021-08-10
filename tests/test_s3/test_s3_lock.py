import time
import boto3
import datetime
import botocore
from moto import mock_s3

import sure


@mock_s3
def test_locked_object():
    s3 = boto3.client("s3")

    bucket_name = "locked-bucket-crist"
    key_name = "file.txt"
    seconds_lock = 5

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    until = datetime.datetime.utcnow() + datetime.timedelta(0, seconds_lock)
    s3.put_object(
        Bucket=bucket_name,
        Body=b"test",
        Key="file.txt",
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
    bucket_name = "locked-bucket"
    key_name = "file.txt"

    s3 = boto3.client("s3")

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=False)
    failed = False
    try:
        s3.put_object(
            Bucket=bucket_name,
            Body=b"test",
            Key=key_name,
            ObjectLockMode="COMPLIANCE",
            ObjectLockLegalHoldStatus="ON",
        )
    except botocore.client.ClientError as e:
        e.response["Error"]["Code"].should.equal("InvalidArgument")
        failed = True

    failed.should.equal(True)
    s3.delete_bucket(Bucket=bucket_name)
