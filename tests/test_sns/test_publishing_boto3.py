import base64
import json
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core.models import responses_mock
from moto.sns import sns_backends


def to_comparable_dicts(list_entry: list):
    if list_entry:
        if isinstance(list_entry[0], dict):
            return set(map(json.dumps, list_entry))

    return set(list_entry)


@mock_aws
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
        Endpoint=f"arn:aws:sqs:us-east-1:{ACCOUNT_ID}:test-queue",
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
    acquired_message = json.loads(messages[0].body)

    assert acquired_message["Message"] == "my message"
    assert acquired_message["MessageId"] == published_message_id
    assert acquired_message["TopicArn"] == topic_arn
    assert acquired_message["SigningCertURL"]
    assert acquired_message["Subject"] == "my subject"


@mock_aws
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
    assert messages[0].body == message


@mock_aws
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


@mock_aws
def test_publish_to_sqs_fifo_with_deduplication_id():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(
        Name="topic.fifo",
        Attributes={"FifoTopic": "true"},
    )

    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName="queue.fifo",
        Attributes={"FifoQueue": "true"},
    )

    topic.subscribe(
        Protocol="sqs",
        Endpoint=queue.attributes["QueueArn"],
        Attributes={"RawMessageDelivery": "true"},
    )

    message = '{"msg": "hello"}'
    with freeze_time("2015-01-01 12:00:00"):
        topic.publish(
            Message=message,
            MessageGroupId="message_group_id",
            MessageDeduplicationId="message_deduplication_id",
        )

    with freeze_time("2015-01-01 12:00:01"):
        messages = queue.receive_messages(
            MaxNumberOfMessages=1,
            AttributeNames=["MessageDeduplicationId", "MessageGroupId"],
        )
    assert messages[0].attributes["MessageGroupId"] == "message_group_id"
    assert (
        messages[0].attributes["MessageDeduplicationId"] == "message_deduplication_id"
    )


@mock_aws
def test_publish_to_sqs_fifo_raw_with_deduplication_id():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(
        Name="topic.fifo",
        Attributes={"FifoTopic": "true"},
    )

    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(
        QueueName="queue.fifo",
        Attributes={"FifoQueue": "true"},
    )

    subscription = topic.subscribe(
        Protocol="sqs", Endpoint=queue.attributes["QueueArn"]
    )
    subscription.set_attributes(
        AttributeName="RawMessageDelivery", AttributeValue="true"
    )

    message = "my message"
    with freeze_time("2015-01-01 12:00:00"):
        topic.publish(
            Message=message,
            MessageGroupId="message_group_id",
            MessageDeduplicationId="message_deduplication_id",
        )

    with freeze_time("2015-01-01 12:00:01"):
        messages = queue.receive_messages(
            MaxNumberOfMessages=1,
            AttributeNames=["MessageDeduplicationId", "MessageGroupId"],
        )
    assert messages[0].attributes["MessageGroupId"] == "message_group_id"
    assert (
        messages[0].attributes["MessageDeduplicationId"] == "message_deduplication_id"
    )


@mock_aws
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
        Endpoint=f"arn:aws:sqs:us-east-1:{ACCOUNT_ID}:test-queue",
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
        assert err.response["Error"]["Code"] == "InvalidParameterValue"
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
        assert err.response["Error"]["Code"] == "InvalidParameterValue"
    try:
        # Test empty Value
        conn.publish(
            TopicArn=topic_arn,
            Message=message,
            MessageAttributes={"store": {"DataType": "String", "StringValue": ""}},
        )
    except ClientError as err:
        assert err.response["Error"]["Code"] == "InvalidParameterValue"
    try:
        # Test Number DataType, with a non numeric value
        conn.publish(
            TopicArn=topic_arn,
            Message=message,
            MessageAttributes={"price": {"DataType": "Number", "StringValue": "error"}},
        )
    except ClientError as err:
        assert err.response["Error"]["Code"] == "InvalidParameterValue"
        assert err.response["Error"]["Message"] == (
            "An error occurred (ParameterValueInvalid) when calling the "
            "Publish operation: Could not cast message attribute 'price' "
            "value to number."
        )


