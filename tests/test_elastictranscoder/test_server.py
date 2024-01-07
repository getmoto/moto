import moto.server as server
from moto import mock_aws

"""
Test the different server responses
"""


@mock_aws
def test_elastictranscoder_list():
    backend = server.create_backend_app("elastictranscoder")
    test_client = backend.test_client()

    res = test_client.get("/2012-09-25/pipelines")
    assert b"Pipelines" in res.data
