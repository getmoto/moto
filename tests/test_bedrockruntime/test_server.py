import moto.server as server
from moto import mock_aws


@mock_aws
def test_invoke_model():
    backend = server.create_backend_app("bedrock-runtime")
    test_client = backend.test_client()
    headers = {
        "X-Amzn-Bedrock-PerformanceConfig-Latency": "optimized",
        "X-Amzn-Bedrock-Service-Tier": "flex",
    }
    resp = test_client.post("/model/test-model-id/invoke", headers=headers, json={})
    assert resp.status_code == 200
    for header, value in resp.headers.items():
        assert resp.headers[header] == value
