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
    # do test