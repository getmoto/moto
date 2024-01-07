import moto.server as server
from moto import mock_aws

"""
Test the different server responses
"""


@mock_aws
def test_batch_list():
    backend = server.create_backend_app("batch")
    test_client = backend.test_client()

    res = test_client.get("/v1/describecomputeenvironments")
    assert res.status_code == 200
