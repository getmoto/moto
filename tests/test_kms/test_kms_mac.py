"""Unit tests for kms-supported APIs."""

import base64

import boto3
import pytest

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


def create_hmac_key() -> str:
    client = boto3.client("kms", region_name="eu-central-1")

    key_id = client.create_key(
        KeyUsage="GENERATE_VERIFY_MAC", KeySpec="HMAC_512", Policy="My Policy"
    )["KeyMetadata"]["KeyId"]

    return key_id


@mock_aws
def test_generate_mac():
    # Arrange
    key_id = create_hmac_key()
    client = boto3.client("kms", region_name="eu-central-1")

    # Act
    resp = client.generate_mac(
        KeyId=key_id,
        MacAlgorithm="HMAC_SHA_512",
        Message=base64.b64encode("Hello World".encode("utf-8")),
    )

    # Assert
    assert "Mac" in resp
    assert resp["KeyId"] == key_id
    assert resp["MacAlgorithm"] == "HMAC_SHA_512"


@mock_aws
def test_generate_fails_for_non_existent_key():
    # Arrange
    client = boto3.client("kms", region_name="eu-central-1")

    # Act + Assert
    with pytest.raises(client.exceptions.NotFoundException):
        client.generate_mac(
            KeyId="some-key",
            MacAlgorithm="HMAC_SHA_512",
            Message=base64.b64encode("Hello World".encode("utf-8")),
        )


@mock_aws
def test_generate_fails_for_invalid_key_usage():
    # Arrange
    client = boto3.client("kms", region_name="eu-central-1")
    key_id = client.create_key(
        KeyUsage="ENCRYPT_DECRYPT", KeySpec="HMAC_512", Policy="My Policy"
    )["KeyMetadata"]["KeyId"]

    # Act + Assert
    with pytest.raises(client.exceptions.InvalidKeyUsageException):
        client.generate_mac(
            KeyId=key_id,
            MacAlgorithm="HMAC_SHA_512",
            Message=base64.b64encode("Hello World".encode("utf-8")),
        )


@mock_aws
def test_generate_fails_for_invalid_key_spec():
    # Arrange
    client = boto3.client("kms", region_name="eu-central-1")
    key_id = client.create_key(
        KeyUsage="GENERATE_VERIFY_MAC", KeySpec="RSA_2048", Policy="My Policy"
    )["KeyMetadata"]["KeyId"]

    # Act + Assert
    with pytest.raises(client.exceptions.InvalidKeyUsageException):
        client.generate_mac(
            KeyId=key_id,
            MacAlgorithm="HMAC_SHA_512",
            Message=base64.b64encode("Hello World".encode("utf-8")),
        )


@mock_aws
def test_verify_mac():
    # Arrange
    key_id = create_hmac_key()
    client = boto3.client("kms", region_name="eu-central-1")
    mac = client.generate_mac(
        KeyId=key_id,
        MacAlgorithm="HMAC_SHA_512",
        Message=base64.b64encode("Hello World".encode("utf-8")),
    )["Mac"]

    # Act
    resp = client.verify_mac(
        KeyId=key_id,
        MacAlgorithm="HMAC_SHA_512",
        Message=base64.b64encode("Hello World".encode("utf-8")),
        Mac=mac,
    )

    # Assert
    assert resp["KeyId"] == key_id
    assert resp["MacAlgorithm"] == "HMAC_SHA_512"
    assert resp["MacValid"] is True


@mock_aws
def test_verify_mac_fails_for_another_key_id():
    # Arrange
    key_id = create_hmac_key()
    other_key_id = create_hmac_key()
    client = boto3.client("kms", region_name="eu-central-1")
    mac = client.generate_mac(
        KeyId=key_id,
        MacAlgorithm="HMAC_SHA_512",
        Message=base64.b64encode("Hello World".encode("utf-8")),
    )["Mac"]

    # Act + Assert
    with pytest.raises(client.exceptions.KMSInvalidMacException):
        client.verify_mac(
            KeyId=other_key_id,
            MacAlgorithm="HMAC_SHA_512",
            Message=base64.b64encode("Hello World".encode("utf-8")),
            Mac=mac,
        )
