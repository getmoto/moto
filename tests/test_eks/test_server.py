from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_eks

'''
Test the different server responses
'''

@mock_eks
def test_eks_list():
    backend = server.create_backend_app("eks")
    test_client = backend.test_client()
    # do test