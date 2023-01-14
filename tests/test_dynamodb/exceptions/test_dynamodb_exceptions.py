import boto3
import botocore
import pytest
import sure  # noqa # pylint: disable=unused-import
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from unittest import SkipTest
from moto import mock_dynamodb, settings

table_schema = {
    "KeySchema": [{"AttributeName": "partitionKey", "KeyType": "HASH"}],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "GSI-K1",
            "KeySchema": [
                {"AttributeName": "gsiK1PartitionKey", "KeyType": "HASH"},
                {"AttributeName": "gsiK1SortKey", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "KEYS_ONLY"},
        }
    ],
    "AttributeDefinitions": [
        {"AttributeName": "partitionKey", "AttributeType": "S"},
        {"AttributeName": "gsiK1PartitionKey", "AttributeType": "S"},
        {"AttributeName": "gsiK1SortKey", "AttributeType": "S"},
    ],
}


@mock_dynamodb
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


@mock_dynamodb
def test_query_table_with_wrong_key_attribute_names_throws_exception():
    item = {
        "partitionKey": "pk-1",
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
            KeyConditionExpression="wrongName = :pk",
            ExpressionAttributeValues={":pk": "pk"},
        )["Items"]
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Query condition missed key schema element: partitionKey"
    )


@mock_dynamodb
def test_empty_expressionattributenames():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = ddb.Table("test-table")
    with pytest.raises(ClientError) as exc:
        table.get_item(Key={"id": "my_id"}, ExpressionAttributeNames={})
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "ExpressionAttributeNames can only be specified when using expressions"
    )


