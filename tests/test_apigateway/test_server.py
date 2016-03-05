from __future__ import unicode_literals
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_list_apis():
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()

    res = test_client.get('/restapis')
    res.data.should.equal(b'{"item": []}')
