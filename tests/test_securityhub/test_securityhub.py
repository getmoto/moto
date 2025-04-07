"""Unit tests for securityhub-supported APIs."""

import os
from unittest import SkipTest, mock

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID


@mock_aws
def test_get_findings():
    client = boto3.client("securityhub", region_name="us-east-1")

    test_finding = {
        "AwsAccountId": DEFAULT_ACCOUNT_ID,
        "CreatedAt": "2024-01-01T00:00:00.001Z",
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

    import_response = client.batch_import_findings(Findings=[test_finding])
    assert import_response["SuccessCount"] == 1

    response = client.get_findings()

    assert "Findings" in response
    assert isinstance(response["Findings"], list)
    assert len(response["Findings"]) == 1
    finding = response["Findings"][0]
    assert finding["Id"] == "test-finding-001"
    assert finding["SchemaVersion"] == "2018-10-08"


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


@mock_aws
def test_get_findings_invalid_parameters():
    client = boto3.client("securityhub", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_findings(MaxResults=101)

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert "MaxResults must be a number between 1 and 100" in err["Message"]


@mock_aws
def test_batch_import_multiple_findings():
    client = boto3.client("securityhub", region_name="us-east-1")

    findings = [
        {
            "AwsAccountId": DEFAULT_ACCOUNT_ID,
            "CreatedAt": "2024-01-01T00:00:00.000Z",
            "UpdatedAt": "2024-01-01T00:00:00.000Z",
            "Description": f"Test finding description {i}",
            "GeneratorId": "test-generator",
            "Id": f"test-finding-{i:03d}",
            "ProductArn": f"arn:aws:securityhub:{client.meta.region_name}:{DEFAULT_ACCOUNT_ID}:product/{DEFAULT_ACCOUNT_ID}/default",
            "Resources": [{"Id": f"test-resource-{i}", "Type": "AwsEc2Instance"}],
            "SchemaVersion": "2018-10-08",
            "Severity": {"Label": "HIGH"},
            "Title": f"Test Finding {i}",
            "Types": ["Software and Configuration Checks"],
        }
        for i in range(1, 4)
    ]

    import_response = client.batch_import_findings(Findings=findings)
    assert import_response["SuccessCount"] == 3
    assert import_response["FailedCount"] == 0
    assert import_response["FailedFindings"] == []

    get_response = client.get_findings()
    assert "Findings" in get_response
    assert isinstance(get_response["Findings"], list)
    assert len(get_response["Findings"]) == 3

    imported_ids = {finding["Id"] for finding in get_response["Findings"]}
    expected_ids = {f"test-finding-{i:03d}" for i in range(1, 4)}
    assert imported_ids == expected_ids


@mock_aws
def test_get_findings_max_results():
    client = boto3.client("securityhub", region_name="us-east-1")

    findings = [
        {
            "AwsAccountId": DEFAULT_ACCOUNT_ID,
            "CreatedAt": "2024-01-01T00:00:00.000Z",
            "UpdatedAt": "2024-01-01T00:00:00.000Z",
            "Description": f"Test finding description {i}",
            "GeneratorId": "test-generator",
            "Id": f"test-finding-{i:03d}",
            "ProductArn": f"arn:aws:securityhub:{client.meta.region_name}:{DEFAULT_ACCOUNT_ID}:product/{DEFAULT_ACCOUNT_ID}/default",
            "Resources": [{"Id": f"test-resource-{i}", "Type": "AwsEc2Instance"}],
            "SchemaVersion": "2018-10-08",
            "Severity": {"Label": "HIGH"},
            "Title": f"Test Finding {i}",
            "Types": ["Software and Configuration Checks"],
        }
        for i in range(1, 4)
    ]

    import_response = client.batch_import_findings(Findings=findings)
    assert import_response["SuccessCount"] == 3

    get_response = client.get_findings(MaxResults=1)
    assert "Findings" in get_response
    assert isinstance(get_response["Findings"], list)
    assert len(get_response["Findings"]) == 1
    assert "NextToken" in get_response


@mock_aws
def test_enable_organization_admin_account():
    client = boto3.client("securityhub", region_name="us-east-1")

    admin_account_id = "123456789012"

    client.enable_organization_admin_account(AdminAccountId=admin_account_id)
    get_resp = client.get_administrator_account()
    assert get_resp["Administrator"]["AccountId"] == admin_account_id


@mock_aws
def test_update_organization_configuration():
    client = boto3.client("securityhub", region_name="us-east-1")

    client.update_organization_configuration(
        AutoEnable=True,
        AutoEnableStandards="NONE",
        OrganizationConfiguration={
            "ConfigurationType": "CENTRAL",
            "Status": "ENABLED",
            "StatusMessage": "Configuration centralized",
        },
    )

    describe_resp = client.describe_organization_configuration()
    assert describe_resp["AutoEnable"] is True
    assert describe_resp["AutoEnableStandards"] == "NONE"
    assert describe_resp["OrganizationConfiguration"]["ConfigurationType"] == "CENTRAL"
    assert describe_resp["OrganizationConfiguration"]["Status"] == "ENABLED"
    assert (
        describe_resp["OrganizationConfiguration"]["StatusMessage"]
        == "Configuration centralized"
    )


@mock_aws
def test_multiple_accounts_in_organization():
    admin_account_id = "111111111111"
    member_account_id_1 = "222222222222"
    member_account_id_2 = "333333333333"
    alternate_admin_account_id = "444444444444"

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")

        admin_client.enable_organization_admin_account(AdminAccountId=admin_account_id)

        admin_client.update_organization_configuration(
            AutoEnable=True,
            AutoEnableStandards="NONE",
        )

        admin_response = admin_client.get_administrator_account()
        assert "Administrator" in admin_response
        assert admin_response["Administrator"]["AccountId"] == admin_account_id

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id_1}):
        member_client_1 = boto3.client("securityhub", region_name="us-east-1")
        admin_response_1 = member_client_1.get_administrator_account()

        assert "Administrator" in admin_response_1
        assert admin_response_1["Administrator"]["AccountId"] == admin_account_id
        assert admin_response_1["Administrator"]["MemberStatus"] == "ENABLED"

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id_2}):
        member_client_2 = boto3.client("securityhub", region_name="us-east-1")
        admin_response_2 = member_client_2.get_administrator_account()

        assert "Administrator" in admin_response_2
        assert admin_response_2["Administrator"]["AccountId"] == admin_account_id
        assert admin_response_2["Administrator"]["MemberStatus"] == "ENABLED"

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client.enable_organization_admin_account(
            AdminAccountId=alternate_admin_account_id
        )

        admin_response = admin_client.get_administrator_account()
        assert "Administrator" in admin_response
        assert (
            admin_response["Administrator"]["AccountId"] == alternate_admin_account_id
        )

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id_1}):
        member_client_1 = boto3.client("securityhub", region_name="us-east-1")
        admin_response_1 = member_client_1.get_administrator_account()

        assert "Administrator" in admin_response_1
        assert (
            admin_response_1["Administrator"]["AccountId"] == alternate_admin_account_id
        )
        assert admin_response_1["Administrator"]["MemberStatus"] == "ENABLED"


