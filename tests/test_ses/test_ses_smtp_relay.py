"""
MOTO_SES_SMTP_RELAY: every accepted SES send is additionally delivered over SMTP, as the
message SES itself would construct (API_SendEmail, API_SendRawEmail,
API_SendTemplatedEmail, SESv2 API_SendEmail and the developer guide's header-fields page).

The SMTP client is monkeypatched with a recorder — these tests assert what moto hands to
smtplib (envelope sender, envelope recipients, MIME bytes), not that a mail server exists.
"""

import email
import re
import smtplib
from email.header import decode_header
from typing import ClassVar

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

REGION = "eu-west-2"
MESSAGE_ID_RE = re.compile(r"^<[A-Za-z0-9-]+@eu-west-2\.amazonses\.com>$")
RFC5322_GMT_RE = re.compile(
    r"^[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} GMT$"
)


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


def _parts(msg):
    return {
        p.get_content_type(): p.get_payload(decode=True).decode(
            p.get_content_charset() or "utf-8"
        )
        for p in msg.walk()
        if not p.is_multipart()
    }


def _ses(verified="sender@example.com"):
    conn = boto3.client("ses", region_name=REGION)
    conn.verify_email_identity(EmailAddress=verified)
    return conn


# ── SendEmail (v1) ─────────────────────────────────────────────────────────────


@mock_aws
def test_send_email_relays_both_body_parts_as_multipart_alternative(relay):
    conn = _ses()
    resp = conn.send_email(
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
    # Envelope recipients are To + Cc + Bcc; Bcc is not in the delivered headers.
    assert sorted(sent["to"]) == ["bcc@example.com", "cc@example.com", "to@example.com"]
    msg = sent["message"]
    assert msg["Subject"] == "relay subject"
    assert msg["From"] == "Sender <sender@example.com>"
    assert msg["To"] == "to@example.com"
    assert msg["Cc"] == "cc@example.com"
    assert msg["Bcc"] is None
    assert msg["Reply-To"] is None
    assert msg.get_content_type() == "multipart/alternative"
    assert _parts(msg) == {"text/plain": "plain part", "text/html": "<b>html part</b>"}
    # SES sets Message-ID to <MessageId@region.amazonses.com> and Date in UTC.
    assert msg["Message-ID"] == f"<{resp['MessageId']}@eu-west-2.amazonses.com>"
    assert RFC5322_GMT_RE.match(msg["Date"]), msg["Date"]


@mock_aws
def test_send_email_text_only_is_a_single_text_part(relay):
    conn = _ses()
    conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={"Subject": {"Data": "s"}, "Body": {"Text": {"Data": "only text"}}},
    )
    msg = relay[0]["message"]
    assert not msg.is_multipart()
    assert msg.get_content_type() == "text/plain"
    assert msg.get_payload(decode=True).decode() == "only text"


@mock_aws
def test_send_email_html_only_is_a_single_html_part(relay):
    conn = _ses()
    conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={
            "Subject": {"Data": "s"},
            "Body": {"Html": {"Data": "<p>only html</p>"}},
        },
    )
    msg = relay[0]["message"]
    assert not msg.is_multipart()
    assert msg.get_content_type() == "text/html"


@mock_aws
def test_send_email_reply_to_and_return_path(relay):
    conn = _ses()
    conn.verify_email_identity(EmailAddress="bounces@example.com")
    conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        ReplyToAddresses=["reply1@example.com", "Reply Two <reply2@example.com>"],
        ReturnPath="bounces@example.com",
        Message={"Subject": {"Data": "s"}, "Body": {"Text": {"Data": "t"}}},
    )
    sent = relay[0]
    # ReturnPath is where bounces go: it becomes the envelope sender. From is unchanged.
    assert sent["from"] == "bounces@example.com"
    assert sent["message"]["From"] == "sender@example.com"
    assert (
        sent["message"]["Reply-To"]
        == "reply1@example.com, Reply Two <reply2@example.com>"
    )


@mock_aws
def test_send_email_honours_charsets_and_encodes_non_ascii_subject(relay):
    conn = _ses()
    conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={
            "Subject": {"Data": "Як ти поживаєш?", "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": "café", "Charset": "ISO-8859-1"},
                "Html": {"Data": "<p>naïve</p>", "Charset": "UTF-8"},
            },
        },
    )
    msg = relay[0]["message"]
    # Header is 7-bit on the wire (encoded-word), decodes back to the original.
    assert msg["Subject"].startswith("=?utf-8?")
    decoded = "".join(
        s.decode(cs or "ascii") if isinstance(s, bytes) else s
        for s, cs in decode_header(msg["Subject"])
    )
    assert decoded == "Як ти поживаєш?"
    parts = {p.get_content_type(): p for p in msg.walk() if not p.is_multipart()}
    assert parts["text/plain"].get_content_charset() == "iso-8859-1"
    assert parts["text/plain"].get_payload(decode=True).decode("iso-8859-1") == "café"
    assert parts["text/html"].get_content_charset() == "utf-8"


