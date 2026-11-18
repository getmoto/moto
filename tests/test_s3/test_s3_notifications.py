import json
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.s3.models import FakeBucket, FakeKey
from moto.s3.notifications import (
    S3NotificationEvent,
    _detail_type,
    _send_event_bridge_message,
)

REGION_NAME = "us-east-1"


@pytest.mark.parametrize(
    "event_names, expected_event_message",
    [
        (
            [
                S3NotificationEvent.OBJECT_CREATED_PUT_EVENT,
                S3NotificationEvent.OBJECT_CREATED_POST_EVENT,
                S3NotificationEvent.OBJECT_CREATED_COPY_EVENT,
                S3NotificationEvent.OBJECT_CREATED_COMPLETE_MULTIPART_UPLOAD_EVENT,
            ],
            "Object Created",
        ),
        (
            [
                S3NotificationEvent.OBJECT_REMOVED_DELETE_EVENT,
                S3NotificationEvent.OBJECT_REMOVED_DELETE_MARKER_CREATED_EVENT,
            ],
            "Object Deleted",
        ),
        ([S3NotificationEvent.OBJECT_RESTORE_POST_EVENT], "Object Restore Initiated"),
        (
            [S3NotificationEvent.OBJECT_RESTORE_COMPLETED_EVENT],
            "Object Restore Completed",
        ),
        (
            [S3NotificationEvent.OBJECT_RESTORE_DELETE_EVENT],
            "Object Restore Expired",
        ),
        (
            [S3NotificationEvent.LIFECYCLE_TRANSITION_EVENT],
            "Object Storage Class Changed",
        ),
        ([S3NotificationEvent.INTELLIGENT_TIERING_EVENT], "Object Access Tier Changed"),
        ([S3NotificationEvent.OBJECT_ACL_UPDATE_EVENT], "Object ACL Updated"),
        ([S3NotificationEvent.OBJECT_TAGGING_PUT_EVENT], "Object Tags Added"),
        ([S3NotificationEvent.OBJECT_TAGGING_DELETE_EVENT], "Object Tags Deleted"),
    ],
)
def test_detail_type(event_names: list[str], expected_event_message: str):
    for event_name in event_names:
        assert _detail_type(event_name) == expected_event_message


def test_detail_type_unknown_event():
    with pytest.raises(ValueError) as ex:
        _detail_type("unknown event")
    assert (
        str(ex.value)
        == "unsupported event `unknown event` for s3 eventbridge notification (https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventBridge.html)"
    )


def _receive_s3_event(queue_url):
    sqs = boto3.client("sqs", region_name=REGION_NAME)
    for message in sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10).get(
        "Messages", []
    ):
        body = json.loads(message["Body"])
        # The first message is the s3:TestEvent that is sent when the
        # notification configuration is created - skip it
        if "Records" in body:
            return body["Records"][0]
    raise AssertionError("No S3 event was delivered to the queue")


def _setup_bucket_with_sqs_notification(versioned):
    s3 = boto3.client("s3", region_name=REGION_NAME)
    sqs = boto3.client("sqs", region_name=REGION_NAME)
    queue_url = sqs.create_queue(QueueName=str(uuid4()))["QueueUrl"]
    queue_arn = sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    bucket_name = str(uuid4())
    s3.create_bucket(Bucket=bucket_name)
    if versioned:
        s3.put_bucket_versioning(
            Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
        )
    s3.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={
            "QueueConfigurations": [
                {"QueueArn": queue_arn, "Events": ["s3:ObjectCreated:*"]}
            ]
        },
    )
    return s3, queue_url, bucket_name


@mock_aws
def test_s3_event_contains_version_id_for_versioned_bucket():
    s3, queue_url, bucket_name = _setup_bucket_with_sqs_notification(versioned=True)

    version_id = s3.put_object(Bucket=bucket_name, Key="k", Body=b"x")["VersionId"]

    record = _receive_s3_event(queue_url)
    assert record["s3"]["object"]["versionId"] == version_id


@mock_aws
def test_s3_event_has_no_version_id_for_unversioned_bucket():
    s3, queue_url, bucket_name = _setup_bucket_with_sqs_notification(versioned=False)

    s3.put_object(Bucket=bucket_name, Key="k", Body=b"x")

    record = _receive_s3_event(queue_url)
    assert "versionId" not in record["s3"]["object"]


@mock_aws
def test_send_event_bridge_message():
    # setup mocks
    events_client = boto3.client("events", region_name=REGION_NAME)
    logs_client = boto3.client("logs", region_name=REGION_NAME)
    rule_name = "test-rule"
    events_client.put_rule(
        Name=rule_name, EventPattern=json.dumps({"account": [ACCOUNT_ID]})
    )
    log_group_name = f"/loggroup{str(uuid4())}"
    logs_client.create_log_group(logGroupName=log_group_name)
    mocked_bucket = FakeBucket(str(uuid4()), ACCOUNT_ID, REGION_NAME)
    mocked_key = FakeKey(
        "test-key",
        bytes("test content", encoding="utf-8"),
        ACCOUNT_ID,
        region_name=REGION_NAME,
    )

    # do nothing if event target does not exists.
    _send_event_bridge_message(
        ACCOUNT_ID,
        mocked_bucket,
        S3NotificationEvent.OBJECT_CREATED_PUT_EVENT,
        mocked_key,
    )
    assert (
        len(logs_client.filter_log_events(logGroupName=log_group_name)["events"]) == 0
    )

    # do nothing even if an error is raised while sending events.
    events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "test",
                "Arn": f"arn:aws:logs:{REGION_NAME}:{ACCOUNT_ID}:log-group:{log_group_name}",
            }
        ],
    )

    _send_event_bridge_message(ACCOUNT_ID, mocked_bucket, "unknown-event", mocked_key)
    assert (
        len(logs_client.filter_log_events(logGroupName=log_group_name)["events"]) == 0
    )

    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Doesn't quite work right with the Proxy or Server")
    # an event is correctly sent to the log group.
    _send_event_bridge_message(
        ACCOUNT_ID,
        mocked_bucket,
        S3NotificationEvent.OBJECT_CREATED_PUT_EVENT,
        mocked_key,
    )
    events = logs_client.filter_log_events(logGroupName=log_group_name)["events"]
    assert len(events) == 1
    event_msg = json.loads(events[0]["message"])
    assert event_msg["detail-type"] == "Object Created"
    assert event_msg["source"] == "aws.s3"
    assert event_msg["region"] == REGION_NAME
    assert event_msg["resources"] == [f"arn:aws:s3:::{mocked_bucket.name}"]
    event_detail = event_msg["detail"]
    assert event_detail["bucket"] == {"name": mocked_bucket.name}
    assert event_detail["object"]["key"] == mocked_key.name
    assert event_detail["reason"] == "ObjectCreated"
