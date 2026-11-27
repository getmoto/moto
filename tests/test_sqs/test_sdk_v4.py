"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import json
from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_sqs import SQSClient, SQSConfig
    from aws_sdk_sqs.models import QueueDoesNotExist
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-sqs is not installed", allow_module_level=True)


@mock_aws
def test_order_queue_with_dead_letter_queue():
    """Produce and consume order events, sending failed messages to a dead-letter queue."""
    config = SQSConfig.resolve(region="us-east-1")
    queue_name = f"orders-{uuid4()}"

    with SQSClient(config=config) as client:
        dlq_url = client.create_queue(queue_name=f"{queue_name}-dlq").queue_url
        dlq_arn = client.get_queue_attributes(
            queue_url=dlq_url, attribute_names=["QueueArn"]
        ).attributes["QueueArn"]

        queue_url = client.create_queue(
            queue_name=queue_name,
            attributes={
                "VisibilityTimeout": "60",
                "RedrivePolicy": json.dumps(
                    {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": "3"}
                ),
            },
        ).queue_url
        assert queue_name in queue_url

        # Producer
        client.send_message(
            queue_url=queue_url,
            message_body=json.dumps({"order_id": "order-1"}),
            message_attributes={
                "priority": {"data_type": "String", "string_value": "high"}
            },
        )
        batch = client.send_message_batch(
            queue_url=queue_url,
            entries=[
                {
                    "id": f"msg{i}",
                    "message_body": json.dumps({"order_id": f"order-{i}"}),
                }
                for i in [2, 3]
            ],
        )
        assert sorted(entry.id for entry in batch.successful) == ["msg2", "msg3"]
        assert batch.failed == []

        attributes = client.get_queue_attributes(
            queue_url=queue_url, attribute_names=["All"]
        ).attributes
        assert attributes["ApproximateNumberOfMessages"] == "3"
        assert json.loads(attributes["RedrivePolicy"])["deadLetterTargetArn"] == dlq_arn

        # Consumer
        received = client.receive_message(
            queue_url=queue_url,
            max_number_of_messages=10,
            message_attribute_names=["All"],
        ).messages
        assert len(received) == 3
        orders = {json.loads(msg.body)["order_id"]: msg for msg in received}
        assert set(orders) == {"order-1", "order-2", "order-3"}
        assert orders["order-1"].message_attributes["priority"].string_value == "high"

        client.delete_message(
            queue_url=queue_url, receipt_handle=orders["order-1"].receipt_handle
        )
        client.delete_message_batch(
            queue_url=queue_url,
            entries=[
                {"id": "msg2", "receipt_handle": orders["order-2"].receipt_handle},
                {"id": "msg3", "receipt_handle": orders["order-3"].receipt_handle},
            ],
        )

        attributes = client.get_queue_attributes(
            queue_url=queue_url,
            attribute_names=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
            ],
        ).attributes
        assert attributes["ApproximateNumberOfMessages"] == "0"
        assert attributes["ApproximateNumberOfMessagesNotVisible"] == "0"

        client.delete_queue(queue_url=queue_url)
        client.delete_queue(queue_url=dlq_url)
        with pytest.raises(QueueDoesNotExist):
            client.get_queue_url(queue_name=queue_name)
