import json
from datetime import datetime

import boto3
import sure  # noqa

from moto import mock_events, mock_sqs, mock_logs
from moto.core import ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds


@mock_events
@mock_logs
def test_send_to_cw_log_group():
    # given
    client_events = boto3.client("events", "eu-central-1")
    client_logs = boto3.client("logs", region_name="eu-central-1")
    log_group_name = "/test-group"
    rule_name = "test-rule"
    client_logs.create_log_group(logGroupName=log_group_name)
    client_events.put_rule(
        Name=rule_name,
        EventPattern=json.dumps({"account": [ACCOUNT_ID]}),
        State="ENABLED",
    )
    client_events.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "logs",
                "Arn": "arn:aws:logs:eu-central-1:{0}:log-group:{1}".format(
                    ACCOUNT_ID, log_group_name
                ),
            }
        ],
    )

    # when
    event_time = datetime(2021, 1, 1, 12, 23, 34)
    client_events.put_events(
        Entries=[
            {
                "Time": event_time,
                "Source": "source",
                "DetailType": "type",
                "Detail": json.dumps({"key": "value"}),
            }
        ],
    )

    # then
    response = client_logs.filter_log_events(logGroupName=log_group_name)
    response["events"].should.have.length_of(1)
    event = response["events"][0]
    event["logStreamName"].should_not.be.empty
    event["timestamp"].should.be.a(float)
    event["ingestionTime"].should.be.a(int)
    event["eventId"].should_not.be.empty

    message = json.loads(event["message"])
    message["version"].should.equal("0")
    message["id"].should_not.be.empty
    message["detail-type"].should.equal("type")
    message["source"].should.equal("source")
    message["time"].should.equal(iso_8601_datetime_without_milliseconds(event_time))
    message["region"].should.equal("eu-central-1")
    message["resources"].should.be.empty
    message["detail"].should.equal({"key": "value"})


@mock_events
@mock_sqs
def test_send_to_sqs_queue():
    # given
    client_events = boto3.client("events", "eu-central-1")
    client_sqs = boto3.client("sqs", region_name="eu-central-1")
    rule_name = "test-rule"
    queue_url = client_sqs.create_queue(QueueName="test-queue")["QueueUrl"]
    queue_arn = client_sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    client_events.put_rule(
        Name=rule_name,
        EventPattern=json.dumps({"account": [ACCOUNT_ID]}),
        State="ENABLED",
    )
    client_events.put_targets(
        Rule=rule_name, Targets=[{"Id": "sqs", "Arn": queue_arn}],
    )

    # when
    event_time = datetime(2021, 1, 1, 12, 23, 34)
    client_events.put_events(
        Entries=[
            {
                "Time": event_time,
                "Source": "source",
                "DetailType": "type",
                "Detail": json.dumps({"key": "value"}),
            }
        ],
    )

    # then
    response = client_sqs.receive_message(QueueUrl=queue_url)
    response["Messages"].should.have.length_of(1)
    message = response["Messages"][0]
    message["MessageId"].should_not.be.empty
    message["ReceiptHandle"].should_not.be.empty
    message["MD5OfBody"].should_not.be.empty

    body = json.loads(message["Body"])
    body["version"].should.equal("0")
    body["id"].should_not.be.empty
    body["detail-type"].should.equal("type")
    body["source"].should.equal("source")
    body["time"].should.equal(iso_8601_datetime_without_milliseconds(event_time))
    body["region"].should.equal("eu-central-1")
    body["resources"].should.be.empty
    body["detail"].should.equal({"key": "value"})
