import datetime
import time

import boto3
import pytest
from botocore.client import ClientError
from botocore.config import Config

from moto import mock_aws
from moto.core.utils import utcnow
from moto.s3.responses import DEFAULT_REGION_NAME
from tests import allow_aws_request
from tests.test_s3 import s3_aws_verified
from tests.test_s3.test_s3 import enable_versioning


@s3_aws_verified
@pytest.mark.aws_verified
def test_put_object_lock_on_non_versioned_bucket(bucket_name=None):
    s3_client = boto3.client("s3", DEFAULT_REGION_NAME)

    with pytest.raises(ClientError) as exc:
        s3_client.put_object_lock_configuration(
            Bucket=bucket_name,
            ObjectLockConfiguration={
                "ObjectLockEnabled": "Enabled",
                "Rule": {"DefaultRetention": {"Mode": "COMPLIANCE", "Days": 1}},
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidBucketState"
    assert (
        err["Message"]
        == "Versioning must be 'Enabled' on the bucket to apply a Object Lock configuration"
    )


@s3_aws_verified
@pytest.mark.aws_verified
def test_put_object_lock_misconfiguration(bucket_name=None):
    s3_client = boto3.client("s3", DEFAULT_REGION_NAME)

    enable_versioning(bucket_name, s3_client)

    with pytest.raises(ClientError) as exc:
        s3_client.put_object_lock_configuration(Bucket=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "MissingRequestBodyError"
    assert err["Message"] == "Request Body is empty"

    with pytest.raises(ClientError) as exc:
        s3_client.put_object_lock_configuration(
            Bucket=bucket_name, ObjectLockConfiguration={}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "MalformedXML"


@s3_aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "bypass_governance_retention",
    [True, False, None],
    ids=["bypass", "no_bypass", "unspecified"],
)
def test_locked_object_governance_mode(bypass_governance_retention, bucket_name=None):
    s3_client = boto3.client("s3", DEFAULT_REGION_NAME)

    key_name = "file.txt"
    seconds_lock = 10

    enable_versioning(bucket_name, s3_client)

    s3_client.put_object_lock_configuration(
        Bucket=bucket_name,
        ObjectLockConfiguration={
            "ObjectLockEnabled": "Enabled",
            "Rule": {"DefaultRetention": {"Mode": "GOVERNANCE", "Days": 1}},
        },
    )

    until = utcnow() + datetime.timedelta(seconds=seconds_lock)
    s3_client.put_object(
        Bucket=bucket_name,
        Body=b"test",
        Key=key_name,
        ObjectLockMode="GOVERNANCE",
        ObjectLockRetainUntilDate=until,
    )

    versions_response = s3_client.list_object_versions(Bucket=bucket_name)
    initial_version_id = versions_response["Versions"][0]["VersionId"]

    with pytest.raises(ClientError) as exc:
        s3_client.delete_object(
            Bucket=bucket_name, Key=key_name, VersionId=initial_version_id
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "AccessDenied"

    kwargs = {}
    if bypass_governance_retention in [True, False]:
        kwargs["BypassGovernanceRetention"] = bypass_governance_retention

    # Delete the object without VersionId always succeeds
    response = s3_client.delete_objects(
        Bucket=bucket_name,
        Delete={
            "Objects": [
                {"Key": key_name},
            ],
        },
        **kwargs,
    )
    assert response["Deleted"][0]["Key"] == key_name
    deleted_version_id = response["Deleted"][0]["DeleteMarkerVersionId"]

    # Delete any version id only succeeds if BypassGovernanceRetention=true
    response = s3_client.delete_objects(
        Bucket=bucket_name,
        Delete={
            "Objects": [
                {"Key": key_name, "VersionId": initial_version_id},
            ],
        },
        **kwargs,
    )
    if bypass_governance_retention:
        assert "Deleted" in response

        deleted_version_id = response["Deleted"][0]["VersionId"]

        response = s3_client.delete_objects(
            Bucket=bucket_name,
            Delete={
                "Objects": [
                    {"Key": key_name, "VersionId": deleted_version_id},
                ],
            },
            **kwargs,
        )
        assert response["Deleted"] == [
            {"Key": key_name, "VersionId": deleted_version_id}
        ]

    else:
        # BypassGovernanceMode is either unspecified or False
        assert "Errors" in response
        assert response["Errors"][0]["Code"] == "AccessDenied"
        assert response["Errors"][0]["Key"] == key_name
        assert (
            response["Errors"][0]["Message"]
            == "Access Denied because object protected by object lock."
        )

        # We know we couldn't delete the initial version ID
        # Can we delete the DeleteVersion
        response = s3_client.delete_objects(
            Bucket=bucket_name,
            Delete={
                "Objects": [
                    {"Key": key_name, "VersionId": deleted_version_id},
                ],
            },
            **kwargs,
        )


@s3_aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "bypass_governance_retention",
    [True, False, None],
    ids=["bypass", "no_bypass", "unspecified"],
)
def test_locked_object_compliance_mode(bypass_governance_retention, bucket_name=None):
    s3_client = boto3.client("s3", DEFAULT_REGION_NAME)

    key_name = "file.txt"
    seconds_lock = 5 if allow_aws_request() else 2

    enable_versioning(bucket_name, s3_client)

    s3_client.put_object_lock_configuration(
        Bucket=bucket_name,
        ObjectLockConfiguration={
            "ObjectLockEnabled": "Enabled",
            "Rule": {"DefaultRetention": {"Mode": "GOVERNANCE", "Days": 1}},
        },
    )

    until = utcnow() + datetime.timedelta(seconds=seconds_lock)
    s3_client.put_object(
        Bucket=bucket_name,
        Body=b"test",
        Key=key_name,
        ObjectLockMode="COMPLIANCE",
        ObjectLockRetainUntilDate=until,
    )

    versions_response = s3_client.list_object_versions(Bucket=bucket_name)
    initial_version_id = versions_response["Versions"][0]["VersionId"]

    kwargs = {}
    if bypass_governance_retention in [True, False]:
        kwargs["BypassGovernanceRetention"] = bypass_governance_retention

    # Delete the object without VersionId always succeeds
    response = s3_client.delete_objects(
        Bucket=bucket_name,
        Delete={
            "Objects": [
                {"Key": key_name},
            ],
        },
        **kwargs,
    )
    assert response["Deleted"][0]["Key"] == key_name

    # Delete any version id never succeeds in COMPLIANCE mode
    response = s3_client.delete_objects(
        Bucket=bucket_name,
        Delete={
            "Objects": [
                {"Key": key_name, "VersionId": initial_version_id},
            ],
        },
        **kwargs,
    )
    assert "Errors" in response
    assert response["Errors"][0]["Code"] == "AccessDenied"
    assert response["Errors"][0]["Key"] == key_name
    assert (
        response["Errors"][0]["Message"]
        == "Access Denied because object protected by object lock."
    )

    time.sleep(seconds_lock)


@mock_aws
def test_fail_locked_object():
    bucket_name = "locked-bucket2"
    key_name = "file.txt"
    seconds_lock = 2

    s3_client = boto3.client("s3", DEFAULT_REGION_NAME)

    s3_client.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=False)
    until = utcnow() + datetime.timedelta(0, seconds_lock)
    failed = False
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Body=b"test",
            Key=key_name,
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=until,
        )
    except ClientError as exc:
        assert exc.response["Error"]["Code"] == "InvalidRequest"
        failed = True

    assert failed is True
    s3_client.delete_bucket(Bucket=bucket_name)


@mock_aws
def test_put_object_lock():
    s3_client = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))

    bucket_name = "put-lock-bucket-test"
    key_name = "file.txt"
    seconds_lock = 2

    s3_client.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)

    versions_response = s3_client.list_object_versions(Bucket=bucket_name)
    version_id = versions_response["Versions"][0]["VersionId"]
    until = utcnow() + datetime.timedelta(0, seconds_lock)

    s3_client.put_object_retention(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id,
        Retention={"Mode": "COMPLIANCE", "RetainUntilDate": until},
    )

    deleted = False
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
        deleted = True
    except ClientError as exc:
        assert exc.response["Error"]["Code"] == "AccessDenied"

    assert deleted is False

    # cleaning
    time.sleep(seconds_lock)
    s3_client.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
    s3_client.delete_bucket(Bucket=bucket_name)


