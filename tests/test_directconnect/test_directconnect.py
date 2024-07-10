"""Unit tests for directconnect-supported APIs."""
import boto3
import pytest
import time

from moto import mock_aws

@pytest.fixture(name="client")
def fixture_dx_client():
    with mock_aws():
        yield boto3.client("directconnect", region_name="us-east-1")

def test_create_connection(client):
    resp = client.create_connection()
    connection = resp["connection"]
    assert connection["connection_id"].startswith("dx-moto")
    assert connection["connectionState"] == "available"

@mock_aws
def test_describe_connections(client):
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection1",
        requestMACSec=False,
    )
    time.sleep(1)
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection2",
        requestMACSec=True,
    )
    time.sleep(1)
    resp = client.describe_connections()
    connections = resp["connections"]
    assert len(connections) == 2
    assert connections[0]["macSecCapable"] == False
    assert connections[1]["macSecCapable"] == True
    assert len(connections[0]["macSecKeys"]) == 0
    assert len(connections[1]["macSecKeys"]) == 1
    assert connections[0]["encryptionMode"] == "no_encrypt"
    assert connections[1]["encryptionMode"] == "must_encrypt"
    resp = client.describe_connections(connectionId=connections[0]["connectionId"])
    assert len(resp["connections"]) == 1

@mock_aws
def test_delete_connection(client):
    create_resp = client.create_connection()
    connection_id = create_resp["connection"]["connection_id"]
    delete_resp = client.delete_connection(connectionId=connection_id)
    assert delete_resp["connection"]["connectionState"] == "deleted"

@mock_aws
def test_update_connection(client):
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection1",
    )
    time.sleep(1)
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection2",
        requestMACSec=True,
    )
    time.sleep(1)
    resp = client.describe_connections()
    connection1_id = resp["connections"][0]["connectionId"]
    connection2_id = resp["connections"][1]["connectionId"]
    update_resp = client.update_connection(
        connectionId=connection1_id,
        connectionName="NewConnectionName",
    )
    assert update_resp["connection"]["connectionName"] == "NewConnectionName"
    update_resp = client.update_connection(
        connectionId=connection2_id,
        encryptionMode="should_encrypt",
    )
    assert update_resp["connection"]["encryptionMode"] == "should_encrypt"

