"""Test different server responses."""

from moto import server


def test_synthetics_list():
    """
    Test that the synthetics server root endpoint returns a 200 response and contains a '?'.
    """
    backend = server.create_backend_app("synthetics")
    test_client = backend.test_client()

    resp = test_client.get("/")

    assert resp.status_code == 200
    assert "?" in str(resp.data)
