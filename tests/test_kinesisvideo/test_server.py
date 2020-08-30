from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_kinesisvideo

"""
Test the different server responses
"""


@mock_kinesisvideo
def test_kinesisvideo_list():
    backend = server.create_backend_app("kinesisvideo")
    test_client = backend.test_client()
    # do test
