import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_kinesisvideo

"""
Test the different server responses
"""


@mock_kinesisvideo
def test_kinesisvideo_server_is_up():
    backend = server.create_backend_app("kinesisvideo")
    test_client = backend.test_client()
    res = test_client.post("/listStreams")
    res.status_code.should.equal(200)
