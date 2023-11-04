import boto3
import os
from functools import wraps
from moto import mock_dynamodb
from uuid import uuid4


def dynamodb_aws_verified(create_table: bool = True):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_dynamodb` context.

    This decorator will:
      - Create a table
      - Run the test and pass the table_name as an argument
      - Delete the table
    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper():
            client = boto3.client("dynamodb", region_name="us-east-1")
            table_name = "t" + str(uuid4())[0:6]

            allow_aws_request = (
                os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
            )

            if allow_aws_request:
                if create_table:
                    print(f"Test {func} will create DynamoDB Table {table_name}")
                    return create_table_and_test(table_name, client)
                else:
                    return func()
            else:
                with mock_dynamodb():
                    if create_table:
                        return create_table_and_test(table_name, client)
                    else:
                        return func()

        def create_table_and_test(table_name, client):
            client.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
                Tags=[{"Key": "environment", "Value": "moto_tests"}],
            )
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=table_name)
            try:
                resp = func(table_name)
            finally:
                ### CLEANUP ###
                client.delete_table(TableName=table_name)

            return resp

        return pagination_wrapper

    return inner
