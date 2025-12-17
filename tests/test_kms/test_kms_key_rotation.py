"""Unit tests for kms-supported APIs."""

import boto3
import pytest

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_rotate_key_on_demand_with_existing_key():
    client = boto3.client("kms", region_name="us-east-2")

    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]

    resp = client.rotate_key_on_demand(KeyId=key_id)

    assert resp["KeyId"] == key_id


@mock_aws
def test_rotate_key_on_demand_with_non_existing_key_fails():
    client = boto3.client("kms", region_name="us-east-2")

    with pytest.raises(client.exceptions.NotFoundException):
        client.rotate_key_on_demand(KeyId="some-id")


@mock_aws
def test_list_key_rotations_with_non_existing_key_fails():
    client = boto3.client("kms", region_name="us-east-2")

    with pytest.raises(client.exceptions.NotFoundException):
        client.list_key_rotations(KeyId="some-id")


@mock_aws
def test_list_key_rotations_are_empty_on_new_key():
    client = boto3.client("kms", region_name="us-east-2")

    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]

    resp = client.list_key_rotations(KeyId=key_id)

    assert len(resp["Rotations"]) == 0
    assert resp["Truncated"] is False
    assert "NextMarker" not in resp


@mock_aws
def test_list_key_rotations_returns_one_rotation():
    # Arrange
    client = boto3.client("kms", region_name="us-east-2")
    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]
    client.rotate_key_on_demand(KeyId=key_id)

    # Act
    resp = client.list_key_rotations(KeyId=key_id)

    # Assert
    assert len(resp["Rotations"]) == 1
    assert resp["Truncated"] is False
    assert "NextMarker" not in resp
    assert resp["Rotations"][0]["RotationType"] == "ON_DEMAND"


@mock_aws
def test_list_key_rotations_returns_truncated_and_next_marker():
    # Arrange
    client = boto3.client("kms", region_name="us-east-2")
    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]
    client.rotate_key_on_demand(KeyId=key_id)
    client.rotate_key_on_demand(KeyId=key_id)
    client.rotate_key_on_demand(KeyId=key_id)

    # Act
    resp = client.list_key_rotations(KeyId=key_id, Limit=1)

    # Assert
    assert len(resp["Rotations"]) == 1
    assert resp["Truncated"] is True
    assert "NextMarker" in resp


@mock_aws
def test_list_key_rotations_pagination():
    # Arrange
    client = boto3.client("kms", region_name="us-east-2")
    key_id = client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]
    client.rotate_key_on_demand(KeyId=key_id)
    client.rotate_key_on_demand(KeyId=key_id)
    client.rotate_key_on_demand(KeyId=key_id)
    initial_page = client.list_key_rotations(KeyId=key_id, Limit=1)

    # Act

    final_page = client.list_key_rotations(
        KeyId=key_id, Limit=2, Marker=initial_page["NextMarker"]
    )

    # Assert
    assert len(final_page["Rotations"]) == 2
    assert final_page["Truncated"] is False
    assert "NextMarker" not in final_page
