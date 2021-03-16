from __future__ import unicode_literals

import boto3
import sure  # noqa
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
    actual_status = [response["status"]["status"]]
    set(actual_status).issubset(possible_statuses).should.be.true


@mock_support
def test_refresh_trusted_advisor_check_cycles_to_new_status_on_each_call():
    """
    On each call, the next expected status is returned
    """
    client = boto3.client("support", "us-east-1")
    check_name = "XXXIIIY"
    actual_statuses = []
    possible_statuses = ["none", "enqueued", "processing", "success", "abandoned"]

    for status in possible_statuses:
        response = client.refresh_trusted_advisor_check(checkId=check_name)
        actual_statuses.append(response["status"]["status"])

    actual_statuses.should.equal(possible_statuses)


@mock_support
def test_refresh_trusted_advisor_check_cycles_to_new_status_on_each_call():
    """
    Called only three times, only three expected statuses are returned
    """
    client = boto3.client("support", "us-east-1")
    check_name = "XXXIIIY"
    actual_statuses = []
    possible_statuses = ["none", "enqueued", "processing"]

    for status in possible_statuses:
        response = client.refresh_trusted_advisor_check(checkId=check_name)
        actual_statuses.append(response["status"]["status"])

    unexpected_statuses = set(["success", "abandoned"]).issubset(actual_statuses)

    actual_statuses.should.equal(
        possible_statuses
    ) and unexpected_statuses.should.be.false


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

    for check in possible_statuses:
        response = client.refresh_trusted_advisor_check(checkId=check_1_name)
        check_1_statuses.append(response["status"]["status"])

    for check in possible_statuses:
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

    for status in possible_statuses:
        client.refresh_trusted_advisor_check(checkId=check_name)

    expected_none_response = client.refresh_trusted_advisor_check(checkId=check_name)

    expected_none_response["status"]["status"].should.equal("none")


@mock_support
def test_support_case_is_closed():
    """
    On closing a case, the correct response is returned
    """
    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="test_severity_code",
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

    set(expected_initial_case).issubset(
        possible_case_status
    ).should.be.true and expected_final_case.should.equal("resolved")


@mock_support
def test_support_case_created():
    """
    On creating a support request its response contains a case ID
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="test_severity_code",
        categoryCode="test_category_code",
        communicationBody="test_communication_body",
        ccEmailAddresses=["test_email_cc",],
        language="test_language",
        issueType="test_issue_type",
        attachmentSetId="test_attachment_set_id",
    )

    len(create_case_response["caseId"]).should.equal(38)


@mock_support
def test_support_created_case_can_be_described():
    """
    On creating a support request it can be described
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="test_severity_code",
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

    actual_case_id = describe_cases_response["cases"][0]["caseId"]

    actual_case_id.should.equal(case_id_list)


@mock_support
def test_multiple_support_created_cases_can_be_described():
    """
    On creating multiple support requests they can be described
    """

    client = boto3.client("support", "us-east-1")
    create_case_response_1 = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="test_severity_code",
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
        severityCode="test_severity_code",
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
def test_support_created_case_can_be_described_and_contains_communications():
    """
    On creating a support request it can be described and contains comms
    when set to true
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="test_severity_code",
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
def test_support_created_case_can_be_described_and_does_not_ontain_communications_when_false():
    """
    On creating a support request it does not include 
    comms when set to false
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="test_severity_code",
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
    On creating a support request it contains resolved cases when set to true
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="test_severity_code",
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
def test_support_created_case_can_be_described_and_contains_resolved_cases_when_false():
    """
    On creating a support request it contains resolved cases when set to false
    """

    client = boto3.client("support", "us-east-1")
    create_case_response = client.create_case(
        subject="test_subject",
        serviceCode="test_service_code",
        severityCode="test_severity_code",
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
        severityCode="test_severity_code",
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

    actual = describe_cases_response["cases"][0]["severityCode"]

    actual.should.equal("urgent")
