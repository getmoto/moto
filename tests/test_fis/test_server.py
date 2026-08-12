"""Test different server responses."""

import json

import moto.server as server


def test_fis_list_experiment_templates():
    backend = server.create_backend_app("fis")
    test_client = backend.test_client()

    resp = test_client.get("/experimentTemplates")

    assert resp.status_code == 200
    assert json.loads(resp.data) == {"experimentTemplates": []}


def test_fis_list_experiments():
    backend = server.create_backend_app("fis")
    test_client = backend.test_client()

    resp = test_client.get("/experiments")

    assert resp.status_code == 200
    assert json.loads(resp.data) == {"experiments": []}
