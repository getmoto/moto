import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.ses.models import Message, RawMessage, ses_backends
from tests import DEFAULT_ACCOUNT_ID

from ..test_ses.test_ses_boto3 import get_raw_email


@pytest.fixture(scope="function")
def ses_v1():
    """Use this for API calls which exist in v1 but not in v2"""
    with mock_aws():
        yield boto3.client("ses", region_name="us-east-1")


@mock_aws
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
    assert e.value.response["Error"]["Code"] == "MessageRejected"

    ses_v1.verify_domain_identity(Domain="example.com")
    conn.send_email(**kwargs)
    send_quota = ses_v1.get_send_quota()

    # Verify
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 3

    if not settings.TEST_SERVER_MODE:
        backend = ses_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        msg: Message = backend.sent_messages[0]
        assert msg.subject == "test subject"
        assert msg.body == "test body"


@mock_aws
def test_send_html_email(ses_v1):  # pylint: disable=redefined-outer-name
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    ses_v1.verify_domain_identity(Domain="example.com")
    kwargs = dict(
        FromEmailAddress="test@example.com",
        Destination={
            "ToAddresses": ["test_to@example.com"],
        },
        Content={
            "Simple": {
                "Subject": {"Data": "test subject"},
                "Body": {"Html": {"Data": "<h1>Test HTML</h1>"}},
            },
        },
    )

    # Execute
    conn.send_email(**kwargs)

    # Verify
    send_quota = ses_v1.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 1

    if not settings.TEST_SERVER_MODE:
        backend = ses_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        msg: Message = backend.sent_messages[0]
        assert msg.subject == "test subject"
        assert msg.body == "<h1>Test HTML</h1>"


@mock_aws
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
    # 2 destinations in the message, two in the 'Destination'-argument
    assert int(send_quota["SentLast24Hours"]) == 4


@mock_aws
def test_send_raw_email__with_specific_message(
    ses_v1,
):  # pylint: disable=redefined-outer-name
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    message = get_raw_email()
    # This particular message means that our base64-encoded body contains a '='
    # Testing this to ensure that we parse the body as JSON, not as a query-dict
    message["Subject"] = "Test-2"
    kwargs = dict(
        Content={"Raw": {"Data": message.as_bytes()}},
    )

    # Execute
    ses_v1.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(**kwargs)

    # Verify
    send_quota = ses_v1.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 2

    if not settings.TEST_SERVER_MODE:
        backend = ses_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        msg: RawMessage = backend.sent_messages[0]
        assert message.as_bytes() == msg.raw_data.encode("utf-8")
        assert msg.source == "test@example.com"
        assert msg.destinations == ["to@example.com", "foo@example.com"]


@mock_aws
def test_send_raw_email__with_to_address_display_name(
    ses_v1,
):  # pylint: disable=redefined-outer-name
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    message = get_raw_email()
    # This particular message means that to-address with display-name which contains many ','
    del message["To"]
    display_name = ",".join(["c" for _ in range(50)])
    message["To"] = f""""{display_name}" <to@example.com>, foo@example.com"""
    kwargs = dict(
        Content={"Raw": {"Data": message.as_bytes()}},
    )

    # Execute
    ses_v1.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(**kwargs)

    # Verify
    send_quota = ses_v1.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 2

    if not settings.TEST_SERVER_MODE:
        backend = ses_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        msg: RawMessage = backend.sent_messages[0]
        assert message.as_bytes() == msg.raw_data.encode("utf-8")
        assert msg.source == "test@example.com"
        assert msg.destinations == [
            """"c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c" <to@example.com>""",
            "foo@example.com",
        ]


@mock_aws
def test_create_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"

    # Execute
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    result = conn.list_contact_lists()

    # Verify
    assert len(result["ContactLists"]) == 1
    assert result["ContactLists"][0]["ContactListName"] == contact_list_name


@mock_aws
def test_create_contact_list__with_topics():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test3"

    # Execute
    conn.create_contact_list(
        ContactListName=contact_list_name,
        Topics=[
            {
                "TopicName": "test-topic",
                "DisplayName": "display=name",
                "DefaultSubscriptionStatus": "OPT_OUT",
            }
        ],
    )
    result = conn.list_contact_lists()

    # Verify
    assert len(result["ContactLists"]) == 1
    assert result["ContactLists"][0]["ContactListName"] == contact_list_name


@mock_aws
def test_list_contact_lists():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")

    # Execute
    result = conn.list_contact_lists()

    # Verify
    assert result["ContactLists"] == []


@mock_aws
def test_get_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.get_contact_list(ContactListName=contact_list_name)
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert (
        e.value.response["Error"]["Message"]
        == f"List with name: {contact_list_name} doesn't exist."
    )

    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    result = conn.get_contact_list(ContactListName=contact_list_name)

    # Verify
    assert result["ContactListName"] == contact_list_name


@mock_aws
def test_delete_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.delete_contact_list(ContactListName=contact_list_name)
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    result = conn.list_contact_lists()
    assert len(result["ContactLists"]) == 1
    conn.delete_contact_list(
        ContactListName=contact_list_name,
    )
    result = conn.list_contact_lists()

    # Verify
    assert len(result["ContactLists"]) == 0


@mock_aws
def test_list_contacts():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )

    # Execute
    result = conn.list_contacts(ContactListName=contact_list_name)

    # Verify
    assert result["Contacts"] == []


@mock_aws
def test_create_contact_no_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.create_contact(
            ContactListName=contact_list_name,
            EmailAddress=email,
        )

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert (
        e.value.response["Error"]["Message"]
        == f"List with name: {contact_list_name} doesn't exist."
    )


@mock_aws
def test_create_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )

    # Execute
    conn.create_contact(
        ContactListName=contact_list_name,
        EmailAddress=email,
    )

    result = conn.list_contacts(ContactListName=contact_list_name)

    # Verify
    assert len(result["Contacts"]) == 1
    assert result["Contacts"][0]["EmailAddress"] == email


@mock_aws
def test_get_contact_no_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.get_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert (
        e.value.response["Error"]["Message"]
        == f"List with name: {contact_list_name} doesn't exist."
    )


@mock_aws
def test_get_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    # Execute

    conn.create_contact(
        ContactListName=contact_list_name,
        EmailAddress=email,
    )
    result = conn.get_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert result["ContactListName"] == contact_list_name
    assert result["EmailAddress"] == email


@mock_aws
def test_get_contact_no_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    # Execute
    with pytest.raises(ClientError) as e:
        conn.get_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert e.value.response["Error"]["Message"] == f"{email} doesn't exist in List."


@mock_aws
def test_delete_contact_no_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.delete_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert (
        e.value.response["Error"]["Message"]
        == f"List with name: {contact_list_name} doesn't exist."
    )


@mock_aws
def test_delete_contact_no_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    conn.create_contact_list(ContactListName=contact_list_name)

    with pytest.raises(ClientError) as e:
        conn.delete_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert e.value.response["Error"]["Message"] == f"{email} doesn't exist in List."


@mock_aws
def test_delete_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    conn.create_contact_list(ContactListName=contact_list_name)
    conn.create_contact(ContactListName=contact_list_name, EmailAddress=email)
    result = conn.list_contacts(ContactListName=contact_list_name)
    assert len(result["Contacts"]) == 1

    conn.delete_contact(ContactListName=contact_list_name, EmailAddress=email)
    result = conn.list_contacts(ContactListName=contact_list_name)

    # Verify
    assert len(result["Contacts"]) == 0
