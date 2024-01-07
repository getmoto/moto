import moto.server as server
from moto import mock_aws

"""
Test the different server responses
"""


@mock_aws
def test_kinesisvideo_server_is_up():
    backend = server.create_backend_app("kinesisvideo")
    test_client = backend.test_client()
    res = test_client.post("/listStreams")
    assert res.status_code == 200
