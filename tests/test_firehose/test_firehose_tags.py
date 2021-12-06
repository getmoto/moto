"""Unit tests verifying tag-related delivery stream APIs."""
import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_firehose
from moto.core import ACCOUNT_ID
from moto.core.utils import get_random_hex
from moto.firehose.models import MAX_TAGS_PER_DELIVERY_STREAM
from tests.test_firehose.test_firehose import TEST_REGION
from tests.test_firehose.test_firehose import sample_s3_dest_config


@mock_firehose
def test_list_tags_for_delivery_stream():
    """Test invocations of list_tags_for_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    stream_name = f"test_list_tags_{get_random_hex(6)}"

    number_of_tags = 50
    tags = [{"Key": f"{x}_k", "Value": f"{x}_v"} for x in range(1, number_of_tags + 1)]

    # Create a delivery stream to work with.
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        S3DestinationConfiguration=sample_s3_dest_config(),
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
def test_tag_delivery_stream():
    """Test successful, failed invocations of tag_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)

    # Create a delivery stream for testing purposes.
    stream_name = f"test_tags_{get_random_hex(6)}"
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        ExtendedS3DestinationConfiguration=sample_s3_dest_config(),
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
    added_tags = [
        {"Key": f"{x}", "Value": f"{x}"} for x in range(MAX_TAGS_PER_DELIVERY_STREAM)
    ]
    client.tag_delivery_stream(DeliveryStreamName=stream_name, Tags=added_tags)
    results = client.list_tags_for_delivery_stream(DeliveryStreamName=stream_name)
    assert len(results["Tags"]) == MAX_TAGS_PER_DELIVERY_STREAM
    assert results["Tags"] == added_tags


@mock_firehose
def test_untag_delivery_stream():
    """Test successful, failed invocations of untag_delivery_stream()."""
    client = boto3.client("firehose", region_name=TEST_REGION)

    # Create a delivery stream for testing purposes.
    stream_name = f"test_untag_{get_random_hex(6)}"
    tag_list = [
        {"Key": "one", "Value": "1"},
        {"Key": "two", "Value": "2"},
        {"Key": "three", "Value": "3"},
    ]
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        ExtendedS3DestinationConfiguration=sample_s3_dest_config(),
        Tags=tag_list,
    )

    # Untag all of the tags.  Verify there are no more tags.
    tag_keys = [x["Key"] for x in tag_list]
    client.untag_delivery_stream(DeliveryStreamName=stream_name, TagKeys=tag_keys)
    results = client.list_tags_for_delivery_stream(DeliveryStreamName=stream_name)
    assert not results["Tags"]
    assert not results["HasMoreTags"]
