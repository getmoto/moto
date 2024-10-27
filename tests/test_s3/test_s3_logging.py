import json
from time import sleep
from unittest import SkipTest
from unittest.mock import patch
from uuid import uuid4

import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID
from moto.s3 import s3_backends
from moto.s3.models import FakeBucket
from moto.s3.responses import DEFAULT_REGION_NAME
from tests.test_s3 import empty_bucket, s3_aws_verified


@mock_aws
def test_put_bucket_logging():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    wrong_region_client = boto3.client("s3", region_name="us-west-2")
    bucket_name = "mybucket"
    log_bucket = "logbucket"
    wrong_region_bucket = "wrongregionlogbucket"
    s3_client.create_bucket(Bucket=bucket_name)
    # Adding the ACL for log-delivery later...
    s3_client.create_bucket(Bucket=log_bucket)
    wrong_region_client.create_bucket(
        Bucket=wrong_region_bucket,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # No logging config:
    result = s3_client.get_bucket_logging(Bucket=bucket_name)
    assert not result.get("LoggingEnabled")

    # A log-bucket that doesn't exist:
    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {"TargetBucket": "IAMNOTREAL", "TargetPrefix": ""}
            },
        )
    assert err.value.response["Error"]["Code"] == "InvalidTargetBucketForLogging"

    # A log-bucket that's missing the proper ACLs for LogDelivery:
    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {"TargetBucket": log_bucket, "TargetPrefix": ""}
            },
        )
    assert err.value.response["Error"]["Code"] == "InvalidTargetBucketForLogging"
    assert "log-delivery" in err.value.response["Error"]["Message"]

    # Add the proper "log-delivery" ACL to the log buckets:
    bucket_owner = s3_client.get_bucket_acl(Bucket=log_bucket)["Owner"]
    for bucket in [log_bucket, wrong_region_bucket]:
        s3_client.put_bucket_acl(
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
        s3_client.put_bucket_logging(
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
    s3_client.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {
                "TargetBucket": log_bucket,
                "TargetPrefix": f"{bucket_name}/",
            }
        },
    )
    result = s3_client.get_bucket_logging(Bucket=bucket_name)
    assert result["LoggingEnabled"]["TargetBucket"] == log_bucket
    assert result["LoggingEnabled"]["TargetPrefix"] == f"{bucket_name}/"
    assert not result["LoggingEnabled"].get("TargetGrants")

    # And disabling:
    s3_client.put_bucket_logging(Bucket=bucket_name, BucketLoggingStatus={})
    assert not s3_client.get_bucket_logging(Bucket=bucket_name).get("LoggingEnabled")

    # And enabling with multiple target grants:
    s3_client.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {
                "TargetBucket": log_bucket,
                "TargetPrefix": f"{bucket_name}/",
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

    result = s3_client.get_bucket_logging(Bucket=bucket_name)
    assert len(result["LoggingEnabled"]["TargetGrants"]) == 2
    assert (
        result["LoggingEnabled"]["TargetGrants"][0]["Grantee"]["ID"]
        == "SOMEIDSTRINGHERE9238748923734823917498237489237409123840983274"
    )

    # Test with just 1 grant:
    s3_client.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {
                "TargetBucket": log_bucket,
                "TargetPrefix": f"{bucket_name}/",
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
    result = s3_client.get_bucket_logging(Bucket=bucket_name)
    assert len(result["LoggingEnabled"]["TargetGrants"]) == 1

    # With an invalid grant:
    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {
                    "TargetBucket": log_bucket,
                    "TargetPrefix": f"{bucket_name}/",
                    "TargetGrants": [
                        {
                            "Grantee": {
                                "ID": (
                                    "SOMEIDSTRINGHERE9238748923734823917498"
                                    "237489237409123840983274"
                                ),
                                "Type": "CanonicalUser",
                            },
                            "Permission": "NOTAREALPERM",
                        }
                    ],
                }
            },
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"


@mock_aws
def test_log_file_is_created():
    # Create necessary buckets
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    log_bucket = "logbucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.create_bucket(Bucket=log_bucket)

    # Enable logging
    bucket_owner = s3_client.get_bucket_acl(Bucket=log_bucket)["Owner"]
    s3_client.put_bucket_acl(
        Bucket=log_bucket,
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
    s3_client.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {
                "TargetBucket": log_bucket,
                "TargetPrefix": f"{bucket_name}/",
            }
        },
    )

    # Make some requests against the source bucket
    s3_client.put_object(Bucket=bucket_name, Key="key1", Body=b"")
    s3_client.put_object(Bucket=bucket_name, Key="key2", Body=b"data")

    s3_client.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {"TargetBucket": log_bucket, "TargetPrefix": ""}
        },
    )
    s3_client.list_objects_v2(Bucket=bucket_name)

    # Verify files are created in the target (logging) bucket
    keys = [k["Key"] for k in s3_client.list_objects_v2(Bucket=log_bucket)["Contents"]]
    assert len([k for k in keys if k.startswith("mybucket/")]) == 3
    assert len([k for k in keys if not k.startswith("mybucket/")]) == 1

    # Verify (roughly) files have the correct content
    contents = [
        s3_client.get_object(Bucket=log_bucket, Key=key)["Body"].read().decode("utf-8")
        for key in keys
    ]
    assert any(c for c in contents if bucket_name in c)
    assert any(c for c in contents if "REST.GET.BUCKET" in c)
    assert any(c for c in contents if "REST.PUT.BUCKET" in c)


