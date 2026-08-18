import json

import moto.server as server
from moto import mock_aws


@mock_aws
def test_control_plane_server_dispatch():
    app = server.create_backend_app("paymentcryptography")
    response = app.test_client().post(
        "/",
        headers={"X-Amz-Target": "PaymentCryptographyControlPlane.ListKeys"},
        data=json.dumps({}),
        content_type="application/x-amz-json-1.0",
    )
    assert response.status_code == 200
    assert json.loads(response.data) == {"Keys": []}
