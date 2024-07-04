from uuid import uuid4

import boto3
import pytest

from . import dynamodb_aws_verified


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_batch_write_single_set(table_name=None):
    ddb_client = boto3.client("dynamodb", region_name="us-east-1")

    ddb_client.transact_write_items(
        TransactItems=[
            {
                "Update": {
                    "TableName": table_name,
                    "Key": {"pk": {"S": "test"}},
                    "UpdateExpression": "SET xxx = :xxx",
                    "ConditionExpression": "attribute_not_exists(xxx)",
                    "ExpressionAttributeValues": {":xxx": {"S": "123"}},
                }
            }
        ]
    )

    results = ddb_client.scan(TableName=table_name)["Items"]
    assert results == [{"pk": {"S": "test"}, "xxx": {"S": "123"}}]


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_batch_write_item_to_multiple_tables():
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    tables = [f"table-{str(uuid4())[0:6]}-{i}" for i in range(3)]
    for name in tables:
        conn.create_table(
            TableName=name,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
    for name in tables:
        waiter = boto3.client("dynamodb", "us-west-2").get_waiter("table_exists")
        waiter.wait(TableName=name)

    try:
        conn.batch_write_item(
            RequestItems={
                tables[0]: [{"PutRequest": {"Item": {"id": "0"}}}],
                tables[1]: [{"PutRequest": {"Item": {"id": "1"}}}],
                tables[2]: [{"PutRequest": {"Item": {"id": "2"}}}],
            }
        )

        for idx, name in enumerate(tables):
            table = conn.Table(name)
            res = table.get_item(Key={"id": str(idx)})
            assert res["Item"] == {"id": str(idx)}
            assert table.scan()["Count"] == 1

        conn.batch_write_item(
            RequestItems={
                tables[0]: [{"DeleteRequest": {"Key": {"id": "0"}}}],
                tables[1]: [{"DeleteRequest": {"Key": {"id": "1"}}}],
                tables[2]: [{"DeleteRequest": {"Key": {"id": "2"}}}],
            }
        )

        for idx, name in enumerate(tables):
            assert conn.Table(name).scan()["Count"] == 0
    finally:
        for name in tables:
            try:
                conn.Table(name).delete()
            except Exception as e:
                print(f"Failed to delete table {name}")  # noqa
                print(e)  # noqa
