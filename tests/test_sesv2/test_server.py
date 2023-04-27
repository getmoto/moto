"""Test different server responses."""

import moto.server as server


def test_sesv2_list():
    backend = server.create_backend_app("sesv2")
    test_client = backend.test_client()

    resp = test_client.post("/v2/email/contact-lists/test/contacts")

    assert resp.status_code == 200
