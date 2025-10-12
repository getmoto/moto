import gzip
import json
from time import sleep
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from . import dynamodb_aws_verified


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_import_from_missing_s3_table(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")

    table_name = "t" + str(uuid4())[0:6]

    import_description = client.import_table(
        S3BucketSource={"S3Bucket": f"{uuid4()}"},
        InputFormat="DYNAMODB_JSON",
        InputCompressionType="NONE",
        TableCreationParameters={
            "TableName": table_name,
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
    )["ImportTableDescription"]

    import_details = wait_for_import(client, import_description)

    assert import_details["ImportStatus"] == "FAILED"
    assert import_details["TableArn"].endswith(f":table/{table_name}")
    assert import_details["FailureCode"] == "S3NoSuchBucket"
    assert "The specified bucket does not exist" in import_details["FailureMessage"]

    assert table_name not in client.list_tables()["TableNames"]


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_import_has_regular_validation(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")

    table_name = "t" + str(uuid4())[0:6]

    with pytest.raises(ClientError) as exc:
        client.import_table(
            S3BucketSource={"S3Bucket": f"{uuid4()}"},
            InputFormat="DYNAMODB_JSON",
            InputCompressionType="NONE",
            TableCreationParameters={
                "TableName": table_name,
                "AttributeDefinitions": [
                    {"AttributeName": "pk", "AttributeType": "S"},
                ],
                "KeySchema": [
                    {"AttributeName": "pk", "KeyType": "HASH"},
                ],
                "BillingMode": "PROVISIONED",
            },
        )

    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == "One or more parameter values were invalid: ReadCapacityUnits and WriteCapacityUnits must both be specified when BillingMode is PROVISIONED"
    )

    assert table_name not in client.list_tables()["TableNames"]


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_import_from_empty_s3_bucket(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)

    import_description = client.import_table(
        S3BucketSource={"S3Bucket": s3_bucket_name},
        InputFormat="DYNAMODB_JSON",
        InputCompressionType="NONE",
        TableCreationParameters={
            "TableName": table_name,
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
    )["ImportTableDescription"]

    import_details = wait_for_import(client, import_description)

    assert import_details["ImportStatus"] == "COMPLETED"
    assert import_details["ErrorCount"] == 0
    assert import_details["ProcessedItemCount"] == 0
    assert import_details["ImportedItemCount"] == 0
    assert import_details["ProcessedSizeBytes"] == 0

    assert table_name in client.list_tables()["TableNames"]

    assert client.scan(TableName=table_name)["Items"] == []

    client.delete_table(TableName=table_name)

    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_import_table_single_file_with_multiple_items():
    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)

    data = ""
    for i in range(5):
        data += (
            json.dumps({"Item": {"pk": {"S": f"msg{i}"}, "data": {"S": f"{uuid4()}"}}})
            + "\n"
        )
    for i in range(10, 15):
        data += json.dumps(
            {"Item": {"pk": {"S": f"msg{i}"}, "data": {"S": f"{uuid4()}"}}}
        )
    filename1 = "data.json"
    s3.put_object(
        Bucket=s3_bucket_name,
        Body=data,
        Key=filename1,
    )

    import_description = client.import_table(
        S3BucketSource={"S3Bucket": s3_bucket_name},
        InputFormat="DYNAMODB_JSON",
        InputCompressionType="NONE",
        TableCreationParameters={
            "TableName": table_name,
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
    )["ImportTableDescription"]

    import_details = wait_for_import(client, import_description)

    assert import_details["ImportStatus"] == "COMPLETED"
    assert import_details["ErrorCount"] == 0
    assert import_details["ProcessedItemCount"] == 10
    assert import_details["ImportedItemCount"] == 10
    assert import_details["ProcessedSizeBytes"] > 0

    assert table_name in client.list_tables()["TableNames"]
    expected = [
        "msg0",
        "msg1",
        "msg10",
        "msg11",
        "msg12",
        "msg13",
        "msg14",
        "msg2",
        "msg3",
        "msg4",
    ]
    assert (
        sorted([i["pk"]["S"] for i in client.scan(TableName=table_name)["Items"]])
        == expected
    )

    client.delete_table(TableName=table_name)

    s3.delete_object(Bucket=s3_bucket_name, Key=filename1)
    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_import_table_multiple_files():
    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)

    items_file1 = {"Item": {"pk": {"S": "msg1"}, "data": {"S": f"{uuid4()}"}}}
    filename1 = "data.json"
    s3.put_object(
        Bucket=s3_bucket_name,
        Body=json.dumps(items_file1),
        Key=filename1,
    )

    items_file2 = {"Item": {"pk": {"S": "msg2"}, "data": {"S": f"{uuid4()}"}}}
    filename2 = "completely_random_filename_without_extension"
    s3.put_object(
        Bucket=s3_bucket_name,
        Body=json.dumps(items_file2),
        Key=filename2,
    )

    import_description = client.import_table(
        S3BucketSource={"S3Bucket": s3_bucket_name},
        InputFormat="DYNAMODB_JSON",
        InputCompressionType="NONE",
        TableCreationParameters={
            "TableName": table_name,
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
    )["ImportTableDescription"]

    import_details = wait_for_import(client, import_description)

    assert import_details["ImportStatus"] == "COMPLETED"
    assert import_details["ErrorCount"] == 0
    assert import_details["ProcessedItemCount"] == 2
    assert import_details["ImportedItemCount"] == 2
    assert import_details["ProcessedSizeBytes"] > 0

    assert table_name in client.list_tables()["TableNames"]

    assert [i["pk"]["S"] for i in client.scan(TableName=table_name)["Items"]] == [
        "msg1",
        "msg2",
    ]

    client.delete_table(TableName=table_name)

    s3.delete_object(Bucket=s3_bucket_name, Key=filename1)
    s3.delete_object(Bucket=s3_bucket_name, Key=filename2)
    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_some_successfull_files_and_some_with_unknown_data():
    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)

    items_file1 = {"Item": {"pk": {"S": "msg1"}, "data": {"S": f"{uuid4()}"}}}
    filename1 = "data.json"
    s3.put_object(
        Bucket=s3_bucket_name,
        Body=json.dumps(items_file1),
        Key=filename1,
    )

    items_file2 = {"pk": {"S": "msg2"}, "data": {"S": f"{uuid4()}"}}
    filename2 = "invaliddata"
    s3.put_object(
        Bucket=s3_bucket_name,
        Body=json.dumps(items_file2),
        Key=filename2,
    )

    import_description = client.import_table(
        S3BucketSource={"S3Bucket": s3_bucket_name},
        InputFormat="DYNAMODB_JSON",
        InputCompressionType="NONE",
        TableCreationParameters={
            "TableName": table_name,
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
    )["ImportTableDescription"]

    import_details = wait_for_import(client, import_description)

    assert import_details["ImportStatus"] == "FAILED"
    assert import_details["ErrorCount"] == 1
    assert import_details["ProcessedItemCount"] == 2
    assert import_details["ImportedItemCount"] == 1
    assert import_details["ProcessedSizeBytes"] > 0

    assert table_name in client.list_tables()["TableNames"]

    assert [i["pk"]["S"] for i in client.scan(TableName=table_name)["Items"]] == [
        "msg1"
    ]

    client.delete_table(TableName=table_name)

    s3.delete_object(Bucket=s3_bucket_name, Key=filename1)
    s3.delete_object(Bucket=s3_bucket_name, Key=filename2)
    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_only_process_file_with_prefix():
    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)

    items_file1 = {"Item": {"pk": {"S": "msg1"}, "data": {"S": f"{uuid4()}"}}}
    filename1 = "yesdata.json"
    s3.put_object(
        Bucket=s3_bucket_name,
        Body=json.dumps(items_file1),
        Key=filename1,
    )

    items_file2 = {"Item": {"pk": {"S": "msg2"}, "data": {"S": f"{uuid4()}"}}}
    filename2 = "nodata.json"
    s3.put_object(
        Bucket=s3_bucket_name,
        Body=json.dumps(items_file2),
        Key=filename2,
    )

    import_description = client.import_table(
        S3BucketSource={"S3Bucket": s3_bucket_name, "S3KeyPrefix": "yes"},
        InputFormat="DYNAMODB_JSON",
        InputCompressionType="NONE",
        TableCreationParameters={
            "TableName": table_name,
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
    )["ImportTableDescription"]

    import_details = wait_for_import(client, import_description)

    assert import_details["ImportStatus"] == "COMPLETED"
    assert import_details["ErrorCount"] == 0
    assert import_details["ProcessedItemCount"] == 1
    assert import_details["ImportedItemCount"] == 1
    assert import_details["ProcessedSizeBytes"] > 0

    assert table_name in client.list_tables()["TableNames"]

    assert [i["pk"]["S"] for i in client.scan(TableName=table_name)["Items"]] == [
        "msg1"
    ]

    client.delete_table(TableName=table_name)

    s3.delete_object(Bucket=s3_bucket_name, Key=filename1)
    s3.delete_object(Bucket=s3_bucket_name, Key=filename2)
    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_process_gzipped_file():
    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)

    items_file1 = {"Item": {"pk": {"S": "msg1"}, "data": {"S": f"{uuid4()}"}}}
    filename1 = "data.json"
    s3.put_object(
        Bucket=s3_bucket_name,
        Body=gzip.compress(json.dumps(items_file1).encode("utf-8")),
        Key=filename1,
    )

    import_description = client.import_table(
        S3BucketSource={"S3Bucket": s3_bucket_name},
        InputFormat="DYNAMODB_JSON",
        InputCompressionType="GZIP",
        TableCreationParameters={
            "TableName": table_name,
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
    )["ImportTableDescription"]

    import_details = wait_for_import(client, import_description)

    assert import_details["ImportStatus"] == "COMPLETED"
    assert import_details["ErrorCount"] == 0
    assert import_details["ProcessedItemCount"] == 1
    assert import_details["ImportedItemCount"] == 1
    assert import_details["ProcessedSizeBytes"] > 0

    assert table_name in client.list_tables()["TableNames"]

    assert [i["pk"]["S"] for i in client.scan(TableName=table_name)["Items"]] == [
        "msg1"
    ]

    client.delete_table(TableName=table_name)

    s3.delete_object(Bucket=s3_bucket_name, Key=filename1)
    s3.delete_bucket(Bucket=s3_bucket_name)


def wait_for_import(client, import_description):
    import_details = client.describe_import(ImportArn=import_description["ImportArn"])
    status = import_details["ImportTableDescription"]["ImportStatus"]
    while status == "IN_PROGRESS":
        sleep(0.1)
        import_details = client.describe_import(
            ImportArn=import_description["ImportArn"]
        )
        status = import_details["ImportTableDescription"]["ImportStatus"]
    return import_details["ImportTableDescription"]