@mock_aws
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
    assert message["Message"] == "my message"
    assert message["MessageAttributes"] == {
        "store": {
            "Type": "Binary",
            "Value": base64.b64encode(b"\x02\x03\x04").decode(),
        }
    }

    message = queue_raw.receive_messages()[0]
    assert message.body == "my message"


@mock_aws
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
    assert message["Message"] == "test message"
    assert message["MessageAttributes"] == {"retries": {"Type": "Number", "Value": "0"}}

    message = queue_raw.receive_messages()[0]
    assert message.body == "test message"


@mock_aws
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
    assert message_attributes == {
        "integer": {"DataType": "Number", "StringValue": "123"},
        "float": {"DataType": "Number", "StringValue": "12.34"},
        "big-integer": {"DataType": "Number", "StringValue": "123456789"},
        "big-float": {"DataType": "Number", "StringValue": "123456.789"},
    }


@mock_aws
def test_publish_sms():
    client = boto3.client("sns", region_name="us-east-1")

    result = client.publish(PhoneNumber="+15551234567", Message="my message")

    assert "MessageId" in result
    if not settings.TEST_SERVER_MODE:
        sns_backend = sns_backends[ACCOUNT_ID]["us-east-1"]
        assert sns_backend.sms_messages[result["MessageId"]] == (
            "+15551234567",
            "my message",
        )


@mock_aws
def test_publish_bad_sms():
    client = boto3.client("sns", region_name="us-east-1")

    # Test invalid number
    with pytest.raises(ClientError) as client_err:
        client.publish(PhoneNumber="NAA+15551234567", Message="my message")
    assert client_err.value.response["Error"]["Code"] == "InvalidParameter"
    assert "not meet the E164" in client_err.value.response["Error"]["Message"]

    # Test to long ASCII message
    with pytest.raises(ClientError) as client_err:
        client.publish(PhoneNumber="+15551234567", Message="a" * 1601)
    assert client_err.value.response["Error"]["Code"] == "InvalidParameter"
    assert "must be less than 1600" in client_err.value.response["Error"]["Message"]


@mock_aws
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
        Endpoint=f"arn:aws:sqs:us-east-1:{ACCOUNT_ID}:test-queue",
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

    acquired_message = json.loads(messages[0].body)
    assert json.loads(acquired_message["Message"]) == json.loads(message)
    assert acquired_message["MessageId"] == published_message_id
    assert acquired_message["TopicArn"] == topic_arn
    assert acquired_message["SigningCertURL"]
    assert acquired_message["Subject"] == "my subject"


@mock_aws
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
        Endpoint=f"arn:aws:sqs:us-west-2:{ACCOUNT_ID}:test-queue",
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

    acquired_message = json.loads(messages[0].body)
    assert acquired_message["MessageId"] == published_message_id
    assert acquired_message["Message"] == "my message"
    assert acquired_message["TopicArn"] == topic_arn
    assert acquired_message["SigningCertURL"]
    assert acquired_message["Subject"] == "my subject"


@freeze_time("2013-01-01")
@mock_aws
def test_publish_to_http():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't mock requests in ServerMode")

    def callback(request):
        assert request.headers["Content-Type"] == "text/plain; charset=UTF-8"
        try:
            json.loads(request.body.decode())
        except Exception:
            assert False, "json.load() raised an exception"
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
    assert len(sns_backend.topics[topic_arn].sent_notifications) == 1
    notification = sns_backend.topics[topic_arn].sent_notifications[0]
    _, msg, subject, _, _ = notification
    assert msg == "my message"
    assert subject == "my subject"


@mock_aws
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
        Endpoint=f"arn:aws:sqs:us-east-1:{ACCOUNT_ID}:test-queue",
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
        assert err.response["Error"]["Code"] == "InvalidParameter"
    else:
        raise RuntimeError("Should have raised an InvalidParameter exception")


