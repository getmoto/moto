import json
from datetime import datetime
from unittest import SkipTest, mock

import boto3
import os

import sure  # noqa # pylint: disable=unused-import

from moto import mock_events, mock_sqs, mock_logs, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
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
                "Arn": f"arn:aws:logs:eu-central-1:{ACCOUNT_ID}:log-group:{log_group_name}",
            }
        ],
    )

    # when
    event_time = datetime.utcnow()
    client_events.put_events(
        Entries=[
            {
                "Time": event_time,
                "Source": "source",
                "DetailType": "type",
                "Detail": json.dumps({"key": "value"}),
            }
        ]
    )

    # then
    response = client_logs.filter_log_events(logGroupName=log_group_name)
    response["events"].should.have.length_of(1)
    event = response["events"][0]
    event["logStreamName"].should_not.equal(None)
    event["timestamp"].should.be.a(float)
    event["ingestionTime"].should.be.a(int)
    event["eventId"].should_not.equal(None)

    message = json.loads(event["message"])
    message["version"].should.equal("0")
    message["id"].should_not.equal(None)
    message["detail-type"].should.equal("type")
    message["source"].should.equal("source")
    message["time"].should.equal(iso_8601_datetime_without_milliseconds(event_time))
    message["region"].should.equal("eu-central-1")
    message["resources"].should.equal([])
    message["detail"].should.equal({"key": "value"})


@mock_events
@mock_sqs
def test_send_to_sqs_fifo_queue():
    # given
    client_events = boto3.client("events", "eu-central-1")
    client_sqs = boto3.client("sqs", region_name="eu-central-1")
    rule_name = "test-rule"

    queue_url = client_sqs.create_queue(
        QueueName="test-queue.fifo", Attributes={"FifoQueue": "true"}
    )["QueueUrl"]
    queue_arn = client_sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    queue_url_dedup = client_sqs.create_queue(
        QueueName="test-queue-dedup.fifo",
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )["QueueUrl"]
    queue_arn_dedup = client_sqs.get_queue_attributes(
        QueueUrl=queue_url_dedup, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    client_events.put_rule(
        Name=rule_name,
        EventPattern=json.dumps({"account": [ACCOUNT_ID]}),
        State="ENABLED",
    )
    client_events.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "sqs-fifo",
                "Arn": queue_arn,
                "SqsParameters": {"MessageGroupId": "group-id"},
            },
            {
                "Id": "sqs-dedup-fifo",
                "Arn": queue_arn_dedup,
                "SqsParameters": {"MessageGroupId": "group-id"},
            },
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
        ]
    )

    # then
    response = client_sqs.receive_message(
        QueueUrl=queue_url_dedup,
        AttributeNames=["MessageDeduplicationId", "MessageGroupId"],
    )
    response["Messages"].should.have.length_of(1)
    message = response["Messages"][0]
    message["MessageId"].should_not.equal(None)
    message["ReceiptHandle"].should_not.equal(None)
    message["MD5OfBody"].should_not.equal(None)

    message["Attributes"]["MessageDeduplicationId"].should_not.equal(None)
    message["Attributes"]["MessageGroupId"].should.equal("group-id")

    body = json.loads(message["Body"])
    body["version"].should.equal("0")
    body["id"].should_not.equal(None)
    body["detail-type"].should.equal("type")
    body["source"].should.equal("source")
    body["time"].should.equal(iso_8601_datetime_without_milliseconds(event_time))
    body["region"].should.equal("eu-central-1")
    body["resources"].should.equal([])
    body["detail"].should.equal({"key": "value"})

    # A FIFO queue without content-based deduplication enabled
    # does not receive any event from the Event Bus
    response = client_sqs.receive_message(
        QueueUrl=queue_url, AttributeNames=["MessageDeduplicationId", "MessageGroupId"]
    )
    response.should_not.have.key("Messages")


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
    client_events.put_targets(Rule=rule_name, Targets=[{"Id": "sqs", "Arn": queue_arn}])

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
        ]
    )

    # then
    response = client_sqs.receive_message(QueueUrl=queue_url)
    response["Messages"].should.have.length_of(1)
    message = response["Messages"][0]
    message["MessageId"].should_not.equal(None)
    message["ReceiptHandle"].should_not.equal(None)
    message["MD5OfBody"].should_not.equal(None)

    body = json.loads(message["Body"])
    body["version"].should.equal("0")
    body["id"].should_not.equal(None)
    body["detail-type"].should.equal("type")
    body["source"].should.equal("source")
    body["time"].should.equal(iso_8601_datetime_without_milliseconds(event_time))
    body["region"].should.equal("eu-central-1")
    body["resources"].should.equal([])
    body["detail"].should.equal({"key": "value"})


