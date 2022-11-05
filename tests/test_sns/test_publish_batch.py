import boto3
import json
import sure  # noqa # pylint: disable=unused-import

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
    err["Code"].should.equal("NotFound")
    err["Message"].should.equal("Topic does not exist")


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
    err["Code"].should.equal("TooManyEntriesInBatchRequest")
    err["Message"].should.equal(
        "The batch request contains more entries than permissible."
    )


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
    err["Code"].should.equal("BatchEntryIdsNotDistinct")
    err["Message"].should.equal(
        "Two or more batch entries in the request have the same Id."
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
    err["Code"].should.equal("InvalidParameter")
    err["Message"].should.equal(
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

    resp.should.have.key("Successful").length_of(2)
    for message_status in resp["Successful"]:
        message_status.should.have.key("MessageId")
    [m["Id"] for m in resp["Successful"]].should.equal(["id_1", "id_3"])

    resp.should.have.key("Failed").length_of(1)
    resp["Failed"][0].should.equal(
        {
            "Id": "id_2",
            "Code": "InvalidParameter",
            "Message": "Invalid parameter: Value mgid for parameter MessageGroupId is invalid. Reason: The request include parameter that is not valid for this queue type.",
            "SenderFault": True,
        }
    )


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

    queue_url = "arn:aws:sqs:us-east-1:{}:test-queue".format(ACCOUNT_ID)
    client.subscribe(TopicArn=topic_arn, Protocol="sqs", Endpoint=queue_url)

    resp = client.publish_batch(TopicArn=topic_arn, PublishBatchRequestEntries=entries)

    resp.should.have.key("Successful").length_of(3)

    messages = queue.receive_messages(MaxNumberOfMessages=3)
    messages.should.have.length_of(3)

    messages = [json.loads(m.body) for m in messages]
    for m in messages:
        for key in list(m.keys()):
            if key not in ["Message", "Subject", "MessageAttributes"]:
                del m[key]

    messages.should.contain({"Message": "1"})
    messages.should.contain({"Message": "2", "Subject": "subj2"})
    messages.should.contain(
        {"Message": "3", "MessageAttributes": {"a": {"Type": "String", "Value": "v"}}}
    )


@mock_sqs
@mock_sns
def test_publish_batch_to_sqs_raw():
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="standard_topic")["TopicArn"]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-queue")

    queue_url = "arn:aws:sqs:us-east-1:{}:test-queue".format(ACCOUNT_ID)
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

    resp.should.have.key("Successful").length_of(2)

    received = queue.receive_messages(
        MaxNumberOfMessages=10, MessageAttributeNames=["All"]
    )

    messages = [(message.body, message.message_attributes) for message in received]

    messages.should.contain(("foo", None))
    messages.should.contain(("bar", {"a": {"StringValue": "v", "DataType": "String"}}))
