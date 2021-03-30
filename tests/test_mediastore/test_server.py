from __future__ import unicode_literals

import sure  # noqa

# import moto.server as server
from moto import mock_mediastore

"""
Test the different server responses
"""


@mock_mediastore
def test_mediastore_list_containers():
    pass
    # backend = server.create_backend_app("mediastore")
    # test_client = backend.test_client()
    # res = test_client.get("/containers")
    # result = res.data.decode("utf-8")
    # print(result)
    # result.should.contain('"containers": []')
