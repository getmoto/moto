"""Unit tests for directconnect-supported APIs."""

import time

import boto3
import pytest

from moto import mock_aws


@pytest.fixture(name="client")
def fixture_dx_client():
    with mock_aws():
        yield boto3.client("directconnect", region_name="us-east-1")


def test_create_connection(client):
    connection = client.create_connection(
        location="EqDC2", bandwidth="10Gbps", connectionName="TestConnection"
    )
    assert connection["connectionId"].startswith("dx-moto")
    assert connection["connectionState"] == "available"


def test_describe_connections(client):
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection1",
        requestMACSec=False,
    )
    time.sleep(0.1)
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection2",
        requestMACSec=True,
    )
    time.sleep(0.1)
    resp = client.describe_connections()
    connections = resp["connections"]
    assert len(connections) == 2
    assert not connections[0]["macSecCapable"]
    assert connections[1]["macSecCapable"]
    assert len(connections[0]["macSecKeys"]) == 0
    assert len(connections[1]["macSecKeys"]) == 1
    assert connections[0]["encryptionMode"] == "no_encrypt"
    assert connections[1]["encryptionMode"] == "must_encrypt"
    resp = client.describe_connections(connectionId=connections[0]["connectionId"])
    assert len(resp["connections"]) == 1


def test_delete_connection(client):
    connection = client.create_connection(
        location="EqDC2", bandwidth="10Gbps", connectionName="TestConnection"
    )
    connection = client.delete_connection(connectionId=connection["connectionId"])
    assert connection["connectionState"] == "deleted"


def test_update_connection(client):
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection1",
    )
    time.sleep(0.1)
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection2",
        requestMACSec=True,
    )
    time.sleep(0.1)
    resp = client.describe_connections()
    connection1_id = resp["connections"][0]["connectionId"]
    connection2_id = resp["connections"][1]["connectionId"]
    connection = client.update_connection(
        connectionId=connection1_id,
        connectionName="NewConnectionName",
    )
    assert connection["connectionName"] == "NewConnectionName"
    connection = client.update_connection(
        connectionId=connection2_id,
        encryptionMode="should_encrypt",
    )
    assert connection["encryptionMode"] == "should_encrypt"
