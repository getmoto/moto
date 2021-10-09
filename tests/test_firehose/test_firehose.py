"""Unit tests specific to basic Firehose Delivery Stream-related APIs."""
from unittest import SkipTest
import warnings

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_firehose
from moto import settings
from moto.core import ACCOUNT_ID
from moto.core.utils import get_random_hex
from moto.firehose.models import DeliveryStream

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


def sample_s3_dest_config():
    """Return a simple extended s3 destination configuration."""
    return {
        "RoleARN": f"arn:aws:iam::{ACCOUNT_ID}:role/firehose-test-role",
        "BucketARN": "arn:aws:s3::firehosetestbucket",
    }


@mock_firehose
def test_warnings():
    """Test features that raise a warning as they're unimplemented."""
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't capture warnings in server mode")

    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()

    # DeliveryStreamEncryption is not supported.
    stream_name = f"test_warning_{get_random_hex(6)}"
    with warnings.catch_warnings(record=True) as warn_msg:
        client.create_delivery_stream(
            DeliveryStreamName=stream_name,
            ExtendedS3DestinationConfiguration=s3_dest_config,
            DeliveryStreamEncryptionConfigurationInput={"KeyType": "AWS_OWNED_CMK"},
        )
    assert "server-side encryption enabled is not yet implemented" in str(
        warn_msg[-1].message
    )

    # Can't create a delivery stream for Splunk as it's unimplemented.
    stream_name = f"test_splunk_destination_{get_random_hex(6)}"
    with warnings.catch_warnings(record=True) as warn_msg:
        client.create_delivery_stream(
            DeliveryStreamName=stream_name,
            SplunkDestinationConfiguration={
                "HECEndpoint": "foo",
                "HECEndpointType": "foo",
                "HECToken": "foo",
                "S3Configuration": {"RoleARN": "foo", "BucketARN": "foo"},
            },
        )
    assert "Splunk destination delivery stream is not yet implemented" in str(
        warn_msg[-1].message
    )

    # Can't update a delivery stream to Splunk as it's unimplemented.
    stream_name = f"test_update_splunk_destination_{get_random_hex(6)}"
    client.create_delivery_stream(
        DeliveryStreamName=stream_name, S3DestinationConfiguration=s3_dest_config,
    )

    with warnings.catch_warnings(record=True) as warn_msg:
        client.update_destination(
            DeliveryStreamName=stream_name,
            CurrentDeliveryStreamVersionId="1",
            DestinationId="destinationId-000000000001",
            SplunkDestinationUpdate={
                "HECEndpoint": "foo",
                "HECEndpointType": "foo",
                "HECToken": "foo",
            },
        )
    assert "Splunk destination delivery stream is not yet implemented" in str(
        warn_msg[-1].message
    )


@mock_firehose
def test_create_delivery_stream_failures():
    """Test errors invoking create_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()
    failure_name = f"test_failure_{get_random_hex(6)}"

    # Create too many streams.
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

    # Create a stream with the same name as an existing stream.
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

    # At least one destination configuration is required.
    with pytest.raises(ClientError) as exc:
        client.create_delivery_stream(DeliveryStreamName=f"{failure_name}_2manyconfigs")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        "Exactly one destination configuration is supported for a Firehose"
        in err["Message"]
    )

    # Provide a Kinesis source configuration, but use DirectPut stream type.
    with pytest.raises(ClientError) as exc:
        client.create_delivery_stream(
            DeliveryStreamName=f"{failure_name}_bad_source_type",
            DeliveryStreamType="DirectPut",
            KinesisStreamSourceConfiguration={
                "KinesisStreamARN": "kinesis_test_ds",
                "RoleARN": "foo",
            },
            ExtendedS3DestinationConfiguration=s3_dest_config,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        "KinesisSourceStreamConfig is only applicable for "
        "KinesisStreamAsSource stream type" in err["Message"]
    )


@mock_firehose
def test_delete_delivery_stream():
    """Test successful and failed invocations of delete_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()
    stream_name = f"test_delete_{get_random_hex(6)}"

    # Create a couple of streams to test with.
    for idx in range(5):
        client.create_delivery_stream(
            DeliveryStreamName=f"{stream_name}-{idx}",
            S3DestinationConfiguration=s3_dest_config,
        )

    # Attempt to delete a non-existent stream.
    with pytest.raises(ClientError) as exc:
        client.delete_delivery_stream(DeliveryStreamName="foo")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Firehose foo under account {ACCOUNT_ID} not found." in err["Message"]

    # Delete one stream, verify the remaining exist.
    client.delete_delivery_stream(DeliveryStreamName=f"{stream_name}-0")
    hoses = client.list_delivery_streams()
    assert len(hoses["DeliveryStreamNames"]) == 4
    expected_list = [f"{stream_name}-{x}" for x in range(1, 5)]
    assert hoses["DeliveryStreamNames"] == expected_list

    # Delete all streams, verify there are no more streams.
    for idx in range(1, 5):
        client.delete_delivery_stream(DeliveryStreamName=f"{stream_name}-{idx}")
    hoses = client.list_delivery_streams()
    assert len(hoses["DeliveryStreamNames"]) == 0
    assert hoses["DeliveryStreamNames"] == []


