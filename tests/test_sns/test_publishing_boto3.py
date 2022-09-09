import base64
import json

import boto3
import re
from freezegun import freeze_time
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from unittest import SkipTest
import pytest
from moto import mock_sns, mock_sqs, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core.models import responses_mock
from moto.sns import sns_backends

MESSAGE_FROM_SQS_TEMPLATE = (
    '{\n  "Message": "%s",\n  "MessageId": "%s",\n  "Signature": "EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc=",\n  "SignatureVersion": "1",\n  "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem",\n  "Subject": "my subject",\n  "Timestamp": "2015-01-01T12:00:00.000Z",\n  "TopicArn": "arn:aws:sns:%s:'
    + ACCOUNT_ID
    + ':some-topic",\n  "Type": "Notification",\n  "UnsubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:'
    + ACCOUNT_ID
    + ':some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55"\n}'
)


@mock_sqs
@mock_sns
def test_publish_to_sqs():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    sqs_conn = boto3.resource("sqs", region_name="us-east-1")
    sqs_conn.create_queue(QueueName="test-queue")

    conn.subscribe(
        TopicArn=topic_arn,
        Protocol="sqs",
        Endpoint="arn:aws:sqs:us-east-1:{}:test-queue".format(ACCOUNT_ID),
    )
    message = "my message"
    with freeze_time("2015-01-01 12:00:00"):
        published_message = conn.publish(
            TopicArn=topic_arn, Message=message, Subject="my subject"
        )
    published_message_id = published_message["MessageId"]

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    with freeze_time("2015-01-01 12:00:01"):
        messages = queue.receive_messages(MaxNumberOfMessages=1)
    expected = MESSAGE_FROM_SQS_TEMPLATE % (message, published_message_id, "us-east-1")
    acquired_message = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z",
        "2015-01-01T12:00:00.000Z",
        messages[0].body,
    )
    acquired_message.should.equal(expected)


@mock_sqs
@mock_sns
def test_publish_to_sqs_raw():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="some-topic")

    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-queue")

    subscription = topic.subscribe(
        Protocol="sqs", Endpoint=queue.attributes["QueueArn"]
    )

    subscription.set_attributes(
        AttributeName="RawMessageDelivery", AttributeValue="true"
    )

    message = "my message"
    with freeze_time("2015-01-01 12:00:00"):
        topic.publish(Message=message)

    with freeze_time("2015-01-01 12:00:01"):
        messages = queue.receive_messages(MaxNumberOfMessages=1)
    messages[0].body.should.equal(message)


@mock_sns
@mock_sqs
def test_publish_to_sqs_fifo():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(
        Name="topic.fifo",
        Attributes={"FifoTopic": "true", "ContentBasedDeduplication": "true"},
    )

    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName="queue.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )
    topic.subscribe(Protocol="sqs", Endpoint=queue.attributes["QueueArn"])

    topic.publish(Message="message", MessageGroupId="message_group_id")


