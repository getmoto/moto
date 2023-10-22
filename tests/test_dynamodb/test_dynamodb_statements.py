import boto3
import pytest

from moto import mock_dynamodb
from unittest import TestCase

from . import dynamodb_aws_verified


item1 = {
    "pk": {"S": "msg1"},
    "body": {"S": "some text"},
    "nested_attrs": {"M": {"some": {"S": "key"}}},
    "price": {"N": "123.4"},
    "list_attrs": {"L": [{"BOOL": True}, {"BOOL": False}]},
    "bool_attr": {"BOOL": True},
}
item2 = {"pk": {"S": "msg2"}, "body": {"S": "n/a"}, "unique_key": {"S": "key"}}


def create_items(table_name):
    client = boto3.client("dynamodb", "us-east-1")
    client.put_item(TableName=table_name, Item=item1)
    client.put_item(TableName=table_name, Item=item2)


@pytest.mark.aws_verified
@dynamodb_aws_verified
def test_execute_statement_select_star(table_name=None):
    client = boto3.client("dynamodb", "us-east-1")
    create_items(table_name)
    items = client.execute_statement(Statement=f"select * from {table_name}")["Items"]
    assert item1 in items
    assert item2 in items


@pytest.mark.aws_verified
@dynamodb_aws_verified
def test_execute_statement_select_attr(table_name=None):
    client = boto3.client("dynamodb", "us-east-1")
    create_items(table_name)
    items = client.execute_statement(Statement=f"select unique_key from {table_name}")[
        "Items"
    ]
    assert {} in items
    assert {"unique_key": {"S": "key"}} in items


@pytest.mark.aws_verified
@dynamodb_aws_verified
def test_execute_statement_with_quoted_table(table_name=None):
    client = boto3.client("dynamodb", "us-east-1")
    create_items(table_name)
    items = client.execute_statement(Statement=f'select * from "{table_name}"')["Items"]
    assert item1 in items
    assert item2 in items


@pytest.mark.aws_verified
@dynamodb_aws_verified
def test_execute_statement_with_parameter(table_name=None):
    client = boto3.client("dynamodb", "us-east-1")
    create_items(table_name)
    stmt = f"select * from {table_name} where pk = ?"
    items = client.execute_statement(Statement=stmt, Parameters=[{"S": "msg1"}])[
        "Items"
    ]
    assert len(items) == 1
    assert item1 in items

    stmt = f"select pk from {table_name} where pk = ?"
    items = client.execute_statement(Statement=stmt, Parameters=[{"S": "msg1"}])[
        "Items"
    ]
    assert len(items) == 1
    assert {"pk": {"S": "msg1"}} in items


@pytest.mark.aws_verified
@dynamodb_aws_verified
def test_execute_statement_with_no_results(table_name=None):
    client = boto3.client("dynamodb", "us-east-1")
    create_items(table_name)
    stmt = f"select * from {table_name} where pk = ?"
    items = client.execute_statement(Statement=stmt, Parameters=[{"S": "msg3"}])[
        "Items"
    ]
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


@pytest.mark.aws_verified
@dynamodb_aws_verified
def test_execute_statement_with_all_clauses(table_name=None):
    dynamodb_client = boto3.client("dynamodb", "us-east-1")

    items = [
        {
            "pk": {"S": "0"},
            "Name": {"S": "Lambda"},
            "NameLower": {"S": "lambda"},
            "Description": {"S": "Run code in under 15 minutes"},
            "DescriptionLower": {"S": "run code in under 15 minutes"},
            "Price": {"N": "2E-7"},
            "Unit": {"S": "invocation"},
            "Category": {"S": "free"},
            "FreeTier": {"N": "1E+6"},
        },
        {
            "pk": {"S": "1"},
            "Name": {"S": "Auto Scaling"},
            "NameLower": {"S": "auto scaling"},
            "Description": {
                "S": "Automatically scale the number of EC2 instances with demand",
            },
            "DescriptionLower": {
                "S": "automatically scale the number of ec2 instances with demand"
            },
            "Price": {"N": "0"},
            "Unit": {"S": "group"},
            "Category": {"S": "free"},
            "FreeTier": {"NULL": True},
        },
        {
            "pk": {"S": "2"},
            "Name": {"S": "EC2"},
            "NameLower": {"S": "ec2"},
            "Description": {"S": "Servers in the cloud"},
            "DescriptionLower": {"S": "servers in the cloud"},
            "Price": {"N": "7.2"},
            "Unit": {"S": "instance"},
            "Category": {"S": "trial"},
        },
        {
            "pk": {"S": "3"},
            "Name": {"S": "Config"},
            "NameLower": {"S": "config"},
            "Description": {"S": "Audit the configuration of AWS resources"},
            "DescriptionLower": {"S": "audit the configuration of aws resources"},
            "Price": {"N": "0.003"},
            "Unit": {"S": "configuration item"},
            "Category": {"S": "paid"},
        },
    ]

    for item in items:
        dynamodb_client.put_item(TableName=table_name, Item=item)

    partiql_statement = f"SELECT pk FROM \"{table_name}\" WHERE (contains(\"NameLower\", 'code') OR contains(\"DescriptionLower\", 'code')) AND Category = 'free' AND Price >= 0 AND Price <= 1 AND FreeTier IS NOT MISSING AND attribute_type(\"FreeTier\", 'N')"
    items = dynamodb_client.execute_statement(Statement=partiql_statement)["Items"]
    assert items == [{"pk": {"S": "0"}}]