@mock_aws
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
        Endpoint=f"arn:aws:sqs:us-east-1:{ACCOUNT_ID}:test-queue",
    )
    message = "my message"
    with freeze_time("2015-01-01 12:00:00"):
        conn.publish(TopicArn=topic_arn, Message=message)

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    with freeze_time("2015-01-01 12:00:01"):
        messages = queue.receive_messages(MaxNumberOfMessages=1)

    acquired_message = json.loads(messages[0].body)
    assert acquired_message["Message"] == message
    assert "Subject" not in acquired_message


@mock_aws
def test_publish_message_too_long():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="some-topic")

    with pytest.raises(ClientError):
        topic.publish(Message="".join(["." for i in range(0, 262145)]))

    # message short enough - does not raise an error
    topic.publish(Message="".join(["." for i in range(0, 262144)]))


@mock_aws
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


@mock_aws
def test_publish_group_id_to_non_fifo():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="topic")

    with pytest.raises(
        ClientError,
        match="The request includes MessageGroupId parameter that is not valid for this topic type",
    ):
        topic.publish(Message="message", MessageGroupId="message_group_id")

    # message group not included - OK
    topic.publish(Message="message")


@mock_aws
def test_publish_fifo_needs_deduplication_id():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(
        Name="topic.fifo",
        Attributes={"FifoTopic": "true"},
    )

    with pytest.raises(
        ClientError,
        match=(
            "The topic should either have ContentBasedDeduplication "
            "enabled or MessageDeduplicationId provided explicitly"
        ),
    ):
        topic.publish(Message="message", MessageGroupId="message_group_id")

    # message deduplication id included - OK
    topic.publish(
        Message="message",
        MessageGroupId="message_group_id",
        MessageDeduplicationId="message_deduplication_id",
    )


@mock_aws
def test_publish_deduplication_id_to_non_fifo():
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="topic")

    with pytest.raises(
        ClientError,
        match=(
            "The request includes MessageDeduplicationId parameter that "
            "is not valid for this topic type"
        ),
    ):
        topic.publish(
            Message="message", MessageDeduplicationId="message_deduplication_id"
        )

    # message group not included - OK
    topic.publish(Message="message")


def _setup_filter_policy_test(
    filter_policy: dict, filter_policy_scope: str = "MessageAttributes"
):
    sns = boto3.resource("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="some-topic")

    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-queue")

    subscription = topic.subscribe(
        Protocol="sqs", Endpoint=queue.attributes["QueueArn"]
    )

    subscription.set_attributes(
        AttributeName="FilterPolicyScope", AttributeValue=filter_policy_scope
    )

    subscription.set_attributes(
        AttributeName="FilterPolicy", AttributeValue=json.dumps(filter_policy)
    )

    return topic, queue


@mock_aws
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
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {"store": {"Type": "String", "Value": "example_corp"}}
    ]


@mock_aws
def test_filtering_exact_string_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp"]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"store": "example_corp"}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"result": {"Type": "String", "Value": "match"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"store": "example_corp"}]


@mock_aws
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
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "store": {"Type": "String", "Value": "example_corp"},
            "event": {"Type": "String", "Value": "order_cancelled"},
        }
    ]


@mock_aws
def test_filtering_exact_string_multiple_message_attributes_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp"]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"store": "example_corp", "event": "order_cancelled"}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"result": {"Type": "String", "Value": "match"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"store": "example_corp", "event": "order_cancelled"}]


@mock_aws
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
    assert message_bodies == ["match example_corp", "match different_corp"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {"store": {"Type": "String", "Value": "example_corp"}},
        {"store": {"Type": "String", "Value": "different_corp"}},
    ]


@mock_aws
def test_filtering_exact_string_OR_matching_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp", "different_corp"]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"store": "example_corp"}),
        MessageAttributes={
            "result": {"DataType": "String", "StringValue": "match example_corp"}
        },
    )

    topic.publish(
        Message=json.dumps({"store": "different_corp"}),
        MessageAttributes={
            "result": {"DataType": "String", "StringValue": "match different_corp"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert to_comparable_dicts(message_attributes) == to_comparable_dicts(
        [
            {"result": {"Type": "String", "Value": "match example_corp"}},
            {"result": {"Type": "String", "Value": "match different_corp"}},
        ]
    )
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"store": "example_corp"}, {"store": "different_corp"}]
    )


