import os
from functools import wraps
from uuid import uuid4

import boto3

from moto import mock_aws


def dynamodb_aws_verified(
    create_table: bool = True,
    add_range: bool = False,
    numeric_range: bool = False,
    add_gsi: bool = False,
    add_gsi_range: bool = False,
    add_lsi: bool = False,
    numeric_gsi_range: bool = False,
    numeric_lsi_range: bool = False,
):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.

    This decorator will:
      - Create a table
      - Run the test and pass the table_name as an argument
      - Delete the table
    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper():
            table_name = "t" + str(uuid4())[0:6]

            allow_aws_request = (
                os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
            )

            if allow_aws_request:
                if create_table:
                    print(f"Test {func} will create DDB Table {table_name}")  # noqa
                    return create_table_and_test(table_name)
                else:
                    return func()
            else:
                with mock_aws():
                    if create_table:
                        return create_table_and_test(table_name)
                    else:
                        return func()

        def create_table_and_test(table_name):
            client = boto3.client("dynamodb", region_name="us-east-1")

            range_type = "N" if numeric_range else "S"
            gsi_range_type = "N" if numeric_gsi_range else "S"
            lsi_range_type = "N" if numeric_lsi_range else "S"

            kwargs = {
                "KeySchema": [{"AttributeName": "pk", "KeyType": "HASH"}],
                "AttributeDefinitions": [{"AttributeName": "pk", "AttributeType": "S"}],
            }
            if add_range or numeric_range:
                kwargs["KeySchema"].append({"AttributeName": "sk", "KeyType": "RANGE"})
                kwargs["AttributeDefinitions"].append(
                    {"AttributeName": "sk", "AttributeType": range_type}
                )
            if add_gsi:
                kwargs["GlobalSecondaryIndexes"] = [
                    {
                        "IndexName": "test_gsi",
                        "KeySchema": [
                            {"AttributeName": "gsi_pk", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 1,
                            "WriteCapacityUnits": 1,
                        },
                    }
                ]
                kwargs["AttributeDefinitions"].append(
                    {"AttributeName": "gsi_pk", "AttributeType": "S"}
                )
            if add_gsi_range or numeric_gsi_range:
                kwargs["GlobalSecondaryIndexes"] = [
                    {
                        "IndexName": "test_gsi",
                        "KeySchema": [
                            {"AttributeName": "gsi_pk", "KeyType": "HASH"},
                            {"AttributeName": "gsi_sk", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 1,
                            "WriteCapacityUnits": 1,
                        },
                    }
                ]
                kwargs["AttributeDefinitions"].append(
                    {"AttributeName": "gsi_pk", "AttributeType": "S"}
                )
                kwargs["AttributeDefinitions"].append(
                    {"AttributeName": "gsi_sk", "AttributeType": gsi_range_type}
                )
            if add_lsi or numeric_lsi_range:
                kwargs["LocalSecondaryIndexes"] = [
                    {
                        "IndexName": "test_lsi",
                        "KeySchema": [
                            {"AttributeName": "pk", "KeyType": "HASH"},
                            {"AttributeName": "lsi_sk", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ]
                kwargs["AttributeDefinitions"].append(
                    {"AttributeName": "lsi_sk", "AttributeType": lsi_range_type}
                )
            client.create_table(
                TableName=table_name,
                ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
                Tags=[{"Key": "environment", "Value": "moto_tests"}],
                **kwargs,
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
