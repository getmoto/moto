from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_mediastoredata

"""
Test the different server responses
"""


@mock_mediastoredata
def test_mediastore_lists_containers():
    backend = server.create_backend_app("mediastoreback")
    test_client = backend.test_client()

    # res = test_client.get(
    #     "/", headers={"X-Amz-Target": "MediaStore_20170901.ListContainers"},
    # )
    #
    # result = res.data.decode("utf-8")
    # result.should.contain('"Containers": []')