@mock_aws
def test_invalid_bucket_logging_when_permissions_are_false():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't patch permission logic in ServerMode")

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    log_bucket = "logbucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.create_bucket(Bucket=log_bucket)
    with patch(
        "moto.s3.models.FakeBucket._log_permissions_enabled_policy", return_value=False
    ), patch(
        "moto.s3.models.FakeBucket._log_permissions_enabled_acl", return_value=False
    ):
        with pytest.raises(ClientError) as err:
            s3_client.put_bucket_logging(
                Bucket=bucket_name,
                BucketLoggingStatus={
                    "LoggingEnabled": {"TargetBucket": log_bucket, "TargetPrefix": ""}
                },
            )
        assert err.value.response["Error"]["Code"] == "InvalidTargetBucketForLogging"
        assert "log-delivery" in err.value.response["Error"]["Message"]


@mock_aws
def test_valid_bucket_logging_when_permissions_are_true():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't patch permission logic in ServerMode")

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    log_bucket = "logbucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.create_bucket(Bucket=log_bucket)
    with patch(
        "moto.s3.models.FakeBucket._log_permissions_enabled_policy", return_value=True
    ), patch(
        "moto.s3.models.FakeBucket._log_permissions_enabled_acl", return_value=True
    ):
        s3_client.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {
                    "TargetBucket": log_bucket,
                    "TargetPrefix": f"{bucket_name}/",
                }
            },
        )
        result = s3_client.get_bucket_logging(Bucket=bucket_name)
        assert result["LoggingEnabled"]["TargetBucket"] == log_bucket
        assert result["LoggingEnabled"]["TargetPrefix"] == f"{bucket_name}/"


@mock_aws
def test_bucket_policy_not_set():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't patch permission logic in ServerMode")

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_backend = s3_backends[DEFAULT_ACCOUNT_ID]["global"]

    log_bucket = "log_bucket"
    s3_client.create_bucket(Bucket=log_bucket)
    log_bucket_obj = s3_backend.get_bucket(log_bucket)

    assert (
        FakeBucket._log_permissions_enabled_policy(
            target_bucket=log_bucket_obj, target_prefix=""
        )
        is False
    )