@mock_dynamodb
def test_empty_expressionattributenames_with_empty_projection():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = ddb.Table("test-table")
    with pytest.raises(ClientError) as exc:
        table.get_item(
            Key={"id": "my_id"}, ProjectionExpression="", ExpressionAttributeNames={}
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("ExpressionAttributeNames must not be empty")


@mock_dynamodb
def test_empty_expressionattributenames_with_projection():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = ddb.Table("test-table")
    with pytest.raises(ClientError) as exc:
        table.get_item(
            Key={"id": "my_id"}, ProjectionExpression="id", ExpressionAttributeNames={}
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("ExpressionAttributeNames must not be empty")


@mock_dynamodb
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


@mock_dynamodb
def test_batch_get_item_non_existing_table():

    client = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.batch_get_item(RequestItems={"my-table": {"Keys": [{"id": {"N": "0"}}]}})
    err = exc.value.response["Error"]
    assert err["Code"].should.equal("ResourceNotFoundException")
    assert err["Message"].should.equal("Requested resource not found")


@mock_dynamodb
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


@mock_dynamodb
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


@mock_dynamodb
def test_create_table_with_missing_attributes():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="test-table",
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
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
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
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


@mock_dynamodb
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


@mock_dynamodb
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


@mock_dynamodb
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
@mock_dynamodb
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


@mock_dynamodb
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


@mock_dynamodb
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


@mock_dynamodb
def test_multiple_transactions_on_same_item():
    schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **schema
    )
    # Insert an item
    dynamodb.put_item(TableName="test-table", Item={"id": {"S": "foo"}})

    def update_email_transact(email):
        return {
            "Update": {
                "Key": {"id": {"S": "foo"}},
                "TableName": "test-table",
                "UpdateExpression": "SET #e = :v",
                "ExpressionAttributeNames": {"#e": "email_address"},
                "ExpressionAttributeValues": {":v": {"S": email}},
            }
        }

    with pytest.raises(ClientError) as exc:
        dynamodb.transact_write_items(
            TransactItems=[
                update_email_transact("test1@moto.com"),
                update_email_transact("test2@moto.com"),
            ]
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Transaction request cannot include multiple operations on one item"
    )


@mock_dynamodb
def test_transact_write_items__too_many_transactions():
    schema = {
        "KeySchema": [{"AttributeName": "pk", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "pk", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **schema
    )

    def update_email_transact(email):
        return {
            "Put": {
                "TableName": "test-table",
                "Item": {"pk": {"S": ":v"}},
                "ExpressionAttributeValues": {":v": {"S": email}},
            }
        }

    update_email_transact("test1@moto.com")
    with pytest.raises(ClientError) as exc:
        dynamodb.transact_write_items(
            TransactItems=[
                update_email_transact(f"test{idx}@moto.com") for idx in range(101)
            ]
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.match(
        "1 validation error detected at 'transactItems' failed to satisfy constraint: "
        "Member must have length less than or equal to 100."
    )


@mock_dynamodb
def test_update_item_non_existent_table():
    client = boto3.client("dynamodb", region_name="us-west-2")
    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.update_item(
            TableName="non-existent",
            Key={"forum_name": {"S": "LOLCat Forum"}},
            UpdateExpression="set Body=:Body",
            ExpressionAttributeValues={":Body": {"S": ""}},
        )
    err = exc.value.response["Error"]
    assert err["Code"].should.equal("ResourceNotFoundException")
    assert err["Message"].should.equal("Requested resource not found")


@mock_dynamodb
@pytest.mark.parametrize(
    "expression",
    [
        "set example_column = :example_column, example_column = :example_column",
        "set example_column = :example_column ADD x :y set example_column = :example_column",
    ],
)
def test_update_item_with_duplicate_expressions(expression):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="example_table",
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    record = {
        "pk": "example_id",
        "example_column": "example",
    }
    table = dynamodb.Table("example_table")
    table.put_item(Item=record)
    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"pk": "example_id"},
            UpdateExpression=expression,
            ExpressionAttributeValues={":example_column": "test"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "Invalid UpdateExpression: Two document paths overlap with each other; must remove or rewrite one of these paths; path one: [example_column], path two: [example_column]"
    )

    # The item is not updated
    item = table.get_item(Key={"pk": "example_id"})["Item"]
    item.should.equal({"pk": "example_id", "example_column": "example"})


@mock_dynamodb
def test_put_item_wrong_datatype():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to mock a session with Config in ServerMode")
    session = botocore.session.Session()
    config = botocore.client.Config(parameter_validation=False)
    client = session.create_client("dynamodb", region_name="us-east-1", config=config)
    client.create_table(
        TableName="test2",
        KeySchema=[{"AttributeName": "mykey", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "mykey", "AttributeType": "N"}],
        BillingMode="PAY_PER_REQUEST",
    )
    with pytest.raises(ClientError) as exc:
        client.put_item(TableName="test2", Item={"mykey": {"N": 123}})
    err = exc.value.response["Error"]
    err["Code"].should.equal("SerializationException")
    err["Message"].should.equal("NUMBER_VALUE cannot be converted to String")

    # Same thing - but with a non-key, and nested
    with pytest.raises(ClientError) as exc:
        client.put_item(
            TableName="test2",
            Item={"mykey": {"N": "123"}, "nested": {"M": {"sth": {"N": 5}}}},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("SerializationException")
    err["Message"].should.equal("NUMBER_VALUE cannot be converted to String")


@mock_dynamodb
def test_put_item_empty_set():
    client = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="test-table",
        KeySchema=[{"AttributeName": "Key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "Key", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table = dynamodb.Table("test-table")
    with pytest.raises(ClientError) as exc:
        table.put_item(Item={"Key": "some-irrelevant_key", "attr2": {"SS": set([])}})
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: An number set  may not be empty"
    )


@mock_dynamodb
def test_update_expression_with_trailing_comma():
    resource = boto3.resource(service_name="dynamodb", region_name="us-east-1")
    table = resource.create_table(
        TableName="test-table",
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table.put_item(Item={"pk": "key", "attr2": 2})

    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"pk": "key", "sk": "sk"},
            # Trailing comma should be invalid
            UpdateExpression="SET #attr1 = :val1, #attr2 = :val2,",
            ExpressionAttributeNames={"#attr1": "attr1", "#attr2": "attr2"},
            ExpressionAttributeValues={":val1": 3, ":val2": 4},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        'Invalid UpdateExpression: Syntax error; token: "<EOF>", near: ","'
    )


@mock_dynamodb
def test_batch_put_item_with_empty_value():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        TableName="test-table",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "SORT"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = ddb.Table("test-table")

    # Empty Partition Key throws an error
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        with table.batch_writer() as batch:
            batch.put_item(Item={"pk": "", "sk": "sth"})
    err = exc.value.response["Error"]
    err["Message"].should.equal(
        "One or more parameter values are not valid. The AttributeValue for a key attribute cannot contain an empty string value. Key: pk"
    )
    err["Code"].should.equal("ValidationException")

    # Empty SortKey throws an error
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        with table.batch_writer() as batch:
            batch.put_item(Item={"pk": "sth", "sk": ""})
    err = exc.value.response["Error"]
    err["Message"].should.equal(
        "One or more parameter values are not valid. The AttributeValue for a key attribute cannot contain an empty string value. Key: sk"
    )
    err["Code"].should.equal("ValidationException")

    # Empty regular parameter workst just fine though
    with table.batch_writer() as batch:
        batch.put_item(Item={"pk": "sth", "sk": "else", "par": ""})


@mock_dynamodb
def test_query_begins_with_without_brackets():
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="test-table",
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
    )
    with pytest.raises(ClientError) as exc:
        client.query(
            TableName="test-table",
            KeyConditionExpression="pk=:pk AND begins_with sk, :sk ",
            ExpressionAttributeValues={":pk": {"S": "test1"}, ":sk": {"S": "test2"}},
        )
    err = exc.value.response["Error"]
    err["Message"].should.equal(
        'Invalid KeyConditionExpression: Syntax error; token: "sk"'
    )
    err["Code"].should.equal("ValidationException")


@mock_dynamodb
def test_transact_write_items_multiple_operations_fail():

    # Setup
    schema = {
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
    }
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    table_name = "test-table"
    dynamodb.create_table(TableName=table_name, BillingMode="PAY_PER_REQUEST", **schema)

    # Execute
    with pytest.raises(ClientError) as exc:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "Item": {"id": {"S": "test"}},
                        "TableName": table_name,
                    },
                    "Delete": {
                        "Key": {"id": {"S": "test"}},
                        "TableName": table_name,
                    },
                }
            ]
        )
    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "TransactItems can only contain one of Check, Put, Update or Delete"
    )


