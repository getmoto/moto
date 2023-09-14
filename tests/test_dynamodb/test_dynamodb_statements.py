import boto3

from moto import mock_dynamodb
from unittest import TestCase


class TestSelectStatements:
    mock = mock_dynamodb()

    @classmethod
    def setup_class(cls):
        cls.mock.start()
        cls.client = boto3.client("dynamodb", "us-east-1")
        cls.client.create_table(
            TableName="messages",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
        )
        cls.item1 = {"id": {"S": "msg1"}, "body": {"S": "some text"}}
        cls.item2 = {"id": {"S": "msg2"}, "body": {"S": "n/a"}, "unique": {"S": "key"}}
        cls.client.put_item(TableName="messages", Item=cls.item1)
        cls.client.put_item(TableName="messages", Item=cls.item2)

    @classmethod
    def teardown_class(cls):
        try:
            cls.mock.stop()
        except RuntimeError:
            pass

    def test_execute_statement_select_star(self):
        items = TestSelectStatements.client.execute_statement(
            Statement="select * from messages"
        )["Items"]
        assert TestSelectStatements.item1 in items
        assert TestSelectStatements.item2 in items

    def test_execute_statement_select_unique(self):
        items = TestSelectStatements.client.execute_statement(
            Statement="select unique from messages"
        )["Items"]
        assert {} in items
        assert {"unique": {"S": "key"}} in items

    def test_execute_statement_with_parameter(self):
        stmt = "select * from messages where id = ?"
        items = TestSelectStatements.client.execute_statement(
            Statement=stmt, Parameters=[{"S": "msg1"}]
        )["Items"]
        assert len(items) == 1
        assert TestSelectStatements.item1 in items

        stmt = "select id from messages where id = ?"
        items = TestSelectStatements.client.execute_statement(
            Statement=stmt, Parameters=[{"S": "msg1"}]
        )["Items"]
        assert len(items) == 1
        assert {"id": {"S": "msg1"}} in items

    def test_execute_statement_with_no_results(self):
        stmt = "select * from messages where id = ?"
        items = TestSelectStatements.client.execute_statement(
            Statement=stmt, Parameters=[{"S": "msg3"}]
        )["Items"]
        assert items == []


@mock_dynamodb
class TestExecuteTransaction(TestCase):
    def setUp(self):
        self.client = boto3.client("dynamodb", "us-east-1")
        self.client.create_table(
            TableName="messages",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
        )
        self.item1 = {"id": {"S": "msg1"}, "body": {"S": "some text"}}
        self.item2 = {"id": {"S": "msg2"}, "body": {"S": "n/a"}, "unique": {"S": "key"}}
        self.client.put_item(TableName="messages", Item=self.item1)
        self.client.put_item(TableName="messages", Item=self.item2)

    def test_execute_transaction(self):
        items = self.client.execute_transaction(
            TransactStatements=[
                {"Statement": "select id from messages"},
                {
                    "Statement": "select * from messages where id = ?",
                    "Parameters": [{"S": "msg2"}],
                },
            ]
        )["Responses"]
        assert len(items) == 3


@mock_dynamodb
class TestBatchExecuteStatement(TestCase):
    def setUp(self):
        self.client = boto3.client("dynamodb", "us-east-1")
        for name in ["table1", "table2"]:
            self.client.create_table(
                TableName=name,
                KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
                ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
            )
        self.item1 = {"id": {"S": "msg1"}, "body": {"S": "some text"}}
        self.item2 = {"id": {"S": "msg2"}, "body": {"S": "n/a"}, "unique": {"S": "key"}}
        self.client.put_item(TableName="table1", Item=self.item1)
        self.client.put_item(TableName="table1", Item=self.item2)
        self.client.put_item(TableName="table2", Item=self.item1)

    def test_execute_transaction(self):
        items = self.client.batch_execute_statement(
            Statements=[
                {
                    "Statement": "select id from table1 where id = ?",
                    "Parameters": [{"S": "msg1"}],
                },
                {
                    "Statement": "select * from table2 where id = ?",
                    "Parameters": [{"S": "msg1"}],
                },
                {
                    "Statement": "select * from table2 where id = ?",
                    "Parameters": [{"S": "msg2"}],
                },
            ]
        )["Responses"]
        assert len(items) == 3
        assert {"TableName": "table1", "Item": {"id": {"S": "msg1"}}} in items
        assert {"TableName": "table2", "Item": self.item1} in items
        assert {"TableName": "table2"} in items

    def test_without_primary_key_in_where_clause(self):
        items = self.client.batch_execute_statement(
            Statements=[
                # Unknown table
                {"Statement": "select id from unknown-table"},
                # No WHERE-clause
                {"Statement": "select id from table1"},
                # WHERE-clause does not contain HashKey
                {
                    "Statement": "select * from table1 where body = ?",
                    "Parameters": [{"S": "msg1"}],
                },
                # Valid WHERE-clause
                {
                    "Statement": "select * from table2 where id = ?",
                    "Parameters": [{"S": "msg1"}],
                },
            ]
        )["Responses"]
        assert len(items) == 4
        assert {
            "Error": {
                "Code": "ResourceNotFound",
                "Message": "Requested resource not found",
            }
        } in items
        assert {
            "Error": {
                "Code": "ValidationError",
                "Message": "Select statements within BatchExecuteStatement must "
                "specify the primary key in the where clause.",
            },
            "TableName": "table1",
        } in items
        assert {
            "Error": {
                "Code": "ValidationError",
                "Message": "Select statements within BatchExecuteStatement must "
                "specify the primary key in the where clause.",
            },
            "TableName": "table1",
        } in items
        assert {"TableName": "table2", "Item": self.item1} in items