@mock_firehose
def test_describe_delivery_stream():
    """Test successful, failed invocations of describe_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()
    stream_name = f"test_describe_{get_random_hex(6)}"
    role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/testrole"

    # Create delivery stream with S3 destination, kinesis type and source
    # for testing purposes.
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        DeliveryStreamType="KinesisStreamAsSource",
        KinesisStreamSourceConfiguration={
            "KinesisStreamARN": f"arn:aws:kinesis:{TEST_REGION}:{ACCOUNT_ID}:stream/test-datastream",
            "RoleARN": role_arn,
        },
        S3DestinationConfiguration=s3_dest_config,
    )

    labels_with_kinesis_source = {
        "DeliveryStreamName",
        "DeliveryStreamARN",
        "DeliveryStreamStatus",
        "DeliveryStreamType",
        "VersionId",
        "CreateTimestamp",
        "Source",
        "Destinations",
        "LastUpdateTimestamp",
        "HasMoreDestinations",
    }

    # Verify the created fields are as expected.
    results = client.describe_delivery_stream(DeliveryStreamName=stream_name)
    description = results["DeliveryStreamDescription"]
    assert set(description.keys()) == labels_with_kinesis_source
    assert description["DeliveryStreamName"] == stream_name
    assert (
        description["DeliveryStreamARN"]
        == f"arn:aws:firehose:{TEST_REGION}:{ACCOUNT_ID}:/delivery_stream/{stream_name}"
    )
    assert description["DeliveryStreamStatus"] == "ACTIVE"
    assert description["DeliveryStreamType"] == "KinesisStreamAsSource"
    assert description["VersionId"] == "1"
    assert (
        description["Source"]["KinesisStreamSourceDescription"]["RoleARN"] == role_arn
    )
    assert len(description["Destinations"]) == 1
    assert set(description["Destinations"][0].keys()) == {
        "S3DestinationDescription",
        "DestinationId",
    }

    # Update destination with ExtendedS3.
    client.update_destination(
        DeliveryStreamName=stream_name,
        CurrentDeliveryStreamVersionId="1",
        DestinationId="destinationId-000000000001",
        ExtendedS3DestinationUpdate=s3_dest_config,
    )

    # Verify the created fields are as expected.  There should be one
    # destination with two destination types.  The last update timestamp
    # should be present and the version number updated.
    results = client.describe_delivery_stream(DeliveryStreamName=stream_name)
    description = results["DeliveryStreamDescription"]
    assert set(description.keys()) == labels_with_kinesis_source | {
        "LastUpdateTimestamp"
    }
    assert description["DeliveryStreamName"] == stream_name
    assert (
        description["DeliveryStreamARN"]
        == f"arn:aws:firehose:{TEST_REGION}:{ACCOUNT_ID}:/delivery_stream/{stream_name}"
    )
    assert description["DeliveryStreamStatus"] == "ACTIVE"
    assert description["DeliveryStreamType"] == "KinesisStreamAsSource"
    assert description["VersionId"] == "2"
    assert (
        description["Source"]["KinesisStreamSourceDescription"]["RoleARN"] == role_arn
    )
    assert len(description["Destinations"]) == 1
    assert set(description["Destinations"][0].keys()) == {
        "S3DestinationDescription",
        "DestinationId",
        "ExtendedS3DestinationDescription",
    }

    # Update ExtendedS3 destination with a few different values.
    client.update_destination(
        DeliveryStreamName=stream_name,
        CurrentDeliveryStreamVersionId="2",
        DestinationId="destinationId-000000000001",
        ExtendedS3DestinationUpdate={
            "RoleARN": role_arn,
            "BucketARN": "arn:aws:s3:::testbucket",
            # IntervalInSeconds increased from 300 to 700.
            "BufferingHints": {"IntervalInSeconds": 700, "SizeInMBs": 5},
        },
    )
    results = client.describe_delivery_stream(DeliveryStreamName=stream_name)
    description = results["DeliveryStreamDescription"]
    assert description["VersionId"] == "3"
    assert len(description["Destinations"]) == 1
    destination = description["Destinations"][0]
    assert (
        destination["ExtendedS3DestinationDescription"]["BufferingHints"][
            "IntervalInSeconds"
        ]
        == 700
    )

    # Verify S3 was added when ExtendedS3 was added.
    assert set(destination.keys()) == {
        "S3DestinationDescription",
        "DestinationId",
        "ExtendedS3DestinationDescription",
    }
    assert set(destination["S3DestinationDescription"].keys()) == {
        "RoleARN",
        "BucketARN",
        "BufferingHints",
    }

    # Update delivery stream from ExtendedS3 to S3.
    client.update_destination(
        DeliveryStreamName=stream_name,
        CurrentDeliveryStreamVersionId="3",
        DestinationId="destinationId-000000000001",
        S3DestinationUpdate={
            "RoleARN": role_arn,
            "BucketARN": "arn:aws:s3:::testbucket",
            # IntervalInSeconds decreased from 700 to 500.
            "BufferingHints": {"IntervalInSeconds": 500, "SizeInMBs": 5},
        },
    )
    results = client.describe_delivery_stream(DeliveryStreamName=stream_name)
    description = results["DeliveryStreamDescription"]
    assert description["VersionId"] == "4"
    assert len(description["Destinations"]) == 1
    assert set(description["Destinations"][0].keys()) == {
        "S3DestinationDescription",
        "ExtendedS3DestinationDescription",
        "DestinationId",
    }
    destination = description["Destinations"][0]
    assert (
        destination["ExtendedS3DestinationDescription"]["BufferingHints"][
            "IntervalInSeconds"
        ]
        == 500
    )
    assert (
        destination["S3DestinationDescription"]["BufferingHints"]["IntervalInSeconds"]
        == 500
    )


@mock_firehose
def test_list_delivery_streams():
    """Test successful and failed invocations of list_delivery_streams()."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()
    stream_name = f"test_list_{get_random_hex(6)}"

    # Create a couple of streams of both types to test with.
    for idx in range(5):
        client.create_delivery_stream(
            DeliveryStreamName=f"{stream_name}-{idx}",
            DeliveryStreamType="DirectPut",
            S3DestinationConfiguration=s3_dest_config,
        )
    for idx in range(5):
        client.create_delivery_stream(
            DeliveryStreamName=f"{stream_name}-{idx+5}",
            DeliveryStreamType="KinesisStreamAsSource",
            S3DestinationConfiguration=s3_dest_config,
        )

    # Verify limit works.
    hoses = client.list_delivery_streams(Limit=1)
    assert len(hoses["DeliveryStreamNames"]) == 1
    assert hoses["DeliveryStreamNames"] == [f"{stream_name}-0"]
    assert hoses["HasMoreDeliveryStreams"] is True

    hoses = client.list_delivery_streams(Limit=10)
    assert len(hoses["DeliveryStreamNames"]) == 10
    assert hoses["HasMoreDeliveryStreams"] is False

    # Verify delivery_stream_type works as a filter.
    hoses = client.list_delivery_streams(DeliveryStreamType="DirectPut")
    assert len(hoses["DeliveryStreamNames"]) == 5
    expected_directput_list = [f"{stream_name}-{x}" for x in range(5)]
    assert hoses["DeliveryStreamNames"] == expected_directput_list
    assert hoses["HasMoreDeliveryStreams"] is False

    hoses = client.list_delivery_streams(DeliveryStreamType="KinesisStreamAsSource")
    assert len(hoses["DeliveryStreamNames"]) == 5
    expected_kinesis_stream_list = [f"{stream_name}-{x+5}" for x in range(5)]
    assert hoses["DeliveryStreamNames"] == expected_kinesis_stream_list
    assert hoses["HasMoreDeliveryStreams"] is False

    # Verify exclusive_start_delivery_stream_name returns truncated list.
    hoses = client.list_delivery_streams(
        ExclusiveStartDeliveryStreamName=f"{stream_name}-5"
    )
    assert len(hoses["DeliveryStreamNames"]) == 4
    expected_stream_list = [f"{stream_name}-{x+5}" for x in range(1, 5)]
    assert hoses["DeliveryStreamNames"] == expected_stream_list
    assert hoses["HasMoreDeliveryStreams"] is False

    hoses = client.list_delivery_streams(
        ExclusiveStartDeliveryStreamName=f"{stream_name}-9"
    )
    assert len(hoses["DeliveryStreamNames"]) == 0
    assert hoses["HasMoreDeliveryStreams"] is False

    # boto3 ignores bad stream names for ExclusiveStartDeliveryStreamName.
    hoses = client.list_delivery_streams(ExclusiveStartDeliveryStreamName="foo")
    assert len(hoses["DeliveryStreamNames"]) == 10
    assert (
        hoses["DeliveryStreamNames"]
        == expected_directput_list + expected_kinesis_stream_list
    )
    assert hoses["HasMoreDeliveryStreams"] is False

    # Verify no parameters returns entire list.
    client.list_delivery_streams()
    assert len(hoses["DeliveryStreamNames"]) == 10
    assert (
        hoses["DeliveryStreamNames"]
        == expected_directput_list + expected_kinesis_stream_list
    )
    assert hoses["HasMoreDeliveryStreams"] is False


