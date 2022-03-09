import json

import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import ParamValidationError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pytest

import sure  # noqa # pylint: disable=unused-import

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
        Destination={"ToAddresses": ["test_to@example.com"]},
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
def test_send_unverified_email_with_chevrons():
    conn = boto3.client("ses", region_name="us-east-1")

    # Sending an email to an unverified source should fail
    with pytest.raises(ClientError) as ex:
        conn.send_email(
            Source=f"John Smith <foobar@example.com>",  # << Unverified source address
            Destination={
                "ToAddresses": ["blah@example.com"],
                "CcAddresses": [],
                "BccAddresses": [],
            },
            Message={
                "Subject": {"Data": "Hello!"},
                "Body": {"Html": {"Data": "<html>Hi</html>"}},
            },
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("MessageRejected")
    # The source should be returned exactly as provided - without XML encoding issues
    err["Message"].should.equal(
        "Email address not verified John Smith <foobar@example.com>"
    )


@mock_ses
def test_send_email_invalid_address():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_domain_identity(Domain="example.com")

    with pytest.raises(ClientError) as ex:
        conn.send_email(
            Source="test@example.com",
            Destination={
                "ToAddresses": ["test_to@example.com", "invalid_address"],
                "CcAddresses": [],
                "BccAddresses": [],
            },
            Message={
                "Subject": {"Data": "test subject"},
                "Body": {"Text": {"Data": "test body"}},
            },
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Missing domain")


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
def test_send_templated_email_invalid_address():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_domain_identity(Domain="example.com")
    conn.create_template(
        Template={
            "TemplateName": "test_template",
            "SubjectPart": "lalala",
            "HtmlPart": "",
            "TextPart": "",
        }
    )

    with pytest.raises(ClientError) as ex:
        conn.send_templated_email(
            Source="test@example.com",
            Destination={
                "ToAddresses": ["test_to@example.com", "invalid_address"],
                "CcAddresses": [],
                "BccAddresses": [],
            },
            Template="test_template",
            TemplateData='{"name": "test"}',
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Missing domain")


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


@mock_ses
def test_send_raw_email_invalid_address():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_domain_identity(Domain="example.com")

    message = get_raw_email()
    del message["To"]

    with pytest.raises(ClientError) as ex:
        conn.send_raw_email(
            Source=message["From"],
            Destinations=["test_to@example.com", "invalid_address"],
            RawMessage={"Data": message.as_string()},
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Missing domain")


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
        Message={"Subject": {"Data": "hi"}, "Body": {"Text": {"Data": "there"}}},
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
            "MatchingEventTypes": ["send"],
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
                "MatchingEventTypes": ["send"],
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
                "MatchingEventTypes": ["send"],
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
def test_describe_receipt_rule_set():
    conn = boto3.client("ses", region_name="us-east-1")
    create_receipt_rule_set_response = conn.create_receipt_rule_set(
        RuleSetName="testRuleSet"
    )

    create_receipt_rule_set_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(
        200
    )

    result = conn.describe_receipt_rule_set(RuleSetName="testRuleSet")

    result["Metadata"]["Name"].should.equal("testRuleSet")
    # result['Metadata']['CreatedTimestamp'].should.equal()

    len(result["Rules"]).should.equal(0)


@mock_ses
def test_describe_receipt_rule_set_with_rules():
    conn = boto3.client("ses", region_name="us-east-1")
    create_receipt_rule_set_response = conn.create_receipt_rule_set(
        RuleSetName="testRuleSet"
    )

    create_receipt_rule_set_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(
        200
    )

    receipt_rule = {
        "Name": "testRule",
        "Enabled": True,
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
    }

    create_receipt_rule_response = conn.create_receipt_rule(
        RuleSetName="testRuleSet", Rule=receipt_rule
    )

    create_receipt_rule_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    result = conn.describe_receipt_rule_set(RuleSetName="testRuleSet")

    result["Metadata"]["Name"].should.equal("testRuleSet")
    # result['Metadata']['CreatedTimestamp'].should.equal()

    len(result["Rules"]).should.equal(1)
    result["Rules"][0].should.equal(receipt_rule)


@mock_ses
def test_describe_receipt_rule():
    conn = boto3.client("ses", region_name="us-east-1")
    rule_set_name = "testRuleSet"
    conn.create_receipt_rule_set(RuleSetName=rule_set_name)

    rule_name = "testRule"
    conn.create_receipt_rule(
        RuleSetName=rule_set_name,
        Rule={
            "Name": rule_name,
            "Enabled": False,
            "TlsPolicy": "Optional",
            "Recipients": ["test@email.com", "test2@email.com"],
            "Actions": [
                {
                    "S3Action": {
                        "TopicArn": "string",
                        "BucketName": "testBucketName",
                        "ObjectKeyPrefix": "testObjectKeyPrefix",
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

    receipt_rule_response = conn.describe_receipt_rule(
        RuleSetName=rule_set_name, RuleName=rule_name
    )

    receipt_rule_response["Rule"]["Name"].should.equal(rule_name)

    receipt_rule_response["Rule"]["Enabled"].should.equal(False)

    receipt_rule_response["Rule"]["TlsPolicy"].should.equal("Optional")

    len(receipt_rule_response["Rule"]["Recipients"]).should.equal(2)
    receipt_rule_response["Rule"]["Recipients"][0].should.equal("test@email.com")

    len(receipt_rule_response["Rule"]["Actions"]).should.equal(1)
    receipt_rule_response["Rule"]["Actions"][0].should.have.key("S3Action")

    receipt_rule_response["Rule"]["Actions"][0]["S3Action"].should.have.key(
        "TopicArn"
    ).being.equal("string")
    receipt_rule_response["Rule"]["Actions"][0]["S3Action"].should.have.key(
        "BucketName"
    ).being.equal("testBucketName")
    receipt_rule_response["Rule"]["Actions"][0]["S3Action"].should.have.key(
        "ObjectKeyPrefix"
    ).being.equal("testObjectKeyPrefix")
    receipt_rule_response["Rule"]["Actions"][0]["S3Action"].should.have.key(
        "KmsKeyArn"
    ).being.equal("string")

    receipt_rule_response["Rule"]["Actions"][0].should.have.key("BounceAction")

    receipt_rule_response["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "TopicArn"
    ).being.equal("string")
    receipt_rule_response["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "SmtpReplyCode"
    ).being.equal("string")
    receipt_rule_response["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "StatusCode"
    ).being.equal("string")
    receipt_rule_response["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "Message"
    ).being.equal("string")
    receipt_rule_response["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "Sender"
    ).being.equal("string")

    receipt_rule_response["Rule"]["ScanEnabled"].should.equal(False)

    with pytest.raises(ClientError) as error:
        conn.describe_receipt_rule(RuleSetName="invalidRuleSetName", RuleName=rule_name)

    error.value.response["Error"]["Code"].should.equal("RuleSetDoesNotExist")

    with pytest.raises(ClientError) as error:
        conn.describe_receipt_rule(
            RuleSetName=rule_set_name, RuleName="invalidRuleName"
        )

    error.value.response["Error"]["Code"].should.equal("RuleDoesNotExist")


@mock_ses
def test_update_receipt_rule():
    conn = boto3.client("ses", region_name="us-east-1")
    rule_set_name = "testRuleSet"
    conn.create_receipt_rule_set(RuleSetName=rule_set_name)

    rule_name = "testRule"
    conn.create_receipt_rule(
        RuleSetName=rule_set_name,
        Rule={
            "Name": rule_name,
            "Enabled": False,
            "TlsPolicy": "Optional",
            "Recipients": ["test@email.com", "test2@email.com"],
            "Actions": [
                {
                    "S3Action": {
                        "TopicArn": "string",
                        "BucketName": "testBucketName",
                        "ObjectKeyPrefix": "testObjectKeyPrefix",
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

    update_receipt_rule_response = conn.update_receipt_rule(
        RuleSetName=rule_set_name,
        Rule={
            "Name": rule_name,
            "Enabled": True,
            "TlsPolicy": "Optional",
            "Recipients": ["test@email.com"],
            "Actions": [
                {
                    "S3Action": {
                        "TopicArn": "string",
                        "BucketName": "testBucketName",
                        "ObjectKeyPrefix": "testObjectKeyPrefix",
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

    update_receipt_rule_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    updated_rule_description = conn.describe_receipt_rule(
        RuleSetName=rule_set_name, RuleName=rule_name
    )

    updated_rule_description["Rule"]["Name"].should.equal(rule_name)
    updated_rule_description["Rule"]["Enabled"].should.equal(True)
    len(updated_rule_description["Rule"]["Recipients"]).should.equal(1)
    updated_rule_description["Rule"]["Recipients"][0].should.equal("test@email.com")

    len(updated_rule_description["Rule"]["Actions"]).should.equal(1)
    updated_rule_description["Rule"]["Actions"][0].should.have.key("S3Action")
    updated_rule_description["Rule"]["Actions"][0].should.have.key("BounceAction")

    with pytest.raises(ClientError) as error:
        conn.update_receipt_rule(
            RuleSetName="invalidRuleSetName",
            Rule={
                "Name": rule_name,
                "Enabled": True,
                "TlsPolicy": "Optional",
                "Recipients": ["test@email.com"],
                "Actions": [
                    {
                        "S3Action": {
                            "TopicArn": "string",
                            "BucketName": "testBucketName",
                            "ObjectKeyPrefix": "testObjectKeyPrefix",
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

    error.value.response["Error"]["Code"].should.equal("RuleSetDoesNotExist")
    error.value.response["Error"]["Message"].should.equal(
        "Rule set does not exist: invalidRuleSetName"
    )

    with pytest.raises(ClientError) as error:
        conn.update_receipt_rule(
            RuleSetName=rule_set_name,
            Rule={
                "Name": "invalidRuleName",
                "Enabled": True,
                "TlsPolicy": "Optional",
                "Recipients": ["test@email.com"],
                "Actions": [
                    {
                        "S3Action": {
                            "TopicArn": "string",
                            "BucketName": "testBucketName",
                            "ObjectKeyPrefix": "testObjectKeyPrefix",
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

    error.value.response["Error"]["Code"].should.equal("RuleDoesNotExist")
    error.value.response["Error"]["Message"].should.equal(
        "Rule does not exist: invalidRuleName"
    )

    with pytest.raises(ParamValidationError) as error:
        conn.update_receipt_rule(
            RuleSetName=rule_set_name,
            Rule={
                "Enabled": True,
                "TlsPolicy": "Optional",
                "Recipients": ["test@email.com"],
                "Actions": [
                    {
                        "S3Action": {
                            "TopicArn": "string",
                            "BucketName": "testBucketName",
                            "ObjectKeyPrefix": "testObjectKeyPrefix",
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

    str(error.value).should.contain(
        'Parameter validation failed:\nMissing required parameter in Rule: "Name"'
    )


@mock_ses
def test_update_receipt_rule_actions():
    conn = boto3.client("ses", region_name="us-east-1")
    rule_set_name = "testRuleSet"
    conn.create_receipt_rule_set(RuleSetName=rule_set_name)

    rule_name = "testRule"
    conn.create_receipt_rule(
        RuleSetName=rule_set_name,
        Rule={
            "Name": rule_name,
            "Enabled": False,
            "TlsPolicy": "Optional",
            "Recipients": ["test@email.com", "test2@email.com"],
            "Actions": [
                {
                    "S3Action": {
                        "TopicArn": "string",
                        "BucketName": "testBucketName",
                        "ObjectKeyPrefix": "testObjectKeyPrefix",
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

    update_receipt_rule_response = conn.update_receipt_rule(
        RuleSetName=rule_set_name,
        Rule={
            "Name": rule_name,
            "Enabled": False,
            "TlsPolicy": "Optional",
            "Recipients": ["test@email.com", "test2@email.com"],
            "Actions": [
                {
                    "S3Action": {
                        "TopicArn": "newString",
                        "BucketName": "updatedTestBucketName",
                        "ObjectKeyPrefix": "updatedTestObjectKeyPrefix",
                        "KmsKeyArn": "newString",
                    },
                    "BounceAction": {
                        "TopicArn": "newString",
                        "SmtpReplyCode": "newString",
                        "StatusCode": "newString",
                        "Message": "newString",
                        "Sender": "newString",
                    },
                }
            ],
            "ScanEnabled": False,
        },
    )

    update_receipt_rule_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    updated_rule_description = conn.describe_receipt_rule(
        RuleSetName=rule_set_name, RuleName=rule_name
    )

    len(updated_rule_description["Rule"]["Actions"]).should.equal(1)
    updated_rule_description["Rule"]["Actions"][0].should.have.key("S3Action")

    updated_rule_description["Rule"]["Actions"][0]["S3Action"].should.have.key(
        "TopicArn"
    ).being.equal("newString")
    updated_rule_description["Rule"]["Actions"][0]["S3Action"].should.have.key(
        "BucketName"
    ).being.equal("updatedTestBucketName")
    updated_rule_description["Rule"]["Actions"][0]["S3Action"].should.have.key(
        "ObjectKeyPrefix"
    ).being.equal("updatedTestObjectKeyPrefix")
    updated_rule_description["Rule"]["Actions"][0]["S3Action"].should.have.key(
        "KmsKeyArn"
    ).being.equal("newString")

    updated_rule_description["Rule"]["Actions"][0].should.have.key("BounceAction")

    updated_rule_description["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "TopicArn"
    ).being.equal("newString")
    updated_rule_description["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "SmtpReplyCode"
    ).being.equal("newString")
    updated_rule_description["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "StatusCode"
    ).being.equal("newString")
    updated_rule_description["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "Message"
    ).being.equal("newString")
    updated_rule_description["Rule"]["Actions"][0]["BounceAction"].should.have.key(
        "Sender"
    ).being.equal("newString")

    with pytest.raises(ParamValidationError) as error:
        conn.update_receipt_rule(
            RuleSetName=rule_set_name,
            Rule={
                "Name": rule_name,
                "Enabled": False,
                "TlsPolicy": "Optional",
                "Recipients": ["test@email.com", "test2@email.com"],
                "Actions": [
                    {
                        "S3Action": {
                            "TopicArn": "newString",
                            "ObjectKeyPrefix": "updatedTestObjectKeyPrefix",
                            "KmsKeyArn": "newString",
                        },
                        "BounceAction": {
                            "TopicArn": "newString",
                            "StatusCode": "newString",
                        },
                    }
                ],
                "ScanEnabled": False,
            },
        )

    assert (str(error.value)).should.contain(
        'Parameter validation failed:\nMissing required parameter in Rule.Actions[0].S3Action: "BucketName"\nMissing required parameter in Rule.Actions[0].BounceAction: "SmtpReplyCode"\nMissing required parameter in Rule.Actions[0].BounceAction: "Message"\nMissing required parameter in Rule.Actions[0].BounceAction: "Sender"'
    )


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

    kwargs = dict(
        TemplateName="MyTestTemplate",
        TemplateData=json.dumps({"name": "John", "favoriteanimal": "Lion"}),
    )

    conn.create_template(
        Template={
            "TemplateName": "MyTestTemplate1",
            "SubjectPart": "Greetings, {{name}}!",
            "TextPart": "Dear {{name}},"
            "\r\nYour favorite animal is {{favoriteanimal}}.",
            "HtmlPart": "<h1>Hello {{name}},"
            "</h1><p>Your favorite animal is {{favoriteanimal  }}.</p>",
        }
    )

    result = conn.test_render_template(**kwargs)
    result["RenderedTemplate"].should.contain("Subject: Greetings, John!")
    result["RenderedTemplate"].should.contain("Dear John,")
    result["RenderedTemplate"].should.contain("<h1>Hello John,</h1>")
    result["RenderedTemplate"].should.contain("Your favorite animal is Lion")

    kwargs = dict(
        TemplateName="MyTestTemplate", TemplateData=json.dumps({"name": "John"})
    )

    with pytest.raises(ClientError) as ex:
        conn.test_render_template(**kwargs)
    assert ex.value.response["Error"]["Code"] == "MissingRenderingAttributeException"
    assert (
        ex.value.response["Error"]["Message"]
        == "Attribute 'favoriteanimal' is not present in the rendering data."
    )


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


@mock_ses
def test_domains_are_case_insensitive():
    client = boto3.client("ses", region_name="us-east-1")
    duplicate_domains = [
        "EXAMPLE.COM",
        "EXAMple.Com",
        "example.com",
    ]
    for domain in duplicate_domains:
        client.verify_domain_identity(Domain=domain)
        client.verify_domain_dkim(Domain=domain)
        identities = client.list_identities(IdentityType="Domain")["Identities"]
        identities.should.have.length_of(1)
        identities[0].should.equal("example.com")


@mock_ses
def test_get_send_statistics():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = dict(
        Source="test@example.com",
        Destination={"ToAddresses": ["test_to@example.com"]},
        Message={
            "Subject": {"Data": "test subject"},
            "Body": {"Html": {"Data": "<span>test body</span>"}},
        },
    )
    with pytest.raises(ClientError) as ex:
        conn.send_email(**kwargs)
    err = ex.value.response["Error"]
    err["Code"].should.equal("MessageRejected")
    err["Message"].should.equal("Email address not verified test@example.com")

    # tests to verify rejects in get_send_statistics
    stats = conn.get_send_statistics()["SendDataPoints"]

    stats[0]["Rejects"].should.equal(1)
    stats[0]["DeliveryAttempts"].should.equal(0)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(
        Source="test@example.com",
        Message={
            "Subject": {"Data": "test subject"},
            "Body": {"Text": {"Data": "test body"}},
        },
        Destination={"ToAddresses": ["test_to@example.com"]},
    )

    # tests to delivery attempts in get_send_statistics
    stats = conn.get_send_statistics()["SendDataPoints"]

    stats[0]["Rejects"].should.equal(1)
    stats[0]["DeliveryAttempts"].should.equal(1)


@mock_ses
def test_set_identity_mail_from_domain():
    conn = boto3.client("ses", region_name="eu-central-1")

    # Must raise if provided identity does not exist
    with pytest.raises(ClientError) as exc:
        conn.set_identity_mail_from_domain(Identity="foo.com")
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Identity 'foo.com' does not exist.")

    conn.verify_domain_identity(Domain="foo.com")

    # Must raise if MAILFROM is not a subdomain of identity
    with pytest.raises(ClientError) as exc:
        conn.set_identity_mail_from_domain(
            Identity="foo.com", MailFromDomain="lorem.ipsum.com"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "Provided MAIL-FROM domain 'lorem.ipsum.com' is not subdomain of "
        "the domain of the identity 'foo.com'."
    )

    # Must raise if BehaviorOnMXFailure is not a valid choice
    with pytest.raises(ClientError) as exc:
        conn.set_identity_mail_from_domain(
            Identity="foo.com",
            MailFromDomain="lorem.foo.com",
            BehaviorOnMXFailure="SelfDestruct",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "1 validation error detected: Value 'SelfDestruct' at "
        "'behaviorOnMXFailure'failed to satisfy constraint: Member must "
        "satisfy enum value set: [RejectMessage, UseDefaultValue]"
    )

    # Must set config for valid input
    behaviour_on_mx_failure = "RejectMessage"
    mail_from_domain = "lorem.foo.com"

    conn.set_identity_mail_from_domain(
        Identity="foo.com",
        MailFromDomain=mail_from_domain,
        BehaviorOnMXFailure=behaviour_on_mx_failure,
    )

    attributes = conn.get_identity_mail_from_domain_attributes(Identities=["foo.com"])
    actual_attributes = attributes["MailFromDomainAttributes"]["foo.com"]
    actual_attributes.should.have.key("MailFromDomain").being.equal(mail_from_domain)
    actual_attributes.should.have.key("BehaviorOnMXFailure").being.equal(
        behaviour_on_mx_failure
    )
    actual_attributes.should.have.key("MailFromDomainStatus").being.equal("Success")

    # Must unset config when MailFromDomain is null
    conn.set_identity_mail_from_domain(Identity="foo.com")

    attributes = conn.get_identity_mail_from_domain_attributes(Identities=["foo.com"])
    actual_attributes = attributes["MailFromDomainAttributes"]["foo.com"]
    actual_attributes.should.have.key("BehaviorOnMXFailure").being.equal(
        "UseDefaultValue"
    )
    actual_attributes.should_not.have.key("MailFromDomain")
    actual_attributes.should_not.have.key("MailFromDomainStatus")


@mock_ses
def test_get_identity_mail_from_domain_attributes():
    conn = boto3.client("ses", region_name="eu-central-1")

    # Must return empty for non-existent identities
    attributes = conn.get_identity_mail_from_domain_attributes(
        Identities=["bar@foo.com", "lorem.com"]
    )
    attributes["MailFromDomainAttributes"].should.have.length_of(0)

    # Must return default options for non-configured identities
    conn.verify_email_identity(EmailAddress="bar@foo.com")
    attributes = conn.get_identity_mail_from_domain_attributes(
        Identities=["bar@foo.com", "lorem.com"]
    )
    attributes["MailFromDomainAttributes"].should.have.length_of(1)
    attributes["MailFromDomainAttributes"]["bar@foo.com"].should.have.length_of(1)
    attributes["MailFromDomainAttributes"]["bar@foo.com"].should.have.key(
        "BehaviorOnMXFailure"
    ).being.equal("UseDefaultValue")

    # Must return multiple configured identities
    conn.verify_domain_identity(Domain="lorem.com")
    attributes = conn.get_identity_mail_from_domain_attributes(
        Identities=["bar@foo.com", "lorem.com"]
    )
    attributes["MailFromDomainAttributes"].should.have.length_of(2)
    attributes["MailFromDomainAttributes"]["bar@foo.com"].should.have.length_of(1)
    attributes["MailFromDomainAttributes"]["lorem.com"].should.have.length_of(1)
