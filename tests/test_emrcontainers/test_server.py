"""Test different server responses."""
import sure  # noqa # pylint: disable=unused-import
import moto.server as server

"""
Test the different server responses
"""


def test_list_virtual_clusters():
    backend = server.create_backend_app("emr-containers")
    test_client = backend.test_client()

    res = test_client.get("/virtualclusters")

    b'{"virtualClusters": [], "nextToken": null}' in res.data
