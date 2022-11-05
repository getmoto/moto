import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_batch

"""
Test the different server responses
"""


@mock_batch
def test_batch_list():
    backend = server.create_backend_app("batch")
    test_client = backend.test_client()

    res = test_client.get("/v1/describecomputeenvironments")
    res.status_code.should.equal(200)
