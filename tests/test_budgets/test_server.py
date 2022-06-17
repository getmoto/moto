import json
import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_budgets
from tests import DEFAULT_ACCOUNT_ID


@mock_budgets
def test_budgets_describe_budgets():
    backend = server.create_backend_app(
        account_id=DEFAULT_ACCOUNT_ID, service="budgets"
    )
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets"}
    resp = test_client.post("/", headers=headers, json={})
    resp.status_code.should.equal(200)
    json.loads(resp.data).should.equal({"Budgets": [], "nextToken": None})
