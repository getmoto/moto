"""Test the different server responses."""
import moto.server as server
from moto import mock_polly


@mock_polly
def test_polly_list():
    backend = server.create_backend_app("polly")
    test_client = backend.test_client()

    res = test_client.get("/v1/lexicons")
    assert res.status_code == 200