@s3_aws_verified
@pytest.mark.aws_verified
def test_put_object_legal_hold(bucket_name=None):
    s3_client = boto3.client("s3", DEFAULT_REGION_NAME)

    key_name = "file.txt"

    s3_client.create_bucket(Bucket=bucket_name)
    enable_versioning(bucket_name, s3_client)

    s3_client.put_object_lock_configuration(
        Bucket=bucket_name,
        ObjectLockConfiguration={
            "ObjectLockEnabled": "Enabled",
            "Rule": {"DefaultRetention": {"Mode": "GOVERNANCE", "Days": 1}},
        },
    )

    s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)

    versions_response = s3_client.list_object_versions(Bucket=bucket_name)
    version_id = versions_response["Versions"][0]["VersionId"]

    s3_client.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id,
        LegalHold={"Status": "ON"},
    )

    with pytest.raises(ClientError) as exc:
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=key_name,
            VersionId=version_id,
            BypassGovernanceRetention=True,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "AccessDenied"

    # Deletion works when LegalHold is OFF
    s3_client.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id,
        LegalHold={"Status": "OFF"},
    )
    s3_client.delete_object(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id,
        BypassGovernanceRetention=True,
    )


@mock_aws
def test_put_default_lock():
    # do not run this test in aws, it will block the deletion for a whole day

    s3_client = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))
    bucket_name = "put-default-lock-bucket"
    key_name = "file.txt"

    days = 1
    mode = "COMPLIANCE"
    enabled = "Enabled"

    s3_client.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)
    s3_client.put_object_lock_configuration(
        Bucket=bucket_name,
        ObjectLockConfiguration={
            "ObjectLockEnabled": enabled,
            "Rule": {"DefaultRetention": {"Mode": mode, "Days": days}},
        },
    )

    s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)

    deleted = False
    versions_response = s3_client.list_object_versions(Bucket=bucket_name)
    version_id = versions_response["Versions"][0]["VersionId"]

    try:
        s3_client.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
        deleted = True
    except ClientError as exc:
        assert exc.response["Error"]["Code"] == "AccessDenied"

    assert deleted is False

    response = s3_client.get_object_lock_configuration(Bucket=bucket_name)
    assert response["ObjectLockConfiguration"]["ObjectLockEnabled"] == enabled
    assert (
        response["ObjectLockConfiguration"]["Rule"]["DefaultRetention"]["Mode"] == mode
    )
    assert (
        response["ObjectLockConfiguration"]["Rule"]["DefaultRetention"]["Days"] == days
    )