@mock_aws
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
    assert message_bodies == ["match example_corp order_cancelled"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "store": {"Type": "String", "Value": "example_corp"},
            "event": {"Type": "String", "Value": "order_cancelled"},
        }
    ]


@mock_aws
def test_filtering_exact_string_AND_matching_positive_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp"], "event": ["order_cancelled"]},
        filter_policy_scope="MessageBody",
    )

    topic.publish(
        Message=json.dumps({"store": "example_corp", "event": "order_cancelled"}),
        MessageAttributes={
            "result": {
                "DataType": "String",
                "StringValue": "match example_corp order_cancelled",
            }
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "result": {
                "Type": "String",
                "Value": "match example_corp order_cancelled",
            },
        }
    ]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"store": "example_corp", "event": "order_cancelled"}]


@mock_aws
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
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_exact_string_AND_matching_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp"], "event": ["order_cancelled"]},
        filter_policy_scope="MessageBody",
    )

    topic.publish(
        Message=json.dumps({"store": "example_corp", "event": "order_accepted"}),
        MessageAttributes={
            "result": {
                "DataType": "String",
                "StringValue": "match example_corp order_accepted",
            }
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
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
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_exact_string_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp"]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"store": "different_corp"}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
def test_filtering_exact_string_no_attributes_no_match():
    topic, queue = _setup_filter_policy_test({"store": ["example_corp"]})

    topic.publish(Message="no match")

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_exact_string_empty_body_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp"]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
def test_filtering_exact_number_int():
    topic, queue = _setup_filter_policy_test({"price": [100]})

    topic.publish(
        Message="match",
        MessageAttributes={"price": {"DataType": "Number", "StringValue": "100"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"price": {"Type": "Number", "Value": "100"}}]


@mock_aws
def test_filtering_exact_number_int_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [100]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": 100}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "result": {"Type": "String", "Value": "match"},
        }
    ]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"price": 100}]


@mock_aws
def test_filtering_exact_number_float():
    topic, queue = _setup_filter_policy_test({"price": [100.1]})

    topic.publish(
        Message="match",
        MessageAttributes={"price": {"DataType": "Number", "StringValue": "100.1"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"price": {"Type": "Number", "Value": "100.1"}}]


@mock_aws
def test_filtering_exact_number_float_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [100.1]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": 100.1}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "result": {"Type": "String", "Value": "match"},
        }
    ]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"price": 100.1}]


@mock_aws
def test_filtering_exact_number_float_accuracy():
    topic, queue = _setup_filter_policy_test({"price": [100.123456789]})

    topic.publish(
        Message="match",
        MessageAttributes={
            "price": {"DataType": "Number", "StringValue": "100.1234567"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"price": {"Type": "Number", "Value": "100.1234567"}}]


@mock_aws
def test_filtering_exact_number_float_accuracy_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [100.123456789]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": 100.1234567}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "result": {"Type": "String", "Value": "match"},
        }
    ]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"price": 100.1234567}]


@mock_aws
def test_filtering_exact_number_no_match():
    topic, queue = _setup_filter_policy_test({"price": [100]})

    topic.publish(
        Message="no match",
        MessageAttributes={"price": {"DataType": "Number", "StringValue": "101"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_exact_number_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [100]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": 101}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
def test_filtering_exact_number_with_string_no_match():
    topic, queue = _setup_filter_policy_test({"price": [100]})

    topic.publish(
        Message="no match",
        MessageAttributes={"price": {"DataType": "String", "StringValue": "100"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_exact_number_with_string_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [100]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": "100"}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
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
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "customer_interests": {
                "Type": "String.Array",
                "Value": json.dumps(["basketball", "rugby"]),
            }
        }
    ]


@mock_aws
def test_filtering_string_array_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": ["basketball", "baseball"]},
        filter_policy_scope="MessageBody",
    )

    topic.publish(
        Message=json.dumps({"customer_interests": ["basketball", "rugby"]}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "result": {"Type": "String", "Value": "match"},
        }
    ]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"customer_interests": ["basketball", "rugby"]}]


@mock_aws
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
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_string_array_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": ["baseball"]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"customer_interests": ["basketball", "rugby"]}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no_match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
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
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {"price": {"Type": "String.Array", "Value": json.dumps([100, 50])}}
    ]


