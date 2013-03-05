import sure  # flake8: noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("ses")


def test_ses_list_identities():
    test_client = server.app.test_client()
    res = test_client.get('/?Action=ListIdentities')
    res.data.should.contain("ListIdentitiesResponse")
