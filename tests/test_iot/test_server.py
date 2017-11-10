from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_iot

'''
Test the different server responses
'''

@mock_iot
def test_iot_list():
    backend = server.create_backend_app("iot")
    test_client = backend.test_client()

    # just making sure that server is up
    res = test_client.get('/things')
    res.status_code.should.equal(404)