@mock_sqs
@mock_sns
def test_publish_to_sqs_bad():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    sqs_conn = boto3.resource("sqs", region_name="us-east-1")
    sqs_conn.create_queue(QueueName="test-queue")

    conn.subscribe(
        TopicArn=topic_arn,
        Protocol="sqs",
        Endpoint="arn:aws:sqs:us-east-1:{}:test-queue".format(ACCOUNT_ID),
    )
    message = "my message"
    try:
        # Test missing Value
        conn.publish(
            TopicArn=topic_arn,
            Message=message,
            MessageAttributes={"store": {"DataType": "String"}},
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidParameterValue")
    try:
        # Test empty DataType (if the DataType field is missing entirely
        # botocore throws an exception during validation)
        conn.publish(
            TopicArn=topic_arn,
            Message=message,
            MessageAttributes={
                "store": {"DataType": "", "StringValue": "example_corp"}
            },
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidParameterValue")
    try:
        # Test empty Value
        conn.publish(
            TopicArn=topic_arn,
            Message=message,
            MessageAttributes={"store": {"DataType": "String", "StringValue": ""}},
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidParameterValue")
    try:
        # Test Number DataType, with a non numeric value
        conn.publish(
            TopicArn=topic_arn,
            Message=message,
            MessageAttributes={"price": {"DataType": "Number", "StringValue": "error"}},
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidParameterValue")
        err.response["Error"]["Message"].should.equal(
            "An error occurred (ParameterValueInvalid) when calling the Publish operation: Could not cast message attribute 'price' value to number."
        )


@mock_sqs
@mock_sns
def test_publish_to_sqs_msg_attr_byte_value():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-queue")
    conn.subscribe(
        TopicArn=topic_arn, Protocol="sqs", Endpoint=queue.attributes["QueueArn"]
    )
    queue_raw = sqs.create_queue(QueueName="test-queue-raw")
    conn.subscribe(
        TopicArn=topic_arn,
        Protocol="sqs",
        Endpoint=queue_raw.attributes["QueueArn"],
        Attributes={"RawMessageDelivery": "true"},
    )

    conn.publish(
        TopicArn=topic_arn,
        Message="my message",
        MessageAttributes={
            "store": {"DataType": "Binary", "BinaryValue": b"\x02\x03\x04"}
        },
    )

    message = json.loads(queue.receive_messages()[0].body)
    message["Message"].should.equal("my message")
    message["MessageAttributes"].should.equal(
        {
            "store": {
                "Type": "Binary",
                "Value": base64.b64encode(b"\x02\x03\x04").decode(),
            }
        }
    )

    message = queue_raw.receive_messages()[0]
    message.body.should.equal("my message")


@mock_sqs
@mock_sns
def test_publish_to_sqs_msg_attr_number_type():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="test-topic")
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-queue")
    topic.subscribe(Protocol="sqs", Endpoint=queue.attributes["QueueArn"])
    queue_raw = sqs.create_queue(QueueName="test-queue-raw")
    topic.subscribe(
        Protocol="sqs",
        Endpoint=queue_raw.attributes["QueueArn"],
        Attributes={"RawMessageDelivery": "true"},
    )

    topic.publish(
        Message="test message",
        MessageAttributes={"retries": {"DataType": "Number", "StringValue": "0"}},
    )

    message = json.loads(queue.receive_messages()[0].body)
    message["Message"].should.equal("test message")
    message["MessageAttributes"].should.equal(
        {"retries": {"Type": "Number", "Value": 0}}
    )

    message = queue_raw.receive_messages()[0]
    message.body.should.equal("test message")


@mock_sqs
@mock_sns
def test_publish_to_sqs_msg_attr_different_formats():
    """
    Verify different Number-formats are processed correctly
    """
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="test-topic")
    sqs = boto3.resource("sqs", region_name="us-east-1")
    sqs_client = boto3.client("sqs", region_name="us-east-1")
    queue_raw = sqs.create_queue(QueueName="test-queue-raw")

    topic.subscribe(
        Protocol="sqs",
        Endpoint=queue_raw.attributes["QueueArn"],
        Attributes={"RawMessageDelivery": "true"},
    )

    topic.publish(
        Message="test message",
        MessageAttributes={
            "integer": {"DataType": "Number", "StringValue": "123"},
            "float": {"DataType": "Number", "StringValue": "12.34"},
            "big-integer": {"DataType": "Number", "StringValue": "123456789"},
            "big-float": {"DataType": "Number", "StringValue": "123456.789"},
        },
    )

    messages_resp = sqs_client.receive_message(
        QueueUrl=queue_raw.url, MessageAttributeNames=["All"]
    )
    message = messages_resp["Messages"][0]
    message_attributes = message["MessageAttributes"]
    message_attributes.should.equal(
        {
            "integer": {"DataType": "Number", "StringValue": "123"},
            "float": {"DataType": "Number", "StringValue": "12.34"},
            "big-integer": {"DataType": "Number", "StringValue": "123456789"},
            "big-float": {"DataType": "Number", "StringValue": "123456.789"},
        }
    )


@mock_sns
def test_publish_sms():
    client = boto3.client("sns", region_name="us-east-1")

    result = client.publish(PhoneNumber="+15551234567", Message="my message")

    result.should.contain("MessageId")
    if not settings.TEST_SERVER_MODE:
        sns_backend = sns_backends[ACCOUNT_ID]["us-east-1"]
        sns_backend.sms_messages.should.have.key(result["MessageId"]).being.equal(
            ("+15551234567", "my message")
        )


@mock_sns
def test_publish_bad_sms():
    client = boto3.client("sns", region_name="us-east-1")

    # Test invalid number
    with pytest.raises(ClientError) as cm:
        client.publish(PhoneNumber="NAA+15551234567", Message="my message")
    cm.value.response["Error"]["Code"].should.equal("InvalidParameter")
    cm.value.response["Error"]["Message"].should.contain("not meet the E164")

    # Test to long ASCII message
    with pytest.raises(ClientError) as cm:
        client.publish(PhoneNumber="+15551234567", Message="a" * 1601)
    cm.value.response["Error"]["Code"].should.equal("InvalidParameter")
    cm.value.response["Error"]["Message"].should.contain("must be less than 1600")


@mock_sqs
@mock_sns
def test_publish_to_sqs_dump_json():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    sqs_conn = boto3.resource("sqs", region_name="us-east-1")
    sqs_conn.create_queue(QueueName="test-queue")

    conn.subscribe(
        TopicArn=topic_arn,
        Protocol="sqs",
        Endpoint="arn:aws:sqs:us-east-1:{}:test-queue".format(ACCOUNT_ID),
    )

    message = json.dumps(
        {
            "Records": [
                {
                    "eventVersion": "2.0",
                    "eventSource": "aws:s3",
                    "s3": {"s3SchemaVersion": "1.0"},
                }
            ]
        },
        sort_keys=True,
    )
    with freeze_time("2015-01-01 12:00:00"):
        published_message = conn.publish(
            TopicArn=topic_arn, Message=message, Subject="my subject"
        )
    published_message_id = published_message["MessageId"]

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    with freeze_time("2015-01-01 12:00:01"):
        messages = queue.receive_messages(MaxNumberOfMessages=1)

    escaped = message.replace('"', '\\"')
    expected = MESSAGE_FROM_SQS_TEMPLATE % (escaped, published_message_id, "us-east-1")
    acquired_message = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z",
        "2015-01-01T12:00:00.000Z",
        messages[0].body,
    )
    acquired_message.should.equal(expected)


@mock_sqs
@mock_sns
def test_publish_to_sqs_in_different_region():
    conn = boto3.client("sns", region_name="us-west-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    sqs_conn = boto3.resource("sqs", region_name="us-west-2")
    sqs_conn.create_queue(QueueName="test-queue")

    conn.subscribe(
        TopicArn=topic_arn,
        Protocol="sqs",
        Endpoint="arn:aws:sqs:us-west-2:{}:test-queue".format(ACCOUNT_ID),
    )

    message = "my message"
    with freeze_time("2015-01-01 12:00:00"):
        published_message = conn.publish(
            TopicArn=topic_arn, Message=message, Subject="my subject"
        )
    published_message_id = published_message["MessageId"]

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    with freeze_time("2015-01-01 12:00:01"):
        messages = queue.receive_messages(MaxNumberOfMessages=1)
    expected = MESSAGE_FROM_SQS_TEMPLATE % (message, published_message_id, "us-west-1")
    acquired_message = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z",
        "2015-01-01T12:00:00.000Z",
        messages[0].body,
    )
    acquired_message.should.equal(expected)


@freeze_time("2013-01-01")
@mock_sns
def test_publish_to_http():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't mock requests in ServerMode")

    def callback(request):
        request.headers["Content-Type"].should.equal("text/plain; charset=UTF-8")
        json.loads.when.called_with(request.body.decode()).should_not.throw(Exception)
        return 200, {}, ""

    responses_mock.add_callback(
        method="POST", url="http://example.com/foobar", callback=callback
    )

    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    conn.subscribe(
        TopicArn=topic_arn, Protocol="http", Endpoint="http://example.com/foobar"
    )

    conn.publish(TopicArn=topic_arn, Message="my message", Subject="my subject")

    sns_backend = sns_backends[ACCOUNT_ID]["us-east-1"]
    sns_backend.topics[topic_arn].sent_notifications.should.have.length_of(1)
    notification = sns_backend.topics[topic_arn].sent_notifications[0]
    _, msg, subject, _, _ = notification
    msg.should.equal("my message")
    subject.should.equal("my subject")


@mock_sqs
@mock_sns
def test_publish_subject():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    sqs_conn = boto3.resource("sqs", region_name="us-east-1")
    sqs_conn.create_queue(QueueName="test-queue")

    conn.subscribe(
        TopicArn=topic_arn,
        Protocol="sqs",
        Endpoint="arn:aws:sqs:us-east-1:{}:test-queue".format(ACCOUNT_ID),
    )
    message = "my message"
    subject1 = "test subject"
    subject2 = "test subject" * 20
    with freeze_time("2015-01-01 12:00:00"):
        conn.publish(TopicArn=topic_arn, Message=message, Subject=subject1)

    # Just that it doesnt error is a pass
    try:
        with freeze_time("2015-01-01 12:00:00"):
            conn.publish(TopicArn=topic_arn, Message=message, Subject=subject2)
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidParameter")
    else:
        raise RuntimeError("Should have raised an InvalidParameter exception")


@mock_sqs
@mock_sns
def test_publish_null_subject():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    sqs_conn = boto3.resource("sqs", region_name="us-east-1")
    sqs_conn.create_queue(QueueName="test-queue")

    conn.subscribe(
        TopicArn=topic_arn,
        Protocol="sqs",
        Endpoint="arn:aws:sqs:us-east-1:{}:test-queue".format(ACCOUNT_ID),
    )
    message = "my message"
    with freeze_time("2015-01-01 12:00:00"):
        conn.publish(TopicArn=topic_arn, Message=message)

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    with freeze_time("2015-01-01 12:00:01"):
        messages = queue.receive_messages(MaxNumberOfMessages=1)

    acquired_message = json.loads(messages[0].body)
    acquired_message["Message"].should.equal(message)
    acquired_message.shouldnt.have.key("Subject")


@mock_sns
def test_publish_message_too_long():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="some-topic")

    with pytest.raises(ClientError):
        topic.publish(Message="".join(["." for i in range(0, 262145)]))

    # message short enough - does not raise an error
    topic.publish(Message="".join(["." for i in range(0, 262144)]))


