import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
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


@mock_dynamodb2
def test_create_table_with_redundant_attributes():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="test-table",
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
            ],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )

    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Number of attributes in KeySchema does not exactly match number of attributes defined in AttributeDefinitions"
    )

    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="test-table",
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "user", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
            ],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "gsi_user-items",
                    "KeySchema": [{"AttributeName": "user", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Some AttributeDefinitions are not used. AttributeDefinitions: [created_at, id, user], keys used: [id, user]"
    )


@mock_dynamodb2
def test_create_table_with_missing_attributes():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="test-table",
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"},],
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Invalid KeySchema: Some index key attribute have no definition"
    )

    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="test-table",
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"},],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "gsi_user-items",
                    "KeySchema": [{"AttributeName": "user", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Some index key attributes are not defined in AttributeDefinitions. Keys: [user], AttributeDefinitions: [id]"
    )


@mock_dynamodb2
def test_create_table_with_redundant_and_missing_attributes():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="test-table",
            AttributeDefinitions=[
                {"AttributeName": "created_at", "AttributeType": "N"}
            ],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Some index key attributes are not defined in AttributeDefinitions. Keys: [id], AttributeDefinitions: [created_at]"
    )

    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="test-table",
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
            ],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "gsi_user-items",
                    "KeySchema": [{"AttributeName": "user", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Some index key attributes are not defined in AttributeDefinitions. Keys: [user], AttributeDefinitions: [created_at, id]"
    )


@mock_dynamodb2
def test_put_item_wrong_attribute_type():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="test-table",
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "N"},
        ],
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    item = {
        "id": {"N": "1"},  # should be a string
        "created_at": {"N": "2"},
        "someAttribute": {"S": "lore ipsum"},
    }

    with pytest.raises(ClientError) as exc:
        dynamodb.put_item(TableName="test-table", Item=item)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Type mismatch for key id expected: S actual: N"
    )

    item = {
        "id": {"S": "some id"},
        "created_at": {"S": "should be date not string"},
        "someAttribute": {"S": "lore ipsum"},
    }

    with pytest.raises(ClientError) as exc:
        dynamodb.put_item(TableName="test-table", Item=item)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Type mismatch for key created_at expected: N actual: S"
    )


@mock_dynamodb2
# https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_Query.html#DDB-Query-request-KeyConditionExpression
def test_hash_key_cannot_use_begins_with_operations():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName="test-table",
        KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    items = [
        {"key": "prefix-$LATEST", "value": "$LATEST"},
        {"key": "prefix-DEV", "value": "DEV"},
        {"key": "prefix-PROD", "value": "PROD"},
    ]

    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    table = dynamodb.Table("test-table")
    with pytest.raises(ClientError) as ex:
        table.query(KeyConditionExpression=Key("key").begins_with("prefix-"))
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.equal(
        "Query key condition not supported"
    )


# Test this again, but with manually supplying an operator
@mock_dynamodb2
@pytest.mark.parametrize("operator", ["<", "<=", ">", ">="])
def test_hash_key_can_only_use_equals_operations(operator):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table",
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table = dynamodb.Table("test-table")

    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression=f"pk {operator} :pk",
            ExpressionAttributeValues={":pk": "p"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("Query key condition not supported")


@mock_dynamodb2
def test_creating_table_with_0_local_indexes():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="test-table",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
            LocalSecondaryIndexes=[],
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: List of LocalSecondaryIndexes is empty"
    )


@mock_dynamodb2
def test_creating_table_with_0_global_indexes():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="test-table",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
            GlobalSecondaryIndexes=[],
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: List of GlobalSecondaryIndexes is empty"
    )