@mock_aws
def test_organization_auto_enable_disabled():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Test runs successfully locally, but not in CI")

    admin_account_id = "111111111111"
    member_account_id = "222222222222"

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")

        admin_client.enable_organization_admin_account(AdminAccountId=admin_account_id)

        admin_client.update_organization_configuration(
            AutoEnable=False,
            AutoEnableStandards="NONE",
        )

        config_response = admin_client.describe_organization_configuration()
        assert config_response["AutoEnable"] is False

        admin_response = admin_client.get_administrator_account()
        assert "Administrator" in admin_response
        assert admin_response["Administrator"]["AccountId"] == admin_account_id

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id}):
        member_client = boto3.client("securityhub", region_name="us-east-1")
        member_admin_response = member_client.get_administrator_account()

        assert "Administrator" not in member_admin_response

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")
        admin_client.update_organization_configuration(AutoEnable=True)

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id}):
        member_client = boto3.client("securityhub", region_name="us-east-1")
        member_admin_response = member_client.get_administrator_account()

        assert "Administrator" in member_admin_response
        assert member_admin_response["Administrator"]["AccountId"] == admin_account_id
        assert member_admin_response["Administrator"]["MemberStatus"] == "ENABLED"


@mock_aws
def test_get_administrator_account():
    admin_account_id = "123456789012"

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        client = boto3.client("securityhub", region_name="us-east-1")

        client.enable_organization_admin_account(AdminAccountId=admin_account_id)

        resp = client.get_administrator_account()
        assert "Administrator" in resp
        assert resp["Administrator"]["AccountId"] == admin_account_id
        assert resp["Administrator"]["MemberStatus"] == "ENABLED"
        assert "InvitationId" in resp["Administrator"]
        assert "InvitedAt" in resp["Administrator"]
