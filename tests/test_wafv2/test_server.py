from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_wafv2

'''
Test the different server responses
'''

@mock_wafv2
def test_wafv2_list():
    backend = server.create_backend_app("wafv2")
    test_client = backend.test_client()
    # do test