@mock_sns
def test_publish_fifo_needs_group_id():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(
        Name="topic.fifo",
        Attributes={"FifoTopic": "true", "ContentBasedDeduplication": "true"},
    )

    with pytest.raises(
        ClientError, match="The request must contain the parameter MessageGroupId"
    ):
        topic.publish(Message="message")

    # message group included - OK
    topic.publish(Message="message", MessageGroupId="message_group_id")


@mock_sns
@mock_sqs
def test_publish_group_id_to_non_fifo():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="topic")

    with pytest.raises(
        ClientError,
        match="The request include parameter that is not valid for this queue type",
    ):
        topic.publish(Message="message", MessageGroupId="message_group_id")

    # message group not included - OK
    topic.publish(Message="message")


def _setup_filter_policy_test(filter_policy):
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="some-topic")

    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-queue")

    subscription = topic.subscribe(
        Protocol="sqs", Endpoint=queue.attributes["QueueArn"]
    )

    subscription.set_attributes(
        AttributeName="FilterPolicy", AttributeValue=json.dumps(filter_policy)
    )

    return topic, queue


@mock_sqs
@mock_sns
def test_filtering_exact_string():
    topic, queue = _setup_filter_policy_test({"store": ["example_corp"]})

    topic.publish(
        Message="match",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "example_corp"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [{"store": {"Type": "String", "Value": "example_corp"}}]
    )


