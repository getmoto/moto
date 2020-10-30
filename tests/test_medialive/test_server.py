from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_medialive

"""
Test the different server responses
"""


@mock_medialive
def test_medialive_list():
    backend = server.create_backend_app("medialive")
    test_client = backend.test_client()
    # do test
