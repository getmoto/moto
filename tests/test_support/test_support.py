import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from moto import mock_support


@mock_support
def test_describe_trusted_advisor_checks_returns_amount_of_checks():
    """
    test that the 104 checks that are listed under trusted advisor currently
    are returned
    """
    client = boto3.client("support", "us-east-1")
    response = client.describe_trusted_advisor_checks(language="en",)

    response["checks"].should.be.length_of(104)


@mock_support
def test_describe_trusted_advisor_checks_returns_an_expected_id():
    """
    test that a random check id is returned
    """
    client = boto3.client("support", "us-east-1")
    response = client.describe_trusted_advisor_checks(language="en",)
    check_ids = []
    for check in response["checks"]:
        check_ids.append(check["id"])

    check_ids.should.contain("zXCkfM1nI3")


@mock_support
def test_describe_trusted_advisor_checks_returns_an_expected_check_name():
    """
    test that a random check name is returned
    """
    client = boto3.client("support", "us-east-1")
    response = client.describe_trusted_advisor_checks(language="en",)
    check_names = []
    for check in response["checks"]:
        check_names.append(check["name"])

    check_names.should.contain("Unassociated Elastic IP Addresses")


@mock_support
def test_refresh_trusted_advisor_check_returns_expected_check():
    """
    A refresh of a trusted advisor check returns the check id
    in the response
    """
    client = boto3.client("support", "us-east-1")
    check_name = "XXXIIIY"
    response = client.refresh_trusted_advisor_check(checkId=check_name)
    response["status"]["checkId"].should.equal(check_name)


@mock_support
def test_refresh_trusted_advisor_check_returns_an_expected_status():
    """
    A refresh of a trusted advisor check returns an expected status
    """
    client = boto3.client("support", "us-east-1")
    possible_statuses = ["none", "enqueued", "processing", "success", "abandoned"]
    check_name = "XXXIIIY"
    response = client.refresh_trusted_advisor_check(checkId=check_name)
    actual_status = response["status"]["status"]
    possible_statuses.should.contain(actual_status)


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
    """
    Called only three times, only three expected statuses are returned
    """
    client = boto3.client("support", "us-east-1")
    check_name = "XXXIIIY"
    actual_statuses = []

    for _ in possible_statuses:
        response = client.refresh_trusted_advisor_check(checkId=check_name)
        actual_statuses.append(response["status"]["status"])

    actual_statuses.should.equal(possible_statuses)


@mock_support
def test_refresh_trusted_advisor_check_cycles_to_new_status_on_with_two_checks():
    """
    On each call, the next expected status is returned when additional checks are made
    """
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

    check_1_statuses.should.equal(possible_statuses) and check_2_statuses.should.equal(
        possible_statuses
    )


@mock_support
def test_refresh_trusted_advisor_check_cycle_continues_on_full_cycle():
    """
    After cycling through all statuses, the check continues the cycle
    """

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

    expected_none_response["status"]["status"].should.equal("none")


@mock_support
def test_support_case_is_closed():
    """
    On closing a case, the correct resolved response is returned
    """
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    set(expected_initial_case).issubset(possible_case_status).should.be.true

    expected_final_case.should.equal("resolved")


@mock_support
def test_support_case_created():
    """
    On creating a support request its response contains a case ID
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    len(create_case_response["caseId"]).should.equal(38)


@pytest.mark.parametrize(
    "key,value",
    [
        ("subject", "test_subject",),
        ("serviceCode", "test_service_code",),
        ("severityCode", "normal",),
        ("categoryCode", "test_category_code",),
        ("language", "test_language",),
    ],
)
@mock_support
def test_support_created_case_can_be_described(key, value):
    """
    On creating a support request it can be described
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual_case_id.should.equal(value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("subject", "test_subject",),
        ("serviceCode", "test_service_code",),
        ("severityCode", "normal",),
        ("categoryCode", "test_category_code",),
        ("language", "test_language",),
    ],
)
@mock_support
def test_support_created_case_can_be_described_without_next_token(key, value):
    """
    On creating a support request it can be described without next token
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual_case_id.should.equal(value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("subject", "test_subject",),
        ("serviceCode", "test_service_code",),
        ("severityCode", "normal",),
        ("categoryCode", "test_category_code",),
        ("language", "test_language",),
    ],
)
@mock_support
def test_support_created_case_can_be_described_without_max_results(key, value):
    """
    On creating a support request it can be described without max_results
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual_case_id.should.equal(value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("subject", "test_subject",),
        ("serviceCode", "test_service_code",),
        ("severityCode", "normal",),
        ("categoryCode", "test_category_code",),
        ("language", "test_language",),
    ],
)
@mock_support
def test_support_created_case_can_be_described_without_max_results_or_next_token(
    key, value
):
    """
    On creating a support request it can be described without max_results
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual_case_id.should.equal(value)


@mock_support
def test_support_created_case_can_be_described_without_params():
    """
    On creating a support request it can be described
    """

    client = boto3.client("support", "us-east-1")

    describe_cases_response = client.describe_cases()
    describe_cases_response["cases"].should.equal([])

    client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    describe_cases_response = client.describe_cases()
    describe_cases_response["cases"].should.have.length_of(1)


@mock_support
def test_support_created_case_cc_email_correct():
    """
    On creating a support request it can be described with
    the correct cc email
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual_case_id.should.equal("test_email_cc")


@mock_support
def test_support_case_include_resolved_defaults_to_false():
    """
    On creating a support request it can be described and it
    defaults to not include resolved cases
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual.should_not.contain(case_id_list)


@mock_support
def test_support_case_include_communications_defaults_to_true():
    """
    On creating a support request it can be described and it
    defaults to include communcations cases
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual.should.contain("recentCommunications")


@mock_support
def test_multiple_support_created_cases_can_be_described():
    """
    On creating multiple support requests they can be described
    """

    client = boto3.client("support", "us-east-1")
    create_case_response_1 = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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
        ccEmailAddresses=["test_email_cc",],
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

    actual_case_id_1.should.equal(case_id_list[0])
    actual_case_id_2.should.equal(case_id_list[1])


@mock_support
def test_support_created_case_can_be_described_and_contains_communications_when_set_to_true():
    """
    On creating a support request it can be described and contains comms
    when includeResolvedCases=True
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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
    actual_recent_comm.should.contain("recentCommunications")


@mock_support
def test_support_created_case_can_be_described_and_does_not_contain_communications_when_false():
    """
    On creating a support request it does not include
    comms when  includeCommunications=False
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual_recent_comm.should_not.contain("recentCommunications")


@mock_support
def test_support_created_case_can_be_described_and_contains_resolved_cases_when_true():
    """
    On creating a support request it does contain resolved cases when
    includeResolvedCases=true
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual.should.equal(case_id_list)


@mock_support
def test_support_created_case_can_be_described_and_does_not_contain_resolved_cases_when_false():
    """
    On creating a support request it does not contain resolved cases when
    includeResolvedCases=false
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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
    actual.should_not.contain(case_id_list)


@mock_support
def test_support_created_case_can_be_described_and_can_cycle_case_severities():
    """
    On creating a support request it can be described and cycles case severities
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="low",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
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

    actual.should.equal("urgent")
