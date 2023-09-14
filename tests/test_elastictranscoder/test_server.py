import moto.server as server
from moto import mock_elastictranscoder

"""
Test the different server responses
"""


@mock_elastictranscoder
def test_elastictranscoder_list():
    backend = server.create_backend_app("elastictranscoder")
    test_client = backend.test_client()

    res = test_client.get("/2012-09-25/pipelines")
    assert b"Pipelines" in res.data
