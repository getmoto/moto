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


@mock_aws
def test_connection_tags(client):
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection1",
        requestMACSec=False,
        tags=[
            {
                "key": "name",
                "value": "Test Connection",
            },
            {
                "key": "connection-id",
                "value": "test-1",
            },
        ],
    )
    client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection2",
        requestMACSec=True,
        tags=[
            {
                "key": "name",
                "value": "Test Connection 2",
            },
            {
                "key": "connection-id",
                "value": "test-2",
            },
        ],
    )
    resp = client.describe_connections()
    connections = resp["connections"]
    assert len(connections) == 2

    assert len(connections[0]["tags"]) == 2
    assert connections[0]["tags"][0]["key"] == "name"
    assert connections[0]["tags"][0]["value"] == "Test Connection"
    assert connections[0]["tags"][1]["key"] == "connection-id"
    assert connections[0]["tags"][1]["value"] == "test-1"

    assert connections[1]["tags"][0]["key"] == "name"
    assert connections[1]["tags"][0]["value"] == "Test Connection 2"
    assert connections[1]["tags"][1]["key"] == "connection-id"
    assert connections[1]["tags"][1]["value"] == "test-2"


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


def test_associate_mac_sec_key_connection(client):
    connection = client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection1",
    )
    resp = client.associate_mac_sec_key(
        connectionId=connection["connectionId"], ckn="_fake_ckn_", cak="_fake_cak_"
    )
    assert resp["connectionId"] == connection["connectionId"]
    mac_sec_keys = resp["macSecKeys"]
    assert len(mac_sec_keys) == 1
    assert mac_sec_keys[0]["ckn"] == "_fake_ckn_"
    assert "cak" not in mac_sec_keys[0]
    assert mac_sec_keys[0]["secretARN"] == "mock_secret_arn"


def test_associate_mac_sec_key_lag(client):
    lag = client.create_lag(
        numberOfConnections=1,
        location="eqDC2",
        connectionsBandwidth="10Gbps",
        lagName="TestLag1",
    )
    resp = client.associate_mac_sec_key(
        connectionId=lag["lagId"], ckn="_fake_ckn_", cak="_fake_cak_"
    )
    assert resp["connectionId"] == lag["lagId"]
    mac_sec_keys = resp["macSecKeys"]
    assert len(mac_sec_keys) == 1
    assert mac_sec_keys[0]["ckn"] == "_fake_ckn_"
    assert "cak" not in mac_sec_keys[0]
    assert mac_sec_keys[0]["secretARN"] == "mock_secret_arn"


def test_create_lag(client):
    lag = client.create_lag(
        numberOfConnections=1,
        location="eqDC2",
        connectionsBandwidth="10Gbps",
        lagName="TestLag0",
    )
    assert lag["lagId"].startswith("dxlag-moto")
    assert lag["lagState"] == "available"
    assert len(lag["connections"]) == 1
    connection = lag["connections"][0]
    assert connection["connectionName"].startswith(
        "Requested Connection 1 for Lag dxlag-moto"
    )


def test_describe_lags(client):
    client.create_lag(
        location="EqDC2",
        connectionsBandwidth="10Gbps",
        lagName="TestLag1",
        numberOfConnections=1,
        requestMACSec=False,
    )
    time.sleep(0.1)
    client.create_lag(
        location="EqDC2",
        connectionsBandwidth="10Gbps",
        lagName="TestLag2",
        numberOfConnections=1,
        requestMACSec=True,
    )
    time.sleep(0.1)
    resp = client.describe_lags()
    lags = resp["lags"]
    assert len(lags) == 2
    assert len(lags[0]["connections"]) == 1
    assert len(lags[1]["connections"]) == 1
    assert not lags[0]["macSecCapable"]
    assert not lags[0]["connections"][0]["macSecCapable"]
    assert lags[1]["macSecCapable"]
    assert lags[1]["connections"][0]["macSecCapable"]
    assert len(lags[0]["macSecKeys"]) == 0
    assert len(lags[0]["connections"][0]["macSecKeys"]) == 0
    assert len(lags[1]["macSecKeys"]) == 1
    assert len(lags[1]["connections"][0]["macSecKeys"]) == 1
    assert lags[0]["encryptionMode"] == "no_encrypt"
    assert lags[0]["connections"][0]["encryptionMode"] == "no_encrypt"
    assert lags[1]["encryptionMode"] == "must_encrypt"
    assert lags[1]["connections"][0]["encryptionMode"] == "must_encrypt"
    resp = client.describe_lags(lagId=lags[0]["lagId"])
    assert len(resp["lags"]) == 1


def _test_disassociate_mac_sec_key_common(client, connection_id: str):
    secret_arn = "_fake_secret_arn_"
    assoc_resp = client.associate_mac_sec_key(
        connectionId=connection_id,
        ckn="_fake_ckn_",
        cak="_fake_cak_",
        secretARN=secret_arn,
    )
    assert assoc_resp["connectionId"] == connection_id
    resp = client.disassociate_mac_sec_key(
        connectionId=connection_id, secretARN=secret_arn
    )
    assert resp["connectionId"] == connection_id
    mac_sec_keys = resp["macSecKeys"]
    assert len(mac_sec_keys) == 1
    assert mac_sec_keys[0]["secretARN"] == secret_arn
    assert mac_sec_keys[0]["state"] == "disassociated"


def test_disassociate_mac_sec_key_connection(client):
    connection = client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection1",
    )
    connection_id = connection["connectionId"]
    _test_disassociate_mac_sec_key_common(client=client, connection_id=connection_id)


def test_disassociate_mac_sec_key_lag(client):
    lag = client.create_lag(
        numberOfConnections=1,
        location="eqDC2",
        connectionsBandwidth="10Gbps",
        lagName="TestLag1",
    )
    lag_id = lag["lagId"]
    _test_disassociate_mac_sec_key_common(client=client, connection_id=lag_id)


@mock_aws
def test_tag_resource(client):
    connection = client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection1",
        requestMACSec=False,
    )
    connection_id = connection["connectionId"]

    client.tag_resource(
        resourceArn=connection_id,
        tags=[{"key": "t1", "value": "v1"}, {"key": "t2", "value": "v2"}],
    )

    expected = [{"key": "t1", "value": "v1"}, {"key": "t2", "value": "v2"}]
    assert get_tags(connection_id, client) == expected
    assert (
        client.describe_connections(connectionId=connection_id)["connections"][0][
            "tags"
        ]
        == expected
    )

    client.untag_resource(resourceArn=connection_id, tagKeys=["t1"])
    assert get_tags(connection_id, client) == [{"key": "t2", "value": "v2"}]

    client.untag_resource(resourceArn=connection_id, tagKeys=["t2"])
    assert get_tags(connection_id, client) == []


def get_tags(arn, client):
    tags = client.describe_tags(resourceArns=[arn])
    return tags["resourceTags"][0]["tags"]
