import pytest

import moto.server as server


def test_sesv2_list():
    backend = server.create_backend_app("sesv2")
    test_client = backend.test_client()

    resp = test_client.get("/v2/email/contact-lists")

    assert resp.status_code == 200
    assert resp.data == b'{"ContactLists": []}'


@pytest.mark.parametrize(
    "request_uri", ["/v2/email/list-configuration-sets", "/v2/email/list-identities"]
)
def test_anomalous_uris(request_uri):
    # Botocore 1.43.105 updated the request uris (to a non-standard) format
    # for some action methods. (https://github.com/boto/botocore/commit/9931e97)
    backend = server.create_backend_app("sesv2")
    test_client = backend.test_client()
    resp = test_client.post(request_uri)
    assert resp.status_code == 200
