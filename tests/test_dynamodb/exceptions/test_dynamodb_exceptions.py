from unittest import SkipTest
from uuid import uuid4

import boto3
import botocore
import pytest
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from tests import allow_aws_request
from tests.test_dynamodb import dynamodb_aws_verified

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


class BaseTest:
    @classmethod
    def setup_class(cls, add_range=False):
        if not allow_aws_request():
            cls.mock = mock_aws()
            cls.mock.start()
        cls.client = boto3.client("dynamodb", region_name="us-east-1")
        cls.table_name = "T" + str(uuid4())[0:6]
        cls.has_range_key = add_range

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create the DynamoDB table.
        schema = [{"AttributeName": "pk", "KeyType": "HASH"}]
        defs = [{"AttributeName": "pk", "AttributeType": "S"}]
        if add_range:
            schema.append({"AttributeName": "rk", "KeyType": "RANGE"})
            defs.append({"AttributeName": "rk", "AttributeType": "S"})
        dynamodb.create_table(
            TableName=cls.table_name,
            KeySchema=schema,
            AttributeDefinitions=defs,
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        waiter = cls.client.get_waiter("table_exists")
        waiter.wait(TableName=cls.table_name)
        cls.table = dynamodb.Table(cls.table_name)

    def setup_method(self):
        # Empty table between runs
        items = self.table.scan()["Items"]
        for item in items:
            if self.has_range_key:
                self.table.delete_item(Key={"pk": item["pk"], "rk": item["rk"]})
            else:
                self.table.delete_item(Key={"pk": item["pk"]})

    @classmethod
    def teardown_class(cls):
        cls.client.delete_table(TableName=cls.table_name)
        if not allow_aws_request():
            cls.mock.stop()


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Query condition missed key schema element: gsiK1SortKey"

    # check using wrong name for partition key throws exception
    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression="wrongName = :pk AND gsiK1SortKey = :sk",
            ExpressionAttributeValues={":pk": "gsi-pk", ":sk": "gsi-sk"},
            IndexName="GSI-K1",
        )["Items"]
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"] == "Query condition missed key schema element: gsiK1PartitionKey"
    )

    # verify same behaviour for begins_with
    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression="gsiK1PartitionKey = :pk AND begins_with ( wrongName , :sk )",
            ExpressionAttributeValues={":pk": "gsi-pk", ":sk": "gsi-sk"},
            IndexName="GSI-K1",
        )["Items"]
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Query condition missed key schema element: gsiK1SortKey"

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
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Query condition missed key schema element: gsiK1SortKey"


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Query condition missed key schema element: partitionKey"


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_empty_expressionattributenames(table_name=None):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table(table_name)
    with pytest.raises(ClientError) as exc:
        # Note: provided key is wrong
        # Empty ExpressionAttributeName is verified earlier, so that's the error we get
        table.get_item(Key={"id": "my_id"}, ExpressionAttributeNames={})
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "ExpressionAttributeNames can only be specified when using expressions"
    )


