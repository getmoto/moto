"""
MOTO_SES_SMTP_RELAY: every accepted SES send is additionally delivered over SMTP.

The SMTP client is monkeypatched with a recorder — these tests assert what moto hands to
smtplib (envelope sender, envelope recipients, MIME bytes), not that a mail server exists.
"""

import email
import smtplib
from typing import ClassVar

import boto3
import pytest

from moto import mock_aws


class _RecordingSMTP:
    """Stands in for smtplib.SMTP: records sendmail() calls, never touches a network."""

    sent: ClassVar[list] = []

    def __init__(self, host, port=25, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def sendmail(self, from_addr, to_addrs, msg):
        _RecordingSMTP.sent.append(
            {
                "host": self.host,
                "port": self.port,
                "from": from_addr,
                "to": list(to_addrs),
                "message": email.message_from_bytes(msg),
            }
        )


@pytest.fixture
def relay(monkeypatch):
    _RecordingSMTP.sent = []
    monkeypatch.setenv("MOTO_SES_SMTP_RELAY", "mail.local:1025")
    monkeypatch.setattr(smtplib, "SMTP", _RecordingSMTP)
    return _RecordingSMTP.sent


@mock_aws
def test_send_email_relays_both_body_parts(relay):
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="sender@example.com")

    conn.send_email(
        Source="Sender <sender@example.com>",
        Destination={
            "ToAddresses": ["to@example.com"],
            "CcAddresses": ["cc@example.com"],
            "BccAddresses": ["bcc@example.com"],
        },
        Message={
            "Subject": {"Data": "relay subject"},
            "Body": {
                "Text": {"Data": "plain part"},
                "Html": {"Data": "<b>html part</b>"},
            },
        },
    )

    assert len(relay) == 1
    sent = relay[0]
    assert (sent["host"], sent["port"]) == ("mail.local", 1025)
    assert sent["from"] == "sender@example.com"
    # Envelope recipients include Bcc; the visible headers do not.
    assert sorted(sent["to"]) == ["bcc@example.com", "cc@example.com", "to@example.com"]
    msg = sent["message"]
    assert msg["Subject"] == "relay subject"
    assert msg["From"] == "Sender <sender@example.com>"
    assert msg["To"] == "to@example.com"
    assert msg["Cc"] == "cc@example.com"
    assert msg["Bcc"] is None
    assert msg.get_content_type() == "multipart/alternative"
    parts = {
        p.get_content_type(): p.get_payload(decode=True).decode()
        for p in msg.walk()
        if not p.is_multipart()
    }
    assert parts == {"text/plain": "plain part", "text/html": "<b>html part</b>"}


@mock_aws
def test_send_email_text_only_relays_a_single_text_part(relay):
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="sender@example.com")
    conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={"Subject": {"Data": "s"}, "Body": {"Text": {"Data": "only text"}}},
    )
    parts = [
        p.get_content_type() for p in relay[0]["message"].walk() if not p.is_multipart()
    ]
    assert parts == ["text/plain"]


@mock_aws
def test_send_raw_email_relays_the_raw_message_verbatim(relay):
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="sender@example.com")
    raw = (
        "From: sender@example.com\r\nTo: to@example.com\r\n"
        "Subject: raw subject\r\nX-Custom: kept\r\n\r\nraw body\r\n"
    )
    conn.send_raw_email(RawMessage={"Data": raw})

    assert len(relay) == 1
    assert relay[0]["from"] == "sender@example.com"
    assert relay[0]["to"] == ["to@example.com"]
    assert relay[0]["message"]["X-Custom"] == "kept"
    assert relay[0]["message"].get_payload().strip() == "raw body"


@mock_aws
def test_send_templated_email_relays_the_rendered_template(relay):
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="sender@example.com")
    conn.create_template(
        Template={
            "TemplateName": "welcome",
            "SubjectPart": "Hello {{name}}",
            "TextPart": "Hi {{name}}",
            "HtmlPart": "<p>Hi {{name}}</p>",
        }
    )
    conn.send_templated_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Template="welcome",
        TemplateData='{"name": "Ada"}',
    )

    msg = relay[0]["message"]
    assert msg["Subject"] == "Hello Ada"
    assert msg["From"] == "sender@example.com"
    assert msg["To"] == "to@example.com"
    bodies = [
        p.get_payload(decode=True).decode() for p in msg.walk() if not p.is_multipart()
    ]
    assert "Hi Ada" in bodies[0] and "<p>Hi Ada</p>" in bodies[1]


@mock_aws
def test_sesv2_simple_send_relays_both_parts(relay):
    v1 = boto3.client("ses", region_name="us-east-1")
    v1.verify_email_identity(EmailAddress="sender@example.com")
    v2 = boto3.client("sesv2", region_name="us-east-1")
    v2.send_email(
        FromEmailAddress="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Content={
            "Simple": {
                "Subject": {"Data": "v2 subject"},
                "Body": {
                    "Text": {"Data": "v2 text"},
                    "Html": {"Data": "<i>v2 html</i>"},
                },
            }
        },
    )
    parts = {
        p.get_content_type(): p.get_payload(decode=True).decode()
        for p in relay[0]["message"].walk()
        if not p.is_multipart()
    }
    assert parts == {"text/plain": "v2 text", "text/html": "<i>v2 html</i>"}


@mock_aws
def test_relay_is_off_by_default(monkeypatch):
    monkeypatch.delenv("MOTO_SES_SMTP_RELAY", raising=False)
    _RecordingSMTP.sent = []
    monkeypatch.setattr(smtplib, "SMTP", _RecordingSMTP)
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="sender@example.com")
    conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={"Subject": {"Data": "s"}, "Body": {"Text": {"Data": "t"}}},
    )
    assert _RecordingSMTP.sent == []


@mock_aws
def test_relay_failure_does_not_fail_the_ses_call(monkeypatch, capsys):
    monkeypatch.setenv("MOTO_SES_SMTP_RELAY", "nowhere.invalid:1025")

    class _Broken:
        def __init__(self, *a, **k):
            raise ConnectionRefusedError("no server")

    monkeypatch.setattr(smtplib, "SMTP", _Broken)
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="sender@example.com")
    resp = conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={"Subject": {"Data": "s"}, "Body": {"Text": {"Data": "t"}}},
    )
    assert resp["MessageId"]
    assert "SES SMTP relay" in capsys.readouterr().err