@mock_aws
def test_send_email_unencodable_charset_falls_back_to_utf8(relay):
    conn = _ses()
    conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={
            "Subject": {"Data": "s"},
            "Body": {"Text": {"Data": "日本語", "Charset": "ISO-8859-1"}},
        },
    )
    msg = relay[0]["message"]
    assert msg.get_content_charset() == "utf-8"
    assert msg.get_payload(decode=True).decode("utf-8") == "日本語"


# ── SendRawEmail (v1) ──────────────────────────────────────────────────────────


@mock_aws
def test_send_raw_email_keeps_content_but_applies_ses_headers(relay):
    conn = _ses()
    raw = (
        "From: sender@example.com\r\nTo: to@example.com\r\nBcc: hidden@example.com\r\n"
        "Subject: raw subject\r\nX-Custom: kept\r\n"
        "Date: Mon, 01 Jan 2001 00:00:00 +0000\r\nMessage-ID: <mine@example.com>\r\n"
        "Return-Path: <mine-bounces@example.com>\r\n\r\nraw body\r\n"
    )
    resp = conn.send_raw_email(RawMessage={"Data": raw})

    assert len(relay) == 1
    sent = relay[0]
    assert sent["from"] == "sender@example.com"
    # Envelope recipients come from To/Cc/Bcc headers when Destinations is omitted; the
    # Bcc header itself is stripped from what recipients receive.
    assert sorted(sent["to"]) == ["hidden@example.com", "to@example.com"]
    msg = sent["message"]
    assert msg["Bcc"] is None
    assert msg["X-Custom"] == "kept"
    assert msg["Subject"] == "raw subject"
    assert msg.get_payload().strip() == "raw body"
    # SES overrides Date and Message-ID; recipients see SES's Return-Path, not the caller's.
    assert msg["Message-ID"] == f"<{resp['MessageId']}@eu-west-2.amazonses.com>"
    assert RFC5322_GMT_RE.match(msg["Date"]), msg["Date"]
    assert msg["Return-Path"] is None
    assert len(msg.get_all("Date")) == 1 and len(msg.get_all("Message-ID")) == 1


@mock_aws
def test_send_raw_email_destinations_and_headers_are_not_double_delivered(relay):
    conn = _ses()
    raw = "From: sender@example.com\r\nTo: to@example.com\r\nSubject: s\r\n\r\nbody\r\n"
    conn.send_raw_email(
        Source="sender@example.com",
        Destinations=["to@example.com", "extra@example.com"],
        RawMessage={"Data": raw},
    )
    assert sorted(relay[0]["to"]) == ["extra@example.com", "to@example.com"]


@mock_aws
def test_send_raw_email_multipart_with_attachment_survives_intact(relay):
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    conn = _ses()
    outer = MIMEMultipart("mixed")
    outer["From"] = "sender@example.com"
    outer["To"] = "to@example.com"
    outer["Subject"] = "with attachment"
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText("text", "plain", "utf-8"))
    alt.attach(MIMEText("<p>html</p>", "html", "utf-8"))
    outer.attach(alt)
    att = MIMEApplication(b"\x00\x01binary\xff", Name="blob.bin")
    att.add_header("Content-Disposition", "attachment", filename="blob.bin")
    outer.attach(att)

    conn.send_raw_email(RawMessage={"Data": outer.as_string()})
    msg = relay[0]["message"]
    assert msg.get_content_type() == "multipart/mixed"
    leaves = [p for p in msg.walk() if not p.is_multipart()]
    assert [p.get_content_type() for p in leaves] == [
        "text/plain",
        "text/html",
        "application/octet-stream",
    ]
    assert leaves[2].get_payload(decode=True) == b"\x00\x01binary\xff"
    assert leaves[2].get_filename() == "blob.bin"


# ── SendTemplatedEmail (v1) ────────────────────────────────────────────────────


@mock_aws
def test_send_templated_email_relays_the_rendered_template(relay):
    conn = _ses()
    conn.create_template(
        Template={
            "TemplateName": "welcome",
            "SubjectPart": "Hello {{name}}",
            "TextPart": "Hi {{name}}",
            "HtmlPart": "<p>Hi {{name}}</p>",
        }
    )
    resp = conn.send_templated_email(
        Source="Sender <sender@example.com>",
        Destination={
            "ToAddresses": ["to@example.com"],
            "CcAddresses": ["cc@example.com"],
            "BccAddresses": ["bcc@example.com"],
        },
        ReplyToAddresses=["reply@example.com"],
        Template="welcome",
        TemplateData='{"name": "Ada"}',
    )

    sent = relay[0]
    assert sorted(sent["to"]) == ["bcc@example.com", "cc@example.com", "to@example.com"]
    msg = sent["message"]
    assert msg["Subject"] == "Hello Ada"
    assert msg["From"] == "Sender <sender@example.com>"
    assert msg["To"] == "to@example.com"
    assert msg["Cc"] == "cc@example.com"
    assert msg["Bcc"] is None
    assert msg["Reply-To"] == "reply@example.com"
    assert msg["Message-ID"] == f"<{resp['MessageId']}@eu-west-2.amazonses.com>"
    assert RFC5322_GMT_RE.match(msg["Date"]), msg["Date"]
    assert msg.get_content_type() == "multipart/alternative"
    assert _parts(msg) == {"text/plain": "Hi Ada", "text/html": "<p>Hi Ada</p>"}


