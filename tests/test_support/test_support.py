import boto3
import pytest

from moto import mock_support


@mock_support
def test_describe_trusted_advisor_checks_returns_amount_of_checks():
    """Test that trusted advisor returns 104 checks."""
    client = boto3.client("support", "us-east-1")
    response = client.describe_trusted_advisor_checks(language="en")
    assert len(response["checks"]) == 104


@mock_support
def test_describe_trusted_advisor_checks_returns_an_expected_id():
    """Test that a random check id is returned."""
    client = boto3.client("support", "us-east-1")
    response = client.describe_trusted_advisor_checks(language="en")
    check_ids = []
    for check in response["checks"]:
        check_ids.append(check["id"])

    assert "zXCkfM1nI3" in check_ids


@mock_support
def test_describe_trusted_advisor_checks_returns_an_expected_check_name():
    """Test that a random check name is returned."""
    client = boto3.client("support", "us-east-1")
    response = client.describe_trusted_advisor_checks(language="en")
    check_names = []
    for check in response["checks"]:
        check_names.append(check["name"])

    assert "Unassociated Elastic IP Addresses" in check_names


@mock_support
def test_refresh_trusted_advisor_check_returns_expected_check():
    """Test refresh of a trusted advisor check returns check id in response."""
    client = boto3.client("support", "us-east-1")
    check_name = "XXXIIIY"
    response = client.refresh_trusted_advisor_check(checkId=check_name)
    assert response["status"]["checkId"] == check_name


@mock_support
def test_refresh_trusted_advisor_check_returns_an_expected_status():
    """Test refresh of a trusted advisor check returns an expected status."""
    client = boto3.client("support", "us-east-1")
    possible_statuses = ["none", "enqueued", "processing", "success", "abandoned"]
    check_name = "XXXIIIY"
    response = client.refresh_trusted_advisor_check(checkId=check_name)
    actual_status = response["status"]["status"]
    assert actual_status in possible_statuses


@pytest.mark.parametrize(
    "possible_statuses",
    [
        ["none", "enqueued", "processing"],
        ["none", "enqueued", "processing", "success", "abandoned"],
    ],
)
@mock_support
def test_refresh_trusted_advisor_check_cycles_to_new_status_on_each_call(
    possible_statuses,
):
    """Test when check is called 3 times, 3 expected statuses are returned."""
    client = boto3.client("support", "us-east-1")
    check_name = "XXXIIIY"
    actual_statuses = []

    for _ in possible_statuses:
        response = client.refresh_trusted_advisor_check(checkId=check_name)
        actual_statuses.append(response["status"]["status"])

    assert actual_statuses == possible_statuses


@mock_support
def test_refresh_trusted_advisor_check_cycles_to_new_status_on_with_two_checks():
    """Test next expected status is returned when additional checks are made."""
    client = boto3.client("support", "us-east-1")
    check_1_name = "XXXIIIY"
    check_2_name = "XXXIIIZ"
    check_1_statuses = []
    check_2_statuses = []
    possible_statuses = [
        "none",
        "enqueued",
        "processing",
        "success",
        "abandoned",
    ]

    for _ in possible_statuses:
        response = client.refresh_trusted_advisor_check(checkId=check_1_name)
        check_1_statuses.append(response["status"]["status"])

    for _ in possible_statuses:
        response = client.refresh_trusted_advisor_check(checkId=check_2_name)
        check_2_statuses.append(response["status"]["status"])

    assert (
        check_1_statuses == possible_statuses and check_2_statuses == possible_statuses
    )


@mock_support
def test_refresh_trusted_advisor_check_cycle_continues_on_full_cycle():
    """Test that after cycling through all statuses, check continues cycle."""
    client = boto3.client("support", "us-east-1")
    check_name = "XXXIIIY"
    possible_statuses = [
        "none",
        "enqueued",
        "processing",
        "success",
        "abandoned",
    ]

    for _ in possible_statuses:
        client.refresh_trusted_advisor_check(checkId=check_name)

    expected_none_response = client.refresh_trusted_advisor_check(checkId=check_name)

    assert expected_none_response["status"]["status"] == "none"


@mock_support
def test_support_case_is_closed():
    """Test that on closing a case, the correct response is returned."""
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )
    case_id = create_case_response["caseId"]

    resolve_case_response = client.resolve_case(caseId=case_id)

    possible_case_status = [
        "opened",
        "pending-customer-action",
        "reopened",
        "unassigned",
        "resolved",
        "work-in-progress",
    ]
    expected_initial_case = [resolve_case_response["initialCaseStatus"]]
    expected_final_case = "resolved"

    assert set(expected_initial_case).issubset(possible_case_status) is True

    assert expected_final_case == "resolved"


