import copy
import json
import os
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core.utils import unix_time_millis

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"
allow_aws_request = (
    os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
)


S3_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "s3:GetBucketAcl",
            "Effect": "Allow",
            "Resource": "arn:aws:s3:::{BUCKET_NAME}",
            "Principal": {"Service": "logs.us-east-1.amazonaws.com"},
            "Condition": {
                "StringEquals": {"aws:SourceAccount": ["AccountId1"]},
                "ArnLike": {"aws:SourceArn": ["..."]},
            },
        },
        {
            "Action": "s3:PutObject",
            "Effect": "Allow",
            "Resource": "arn:aws:s3:::{BUCKET_NAME}/*",
            "Principal": {"Service": "logs.us-east-1.amazonaws.com"},
            "Condition": {
                "StringEquals": {
                    "s3:x-amz-acl": "bucket-owner-full-control",
                    "aws:SourceAccount": ["AccountId1"],
                },
                "ArnLike": {"aws:SourceArn": ["..."]},
            },
        },
    ],
}


@pytest.fixture()
def logs():
    if allow_aws_request:
        yield boto3.client("logs", region_name="us-east-1")
    else:
        with mock_aws():
            yield boto3.client("logs", region_name="us-east-1")


@pytest.fixture()
def s3():
    if allow_aws_request:
        yield boto3.client("s3", region_name="us-east-1")
    else:
        with mock_aws():
            yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture(scope="function")
def log_group_name(logs):  # pylint: disable=redefined-outer-name
    name = "/moto/logs_test/" + str(uuid4())[0:5]
    logs.create_log_group(logGroupName=name)
    yield name
    logs.delete_log_group(logGroupName=name)


@pytest.fixture()
def bucket_name(s3, account_id):  # pylint: disable=redefined-outer-name
    name = f"moto-logs-test-{str(uuid4())[0:6]}"
    s3.create_bucket(Bucket=name)
    policy = copy.copy(S3_POLICY)
    policy["Statement"][0]["Resource"] = f"arn:aws:s3:::{name}"
    policy["Statement"][0]["Condition"]["StringEquals"]["aws:SourceAccount"] = [
        account_id
    ]
    policy["Statement"][0]["Condition"]["ArnLike"]["aws:SourceArn"] = [
        f"arn:aws:logs:us-east-1:{account_id}:log-group:*"
    ]
    policy["Statement"][1]["Resource"] = f"arn:aws:s3:::{name}/*"
    policy["Statement"][1]["Condition"]["StringEquals"]["aws:SourceAccount"] = [
        account_id
    ]
    policy["Statement"][1]["Condition"]["ArnLike"]["aws:SourceArn"] = [
        f"arn:aws:logs:us-east-1:{account_id}:log-group:*"
    ]

    s3.put_bucket_policy(Bucket=name, Policy=json.dumps(policy))
    yield name

    # Delete any files left behind
    versions = s3.list_object_versions(Bucket=name).get("Versions", [])
    for key in versions:
        s3.delete_object(Bucket=name, Key=key["Key"], VersionId=key.get("VersionId"))
    delete_markers = s3.list_object_versions(Bucket=name).get("DeleteMarkers", [])
    for key in delete_markers:
        s3.delete_object(Bucket=name, Key=key["Key"], VersionId=key.get("VersionId"))

    # Delete bucket itself
    s3.delete_bucket(Bucket=name)


@pytest.mark.aws_verified
def test_create_export_task_happy_path(logs, s3, log_group_name, bucket_name):  # pylint: disable=redefined-outer-name
    fromTime = 1611316574
    to = 1642852574
    resp = logs.create_export_task(
        logGroupName=log_group_name,
        fromTime=fromTime,
        to=to,
        destination=bucket_name,
    )
    task_id = resp["taskId"]
    # taskId resembles a valid UUID (i.e. a string of 32 hexadecimal digits)
    assert UUID(task_id)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # s3 bucket contains indication that permissions were successful
    resp = s3.get_object(Bucket=bucket_name, Key="aws-logs-write-test")
    assert resp["Body"].read() == b"Permission Check Successful"

    try:
        # ExportTask's can take a long time to succeed
        # From the docs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/S3ExportTasks.html
        #     > the export task might take anywhere from a few seconds to a few hours
        #
        # There can be only one ExportTask active at any point in time
        # Cancelling this one ensures that there's no Task active
        # And subsequent tests can create Export Tasks without running into a LimitExceededException
        logs.cancel_export_task(taskId=task_id)
    except ClientError as exc:
        # Because there are no logs, the export task in AWS usually finishes very quickly
        # Which is fine - we can just ignore that
        assert (
            exc.response["Error"]["Message"]
            == "The specified export task has already finished"
        )


@pytest.mark.aws_verified
def test_cancel_unknown_export_task(logs):  # pylint: disable=redefined-outer-name
    with pytest.raises(ClientError) as exc:
        logs.cancel_export_task(taskId=str(uuid4()))
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The specified export task does not exist."


