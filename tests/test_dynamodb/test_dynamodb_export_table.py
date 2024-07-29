import gzip
import json
from time import sleep
from unittest import SkipTest, mock
from uuid import uuid4

import boto3
import pytest

from moto import settings
from moto.dynamodb.models import TableExport

from . import dynamodb_aws_verified


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_export_from_missing_table(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    s3_prefix = "prefix"
    s3.create_bucket(Bucket=s3_bucket_name)
    table_arn = "t" + str(uuid4())[0:6]

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMO_JSON",
        S3Bucket=s3_bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)

    assert export_details["ExportStatus"] == "FAILED"
    assert export_details["FailureCode"] == "DynamoDBTableNotFound"
    assert "The specified table does not exist" in export_details["FailureMessage"]

    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_export_to_missing_s3_bucket(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    s3_prefix = "prefix"
    table_name = "test-table"

    response = client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table_arn = response["TableDescription"]["TableArn"]

    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMO_JSON",
        S3Bucket=s3_bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)

    assert export_details["ExportStatus"] == "FAILED"
    assert export_details["FailureCode"] == "S3NoSuchBucket"
    assert "The specified bucket does not exist" in export_details["FailureMessage"]


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_export_point_in_time_recovery_not_enabled(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    s3_prefix = "prefix"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)
    response = client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    table_arn = response["TableDescription"]["TableArn"]

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMO_JSON",
        S3Bucket=s3_bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)

    assert export_details["ExportStatus"] == "FAILED"
    assert export_details["FailureCode"] == "PointInTimeRecoveryUnavailable"
    assert (
        "Point in time recovery not enabled for table"
        in export_details["FailureMessage"]
    )

    client.delete_table(TableName=table_name)
    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
@mock.patch.object(TableExport, "_backup_to_s3_file", mock.Mock(side_effect=Exception))
def test_export_backup_to_s3_error(table_name=None):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't mock backup to s3 error in server mode")

    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    s3_prefix = "prefix"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)
    response = client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table_arn = response["TableDescription"]["TableArn"]
    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMO_JSON",
        S3Bucket=s3_bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)

    assert export_details["ExportStatus"] == "FAILED"
    assert export_details["FailureCode"] == "UNKNOWN"

    client.delete_table(TableName=table_name)
    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_export_empty_table(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    s3_prefix = "prefix"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)
    response = client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table_arn = response["TableDescription"]["TableArn"]

    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMO_JSON",
        S3Bucket=s3_bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)

    assert export_details["BilledSizeBytes"] == 0
    assert export_details["ExportStatus"] == "COMPLETED"
    assert export_details["ItemCount"] == 0
    assert export_details["ExportFormat"] == "DYNAMO_JSON"
    assert export_details["ExportType"] == "FULL_EXPORT"

    s3_contents = s3.list_objects(Bucket=s3_bucket_name, Prefix=s3_prefix)["Contents"][
        0
    ]
    object_key = s3_contents["Key"]
    compressed_backup = s3.get_object(Bucket=s3_bucket_name, Key=object_key)[
        "Body"
    ].read()
    file_contents = gzip.decompress(compressed_backup).decode("utf-8")
    assert json.loads(file_contents) == []

    client.delete_table(TableName=table_name)
    s3.delete_object(Bucket=s3_bucket_name, Key=object_key)
    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_export_table(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    s3_prefix = "prefix"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)
    response = client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table_arn = response["TableDescription"]["TableArn"]

    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    client.put_item(
        TableName=table_name,
        Item={"username": {"S": "user1"}, "binaryfoo": {"B": b"bar"}},
    )
    client.put_item(
        TableName=table_name, Item={"username": {"S": "user2"}, "foo": {"S": "bar"}}
    )
    client.put_item(
        TableName=table_name, Item={"username": {"S": "user3"}, "foo": {"S": "bar"}}
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMO_JSON",
        S3Bucket=s3_bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)
    assert export_details["BilledSizeBytes"] == 3
    assert export_details["ExportStatus"] == "COMPLETED"
    assert export_details["ItemCount"] == 3
    assert export_details["ExportFormat"] == "DYNAMO_JSON"
    assert export_details["ExportType"] == "FULL_EXPORT"

    s3_contents = s3.list_objects(Bucket=s3_bucket_name, Prefix=s3_prefix)["Contents"][
        0
    ]
    object_key = s3_contents["Key"]
    compressed_backup = s3.get_object(Bucket=s3_bucket_name, Key=object_key)[
        "Body"
    ].read()
    file_contents = gzip.decompress(compressed_backup).decode("utf-8")
    assert json.loads(file_contents) == [
        {"Attributes": {"username": {"S": "user1"}, "binaryfoo": {"B": "YmFy"}}},
        {"Attributes": {"username": {"S": "user2"}, "foo": {"S": "bar"}}},
        {"Attributes": {"username": {"S": "user3"}, "foo": {"S": "bar"}}},
    ]

    client.delete_table(TableName=table_name)
    s3.delete_object(Bucket=s3_bucket_name, Key=object_key)
    s3.delete_bucket(Bucket=s3_bucket_name)


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_list_exports(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_bucket_name = f"inttest{uuid4()}"
    s3_prefix = "prefix"
    table_name = "moto_test_" + str(uuid4())[0:6]

    s3.create_bucket(Bucket=s3_bucket_name)
    response = client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table_arn = response["TableDescription"]["TableArn"]

    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    client.put_item(
        TableName=table_name,
        Item={"username": {"S": "user1"}, "binaryfoo": {"B": b"bar"}},
    )
    client.put_item(
        TableName=table_name, Item={"username": {"S": "user2"}, "foo": {"S": "bar"}}
    )
    client.put_item(
        TableName=table_name, Item={"username": {"S": "user3"}, "foo": {"S": "bar"}}
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMO_JSON",
        S3Bucket=s3_bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details_1 = wait_for_export(client, export_description)
    assert export_details_1["ExportStatus"] == "COMPLETED"
    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMO_JSON",
        S3Bucket=s3_bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details_2 = wait_for_export(client, export_description)
    assert export_details_2["ExportStatus"] == "COMPLETED"
    export_summaries = client.list_exports(TableArn=table_arn)["ExportSummaries"]
    assert len(export_summaries) == 2
    assert export_summaries[0]["ExportStatus"] == "COMPLETED"
    assert export_summaries[0]["ExportType"] == "FULL_EXPORT"
    assert export_summaries[0]["ExportArn"] == export_details_1["ExportArn"]
    assert export_summaries[1]["ExportStatus"] == "COMPLETED"
    assert export_summaries[1]["ExportType"] == "FULL_EXPORT"
    assert export_summaries[1]["ExportArn"] == export_details_2["ExportArn"]

    client.delete_table(TableName=table_name)
    s3_contents = s3.list_objects(Bucket=s3_bucket_name, Prefix=s3_prefix)["Contents"]
    for object in s3_contents:
        s3.delete_object(Bucket=s3_bucket_name, Key=object["Key"])
    s3.delete_bucket(Bucket=s3_bucket_name)


def wait_for_export(client, export_description):
    status = "IN_PROGRESS"
    while status == "IN_PROGRESS":
        export_details = client.describe_export(
            ExportArn=export_description["ExportArn"]
        )
        status = export_details["ExportDescription"]["ExportStatus"]
        sleep(0.1)
    return export_details["ExportDescription"]