@mock_sqs
@mock_sns
def test_filtering_exact_string_multiple_message_attributes():
    topic, queue = _setup_filter_policy_test({"store": ["example_corp"]})

    topic.publish(
        Message="match",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "example_corp"},
            "event": {"DataType": "String", "StringValue": "order_cancelled"},
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [
            {
                "store": {"Type": "String", "Value": "example_corp"},
                "event": {"Type": "String", "Value": "order_cancelled"},
            }
        ]
    )


@mock_sqs
@mock_sns
def test_filtering_exact_string_OR_matching():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp", "different_corp"]}
    )

    topic.publish(
        Message="match example_corp",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "example_corp"}
        },
    )
    topic.publish(
        Message="match different_corp",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "different_corp"}
        },
    )
    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match example_corp", "match different_corp"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [
            {"store": {"Type": "String", "Value": "example_corp"}},
            {"store": {"Type": "String", "Value": "different_corp"}},
        ]
    )


@mock_sqs
@mock_sns
def test_filtering_exact_string_AND_matching_positive():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp"], "event": ["order_cancelled"]}
    )

    topic.publish(
        Message="match example_corp order_cancelled",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "example_corp"},
            "event": {"DataType": "String", "StringValue": "order_cancelled"},
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match example_corp order_cancelled"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [
            {
                "store": {"Type": "String", "Value": "example_corp"},
                "event": {"Type": "String", "Value": "order_cancelled"},
            }
        ]
    )


