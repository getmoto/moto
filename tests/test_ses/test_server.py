import sure  # noqa # pylint: disable=unused-import

import moto.server as server

"""
Test the different server responses
"""


def test_ses_list_identities():
    backend = server.create_backend_app("ses")
    test_client = backend.test_client()

    res = test_client.get("/?Action=ListIdentities")
    res.data.should.contain(b"ListIdentitiesResponse")
