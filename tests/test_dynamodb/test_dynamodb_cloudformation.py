import json
from copy import deepcopy

import boto3

from moto import mock_aws

template_create_table = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "table": {
            "Type": "AWS::DynamoDB::Table",
            "Properties": {
                "AttributeDefinitions": [
                    {"AttributeName": "Name", "AttributeType": "S"},
                    {"AttributeName": "Age", "AttributeType": "S"},
                ],
                "KeySchema": [
                    {"AttributeName": "Name", "KeyType": "HASH"},
                    {"AttributeName": "Age", "KeyType": "RANGE"},
                ],
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
                "TableName": "Person",
            },
        }
    },
}


@mock_aws
def test_create_stack_pay_per_request():
    conn = boto3.client("cloudformation", region_name="us-east-1")
    dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
    template = deepcopy(template_create_table)
    template["Resources"]["table"]["Properties"]["BillingMode"] = "PAY_PER_REQUEST"
    del template["Resources"]["table"]["Properties"]["ProvisionedThroughput"]

    conn.create_stack(StackName="test", TemplateBody=json.dumps(template))
    table_desc = dynamodb_client.list_tables()
    assert len(table_desc.get("TableNames")) == 1

    table = dynamodb_client.describe_table(TableName=table_desc["TableNames"][0])[
        "Table"
    ]
    assert table["BillingModeSummary"] == {"BillingMode": "PAY_PER_REQUEST"}


@mock_aws
def test_create_stack_with_indexes():
    conn = boto3.client("cloudformation", region_name="us-east-1")
    dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
    template = deepcopy(template_create_table)
    template["Resources"]["table"]["Properties"]["GlobalSecondaryIndexes"] = [
        {
            "IndexName": "gsi",
            "KeySchema": [{"AttributeName": "gsipk", "KeyType": "S"}],
            "Projection": {"ProjectionType": "ALL"},
        }
    ]
    template["Resources"]["table"]["Properties"]["LocalSecondaryIndexes"] = [
        {
            "IndexName": "lsi",
            "KeySchema": [{"AttributeName": "lsipk", "KeyType": "S"}],
            "Projection": {"ProjectionType": "ALL"},
        }
    ]

    conn.create_stack(StackName="test", TemplateBody=json.dumps(template))
    table_desc = dynamodb_client.list_tables()
    assert len(table_desc.get("TableNames")) == 1

    table = dynamodb_client.describe_table(TableName=table_desc["TableNames"][0])[
        "Table"
    ]
    assert len(table["GlobalSecondaryIndexes"]) == 1
    assert len(table["LocalSecondaryIndexes"]) == 1


@mock_aws
def test_delete_stack_dynamo_template():
    conn = boto3.client("cloudformation", region_name="us-east-1")
    dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")

    conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(template_create_table)
    )
    table_desc = dynamodb_client.list_tables()
    assert len(table_desc.get("TableNames")) == 1

    table = dynamodb_client.describe_table(TableName=table_desc["TableNames"][0])[
        "Table"
    ]
    assert table["ProvisionedThroughput"] == {
        "NumberOfDecreasesToday": 0,
        "ReadCapacityUnits": 5,
        "WriteCapacityUnits": 5,
    }
    assert table["BillingModeSummary"] == {"BillingMode": "PROVISIONED"}
    assert table["LocalSecondaryIndexes"] == []
    assert table["GlobalSecondaryIndexes"] == []
    assert table["DeletionProtectionEnabled"] is False

    conn.delete_stack(StackName="test_stack")
    table_desc = dynamodb_client.list_tables()
    assert len(table_desc.get("TableNames")) == 0

    conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(template_create_table)
    )