@mock_aws
def test_bucket_policy_principal():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't patch permission logic in ServerMode")

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_backend = s3_backends[DEFAULT_ACCOUNT_ID]["global"]

    log_bucket = "log_bucket"
    s3_client.create_bucket(Bucket=log_bucket)
    log_bucket_obj = s3_backend.get_bucket(log_bucket)

    invalid_principal_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "not_logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket}/*",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket, Policy=json.dumps(invalid_principal_policy)
    )
    assert (
        FakeBucket._log_permissions_enabled_policy(
            target_bucket=log_bucket_obj, target_prefix=""
        )
        is False
    )

    s3_client.delete_bucket_policy(Bucket=log_bucket)
    valid_principal_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket}/*",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket, Policy=json.dumps(valid_principal_policy)
    )
    assert FakeBucket._log_permissions_enabled_policy(
        target_bucket=log_bucket_obj, target_prefix=""
    )


@mock_aws
def test_bucket_policy_effect():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't patch permission logic in ServerMode")

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_backend = s3_backends[DEFAULT_ACCOUNT_ID]["global"]

    log_bucket = "log_bucket"
    s3_client.create_bucket(Bucket=log_bucket)
    log_bucket_obj = s3_backend.get_bucket(log_bucket)
    deny_effect_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Deny",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket}/*",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket, Policy=json.dumps(deny_effect_policy)
    )
    assert (
        FakeBucket._log_permissions_enabled_policy(
            target_bucket=log_bucket_obj, target_prefix=""
        )
        is False
    )

    s3_client.delete_bucket_policy(Bucket=log_bucket)
    allow_effect_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket}/*",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket, Policy=json.dumps(allow_effect_policy)
    )
    assert FakeBucket._log_permissions_enabled_policy(
        target_bucket=log_bucket_obj, target_prefix=""
    )


@mock_aws
def test_bucket_policy_action():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't patch permission logic in ServerMode")

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_backend = s3_backends[DEFAULT_ACCOUNT_ID]["global"]

    log_bucket = "log_bucket"
    s3_client.create_bucket(Bucket=log_bucket)
    log_bucket_obj = s3_backend.get_bucket(log_bucket)
    non_put_object_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:GetObject"],
                "Resource": f"arn:aws:s3:::{log_bucket}/*",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket, Policy=json.dumps(non_put_object_policy)
    )
    assert (
        FakeBucket._log_permissions_enabled_policy(
            target_bucket=log_bucket_obj, target_prefix=""
        )
        is False
    )

    s3_client.delete_bucket_policy(Bucket=log_bucket)
    put_object_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket}/*",
            }
        ],
    }
    s3_client.put_bucket_policy(Bucket=log_bucket, Policy=json.dumps(put_object_policy))
    assert FakeBucket._log_permissions_enabled_policy(
        target_bucket=log_bucket_obj, target_prefix=""
    )


@mock_aws
def test_bucket_policy_resource():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't patch permission logic in ServerMode")

    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_backend = s3_backends[DEFAULT_ACCOUNT_ID]["global"]

    log_bucket = "log_bucket"
    s3_client.create_bucket(Bucket=log_bucket)
    log_bucket_obj = s3_backend.get_bucket(log_bucket)
    entire_bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket}/*",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket, Policy=json.dumps(entire_bucket_policy)
    )
    assert FakeBucket._log_permissions_enabled_policy(
        target_bucket=log_bucket_obj, target_prefix=""
    )
    assert FakeBucket._log_permissions_enabled_policy(
        target_bucket=log_bucket_obj, target_prefix="prefix"
    )

    s3_client.delete_bucket_policy(Bucket=log_bucket)
    bucket_level_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket}",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket, Policy=json.dumps(bucket_level_policy)
    )
    assert FakeBucket._log_permissions_enabled_policy(
        target_bucket=log_bucket_obj, target_prefix=""
    )
    assert FakeBucket._log_permissions_enabled_policy(
        target_bucket=log_bucket_obj, target_prefix="prefix"
    )

    s3_client.delete_bucket_policy(Bucket=log_bucket)
    specfic_prefix_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket}/prefix*",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket, Policy=json.dumps(specfic_prefix_policy)
    )
    assert (
        FakeBucket._log_permissions_enabled_policy(
            target_bucket=log_bucket_obj, target_prefix=""
        )
        is False
    )
    assert FakeBucket._log_permissions_enabled_policy(
        target_bucket=log_bucket_obj, target_prefix="prefix"
    )


@s3_aws_verified
@pytest.mark.aws_verified
def test_put_logging_w_bucket_policy_no_prefix(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    log_bucket_name = f"{uuid4()}"
    s3_client.create_bucket(Bucket=log_bucket_name)
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket_name}/*",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket_name, Policy=json.dumps(bucket_policy)
    )
    s3_client.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {"TargetBucket": log_bucket_name, "TargetPrefix": ""}
        },
    )
    result = s3_client.get_bucket_logging(Bucket=bucket_name)
    # Logging Config is not immediately available
    for _ in range(5):
        if "LoggingEnabled" not in result:
            sleep(1)
            result = s3_client.get_bucket_logging(Bucket=bucket_name)
    assert result["LoggingEnabled"]["TargetBucket"] == log_bucket_name
    assert result["LoggingEnabled"]["TargetPrefix"] == ""

    empty_bucket(s3_client, log_bucket_name)
    s3_client.delete_bucket(Bucket=log_bucket_name)


@s3_aws_verified
@pytest.mark.aws_verified
def test_put_logging_w_bucket_policy_w_prefix(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    log_bucket_name = f"{uuid4()}"
    s3_client.create_bucket(Bucket=log_bucket_name)
    prefix = "some-prefix"
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ServerAccessLogsPolicy",
                "Effect": "Allow",
                "Principal": {"Service": "logging.s3.amazonaws.com"},
                "Action": ["s3:PutObject"],
                "Resource": f"arn:aws:s3:::{log_bucket_name}/{prefix}*",
            }
        ],
    }
    s3_client.put_bucket_policy(
        Bucket=log_bucket_name, Policy=json.dumps(bucket_policy)
    )
    s3_client.put_bucket_logging(
        Bucket=bucket_name,
        BucketLoggingStatus={
            "LoggingEnabled": {"TargetBucket": log_bucket_name, "TargetPrefix": prefix}
        },
    )
    result = s3_client.get_bucket_logging(Bucket=bucket_name)
    # Logging Config is not immediately available
    for _ in range(5):
        if "LoggingEnabled" not in result:
            sleep(1)
            result = s3_client.get_bucket_logging(Bucket=bucket_name)
    assert result["LoggingEnabled"]["TargetBucket"] == log_bucket_name
    assert result["LoggingEnabled"]["TargetPrefix"] == prefix

    empty_bucket(s3_client, log_bucket_name)
    s3_client.delete_bucket(Bucket=log_bucket_name)
