"""Unit tests for securityhub-supported APIs."""

import os
from unittest import mock

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
    if not settings.TEST_DECORATOR_MODE:
        # Can't set env variables in ServerMode
        return

    org_client = boto3.client("organizations", region_name="us-east-1")
    org_client.create_organization(FeatureSet="ALL")

    org_client.create_account(
        AccountName="SecurityHubAdmin",
        Email="securityhub.admin@example.com",
    )

    accounts = org_client.list_accounts()["Accounts"]
    admin_account = next(acc for acc in accounts if acc["Name"] == "SecurityHubAdmin")
    admin_account_id = admin_account["Id"]

    client = boto3.client("securityhub", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.enable_organization_admin_account(AdminAccountId="111111111111")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert "is not a member of organization" in err["Message"]

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        non_management_client = boto3.client("securityhub", region_name="us-east-1")
        with pytest.raises(ClientError) as exc:
            non_management_client.enable_organization_admin_account(
                AdminAccountId=admin_account_id
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "AccessDeniedException"

    client.enable_organization_admin_account(AdminAccountId=admin_account_id)

    get_resp = client.get_administrator_account()
    assert "Administrator" not in get_resp


@mock_aws
def test_enable_organization_admin_account_without_org():
    client = boto3.client("securityhub", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.enable_organization_admin_account(AdminAccountId="123456789012")

    err = exc.value.response["Error"]
    assert err["Code"] == "AWSOrganizationsNotInUseException"


@mock_aws
def test_enable_organization_admin_account_non_management():
    if not settings.TEST_DECORATOR_MODE:
        # Can't set env variables in ServerMode
        return

    org_client = boto3.client("organizations", region_name="us-east-1")
    org_client.create_organization(FeatureSet="ALL")

    admin_account_id = "123456789012"
    org_client.create_account(
        AccountName="SecurityHubAdmin",
        Email="securityhub.admin@example.com",
    )

    accounts = org_client.list_accounts()["Accounts"]
    admin_account = next(acc for acc in accounts if acc["Name"] == "SecurityHubAdmin")
    admin_account_id = admin_account["Id"]

    # Enable SecurityHub admin account from non-management account
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        client = boto3.client("securityhub", region_name="us-east-1")
        with pytest.raises(ClientError) as exc:
            client.enable_organization_admin_account(AdminAccountId=admin_account_id)

        err = exc.value.response["Error"]
        assert err["Code"] == "AccessDeniedException"


@mock_aws
def test_update_organization_configuration():
    if not settings.TEST_DECORATOR_MODE:
        return

    client = boto3.client("securityhub", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.update_organization_configuration(
            AutoEnable=True, AutoEnableStandards="DEFAULT"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        "AWS Organizations is not in use or not configured for this account"
        in err["Message"]
    )

    org_client = boto3.client("organizations", region_name="us-east-1")
    org_client.create_organization(FeatureSet="ALL")

    org_client.create_account(
        AccountName="SecurityHubAdmin",
        Email="securityhub.admin@example.com",
    )

    accounts = org_client.list_accounts()["Accounts"]
    admin_account = next(acc for acc in accounts if acc["Name"] == "SecurityHubAdmin")
    admin_account_id = admin_account["Id"]

    client = boto3.client("securityhub", region_name="us-east-1")

    # Test ResourceNotFoundException when no admin account is designated
    with pytest.raises(ClientError) as exc:
        client.update_organization_configuration(
            AutoEnable=True, AutoEnableStandards="DEFAULT"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "no administrator account has been designated" in err["Message"]

    client.enable_organization_admin_account(AdminAccountId=admin_account_id)

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")
        with pytest.raises(ClientError) as exc:
            admin_client.update_organization_configuration(
                AutoEnable=True, AutoEnableStandards="INVALID_VALUE"
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidInputException"
        assert "AutoEnableStandards must be either NONE or DEFAULT" in err["Message"]

        with pytest.raises(ClientError) as exc:
            admin_client.update_organization_configuration(
                AutoEnable=True,
                AutoEnableStandards="NONE",
                OrganizationConfiguration={
                    "ConfigurationType": "CENTRAL",
                    "Status": "ENABLED",
                    "StatusMessage": "Configuration centralized",
                },
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert (
            "AutoEnable must be false when ConfigurationType is CENTRAL"
            in err["Message"]
        )

        with pytest.raises(ClientError) as exc:
            admin_client.update_organization_configuration(
                AutoEnable=False,
                AutoEnableStandards="DEFAULT",
                OrganizationConfiguration={
                    "ConfigurationType": "CENTRAL",
                    "Status": "ENABLED",
                    "StatusMessage": "Configuration centralized",
                },
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert (
            "AutoEnableStandards must be NONE when ConfigurationType is CENTRAL"
            in err["Message"]
        )

        admin_client.update_organization_configuration(
            AutoEnable=False,
            AutoEnableStandards="NONE",
            OrganizationConfiguration={
                "ConfigurationType": "CENTRAL",
                "Status": "ENABLED",
                "StatusMessage": "Configuration centralized",
            },
        )

        describe_resp = admin_client.describe_organization_configuration()
        assert describe_resp["AutoEnable"] is False
        assert describe_resp["AutoEnableStandards"] == "NONE"
        assert (
            describe_resp["OrganizationConfiguration"]["ConfigurationType"] == "CENTRAL"
        )
        assert describe_resp["OrganizationConfiguration"]["Status"] == "ENABLED"
        assert (
            describe_resp["OrganizationConfiguration"]["StatusMessage"]
            == "Configuration centralized"
        )

    # Test non-admin account access
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": DEFAULT_ACCOUNT_ID}):
        non_admin_client = boto3.client("securityhub", region_name="us-east-1")
        with pytest.raises(ClientError) as exc:
            non_admin_client.update_organization_configuration(
                AutoEnable=True,
                AutoEnableStandards="DEFAULT",
            )
        assert exc.value.response["Error"]["Code"] == "AccessDeniedException"


@mock_aws
def test_multiple_accounts_in_organization():
    if not settings.TEST_DECORATOR_MODE:
        # Can't set env variables in ServerMode
        return

    org_client = boto3.client("organizations", region_name="us-east-1")
    org_client.create_organization(FeatureSet="ALL")

    org_client.create_account(
        AccountName="SecurityHubAdmin",
        Email="securityhub.admin@example.com",
    )
    org_client.create_account(
        AccountName="Member1",
        Email="member1@example.com",
    )
    org_client.create_account(
        AccountName="Member2",
        Email="member2@example.com",
    )

    accounts = org_client.list_accounts()["Accounts"]
    admin_account = next(acc for acc in accounts if acc["Name"] == "SecurityHubAdmin")
    member1_account = next(acc for acc in accounts if acc["Name"] == "Member1")
    member2_account = next(acc for acc in accounts if acc["Name"] == "Member2")

    admin_account_id = admin_account["Id"]
    member_account_id_1 = member1_account["Id"]
    member_account_id_2 = member2_account["Id"]

    client = boto3.client("securityhub", region_name="us-east-1")
    client.enable_organization_admin_account(AdminAccountId=admin_account_id)

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")
        admin_client.update_organization_configuration(
            AutoEnable=True,
            AutoEnableStandards="NONE",
        )

    admin_response = client.get_administrator_account()
    assert "Administrator" not in admin_response

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")
        admin_response = admin_client.get_administrator_account()
        assert "Administrator" not in admin_response

    # Check from member account 1 - should see admin details since auto_enable is True
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id_1}):
        member_client_1 = boto3.client("securityhub", region_name="us-east-1")
        admin_response_1 = member_client_1.get_administrator_account()

        assert "Administrator" in admin_response_1
        assert admin_response_1["Administrator"]["AccountId"] == admin_account_id
        assert admin_response_1["Administrator"]["MemberStatus"] == "ENABLED"

    # Check from member account 2 - should see admin details since auto_enable is True
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id_2}):
        member_client_2 = boto3.client("securityhub", region_name="us-east-1")
        admin_response_2 = member_client_2.get_administrator_account()

        assert "Administrator" in admin_response_2
        assert admin_response_2["Administrator"]["AccountId"] == admin_account_id
        assert admin_response_2["Administrator"]["MemberStatus"] == "ENABLED"


@mock_aws
def test_organization_auto_enable_disabled():
    if not settings.TEST_DECORATOR_MODE:
        # Can't set env variables in ServerMode
        return

    org_client = boto3.client("organizations", region_name="us-east-1")
    org_client.create_organization(FeatureSet="ALL")

    org_client.create_account(
        AccountName="SecurityHubAdmin",
        Email="securityhub.admin@example.com",
    )
    org_client.create_account(
        AccountName="Member1",
        Email="member1@example.com",
    )

    accounts = org_client.list_accounts()["Accounts"]
    admin_account = next(acc for acc in accounts if acc["Name"] == "SecurityHubAdmin")
    member1_account = next(acc for acc in accounts if acc["Name"] == "Member1")

    admin_account_id = admin_account["Id"]
    member_account_id = member1_account["Id"]

    client = boto3.client("securityhub", region_name="us-east-1")
    client.enable_organization_admin_account(AdminAccountId=admin_account_id)

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")
        admin_client.update_organization_configuration(
            AutoEnable=False,
            AutoEnableStandards="NONE",
        )

    admin_response = client.get_administrator_account()
    assert "Administrator" not in admin_response

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")
        admin_response = admin_client.get_administrator_account()
        assert "Administrator" not in admin_response

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id}):
        member_client = boto3.client("securityhub", region_name="us-east-1")
        member_response = member_client.get_administrator_account()
        assert "Administrator" in member_response
        assert member_response["Administrator"]["AccountId"] == admin_account_id
        assert member_response["Administrator"]["MemberStatus"] == "ENABLED"


@mock_aws
def test_describe_organization_configuration_access_control():
    if not settings.TEST_DECORATOR_MODE:
        # Can't set env variables in ServerMode
        return

    org_client = boto3.client("organizations", region_name="us-east-1")
    org_client.create_organization(FeatureSet="ALL")

    org_client.create_account(
        AccountName="SecurityHubAdmin",
        Email="securityhub.admin@example.com",
    )

    accounts = org_client.list_accounts()["Accounts"]
    admin_account = next(acc for acc in accounts if acc["Name"] == "SecurityHubAdmin")
    admin_account_id = admin_account["Id"]

    client = boto3.client("securityhub", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.describe_organization_configuration()
    err = exc.value.response["Error"]
    assert err["Code"] == "AccessDeniedException"
    assert "You do not have sufficient access to perform this action" in err["Message"]

    client.enable_organization_admin_account(AdminAccountId=admin_account_id)

    with pytest.raises(ClientError) as exc:
        client.describe_organization_configuration()
    err = exc.value.response["Error"]
    assert err["Code"] == "AccessDeniedException"
    assert "You do not have sufficient access to perform this action" in err["Message"]

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")
        response = admin_client.describe_organization_configuration()
        assert "AutoEnable" in response
        assert "MemberAccountLimitReached" in response
        assert "AutoEnableStandards" in response
        assert "OrganizationConfiguration" in response

    org_client.create_account(
        AccountName="Member1",
        Email="member1@example.com",
    )

    accounts = org_client.list_accounts()["Accounts"]
    member_account = next(acc for acc in accounts if acc["Name"] == "Member1")
    member_account_id = member_account["Id"]
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id}):
        member_client = boto3.client("securityhub", region_name="us-east-1")
        with pytest.raises(ClientError) as exc:
            member_client.describe_organization_configuration()
        err = exc.value.response["Error"]
        assert err["Code"] == "AccessDeniedException"
        assert (
            "You do not have sufficient access to perform this action" in err["Message"]
        )


@mock_aws
def test_multiple_admin_member_relationships():
    if not settings.TEST_DECORATOR_MODE:
        # Can't set env variables in ServerMode
        return

    """Different accounts can be admins of different member accounts.
    - Account A is admin of Account B
    - Account C is admin of Account D
    """
    org_client_1 = boto3.client("organizations", region_name="us-east-1")
    org_client_1.create_organization(FeatureSet="ALL")

    org_client_1.create_account(
        AccountName="AdminA",
        Email="admin.a@bestcompany.com",
    )
    org_client_1.create_account(
        AccountName="MemberB",
        Email="member.b@bestcompany.com",
    )

    accounts_1 = org_client_1.list_accounts()["Accounts"]
    admin_a = next(acc for acc in accounts_1 if acc["Name"] == "AdminA")
    member_b = next(acc for acc in accounts_1 if acc["Name"] == "MemberB")

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": "999999999999"}):
        org_client_2 = boto3.client("organizations", region_name="us-east-1")
        org_client_2.create_organization(FeatureSet="ALL")

        # Create accounts C and D
        org_client_2.create_account(
            AccountName="AdminC",
            Email="admin.c@bestcompany.com",
        )
        org_client_2.create_account(
            AccountName="MemberD",
            Email="member.d@bestcompany.com",
        )

        accounts_2 = org_client_2.list_accounts()["Accounts"]
        admin_c = next(acc for acc in accounts_2 if acc["Name"] == "AdminC")
        member_d = next(acc for acc in accounts_2 if acc["Name"] == "MemberD")

    # Setup A as admin of B
    client_1 = boto3.client("securityhub", region_name="us-east-1")
    client_1.enable_organization_admin_account(AdminAccountId=admin_a["Id"])

    # Setup C as admin of D
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": "999999999999"}):
        client_2 = boto3.client("securityhub", region_name="us-east-1")
        client_2.enable_organization_admin_account(AdminAccountId=admin_c["Id"])

    # Verify B sees A as its admin
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_b["Id"]}):
        member_b_client = boto3.client("securityhub", region_name="us-east-1")
        admin_response_b = member_b_client.get_administrator_account()
        assert "Administrator" in admin_response_b
        assert admin_response_b["Administrator"]["AccountId"] == admin_a["Id"]

    # Verify D sees C as its admin
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_d["Id"]}):
        member_d_client = boto3.client("securityhub", region_name="us-east-1")
        admin_response_d = member_d_client.get_administrator_account()
        assert "Administrator" in admin_response_d
        assert admin_response_d["Administrator"]["AccountId"] == admin_c["Id"]

    # Verify B doesn't see C as its admin
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_b["Id"]}):
        member_b_client = boto3.client("securityhub", region_name="us-east-1")
        admin_response_b = member_b_client.get_administrator_account()
        assert "Administrator" in admin_response_b
        assert admin_response_b["Administrator"]["AccountId"] != admin_c["Id"]

    # Verify D doesn't see A as its admin
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_d["Id"]}):
        member_d_client = boto3.client("securityhub", region_name="us-east-1")
        admin_response_d = member_d_client.get_administrator_account()
        assert "Administrator" in admin_response_d
        assert admin_response_d["Administrator"]["AccountId"] != admin_a["Id"]