@mock_support
def test_support_case_created():
    """Test support request creation response contains case ID."""
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    assert len(create_case_response["caseId"]) == 38


@pytest.mark.parametrize(
    "key,value",
    [
        ("subject", "test_subject"),
        ("serviceCode", "test_service_code"),
        ("severityCode", "normal"),
        ("categoryCode", "test_category_code"),
        ("language", "test_language"),
    ],
)
@mock_support
def test_support_created_case_can_be_described(key, value):
    """Test support request creation can be described."""

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]
    describe_cases_response = client.describe_cases(
        caseIdList=[case_id_list],
        displayId="test_display_id",
        afterTime="test_after_time",
        beforeTime="test_before_time",
        includeResolvedCases=True,
        nextToken="test_next_token",
        maxResults=137,
        language="test_lanauage",
        includeCommunications=True,
    )

    actual_case_id = describe_cases_response["cases"][0][key]

    assert actual_case_id == value


@pytest.mark.parametrize(
    "key,value",
    [
        ("subject", "test_subject"),
        ("serviceCode", "test_service_code"),
        ("severityCode", "normal"),
        ("categoryCode", "test_category_code"),
        ("language", "test_language"),
    ],
)
@mock_support
def test_support_created_case_can_be_described_without_next_token(key, value):
    """Test support request creation can be described without next token."""

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]
    describe_cases_response = client.describe_cases(
        caseIdList=[case_id_list],
        displayId="test_display_id",
        afterTime="test_after_time",
        beforeTime="test_before_time",
        includeResolvedCases=True,
        language="test_lanauage",
        includeCommunications=True,
        maxResults=137,
    )

    actual_case_id = describe_cases_response["cases"][0][key]

    assert actual_case_id == value


@pytest.mark.parametrize(
    "key,value",
    [
        ("subject", "test_subject"),
        ("serviceCode", "test_service_code"),
        ("severityCode", "normal"),
        ("categoryCode", "test_category_code"),
        ("language", "test_language"),
    ],
)
@mock_support
def test_support_created_case_can_be_described_without_max_results(key, value):
    """Test support request creation can be described without max_results."""

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]
    describe_cases_response = client.describe_cases(
        caseIdList=[case_id_list],
        displayId="test_display_id",
        afterTime="test_after_time",
        beforeTime="test_before_time",
        includeResolvedCases=True,
        language="test_lanauage",
        nextToken="test_next_token",
        includeCommunications=True,
    )

    actual_case_id = describe_cases_response["cases"][0][key]

    assert actual_case_id == value


@pytest.mark.parametrize(
    "key,value",
    [
        ("subject", "test_subject"),
        ("serviceCode", "test_service_code"),
        ("severityCode", "normal"),
        ("categoryCode", "test_category_code"),
        ("language", "test_language"),
    ],
)
@mock_support
def test_support_created_case_can_be_described_without_max_results_or_next_token(
    key, value
):
    """Test support request creation can be described without next token."""

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]
    describe_cases_response = client.describe_cases(
        caseIdList=[case_id_list],
        displayId="test_display_id",
        afterTime="test_after_time",
        beforeTime="test_before_time",
        includeResolvedCases=True,
        language="test_lanauage",
        includeCommunications=True,
    )

    actual_case_id = describe_cases_response["cases"][0][key]

    assert actual_case_id == value


@mock_support
def test_support_created_case_can_be_described_without_params():
    """Test support request creation without params can be described."""

    client = boto3.client("support", "us-east-1")

    describe_cases_response = client.describe_cases()
    assert describe_cases_response["cases"] == []

    client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    describe_cases_response = client.describe_cases()
    assert len(describe_cases_response["cases"]) == 1


@mock_support
def test_support_created_case_cc_email_correct():
    """Test a support request can be described with correct cc email."""

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]
    describe_cases_response = client.describe_cases(
        caseIdList=[case_id_list],
        displayId="test_display_id",
        afterTime="test_after_time",
        beforeTime="test_before_time",
        includeResolvedCases=True,
        nextToken="test_next_token",
        maxResults=137,
        language="test_lanauage",
        includeCommunications=True,
    )

    actual_case_id = describe_cases_response["cases"][0]["ccEmailAddresses"][0]

    assert actual_case_id == "test_email_cc"


@mock_support
def test_support_case_include_resolved_defaults_to_false():
    """Test support request description doesn't include resolved cases."""
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]

    for _ in range(3):
        describe_cases_response = client.describe_cases(
            caseIdList=[case_id_list],
            displayId="test_display_id",
            afterTime="test_after_time",
            beforeTime="test_before_time",
            nextToken="test_next_token",
            maxResults=137,
            language="test_lanauage",
            includeCommunications=True,
        )
    actual = describe_cases_response["cases"]

    assert case_id_list not in actual


