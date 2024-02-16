import json
from uuid import uuid4

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

REGION_NAME = "us-east-1"


@mock_aws
def test_pub_object_notification():
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
