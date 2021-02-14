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
