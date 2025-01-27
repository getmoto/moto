"""Unit tests for securityhub-supported APIs."""

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID


@mock_aws
def test_get_findings():
    client = boto3.client("securityhub", region_name="us-east-1")

    test_finding = {
        "AwsAccountId": DEFAULT_ACCOUNT_ID,
        "CreatedAt": "2024-01-01T00:00:00.000Z",
        "UpdatedAt": "2024-01-01T00:00:00.000Z",
        "Description": "Test finding description",
        "GeneratorId": "test-generator",
        "Id": "test-finding-001",
        "ProductArn": f"arn:aws:securityhub:{client.meta.region_name}:{DEFAULT_ACCOUNT_ID}:product/{DEFAULT_ACCOUNT_ID}/default",
        "Resources": [{"Id": "test-resource", "Type": "AwsEc2Instance"}],
        "SchemaVersion": "2018-10-08",
        "Severity": {"Label": "HIGH"},
        "Title": "Test Finding",
        "Types": ["Software and Configuration Checks"],
    }

    # Import the finding
    import_response = client.batch_import_findings(Findings=[test_finding])
    assert import_response["SuccessCount"] == 1

    # Get the findings
    response = client.get_findings()

    assert "Findings" in response
    assert isinstance(response["Findings"], list)
    assert len(response["Findings"]) == 1
    finding = response["Findings"][0]
    assert finding["Id"] == "test-finding-001"
    assert finding["SchemaVersion"] == "2018-10-08"
    # assert finding["WorkflowState"] == "NEW"
    # assert finding["RecordState"] == "ACTIVE"


@mock_aws
def test_batch_import_findings():
    client = boto3.client("securityhub", region_name="us-east-2")

    valid_finding = {
        "AwsAccountId": DEFAULT_ACCOUNT_ID,
        "CreatedAt": "2024-01-01T00:00:00.000Z",
        "UpdatedAt": "2024-01-01T00:00:00.000Z",
        "Description": "Test finding description",
        "GeneratorId": "test-generator",
        "Id": "test-finding-001",
        "ProductArn": f"arn:aws:securityhub:{client.meta.region_name}:{DEFAULT_ACCOUNT_ID}:product/{DEFAULT_ACCOUNT_ID}/default",
        "Resources": [{"Id": "test-resource", "Type": "AwsEc2Instance"}],
        "SchemaVersion": "2018-10-08",
        "Severity": {"Label": "HIGH"},
        "Title": "Test Finding",
        "Types": ["Software and Configuration Checks"],
    }

    response = client.batch_import_findings(Findings=[valid_finding])
    assert response["SuccessCount"] == 1
    assert response["FailedCount"] == 0
    assert response["FailedFindings"] == []

    invalid_finding = valid_finding.copy()
    invalid_finding["Id"] = "test-finding-002"
    invalid_finding["Severity"]["Label"] = "INVALID_LABEL"

    response = client.batch_import_findings(Findings=[invalid_finding])

    assert response["SuccessCount"] == 1
    assert response["FailedCount"] == 0
    assert len(response["FailedFindings"]) == 0


# @mock_aws
# def test_get_findings_invalid_parameters():
#     """Test getting findings with invalid parameters."""
#     client = boto3.client("securityhub", region_name="us-east-1")

#     # Test invalid MaxResults
#     with pytest.raises(ClientError) as exc:
#         client.get_findings(MaxResults=0)
#     err = exc.value.response["Error"]
#     assert err["Code"] == "InvalidInputException"
#     assert "MaxResults must be a number greater than 0" in err["Message"]

# @mock_aws
# def test_batch_import_findings_validation():
#     """Test batch import findings with invalid input."""
#     client = boto3.client("securityhub", region_name="us-east-1")

#     # Test missing required fields
#     invalid_finding = {
#         "Id": "test-finding-001",
#         # Missing other required fields
#     }

#     response = client.batch_import_findings(Findings=[invalid_finding])
#     assert response["FailedCount"] == 1
#     assert response["SuccessCount"] == 0
#     assert len(response["FailedFindings"]) == 1
#     assert "required fields" in response["FailedFindings"][0]["ErrorMessage"]

#     # Test empty resources array
#     invalid_finding = {
#         "AwsAccountId": DEFAULT_ACCOUNT_ID,
#         "CreatedAt": "2024-01-01T00:00:00.000Z",
#         "UpdatedAt": "2024-01-01T00:00:00.000Z",
#         "Description": "Test finding",
#         "GeneratorId": "test-generator",
#         "Id": "test-finding-001",
#         "ProductArn": f"arn:aws:securityhub:{client.meta.region_name}:{DEFAULT_ACCOUNT_ID}:product/{DEFAULT_ACCOUNT_ID}/default",
#         "Resources": [],  # Empty resources array
#         "SchemaVersion": "2018-10-08",
#         "Severity": {"Label": "HIGH"},
#         "Title": "Test Finding",
#         "Types": ["Software and Configuration Checks"],
#     }

#     response = client.batch_import_findings(Findings=[invalid_finding])
#     assert response["FailedCount"] == 1
#     assert response["SuccessCount"] == 0
#     assert len(response["FailedFindings"]) == 1
#     assert "must contain at least one resource" in response["FailedFindings"][0]["ErrorMessage"]
