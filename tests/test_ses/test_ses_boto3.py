import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import pytest
from botocore.exceptions import ClientError, ParamValidationError

from moto import mock_aws

from . import ses_aws_verified


@mock_aws
def test_list_verified_identities():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="test@example.com")

    identities = conn.list_identities()["Identities"]
    assert identities == ["test@example.com"]

    conn.verify_domain_dkim(Domain="domain1.com")
    conn.verify_domain_identity(Domain="domain2.com")

    identities = conn.list_identities()["Identities"]
    assert identities == ["domain1.com", "domain2.com", "test@example.com"]

    identities = conn.list_identities(IdentityType="EmailAddress")["Identities"]
    assert identities == ["test@example.com"]

    identities = conn.list_identities(IdentityType="Domain")["Identities"]
    assert identities == ["domain1.com", "domain2.com"]

    with pytest.raises(ClientError) as exc:
        conn.list_identities(IdentityType="Unknown")
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == "Value 'Unknown' at 'identityType' failed to satisfy constraint: Member must satisfy enum value set: [Domain, EmailAddress]"
    )


@mock_aws
def test_identities_are_region_specific():
    us_east = boto3.client("ses", region_name="us-east-1")
    us_east.verify_email_identity(EmailAddress="test@example.com")

    us_west = boto3.client("ses", region_name="us-west-1")
    assert not us_west.list_identities()["Identities"]


@mock_aws
def test_verify_email_identity_idempotency():
    conn = boto3.client("ses", region_name="us-east-1")
    address = "test@example.com"
    conn.verify_email_identity(EmailAddress=address)
    conn.verify_email_identity(EmailAddress=address)

    identities = conn.list_identities()
    address_list = identities["Identities"]
    assert address_list == [address]


@mock_aws
def test_verify_email_address():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_address(EmailAddress="test@example.com")
    email_addresses = conn.list_verified_email_addresses()
    email = email_addresses["VerifiedEmailAddresses"][0]
    assert email == "test@example.com"


@mock_aws
def test_delete_identity():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress="test@example.com")

    assert len(conn.list_identities()["Identities"]) == 1
    conn.delete_identity(Identity="test@example.com")
    assert not conn.list_identities()["Identities"]


@mock_aws
def test_send_email():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = {
        "Source": "test@example.com",
        "Destination": {
            "ToAddresses": ["test_to@example.com"],
            "CcAddresses": ["test_cc@example.com"],
            "BccAddresses": ["test_bcc@example.com"],
        },
        "Message": {
            "Subject": {"Data": "test subject"},
            "Body": {"Text": {"Data": "test body"}},
        },
    }

    with pytest.raises(ClientError):
        conn.send_email(**kwargs)

    conn.verify_domain_identity(Domain="example.com")
    conn.send_email(**kwargs)

    too_many_addresses = list(f"to{i}@example.com" for i in range(51))
    with pytest.raises(ClientError):
        conn.send_email(**dict(kwargs, Destination={"ToAddresses": too_many_addresses}))

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 3


