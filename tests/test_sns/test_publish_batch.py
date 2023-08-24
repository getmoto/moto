import json

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_sns, mock_sqs
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_sns
def test_publish_batch_unknown_topic():
    client = boto3.client("sns", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.publish_batch(
            TopicArn=f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:unknown",
            PublishBatchRequestEntries=[{"Id": "id_1", "Message": "1"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFound"
    assert err["Message"] == "Topic does not exist"


@mock_sns
def test_publish_batch_too_many_items():
    client = boto3.client("sns", region_name="eu-north-1")
    topic = client.create_topic(Name="some-topic")

    with pytest.raises(ClientError) as exc:
        client.publish_batch(
            TopicArn=topic["TopicArn"],
            PublishBatchRequestEntries=[
                {"Id": f"id_{idx}", "Message": f"{idx}"} for idx in range(11)
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "TooManyEntriesInBatchRequest"
    assert err["Message"] == "The batch request contains more entries than permissible."


@mock_sns
def test_publish_batch_non_unique_ids():
    client = boto3.client("sns", region_name="us-west-2")
    topic = client.create_topic(Name="some-topic")

    with pytest.raises(ClientError) as exc:
        client.publish_batch(
            TopicArn=topic["TopicArn"],
            PublishBatchRequestEntries=[
                {"Id": "id", "Message": f"{idx}"} for idx in range(5)
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "BatchEntryIdsNotDistinct"
    assert (
        err["Message"] == "Two or more batch entries in the request have the same Id."
    )


@mock_sns
def test_publish_batch_fifo_without_message_group_id():
    client = boto3.client("sns", region_name="us-east-1")
    topic = client.create_topic(
        Name="fifo_without_msg.fifo",
        Attributes={"FifoTopic": "true", "ContentBasedDeduplication": "true"},
    )

    with pytest.raises(ClientError) as exc:
        client.publish_batch(
            TopicArn=topic["TopicArn"],
            PublishBatchRequestEntries=[{"Id": "id_2", "Message": "2"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameter"
    assert err["Message"] == (
        "Invalid parameter: The MessageGroupId parameter is required for FIFO topics"
    )


@mock_sns
def test_publish_batch_standard_with_message_group_id():
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="standard_topic")["TopicArn"]
    entries = [
        {"Id": "id_1", "Message": "1"},
        {"Id": "id_2", "Message": "2", "MessageGroupId": "mgid"},
        {"Id": "id_3", "Message": "3"},
    ]
    resp = client.publish_batch(TopicArn=topic_arn, PublishBatchRequestEntries=entries)

    assert len(resp["Successful"]) == 2
    for message_status in resp["Successful"]:
        assert "MessageId" in message_status
    assert [m["Id"] for m in resp["Successful"]] == ["id_1", "id_3"]

    assert len(resp["Failed"]) == 1
    assert resp["Failed"][0] == {
        "Id": "id_2",
        "Code": "InvalidParameter",
        "Message": (
            "Invalid parameter: MessageGroupId Reason: The request includes "
            "MessageGroupId parameter that is not valid for this topic type"
        ),
        "SenderFault": True,
    }


@mock_sns
@mock_sqs
def test_publish_batch_to_sqs():
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="standard_topic")["TopicArn"]
    entries = [
        {"Id": "id_1", "Message": "1"},
        {"Id": "id_2", "Message": "2", "Subject": "subj2"},
        {
            "Id": "id_3",
            "Message": "3",
            "MessageAttributes": {"a": {"DataType": "String", "StringValue": "v"}},
        },
    ]

    sqs_conn = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs_conn.create_queue(QueueName="test-queue")

    queue_url = f"arn:aws:sqs:us-east-1:{ACCOUNT_ID}:test-queue"
    client.subscribe(TopicArn=topic_arn, Protocol="sqs", Endpoint=queue_url)

    resp = client.publish_batch(TopicArn=topic_arn, PublishBatchRequestEntries=entries)

    assert len(resp["Successful"]) == 3

    messages = queue.receive_messages(MaxNumberOfMessages=3)
    assert len(messages) == 3

    messages = [json.loads(m.body) for m in messages]
    for message in messages:
        for key in list(message.keys()):
            if key not in ["Message", "Subject", "MessageAttributes"]:
                del message[key]

    assert {"Message": "1"} in messages
    assert {"Message": "2", "Subject": "subj2"} in messages
    assert (
        {"Message": "3", "MessageAttributes": {"a": {"Type": "String", "Value": "v"}}}
    ) in messages


@mock_sqs
@mock_sns
def test_publish_batch_to_sqs_raw():
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="standard_topic")["TopicArn"]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-queue")

    queue_url = f"arn:aws:sqs:us-east-1:{ACCOUNT_ID}:test-queue"
    client.subscribe(
        TopicArn=topic_arn,
        Protocol="sqs",
        Endpoint=queue_url,
        Attributes={"RawMessageDelivery": "true"},
    )

    entries = [
        {"Id": "1", "Message": "foo"},
        {
            "Id": "2",
            "Message": "bar",
            "MessageAttributes": {"a": {"DataType": "String", "StringValue": "v"}},
        },
    ]
    resp = client.publish_batch(TopicArn=topic_arn, PublishBatchRequestEntries=entries)

    assert len(resp["Successful"]) == 2

    received = queue.receive_messages(
        MaxNumberOfMessages=10, MessageAttributeNames=["All"]
    )

    messages = [(message.body, message.message_attributes) for message in received]

    assert ("foo", None) in messages
    assert ("bar", {"a": {"StringValue": "v", "DataType": "String"}}) in messages