# ── SESv2 SendEmail ────────────────────────────────────────────────────────────


@mock_aws
def test_sesv2_simple_send_relays_both_parts_reply_to_and_feedback_address(relay):
    _ses()
    v2 = boto3.client("sesv2", region_name=REGION)
    resp = v2.send_email(
        FromEmailAddress="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        ReplyToAddresses=["reply@example.com"],
        FeedbackForwardingEmailAddress="bounces@example.com",
        Content={
            "Simple": {
                "Subject": {"Data": "v2 subject"},
                "Body": {
                    "Text": {"Data": "v2 text"},
                    "Html": {"Data": "<i>v2 html</i>"},
                },
                "Headers": [{"Name": "X-Campaign", "Value": "spring"}],
            }
        },
    )
    sent = relay[0]
    assert sent["from"] == "bounces@example.com"
    msg = sent["message"]
    assert msg["Reply-To"] == "reply@example.com"
    assert msg["X-Campaign"] == "spring"
    assert msg["Message-ID"] == f"<{resp['MessageId']}@eu-west-2.amazonses.com>"
    assert _parts(msg) == {"text/plain": "v2 text", "text/html": "<i>v2 html</i>"}


@mock_aws
@pytest.mark.parametrize(
    "name", ["To", "from", "Date", "Message-ID", "Subject", "MIME-Version"]
)
def test_sesv2_rejects_custom_headers_that_ses_sets_itself(relay, name):
    _ses()
    v2 = boto3.client("sesv2", region_name=REGION)
    with pytest.raises(ClientError) as exc:
        v2.send_email(
            FromEmailAddress="sender@example.com",
            Destination={"ToAddresses": ["to@example.com"]},
            Content={
                "Simple": {
                    "Subject": {"Data": "s"},
                    "Body": {"Text": {"Data": "t"}},
                    "Headers": [{"Name": name, "Value": "x"}],
                }
            },
        )
    assert exc.value.response["Error"]["Code"] == "BadRequestException"
    assert relay == []


@mock_aws
def test_sesv2_raw_send_relays(relay):
    _ses()
    v2 = boto3.client("sesv2", region_name=REGION)
    raw = b"From: sender@example.com\r\nTo: to@example.com\r\nSubject: v2 raw\r\n\r\nbody\r\n"
    v2.send_email(
        FromEmailAddress="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Content={"Raw": {"Data": raw}},
    )
    assert relay[0]["to"] == ["to@example.com"]
    assert relay[0]["message"]["Subject"] == "v2 raw"
    assert MESSAGE_ID_RE.match(relay[0]["message"]["Message-ID"])


# ── switches and failure ───────────────────────────────────────────────────────


@mock_aws
def test_relay_is_off_by_default(monkeypatch):
    monkeypatch.delenv("MOTO_SES_SMTP_RELAY", raising=False)
    _RecordingSMTP.sent = []
    monkeypatch.setattr(smtplib, "SMTP", _RecordingSMTP)
    conn = _ses()
    conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={"Subject": {"Data": "s"}, "Body": {"Text": {"Data": "t"}}},
    )
    assert _RecordingSMTP.sent == []


@mock_aws
def test_relay_host_without_port_defaults_to_25(monkeypatch):
    _RecordingSMTP.sent = []
    monkeypatch.setenv("MOTO_SES_SMTP_RELAY", "mail.local")
    monkeypatch.setattr(smtplib, "SMTP", _RecordingSMTP)
    conn = _ses()
    conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={"Subject": {"Data": "s"}, "Body": {"Text": {"Data": "t"}}},
    )
    assert (_RecordingSMTP.sent[0]["host"], _RecordingSMTP.sent[0]["port"]) == (
        "mail.local",
        25,
    )


@mock_aws
def test_relay_failure_does_not_fail_the_ses_call(monkeypatch, capsys):
    monkeypatch.setenv("MOTO_SES_SMTP_RELAY", "nowhere.invalid:1025")

    class _Broken:
        def __init__(self, *a, **k):
            raise ConnectionRefusedError("no server")

    monkeypatch.setattr(smtplib, "SMTP", _Broken)
    conn = _ses()
    resp = conn.send_email(
        Source="sender@example.com",
        Destination={"ToAddresses": ["to@example.com"]},
        Message={"Subject": {"Data": "s"}, "Body": {"Text": {"Data": "t"}}},
    )
    assert resp["MessageId"]
    assert "SES SMTP relay" in capsys.readouterr().err
