"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import json
from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_sns import SNSClient, SNSConfig
    from aws_sdk_sns.models import NotFoundException
    from aws_sdk_sqs import SQSClient, SQSConfig
except ImportError:  # Requires Python 3.12+
    pytest.skip(
        "aws-sdk-sns and aws-sdk-sqs are not installed", allow_module_level=True
    )


@mock_aws
def test_order_events_fan_out_to_queue():
    """Publish order events to a topic, and deliver only the relevant ones to a queue."""
    suffix = uuid4().hex[:8]

    with (
        SNSClient(config=SNSConfig.resolve(region="us-east-1")) as sns,
        SQSClient(config=SQSConfig.resolve(region="us-east-1")) as sqs,
    ):
        queue_url = sqs.create_queue(queue_name=f"shipping-{suffix}").queue_url
        queue_arn = sqs.get_queue_attributes(
            queue_url=queue_url, attribute_names=["QueueArn"]
        ).attributes["QueueArn"]

        topic_arn = sns.create_topic(
            name=f"order-events-{suffix}",
            attributes={"DisplayName": "Order events"},
            tags=[{"key": "team", "value": "checkout"}],
        ).topic_arn
        assert topic_arn.endswith(f":order-events-{suffix}")

        # The shipping service only cares about orders that are paid
        subscription_arn = sns.subscribe(
            topic_arn=topic_arn,
            protocol="sqs",
            endpoint=queue_arn,
            attributes={
                "RawMessageDelivery": "true",
                "FilterPolicy": json.dumps({"event_type": ["order_paid"]}),
            },
            return_subscription_arn=True,
        ).subscription_arn
        assert subscription_arn.startswith(f"{topic_arn}:")

        subscriptions = sns.list_subscriptions_by_topic(topic_arn=topic_arn)
        assert [(s.protocol, s.endpoint) for s in subscriptions.subscriptions] == [
            ("sqs", queue_arn)
        ]

        topic_attributes = sns.get_topic_attributes(topic_arn=topic_arn).attributes
        assert topic_attributes["DisplayName"] == "Order events"

        subscription_attributes = sns.get_subscription_attributes(
            subscription_arn=subscription_arn
        ).attributes
        assert subscription_attributes["PendingConfirmation"] == "false"
        assert subscription_attributes["RawMessageDelivery"] == "true"

        for order_id, event_type in [("1001", "order_created"), ("1001", "order_paid")]:
            published = sns.publish(
                topic_arn=topic_arn,
                message=json.dumps({"order_id": order_id}),
                message_attributes={
                    "event_type": {"data_type": "String", "string_value": event_type}
                },
            )
            assert published.message_id

        received = sqs.receive_message(
            queue_url=queue_url, max_number_of_messages=10, wait_time_seconds=1
        )
        assert [json.loads(m.body) for m in received.messages or []] == [
            {"order_id": "1001"}
        ]

        sns.unsubscribe(subscription_arn=subscription_arn)
        sns.delete_topic(topic_arn=topic_arn)
        with pytest.raises(NotFoundException):
            sns.get_topic_attributes(topic_arn=topic_arn)
