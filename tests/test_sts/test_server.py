import moto.server as server


def test_sts_get_session_token():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetSessionToken")
    assert res.status_code == 200
    assert b"SessionToken" in res.data
    assert b"AccessKeyId" in res.data


def test_sts_get_federation_token():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetFederationToken&Name=Bob")
    assert res.status_code == 200
    assert b"SessionToken" in res.data
    assert b"AccessKeyId" in res.data


def test_sts_get_caller_identity():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetCallerIdentity")
    assert res.status_code == 200
    assert b"Arn" in res.data
    assert b"UserId" in res.data
    assert b"Account" in res.data


def test_sts_wellformed_xml():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetFederationToken&Name=Bob")
    assert b"\n" not in res.data
    res = test_client.get("/?Action=GetSessionToken")
    assert b"\n" not in res.data
    res = test_client.get("/?Action=GetCallerIdentity")
    assert b"\n" not in res.data