@mock_aws
def test_filtering_string_array_with_number_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [100, 500]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": [100, 50]}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "result": {"Type": "String", "Value": "match"},
        }
    ]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"price": [100, 50]}]


@mock_aws
def test_filtering_string_array_with_number_float_accuracy_match():
    topic, queue = _setup_filter_policy_test({"price": [100.123456789, 500]})

    topic.publish(
        Message="match",
        MessageAttributes={
            "price": {
                "DataType": "String.Array",
                "StringValue": json.dumps([100.1234567, 50]),
            }
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {"price": {"Type": "String.Array", "Value": json.dumps([100.1234567, 50])}}
    ]


@mock_aws
def test_filtering_string_array_with_number_float_accuracy_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [100.123456789, 500]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": [100.1234567, 50]}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "result": {"Type": "String", "Value": "match"},
        }
    ]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"price": [100.1234567, 50]}]


@mock_aws
# this is the correct behavior from SNS
def test_filtering_string_array_with_number_no_array_match():
    topic, queue = _setup_filter_policy_test({"price": [100, 500]})

    topic.publish(
        Message="match",
        MessageAttributes={"price": {"DataType": "String.Array", "StringValue": "100"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"price": {"Type": "String.Array", "Value": "100"}}]


@mock_aws
# this is the correct behavior from SNS
def test_filtering_string_array_with_number_no_array_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [100, 500]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": 100}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"result": {"Type": "String", "Value": "match"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"price": 100}]


@mock_aws
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
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_string_array_with_number_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [500]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": [100, 50]}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no_match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
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
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_string_array_with_string_no_array_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"price": [100]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"price": "one hundred"}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no_match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
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
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {"store": {"Type": "String", "Value": "example_corp"}}
    ]


@mock_aws
def test_filtering_body_key_exists_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": [{"exists": True}]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"store": "example_corp"}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"result": {"Type": "String", "Value": "match"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"store": "example_corp"}]


@mock_aws
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
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_body_key_exists_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": [{"exists": True}]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"event": "order_cancelled"}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
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
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {"event": {"Type": "String", "Value": "order_cancelled"}}
    ]


@mock_aws
def test_filtering_body_key_not_exists_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": [{"exists": False}]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"event": "order_cancelled"}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"result": {"Type": "String", "Value": "match"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [{"event": "order_cancelled"}]


@mock_aws
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
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_body_key_not_exists_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {"store": [{"exists": False}]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"store": "example_corp"}),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
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
    assert message_bodies == ["match"]
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [
        {
            "store": {"Type": "String", "Value": "example_corp"},
            "event": {"Type": "String", "Value": "order_cancelled"},
            "customer_interests": {
                "Type": "String.Array",
                "Value": json.dumps(["basketball", "rugby"]),
            },
            "price": {"Type": "Number", "Value": "100"},
        }
    ]


