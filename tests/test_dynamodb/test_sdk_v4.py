"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_dynamodb import DynamoDBClient, DynamoDBConfig
    from aws_sdk_dynamodb.models import (
        AttributeValueN,
        AttributeValueS,
        ConditionalCheckFailedException,
    )
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-dynamodb is not installed", allow_module_level=True)


@mock_aws
def test_order_tracking():
    """Store orders per customer, query them, and update an order's status."""
    config = DynamoDBConfig.resolve(region="us-east-1")
    table_name = f"orders-{uuid4()}"

    with DynamoDBClient(config=config) as client:
        created = client.create_table(
            table_name=table_name,
            key_schema=[
                {"attribute_name": "customer_id", "key_type": "HASH"},
                {"attribute_name": "order_id", "key_type": "RANGE"},
            ],
            attribute_definitions=[
                {"attribute_name": "customer_id", "attribute_type": "S"},
                {"attribute_name": "order_id", "attribute_type": "S"},
            ],
            billing_mode="PAY_PER_REQUEST",
        )
        assert created.table_description.table_name == table_name
        assert created.table_description.table_status == "ACTIVE"

        client.batch_write_item(
            request_items={
                table_name: [
                    {
                        "put_request": {
                            "item": {
                                "customer_id": {"s": customer},
                                "order_id": {"s": order},
                                "total": {"n": total},
                                "status": {"s": "PENDING"},
                            }
                        }
                    }
                    for customer, order, total in [
                        ("alice", "order-1", "15.50"),
                        ("alice", "order-2", "99"),
                        ("bob", "order-3", "7"),
                    ]
                ]
            }
        )

        alice_orders = client.query(
            table_name=table_name,
            key_condition_expression="customer_id = :customer",
            expression_attribute_values={":customer": {"s": "alice"}},
        )
        assert alice_orders.count == 2
        assert [item["order_id"] for item in alice_orders.items or []] == [
            AttributeValueS("order-1"),
            AttributeValueS("order-2"),
        ]

        # Ship the order, but only if it hasn't been shipped yet
        updated = client.update_item(
            table_name=table_name,
            key={"customer_id": {"s": "alice"}, "order_id": {"s": "order-2"}},
            update_expression="SET #status = :shipped",
            condition_expression="#status = :pending",
            expression_attribute_names={"#status": "status"},
            expression_attribute_values={
                ":shipped": {"s": "SHIPPED"},
                ":pending": {"s": "PENDING"},
            },
            return_values="ALL_NEW",
        )
        assert updated.attributes["status"] == AttributeValueS("SHIPPED")
        assert updated.attributes["total"] == AttributeValueN("99")

        with pytest.raises(ConditionalCheckFailedException):
            client.update_item(
                table_name=table_name,
                key={"customer_id": {"s": "alice"}, "order_id": {"s": "order-2"}},
                update_expression="SET #status = :shipped",
                condition_expression="#status = :pending",
                expression_attribute_names={"#status": "status"},
                expression_attribute_values={
                    ":shipped": {"s": "SHIPPED"},
                    ":pending": {"s": "PENDING"},
                },
            )

        order = client.get_item(
            table_name=table_name,
            key={"customer_id": {"s": "alice"}, "order_id": {"s": "order-2"}},
            consistent_read=True,
        )
        assert order.item["status"] == AttributeValueS("SHIPPED")

        client.delete_item(
            table_name=table_name,
            key={"customer_id": {"s": "bob"}, "order_id": {"s": "order-3"}},
        )
        remaining = client.scan(table_name=table_name)
        assert remaining.count == 2

        client.delete_table(table_name=table_name)