@mock_events
@mock_sqs
def test_send_to_sqs_queue_with_custom_event_bus():
    # given
    client_events = boto3.client("events", "eu-central-1")
    client_sqs = boto3.client("sqs", region_name="eu-central-1")

    event_bus_arn = client_events.create_event_bus(Name="mock")["EventBusArn"]
    rule_name = "test-rule"
    queue_url = client_sqs.create_queue(QueueName="test-queue")["QueueUrl"]
    queue_arn = client_sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    client_events.put_rule(
        Name=rule_name,
        EventPattern=json.dumps({"account": [ACCOUNT_ID]}),
        State="ENABLED",
        EventBusName=event_bus_arn,
    )
    client_events.put_targets(
        Rule=rule_name,
        Targets=[{"Id": "sqs", "Arn": queue_arn}],
        EventBusName=event_bus_arn,
    )

    # when
    client_events.put_events(
        Entries=[
            {
                "Source": "source",
                "DetailType": "type",
                "Detail": json.dumps({"key": "value"}),
                "EventBusName": event_bus_arn,
            }
        ]
    )

    # then
    response = client_sqs.receive_message(QueueUrl=queue_url)
    assert len(response["Messages"]) == 1

    body = json.loads(response["Messages"][0]["Body"])
    body["detail"].should.equal({"key": "value"})


@mock_events
@mock_logs
def test_moto_matches_none_value_with_exists_filter():
    pattern = {
        "source": ["test-source"],
        "detail-type": ["test-detail-type"],
        "detail": {
            "foo": [{"exists": True}],
            "bar": [{"exists": True}],
        },
    }
    logs_client = boto3.client("logs", region_name="eu-west-1")
    log_group_name = "test-log-group"
    logs_client.create_log_group(logGroupName=log_group_name)

    events_client = boto3.client("events", region_name="eu-west-1")
    event_bus_name = "test-event-bus"
    events_client.create_event_bus(Name=event_bus_name)

    rule_name = "test-event-rule"
    events_client.put_rule(
        Name=rule_name,
        State="ENABLED",
        EventPattern=json.dumps(pattern),
        EventBusName=event_bus_name,
    )

    events_client.put_targets(
        Rule=rule_name,
        EventBusName=event_bus_name,
        Targets=[
            {
                "Id": "123",
                "Arn": f"arn:aws:logs:eu-west-1:{ACCOUNT_ID}:log-group:{log_group_name}",
            }
        ],
    )

    events_client.put_events(
        Entries=[
            {
                "EventBusName": event_bus_name,
                "Source": "test-source",
                "DetailType": "test-detail-type",
                "Detail": json.dumps({"foo": "123", "bar": "123"}),
            },
            {
                "EventBusName": event_bus_name,
                "Source": "test-source",
                "DetailType": "test-detail-type",
                "Detail": json.dumps({"foo": None, "bar": "123"}),
            },
        ]
    )

    events = sorted(
        logs_client.filter_log_events(logGroupName=log_group_name)["events"],
        key=lambda x: x["eventId"],
    )
    event_details = [json.loads(x["message"])["detail"] for x in events]

    event_details.should.equal(
        [
            {"foo": "123", "bar": "123"},
            {"foo": None, "bar": "123"},
        ],
    )


@mock_events
@mock_sqs
def test_put_events_event_bus_forwarding_rules():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cross-account test - easiest to just test in DecoratorMode")

    # EventBus1 --> EventBus2 --> SQS
    account1 = ACCOUNT_ID
    account2 = "222222222222"
    event_bus_name1 = "asdf"
    event_bus_name2 = "erty"
    events_client = boto3.client("events", "eu-central-1")
    sqs_client = boto3.client("sqs", region_name="eu-central-1")

    pattern = {
        "source": ["source1"],
        "detail-type": ["test-detail-type"],
        "detail": {
            "test": [{"exists": True}],
        },
    }

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account2}):
        # Setup SQS rule in account 2
        queue_url = sqs_client.create_queue(QueueName="test-queue")["QueueUrl"]
        queue_arn = sqs_client.get_queue_attributes(
            QueueUrl=queue_url, AttributeNames=["QueueArn"]
        )["Attributes"]["QueueArn"]

        event_bus_arn2 = events_client.create_event_bus(Name=event_bus_name2)[
            "EventBusArn"
        ]

        events_client.put_rule(
            Name="event_bus_2_rule",
            EventPattern=json.dumps(pattern),
            State="ENABLED",
            EventBusName=event_bus_name2,
        )

        events_client.put_targets(
            Rule="event_bus_2_rule",
            EventBusName=event_bus_name2,
            Targets=[{"Id": "sqs-dedup-fifo", "Arn": queue_arn}],
        )

    # Setup EventBus1
    events_client.create_event_bus(Name=event_bus_name1)["EventBusArn"]

    events_client.put_rule(
        Name="event_bus_1_rule",
        RoleArn=f"arn:aws:iam::{account1}:role/Administrator",
        EventPattern=json.dumps(pattern),
        State="ENABLED",
        EventBusName=event_bus_name1,
    )

    events_client.put_targets(
        Rule="event_bus_1_rule",
        EventBusName=event_bus_name1,
        Targets=[
            {
                "Id": "event_bus_2",
                "Arn": event_bus_arn2,
                "RoleArn": "arn:aws:iam::123456789012:role/Administrator",
            },
        ],
    )

    test_events = [
        {
            "Source": "source1",
            "DetailType": "test-detail-type",
            "Detail": json.dumps({"test": "true"}),
            "EventBusName": event_bus_name1,
        }
    ]

    events_client.put_events(Entries=test_events)

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account2}):
        # Verify SQS messages were received in account 2

        response = sqs_client.receive_message(QueueUrl=queue_url)

        response["Messages"].should.have.length_of(1)

        message = json.loads(response["Messages"][0]["Body"])
        message["source"].should.equal("source1")
        message["detail-type"].should.equal("test-detail-type")
        message["detail"].should.equal({"test": "true"})
