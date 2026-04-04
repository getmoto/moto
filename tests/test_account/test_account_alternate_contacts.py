import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
@pytest.mark.parametrize("contact_type", ["BILLING", "OPERATIONS", "SECURITY"])
def test_put_alternate_contact(contact_type):
    client = boto3.client("account", region_name="ap-southeast-1")
    client.put_alternate_contact(
        AlternateContactType=contact_type,
        EmailAddress="test@test.com",
        Name="Test Test",
        PhoneNumber="000000000000",
        Title="Dr. Test",
    )

    # Create contact in different account
    client.put_alternate_contact(
        AccountId="111111111111",
        AlternateContactType=contact_type,
        EmailAddress="test@diff.com",
        Name="Contact in 111111111111",
        PhoneNumber="000000000000",
        Title="Dr. Test",
    )

    details = client.get_alternate_contact(AlternateContactType=contact_type)[
        "AlternateContact"
    ]

    assert details["AlternateContactType"] == contact_type
    assert details["Title"] == "Dr. Test"
    assert details["Name"] == "Test Test"
    assert details["EmailAddress"] == "test@test.com"
    assert details["PhoneNumber"] == "000000000000"

    details = client.get_alternate_contact(
        AccountId="111111111111", AlternateContactType=contact_type
    )["AlternateContact"]

    assert details["Name"] == "Contact in 111111111111"
    assert details["EmailAddress"] == "test@diff.com"


@mock_aws
def test_get_unspecified_alternate_contact():
    sts = boto3.client("sts", "us-east-1")
    caller = sts.get_caller_identity()["Arn"]

    client = boto3.client("account", "us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_alternate_contact(AlternateContactType="UNKNOWN")
    err = exc.value.response["Error"]
    assert err["Code"] == "AccessDeniedException"
    assert (
        err["Message"]
        == f"User: {caller} is not authorized to perform: account:GetAlternateContact (You specified an invalid Alternate Contact type.)"
    )


@mock_aws
def test_get_unknown_alternate_contact():
    client = boto3.client("account", "us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_alternate_contact(AlternateContactType="SECURITY")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "No contact of the inputted alternate contact type found."


@mock_aws
def test_delete_alternate_contact():
    client = boto3.client("account", region_name="ap-southeast-1")
    client.put_alternate_contact(
        AlternateContactType="SECURITY",
        EmailAddress="test@test.com",
        Name="Test Test",
        PhoneNumber="000000000000",
        Title="Dr. Test",
    )

    # SUCCESS
    client.get_alternate_contact(AlternateContactType="SECURITY")

    client.delete_alternate_contact(AlternateContactType="SECURITY")

    # FAILURE
    with pytest.raises(ClientError) as exc:
        client.get_alternate_contact(AlternateContactType="SECURITY")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
