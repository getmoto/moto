import boto3
import pytest
import sure  # noqa

from botocore.exceptions import ClientError
from moto import mock_dynamodb2


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


@mock_dynamodb2
def test_query_gsi_with_wrong_key_attribute_names_throws_exception():
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


@mock_dynamodb2
def test_empty_expressionattributenames():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = ddb.Table("test-table")
    with pytest.raises(ClientError) as exc:
        table.get_item(
            Key={"id": "my_id"}, ExpressionAttributeNames={},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "ExpressionAttributeNames can only be specified when using expressions"
    )


@mock_dynamodb2
def test_empty_expressionattributenames_with_empty_projection():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = ddb.Table("test-table")
    with pytest.raises(ClientError) as exc:
        table.get_item(
            Key={"id": "my_id"}, ProjectionExpression="", ExpressionAttributeNames={},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("ExpressionAttributeNames must not be empty")


@mock_dynamodb2
def test_empty_expressionattributenames_with_projection():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = ddb.Table("test-table")
    with pytest.raises(ClientError) as exc:
        table.get_item(
            Key={"id": "my_id"}, ProjectionExpression="id", ExpressionAttributeNames={},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("ExpressionAttributeNames must not be empty")


@mock_dynamodb2
def test_update_item_range_key_set():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = ddb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )

    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"partitionKey": "the-key"},
            UpdateExpression="ADD x :one SET a = :a ADD y :one",
            ExpressionAttributeValues={":one": 1, ":a": "lore ipsum"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        'Invalid UpdateExpression: The "ADD" section can only be used once in an update expression;'
    )


@mock_dynamodb2
def test_batch_get_item_non_existing_table():

    client = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.batch_get_item(RequestItems={"my-table": {"Keys": [{"id": {"N": "0"}}]}})
    err = exc.value.response["Error"]
    assert err["Code"].should.equal("ResourceNotFoundException")
    assert err["Message"].should.equal("Requested resource not found")


@mock_dynamodb2
def test_batch_write_item_non_existing_table():
    client = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        # Table my-table does not exist
        client.batch_write_item(
            RequestItems={"my-table": [{"PutRequest": {"Item": {}}}]}
        )
    err = exc.value.response["Error"]
    assert err["Code"].should.equal("ResourceNotFoundException")
    assert err["Message"].should.equal("Requested resource not found")
