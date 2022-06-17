import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_elastictranscoder
from tests import DEFAULT_ACCOUNT_ID

"""
Test the different server responses
"""


@mock_elastictranscoder
def test_elastictranscoder_list():
    backend = server.create_backend_app(
        account_id=DEFAULT_ACCOUNT_ID, service="elastictranscoder"
    )
    test_client = backend.test_client()

    res = test_client.get("/2012-09-25/pipelines")
    res.data.should.contain(b"Pipelines")