@mock_aws
def test_empty_expressionattributenames_with_empty_projection():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = ddb.Table("test-table")
    with pytest.raises(ClientError) as exc:
        table.get_item(
            Key={"id": "my_id"}, ProjectionExpression="a", ExpressionAttributeNames={}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "ExpressionAttributeNames must not be empty"


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "ExpressionAttributeNames must not be empty"


@pytest.mark.aws_verified
class TestUpdateExpressionClausesWithClashingExpressions(BaseTest):
    def test_multiple_add_clauses(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "the-key"},
                UpdateExpression="ADD x :one SET a = :a ADD y :one",
                ExpressionAttributeValues={":one": 1, ":a": "lore ipsum"},
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert (
            err["Message"]
            == 'Invalid UpdateExpression: The "ADD" section can only be used once in an update expression;'
        )

    def test_multiple_remove_clauses(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "the-key"},
                UpdateExpression="REMOVE #ulist[0] SET current_user = :current_user REMOVE some_param",
                ExpressionAttributeNames={"#ulist": "user_list"},
                ExpressionAttributeValues={":current_user": {"name": "Jane"}},
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert (
            err["Message"]
            == 'Invalid UpdateExpression: The "REMOVE" section can only be used once in an update expression;'
        )

    def test_multiple_set_clauses(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "the-key"},
                UpdateExpression="SET current_user = :current_user SET some_param = :current_user",
                ExpressionAttributeValues={":current_user": {"name": "Jane"}},
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert (
            err["Message"]
            == 'Invalid UpdateExpression: The "SET" section can only be used once in an update expression;'
        )

    def test_delete_and_add_on_same_set(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "foo"},
                UpdateExpression="ADD #stringSet :addSet DELETE #stringSet :deleteSet",
                ExpressionAttributeNames={"#stringSet": "string_set"},
                ExpressionAttributeValues={":addSet": {"c"}, ":deleteSet": {"a"}},
            )
        assert exc.value.response["Error"]["Code"] == "ValidationException"
        assert exc.value.response["Error"]["Message"].startswith(
            "Invalid UpdateExpression: Two document paths overlap with each other;"
        )

    def test_remove_and_add_on_same_set(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "foo"},
                UpdateExpression="ADD #stringSet :addSet REMOVE #stringSet",
                ExpressionAttributeNames={"#stringSet": "string_set.nested"},
                ExpressionAttributeValues={":addSet": {"c"}},
            )
        assert exc.value.response["Error"]["Code"] == "ValidationException"
        assert exc.value.response["Error"]["Message"].startswith(
            "Invalid UpdateExpression: Two document paths overlap with each other;"
        )

    def test_set_and_remove_on_overlapping_paths(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "foo"},
                UpdateExpression="REMOVE string_set SET string_set.nested = :h",
                ExpressionAttributeValues={":h": "H"},
            )
        assert exc.value.response["Error"]["Code"] == "ValidationException"
        assert exc.value.response["Error"]["Message"].startswith(
            "Invalid UpdateExpression: Two document paths overlap with each other;"
        )

    def test_set_path_overlap(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "foo"},
                UpdateExpression="SET string_set = :h, string_set.nested = :h",
                ExpressionAttributeValues={":h": "H"},
            )
        assert exc.value.response["Error"]["Code"] == "ValidationException"
        assert exc.value.response["Error"]["Message"].startswith(
            "Invalid UpdateExpression: Two document paths overlap with each other;"
        )

    def test_path_overlap_error_uses_expression_attribute_name(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "foo"},
                UpdateExpression="SET #stringSet = :h, #stringSet = :h",
                ExpressionAttributeNames={"#stringSet": "string_set"},
                ExpressionAttributeValues={":h": "H"},
            )
        assert exc.value.response["Error"]["Code"] == "ValidationException"
        assert (
            exc.value.response["Error"]["Message"]
            == "Invalid UpdateExpression: Two document paths overlap with each other; must remove or rewrite one of these paths; path one: [string_set], path two: [string_set]"
        )

    def test_path_overlap_error_splits_paths(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "foo"},
                UpdateExpression="SET string_set.nested = :h, string_set.nested = :h",
                ExpressionAttributeValues={":h": "H"},
            )
        assert exc.value.response["Error"]["Code"] == "ValidationException"
        assert (
            exc.value.response["Error"]["Message"]
            == "Invalid UpdateExpression: Two document paths overlap with each other; must remove or rewrite one of these paths; path one: [string_set, nested], path two: [string_set, nested]"
        )

    # pretty weird AWS behavior with the next two tests, seems like a bug
    def test_no_overlapping_paths_error_if_one_of_the_overlapping_paths_is_an_expression_attribute_name(
        self,
    ):
        self.table.update_item(
            Key={"pk": "foo"},
            UpdateExpression="SET string_set = :h, #nested = :h",
            ExpressionAttributeNames={"#nested": "string_set.nested"},
            ExpressionAttributeValues={":h": "H"},
        )

    def test_overlapping_paths_error_if_identical_paths_are_expression_attribute_names(
        self,
    ):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "foo"},
                UpdateExpression="SET #stringSet = :h, #nested = :h",
                ExpressionAttributeNames={
                    "#stringSet": "string_set",
                    "#nested": "string_set",
                },
                ExpressionAttributeValues={":h": "H"},
            )
        assert exc.value.response["Error"]["Code"] == "ValidationException"
        assert exc.value.response["Error"]["Message"].startswith(
            "Invalid UpdateExpression: Two document paths overlap with each other;"
        )

    def test_update_item_with_shared_root_but_different_overall(self):
        # Can update an item where the first part of the expressions is duplicate but not the rest
        nested = {"key1": "value1", "key2": "value2", "key3": "value3"}
        item = {"pk": "1", "name": "test", "nested": nested}
        self.table.put_item(Item=item)
        self.table.update_item(
            Key={"pk": "1"},
            UpdateExpression="SET #root.#child1=:key1,#root.#child2=:key2",
            ExpressionAttributeNames={
                "#root": "nested",
                "#child1": "key1",
                "#child2": "key2",
            },
            ExpressionAttributeValues={":key1": "new value1", ":key2": "new value2"},
        )
        item = self.table.get_item(Key={"pk": "1"})["Item"]
        assert item["nested"] == {
            "key1": "new value1",
            "key2": "new value2",
            "key3": "value3",
        }

    def test_delete_and_add_on_different_set(self):
        self.table.update_item(
            Key={"pk": "the-key"},
            UpdateExpression="ADD #stringSet1 :addSet DELETE #stringSet2 :deleteSet",
            ExpressionAttributeNames={"#stringSet1": "ss1", "#stringSet2": "ss2"},
            ExpressionAttributeValues={":addSet": {"c"}, ":deleteSet": {"a"}},
        )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_update_item_unused_attribute_name(table_name=None):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = ddb.Table(table_name)
    table.put_item(Item={"pk": "pk1", "spec": {}, "am": 0})

    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"pk": "pk1"},
            UpdateExpression="SET spec.#limit = :limit",
            ExpressionAttributeNames={"#count": "count", "#limit": "limit"},
            ExpressionAttributeValues={":countChange": 1, ":limit": "limit"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )

    with pytest.raises(ClientError) as exc:
        table.update_item(
            Key={"pk": "pk1"},
            UpdateExpression="ADD am :limit",
            ExpressionAttributeNames={"#count": "count"},
            ExpressionAttributeValues={":limit": 2},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_put_item_unused_attribute_name(table_name=None):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")

    table = ddb.Table(table_name)

    with pytest.raises(ClientError) as exc:
        table.put_item(
            Item={"pk": "pk1", "spec": {}, "am": 0},
            ConditionExpression="attribute_not_exists(body)",
            ExpressionAttributeNames={"#count": "count"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_get_item_unused_attribute_name(table_name=None):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")

    table = ddb.Table(table_name)

    with pytest.raises(ClientError) as exc:
        table.get_item(
            Key={"pk": "example_id"},
            ProjectionExpression="pk",
            ExpressionAttributeNames={"#count": "count"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_query_unused_attribute_name(table_name=None):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")

    table = ddb.Table(table_name)

    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression="(#0 = x) AND (begins_with(#1, a))",
            ExpressionAttributeNames={"#0": "pk", "#1": "sk", "#count": "count"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_scan_unused_attribute_name(table_name=None):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")

    table = ddb.Table(table_name)

    with pytest.raises(ClientError) as exc:
        table.scan(
            TableName=table_name,
            FilterExpression="#h = :h",
            ExpressionAttributeNames={"#h": "pk", "#count": "count"},
            ExpressionAttributeValues={":h": {"S": "hash_value"}},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_delete_unused_attribute_name(table_name=None):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")

    table = ddb.Table(table_name)

    with pytest.raises(ClientError) as exc:
        table.delete_item(
            Key={"pk": "pk1"},
            ConditionExpression="attribute_not_exists(body)",
            ExpressionAttributeNames={"#count": "count"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_batch_get_item_unused_attribute_name(table_name=None):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        ddb.batch_get_item(
            RequestItems={
                "users": {
                    "Keys": [
                        {"username": {"S": "user0"}},
                        {"username": {"S": "user1"}},
                        {"username": {"S": "user2"}},
                        {"username": {"S": "user3"}},
                    ],
                    "ConsistentRead": True,
                    "ProjectionExpression": "#rl",
                    "ExpressionAttributeNames": {"#rl": "username", "#count": "count"},
                }
            }
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_transact_write_item_put_unused_attribute_name(table_name=None):
    ddb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        ddb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "Item": {
                            "pk": {"S": "foo"},
                            "foo": {"S": "bar"},
                        },
                        "TableName": table_name,
                        "ConditionExpression": "#i <> foo",
                        "ExpressionAttributeNames": {"#i": "pk", "#count": "count"},
                    },
                }
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_transact_write_item_update_unused_attribute_name(table_name=None):
    ddb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        ddb.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "Key": {"id": {"S": "foo"}},
                        "TableName": table_name,
                        "UpdateExpression": "SET #e = test",
                        "ExpressionAttributeNames": {
                            "#e": "email_address",
                            "#count": "count",
                        },
                    }
                }
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_transact_write_item_delete_unused_attribute_name(table_name=None):
    ddb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        ddb.transact_write_items(
            TransactItems=[
                {
                    "Delete": {
                        "Key": {
                            "pk": {"S": "foo"},
                            "foo": {"S": "bar"},
                        },
                        "TableName": table_name,
                        "ConditionExpression": "#i <> foo",
                        "ExpressionAttributeNames": {"#i": "pk", "#count": "count"},
                    },
                }
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_transact_write_item_unused_attribute_name_in_condition_check(table_name=None):
    ddb = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        ddb.transact_write_items(
            TransactItems=[
                {
                    "ConditionCheck": {
                        "Key": {"id": {"S": "foo"}},
                        "TableName": table_name,
                        "ConditionExpression": "attribute_exists(#e)",
                        "ExpressionAttributeNames": {
                            "#e": "email_address",
                            "#count": "count",
                        },
                    }
                },
                {
                    "Put": {
                        "Item": {
                            "id": {"S": "bar"},
                            "email_address": {"S": "bar@moto.com"},
                        },
                        "TableName": table_name,
                    }
                },
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Value provided in ExpressionAttributeNames unused in expressions: keys: {#count}"
    )


@mock_aws
def test_batch_get_item_non_existing_table():
    client = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.batch_get_item(RequestItems={"my-table": {"Keys": [{"id": {"N": "0"}}]}})
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Requested resource not found"


@mock_aws
def test_batch_write_item_non_existing_table():
    client = boto3.client("dynamodb", region_name="us-west-2")

    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        # Table my-table does not exist
        client.batch_write_item(
            RequestItems={"my-table": [{"PutRequest": {"Item": {}}}]}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Requested resource not found"


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Number of attributes in KeySchema does not exactly match number of attributes defined in AttributeDefinitions"
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Some AttributeDefinitions are not used. AttributeDefinitions: [created_at, id, user], keys used: [id, user]"
    )


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Invalid KeySchema: Some index key attribute have no definition"
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Some index key attributes are not defined in AttributeDefinitions. Keys: [user], AttributeDefinitions: [id]"
    )


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Some index key attributes are not defined in AttributeDefinitions. Keys: [id], AttributeDefinitions: [created_at]"
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Some index key attributes are not defined in AttributeDefinitions. Keys: [user], AttributeDefinitions: [created_at, id]"
    )


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Type mismatch for key id expected: S actual: N"
    )

    item = {
        "id": {"S": "some id"},
        "created_at": {"S": "should be date not string"},
        "someAttribute": {"S": "lore ipsum"},
    }

    with pytest.raises(ClientError) as exc:
        dynamodb.put_item(TableName="test-table", Item=item)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Type mismatch for key created_at expected: N actual: S"
    )


@mock_aws
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
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == "Query key condition not supported"


# Test this again, but with manually supplying an operator
@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Query key condition not supported"


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: List of LocalSecondaryIndexes is empty"
    )


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: List of GlobalSecondaryIndexes is empty"
    )


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Transaction request cannot include multiple operations on one item"
    )


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected at 'transactItems' failed to satisfy constraint: Member must have length less than or equal to 100."
    )


@mock_aws
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
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Requested resource not found"


@pytest.mark.aws_verified
class TestDuplicateProjectionExpressions(BaseTest):
    def test_query_item_with_duplicate_path_in_projection_expressions(self):
        with pytest.raises(ClientError) as exc:
            TestDuplicateProjectionExpressions.table.query(
                KeyConditionExpression=Key("pk").eq("the-key"),
                ProjectionExpression="body, subject, body",  # duplicate body
            )
        self._validate(exc)

    def test_get_item_with_duplicate_path_in_projection_expressions(self):
        with pytest.raises(ClientError) as exc:
            TestDuplicateProjectionExpressions.table.get_item(
                Key={"pk": "the-key"},
                ProjectionExpression="#rl, #rt, subject, subject",  # duplicate subject
                ExpressionAttributeNames={"#rl": "body", "#rt": "attachment"},
            )
        self._validate(exc)

    def test_scan_with_duplicate_path_in_projection_expressions(self):
        with pytest.raises(ClientError) as exc:
            TestDuplicateProjectionExpressions.table.scan(
                FilterExpression=Key("forum_name").eq("the-key"),
                ProjectionExpression="#rl, #rt, subject, subject",  # duplicate subject
                ExpressionAttributeNames={"#rl": "body", "#rt": "attachment"},
            )
        self._validate(exc)

    def _validate(self, exc):
        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert "Invalid ProjectionExpression: " in err["Message"]
        assert (
            "Two document paths overlap with each other; must remove or rewrite one of these paths"
            in err["Message"]
        )


@mock_aws
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
    assert err["Code"] == "SerializationException"
    assert err["Message"] == "NUMBER_VALUE cannot be converted to String"

    # Same thing - but with a non-key, and nested
    with pytest.raises(ClientError) as exc:
        client.put_item(
            TableName="test2",
            Item={"mykey": {"N": "123"}, "nested": {"M": {"sth": {"N": 5}}}},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "SerializationException"
    assert err["Message"] == "NUMBER_VALUE cannot be converted to String"


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_put_item_empty_set(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    table = dynamodb.Table(table_name)
    with pytest.raises(ClientError) as exc:
        table.put_item(Item={"pk": "some-irrelevant_key", "attr2": {"SS": set([])}})
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: An number set  may not be empty"
    )

    with pytest.raises(ClientError) as exc:
        client.put_item(
            TableName=table_name, Item={"pk": {"S": "foo"}, "stringSet": {"SS": []}}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: An string set  may not be empty"
    )


@mock_aws
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
            Key={"pk": "key"},
            # Trailing comma should be invalid
            UpdateExpression="SET #attr1 = :val1, #attr2 = :val2,",
            ExpressionAttributeNames={"#attr1": "attr1", "#attr2": "attr2"},
            ExpressionAttributeValues={":val1": 3, ":val2": 4},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == 'Invalid UpdateExpression: Syntax error; token: "<EOF>", near: ","'
    )


@mock_aws
def test_batch_items_should_throw_exception_for_duplicate_request(
    ddb_resource, create_user_table, users_table_name
):
    # Setup
    table = ddb_resource.Table(users_table_name)
    test_item = {"forum_name": "test_dupe", "subject": "test1"}

    # Execute
    with pytest.raises(ClientError) as ex:
        with table.batch_writer() as batch:
            for i in range(0, 5):
                batch.put_item(Item=test_item)

    with pytest.raises(ClientError) as ex2:
        with table.batch_writer() as batch:
            for i in range(0, 5):
                batch.delete_item(Key=test_item)

    # Verify
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Provided list of item keys contains duplicates"

    err2 = ex2.value.response["Error"]
    assert err2["Code"] == "ValidationException"
    assert err2["Message"] == "Provided list of item keys contains duplicates"


@mock_aws
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
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = ddb.Table("test-table")

    # Empty Partition Key throws an error
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        with table.batch_writer() as batch:
            batch.put_item(Item={"pk": "", "sk": "sth"})
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == "One or more parameter values are not valid. The AttributeValue for a key attribute cannot contain an empty string value. Key: pk"
    )
    assert err["Code"] == "ValidationException"

    # Empty SortKey throws an error
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        with table.batch_writer() as batch:
            batch.put_item(Item={"pk": "sth", "sk": ""})
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == "One or more parameter values are not valid. The AttributeValue for a key attribute cannot contain an empty string value. Key: sk"
    )
    assert err["Code"] == "ValidationException"

    # Empty regular parameter workst just fine though
    with table.batch_writer() as batch:
        batch.put_item(Item={"pk": "sth", "sk": "else", "par": ""})


