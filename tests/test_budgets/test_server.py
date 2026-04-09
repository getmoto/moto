import json

import moto.server as server
from moto import mock_aws
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1


@mock_aws
def test_budgets_describe_budgets():
    backend = server.create_backend_app("budgets")
    test_client = backend.test_client()

    headers = {
        "X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }
    resp = test_client.post("/", headers=headers, json={})
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"Budgets": [], "nextToken": None}
