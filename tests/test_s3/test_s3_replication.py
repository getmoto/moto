import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_s3
from uuid import uuid4

DEFAULT_REGION_NAME = "us-east-1"


@mock_s3
def test_get_bucket_replication_for_unexisting_bucket():
    bucket_name = str(uuid4())
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3.get_bucket_replication(Bucket=bucket_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchBucket")
    err["Message"].should.equal("The specified bucket does not exist")
    err["BucketName"].should.equal(bucket_name)


@mock_s3
def test_get_bucket_replication_bucket_without_replication():
    bucket_name = str(uuid4())
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)

    with pytest.raises(ClientError) as exc:
        s3.get_bucket_replication(Bucket=bucket_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ReplicationConfigurationNotFoundError")
    err["Message"].should.equal("The replication configuration was not found")
    err["BucketName"].should.equal(bucket_name)


@mock_s3
def test_delete_bucket_replication_unknown_bucket():
    bucket_name = str(uuid4())
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    with pytest.raises(ClientError) as exc:
        s3.delete_bucket_replication(Bucket=bucket_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchBucket")
    err["Message"].should.equal("The specified bucket does not exist")
    err["BucketName"].should.equal(bucket_name)


@mock_s3
def test_delete_bucket_replication_bucket_without_replication():
    bucket_name = str(uuid4())
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3.create_bucket(Bucket=bucket_name)
    # No-op
    s3.delete_bucket_replication(Bucket=bucket_name)


@mock_s3
def test_create_replication_without_versioning():
    bucket_name = str(uuid4())
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)

    with pytest.raises(ClientError) as exc:
        s3.put_bucket_replication(
            Bucket=bucket_name,
            ReplicationConfiguration={
                "Role": "myrole",
                "Rules": [
                    {"Destination": {"Bucket": "secondbucket"}, "Status": "Enabled"}
                ],
            },
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidRequest")
    err["Message"].should.equal(
        "Versioning must be 'Enabled' on the bucket to apply a replication configuration"
    )
    err["BucketName"].should.equal(bucket_name)


@mock_s3
def test_create_and_retrieve_replication_with_single_rules():
    bucket_name = str(uuid4())
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    s3.put_bucket_replication(
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

    config = s3.get_bucket_replication(Bucket=bucket_name)["ReplicationConfiguration"]
    config.should.equal(
        {
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
    )

    s3.delete_bucket_replication(Bucket=bucket_name)

    # Can't retrieve replication that has been deleted
    with pytest.raises(ClientError) as exc:
        s3.get_bucket_replication(Bucket=bucket_name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ReplicationConfigurationNotFoundError")
    err["Message"].should.equal("The replication configuration was not found")
    err["BucketName"].should.equal(bucket_name)


@mock_s3
def test_create_and_retrieve_replication_with_multiple_rules():
    bucket_name = str(uuid4())
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    s3.put_bucket_replication(
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

    config = s3.get_bucket_replication(Bucket=bucket_name)["ReplicationConfiguration"]
    config.should.have.key("Role").equal("myrole")
    rules = config["Rules"]
    rules.should.have.length_of(2)

    first_rule = rules[0]
    first_rule.should.have.key("ID")
    first_rule.should.have.key("Priority").equal(1)
    first_rule.should.have.key("Status").equal("Enabled")
    first_rule.should.have.key("Destination").equal({"Bucket": "secondbucket"})

    second = rules[1]
    second.should.have.key("ID").equal("secondrule")
    second.should.have.key("Priority").equal(2)
    second.should.have.key("Status").equal("Disabled")
    second.should.have.key("Destination").equal({"Bucket": "thirdbucket"})
