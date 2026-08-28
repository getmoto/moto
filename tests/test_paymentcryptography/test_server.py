"""Test the different server responses."""

import json

import moto.server as server
from moto import mock_aws


@mock_aws
def test_list_keys():
    backend = server.create_backend_app("paymentcryptography")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        headers={"X-Amz-Target": "PaymentCryptographyControlPlane.ListKeys"},
        data=json.dumps({}),
        content_type="application/x-amz-json-1.0",
    )
    assert res.status_code == 200
    assert json.loads(res.data)["Keys"] == []