@pytest.mark.aws_verified
def test_create_export_task_raises_ClientError_when_bucket_not_found(
    logs,
    log_group_name,
):  # pylint: disable=redefined-outer-name
    destination = "368a7022dea3dd621"
    fromTime = 1611316574
    to = 1642852574
    with pytest.raises(ClientError) as exc:
        logs.create_export_task(
            logGroupName=log_group_name,
            fromTime=fromTime,
            to=to,
            destination=destination,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "The given bucket does not exist. Please make sure the bucket is valid."
    )


@pytest.mark.aws_verified
def test_create_export_raises_ResourceNotFoundException_log_group_not_found(
    logs,
    bucket_name,
):  # pylint: disable=redefined-outer-name
    with pytest.raises(logs.exceptions.ResourceNotFoundException) as exc:
        logs.create_export_task(
            logGroupName=f"/aws/nonexisting/{str(uuid4())[0:6]}",
            fromTime=1611316574,
            to=1642852574,
            destination=bucket_name,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The specified log group does not exist."


@pytest.mark.aws_verified
def test_create_export_executes_export_task(logs, s3, log_group_name, bucket_name):  # pylint: disable=redefined-outer-name
    fromTime = int(unix_time_millis(datetime.now() - timedelta(days=1)))
    to = int(unix_time_millis(datetime.now() + timedelta(days=1)))

    logs.create_log_stream(logGroupName=log_group_name, logStreamName="/some/stream")

    messages = [
        {"timestamp": int(unix_time_millis()), "message": f"hello_{i}"}
        for i in range(10)
    ]
    logs.put_log_events(
        logGroupName=log_group_name, logStreamName="/some/stream", logEvents=messages
    )

    task_id = logs.create_export_task(
        logGroupName=log_group_name,
        fromTime=fromTime,
        to=to,
        destination=bucket_name,
    )["taskId"]

    task = logs.describe_export_tasks(taskId=task_id)["exportTasks"][0]
    assert task["status"]["code"] in ["COMPLETED", "RUNNING", "PENDING"]
    assert task["logGroupName"] == log_group_name
    assert task["destination"] == bucket_name
    assert task["destinationPrefix"] == "exportedlogs"
    assert task["from"] == fromTime
    assert task["to"] == to

    objects = s3.list_objects(Bucket=bucket_name)["Contents"]
    key_names = [o["Key"] for o in objects]
    assert "aws-logs-write-test" in key_names


def test_describe_export_tasks_happy_path(logs, s3, log_group_name):  # pylint: disable=redefined-outer-name
    destination = "mybucket"
    fromTime = 1611316574
    to = 1642852574
    s3.create_bucket(Bucket=destination)
    logs.create_export_task(
        logGroupName=log_group_name,
        fromTime=fromTime,
        to=to,
        destination=destination,
    )
    resp = logs.describe_export_tasks()
    assert len(resp["exportTasks"]) == 1
    assert resp["exportTasks"][0]["logGroupName"] == log_group_name
    assert resp["exportTasks"][0]["destination"] == destination
    assert resp["exportTasks"][0]["from"] == fromTime
    assert resp["exportTasks"][0]["to"] == to
    assert resp["exportTasks"][0]["status"]["code"] == "COMPLETED"
    assert resp["exportTasks"][0]["status"]["message"] == "Completed successfully"


def test_describe_export_tasks_out_of_order_timestamps(logs, s3, log_group_name):  # pylint: disable=redefined-outer-name
    destination = "mybucket"
    fromTime = 1000
    to = 500
    s3.create_bucket(Bucket=destination)
    logs.create_export_task(
        logGroupName=log_group_name,
        fromTime=fromTime,
        to=to,
        destination=destination,
    )
    resp = logs.describe_export_tasks()
    assert len(resp["exportTasks"]) == 1
    assert resp["exportTasks"][0]["logGroupName"] == log_group_name
    assert resp["exportTasks"][0]["destination"] == destination
    assert resp["exportTasks"][0]["from"] == fromTime
    assert resp["exportTasks"][0]["to"] == to
    assert resp["exportTasks"][0]["status"]["code"] == "active"
    assert resp["exportTasks"][0]["status"]["message"] == "Task is active"


def test_describe_export_tasks_task_id(logs, log_group_name, bucket_name):  # pylint: disable=redefined-outer-name
    fromTime = 1611316574
    to = 1642852574
    resp = logs.create_export_task(
        logGroupName=log_group_name,
        fromTime=fromTime,
        to=to,
        destination=bucket_name,
    )
    taskId = resp["taskId"]
    resp = logs.describe_export_tasks(taskId=taskId)
    assert len(resp["exportTasks"]) == 1
    assert resp["exportTasks"][0]["logGroupName"] == log_group_name
    assert resp["exportTasks"][0]["destination"] == bucket_name
    assert resp["exportTasks"][0]["from"] == fromTime
    assert resp["exportTasks"][0]["to"] == to
    assert resp["exportTasks"][0]["status"]["code"] == "COMPLETED"
    assert resp["exportTasks"][0]["status"]["message"] == "Completed successfully"


def test_describe_export_tasks_raises_ResourceNotFoundException_task_id_not_found(
    logs,
):  # pylint: disable=redefined-outer-name
    with pytest.raises(logs.exceptions.ResourceNotFoundException):
        logs.describe_export_tasks(taskId="368a7022dea3dd621")