@mock_aws
def test_filtering_all_AND_matching_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "store": [{"exists": True}],
            "event": ["order_cancelled"],
            "customer_interests": ["basketball", "baseball"],
            "price": [100],
        },
        filter_policy_scope="MessageBody",
    )

    topic.publish(
        Message=json.dumps(
            {
                "store": "example_corp",
                "event": "order_cancelled",
                "customer_interests": ["basketball", "rugby"],
                "price": 100,
            }
        ),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"result": {"Type": "String", "Value": "match"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [
        {
            "store": "example_corp",
            "event": "order_cancelled",
            "customer_interests": ["basketball", "rugby"],
            "price": 100,
        }
    ]


@mock_aws
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
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_all_AND_matching_no_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "store": [{"exists": True}],
            "event": ["order_cancelled"],
            "customer_interests": ["basketball", "baseball"],
            "price": [100],
            "encrypted": [False],
        },
        filter_policy_scope="MessageBody",
    )

    topic.publish(
        Message=json.dumps(
            {
                "store": "example_corp",
                "event": "order_cancelled",
                "customer_interests": ["basketball", "rugby"],
                "price": 100,
            }
        ),
        MessageAttributes={"result": {"DataType": "String", "StringValue": "no match"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []


@mock_aws
def test_filtering_or():
    filter_policy = {
        "source": ["aws.cloudwatch"],
        "$or": [
            {"metricName": ["CPUUtilization"]},
            {"namespace": ["AWS/EC2"]},
        ],
    }
    topic, queue = _setup_filter_policy_test(filter_policy)

    topic.publish(
        Message="match_first",
        MessageAttributes={
            "source": {"DataType": "String", "StringValue": "aws.cloudwatch"},
            "metricName": {"DataType": "String", "StringValue": "CPUUtilization"},
        },
    )

    topic.publish(
        Message="match_second",
        MessageAttributes={
            "source": {"DataType": "String", "StringValue": "aws.cloudwatch"},
            "namespace": {"DataType": "String", "StringValue": "AWS/EC2"},
        },
    )

    topic.publish(
        Message="no_match",
        MessageAttributes={
            "source": {"DataType": "String", "StringValue": "aws.cloudwatch"}
        },
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert sorted(message_bodies) == ["match_first", "match_second"]


@mock_aws
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
    assert set(message_bodies) == {"match1", "match3"}


@mock_aws
def test_filtering_prefix_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "customer_interests": [{"prefix": "bas"}],
        },
        filter_policy_scope="MessageBody",
    )

    for interest in ["basketball", "rugby", "baseball"]:
        topic.publish(
            Message=json.dumps(
                {
                    "customer_interests": interest,
                }
            )
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"customer_interests": "basketball"}, {"customer_interests": "baseball"}]
    )


@mock_aws
def test_filtering_suffix():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"suffix": "ball"}]}
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
    assert set(message_bodies) == {"match1", "match3"}


@mock_aws
def test_filtering_suffix_message_body():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"suffix": "ball"}]},
        filter_policy_scope="MessageBody",
    )

    for interest in ["basketball", "rugby", "baseball"]:
        topic.publish(Message=json.dumps({"customer_interests": interest}))

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"customer_interests": "basketball"}, {"customer_interests": "baseball"}]
    )


@mock_aws
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
    assert set(message_bodies) == {"match2", "match3"}


@mock_aws
def test_filtering_anything_but_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "customer_interests": [{"anything-but": "basketball"}],
        },
        filter_policy_scope="MessageBody",
    )

    for interest in ["basketball", "rugby", "baseball"]:
        topic.publish(
            Message=json.dumps(
                {
                    "customer_interests": interest,
                }
            )
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"customer_interests": "rugby"}, {"customer_interests": "baseball"}]
    )


@mock_aws
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
    assert set(message_bodies) == {"match3"}


@mock_aws
def test_filtering_anything_but_multiple_values_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "customer_interests": [{"anything-but": ["basketball", "rugby"]}],
        },
        filter_policy_scope="MessageBody",
    )

    for interest in ["basketball", "rugby", "baseball"]:
        topic.publish(
            Message=json.dumps(
                {
                    "customer_interests": interest,
                }
            )
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"customer_interests": "baseball"}]
    )


@mock_aws
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
    assert set(message_bodies) == {"match2"}


@mock_aws
def test_filtering_anything_but_prefix_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "customer_interests": [{"anything-but": {"prefix": "bas"}}],
        },
        filter_policy_scope="MessageBody",
    )

    for interest in ["basketball", "rugby", "baseball"]:
        topic.publish(
            Message=json.dumps(
                {
                    "customer_interests": interest,
                }
            )
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"customer_interests": "rugby"}]
    )


@mock_aws
def test_filtering_anything_but_unknown():
    try:
        _setup_filter_policy_test(
            {"customer_interests": [{"anything-but": {"unknown": "bas"}}]}
        )
    except ClientError as err:
        assert err.response["Error"]["Code"] == "InvalidParameter"


