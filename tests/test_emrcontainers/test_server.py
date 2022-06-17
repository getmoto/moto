import json
import sure  # noqa # pylint: disable=unused-import
import moto.server as server
from tests import DEFAULT_ACCOUNT_ID

"""
Test the different server responses
"""


def test_list_virtual_clusters():
    backend = server.create_backend_app(
        account_id=DEFAULT_ACCOUNT_ID, service="emr-containers"
    )
    test_client = backend.test_client()

    res = test_client.get("/virtualclusters")

    json.loads(res.data).should.have.key("virtualClusters")