@mock_firehose
def test_update_destination():
    """Test successful, failed invocations of update_destination()."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()

    # Can't update a non-existent stream.
    with pytest.raises(ClientError) as exc:
        client.update_destination(
            DeliveryStreamName="foo",
            CurrentDeliveryStreamVersionId="1",
            DestinationId="destinationId-000000000001",
            ExtendedS3DestinationUpdate=s3_dest_config,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Firehose foo under accountId {ACCOUNT_ID} not found" in err["Message"]

    # Create a delivery stream for testing purposes.
    stream_name = f"test_update_{get_random_hex(6)}"
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        DeliveryStreamType="DirectPut",
        S3DestinationConfiguration=s3_dest_config,
    )

    # Only one destination configuration is allowed.
    with pytest.raises(ClientError) as exc:
        client.update_destination(
            DeliveryStreamName=stream_name,
            CurrentDeliveryStreamVersionId="1",
            DestinationId="destinationId-000000000001",
            S3DestinationUpdate=s3_dest_config,
            ExtendedS3DestinationUpdate=s3_dest_config,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        "Exactly one destination configuration is supported for a Firehose"
        in err["Message"]
    )

    # Can't update to/from http or ES.
    with pytest.raises(ClientError) as exc:
        client.update_destination(
            DeliveryStreamName=stream_name,
            CurrentDeliveryStreamVersionId="1",
            DestinationId="destinationId-000000000001",
            HttpEndpointDestinationUpdate={
                "EndpointConfiguration": {"Url": "https://google.com"},
                "RetryOptions": {"DurationInSeconds": 100},
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgumentException"
    assert (
        "Changing the destination type to or from HttpEndpoint is not "
        "supported at this time"
    ) in err["Message"]


@mock_firehose
def test_lookup_name_from_arn():
    """Test delivery stream instance can be retrieved given ARN.

    This won't work in TEST_SERVER_MODE as this script won't have access
    to 'firehose_backends'.
    """
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't access firehose_backend in server mode")

    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()
    stream_name = "test_lookup"

    arn = client.create_delivery_stream(
        DeliveryStreamName=stream_name, S3DestinationConfiguration=s3_dest_config,
    )["DeliveryStreamARN"]

    from moto.firehose.models import (  # pylint: disable=import-outside-toplevel
        firehose_backends,
    )

    delivery_stream = firehose_backends[TEST_REGION].lookup_name_from_arn(arn)
    assert delivery_stream.delivery_stream_arn == arn
    assert delivery_stream.delivery_stream_name == stream_name