@mock_aws
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
    assert err["Message"] == 'Invalid KeyConditionExpression: Syntax error; token: "sk"'
    assert err["Code"] == "ValidationException"


@mock_aws
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


@mock_aws
def test_transact_write_items_with_empty_gsi_key():
    client = boto3.client("dynamodb", "us-east-2")

    client.create_table(
        TableName="test_table",
        KeySchema=[{"AttributeName": "unique_code", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "unique_code", "AttributeType": "S"},
            {"AttributeName": "unique_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "gsi_index",
                "KeySchema": [{"AttributeName": "unique_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    transact_items = [
        {
            "Put": {
                "Item": {"unique_code": {"S": "some code"}, "unique_id": {"S": ""}},
                "TableName": "test_table",
            }
        }
    ]

    with pytest.raises(ClientError) as exc:
        client.transact_write_items(TransactItems=transact_items)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values are not valid. A value specified for a secondary index key is not supported. The AttributeValue for a key attribute cannot contain an empty string value. IndexName: gsi_index, IndexKey: unique_id"
    )


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Cannot update attribute pk. This attribute is part of the key"
    )

    item = table.get_item(Key={"pk": "testchangepk", "sk": "else"})["Item"]
    assert item == {"pk": "testchangepk", "sk": "else"}


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Cannot update attribute pk. This attribute is part of the key"
    )

    item = table.get_item(Key={"pk": "testchangepk"})["Item"]
    assert item == {"pk": "testchangepk"}


@mock_aws
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
    assert err["Code"] == "SerializationException"
    assert err["Message"] == "NUMBER_VALUE cannot be converted to String"

    # A primary key cannot be of type S, but then point to a dictionary
    with pytest.raises(ClientError) as exc:
        client.put_item(TableName="without_sk", Item={"pk": {"S": {"S": "asdf"}}})
    err = exc.value.response["Error"]
    assert err["Code"] == "SerializationException"
    assert err["Message"] == "Start of structure or map found where not expected"

    # Note that a normal attribute name can be an 'S', which follows the same pattern
    # Nested 'S'-s like this are allowed for non-key attributes
    client.put_item(
        TableName="without_sk", Item={"pk": {"S": "val"}, "S": {"S": "asdf"}}
    )
    item = client.get_item(TableName="without_sk", Key={"pk": {"S": "val"}})["Item"]
    assert item == {"pk": {"S": "val"}, "S": {"S": "asdf"}}


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: Type mismatch for Index Key hello Expected: S Actual: NULL IndexName: hello-index"
    )


