import boto3
import json
import sure  # noqa

from moto import mock_cloudformation, mock_dynamodb2


template_create_table = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "myDynamoDBTable": {
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


@mock_dynamodb2
@mock_cloudformation
def test_delete_stack_dynamo_template_boto3():
    conn = boto3.client("cloudformation", region_name="us-east-1")
    dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")

    conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(template_create_table)
    )
    table_desc = dynamodb_client.list_tables()
    len(table_desc.get("TableNames")).should.equal(1)

    conn.delete_stack(StackName="test_stack")
    table_desc = dynamodb_client.list_tables()
    len(table_desc.get("TableNames")).should.equal(0)

    conn.create_stack(
        StackName="test_stack", TemplateBody=json.dumps(template_create_table)
    )
