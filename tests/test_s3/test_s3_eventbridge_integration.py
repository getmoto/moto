import base64
import hashlib
import json
from io import BytesIO
from unittest import SkipTest
from uuid import uuid4

import boto3
import requests

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests.test_s3.test_s3_multipart import reduced_min_part_size

REGION_NAME = "us-east-1"
REDUCED_PART_SIZE = 256


@mock_aws
def test_put_object_notification_ObjectCreated_PUT():
    s3_res = boto3.resource("s3", region_name=REGION_NAME)
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    events_client = boto3.client("events", region_name=REGION_NAME)
    logs_client = boto3.client("logs", region_name=REGION_NAME)

    rule_name = "test-rule"
    events_client.put_rule(
        Name=rule_name, EventPattern=json.dumps({"account": [ACCOUNT_ID]})
    )
    log_group_name = "/test-group"
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

    # Create S3 bucket
    bucket_name = str(uuid4())
    s3_res.create_bucket(Bucket=bucket_name)

    # Put Notification
    s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={"EventBridgeConfiguration": {}},
    )

    # Put Object
    s3_client.put_object(Bucket=bucket_name, Key="keyname", Body="bodyofnewobject")

    events = sorted(
        logs_client.filter_log_events(logGroupName=log_group_name)["events"],
        key=lambda item: item["eventId"],
    )
    assert len(events) == 1
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

    s3_res = boto3.resource("s3", region_name=REGION_NAME)
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    events_client = boto3.client("events", region_name=REGION_NAME)
    logs_client = boto3.client("logs", region_name=REGION_NAME)

    rule_name = "test-rule"
    events_client.put_rule(
        Name=rule_name, EventPattern=json.dumps({"account": [ACCOUNT_ID]})
    )
    log_group_name = "/test-group"
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

    # Create S3 bucket
    bucket_name = str(uuid4())
    s3_res.create_bucket(Bucket=bucket_name)

    # Put bucket notification event bridge
    s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={"EventBridgeConfiguration": {}},
    )

    ###
    # multipart upload POST request (this request is processed in S3Response.__key_response_post)
    ###
    content = b"Hello, this is a sample content for the multipart upload."
    content_md5_hash = base64.b64encode(hashlib.md5(content).digest()).decode("utf-8")
    object_key = "test-key"
    url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"

    # Create multipart upload reqeusts
    res = requests.post(
        url,
        headers={"Content-MD5": content_md5_hash},
        auth=(ACCOUNT_ID, "test-key"),
        params={"uploads": ""},
    )

    # upload the parts
    upload_id = res.text.split("<UploadId>")[1].split("</UploadId>")[0]
    part_number = 1
    res = requests.put(
        url,
        data=content,
        headers={"Content-MD5": content_md5_hash},
        auth=(ACCOUNT_ID, "test-key"),
        params={"partNumber": part_number, "uploadId": upload_id},
    )

    # complete multi-part upload (PutObject event send to the logs)
    etag = res.headers["Etag"]
    _ = requests.post(
        url,
        data=(
            "<CompleteMultipartUpload "
            'xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            f"<Part><ETag>{etag}</ETag><PartNumber>1</PartNumber></Part>"
            "</CompleteMultipartUpload>"
        ),
        auth=(ACCOUNT_ID, "test-key"),
        params={"uploadId": upload_id},
    )

    events = sorted(
        logs_client.filter_log_events(logGroupName=log_group_name)["events"],
        key=lambda item: item["eventId"],
    )
    assert len(events) == 1

    ###
    # multipart/formdata POST request (this request is processed in S3Response._bucket_response_post)
    ###
    url = f"https://{bucket_name}.s3.amazonaws.com/"

    res = requests.post(
        url, data={"key": object_key}, files={"file": ("tmp.txt", BytesIO(content))}
    )

    events = sorted(
        logs_client.filter_log_events(logGroupName=log_group_name)["events"],
        key=lambda item: item["eventId"],
    )
    assert len(events) == 2

    for event in events:
        event_message = json.loads(event["message"])
        assert event_message["detail-type"] == "Object Created"
        assert event_message["source"] == "aws.s3"
        assert event_message["account"] == ACCOUNT_ID
        assert event_message["region"] == REGION_NAME
        assert event_message["detail"]["bucket"]["name"] == bucket_name
        assert event_message["detail"]["reason"] == "ObjectCreated"