@mock_aws
def test_list_append_errors_for_unknown_attribute_value():
    # Verify whether the list_append operation works as expected
    client = boto3.client("dynamodb", region_name="us-east-1")

    client.create_table(
        AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
        TableName="table2",
        KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    client.put_item(
        TableName="table2",
        Item={"key": {"S": "sha-of-file"}, "crontab": {"L": [{"S": "bar1"}]}},
    )

    # append to unknown list directly
    with pytest.raises(ClientError) as exc:
        client.update_item(
            TableName="table2",
            Key={"key": {"S": "sha-of-file"}},
            UpdateExpression="SET uk = list_append(uk, :i)",
            ExpressionAttributeValues={":i": {"L": [{"S": "bar2"}]}},
            ReturnValues="UPDATED_NEW",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "The provided expression refers to an attribute that does not exist in the item"
    )

    # append to unknown list via ExpressionAttributeNames
    with pytest.raises(ClientError) as exc:
        client.update_item(
            TableName="table2",
            Key={"key": {"S": "sha-of-file"}},
            UpdateExpression="SET #0 = list_append(#0, :i)",
            ExpressionAttributeNames={"#0": "uk"},
            ExpressionAttributeValues={":i": {"L": [{"S": "bar2"}]}},
            ReturnValues="UPDATED_NEW",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "The provided expression refers to an attribute that does not exist in the item"
    )

    # append to unknown list, even though end result is known
    with pytest.raises(ClientError) as exc:
        client.update_item(
            TableName="table2",
            Key={"key": {"S": "sha-of-file"}},
            UpdateExpression="SET crontab = list_append(uk, :i)",
            ExpressionAttributeValues={":i": {"L": [{"S": "bar2"}]}},
            ReturnValues="UPDATED_NEW",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "The provided expression refers to an attribute that does not exist in the item"
    )

    # We can append to a known list, into an unknown/new list
    client.update_item(
        TableName="table2",
        Key={"key": {"S": "sha-of-file"}},
        UpdateExpression="SET uk = list_append(crontab, :i)",
        ExpressionAttributeValues={":i": {"L": [{"S": "bar2"}]}},
        ReturnValues="UPDATED_NEW",
    )


@mock_aws
def test_query_with_empty_filter_expression():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="test-table", BillingMode="PAY_PER_REQUEST", **table_schema
    )
    table = ddb.Table("test-table")
    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression="partitionKey = sth", ProjectionExpression=""
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Invalid ProjectionExpression: The expression can not be empty;"
    )

    with pytest.raises(ClientError) as exc:
        table.query(KeyConditionExpression="partitionKey = sth", FilterExpression="")
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"] == "Invalid FilterExpression: The expression can not be empty;"
    )