@mock_sqs
@mock_sns
def test_filtering_exact_string_AND_matching_no_match():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp"], "event": ["order_cancelled"]}
    )

    topic.publish(
        Message="match example_corp order_accepted",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "example_corp"},
            "event": {"DataType": "String", "StringValue": "order_accepted"},
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_exact_string_no_match():
    topic, queue = _setup_filter_policy_test({"store": ["example_corp"]})

    topic.publish(
        Message="no match",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "different_corp"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_exact_string_no_attributes_no_match():
    topic, queue = _setup_filter_policy_test({"store": ["example_corp"]})

    topic.publish(Message="no match")

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_exact_number_int():
    topic, queue = _setup_filter_policy_test({"price": [100]})

    topic.publish(
        Message="match",
        MessageAttributes={"price": {"DataType": "Number", "StringValue": "100"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([{"price": {"Type": "Number", "Value": 100}}])


@mock_sqs
@mock_sns
def test_filtering_exact_number_float():
    topic, queue = _setup_filter_policy_test({"price": [100.1]})

    topic.publish(
        Message="match",
        MessageAttributes={"price": {"DataType": "Number", "StringValue": "100.1"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([{"price": {"Type": "Number", "Value": 100.1}}])


@mock_sqs
@mock_sns
def test_filtering_exact_number_float_accuracy():
    topic, queue = _setup_filter_policy_test({"price": [100.123456789]})

    topic.publish(
        Message="match",
        MessageAttributes={
            "price": {"DataType": "Number", "StringValue": "100.1234561"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [{"price": {"Type": "Number", "Value": 100.1234561}}]
    )


@mock_sqs
@mock_sns
def test_filtering_exact_number_no_match():
    topic, queue = _setup_filter_policy_test({"price": [100]})

    topic.publish(
        Message="no match",
        MessageAttributes={"price": {"DataType": "Number", "StringValue": "101"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_exact_number_with_string_no_match():
    topic, queue = _setup_filter_policy_test({"price": [100]})

    topic.publish(
        Message="no match",
        MessageAttributes={"price": {"DataType": "String", "StringValue": "100"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_string_array_match():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": ["basketball", "baseball"]}
    )

    topic.publish(
        Message="match",
        MessageAttributes={
            "customer_interests": {
                "DataType": "String.Array",
                "StringValue": json.dumps(["basketball", "rugby"]),
            }
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [
            {
                "customer_interests": {
                    "Type": "String.Array",
                    "Value": json.dumps(["basketball", "rugby"]),
                }
            }
        ]
    )


@mock_sqs
@mock_sns
def test_filtering_string_array_no_match():
    topic, queue = _setup_filter_policy_test({"customer_interests": ["baseball"]})

    topic.publish(
        Message="no_match",
        MessageAttributes={
            "customer_interests": {
                "DataType": "String.Array",
                "StringValue": json.dumps(["basketball", "rugby"]),
            }
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_string_array_with_number_match():
    topic, queue = _setup_filter_policy_test({"price": [100, 500]})

    topic.publish(
        Message="match",
        MessageAttributes={
            "price": {"DataType": "String.Array", "StringValue": json.dumps([100, 50])}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [{"price": {"Type": "String.Array", "Value": json.dumps([100, 50])}}]
    )


@mock_sqs
@mock_sns
def test_filtering_string_array_with_number_float_accuracy_match():
    topic, queue = _setup_filter_policy_test({"price": [100.123456789, 500]})

    topic.publish(
        Message="match",
        MessageAttributes={
            "price": {
                "DataType": "String.Array",
                "StringValue": json.dumps([100.1234561, 50]),
            }
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [{"price": {"Type": "String.Array", "Value": json.dumps([100.1234561, 50])}}]
    )


@mock_sqs
@mock_sns
# this is the correct behavior from SNS
def test_filtering_string_array_with_number_no_array_match():
    topic, queue = _setup_filter_policy_test({"price": [100, 500]})

    topic.publish(
        Message="match",
        MessageAttributes={"price": {"DataType": "String.Array", "StringValue": "100"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [{"price": {"Type": "String.Array", "Value": "100"}}]
    )


@mock_sqs
@mock_sns
def test_filtering_string_array_with_number_no_match():
    topic, queue = _setup_filter_policy_test({"price": [500]})

    topic.publish(
        Message="no_match",
        MessageAttributes={
            "price": {"DataType": "String.Array", "StringValue": json.dumps([100, 50])}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
# this is the correct behavior from SNS
def test_filtering_string_array_with_string_no_array_no_match():
    topic, queue = _setup_filter_policy_test({"price": [100]})

    topic.publish(
        Message="no_match",
        MessageAttributes={
            "price": {"DataType": "String.Array", "StringValue": "one hundred"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_attribute_key_exists_match():
    topic, queue = _setup_filter_policy_test({"store": [{"exists": True}]})

    topic.publish(
        Message="match",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "example_corp"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [{"store": {"Type": "String", "Value": "example_corp"}}]
    )


@mock_sqs
@mock_sns
def test_filtering_attribute_key_exists_no_match():
    topic, queue = _setup_filter_policy_test({"store": [{"exists": True}]})

    topic.publish(
        Message="no match",
        MessageAttributes={
            "event": {"DataType": "String", "StringValue": "order_cancelled"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_attribute_key_not_exists_match():
    topic, queue = _setup_filter_policy_test({"store": [{"exists": False}]})

    topic.publish(
        Message="match",
        MessageAttributes={
            "event": {"DataType": "String", "StringValue": "order_cancelled"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [{"event": {"Type": "String", "Value": "order_cancelled"}}]
    )


@mock_sqs
@mock_sns
def test_filtering_attribute_key_not_exists_no_match():
    topic, queue = _setup_filter_policy_test({"store": [{"exists": False}]})

    topic.publish(
        Message="no match",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "example_corp"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_all_AND_matching_match():
    topic, queue = _setup_filter_policy_test(
        {
            "store": [{"exists": True}],
            "event": ["order_cancelled"],
            "customer_interests": ["basketball", "baseball"],
            "price": [100],
        }
    )

    topic.publish(
        Message="match",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "example_corp"},
            "event": {"DataType": "String", "StringValue": "order_cancelled"},
            "customer_interests": {
                "DataType": "String.Array",
                "StringValue": json.dumps(["basketball", "rugby"]),
            },
            "price": {"DataType": "Number", "StringValue": "100"},
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal(["match"])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal(
        [
            {
                "store": {"Type": "String", "Value": "example_corp"},
                "event": {"Type": "String", "Value": "order_cancelled"},
                "customer_interests": {
                    "Type": "String.Array",
                    "Value": json.dumps(["basketball", "rugby"]),
                },
                "price": {"Type": "Number", "Value": 100},
            }
        ]
    )


@mock_sqs
@mock_sns
def test_filtering_all_AND_matching_no_match():
    topic, queue = _setup_filter_policy_test(
        {
            "store": [{"exists": True}],
            "event": ["order_cancelled"],
            "customer_interests": ["basketball", "baseball"],
            "price": [100],
            "encrypted": [False],
        }
    )

    topic.publish(
        Message="no match",
        MessageAttributes={
            "store": {"DataType": "String", "StringValue": "example_corp"},
            "event": {"DataType": "String", "StringValue": "order_cancelled"},
            "customer_interests": {
                "DataType": "String.Array",
                "StringValue": json.dumps(["basketball", "rugby"]),
            },
            "price": {"DataType": "Number", "StringValue": "100"},
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    message_attributes.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_prefix():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"prefix": "bas"}]}
    )

    for interest, idx in [("basketball", "1"), ("rugby", "2"), ("baseball", "3")]:
        topic.publish(
            Message=f"match{idx}",
            MessageAttributes={
                "customer_interests": {"DataType": "String", "StringValue": interest},
            },
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    set(message_bodies).should.equal({"match1", "match3"})


@mock_sqs
@mock_sns
def test_filtering_anything_but():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"anything-but": "basketball"}]}
    )

    for interest, idx in [("basketball", "1"), ("rugby", "2"), ("baseball", "3")]:
        topic.publish(
            Message=f"match{idx}",
            MessageAttributes={
                "customer_interests": {"DataType": "String", "StringValue": interest},
            },
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    set(message_bodies).should.equal({"match2", "match3"})


@mock_sqs
@mock_sns
def test_filtering_anything_but_multiple_values():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"anything-but": ["basketball", "rugby"]}]}
    )

    for interest, idx in [("basketball", "1"), ("rugby", "2"), ("baseball", "3")]:
        topic.publish(
            Message=f"match{idx}",
            MessageAttributes={
                "customer_interests": {"DataType": "String", "StringValue": interest},
            },
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    set(message_bodies).should.equal({"match3"})


@mock_sqs
@mock_sns
def test_filtering_anything_but_prefix():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"anything-but": {"prefix": "bas"}}]}
    )

    for interest, idx in [("basketball", "1"), ("rugby", "2"), ("baseball", "3")]:
        topic.publish(
            Message=f"match{idx}",
            MessageAttributes={
                "customer_interests": {"DataType": "String", "StringValue": interest},
            },
        )

    # This should match rugby only
    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    set(message_bodies).should.equal({"match2"})


@mock_sqs
@mock_sns
def test_filtering_anything_but_unknown():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"anything-but": {"unknown": "bas"}}]}
    )

    for interest, idx in [("basketball", "1"), ("rugby", "2"), ("baseball", "3")]:
        topic.publish(
            Message=f"match{idx}",
            MessageAttributes={
                "customer_interests": {"DataType": "String", "StringValue": interest},
            },
        )

    # This should match rugby only
    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    message_bodies.should.equal([])


@mock_sqs
@mock_sns
def test_filtering_anything_but_numeric():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"anything-but": ["100"]}]}
    )

    for nr, idx in [("50", "1"), ("100", "2"), ("150", "3")]:
        topic.publish(
            Message=f"match{idx}",
            MessageAttributes={
                "customer_interests": {"DataType": "Number", "StringValue": nr},
            },
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    set(message_bodies).should.equal({"match1", "match3"})


@mock_sqs
@mock_sns
def test_filtering_numeric_match():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"numeric": ["=", "100"]}]}
    )

    for nr, idx in [("50", "1"), ("100", "2"), ("150", "3")]:
        topic.publish(
            Message=f"match{idx}",
            MessageAttributes={
                "customer_interests": {"DataType": "Number", "StringValue": nr},
            },
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    set(message_bodies).should.equal({"match2"})


@mock_sqs
@mock_sns
def test_filtering_numeric_range():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"numeric": [">", "49", "<=", "100"]}]}
    )

    for nr, idx in [("50", "1"), ("100", "2"), ("150", "3")]:
        topic.publish(
            Message=f"match{idx}",
            MessageAttributes={
                "customer_interests": {"DataType": "Number", "StringValue": nr},
            },
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    set(message_bodies).should.equal({"match1", "match2"})
