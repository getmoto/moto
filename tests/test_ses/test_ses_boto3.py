from __future__ import unicode_literals
import json

import boto3
from botocore.exceptions import ClientError
from six.moves.email_mime_multipart import MIMEMultipart
from six.moves.email_mime_text import MIMEText
import pytest


import sure  # noqa

from moto import mock_ses


@mock_ses
def test_verify_email_identity():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="test@example.com")

    identities = conn.list_identities()
    address = identities["Identities"][0]
    address.should.equal("test@example.com")


@mock_ses
def test_verify_email_address():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_address(EmailAddress="test@example.com")
    email_addresses = conn.list_verified_email_addresses()
    email = email_addresses["VerifiedEmailAddresses"][0]
    email.should.equal("test@example.com")


@mock_ses
def test_domain_verify():
    conn = boto3.client("ses", region_name="us-east-1")

    conn.verify_domain_dkim(Domain="domain1.com")
    conn.verify_domain_identity(Domain="domain2.com")

    identities = conn.list_identities()
    domains = list(identities["Identities"])
    domains.should.equal(["domain1.com", "domain2.com"])


@mock_ses
def test_delete_identity():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="test@example.com")

    conn.list_identities()["Identities"].should.have.length_of(1)
    conn.delete_identity(Identity="test@example.com")
    conn.list_identities()["Identities"].should.have.length_of(0)


@mock_ses
def test_send_email():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = dict(
        Source="test@example.com",
        Destination={
            "ToAddresses": ["test_to@example.com"],
            "CcAddresses": ["test_cc@example.com"],
            "BccAddresses": ["test_bcc@example.com"],
        },
        Message={
            "Subject": {"Data": "test subject"},
            "Body": {"Text": {"Data": "test body"}},
        },
    )
    conn.send_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_domain_identity(Domain="example.com")
    conn.send_email(**kwargs)

    too_many_addresses = list("to%s@example.com" % i for i in range(51))
    conn.send_email.when.called_with(
        **dict(kwargs, Destination={"ToAddresses": too_many_addresses})
    ).should.throw(ClientError)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    sent_count.should.equal(3)


