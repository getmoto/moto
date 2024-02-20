import json
from io import BytesIO
from uuid import uuid4

import boto3

from moto import mock_aws
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

    # Create multipart upload request (an object is uploaded via POST request).
    key_name = "the-key"
    part1 = b"0" * REDUCED_PART_SIZE
    part2 = b"1"
    multipart = s3_client.create_multipart_upload(Bucket=bucket_name, Key=key_name)
    up1 = s3_client.upload_part(
        Body=BytesIO(part1),
        PartNumber=4,
        Bucket=bucket_name,
        Key=key_name,
        UploadId=multipart["UploadId"],
    )
    up2 = s3_client.upload_part(
        Body=BytesIO(part2),
        PartNumber=2,
        Bucket=bucket_name,
        Key=key_name,
        UploadId=multipart["UploadId"],
    )

    s3_client.complete_multipart_upload(
        Bucket=bucket_name,
        Key=key_name,
        MultipartUpload={
            "Parts": [
                {"ETag": up1["ETag"], "PartNumber": 4},
                {"ETag": up2["ETag"], "PartNumber": 2},
            ]
        },
        UploadId=multipart["UploadId"],
    )

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
    # NOTE: We cannot know if an object is created via PUT or POST request from EventBridge message.
    assert event_message["detail"]["reason"] == "ObjectCreated"
