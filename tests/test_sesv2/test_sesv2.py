import boto3
from botocore.exceptions import ClientError
import pytest
from moto import mock_sesv2, mock_ses
from ..test_ses.test_ses_boto3 import get_raw_email


@pytest.fixture(scope="function")
def ses_v1():
    """Use this for API calls which exist in v1 but not in v2"""
    with mock_ses():
        yield boto3.client("ses", region_name="us-east-1")


@mock_sesv2
def test_send_email(ses_v1):  # pylint: disable=redefined-outer-name
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    kwargs = dict(
        FromEmailAddress="test@example.com",
        Destination={
            "ToAddresses": ["test_to@example.com"],
            "CcAddresses": ["test_cc@example.com"],
            "BccAddresses": ["test_bcc@example.com"],
        },
        Content={
            "Simple": {
                "Subject": {"Data": "test subject"},
                "Body": {"Text": {"Data": "test body"}},
            },
        },
    )

    # Execute
    with pytest.raises(ClientError) as e:
        conn.send_email(**kwargs)
        assert e

    ses_v1.verify_domain_identity(Domain="example.com")
    conn.send_email(**kwargs)
    send_quota = ses_v1.get_send_quota()

    # Verify
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 3


@mock_sesv2
def test_send_raw_email(ses_v1):  # pylint: disable=redefined-outer-name
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    message = get_raw_email()
    destination = {
        "ToAddresses": [x.strip() for x in message["To"].split(",")],
    }
    kwargs = dict(
        FromEmailAddress=message["From"],
        Destination=destination,
        Content={"Raw": {"Data": message.as_bytes()}},
    )

    # Execute
    ses_v1.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(**kwargs)

    # Verify
    send_quota = ses_v1.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 2


@mock_sesv2
def test_list_contacts():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")

    # Execute

    result = conn.list_contacts(ContactListName="test")

    # Verify

    assert result["Contacts"] == []
