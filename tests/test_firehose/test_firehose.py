"""Unit tests specific to the Firehose Delivery Stream-related APIs."""
import boto3
from botocore.exceptions import ClientError
import pytest
import sure  # noqa pylint: disable=unused-import

from moto import mock_firehose
from moto import settings
from moto.core import ACCOUNT_ID
from moto.core.utils import get_random_hex
from moto.firehose.models import DeliveryStream
from moto.firehose.models import MAX_TAGS_PER_DELIVERY_STREAM
from tests.test_firehose.test_firehose_destination_types import (
    create_redshift_delivery_stream,
)

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
    with pytest.raises(NotImplementedError):
        client.create_delivery_stream(
            DeliveryStreamName=failure_name,
            S3DestinationConfiguration=s3_dest_config,
            DeliveryStreamEncryptionConfigurationInput={"KeyType": "AWS_OWNED_CMK"},
        )
    with pytest.raises(NotImplementedError):
        client.create_delivery_stream(
            DeliveryStreamName=failure_name,
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
def test_list_tags_for_delivery_stream():
    """Test invocations of list_tags_for_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()
    stream_name = f"test_list_tags_{get_random_hex(6)}"

    number_of_tags = 50
    tags = [{"Key": f"{x}_k", "Value": f"{x}_v"} for x in range(1, number_of_tags + 1)]

    # Create a delivery stream to work with.
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        S3DestinationConfiguration=s3_dest_config,
        Tags=tags,
    )

    # Verify limit works.
    result = client.list_tags_for_delivery_stream(
        DeliveryStreamName=stream_name, Limit=1
    )
    assert len(result["Tags"]) == 1
    assert result["Tags"] == [{"Key": "1_k", "Value": "1_v"}]
    assert result["HasMoreTags"] is True

    result = client.list_tags_for_delivery_stream(
        DeliveryStreamName=stream_name, Limit=number_of_tags
    )
    assert len(result["Tags"]) == number_of_tags
    assert result["HasMoreTags"] is False

    # Verify exclusive_start_tag_key returns truncated list.
    result = client.list_tags_for_delivery_stream(
        DeliveryStreamName=stream_name, ExclusiveStartTagKey="30_k"
    )
    assert len(result["Tags"]) == number_of_tags - 30
    expected_tags = [
        {"Key": f"{x}_k", "Value": f"{x}_v"} for x in range(31, number_of_tags + 1)
    ]
    assert result["Tags"] == expected_tags
    assert result["HasMoreTags"] is False

    result = client.list_tags_for_delivery_stream(
        DeliveryStreamName=stream_name, ExclusiveStartTagKey=f"{number_of_tags}_k"
    )
    assert len(result["Tags"]) == 0
    assert result["HasMoreTags"] is False

    # boto3 ignores bad stream names for ExclusiveStartTagKey.
    result = client.list_tags_for_delivery_stream(
        DeliveryStreamName=stream_name, ExclusiveStartTagKey="foo"
    )
    assert len(result["Tags"]) == number_of_tags
    assert result["Tags"] == tags
    assert result["HasMoreTags"] is False

    # Verify no parameters returns entire list.
    client.list_tags_for_delivery_stream(DeliveryStreamName=stream_name)
    assert len(result["Tags"]) == number_of_tags
    assert result["Tags"] == tags
    assert result["HasMoreTags"] is False


@mock_firehose
def test_put_record_redshift_destination():
    """Test invocations of put_record() to a Redshift destination.

    At the moment, for Redshift or Elasticsearch destinations, the data
    is just thrown away
    """
    client = boto3.client("firehose", region_name=TEST_REGION)

    stream_name = f"test_put_record_{get_random_hex(6)}"
    create_redshift_delivery_stream(client, stream_name)
    result = client.put_record(
        DeliveryStreamName=stream_name, Record={"Data": "some test data"}
    )
    assert set(result.keys()) == {"RecordId", "Encrypted", "ResponseMetadata"}


@mock_firehose
def test_put_record_batch_redshift_destination():
    """Test invocations of put_record_batch() to a Redshift destination.

    At the moment, for Redshift or Elasticsearch destinations, the data
    is just thrown away
    """
    client = boto3.client("firehose", region_name=TEST_REGION)

    stream_name = f"test_put_record_{get_random_hex(6)}"
    create_redshift_delivery_stream(client, stream_name)
    records = [{"Data": "one"}, {"Data": "two"}, {"Data": "three"}]
    result = client.put_record_batch(DeliveryStreamName=stream_name, Records=records)
    assert set(result.keys()) == {
        "FailedPutCount",
        "Encrypted",
        "RequestResponses",
        "ResponseMetadata",
    }
    assert result["FailedPutCount"] == 0
    assert result["Encrypted"] is False
    for response in result["RequestResponses"]:
        assert set(response.keys()) == {"RecordId"}


@mock_firehose
def test_put_record_http_destination():
    """Test invocations of put_record() to a Http destination."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()

    stream_name = f"test_put_record_{get_random_hex(6)}"
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        HttpEndpointDestinationConfiguration={
            "EndpointConfiguration": {"Url": "https://google.com"},
            "S3Configuration": s3_dest_config,
        },
    )
    result = client.put_record(
        DeliveryStreamName=stream_name, Record={"Data": "some test data"}
    )
    assert set(result.keys()) == {"RecordId", "Encrypted", "ResponseMetadata"}


