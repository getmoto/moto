import boto3
import pytest
import sure  # noqa

from botocore.exceptions import ClientError
from moto import mock_dynamodb2


@mock_dynamodb2
def test_query_gsi_with_wrong_key_attribute_names_throws_exception():
    table_schema = {
        "KeySchema": [{"AttributeName": "partitionKey", "KeyType": "HASH"}],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "GSI-K1",
                "KeySchema": [
                    {"AttributeName": "gsiK1PartitionKey", "KeyType": "HASH"},
                    {"AttributeName": "gsiK1SortKey", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY",},
            }
        ],
        "AttributeDefinitions": [
            {"AttributeName": "partitionKey", "AttributeType": "S"},
            {"AttributeName": "gsiK1PartitionKey", "AttributeType": "S"},
            {"AttributeName": "gsiK1SortKey", "AttributeType": "S"},
        ],
    }

    item = {
        "partitionKey": "pk-1",
        "gsiK1PartitionKey": "gsi-pk",
        "gsiK1SortKey": "gsi-sk",
        "someAttribute": "lore ipsum",
    }

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = dynamodb.Table("test-table")
    table.put_item(Item=item)

    # check using wrong name for sort key throws exception
    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression="gsiK1PartitionKey = :pk AND wrongName = :sk",
            ExpressionAttributeValues={":pk": "gsi-pk", ":sk": "gsi-sk"},
            IndexName="GSI-K1",
        )["Items"]
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Query condition missed key schema element: gsiK1SortKey"
    )

    # check using wrong name for partition key throws exception
    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression="wrongName = :pk AND gsiK1SortKey = :sk",
            ExpressionAttributeValues={":pk": "gsi-pk", ":sk": "gsi-sk"},
            IndexName="GSI-K1",
        )["Items"]
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Query condition missed key schema element: gsiK1PartitionKey"
    )

    # verify same behaviour for begins_with
    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression="gsiK1PartitionKey = :pk AND begins_with ( wrongName , :sk )",
            ExpressionAttributeValues={":pk": "gsi-pk", ":sk": "gsi-sk"},
            IndexName="GSI-K1",
        )["Items"]
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Query condition missed key schema element: gsiK1SortKey"
    )

    # verify same behaviour for between
    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression="gsiK1PartitionKey = :pk AND wrongName BETWEEN :sk1 and :sk2",
            ExpressionAttributeValues={
                ":pk": "gsi-pk",
                ":sk1": "gsi-sk",
                ":sk2": "gsi-sk2",
            },
            IndexName="GSI-K1",
        )["Items"]
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Query condition missed key schema element: gsiK1SortKey"
    )
