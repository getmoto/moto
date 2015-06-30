from __future__ import unicode_literals

import json
import sure  # noqa

import moto.server as server
from moto import mock_kms

'''
Test the different server responses
'''


@mock_kms
def test_list_keys():
    backend = server.create_backend_app("kms")
    test_client = backend.test_client()

    res = test_client.get('/?Action=ListKeys')

    json.loads(res.data.decode("utf-8")).should.equal({
        "Keys": [],
        "NextMarker": None,
        "Truncated": False,
    })