@mock_support
def test_support_case_include_communications_defaults_to_true():
    """Test support request description includes communications cases."""
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]

    describe_cases_response = client.describe_cases(
        caseIdList=[case_id_list],
        displayId="test_display_id",
        afterTime="test_after_time",
        beforeTime="test_before_time",
        nextToken="test_next_token",
        maxResults=137,
        language="test_lanauage",
    )

    actual = describe_cases_response["cases"][0]

    assert "recentCommunications" in actual


@mock_support
def test_multiple_support_created_cases_can_be_described():
    """Test creation of multiple support requests descriptions."""
    client = boto3.client("support", "us-east-1")
    create_case_response_1 = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    create_case_response_2 = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = [create_case_response_1["caseId"], create_case_response_2["caseId"]]
    describe_cases_response = client.describe_cases(
        caseIdList=case_id_list,
        displayId="test_display_id",
        afterTime="test_after_time",
        beforeTime="test_before_time",
        includeResolvedCases=True,
        nextToken="test_next_token",
        maxResults=137,
        language="test_lanauage",
        includeCommunications=True,
    )

    actual_case_id_1 = describe_cases_response["cases"][0]["caseId"]
    actual_case_id_2 = describe_cases_response["cases"][1]["caseId"]

    assert actual_case_id_1 == case_id_list[0]
    assert actual_case_id_2 == case_id_list[1]


@mock_support
def test_support_created_case_can_be_described_and_contains_communications_when_set_to_true():
    """Test support request description when includeResolvedCases=True.

    The suport request description should includes comms.
    """
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]
    describe_cases_response = client.describe_cases(
        caseIdList=[case_id_list],
        displayId="test_display_id",
        afterTime="test_after_time",
        beforeTime="test_before_time",
        includeResolvedCases=True,
        nextToken="test_next_token",
        maxResults=137,
        language="test_lanauage",
        includeCommunications=True,
    )

    actual_recent_comm = describe_cases_response["cases"][0]
    assert "recentCommunications" in actual_recent_comm


@mock_support
def test_support_created_case_can_be_described_and_does_not_contain_communications_when_false():
    """Test support request creation when includeCommunications=False."""

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]
    describe_cases_response = client.describe_cases(
        caseIdList=[case_id_list],
        displayId="test_display_id",
        afterTime="test_after_time",
        beforeTime="test_before_time",
        includeResolvedCases=True,
        nextToken="test_next_token",
        maxResults=137,
        language="test_lanauage",
        includeCommunications=False,
    )

    actual_recent_comm = describe_cases_response["cases"][0]
    assert "recentCommunications" not in actual_recent_comm


@mock_support
def test_support_created_case_can_be_described_and_contains_resolved_cases_when_true():
    """Test support request creation when includeResolvedCases=true."""
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]

    for _ in range(4):
        describe_cases_response = client.describe_cases(
            caseIdList=[case_id_list],
            displayId="test_display_id",
            afterTime="test_after_time",
            beforeTime="test_before_time",
            includeResolvedCases=True,
            nextToken="test_next_token",
            maxResults=137,
            language="test_lanauage",
            includeCommunications=True,
        )

    actual = describe_cases_response["cases"][0]["caseId"]
    assert actual == case_id_list


@mock_support
def test_support_created_case_can_be_described_and_does_not_contain_resolved_cases_when_false():
    """Test support request when includeResolvedCases=false."""
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]

    for _ in range(4):
        describe_cases_response = client.describe_cases(
            caseIdList=[case_id_list],
            displayId="test_display_id",
            afterTime="test_after_time",
            beforeTime="test_before_time",
            includeResolvedCases=False,
            nextToken="test_next_token",
            maxResults=137,
            language="test_lanauage",
            includeCommunications=True,
        )

    actual = describe_cases_response["cases"]
    assert case_id_list not in actual


@mock_support
def test_support_created_case_can_be_described_and_can_cycle_case_severities():
    """Test support request creation cycles case severities."""
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc"],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    case_id_list = create_case_response["caseId"]

    for _ in range(3):
        describe_cases_response = client.describe_cases(
            caseIdList=[case_id_list],
            displayId="test_display_id",
            afterTime="test_after_time",
            beforeTime="test_before_time",
            includeResolvedCases=True,
            nextToken="test_next_token",
            maxResults=137,
            language="test_lanauage",
            includeCommunications=True,
        )

    actual = describe_cases_response["cases"][0]["severityCode"]
    assert actual == "urgent"
