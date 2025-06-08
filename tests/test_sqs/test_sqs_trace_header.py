import boto3
import pytest
from moto import mock_sqs
from uuid import uuid4


@mock_sqs
def test_receive_trace_header_if_requested():
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_name = f"test-queue-{uuid4()}"
    queue_url = sqs.create_queue(QueueName=queue_name)["QueueUrl"]

    trace_header_value = "Root=1-67891233-abcdef012345678912345678"

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody="test message with trace header",
        MessageSystemAttributes={
            "AWSTraceHeader": {
                "StringValue": trace_header_value,
                "DataType": "String",
            }
        },
    )

    receive_response = sqs.receive_message(
        QueueUrl=queue_url,
        MessageSystemAttributeNames=["AWSTraceHeader"],
        MaxNumberOfMessages=1,
    )

    messages = receive_response.get("Messages", [])
    assert len(messages) == 1
    message = messages[0]

    assert "MessageSystemAttributes" in message
    assert "AWSTraceHeader" in message["MessageSystemAttributes"]
    assert (
        message["MessageSystemAttributes"]["AWSTraceHeader"]["StringValue"]
        == trace_header_value
    )

    sqs.delete_queue(QueueUrl=queue_url)


@mock_sqs
def test_no_trace_header_if_not_requested():
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_name = f"test-queue-{uuid4()}"
    queue_url = sqs.create_queue(QueueName=queue_name)["QueueUrl"]

    trace_header_value = "Root=1-abcdef01-23456789abcdef0123456789"

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody="test message with trace header, not requested",
        MessageSystemAttributes={
            "AWSTraceHeader": {
                "StringValue": trace_header_value,
                "DataType": "String",
            }
        },
    )

    receive_response = sqs.receive_message(
        QueueUrl=queue_url,
        # MessageSystemAttributeNames is omitted or empty
        MaxNumberOfMessages=1,
    )

    messages = receive_response.get("Messages", [])
    assert len(messages) == 1
    message = messages[0]

    # AWSTraceHeader should not be present if not specifically requested
    if "MessageSystemAttributes" in message:
        assert "AWSTraceHeader" not in message["MessageSystemAttributes"]
    else:
        # If MessageSystemAttributes itself is not present, the assertion also passes
        pass


    # Also test with an explicit empty list for MessageSystemAttributeNames
    receive_response_empty_list = sqs.receive_message(
        QueueUrl=queue_url,
        MessageSystemAttributeNames=[],
        MaxNumberOfMessages=1,
        VisibilityTimeout=0 # Ensure we get the same message again if not deleted
    )
    messages_empty_list = receive_response_empty_list.get("Messages", [])
    assert len(messages_empty_list) == 1
    message_empty_list = messages_empty_list[0]
    if "MessageSystemAttributes" in message_empty_list:
        assert "AWSTraceHeader" not in message_empty_list["MessageSystemAttributes"]
    else:
        pass


    # Also test with a list containing other attributes for MessageSystemAttributeNames
    receive_response_other_attr = sqs.receive_message(
        QueueUrl=queue_url,
        MessageSystemAttributeNames=["SenderId"], # Requesting a different attribute
        MaxNumberOfMessages=1,
        VisibilityTimeout=0 # Ensure we get the same message again
    )
    messages_other_attr = receive_response_other_attr.get("Messages", [])
    assert len(messages_other_attr) == 1
    message_other_attr = messages_other_attr[0]
    assert "SenderId" in message_other_attr.get("Attributes", {}) # SenderId is in 'Attributes' not 'MessageSystemAttributes' directly
    if "MessageSystemAttributes" in message_other_attr:
         assert "AWSTraceHeader" not in message_other_attr["MessageSystemAttributes"]
    else:
        pass

    sqs.delete_queue(QueueUrl=queue_url)
