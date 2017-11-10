from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_iotdata

'''
Test the different server responses
'''

@mock_iotdata
def test_iotdata_list():
    backend = server.create_backend_app("iot-data")
    test_client = backend.test_client()

    # just making sure that server is up
    thing_name = 'nothing'
    res = test_client.get('/things/{}/shadow'.format(thing_name))
    res.status_code.should.equal(404)