@mock_aws
def test_send_email_when_verify_source():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = {
        "Destination": {"ToAddresses": ["test_to@example.com"]},
        "Message": {
            "Subject": {"Data": "test subject"},
            "Body": {"Text": {"Data": "test body"}},
        },
    }

    with pytest.raises(ClientError):
        conn.send_email(Source="verify_email_address@example.com", **kwargs)

    conn.verify_email_address(EmailAddress="verify_email_address@example.com")
    conn.send_email(Source="verify_email_address@example.com", **kwargs)

    with pytest.raises(ClientError):
        conn.send_email(Source="verify_email_identity@example.com", **kwargs)

    conn.verify_email_identity(EmailAddress="verify_email_identity@example.com")
    conn.send_email(Source="verify_email_identity@example.com", **kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 2


@mock_aws
def test_send_unverified_email_with_chevrons():
    conn = boto3.client("ses", region_name="us-east-1")

    # Sending an email to an unverified source should fail
    with pytest.raises(ClientError) as ex:
        conn.send_email(
            Source="John Smith <foobar@example.com>",  # << Unverified source address
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
    assert err["Code"] == "MessageRejected"
    # The source should be returned exactly as provided - without XML encoding issues
    assert (
        err["Message"] == "Email address not verified John Smith <foobar@example.com>"
    )


@mock_aws
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
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Missing domain"


@mock_aws
def test_send_bulk_templated_email():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = {
        "Source": "test@example.com",
        "Destinations": [
            {
                "Destination": {
                    "ToAddresses": ["test_to@example.com"],
                    "CcAddresses": ["test_cc@example.com"],
                    "BccAddresses": ["test_bcc@example.com"],
                }
            },
            {
                "Destination": {
                    "ToAddresses": ["test_to1@example.com"],
                    "CcAddresses": ["test_cc1@example.com"],
                    "BccAddresses": ["test_bcc1@example.com"],
                }
            },
        ],
        "Template": "test_template",
        "DefaultTemplateData": '{"name": "test"}',
    }

    with pytest.raises(ClientError) as ex:
        conn.send_bulk_templated_email(**kwargs)

    assert ex.value.response["Error"]["Code"] == "MessageRejected"
    assert (
        ex.value.response["Error"]["Message"]
        == "Email address not verified test@example.com"
    )

    conn.verify_domain_identity(Domain="example.com")

    with pytest.raises(ClientError) as ex:
        conn.send_bulk_templated_email(**kwargs)

    assert ex.value.response["Error"]["Code"] == "TemplateDoesNotExist"

    conn.create_template(
        Template={
            "TemplateName": "test_template",
            "SubjectPart": "lalala",
            "HtmlPart": "",
            "TextPart": "",
        }
    )

    conn.send_bulk_templated_email(**kwargs)

    too_many_destinations = list(
        {
            "Destination": {
                "ToAddresses": [f"to{i}@example.com"],
                "CcAddresses": [],
                "BccAddresses": [],
            }
        }
        for i in range(51)
    )

    with pytest.raises(ClientError) as ex:
        args = dict(kwargs, Destinations=too_many_destinations)
        conn.send_bulk_templated_email(**args)

    assert ex.value.response["Error"]["Code"] == "MessageRejected"
    assert ex.value.response["Error"]["Message"] == "Too many destinations."

    too_many_destinations = list(f"to{i}@example.com" for i in range(51))

    with pytest.raises(ClientError) as ex:
        args = dict(
            kwargs,
            Destinations=[
                {
                    "Destination": {
                        "ToAddresses": too_many_destinations,
                        "CcAddresses": [],
                        "BccAddresses": [],
                    }
                }
            ],
        )
        conn.send_bulk_templated_email(**args)

    assert ex.value.response["Error"]["Code"] == "MessageRejected"
    assert ex.value.response["Error"]["Message"] == "Too many destinations."

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 6


@mock_aws
def test_send_templated_email():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = {
        "Source": "test@example.com",
        "Destination": {
            "ToAddresses": ["test_to@example.com"],
            "CcAddresses": ["test_cc@example.com"],
            "BccAddresses": ["test_bcc@example.com"],
        },
        "Template": "test_template",
        "TemplateData": '{"name": "test"}',
    }

    with pytest.raises(ClientError):
        conn.send_templated_email(**kwargs)

    conn.verify_domain_identity(Domain="example.com")

    with pytest.raises(ClientError) as ex:
        conn.send_templated_email(**kwargs)

    assert ex.value.response["Error"]["Code"] == "TemplateDoesNotExist"

    conn.create_template(
        Template={
            "TemplateName": "test_template",
            "SubjectPart": "lalala",
            "HtmlPart": "",
            "TextPart": "",
        }
    )

    conn.send_templated_email(**kwargs)

    too_many_addresses = list(f"to{i}@example.com" for i in range(51))
    with pytest.raises(ClientError) as ex:
        conn.send_templated_email(
            **dict(kwargs, Destination={"ToAddresses": too_many_addresses})
        )

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 3


@mock_aws
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
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Missing domain"


@mock_aws
def test_send_html_email():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = {
        "Source": "test@example.com",
        "Destination": {"ToAddresses": ["test_to@example.com"]},
        "Message": {
            "Subject": {"Data": "test subject"},
            "Body": {"Html": {"Data": "test body"}},
        },
    }

    with pytest.raises(ClientError):
        conn.send_email(**kwargs)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 1


@mock_aws
def test_send_raw_email():
    conn = boto3.client("ses", region_name="us-east-1")

    message = get_raw_email()

    kwargs = {"Source": message["From"], "RawMessage": {"Data": message.as_string()}}

    with pytest.raises(ClientError):
        conn.send_raw_email(**kwargs)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_raw_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 2


@mock_aws
def test_send_raw_email_validate_domain():
    conn = boto3.client("ses", region_name="us-east-1")

    message = get_raw_email()

    kwargs = {"Source": message["From"], "RawMessage": {"Data": message.as_string()}}

    with pytest.raises(ClientError):
        conn.send_raw_email(**kwargs)

    conn.verify_domain_identity(Domain="example.com")
    conn.send_raw_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 2


@mock_aws
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
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Missing domain"


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


@mock_aws
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

    kwargs = {"RawMessage": {"Data": message.as_string()}}

    with pytest.raises(ClientError):
        conn.send_raw_email(**kwargs)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_raw_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 2


@mock_aws
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

    kwargs = {"RawMessage": {"Data": message.as_string()}}

    with pytest.raises(ClientError):
        conn.send_raw_email(**kwargs)


@mock_aws
def test_send_email_notification_with_encoded_sender():
    sender = "Foo <foo@bar.baz>"
    conn = boto3.client("ses", region_name="us-east-1")
    conn.verify_email_identity(EmailAddress=sender)
    response = conn.send_email(
        Source=sender,
        Destination={"ToAddresses": ["your.friend@hotmail.com"]},
        Message={"Subject": {"Data": "hi"}, "Body": {"Text": {"Data": "there"}}},
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_create_configuration_set():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.create_configuration_set(ConfigurationSet=dict({"Name": "test"}))

    with pytest.raises(ClientError) as ex:
        conn.create_configuration_set(ConfigurationSet=dict({"Name": "test"}))
    assert ex.value.response["Error"]["Code"] == "ConfigurationSetAlreadyExists"

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

    assert ex.value.response["Error"]["Code"] == "ConfigurationSetDoesNotExist"

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

    assert ex.value.response["Error"]["Code"] == "EventDestinationAlreadyExists"


@mock_aws
def test_describe_configuration_set():
    conn = boto3.client("ses", region_name="us-east-1")

    name = "test"
    conn.create_configuration_set(ConfigurationSet=dict({"Name": name}))

    with pytest.raises(ClientError) as ex:
        conn.describe_configuration_set(
            ConfigurationSetName="failtest",
        )
    assert ex.value.response["Error"]["Code"] == "ConfigurationSetDoesNotExist"

    config_set = conn.describe_configuration_set(
        ConfigurationSetName=name,
    )
    assert config_set["ConfigurationSet"]["Name"] == name


@mock_aws
def test_create_receipt_rule_set():
    conn = boto3.client("ses", region_name="us-east-1")
    result = conn.create_receipt_rule_set(RuleSetName="testRuleSet")

    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200

    with pytest.raises(ClientError) as ex:
        conn.create_receipt_rule_set(RuleSetName="testRuleSet")

    assert ex.value.response["Error"]["Code"] == "RuleSetNameAlreadyExists"


@mock_aws
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

    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200

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

    assert ex.value.response["Error"]["Code"] == "RuleAlreadyExists"

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

    assert ex.value.response["Error"]["Code"] == "RuleSetDoesNotExist"


@mock_aws
def test_describe_receipt_rule_set():
    conn = boto3.client("ses", region_name="us-east-1")
    create_receipt_rule_set_response = conn.create_receipt_rule_set(
        RuleSetName="testRuleSet"
    )

    assert create_receipt_rule_set_response["ResponseMetadata"]["HTTPStatusCode"] == 200

    result = conn.describe_receipt_rule_set(RuleSetName="testRuleSet")

    assert result["Metadata"]["Name"] == "testRuleSet"
    # assert result['Metadata']['CreatedTimestamp'] == ""

    assert not result["Rules"]


@mock_aws
def test_describe_receipt_rule_set_with_rules():
    conn = boto3.client("ses", region_name="us-east-1")
    create_receipt_rule_set_response = conn.create_receipt_rule_set(
        RuleSetName="testRuleSet"
    )

    assert create_receipt_rule_set_response["ResponseMetadata"]["HTTPStatusCode"] == 200

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

    assert create_receipt_rule_response["ResponseMetadata"]["HTTPStatusCode"] == 200

    result = conn.describe_receipt_rule_set(RuleSetName="testRuleSet")

    assert result["Metadata"]["Name"] == "testRuleSet"
    # assert result['Metadata']['CreatedTimestamp'] == ""

    assert len(result["Rules"]) == 1
    assert result["Rules"][0] == receipt_rule


@mock_aws
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

    assert receipt_rule_response["Rule"]["Name"] == rule_name

    assert receipt_rule_response["Rule"]["Enabled"] is False

    assert receipt_rule_response["Rule"]["TlsPolicy"] == "Optional"

    assert len(receipt_rule_response["Rule"]["Recipients"]) == 2
    assert receipt_rule_response["Rule"]["Recipients"][0] == "test@email.com"

    assert len(receipt_rule_response["Rule"]["Actions"]) == 1
    assert "S3Action" in receipt_rule_response["Rule"]["Actions"][0]

    assert (
        receipt_rule_response["Rule"]["Actions"][0]["S3Action"]["TopicArn"] == "string"
    )
    assert receipt_rule_response["Rule"]["Actions"][0]["S3Action"]["BucketName"] == (
        "testBucketName"
    )
    assert receipt_rule_response["Rule"]["Actions"][0]["S3Action"][
        "ObjectKeyPrefix"
    ] == ("testObjectKeyPrefix")
    assert (
        receipt_rule_response["Rule"]["Actions"][0]["S3Action"]["KmsKeyArn"] == "string"
    )

    assert "BounceAction" in receipt_rule_response["Rule"]["Actions"][0]

    assert (
        receipt_rule_response["Rule"]["Actions"][0]["BounceAction"]["TopicArn"]
        == "string"
    )
    assert (
        receipt_rule_response["Rule"]["Actions"][0]["BounceAction"]["SmtpReplyCode"]
        == "string"
    )
    assert (
        receipt_rule_response["Rule"]["Actions"][0]["BounceAction"]["StatusCode"]
        == "string"
    )
    assert (
        receipt_rule_response["Rule"]["Actions"][0]["BounceAction"]["Message"]
        == "string"
    )
    assert (
        receipt_rule_response["Rule"]["Actions"][0]["BounceAction"]["Sender"]
        == "string"
    )

    assert receipt_rule_response["Rule"]["ScanEnabled"] is False

    with pytest.raises(ClientError) as error:
        conn.describe_receipt_rule(RuleSetName="invalidRuleSetName", RuleName=rule_name)

    assert error.value.response["Error"]["Code"] == "RuleSetDoesNotExist"

    with pytest.raises(ClientError) as error:
        conn.describe_receipt_rule(
            RuleSetName=rule_set_name, RuleName="invalidRuleName"
        )

    assert error.value.response["Error"]["Code"] == "RuleDoesNotExist"


@mock_aws
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

    assert update_receipt_rule_response["ResponseMetadata"]["HTTPStatusCode"] == 200

    updated_rule_description = conn.describe_receipt_rule(
        RuleSetName=rule_set_name, RuleName=rule_name
    )

    assert updated_rule_description["Rule"]["Name"] == rule_name
    assert updated_rule_description["Rule"]["Enabled"] is True
    assert len(updated_rule_description["Rule"]["Recipients"]) == 1
    assert updated_rule_description["Rule"]["Recipients"][0] == "test@email.com"

    assert len(updated_rule_description["Rule"]["Actions"]) == 1
    assert "S3Action" in updated_rule_description["Rule"]["Actions"][0]
    assert "BounceAction" in updated_rule_description["Rule"]["Actions"][0]

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

    assert error.value.response["Error"]["Code"] == "RuleSetDoesNotExist"
    assert error.value.response["Error"]["Message"] == (
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

    assert error.value.response["Error"]["Code"] == "RuleDoesNotExist"
    assert error.value.response["Error"]["Message"] == (
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

    assert (
        'Parameter validation failed:\nMissing required parameter in Rule: "Name"'
    ) in str(error.value)


@mock_aws
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

    assert update_receipt_rule_response["ResponseMetadata"]["HTTPStatusCode"] == 200

    updated_rule_description = conn.describe_receipt_rule(
        RuleSetName=rule_set_name, RuleName=rule_name
    )

    assert len(updated_rule_description["Rule"]["Actions"]) == 1
    assert "S3Action" in updated_rule_description["Rule"]["Actions"][0]

    assert (
        (updated_rule_description["Rule"]["Actions"][0]["S3Action"]["TopicArn"])
        == "newString"
    )
    assert (
        (updated_rule_description["Rule"]["Actions"][0]["S3Action"]["BucketName"])
        == "updatedTestBucketName"
    )
    assert updated_rule_description["Rule"]["Actions"][0]["S3Action"][
        "ObjectKeyPrefix"
    ] == ("updatedTestObjectKeyPrefix")
    assert (
        updated_rule_description["Rule"]["Actions"][0]["S3Action"]["KmsKeyArn"]
        == "newString"
    )

    assert "BounceAction" in updated_rule_description["Rule"]["Actions"][0]

    assert (
        updated_rule_description["Rule"]["Actions"][0]["BounceAction"]["TopicArn"]
        == "newString"
    )
    assert (
        (
            updated_rule_description["Rule"]["Actions"][0]["BounceAction"][
                "SmtpReplyCode"
            ]
        )
        == "newString"
    )
    assert (
        (updated_rule_description["Rule"]["Actions"][0]["BounceAction"]["StatusCode"])
        == "newString"
    )
    assert (
        updated_rule_description["Rule"]["Actions"][0]["BounceAction"]["Message"]
        == "newString"
    )
    assert (
        updated_rule_description["Rule"]["Actions"][0]["BounceAction"]["Sender"]
        == "newString"
    )

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

    assert (
        "Parameter validation failed:\n"
        'Missing required parameter in Rule.Actions[0].S3Action: "BucketName"\n'
        'Missing required parameter in Rule.Actions[0].BounceAction: "SmtpReplyCode"\n'
        'Missing required parameter in Rule.Actions[0].BounceAction: "Message"\n'
        'Missing required parameter in Rule.Actions[0].BounceAction: "Sender"'
    ) in str(error.value)


@mock_aws
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

    assert ex.value.response["Error"]["Code"] == "TemplateNameAlreadyExists"

    # get a template which is already added
    result = conn.get_template(TemplateName="MyTemplate")
    assert result["Template"]["TemplateName"] == "MyTemplate"
    assert result["Template"]["SubjectPart"] == "Greetings, {{name}}!"
    assert result["Template"]["HtmlPart"] == (
        "<h1>Hello {{name}}," "</h1><p>Your favorite animal is {{favoriteanimal}}.</p>"
    )
    # get a template which is not present
    with pytest.raises(ClientError) as ex:
        conn.get_template(TemplateName="MyFakeTemplate")

    assert ex.value.response["Error"]["Code"] == "TemplateDoesNotExist"

    result = conn.list_templates()
    assert result["TemplatesMetadata"][0]["Name"] == "MyTemplate"


@mock_aws
def test_render_template():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = {
        "TemplateName": "MyTestTemplate",
        "TemplateData": json.dumps({"name": "John", "favoriteanimal": "Lion"}),
    }

    with pytest.raises(ClientError) as ex:
        conn.test_render_template(**kwargs)
    assert ex.value.response["Error"]["Code"] == "TemplateDoesNotExist"

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
    assert "Subject: Greetings, John!" in result["RenderedTemplate"]
    assert "Dear John," in result["RenderedTemplate"]
    assert "<h1>Hello John,</h1>" in result["RenderedTemplate"]
    assert "Your favorite animal is Lion" in result["RenderedTemplate"]

    kwargs = {
        "TemplateName": "MyTestTemplate",
        "TemplateData": json.dumps({"name": "John", "favoriteanimal": "Lion"}),
    }

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
    assert "Subject: Greetings, John!" in result["RenderedTemplate"]
    assert "Dear John," in result["RenderedTemplate"]
    assert "<h1>Hello John,</h1>" in result["RenderedTemplate"]
    assert "Your favorite animal is Lion" in result["RenderedTemplate"]

    kwargs = {
        "TemplateName": "MyTestTemplate",
        "TemplateData": json.dumps({"name": "John"}),
    }

    with pytest.raises(ClientError) as ex:
        conn.test_render_template(**kwargs)
    assert ex.value.response["Error"]["Code"] == "MissingRenderingAttributeException"
    assert (
        ex.value.response["Error"]["Message"]
        == "Attribute 'favoriteanimal' is not present in the rendering data."
    )


@pytest.mark.aws_verified
@ses_aws_verified
def test_render_template__advanced():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = {
        "TemplateName": "MTT",
        "TemplateData": json.dumps(
            {
                "items": [
                    {"type": "dog", "name": "bobby", "best": True},
                    {"type": "cat", "name": "pedro", "best": False},
                ]
            }
        ),
    }

    try:
        conn.create_template(
            Template={
                "TemplateName": "MTT",
                "SubjectPart": "..",
                "TextPart": "..",
                "HtmlPart": "{{#each items}} {{name}} is {{#if best}}the best{{else}}a {{type}}{{/if}}, {{/each}}",
            }
        )
        result = conn.test_render_template(**kwargs)
        assert "bobby is the best" in result["RenderedTemplate"]
        assert "pedro is a cat" in result["RenderedTemplate"]
    finally:
        conn.delete_template(TemplateName="MTT")


@mock_aws
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
    assert ex.value.response["Error"]["Code"] == "TemplateDoesNotExist"

    conn.create_template(Template=template)

    template["SubjectPart"] = "Hi, {{name}}!"
    template["TextPart"] = "Dear {{name}},\r\n Your favorite color is {{color}}"
    template["HtmlPart"] = (
        "<h1>Hello {{name}},</h1><p>Your favorite color is {{color}}</p>"
    )
    conn.update_template(Template=template)

    result = conn.get_template(TemplateName=template["TemplateName"])
    assert result["Template"]["SubjectPart"] == "Hi, {{name}}!"
    assert result["Template"]["TextPart"] == (
        "Dear {{name}},\n Your favorite color is {{color}}"
    )
    assert result["Template"]["HtmlPart"] == (
        "<h1>Hello {{name}},</h1><p>Your favorite color is {{color}}</p>"
    )


@mock_aws
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
        assert len(identities) == 1
        assert identities[0] == "example.com"


@mock_aws
def test_get_send_statistics():
    conn = boto3.client("ses", region_name="us-east-1")

    kwargs = {
        "Source": "test@example.com",
        "Destination": {"ToAddresses": ["test_to@example.com"]},
        "Message": {
            "Subject": {"Data": "test subject"},
            "Body": {"Html": {"Data": "<span>test body</span>"}},
        },
    }
    with pytest.raises(ClientError) as ex:
        conn.send_email(**kwargs)
    err = ex.value.response["Error"]
    assert err["Code"] == "MessageRejected"
    assert err["Message"] == "Email address not verified test@example.com"

    # tests to verify rejects in get_send_statistics
    stats = conn.get_send_statistics()["SendDataPoints"]

    assert stats[0]["Rejects"] == 1
    assert stats[0]["DeliveryAttempts"] == 0

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

    assert stats[0]["Rejects"] == 1
    assert stats[0]["DeliveryAttempts"] == 1


@mock_aws
def test_set_identity_mail_from_domain():
    conn = boto3.client("ses", region_name="eu-central-1")

    # Must raise if provided identity does not exist
    with pytest.raises(ClientError) as exc:
        conn.set_identity_mail_from_domain(Identity="foo.com")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Identity 'foo.com' does not exist."

    conn.verify_domain_identity(Domain="foo.com")

    # Must raise if MAILFROM is not a subdomain of identity
    with pytest.raises(ClientError) as exc:
        conn.set_identity_mail_from_domain(
            Identity="foo.com", MailFromDomain="lorem.ipsum.com"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
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
    assert err["Code"] == "ValidationError"
    assert err["Message"] == (
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
    assert actual_attributes["MailFromDomain"] == mail_from_domain
    assert actual_attributes["BehaviorOnMXFailure"] == behaviour_on_mx_failure
    assert actual_attributes["MailFromDomainStatus"] == "Success"

    # Can use email address as an identity
    behaviour_on_mx_failure = "RejectMessage"
    mail_from_domain = "lorem.foo.com"

    conn.set_identity_mail_from_domain(
        Identity="test@foo.com",
        MailFromDomain=mail_from_domain,
        BehaviorOnMXFailure=behaviour_on_mx_failure,
    )

    attributes = conn.get_identity_mail_from_domain_attributes(Identities=["foo.com"])
    actual_attributes = attributes["MailFromDomainAttributes"]["foo.com"]
    assert actual_attributes["MailFromDomain"] == mail_from_domain
    assert actual_attributes["BehaviorOnMXFailure"] == behaviour_on_mx_failure
    assert actual_attributes["MailFromDomainStatus"] == "Success"

    # Must unset config when MailFromDomain is null
    conn.set_identity_mail_from_domain(Identity="foo.com")

    attributes = conn.get_identity_mail_from_domain_attributes(Identities=["foo.com"])
    actual_attributes = attributes["MailFromDomainAttributes"]["foo.com"]
    assert actual_attributes["BehaviorOnMXFailure"] == "UseDefaultValue"
    assert "MailFromDomain" not in actual_attributes
    assert "MailFromDomainStatus" not in actual_attributes


@mock_aws
def test_get_identity_mail_from_domain_attributes():
    conn = boto3.client("ses", region_name="eu-central-1")

    # Must return empty for non-existent identities
    attributes = conn.get_identity_mail_from_domain_attributes(
        Identities=["bar@foo.com", "lorem.com"]
    )
    assert not attributes["MailFromDomainAttributes"]

    # Must return default options for non-configured identities
    conn.verify_email_identity(EmailAddress="bar@foo.com")
    attributes = conn.get_identity_mail_from_domain_attributes(
        Identities=["bar@foo.com", "lorem.com"]
    )
    assert len(attributes["MailFromDomainAttributes"]) == 1
    assert len(attributes["MailFromDomainAttributes"]["bar@foo.com"]) == 1
    assert (
        (attributes["MailFromDomainAttributes"]["bar@foo.com"]["BehaviorOnMXFailure"])
        == "UseDefaultValue"
    )

    # Must return multiple configured identities
    conn.verify_domain_identity(Domain="lorem.com")
    attributes = conn.get_identity_mail_from_domain_attributes(
        Identities=["bar@foo.com", "lorem.com"]
    )
    assert len(attributes["MailFromDomainAttributes"]) == 2
    assert len(attributes["MailFromDomainAttributes"]["bar@foo.com"]) == 1
    assert len(attributes["MailFromDomainAttributes"]["lorem.com"]) == 1


@mock_aws
def test_get_identity_verification_attributes():
    conn = boto3.client("ses", region_name="eu-central-1")

    conn.verify_email_identity(EmailAddress="foo@bar.com")
    conn.verify_domain_identity(Domain="foo.com")

    attributes = conn.get_identity_verification_attributes(
        Identities=["foo.com", "foo@bar.com", "bar@bar.com"]
    )

    assert len(attributes["VerificationAttributes"]) == 2
    assert (
        attributes["VerificationAttributes"]["foo.com"]["VerificationStatus"]
        == "Success"
    )
    assert (
        attributes["VerificationAttributes"]["foo@bar.com"]["VerificationStatus"]
        == "Success"
    )