@mock_aws
def test_filtering_anything_but_unknown_message_body_raises():
    try:
        _setup_filter_policy_test(
            {
                "customer_interests": [{"anything-but": {"unknown": "bas"}}],
            },
            filter_policy_scope="MessageBody",
        )
    except ClientError as err:
        assert err.response["Error"]["Code"] == "InvalidParameter"


@mock_aws
def test_filtering_anything_but_numeric():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"anything-but": [100]}]}
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
    assert set(message_bodies) == {"match1", "match3"}


@mock_aws
def test_filtering_anything_but_numeric_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "customer_interests": [{"anything-but": [100]}],
        },
        filter_policy_scope="MessageBody",
    )

    for nr in [50, 100, 150]:
        topic.publish(
            Message=json.dumps(
                {
                    "customer_interests": nr,
                }
            )
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)

    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"customer_interests": 50}, {"customer_interests": 150}]
    )


@mock_aws
def test_filtering_anything_but_numeric_string():
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
    assert set(message_bodies) == {"match1", "match2", "match3"}


@mock_aws
def test_filtering_anything_but_numeric_string_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "customer_interests": [{"anything-but": ["100"]}],
        },
        filter_policy_scope="MessageBody",
    )

    for nr in [50, 100, 150]:
        topic.publish(
            Message=json.dumps(
                {
                    "customer_interests": nr,
                }
            )
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)

    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [
            {"customer_interests": 50},
            {"customer_interests": 100},
            {"customer_interests": 150},
        ]
    )


@mock_aws
def test_filtering_equals_ignore_case():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"equals-ignore-case": "tennis"}]}
    )

    for interest, idx in [
        ("tenis", "1"),
        ("TeNnis", "2"),
        ("tennis", "3"),
        ("baseball", "4"),
    ]:
        topic.publish(
            Message=f"match{idx}",
            MessageAttributes={
                "customer_interests": {"DataType": "String", "StringValue": interest},
            },
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert sorted(message_bodies) == ["match2", "match3"]


@mock_aws
def test_filtering_equals_ignore_case_message_body():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"equals-ignore-case": "tennis"}]},
        filter_policy_scope="MessageBody",
    )

    for interest in ["tenis", "TeNnis", "tennis", "baseball"]:
        topic.publish(Message=json.dumps({"customer_interests": interest}))

    messages = queue.receive_messages(MaxNumberOfMessages=5)

    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [
            {"customer_interests": "TeNnis"},
            {"customer_interests": "tennis"},
        ]
    )


@mock_aws
def test_filtering_numeric_match():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"numeric": ["=", 100]}]}
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
    assert set(message_bodies) == {"match2"}


@mock_aws
def test_filtering_numeric_match_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "customer_interests": [{"numeric": ["=", 100]}],
        },
        filter_policy_scope="MessageBody",
    )

    for nr in [50, 100, 150]:
        topic.publish(
            Message=json.dumps(
                {
                    "customer_interests": nr,
                }
            )
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"customer_interests": 100}]
    )


@mock_aws
def test_filtering_numeric_range():
    topic, queue = _setup_filter_policy_test(
        {"customer_interests": [{"numeric": [">", 49, "<=", 100]}]}
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
    assert set(message_bodies) == {"match1", "match2"}


@mock_aws
def test_filtering_numeric_range_message_body():
    topic, queue = _setup_filter_policy_test(
        {
            "customer_interests": [{"numeric": [">", 49, "<=", 100]}],
        },
        filter_policy_scope="MessageBody",
    )

    for nr in [50, 100, 150]:
        topic.publish(
            Message=json.dumps(
                {
                    "customer_interests": nr,
                }
            )
        )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"customer_interests": 50}, {"customer_interests": 100}]
    )


@mock_aws
def test_filtering_exact_string_message_body_invalid_json_no_match():
    topic, queue = _setup_filter_policy_test(
        {"store": ["example_corp"]}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message='{"store": "another_corp"',
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_exact_string_message_body_empty_filter_policy_match():
    topic, queue = _setup_filter_policy_test({}, filter_policy_scope="MessageBody")

    topic.publish(
        Message='{"store": "another_corp"}',
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert to_comparable_dicts(message_attributes) == to_comparable_dicts(
        [{"match": {"Type": "String", "Value": "body"}}]
    )
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"store": "another_corp"}]
    )


