from __future__ import unicode_literals
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_ses_list_identities():
    backend = server.create_backend_app("ses")
    test_client = backend.test_client()

    res = test_client.get('/?Action=ListIdentities')
    res.data.should.contain(b"ListIdentitiesResponse")
