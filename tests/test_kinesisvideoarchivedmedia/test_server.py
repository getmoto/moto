from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_kinesisvideoarchivedmedia

"""
Test the different server responses
"""


@mock_kinesisvideoarchivedmedia
def test_kinesisvideoarchivedmedia_list():
    backend = server.create_backend_app("kinesis-video-archived-media")
    test_client = backend.test_client()
    # do test
