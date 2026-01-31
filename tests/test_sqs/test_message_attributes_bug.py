"""Test for the bug where MessageAttributes was being populated with empty dicts for system attributes."""

import boto3

from moto import mock_aws


@mock_aws
def test_message_attributes_should_not_include_system_attributes():
    """
    Test that receiving a message with AttributeNames=['All'] should NOT
    return empty MessageAttributes for system attributes.

    This was a bug where the ShapePrefixAlias was incorrectly mapping
    "MessageAttributes" -> "Attributes", causing the system attributes
    to appear as empty dicts in MessageAttributes.

    See: https://github.com/getmoto/moto/issues/XXXX
    """
    client = boto3.client("sqs", region_name="us-east-1")

    # Create queue
    queue_url = client.create_queue(QueueName="test-queue")["QueueUrl"]

    # Send a message WITHOUT any message attributes
    client.send_message(QueueUrl=queue_url, MessageBody="Hello from app startup!")

    # Receive the message with All system attributes and All message attributes
    response = client.receive_message(
        QueueUrl=queue_url,
        AttributeNames=["All"],
        MessageAttributeNames=["All"],
        MaxNumberOfMessages=1,
    )

    # Check that the message was received
    assert "Messages" in response
    assert len(response["Messages"]) == 1

    message = response["Messages"][0]

    # System attributes should be in Attributes
    assert "Attributes" in message
    assert "SenderId" in message["Attributes"]
    assert "SentTimestamp" in message["Attributes"]
    assert "ApproximateReceiveCount" in message["Attributes"]
    assert "ApproximateFirstReceiveTimestamp" in message["Attributes"]

    # MessageAttributes should either be absent or be an empty dict
    # It should NOT contain empty objects for system attributes
    if "MessageAttributes" in message:
        # MessageAttributes should be empty since we didn't send any
        assert message["MessageAttributes"] == {}, (
            f"MessageAttributes should be empty, but got: {message['MessageAttributes']}"
        )


@mock_aws
def test_message_attributes_work_correctly_when_present():
    """
    Test that MessageAttributes work correctly when actual message attributes are sent.
    """
    client = boto3.client("sqs", region_name="us-east-1")

    # Create queue
    queue_url = client.create_queue(QueueName="test-queue")["QueueUrl"]

    # Send a message WITH message attributes
    client.send_message(
        QueueUrl=queue_url,
        MessageBody="Hello",
        MessageAttributes={
            "Author": {"StringValue": "John Doe", "DataType": "String"},
            "Priority": {"StringValue": "1", "DataType": "Number"},
        },
    )

    # Receive the message with All attributes
    response = client.receive_message(
        QueueUrl=queue_url,
        AttributeNames=["All"],
        MessageAttributeNames=["All"],
        MaxNumberOfMessages=1,
    )

    message = response["Messages"][0]

    # Both Attributes and MessageAttributes should be present
    assert "Attributes" in message
    assert "MessageAttributes" in message

    # MessageAttributes should only contain the custom attributes we sent
    assert set(message["MessageAttributes"].keys()) == {"Author", "Priority"}
    assert message["MessageAttributes"]["Author"]["StringValue"] == "John Doe"
    assert message["MessageAttributes"]["Priority"]["StringValue"] == "1"

    # Attributes should contain system attributes, NOT message attributes
    assert "SenderId" in message["Attributes"]
    assert "SentTimestamp" in message["Attributes"]
    # System attributes should NOT be in MessageAttributes
    assert "SenderId" not in message["MessageAttributes"]
    assert "SentTimestamp" not in message["MessageAttributes"]


@mock_aws
def test_no_empty_message_attributes_without_all_parameter():
    """
    Test that MessageAttributes is not present when AttributeNames is not specified.
    """
    client = boto3.client("sqs", region_name="us-east-1")

    # Create queue
    queue_url = client.create_queue(QueueName="test-queue")["QueueUrl"]

    # Send a message WITHOUT any message attributes
    client.send_message(QueueUrl=queue_url, MessageBody="Hello")

    # Receive the message without AttributeNames or MessageAttributeNames
    response = client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)

    message = response["Messages"][0]

    # MessageAttributes should not be in the response
    assert "MessageAttributes" not in message
