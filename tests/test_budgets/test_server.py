import json

import moto.server as server
from moto import mock_aws


@mock_aws
def test_budgets_describe_budgets():
    backend = server.create_backend_app("budgets")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets"}
    resp = test_client.post("/", headers=headers, json={})
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"Budgets": [], "nextToken": None}
