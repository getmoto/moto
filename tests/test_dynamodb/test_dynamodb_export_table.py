import gzip
import json
import os
from time import sleep
from unittest import SkipTest, mock
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import settings
from moto.dynamodb.models import TableExport
from tests.test_s3 import s3_aws_verified

from . import dynamodb_aws_verified


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
@s3_aws_verified
def test_export_from_missing_table(table_name=None, bucket_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")
    sts = boto3.client("sts", "us-east-1")

    account_id = sts.get_caller_identity()["Account"]

    s3_prefix = "prefix"
    table_arn = f"arn:aws:dynamodb:us-east-1:{account_id}:table/{str(uuid4())[0:6]}"

    with pytest.raises(ClientError) as exc:
        client.export_table_to_point_in_time(
            TableArn=table_arn,
            ExportFormat="DYNAMODB_JSON",
            S3Bucket=bucket_name,
            S3Prefix=s3_prefix,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "TableNotFoundException"
    assert err["Message"] == f"Table not found: {table_arn}"


@pytest.mark.aws_verified
@dynamodb_aws_verified()
def test_export_to_missing_s3_bucket(table_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")

    table_arn = client.describe_table(TableName=table_name)["Table"]["TableArn"]

    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMODB_JSON",
        S3Bucket=f"inttest{uuid4()}",
        S3Prefix="prefix",
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)

    assert export_details["ExportStatus"] == "FAILED"
    assert export_details["FailureCode"] == "S3NoSuchBucket"
    assert "The specified bucket does not exist" in export_details["FailureMessage"]


@pytest.mark.aws_verified
@dynamodb_aws_verified()
@s3_aws_verified
def test_export_point_in_time_recovery_not_enabled(table_name=None, bucket_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")

    table_arn = client.describe_table(TableName=table_name)["Table"]["TableArn"]

    with pytest.raises(ClientError) as exc:
        client.export_table_to_point_in_time(
            TableArn=table_arn,
            ExportFormat="DYNAMODB_JSON",
            S3Bucket=bucket_name,
            S3Prefix="prefix",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "PointInTimeRecoveryUnavailableException"
    assert (
        err["Message"]
        == f"Point in time recovery is not enabled for table '{table_name}'"
    )


@dynamodb_aws_verified()
@s3_aws_verified
@mock.patch.object(TableExport, "_backup_to_s3_file", mock.Mock(side_effect=Exception))
def test_export_backup_to_s3_error(table_name=None, bucket_name=None):
    aws_request = (
        os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
    )
    if not settings.TEST_DECORATOR_MODE or aws_request:
        raise SkipTest("Can't mock backup to s3 error in ServerMode/against AWS")

    client = boto3.client("dynamodb", region_name="us-east-1")

    table_arn = client.describe_table(TableName=table_name)["Table"]["TableArn"]
    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMODB_JSON",
        S3Bucket=bucket_name,
        S3Prefix="prefix",
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)

    assert export_details["ExportStatus"] == "FAILED"
    assert export_details["FailureCode"] == "UNKNOWN"


@pytest.mark.aws_verified
@dynamodb_aws_verified()
@s3_aws_verified
def test_export_empty_table(table_name=None, bucket_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")

    prefix = "prefix"

    table_arn = client.describe_table(TableName=table_name)["Table"]["TableArn"]

    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMODB_JSON",
        S3Bucket=bucket_name,
        S3Prefix=prefix,
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)

    assert export_details["BilledSizeBytes"] == 0
    assert export_details["ExportStatus"] == "COMPLETED"
    assert export_details["ItemCount"] == 0
    assert export_details["ExportFormat"] == "DYNAMODB_JSON"

    s3_files = s3.list_objects(Bucket=bucket_name, Prefix=prefix)["Contents"]
    for file in s3_files:
        # AWS creates other files as well
        # {prefix}/AWSDynamoDB/_started
        # {prefix}/AWSDynamoDB/{number}/data/random.json.gz
        # {prefix}/AWSDynamoDB/{number}/manifest-files.json
        # {prefix}/AWSDynamoDB/{number}/manifest-files.md5
        # {prefix}/AWSDynamoDB/{number}/manifest-summary.json
        # {prefix}/AWSDynamoDB/{number}/manifest-summary.md5
        if "/data/" in file["Key"]:
            s3_object = s3.get_object(Bucket=bucket_name, Key=file["Key"])

            compressed_backup = s3_object["Body"].read()
            file_contents = gzip.decompress(compressed_backup)
            assert file_contents == b""


@pytest.mark.aws_verified
@dynamodb_aws_verified()
@s3_aws_verified
def test_export_table(table_name=None, bucket_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")

    s3_prefix = "prefix"

    table_arn = client.describe_table(TableName=table_name)["Table"]["TableArn"]

    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    client.put_item(
        TableName=table_name, Item={"pk": {"S": "user1"}, "binaryfoo": {"B": b"bar"}}
    )
    client.put_item(
        TableName=table_name, Item={"pk": {"S": "user2"}, "foo": {"S": "bar"}}
    )
    client.put_item(
        TableName=table_name, Item={"pk": {"S": "user3"}, "foo": {"S": "bar"}}
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMODB_JSON",
        S3Bucket=bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details = wait_for_export(client, export_description)
    assert export_details["ExportStatus"] == "COMPLETED"
    assert export_details["ItemCount"] == 3
    assert export_details["ExportFormat"] == "DYNAMODB_JSON"

    s3_files = s3.list_objects(Bucket=bucket_name, Prefix=s3_prefix)["Contents"]
    for file in s3_files:
        # AWS creates other files as well
        # {prefix}/AWSDynamoDB/_started
        # {prefix}/AWSDynamoDB/{number}/data/random.json.gz
        # {prefix}/AWSDynamoDB/{number}/manifest-files.json
        # {prefix}/AWSDynamoDB/{number}/manifest-files.md5
        # {prefix}/AWSDynamoDB/{number}/manifest-summary.json
        # {prefix}/AWSDynamoDB/{number}/manifest-summary.md5
        if "/data/" in file["Key"]:
            s3_object = s3.get_object(Bucket=bucket_name, Key=file["Key"])

            compressed_backup = s3_object["Body"].read()
            file_contents = gzip.decompress(compressed_backup).decode("utf-8")
            rows = [json.loads(r) for r in file_contents.split("\n") if r]

            assert {"Item": {"pk": {"S": "user1"}, "binaryfoo": {"B": "YmFy"}}} in rows
            assert {"Item": {"pk": {"S": "user2"}, "foo": {"S": "bar"}}} in rows
            assert {"Item": {"pk": {"S": "user3"}, "foo": {"S": "bar"}}} in rows


@pytest.mark.aws_verified
@dynamodb_aws_verified()
@s3_aws_verified
def test_list_exports(table_name=None, bucket_name=None):
    client = boto3.client("dynamodb", region_name="us-east-1")

    s3_prefix = "prefix"

    table_arn = client.describe_table(TableName=table_name)["Table"]["TableArn"]

    client.update_continuous_backups(
        TableName=table_name,
        PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
    )

    client.put_item(
        TableName=table_name, Item={"pk": {"S": "user1"}, "binaryfoo": {"B": b"bar"}}
    )
    client.put_item(
        TableName=table_name, Item={"pk": {"S": "user2"}, "foo": {"S": "bar"}}
    )
    client.put_item(
        TableName=table_name, Item={"pk": {"S": "user3"}, "foo": {"S": "bar"}}
    )

    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMODB_JSON",
        S3Bucket=bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details_1 = wait_for_export(client, export_description)
    assert export_details_1["ExportStatus"] == "COMPLETED"
    export_description = client.export_table_to_point_in_time(
        TableArn=table_arn,
        ExportFormat="DYNAMODB_JSON",
        S3Bucket=bucket_name,
        S3Prefix=s3_prefix,
    )["ExportDescription"]

    export_details_2 = wait_for_export(client, export_description)
    assert export_details_2["ExportStatus"] == "COMPLETED"
    exports = client.list_exports(TableArn=table_arn)["ExportSummaries"]
    assert len(exports) == 2

    export_arn1 = export_details_1["ExportArn"]
    export_arn2 = export_details_1["ExportArn"]
    assert {
        "ExportArn": export_arn1,
        "ExportStatus": "COMPLETED",
        "ExportType": "FULL_EXPORT",
    } in exports
    assert {
        "ExportArn": export_arn2,
        "ExportStatus": "COMPLETED",
        "ExportType": "FULL_EXPORT",
    } in exports


def wait_for_export(client, export_description):
    status = "IN_PROGRESS"
    while status == "IN_PROGRESS":
        export_details = client.describe_export(
            ExportArn=export_description["ExportArn"]
        )
        status = export_details["ExportDescription"]["ExportStatus"]
        sleep(0.1)
    return export_details["ExportDescription"]