@mock_aws
def test_put_object_legal_hold_with_versions():
    s3_client = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))

    bucket_name = "put-legal-bucket"
    key_name = "file.txt"

    s3_client.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    put_obj_1 = s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)
    version_id_1 = put_obj_1["VersionId"]
    # lock the object with the version, locking the version 1
    s3_client.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_1,
        LegalHold={"Status": "ON"},
    )

    # put an object on the same key, effectively creating a version 2 of the object
    put_obj_2 = s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)
    version_id_2 = put_obj_2["VersionId"]
    # also lock the version 2 of the object
    s3_client.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_2,
        LegalHold={"Status": "ON"},
    )

    # assert that the version 1 is locked
    head_obj_1 = s3_client.head_object(
        Bucket=bucket_name, Key=key_name, VersionId=version_id_1
    )
    assert head_obj_1["ObjectLockLegalHoldStatus"] == "ON"

    # remove the lock from the version 1 of the object
    s3_client.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_1,
        LegalHold={"Status": "OFF"},
    )

    # assert that you can now delete the version 1 of the object
    s3_client.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_1)

    with pytest.raises(ClientError) as exc:
        s3_client.head_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_1)
    assert exc.value.response["Error"]["Code"] == "404"

    # cleaning
    s3_client.put_object_legal_hold(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_2,
        LegalHold={"Status": "OFF"},
    )
    s3_client.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_2)
    s3_client.delete_bucket(Bucket=bucket_name)


@mock_aws
def test_put_object_lock_with_versions():
    s3_client = boto3.client("s3", config=Config(region_name=DEFAULT_REGION_NAME))

    bucket_name = "put-lock-bucket-test"
    key_name = "file.txt"
    seconds_lock = 2

    s3_client.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    put_obj_1 = s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)
    version_id_1 = put_obj_1["VersionId"]
    put_obj_2 = s3_client.put_object(Bucket=bucket_name, Body=b"test", Key=key_name)
    version_id_2 = put_obj_2["VersionId"]

    until = utcnow() + datetime.timedelta(seconds=seconds_lock)

    s3_client.put_object_retention(
        Bucket=bucket_name,
        Key=key_name,
        VersionId=version_id_1,
        Retention={"Mode": "COMPLIANCE", "RetainUntilDate": until},
    )

    # assert that you can delete the locked version 1 of the object
    deleted = False
    try:
        s3_client.delete_object(
            Bucket=bucket_name, Key=key_name, VersionId=version_id_1
        )
        deleted = True
    except ClientError as exc:
        assert exc.response["Error"]["Code"] == "AccessDenied"

    assert deleted is False

    # assert that you can delete the version 2 of the object, not concerned by the lock
    s3_client.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_2)
    with pytest.raises(ClientError) as exc:
        s3_client.head_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_2)
    assert exc.value.response["Error"]["Code"] == "404"

    # cleaning
    time.sleep(seconds_lock)
    s3_client.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id_1)
    s3_client.delete_bucket(Bucket=bucket_name)
