import json

import moto.server as server


def test_create_without_enable_option():
    backend = server.create_backend_app("guardduty")
    test_client = backend.test_client()

    body = {"enable": "True"}
    response = test_client.post("/detector", data=json.dumps(body))
    assert response.status_code == 200
    assert "detectorId" in json.loads(response.data)
