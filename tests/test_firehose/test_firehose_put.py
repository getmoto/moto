"""Unit tests verifying put-related delivery stream APIs."""

import re

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.moto_api._internal import mock_random
from tests.test_firehose.test_firehose import TEST_REGION, sample_s3_dest_config
from tests.test_firehose.test_firehose_destination_types import (
    create_redshift_delivery_stream,
)

S3_LOCATION_CONSTRAINT = "us-west-1"


@mock_aws
def test_put_record_redshift_destination():
    """Test invocations of put_record() to a Redshift destination.

    At the moment, for Redshift or Elasticsearch destinations, the data
    is just thrown away
    """
    client = boto3.client("firehose", region_name=TEST_REGION)

    stream_name = f"test_put_record_{mock_random.get_random_hex(6)}"
    create_redshift_delivery_stream(client, stream_name)
    result = client.put_record(
        DeliveryStreamName=stream_name, Record={"Data": "some test data"}
    )
    assert set(result.keys()) == {"RecordId", "Encrypted", "ResponseMetadata"}


@mock_aws
def test_put_record_batch_redshift_destination():
    """Test invocations of put_record_batch() to a Redshift destination.

    At the moment, for Redshift or Elasticsearch destinations, the data
    is just thrown away
    """
    client = boto3.client("firehose", region_name=TEST_REGION)

    stream_name = f"test_put_record_{mock_random.get_random_hex(6)}"
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


@mock_aws
def test_put_record_http_destination():
    """Test invocations of put_record() to a Http destination."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()

    stream_name = f"test_put_record_{mock_random.get_random_hex(6)}"
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


@mock_aws
def test_put_record_batch_http_destination():
    """Test invocations of put_record_batch() to a Http destination."""
    client = boto3.client("firehose", region_name=TEST_REGION)
    s3_dest_config = sample_s3_dest_config()

    stream_name = f"test_put_record_{mock_random.get_random_hex(6)}"
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


@mock_aws
def test_put_record_batch_extended_s3_destination():
    """Test invocations of put_record_batch() to a S3 destination."""
    client = boto3.client("firehose", region_name=TEST_REGION)

    # Create a S3 bucket.
    bucket_name = "firehosetestbucket"
    s3_client = boto3.client("s3", region_name=TEST_REGION)
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": S3_LOCATION_CONSTRAINT},
    )

    stream_name = f"test_put_record_{mock_random.get_random_hex(6)}"
    client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        ExtendedS3DestinationConfiguration={
            "RoleARN": f"arn:aws:iam::{ACCOUNT_ID}:role/firehose-test-role",
            "BucketARN": f"arn:aws:s3::{bucket_name}",
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

    # Pull data from S3 bucket.
    bucket_objects = s3_client.list_objects_v2(Bucket=bucket_name)
    response = s3_client.get_object(
        Bucket=bucket_name, Key=bucket_objects["Contents"][0]["Key"]
    )
    assert response["Body"].read() == b"onetwothree"
    assert re.match(
        r"^[0-9]{4}/[0-9]{2}/[0-9]{2}/[0-9]{2}/", bucket_objects["Contents"][0]["Key"]
    )
