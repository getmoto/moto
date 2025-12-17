"""Test the different server responses."""

import json

import moto.server as server


def test_list_global_networks():
    backend = server.create_backend_app("networkmanager")
    test_client = backend.test_client()

    res = test_client.get("/global-networks")

    assert "GlobalNetworks" in json.loads(res.data)


def test_list_core_networks():
    backend = server.create_backend_app("networkmanager")
    test_client = backend.test_client()

    res = test_client.get("/core-networks")

    assert "CoreNetworks" in json.loads(res.data)


def test_tag_resource():
    backend = server.create_backend_app("networkmanager")
    test_client = backend.test_client()

    res = test_client.post(
        "/tags/test-resource-id",
        json={"Tags": [{"Key": "Name", "Value": "CoreNetworks"}]},
    )
    data = json.loads(res.data)
    assert data["Message"] == "Resource not found."
    assert data["ResourceId"] == "test-resource-id"
