import json

import moto.server as server


def test_apigatewayv2_list_apis():
    backend = server.create_backend_app("apigatewayv2")
    test_client = backend.test_client()

    resp = test_client.get("/v2/apis")
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"items": []}
