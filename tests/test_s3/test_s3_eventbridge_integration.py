import json
from io import BytesIO
from typing import Any, Dict, List
from unittest import SkipTest
from uuid import uuid4

import boto3
import requests

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.settings import S3_UPLOAD_PART_MIN_SIZE
from tests.test_s3.test_s3_multipart import reduced_min_part_size

REGION_NAME = "us-east-1"

if settings.TEST_DECORATOR_MODE:
    REDUCED_PART_SIZE = 256
else:
    REDUCED_PART_SIZE = S3_UPLOAD_PART_MIN_SIZE


def _seteup_bucket_notification_eventbridge(
    bucket_name: str = str(uuid4()),
    rule_name: str = "test-rule",
    log_group_name: str = "/test-group",
) -> Dict[str, str]:
    """Setups S3, EventBridge and CloudWatchLogs"""
    # Setup S3
    s3_res = boto3.resource("s3", region_name=REGION_NAME)
    s3_res.create_bucket(Bucket=bucket_name)

    # Put bucket notification event bridge
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={"EventBridgeConfiguration": {}},
    )

    # Setup EventBridge Rule
    events_client = boto3.client("events", region_name=REGION_NAME)
    events_client.put_rule(
        Name=rule_name, EventPattern=json.dumps({"account": [ACCOUNT_ID]})
    )

    # Create a log group and attach it to the events target.
    logs_client = boto3.client("logs", region_name=REGION_NAME)
    logs_client.create_log_group(logGroupName=log_group_name)
    events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "test",
                "Arn": f"arn:aws:logs:{REGION_NAME}:{ACCOUNT_ID}:log-group:{log_group_name}",
            }
        ],
    )

    return {
        "bucket_name": bucket_name,
        "event_rule_name": rule_name,
        "log_group_name": log_group_name,
    }


def _get_send_events(log_group_name: str = "/test-group") -> List[Dict[str, Any]]:
    logs_client = boto3.client("logs", region_name=REGION_NAME)
    return sorted(
        logs_client.filter_log_events(logGroupName=log_group_name)["events"],
        key=lambda item: item["timestamp"],
    )


@mock_aws
def test_put_object_notification_ObjectCreated_PUT():
    resource_names = _seteup_bucket_notification_eventbridge()
    bucket_name = resource_names["bucket_name"]
    s3_client = boto3.client("s3", region_name=REGION_NAME)

    # Put Object
    s3_client.put_object(Bucket=bucket_name, Key="keyname", Body="bodyofnewobject")

    events = _get_send_events()
    assert len(events) == 2
    event_message = json.loads(events[0]["message"])
    assert event_message["detail-type"] == "Object Created"
    assert event_message["source"] == "aws.s3"
    assert event_message["account"] == ACCOUNT_ID
    assert event_message["region"] == REGION_NAME
    assert event_message["detail"]["bucket"]["name"] == bucket_name
    assert event_message["detail"]["reason"] == "ObjectCreated"


@mock_aws
@reduced_min_part_size
def test_put_object_notification_ObjectCreated_POST():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest(("Doesn't quite work right with the Proxy or Server"))

    resource_names = _seteup_bucket_notification_eventbridge()
    bucket_name = resource_names["bucket_name"]

    ###
    # multipart/formdata POST request (this request is processed in S3Response._bucket_response_post)
    ###
    content = b"Hello, this is a sample content for the multipart upload."
    object_key = "test-key"

    _ = requests.post(
        f"https://{bucket_name}.s3.amazonaws.com/",
        data={"key": object_key},
        files={"file": ("tmp.txt", BytesIO(content))},
    )

    events = _get_send_events()
    assert len(events) == 1
    event_message = json.loads(events[0]["message"])
    assert event_message["detail-type"] == "Object Created"
    assert event_message["source"] == "aws.s3"
    assert event_message["account"] == ACCOUNT_ID
    assert event_message["region"] == REGION_NAME
    assert event_message["detail"]["bucket"]["name"] == bucket_name
    assert event_message["detail"]["object"]["key"] == object_key
    assert event_message["detail"]["reason"] == "ObjectCreated"


@mock_aws
def test_copy_object_notification():
    resource_names = _seteup_bucket_notification_eventbridge()
    bucket_name = resource_names["bucket_name"]
    s3_client = boto3.client("s3", region_name=REGION_NAME)

    # Copy object (send two events; PutObject and CopyObject)
    s3_client.put_object(Bucket=bucket_name, Key="keyname", Body="bodyofnewobject")
    object_key = "key2"
    s3_client.copy_object(
        Bucket=bucket_name, CopySource=f"{bucket_name}/keyname", Key="key2"
    )

    events = _get_send_events()
    assert len(events) == 3  # [PutObject, ObjectTagging, CopyObject]
    event_message = json.loads(events[-1]["message"])
    assert event_message["detail-type"] == "Object Created"
    assert event_message["source"] == "aws.s3"
    assert event_message["account"] == ACCOUNT_ID
    assert event_message["region"] == REGION_NAME
    assert event_message["detail"]["bucket"]["name"] == bucket_name
    assert event_message["detail"]["object"]["key"] == object_key
    assert event_message["detail"]["reason"] == "ObjectCreated"