@mock_aws
def test_query_with_missing_expression_attribute():
    ddb = boto3.resource("dynamodb", region_name="us-west-2")
    ddb.create_table(TableName="test", BillingMode="PAY_PER_REQUEST", **table_schema)
    client = boto3.client("dynamodb", region_name="us-west-2")
    with pytest.raises(ClientError) as exc:
        client.query(
            TableName="test",
            KeyConditionExpression="#part_key=some_value",
            ExpressionAttributeNames={"#part_key": "partitionKey"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Invalid condition in KeyConditionExpression: Multiple attribute names used in one condition"
    )


@pytest.mark.aws_verified
class TestReturnValuesOnConditionCheckFailure(BaseTest):
    def setup_method(self):
        super().setup_method()
        self.table.put_item(
            Item={"pk": "the-key", "subject": "123", "body": "some test msg"}
        )

    def test_put_item_does_not_return_old_item(self):
        with pytest.raises(ClientError) as exc:
            self.table.put_item(
                Item={"pk": "the-key", "bar": "quuz"},
                ConditionExpression="attribute_not_exists(body)",
            )
        self._assert_without_return_values(exc)

    def test_put_item_returns_old_item(self):
        with pytest.raises(ClientError) as exc:
            self.table.put_item(
                Item={"pk": "the-key", "bar": "quuz"},
                ReturnValuesOnConditionCheckFailure="ALL_OLD",
                ConditionExpression="attribute_not_exists(body)",
            )
        self._assert_with_return_values(exc)

    def test_update_item_does_not_return_old_item(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "the-key"},
                UpdateExpression="set #lock = :lock",
                ExpressionAttributeNames={"#lock": "lock"},
                ExpressionAttributeValues={":lock": "sth"},
                ConditionExpression="attribute_exists(#lock)",
            )
        self._assert_without_return_values(exc)

    def test_update_item_returns_old_item(self):
        with pytest.raises(ClientError) as exc:
            self.table.update_item(
                Key={"pk": "the-key"},
                UpdateExpression="set #lock = :lock",
                ExpressionAttributeNames={"#lock": "lock"},
                ExpressionAttributeValues={":lock": "sth"},
                ReturnValuesOnConditionCheckFailure="ALL_OLD",
                ConditionExpression="attribute_exists(#lock)",
            )
        self._assert_with_return_values(exc)

    def test_delete_item_does_not_return_old_item(self):
        with pytest.raises(ClientError) as exc:
            self.table.delete_item(
                Key={"pk": "the-key"},
                ExpressionAttributeNames={"#lock": "lock"},
                ConditionExpression="attribute_exists(#lock)",
            )
        self._assert_without_return_values(exc)

    def test_delete_item_returns_old_item(self):
        with pytest.raises(ClientError) as exc:
            self.table.delete_item(
                Key={"pk": "the-key"},
                ExpressionAttributeNames={"#lock": "lock"},
                ReturnValuesOnConditionCheckFailure="ALL_OLD",
                ConditionExpression="attribute_exists(#lock)",
            )
        self._assert_with_return_values(exc)

    def _assert_without_return_values(self, exc):
        resp = exc.value.response
        assert resp["Error"] == {
            "Message": "The conditional request failed",
            "Code": "ConditionalCheckFailedException",
        }
        assert resp["message"] == "The conditional request failed"
        assert "Item" not in resp

    def _assert_with_return_values(self, exc):
        resp = exc.value.response
        assert resp["Error"] == {
            "Message": "The conditional request failed",
            "Code": "ConditionalCheckFailedException",
        }
        assert "message" not in resp
        assert resp["Item"] == {
            "pk": {"S": "the-key"},
            "body": {"S": "some test msg"},
            "subject": {"S": "123"},
        }


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_delete_item_returns_old_item(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)
    table.put_item(Item={"pk": "mark", "lock": {"acquired_at": 123}})


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_scan_with_missing_value(table_name=None):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    with pytest.raises(ClientError) as exc:
        table.scan(
            FilterExpression="attr = loc",
            # Missing ':'
            ExpressionAttributeValues={"loc": "sth"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == 'ExpressionAttributeValues contains invalid key: Syntax error; key: "loc"'
    )

    with pytest.raises(ClientError) as exc:
        table.query(
            KeyConditionExpression="attr = loc",
            # Missing ':'
            ExpressionAttributeValues={"loc": "sth"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == 'ExpressionAttributeValues contains invalid key: Syntax error; key: "loc"'
    )


@mock_aws
def test_too_many_key_schema_attributes():
    ddb = boto3.resource("dynamodb", "us-east-1")
    TableName = "my_test_"

    AttributeDefinitions = [
        {"AttributeName": "UUID", "AttributeType": "S"},
        {"AttributeName": "ComicBook", "AttributeType": "S"},
    ]

    KeySchema = [
        {"AttributeName": "UUID", "KeyType": "HASH"},
        {"AttributeName": "ComicBook", "KeyType": "RANGE"},
        {"AttributeName": "Creator", "KeyType": "RANGE"},
    ]

    ProvisionedThroughput = {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}

    expected_err = "1 validation error detected: Value '[KeySchemaElement(attributeName=UUID, keyType=HASH), KeySchemaElement(attributeName=ComicBook, keyType=RANGE), KeySchemaElement(attributeName=Creator, keyType=RANGE)]' at 'keySchema' failed to satisfy constraint: Member must have length less than or equal to 2"
    with pytest.raises(ClientError) as exc:
        ddb.create_table(
            TableName=TableName,
            KeySchema=KeySchema,
            AttributeDefinitions=AttributeDefinitions,
            ProvisionedThroughput=ProvisionedThroughput,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == expected_err


@mock_aws
def test_cannot_query_gsi_with_consistent_read():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "gsi_hash_key", "AttributeType": "S"},
            {"AttributeName": "gsi_range_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [
                    {"AttributeName": "gsi_hash_key", "KeyType": "HASH"},
                    {"AttributeName": "gsi_range_key", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )

    with pytest.raises(ClientError) as exc:
        dynamodb.query(
            TableName="test",
            IndexName="test_gsi",
            KeyConditionExpression="gsi_hash_key = :gsi_hash_key and gsi_range_key = :gsi_range_key",
            ExpressionAttributeValues={
                ":gsi_hash_key": {"S": "key1"},
                ":gsi_range_key": {"S": "range1"},
            },
            ConsistentRead=True,
        )

    assert exc.value.response["Error"] == {
        "Code": "ValidationException",
        "Message": "Consistent reads are not supported on global secondary indexes",
    }


@mock_aws
def test_cannot_scan_gsi_with_consistent_read():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "gsi_hash_key", "AttributeType": "S"},
            {"AttributeName": "gsi_range_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [
                    {"AttributeName": "gsi_hash_key", "KeyType": "HASH"},
                    {"AttributeName": "gsi_range_key", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )

    with pytest.raises(ClientError) as exc:
        dynamodb.scan(
            TableName="test",
            IndexName="test_gsi",
            ConsistentRead=True,
        )

    assert exc.value.response["Error"] == {
        "Code": "ValidationException",
        "Message": "Consistent reads are not supported on global secondary indexes",
    }


@mock_aws
def test_delete_table():
    client = boto3.client("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    client.create_table(
        TableName="test1",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
        DeletionProtectionEnabled=True,
    )

    with pytest.raises(ClientError) as err:
        client.delete_table(TableName="test1")
    assert err.value.response["Error"]["Code"] == "ValidationException"
    assert (
        err.value.response["Error"]["Message"]
        == "1 validation error detected: Table 'test1' can't be deleted while DeletionProtectionEnabled is set to True"
    )


@pytest.mark.aws_verified
@dynamodb_aws_verified(add_range=False)
def test_provide_range_key_against_table_without_range_key(table_name=None):
    ddb_client = boto3.client("dynamodb", "us-east-1")
    with pytest.raises(ClientError) as exc:
        ddb_client.get_item(
            TableName=table_name, Key={"pk": {"S": "pk"}, "sk": {"S": "sk"}}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "The provided key element does not match the schema"

    with pytest.raises(ClientError) as exc:
        ddb_client.delete_item(
            TableName=table_name, Key={"pk": {"S": "pk"}, "sk": {"S": "sk"}}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "The provided key element does not match the schema"

    with pytest.raises(ClientError) as exc:
        ddb_client.update_item(
            TableName=table_name,
            Key={
                "pk": {"S": "x"},
                "ReceivedTime": {"S": "12/9/2011 11:36:03 PM"},
            },
            UpdateExpression="set body=:New",
            ExpressionAttributeValues={":New": {"S": "hello"}},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "The provided key element does not match the schema"
