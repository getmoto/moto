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
    possible_statuses = ["none", "enqueued", "processing", "success", "abandoned"]

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
