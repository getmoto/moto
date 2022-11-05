import sure  # noqa # pylint: disable=unused-import

import moto.server as server

"""
Test the different server responses
"""


def test_sts_get_session_token():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetSessionToken")
    res.status_code.should.equal(200)
    res.data.should.contain(b"SessionToken")
    res.data.should.contain(b"AccessKeyId")


def test_sts_get_federation_token():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetFederationToken&Name=Bob")
    res.status_code.should.equal(200)
    res.data.should.contain(b"SessionToken")
    res.data.should.contain(b"AccessKeyId")


def test_sts_get_caller_identity():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetCallerIdentity")
    res.status_code.should.equal(200)
    res.data.should.contain(b"Arn")
    res.data.should.contain(b"UserId")
    res.data.should.contain(b"Account")


def test_sts_wellformed_xml():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetFederationToken&Name=Bob")
    res.data.should_not.contain(b"\n")
    res = test_client.get("/?Action=GetSessionToken")
    res.data.should_not.contain(b"\n")
    res = test_client.get("/?Action=GetCallerIdentity")
    res.data.should_not.contain(b"\n")
