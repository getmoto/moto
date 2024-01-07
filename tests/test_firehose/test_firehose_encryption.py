from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from .test_firehose import sample_s3_dest_config


@mock_aws
def test_firehose_without_encryption():
    client = boto3.client("firehose", region_name="us-east-2")
    name = str(uuid4())[0:6]
    client.create_delivery_stream(
        DeliveryStreamName=name,
        ExtendedS3DestinationConfiguration=sample_s3_dest_config(),
    )

    resp = client.describe_delivery_stream(DeliveryStreamName=name)[
        "DeliveryStreamDescription"
    ]
    assert "DeliveryStreamEncryptionConfiguration" not in resp

    client.start_delivery_stream_encryption(
        DeliveryStreamName=name,
        DeliveryStreamEncryptionConfigurationInput={"KeyType": "AWS_OWNED_CMK"},
    )

    stream = client.describe_delivery_stream(DeliveryStreamName=name)[
        "DeliveryStreamDescription"
    ]
    assert stream["DeliveryStreamEncryptionConfiguration"] == {
        "KeyType": "AWS_OWNED_CMK",
        "Status": "ENABLED",
    }


@mock_aws
def test_firehose_with_encryption():
    client = boto3.client("firehose", region_name="us-east-2")
    name = str(uuid4())[0:6]
    client.create_delivery_stream(
        DeliveryStreamName=name,
        ExtendedS3DestinationConfiguration=sample_s3_dest_config(),
        DeliveryStreamEncryptionConfigurationInput={"KeyType": "AWS_OWNED_CMK"},
    )

    stream = client.describe_delivery_stream(DeliveryStreamName=name)[
        "DeliveryStreamDescription"
    ]
    assert stream["DeliveryStreamEncryptionConfiguration"] == {
        "KeyType": "AWS_OWNED_CMK"
    }

    client.stop_delivery_stream_encryption(DeliveryStreamName=name)

    stream = client.describe_delivery_stream(DeliveryStreamName=name)[
        "DeliveryStreamDescription"
    ]
    assert stream["DeliveryStreamEncryptionConfiguration"]["Status"] == "DISABLED"


@mock_aws
def test_start_encryption_on_unknown_stream():
    client = boto3.client("firehose", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.start_delivery_stream_encryption(
            DeliveryStreamName="?",
            DeliveryStreamEncryptionConfigurationInput={"KeyType": "AWS_OWNED_CMK"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Firehose ? under account 123456789012 not found."


@mock_aws
def test_stop_encryption_on_unknown_stream():
    client = boto3.client("firehose", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.stop_delivery_stream_encryption(DeliveryStreamName="?")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Firehose ? under account 123456789012 not found."
