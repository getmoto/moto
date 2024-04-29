"""Test different server responses."""

import moto.server as server


def test_sagemakermetrics_batch_put_metrics():
    backend = server.create_backend_app("sagemaker-metrics")
    test_client = backend.test_client()

    resp = test_client.put("/BatchPutMetrics")

    assert resp.status_code == 200
    assert "VALIDATION_ERROR" in str(resp.data)
