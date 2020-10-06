from __future__ import unicode_literals

import boto3
import json
from botocore.exceptions import ClientError
from six.moves.email_mime_multipart import MIMEMultipart
from six.moves.email_mime_text import MIMEText

import sure  # noqa
from moto import mock_ses, mock_sns, mock_sqs
from moto.ses.models import SESFeedback
from moto.core import ACCOUNT_ID


@mock_ses
def test_enable_disable_ses_sns_communication():
    conn = boto3.client("ses", region_name="us-east-1")
    conn.set_identity_notification_topic(
        Identity="test.com", NotificationType="Bounce", SnsTopic="the-arn"
    )
    conn.set_identity_notification_topic(Identity="test.com", NotificationType="Bounce")


def __setup_feedback_env__(
    ses_conn, sns_conn, sqs_conn, domain, topic, queue, region, expected_msg
):
    """Setup the AWS environment to test the SES SNS Feedback"""
    # Environment setup
    # Create SQS queue
    sqs_conn.create_queue(QueueName=queue)
    # Create SNS topic
    create_topic_response = sns_conn.create_topic(Name=topic)
    topic_arn = create_topic_response["TopicArn"]
    # Subscribe the SNS topic to the SQS queue
    sns_conn.subscribe(
        TopicArn=topic_arn,
        Protocol="sqs",
        Endpoint="arn:aws:sqs:%s:%s:%s" % (region, ACCOUNT_ID, queue),
    )
    # Verify SES domain
    ses_conn.verify_domain_identity(Domain=domain)
    # Specify email address to allow for raw e-mails to be processed
    ses_conn.verify_email_identity(EmailAddress="test@example.com")
    # Setup SES notification topic
    if expected_msg is not None:
        ses_conn.set_identity_notification_topic(
            Identity=domain, NotificationType=expected_msg, SnsTopic=topic_arn
        )


def __test_sns_feedback__(addr, expected_msg, raw_email=False):
    region_name = "us-east-1"
    ses_conn = boto3.client("ses", region_name=region_name)
    sns_conn = boto3.client("sns", region_name=region_name)
    sqs_conn = boto3.resource("sqs", region_name=region_name)
    domain = "example.com"
    topic = "bounce-arn-feedback"
    queue = "feedback-test-queue"

    __setup_feedback_env__(
        ses_conn, sns_conn, sqs_conn, domain, topic, queue, region_name, expected_msg
    )

    # Send the message
    kwargs = dict(
        Source="test@" + domain,
        Destination={
            "ToAddresses": [addr + "@" + domain],
            "CcAddresses": ["test_cc@" + domain],
            "BccAddresses": ["test_bcc@" + domain],
        },
        Message={
            "Subject": {"Data": "test subject"},
            "Body": {"Text": {"Data": "test body"}},
        },
    )
    if raw_email:
        kwargs.pop("Message")
        kwargs.pop("Destination")
        kwargs.update(
            {
                "Destinations": [addr + "@" + domain],
                "RawMessage": {"Data": bytearray("raw_email", "utf-8")},
            }
        )
        ses_conn.send_raw_email(**kwargs)
    else:
        ses_conn.send_email(**kwargs)

    # Wait for messages in the queues
    queue = sqs_conn.get_queue_by_name(QueueName=queue)
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    if expected_msg is not None:
        msg = messages[0].body
        msg = json.loads(msg)
        assert msg["Message"] == SESFeedback.generate_message(expected_msg)
    else:
        assert len(messages) == 0


@mock_sqs
@mock_sns
@mock_ses
def test_no_sns_feedback():
    __test_sns_feedback__("test", None)


@mock_sqs
@mock_sns
@mock_ses
def test_sns_feedback_bounce():
    __test_sns_feedback__(SESFeedback.BOUNCE_ADDR, SESFeedback.BOUNCE)


@mock_sqs
@mock_sns
@mock_ses
def test_sns_feedback_complaint():
    __test_sns_feedback__(SESFeedback.COMPLAINT_ADDR, SESFeedback.COMPLAINT)


@mock_sqs
@mock_sns
@mock_ses
def test_sns_feedback_delivery():
    __test_sns_feedback__(SESFeedback.SUCCESS_ADDR, SESFeedback.DELIVERY)


@mock_sqs
@mock_sns
@mock_ses
def test_sns_feedback_delivery_raw_email():
    __test_sns_feedback__(
        SESFeedback.SUCCESS_ADDR, SESFeedback.DELIVERY, raw_email=True
    )
