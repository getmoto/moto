import sure  # flake8: noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("sts")


def test_sts_get_session_token():
    test_client = server.app.test_client()
    res = test_client.get('/?Action=GetSessionToken')
    res.status_code.should.equal(200)
    res.data.should.contain("SessionToken")
    res.data.should.contain("AccessKeyId")
