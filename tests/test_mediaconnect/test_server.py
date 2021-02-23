from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_mediaconnect

"""
Test the different server responses
"""


@mock_mediaconnect
def test_mediaconnect_list_flows():
    backend = server.create_backend_app("mediaconnect")
    test_client = backend.test_client()

    res = test_client.get("/v1/flows")

    result = res.data.decode("utf-8")
    result.should.contain('"flows": []')
