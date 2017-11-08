from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_resourcegroupstaggingapi

'''
Test the different server responses
'''

@mock_resourcegroupstaggingapi
def test_resourcegroupstaggingapi_list():
    backend = server.create_backend_app("resourcegroupstaggingapi")
    test_client = backend.test_client()
    # do test