@mock_dynamodb
def test_update_primary_key_with_sortkey():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    schema = {
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
    }
    dynamodb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **schema
    )

    table = dynamodb.Table("test-table")
    base_item = {"pk": "testchangepk", "sk": "else"}
    table.put_item(Item=base_item)

    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"pk": "n/a", "sk": "else"},
            UpdateExpression="SET #attr1 = :val1",
            ExpressionAttributeNames={"#attr1": "pk"},
            ExpressionAttributeValues={":val1": "different"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Cannot update attribute pk. This attribute is part of the key"
    )

    table.get_item(Key={"pk": "testchangepk", "sk": "else"})["Item"].should.equal(
        {"pk": "testchangepk", "sk": "else"}
    )


@mock_dynamodb
def test_update_primary_key():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    schema = {
        "KeySchema": [{"AttributeName": "pk", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "pk", "AttributeType": "S"}],
    }
    dynamodb.create_table(
        TableName="without_sk", BillingMode="PAY_PER_REQUEST", **schema
    )

    table = dynamodb.Table("without_sk")
    base_item = {"pk": "testchangepk"}
    table.put_item(Item=base_item)

    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"pk": "n/a"},
            UpdateExpression="SET #attr1 = :val1",
            ExpressionAttributeNames={"#attr1": "pk"},
            ExpressionAttributeValues={":val1": "different"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Cannot update attribute pk. This attribute is part of the key"
    )

    table.get_item(Key={"pk": "testchangepk"})["Item"].should.equal(
        {"pk": "testchangepk"}
    )


@mock_dynamodb
def test_put_item__string_as_integer_value():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to mock a session with Config in ServerMode")
    session = botocore.session.Session()
    config = botocore.client.Config(parameter_validation=False)
    client = session.create_client("dynamodb", region_name="us-east-1", config=config)
    client.create_table(
        TableName="without_sk",
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )
    with pytest.raises(ClientError) as exc:
        client.put_item(TableName="without_sk", Item={"pk": {"S": 123}})
    err = exc.value.response["Error"]
    err["Code"].should.equal("SerializationException")
    err["Message"].should.equal("NUMBER_VALUE cannot be converted to String")

    with pytest.raises(ClientError) as exc:
        client.put_item(TableName="without_sk", Item={"pk": {"S": {"S": "asdf"}}})
    err = exc.value.response["Error"]
    err["Code"].should.equal("SerializationException")
    err["Message"].should.equal("Start of structure or map found where not expected")


@mock_dynamodb
def test_gsi_key_cannot_be_empty():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    hello_index = {
        "IndexName": "hello-index",
        "KeySchema": [{"AttributeName": "hello", "KeyType": "HASH"}],
        "Projection": {"ProjectionType": "ALL"},
    }
    table_name = "lilja-test"

    # Let's create a table with [id: str, hello: str], with an index to hello
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "hello", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[hello_index],
        BillingMode="PAY_PER_REQUEST",
    )

    table = dynamodb.Table(table_name)
    with pytest.raises(ClientError) as exc:
        table.put_item(
            TableName=table_name,
            Item={
                "id": "woop",
                "hello": None,
            },
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "One or more parameter values were invalid: Type mismatch for Index Key hello Expected: S Actual: NULL IndexName: hello-index"
    )
