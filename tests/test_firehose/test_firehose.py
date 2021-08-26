"""Unit tests specific to the Firehose Delivery Stream-related APIs.

 These APIs include:
   create_delivery_stream
   describe_delivery_stream
   delete_delivery_stream
   list_delivery_streams
"""
import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_firehose
from moto.core import ACCOUNT_ID
from moto.core.utils import get_random_hex
from moto.firehose.models import DeliveryStream
from moto import settings

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


def sample_s3_dest_config():
    """Return a simple extended s3 destination configuration."""
    return {
        "RoleARN": f"arn:aws:iam::{ACCOUNT_ID}:role/firehose-test-role",
        "BucketARN": "arn:aws:s3::firehosetestbucket",
    }


@mock_firehose
def test_create_delivery_stream_unimplemented():
    """Test use of umimplemented create_delivery_stream() features."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()
    failure_name = f"test_failure_{get_random_hex(6)}"

    # Verify that unimplemented features are noted and reported.
    with pytest.raises(NotImplementedError) as exc:
        client.create_delivery_stream(
            DeliveryStreamName=failure_name,
            S3DestinationConfiguration=s3_dest_config,
            DeliveryStreamEncryptionConfigurationInput={"KeyType": "AWS_OWNED_CMK"},
        )
    with pytest.raises(NotImplementedError) as exc:
        client.create_delivery_stream(
            DeliveryStreamName=failure_name,
            S3DestinationConfiguration=s3_dest_config,
            RedshiftDestinationConfiguration={
                "RoleARN": "foo",
                "ClusterJDBCURL": "foo",
                "CopyCommand": {"DataTableName": "foo"},
                "Username": "foo",
                "Password": "foobar",
                "S3Configuration": {"RoleARN": "foo", "BucketARN": "foo"},
            },
        )
    with pytest.raises(NotImplementedError) as exc:
        client.create_delivery_stream(
            DeliveryStreamName=failure_name,
            S3DestinationConfiguration=s3_dest_config,
            ElasticsearchDestinationConfiguration={
                "RoleARN": "foo",
                "IndexName": "foo",
                "S3Configuration": {"RoleARN": "foo", "BucketARN": "foo"},
            },
        )
    with pytest.raises(NotImplementedError) as exc:
        client.create_delivery_stream(
            DeliveryStreamName=failure_name,
            S3DestinationConfiguration=s3_dest_config,
            SplunkDestinationConfiguration={
                "HECEndpoint": "foo",
                "HECEndpointType": "foo",
                "HECToken": "foo",
                "S3Configuration": {"RoleARN": "foo", "BucketARN": "foo"},
            },
        )


@mock_firehose
def test_create_delivery_stream_failures():
    """Test errors invoking create_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()
    failure_name = f"test_failure_{get_random_hex(6)}"

    for idx in range(DeliveryStream.MAX_STREAMS_PER_REGION):
        client.create_delivery_stream(
            DeliveryStreamName=f"{failure_name}_{idx}",
            ExtendedS3DestinationConfiguration=s3_dest_config,
        )

    with pytest.raises(ClientError) as exc:
        client.create_delivery_stream(
            DeliveryStreamName=f"{failure_name}_99",
            ExtendedS3DestinationConfiguration=s3_dest_config,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "LimitExceededException"
    assert "You have already consumed your firehose quota" in err["Message"]

    # Free up the memory from the limits test.
    for idx in range(DeliveryStream.MAX_STREAMS_PER_REGION):
        client.delete_delivery_stream(DeliveryStreamName=f"{failure_name}_{idx}")

    # Create a hose with the same name as an existing hose.
    client.create_delivery_stream(
        DeliveryStreamName=f"{failure_name}",
        ExtendedS3DestinationConfiguration=s3_dest_config,
    )
    with pytest.raises(ClientError) as exc:
        client.create_delivery_stream(
            DeliveryStreamName=f"{failure_name}",
            ExtendedS3DestinationConfiguration=s3_dest_config,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceInUseException"
    assert (
        f"Firehose {failure_name} under accountId {ACCOUNT_ID} already exists"
        in err["Message"]
    )

    # Only one destination configuration is allowed.
    with pytest.raises(ClientError) as exc:
        client.create_delivery_stream(
            DeliveryStreamName=f"{failure_name}_2manyconfigs",
            ExtendedS3DestinationConfiguration=s3_dest_config,
            HttpEndpointDestinationConfiguration={
                "EndpointConfiguration": {"Url": "google.com"},
                "S3Configuration": {"RoleARN": "foo", "BucketARN": "foo"},
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        "Exactly one destination configuration is supported for a Firehose"
        in err["Message"]
    )


@mock_firehose
def test_create_delivery_stream_successes():
    """Test successful invocation of create_delivery_stream()."""
    pass


@mock_firehose
def test_delete_delivery_stream():
    pass


@mock_firehose
def test_describe_delivery_stream():
    pass


@mock_firehose
def test_list_delivery_streams():
    pass
