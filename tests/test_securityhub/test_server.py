import json

import moto.server as server
from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID


@mock_aws
def test_securityhub_server():
    backend = server.create_backend_app("securityhub")
    test_client = backend.test_client()

    finding = {
        "AwsAccountId": DEFAULT_ACCOUNT_ID,
        "CreatedAt": "2024-01-01T00:00:00.000Z",
        "UpdatedAt": "2024-01-01T00:00:00.000Z",
        "Description": "Test finding",
        "GeneratorId": "test-generator",
        "Id": "test-finding-001",
        "ProductArn": f"arn:aws:securityhub:us-east-1:{DEFAULT_ACCOUNT_ID}:product/{DEFAULT_ACCOUNT_ID}/default",
        "Resources": [{"Id": "test-resource", "Type": "AwsEc2Instance"}],
        "SchemaVersion": "2018-10-08",
        "Severity": {"Label": "HIGH"},
        "Title": "Test Finding",
        "Types": ["Software and Configuration Checks"],
    }

    resp = test_client.post(
        "/findings/import",
        data=json.dumps({"Findings": [finding]}),
        headers={"X-Amz-Target": "SecurityHub_20180617.BatchImportFindings"},
    )
    assert resp.status_code == 200
