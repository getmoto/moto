"""Test different server responses."""

import moto.server as server
import pytest

# Disable this test
@pytest.mark.skip
def test_fsx_list():
    backend = server.create_backend_app("fsx")
    test_client = backend.test_client()

    resp = test_client.get("/")

    assert resp.status_code == 200
    assert "?" in str(resp.data)