from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_s3

DEFAULT_REGION_NAME = "us-east-1"


@mock_s3
def test_get_bucket_replication_for_unexisting_bucket():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3_client.get_bucket_replication(Bucket=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchBucket"
    assert err["Message"] == "The specified bucket does not exist"
    assert err["BucketName"] == bucket_name


@mock_s3
def test_get_bucket_replication_bucket_without_replication():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)

    with pytest.raises(ClientError) as exc:
        s3_client.get_bucket_replication(Bucket=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ReplicationConfigurationNotFoundError"
    assert err["Message"] == "The replication configuration was not found"
    assert err["BucketName"] == bucket_name


@mock_s3
def test_delete_bucket_replication_unknown_bucket():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3_client.delete_bucket_replication(Bucket=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchBucket"
    assert err["Message"] == "The specified bucket does not exist"
    assert err["BucketName"] == bucket_name


@mock_s3
def test_delete_bucket_replication_bucket_without_replication():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3_client.create_bucket(Bucket=bucket_name)
    # No-op
    s3_client.delete_bucket_replication(Bucket=bucket_name)


@mock_s3
def test_create_replication_without_versioning():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)

    with pytest.raises(ClientError) as exc:
        s3_client.put_bucket_replication(
            Bucket=bucket_name,
            ReplicationConfiguration={
                "Role": "myrole",
                "Rules": [
                    {"Destination": {"Bucket": "secondbucket"}, "Status": "Enabled"}
                ],
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequest"
    assert err["Message"] == (
        "Versioning must be 'Enabled' on the bucket to apply a replication configuration"
    )
    assert err["BucketName"] == bucket_name


@mock_s3
def test_create_and_retrieve_replication_with_single_rules():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    s3_client.put_bucket_replication(
        Bucket=bucket_name,
        ReplicationConfiguration={
            "Role": "myrole",
            "Rules": [
                {
                    "ID": "firstrule",
                    "Priority": 2,
                    "Destination": {"Bucket": "secondbucket"},
                    "Status": "Enabled",
                }
            ],
        },
    )

    config = s3_client.get_bucket_replication(Bucket=bucket_name)[
        "ReplicationConfiguration"
    ]
    assert config == {
        "Role": "myrole",
        "Rules": [
            {
                "DeleteMarkerReplication": {"Status": "Disabled"},
                "Destination": {"Bucket": "secondbucket"},
                "Filter": {"Prefix": ""},
                "ID": "firstrule",
                "Priority": 2,
                "Status": "Enabled",
            }
        ],
    }

    s3_client.delete_bucket_replication(Bucket=bucket_name)

    # Can't retrieve replication that has been deleted
    with pytest.raises(ClientError) as exc:
        s3_client.get_bucket_replication(Bucket=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ReplicationConfigurationNotFoundError"
    assert err["Message"] == "The replication configuration was not found"
    assert err["BucketName"] == bucket_name


@mock_s3
def test_create_and_retrieve_replication_with_multiple_rules():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    s3_client.put_bucket_replication(
        Bucket=bucket_name,
        ReplicationConfiguration={
            "Role": "myrole",
            "Rules": [
                {"Destination": {"Bucket": "secondbucket"}, "Status": "Enabled"},
                {
                    "ID": "secondrule",
                    "Priority": 2,
                    "Destination": {"Bucket": "thirdbucket"},
                    "Status": "Disabled",
                },
            ],
        },
    )

    config = s3_client.get_bucket_replication(Bucket=bucket_name)[
        "ReplicationConfiguration"
    ]
    assert config["Role"] == "myrole"
    rules = config["Rules"]
    assert len(rules) == 2

    first_rule = rules[0]
    assert "ID" in first_rule
    assert first_rule["Priority"] == 1
    assert first_rule["Status"] == "Enabled"
    assert first_rule["Destination"] == {"Bucket": "secondbucket"}

    second = rules[1]
    assert second["ID"] == "secondrule"
    assert second["Priority"] == 2
    assert second["Status"] == "Disabled"
    assert second["Destination"] == {"Bucket": "thirdbucket"}
