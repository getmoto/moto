import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_polly
from tests import DEFAULT_ACCOUNT_ID

"""
Test the different server responses
"""


@mock_polly
def test_polly_list():
    backend = server.create_backend_app(account_id=DEFAULT_ACCOUNT_ID, service="polly")
    test_client = backend.test_client()

    res = test_client.get("/v1/lexicons")
    res.status_code.should.equal(200)