@mock_ses
def test_send_email_when_verify_source():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = dict(
        Destination={"ToAddresses": ["test_to@example.com"],},
        Message={
            "Subject": {"Data": "test subject"},
            "Body": {"Text": {"Data": "test body"}},
        },
    )

    conn.send_email.when.called_with(
        Source="verify_email_address@example.com", **kwargs
    ).should.throw(ClientError)
    conn.verify_email_address(EmailAddress="verify_email_address@example.com")
    conn.send_email(Source="verify_email_address@example.com", **kwargs)

    conn.send_email.when.called_with(
        Source="verify_email_identity@example.com", **kwargs
    ).should.throw(ClientError)
    conn.verify_email_identity(EmailAddress="verify_email_identity@example.com")
    conn.send_email(Source="verify_email_identity@example.com", **kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    sent_count.should.equal(2)


@mock_ses
def test_send_templated_email():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = dict(
        Source="test@example.com",
        Destination={
            "ToAddresses": ["test_to@example.com"],
            "CcAddresses": ["test_cc@example.com"],
            "BccAddresses": ["test_bcc@example.com"],
        },
        Template="test_template",
        TemplateData='{"name": "test"}',
    )

    conn.send_templated_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_domain_identity(Domain="example.com")

    with pytest.raises(ClientError) as ex:
        conn.send_templated_email(**kwargs)

    ex.value.response["Error"]["Code"].should.equal("TemplateDoesNotExist")

    conn.create_template(
        Template={
            "TemplateName": "test_template",
            "SubjectPart": "lalala",
            "HtmlPart": "",
            "TextPart": "",
        }
    )

    conn.send_templated_email(**kwargs)

    too_many_addresses = list("to%s@example.com" % i for i in range(51))
    conn.send_templated_email.when.called_with(
        **dict(kwargs, Destination={"ToAddresses": too_many_addresses})
    ).should.throw(ClientError)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    sent_count.should.equal(3)


@mock_ses
def test_send_html_email():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = dict(
        Source="test@example.com",
        Destination={"ToAddresses": ["test_to@example.com"]},
        Message={
            "Subject": {"Data": "test subject"},
            "Body": {"Html": {"Data": "test body"}},
        },
    )

    conn.send_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    sent_count.should.equal(1)


@mock_ses
def test_send_raw_email():
    conn = boto3.client("ses", region_name="us-east-1")

    message = get_raw_email()

    kwargs = dict(Source=message["From"], RawMessage={"Data": message.as_string()})

    conn.send_raw_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_raw_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    sent_count.should.equal(2)


@mock_ses
def test_send_raw_email_validate_domain():
    conn = boto3.client("ses", region_name="us-east-1")

    message = get_raw_email()

    kwargs = dict(Source=message["From"], RawMessage={"Data": message.as_string()})

    conn.send_raw_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_domain_identity(Domain="example.com")
    conn.send_raw_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    sent_count.should.equal(2)


def get_raw_email():
    message = MIMEMultipart()
    message["Subject"] = "Test"
    message["From"] = "test@example.com"
    message["To"] = "to@example.com, foo@example.com"
    # Message body
    part = MIMEText("test file attached")
    message.attach(part)
    # Attachment
    part = MIMEText("contents of test file here")
    part.add_header("Content-Disposition", "attachment; filename=test.txt")
    message.attach(part)
    return message


@mock_ses
def test_send_raw_email_without_source():
    conn = boto3.client("ses", region_name="us-east-1")

    message = MIMEMultipart()
    message["Subject"] = "Test"
    message["From"] = "test@example.com"
    message["To"] = "to@example.com, foo@example.com"

    # Message body
    part = MIMEText("test file attached")
    message.attach(part)

    # Attachment
    part = MIMEText("contents of test file here")
    part.add_header("Content-Disposition", "attachment; filename=test.txt")
    message.attach(part)

    kwargs = dict(RawMessage={"Data": message.as_string()})

    conn.send_raw_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_raw_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    sent_count.should.equal(2)


@mock_ses
def test_send_raw_email_without_source_or_from():
    conn = boto3.client("ses", region_name="us-east-1")

    message = MIMEMultipart()
    message["Subject"] = "Test"
    message["To"] = "to@example.com, foo@example.com"

    # Message body
    part = MIMEText("test file attached")
    message.attach(part)
    # Attachment
    part = MIMEText("contents of test file here")
    part.add_header("Content-Disposition", "attachment; filename=test.txt")
    message.attach(part)

    kwargs = dict(RawMessage={"Data": message.as_string()})

    conn.send_raw_email.when.called_with(**kwargs).should.throw(ClientError)


@mock_ses
def test_send_email_notification_with_encoded_sender():
    sender = "Foo <foo@bar.baz>"
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress=sender)
    response = conn.send_email(
        Source=sender,
        Destination={"ToAddresses": ["your.friend@hotmail.com"]},
        Message={"Subject": {"Data": "hi",}, "Body": {"Text": {"Data": "there",}},},
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_ses
def test_create_configuration_set():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.create_configuration_set(ConfigurationSet=dict({"Name": "test"}))

    conn.create_configuration_set_event_destination(
        ConfigurationSetName="test",
        EventDestination={
            "Name": "snsEvent",
            "Enabled": True,
            "MatchingEventTypes": ["send",],
            "SNSDestination": {
                "TopicARN": "arn:aws:sns:us-east-1:123456789012:myTopic"
            },
        },
    )

    with pytest.raises(ClientError) as ex:
        conn.create_configuration_set_event_destination(
            ConfigurationSetName="failtest",
            EventDestination={
                "Name": "snsEvent",
                "Enabled": True,
                "MatchingEventTypes": ["send",],
                "SNSDestination": {
                    "TopicARN": "arn:aws:sns:us-east-1:123456789012:myTopic"
                },
            },
        )

    ex.value.response["Error"]["Code"].should.equal("ConfigurationSetDoesNotExist")

    with pytest.raises(ClientError) as ex:
        conn.create_configuration_set_event_destination(
            ConfigurationSetName="test",
            EventDestination={
                "Name": "snsEvent",
                "Enabled": True,
                "MatchingEventTypes": ["send",],
                "SNSDestination": {
                    "TopicARN": "arn:aws:sns:us-east-1:123456789012:myTopic"
                },
            },
        )

    ex.value.response["Error"]["Code"].should.equal("EventDestinationAlreadyExists")


@mock_ses
def test_create_receipt_rule_set():
    conn = boto3.client("ses", region_name="us-east-1")
    result = conn.create_receipt_rule_set(RuleSetName="testRuleSet")

    result["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    with pytest.raises(ClientError) as ex:
        conn.create_receipt_rule_set(RuleSetName="testRuleSet")

    ex.value.response["Error"]["Code"].should.equal("RuleSetNameAlreadyExists")


@mock_ses
def test_create_receipt_rule():
    conn = boto3.client("ses", region_name="us-east-1")
    rule_set_name = "testRuleSet"
    conn.create_receipt_rule_set(RuleSetName=rule_set_name)

    result = conn.create_receipt_rule(
        RuleSetName=rule_set_name,
        Rule={
            "Name": "testRule",
            "Enabled": False,
            "TlsPolicy": "Optional",
            "Recipients": ["string"],
            "Actions": [
                {
                    "S3Action": {
                        "TopicArn": "string",
                        "BucketName": "string",
                        "ObjectKeyPrefix": "string",
                        "KmsKeyArn": "string",
                    },
                    "BounceAction": {
                        "TopicArn": "string",
                        "SmtpReplyCode": "string",
                        "StatusCode": "string",
                        "Message": "string",
                        "Sender": "string",
                    },
                }
            ],
            "ScanEnabled": False,
        },
    )

    result["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    with pytest.raises(ClientError) as ex:
        conn.create_receipt_rule(
            RuleSetName=rule_set_name,
            Rule={
                "Name": "testRule",
                "Enabled": False,
                "TlsPolicy": "Optional",
                "Recipients": ["string"],
                "Actions": [
                    {
                        "S3Action": {
                            "TopicArn": "string",
                            "BucketName": "string",
                            "ObjectKeyPrefix": "string",
                            "KmsKeyArn": "string",
                        },
                        "BounceAction": {
                            "TopicArn": "string",
                            "SmtpReplyCode": "string",
                            "StatusCode": "string",
                            "Message": "string",
                            "Sender": "string",
                        },
                    }
                ],
                "ScanEnabled": False,
            },
        )

    ex.value.response["Error"]["Code"].should.equal("RuleAlreadyExists")

    with pytest.raises(ClientError) as ex:
        conn.create_receipt_rule(
            RuleSetName="InvalidRuleSetaName",
            Rule={
                "Name": "testRule",
                "Enabled": False,
                "TlsPolicy": "Optional",
                "Recipients": ["string"],
                "Actions": [
                    {
                        "S3Action": {
                            "TopicArn": "string",
                            "BucketName": "string",
                            "ObjectKeyPrefix": "string",
                            "KmsKeyArn": "string",
                        },
                        "BounceAction": {
                            "TopicArn": "string",
                            "SmtpReplyCode": "string",
                            "StatusCode": "string",
                            "Message": "string",
                            "Sender": "string",
                        },
                    }
                ],
                "ScanEnabled": False,
            },
        )

    ex.value.response["Error"]["Code"].should.equal("RuleSetDoesNotExist")


@mock_ses
def test_create_ses_template():
    conn = boto3.client("ses", region_name="us-east-1")

    conn.create_template(
        Template={
            "TemplateName": "MyTemplate",
            "SubjectPart": "Greetings, {{name}}!",
            "TextPart": "Dear {{name}},"
            "\r\nYour favorite animal is {{favoriteanimal}}.",
            "HtmlPart": "<h1>Hello {{name}},"
            "</h1><p>Your favorite animal is {{favoriteanimal}}.</p>",
        }
    )
    with pytest.raises(ClientError) as ex:
        conn.create_template(
            Template={
                "TemplateName": "MyTemplate",
                "SubjectPart": "Greetings, {{name}}!",
                "TextPart": "Dear {{name}},"
                "\r\nYour favorite animal is {{favoriteanimal}}.",
                "HtmlPart": "<h1>Hello {{name}},"
                "</h1><p>Your favorite animal is {{favoriteanimal}}.</p>",
            }
        )

    ex.value.response["Error"]["Code"].should.equal("TemplateNameAlreadyExists")

    # get a template which is already added
    result = conn.get_template(TemplateName="MyTemplate")
    result["Template"]["TemplateName"].should.equal("MyTemplate")
    result["Template"]["SubjectPart"].should.equal("Greetings, {{name}}!")
    result["Template"]["HtmlPart"].should.equal(
        "<h1>Hello {{name}}," "</h1><p>Your favorite animal is {{favoriteanimal}}.</p>"
    )
    # get a template which is not present
    with pytest.raises(ClientError) as ex:
        conn.get_template(TemplateName="MyFakeTemplate")

    ex.value.response["Error"]["Code"].should.equal("TemplateDoesNotExist")

    result = conn.list_templates()
    result["TemplatesMetadata"][0]["Name"].should.equal("MyTemplate")


@mock_ses
def test_render_template():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = dict(
        TemplateName="MyTestTemplate",
        TemplateData=json.dumps({"name": "John", "favoriteanimal": "Lion"}),
    )

    with pytest.raises(ClientError) as ex:
        conn.test_render_template(**kwargs)
    ex.value.response["Error"]["Code"].should.equal("TemplateDoesNotExist")

    conn.create_template(
        Template={
            "TemplateName": "MyTestTemplate",
            "SubjectPart": "Greetings, {{name}}!",
            "TextPart": "Dear {{name}},"
            "\r\nYour favorite animal is {{favoriteanimal}}.",
            "HtmlPart": "<h1>Hello {{name}},"
            "</h1><p>Your favorite animal is {{favoriteanimal}}.</p>",
        }
    )
    result = conn.test_render_template(**kwargs)
    result["RenderedTemplate"].should.contain("Subject: Greetings, John!")
    result["RenderedTemplate"].should.contain("Dear John,")
    result["RenderedTemplate"].should.contain("<h1>Hello John,</h1>")
    result["RenderedTemplate"].should.contain("Your favorite animal is Lion")


@mock_ses
def test_update_ses_template():
    conn = boto3.client("ses", region_name="us-east-1")
    template = {
        "TemplateName": "MyTemplateToUpdate",
        "SubjectPart": "Greetings, {{name}}!",
        "TextPart": "Dear {{name}}," "\r\nYour favorite animal is {{favoriteanimal}}.",
        "HtmlPart": "<h1>Hello {{name}},"
        "</h1><p>Your favorite animal is {{favoriteanimal}}.</p>",
    }

    with pytest.raises(ClientError) as ex:
        conn.update_template(Template=template)
    ex.value.response["Error"]["Code"].should.equal("TemplateDoesNotExist")

    conn.create_template(Template=template)

    template["SubjectPart"] = "Hi, {{name}}!"
    template["TextPart"] = "Dear {{name}},\r\n Your favorite color is {{color}}"
    template[
        "HtmlPart"
    ] = "<h1>Hello {{name}},</h1><p>Your favorite color is {{color}}</p>"
    conn.update_template(Template=template)

    result = conn.get_template(TemplateName=template["TemplateName"])
    result["Template"]["SubjectPart"].should.equal("Hi, {{name}}!")
    result["Template"]["TextPart"].should.equal(
        "Dear {{name}},\n Your favorite color is {{color}}"
    )
    result["Template"]["HtmlPart"].should.equal(
        "<h1>Hello {{name}},</h1><p>Your favorite color is {{color}}</p>"
    )