@mock_aws
def test_describe_organization_configuration():
    if not settings.TEST_DECORATOR_MODE:
        # Can't set env variables in ServerMode
        return

    org_client = boto3.client("organizations", region_name="us-east-1")
    org_client.create_organization(FeatureSet="ALL")

    org_client.create_account(
        AccountName="SecurityHubAdmin",
        Email="securityhub.admin@example.com",
    )

    accounts = org_client.list_accounts()["Accounts"]
    admin_account = next(acc for acc in accounts if acc["Name"] == "SecurityHubAdmin")
    admin_account_id = admin_account["Id"]

    client = boto3.client("securityhub", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.describe_organization_configuration()
    err = exc.value.response["Error"]
    assert err["Code"] == "AccessDeniedException"
    assert "You do not have sufficient access to perform this action" in err["Message"]

    client.enable_organization_admin_account(AdminAccountId=admin_account_id)

    with pytest.raises(ClientError) as exc:
        client.describe_organization_configuration()
    err = exc.value.response["Error"]
    assert err["Code"] == "AccessDeniedException"
    assert "You do not have sufficient access to perform this action" in err["Message"]

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")
        response = admin_client.describe_organization_configuration()
        assert "AutoEnable" in response
        assert "MemberAccountLimitReached" in response
        assert "AutoEnableStandards" in response
        assert "OrganizationConfiguration" in response


@mock_aws
def test_get_administrator_account():
    if not settings.TEST_DECORATOR_MODE:
        return

    org_client = boto3.client("organizations", region_name="us-east-1")
    org_client.create_organization(FeatureSet="ALL")

    org_client.create_account(
        AccountName="SecurityHubAdmin",
        Email="securityhub.admin@example.com",
    )
    org_client.create_account(
        AccountName="Member",
        Email="member@example.com",
    )

    accounts = org_client.list_accounts()["Accounts"]
    admin_account = next(acc for acc in accounts if acc["Name"] == "SecurityHubAdmin")
    member_account = next(acc for acc in accounts if acc["Name"] == "Member")
    admin_account_id = admin_account["Id"]
    member_account_id = member_account["Id"]

    client = boto3.client("securityhub", region_name="us-east-1")

    response = client.get_administrator_account()
    assert "Administrator" not in response

    client.enable_organization_admin_account(AdminAccountId=admin_account_id)

    response = client.get_administrator_account()
    assert "Administrator" not in response

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": admin_account_id}):
        admin_client = boto3.client("securityhub", region_name="us-east-1")
        response = admin_client.get_administrator_account()
        assert "Administrator" not in response

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": member_account_id}):
        member_client = boto3.client("securityhub", region_name="us-east-1")
        response = member_client.get_administrator_account()
        assert "Administrator" in response
        assert response["Administrator"]["AccountId"] == admin_account_id
        assert response["Administrator"]["MemberStatus"] == "ENABLED"