@mock_aws
def test_filtering_exact_string_message_body_nested():
    topic, queue = _setup_filter_policy_test(
        {"store": {"name": ["example_corp"]}}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"store": {"name": "example_corp"}}),
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"match": {"Type": "String", "Value": "body"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"store": {"name": "example_corp"}}]
    )


@mock_aws
def test_filtering_exact_string_message_body_nested_no_match():
    topic, queue = _setup_filter_policy_test(
        {"store": {"name": ["example_corp"]}}, filter_policy_scope="MessageBody"
    )

    topic.publish(
        Message=json.dumps({"store": {"name": "another_corp"}}),
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_message_body_nested_prefix():
    topic, queue = _setup_filter_policy_test(
        {"store": {"name": [{"prefix": "example_corp"}]}},
        filter_policy_scope="MessageBody",
    )

    topic.publish(
        Message=json.dumps({"store": {"name": "example_corp"}}),
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"match": {"Type": "String", "Value": "body"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert to_comparable_dicts(message_bodies) == to_comparable_dicts(
        [{"store": {"name": "example_corp"}}]
    )


@mock_aws
def test_filtering_message_body_nested_prefix_no_match():
    topic, queue = _setup_filter_policy_test(
        {"store": {"name": [{"prefix": "example_corp"}]}},
        filter_policy_scope="MessageBody",
    )

    topic.publish(
        Message=json.dumps({"store": {"name": "another_corp-1"}}),
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_message_body_nested_multiple_prefix():
    topic, queue = _setup_filter_policy_test(
        {
            "Records": {
                "s3": {"object": {"key": [{"prefix": "test-"}]}},
                "eventName": [{"prefix": "ObjectCreated:"}],
            }
        },
        filter_policy_scope="MessageBody",
    )

    payload = {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "object": {
                        "key": "test-entry.xml",
                    }
                },
            }
        ]
    }

    topic.publish(
        Message=json.dumps(payload),
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"match": {"Type": "String", "Value": "body"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [payload]


@mock_aws
def test_filtering_message_body_nested_multiple_prefix_no_match():
    topic, queue = _setup_filter_policy_test(
        {
            "Records": {
                "s3": {"object": {"key": [{"prefix": "test-"}]}},
                "eventName": [{"prefix": "ObjectCreated:"}],
            }
        },
        filter_policy_scope="MessageBody",
    )

    payload = {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "object": {
                        "key": "no-match-entry.xml",
                    }
                },
            }
        ]
    }

    topic.publish(
        Message=json.dumps(payload),
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_bodies = [json.loads(m.body)["Message"] for m in messages]
    assert message_bodies == []
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == []


@mock_aws
def test_filtering_message_body_nested_multiple_records_partial_match():
    topic, queue = _setup_filter_policy_test(
        {
            "Records": {
                "eventName": [{"prefix": "ObjectCreated:"}],
            }
        },
        filter_policy_scope="MessageBody",
    )

    payload = {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
            },
            {
                "eventName": "ObjectDeleted:Delete",
            },
        ]
    }

    topic.publish(
        Message=json.dumps(payload),
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"match": {"Type": "String", "Value": "body"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [payload]


@mock_aws
def test_filtering_message_body_nested_multiple_records_match():
    topic, queue = _setup_filter_policy_test(
        {
            "Records": {
                "eventName": [{"prefix": "ObjectCreated:"}],
            }
        },
        filter_policy_scope="MessageBody",
    )

    payload = {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
            },
            {
                "eventName": "ObjectCreated:Put",
            },
        ]
    }

    topic.publish(
        Message=json.dumps(payload),
        MessageAttributes={"match": {"DataType": "String", "StringValue": "body"}},
    )

    messages = queue.receive_messages(MaxNumberOfMessages=5)
    message_attributes = [json.loads(m.body)["MessageAttributes"] for m in messages]
    assert message_attributes == [{"match": {"Type": "String", "Value": "body"}}]
    message_bodies = [json.loads(json.loads(m.body)["Message"]) for m in messages]
    assert message_bodies == [payload]
