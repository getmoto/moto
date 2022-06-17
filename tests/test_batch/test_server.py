import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_batch
from tests import DEFAULT_ACCOUNT_ID

"""
Test the different server responses
"""


@mock_batch
def test_batch_list():
    backend = server.create_backend_app(account_id=DEFAULT_ACCOUNT_ID, service="batch")
    test_client = backend.test_client()

    res = test_client.get("/v1/describecomputeenvironments")
    res.status_code.should.equal(200)