@mock_aws
@reduced_min_part_size
def test_complete_multipart_upload_notification():
    resource_names = _seteup_bucket_notification_eventbridge()
    bucket_name = resource_names["bucket_name"]
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    object_key = "testkey"

    part1 = b"0" * REDUCED_PART_SIZE
    part2 = b"1"
    multipart = s3_client.create_multipart_upload(Bucket=bucket_name, Key=object_key)
    up1 = s3_client.upload_part(
        Body=BytesIO(part1),
        PartNumber=1,
        Bucket=bucket_name,
        Key=object_key,
        UploadId=multipart["UploadId"],
    )
    up2 = s3_client.upload_part(
        Body=BytesIO(part2),
        PartNumber=2,
        Bucket=bucket_name,
        Key=object_key,
        UploadId=multipart["UploadId"],
    )

    s3_client.complete_multipart_upload(
        Bucket=bucket_name,
        Key=object_key,
        MultipartUpload={
            "Parts": [
                {"ETag": up1["ETag"], "PartNumber": 1},
                {"ETag": up2["ETag"], "PartNumber": 2},
            ]
        },
        UploadId=multipart["UploadId"],
    )

    events = _get_send_events()
    assert len(events) == 3  # [PutObject, ObjectTagging, CompleteMultipartUpload]
    event_message = json.loads(events[-1]["message"])
    assert event_message["detail-type"] == "Object Created"
    assert event_message["source"] == "aws.s3"
    assert event_message["account"] == ACCOUNT_ID
    assert event_message["region"] == REGION_NAME
    assert event_message["detail"]["bucket"]["name"] == bucket_name
    assert event_message["detail"]["object"]["key"] == object_key
    assert event_message["detail"]["reason"] == "ObjectCreated"


@mock_aws
def test_delete_object_notification():
    resource_names = _seteup_bucket_notification_eventbridge()
    bucket_name = resource_names["bucket_name"]
    s3_client = boto3.client("s3", region_name=REGION_NAME)

    # Put Object
    s3_client.put_object(Bucket=bucket_name, Key="keyname", Body="bodyofnewobject")

    # Delete Object
    s3_client.delete_object(Bucket=bucket_name, Key="keyname")

    events = _get_send_events()
    assert len(events) == 3  # [PutObject, ObjectTagging, DeleteObect]
    event_message = json.loads(events[-1]["message"])
    assert event_message["detail-type"] == "Object Deleted"
    assert event_message["source"] == "aws.s3"
    assert event_message["account"] == ACCOUNT_ID
    assert event_message["region"] == REGION_NAME
    assert event_message["detail"]["bucket"]["name"] == bucket_name
    assert event_message["detail"]["reason"] == "ObjectRemoved"


@mock_aws
def test_restore_key_notifications():
    resource_names = _seteup_bucket_notification_eventbridge()
    bucket_name = resource_names["bucket_name"]

    s3_resource = boto3.resource("s3", region_name=REGION_NAME)

    bucket = s3_resource.Bucket(bucket_name)
    key = bucket.put_object(Key="the-key", Body=b"somedata", StorageClass="GLACIER")
    key.restore_object(RestoreRequest={"Days": 1})

    events = _get_send_events()
    event_names = [json.loads(e["message"])["detail"]["reason"] for e in events]
    assert event_names == ["ObjectCreated", "ObjectTagging", "ObjectRestore"]

    # Finish the Object Restoration - restore Completes immediately by default
    key.load()

    events = _get_send_events()
    event_names = [json.loads(e["message"])["detail"]["reason"] for e in events]
    assert event_names == [
        "ObjectCreated",
        "ObjectTagging",
        "ObjectRestore",
        "ObjectRestore",
    ]

    # Sanity check - loading the Key does not mean the Restore-event is fired every time
    key.load()

    events = _get_send_events()
    event_names = [json.loads(e["message"])["detail"]["reason"] for e in events]
    assert event_names == [
        "ObjectCreated",
        "ObjectTagging",
        "ObjectRestore",
        "ObjectRestore",
    ]


@mock_aws
def test_put_object_tagging_notification():
    resource_names = _seteup_bucket_notification_eventbridge()
    bucket_name = resource_names["bucket_name"]
    s3_client = boto3.client("s3", region_name=REGION_NAME)

    # Put Object
    s3_client.put_object(Bucket=bucket_name, Key="keyname", Body="bodyofnewobject")

    # Put Object Tagging
    s3_client.put_object_tagging(
        Bucket=bucket_name,
        Key="keyname",
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "foo"},
                {"Key": "item2", "Value": "bar"},
            ]
        },
    )

    events = _get_send_events()
    assert len(events) == 3
    event_message = json.loads(events[2]["message"])
    assert event_message["detail-type"] == "Object Tags Added"
    assert event_message["source"] == "aws.s3"
    assert event_message["account"] == ACCOUNT_ID
    assert event_message["region"] == REGION_NAME
    assert event_message["detail"]["bucket"]["name"] == bucket_name
    assert event_message["detail"]["reason"] == "ObjectTagging"