@mock_firehose
def test_put_record_batch_http_destination():
    """Test invocations of put_record_batch() to a Http destination."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()

    stream_name = f"test_put_record_{get_random_hex(6)}"
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        HttpEndpointDestinationConfiguration={
            "EndpointConfiguration": {"Url": "https://google.com"},
            "S3Configuration": s3_dest_config,
        },
    )
    records = [{"Data": "one"}, {"Data": "two"}, {"Data": "three"}]
    result = client.put_record_batch(DeliveryStreamName=stream_name, Records=records)
    assert set(result.keys()) == {
        "FailedPutCount",
        "Encrypted",
        "RequestResponses",
        "ResponseMetadata",
    }
    assert result["FailedPutCount"] == 0
    assert result["Encrypted"] is False
    for response in result["RequestResponses"]:
        assert set(response.keys()) == {"RecordId"}


@mock_firehose
def test_tag_delivery_stream():
    """Test successful, failed invocations of tag_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)

    # Create a delivery stream for testing purposes.
    s3_dest_config = sample_s3_dest_config()
    stream_name = f"test_tags_{get_random_hex(6)}"
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        ExtendedS3DestinationConfiguration=s3_dest_config,
    )

    # Unknown stream name.
    unknown_name = "foo"
    with pytest.raises(ClientError) as exc:
        client.tag_delivery_stream(
            DeliveryStreamName=unknown_name, Tags=[{"Key": "foo", "Value": "bar"}]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        f"Firehose {unknown_name} under account {ACCOUNT_ID} not found"
        in err["Message"]
    )

    # Too many tags.
    with pytest.raises(ClientError) as exc:
        client.tag_delivery_stream(
            DeliveryStreamName=stream_name,
            Tags=[{"Key": f"{x}", "Value": f"{x}"} for x in range(51)],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        f"failed to satisify contstraint: Member must have length "
        f"less than or equal to {MAX_TAGS_PER_DELIVERY_STREAM}"
    ) in err["Message"]

    # Bad tags.
    with pytest.raises(ClientError) as exc:
        client.tag_delivery_stream(
            DeliveryStreamName=stream_name, Tags=[{"Key": "foo!", "Value": "bar"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        "1 validation error detected: Value 'foo!' at 'tags.1.member.key' "
        "failed to satisfy constraint: Member must satisfy regular "
        "expression pattern"
    ) in err["Message"]

    # Successful addition of tags.
    added_tags = [{"Key": f"{x}", "Value": f"{x}"} for x in range(10)]
    client.tag_delivery_stream(DeliveryStreamName=stream_name, Tags=added_tags)
    results = client.list_tags_for_delivery_stream(DeliveryStreamName=stream_name)
    assert len(results["Tags"]) == 10
    assert results["Tags"] == added_tags


@mock_firehose
def test_untag_delivery_stream():
    """Test successful, failed invocations of untag_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)

    # Create a delivery stream for testing purposes.
    s3_dest_config = sample_s3_dest_config()
    stream_name = f"test_untag_{get_random_hex(6)}"
    tag_list = [
        {"Key": "one", "Value": "1"},
        {"Key": "two", "Value": "2"},
        {"Key": "three", "Value": "3"},
    ]
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        ExtendedS3DestinationConfiguration=s3_dest_config,
        Tags=tag_list,
    )

    # Untag all of the tags.  Verify there are no more tags.
    tag_keys = [x["Key"] for x in tag_list]
    client.untag_delivery_stream(DeliveryStreamName=stream_name, TagKeys=tag_keys)
    results = client.list_tags_for_delivery_stream(DeliveryStreamName=stream_name)
    assert not results["Tags"]
    assert not results["HasMoreTags"]


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
