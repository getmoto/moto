import json
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

REGION = "us-east-1"


def _create_queue_with_dlq(sqs, max_receive_count=1):
    dlq_url = sqs.create_queue(QueueName=f"dlq-{uuid4().hex[:8]}")["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]
    source_url = sqs.create_queue(
        QueueName=f"source-{uuid4().hex[:8]}",
        Attributes={
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": max_receive_count}
            )
        },
    )["QueueUrl"]
    source_arn = sqs.get_queue_attributes(
        QueueUrl=source_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    return source_url, source_arn, dlq_url, dlq_arn


def _send_to_dlq(sqs, source_url, bodies):
    """Send messages and receive them until the redrive policy moves them to the DLQ."""
    for body in bodies:
        sqs.send_message(QueueUrl=source_url, MessageBody=body)
    # The first receive counts once, the next one moves them (maxReceiveCount=1)
    sqs.receive_message(
        QueueUrl=source_url, MaxNumberOfMessages=10, VisibilityTimeout=0
    )
    sqs.receive_message(
        QueueUrl=source_url, MaxNumberOfMessages=10, VisibilityTimeout=0
    )


def _bodies(sqs, queue_url):
    messages = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        VisibilityTimeout=0,
        AttributeNames=["ApproximateReceiveCount"],
    ).get("Messages", [])
    return sorted(message["Body"] for message in messages), messages


@mock_aws
def test_start_message_move_task_moves_messages_back_to_the_source_queue():
    sqs = boto3.client("sqs", region_name=REGION)
    source_url, _, dlq_url, dlq_arn = _create_queue_with_dlq(sqs)
    _send_to_dlq(sqs, source_url, ["first", "second"])

    handle = sqs.start_message_move_task(SourceArn=dlq_arn)["TaskHandle"]

    assert handle
    assert _bodies(sqs, dlq_url)[0] == []
    bodies, messages = _bodies(sqs, source_url)
    assert bodies == ["first", "second"]
    # Moved messages start with a fresh receive count, so they are not moved
    # straight back to the dead-letter queue
    assert all(m["Attributes"]["ApproximateReceiveCount"] == "1" for m in messages)


@mock_aws
def test_start_message_move_task_moves_messages_to_the_destination_queue():
    sqs = boto3.client("sqs", region_name=REGION)
    source_url, _, dlq_url, dlq_arn = _create_queue_with_dlq(sqs)
    _send_to_dlq(sqs, source_url, ["first"])
    destination_url = sqs.create_queue(QueueName="destination")["QueueUrl"]
    destination_arn = sqs.get_queue_attributes(
        QueueUrl=destination_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    sqs.start_message_move_task(SourceArn=dlq_arn, DestinationArn=destination_arn)

    assert _bodies(sqs, destination_url)[0] == ["first"]
    assert _bodies(sqs, source_url)[0] == []
    assert _bodies(sqs, dlq_url)[0] == []


@mock_aws
def test_start_message_move_task_returns_each_message_to_its_own_source_queue():
    sqs = boto3.client("sqs", region_name=REGION)
    first_url, _, dlq_url, dlq_arn = _create_queue_with_dlq(sqs)
    second_url = sqs.create_queue(
        QueueName="second-source",
        Attributes={
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": 1}
            )
        },
    )["QueueUrl"]
    _send_to_dlq(sqs, first_url, ["from-first"])
    _send_to_dlq(sqs, second_url, ["from-second"])

    sqs.start_message_move_task(SourceArn=dlq_arn)

    assert _bodies(sqs, first_url)[0] == ["from-first"]
    assert _bodies(sqs, second_url)[0] == ["from-second"]
    assert _bodies(sqs, dlq_url)[0] == []


@mock_aws
def test_start_message_move_task_with_message_sent_directly_to_the_dlq():
    """A message that never went through the redrive policy goes to the only source queue."""
    sqs = boto3.client("sqs", region_name=REGION)
    source_url, _, dlq_url, dlq_arn = _create_queue_with_dlq(sqs)
    sqs.send_message(QueueUrl=dlq_url, MessageBody="direct")

    sqs.start_message_move_task(SourceArn=dlq_arn)

    assert _bodies(sqs, source_url)[0] == ["direct"]


@mock_aws
def test_start_message_move_task_leaves_messages_without_a_known_source_queue():
    """With several source queues, a message sent directly to the DLQ has no source to go back to."""
    sqs = boto3.client("sqs", region_name=REGION)
    first_url, _, dlq_url, dlq_arn = _create_queue_with_dlq(sqs)
    second_url = sqs.create_queue(
        QueueName="second-source",
        Attributes={
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": 1}
            )
        },
    )["QueueUrl"]
    _send_to_dlq(sqs, first_url, ["from-first"])
    sqs.send_message(QueueUrl=dlq_url, MessageBody="direct")

    sqs.start_message_move_task(SourceArn=dlq_arn)

    assert _bodies(sqs, first_url)[0] == ["from-first"]
    assert _bodies(sqs, second_url)[0] == []
    assert _bodies(sqs, dlq_url)[0] == ["direct"]
    task = sqs.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]
    assert task["ApproximateNumberOfMessagesMoved"] == 1
    assert task["ApproximateNumberOfMessagesToMove"] == 2


@mock_aws
def test_list_message_move_tasks_includes_the_destination():
    sqs = boto3.client("sqs", region_name=REGION)
    _, _, _, dlq_arn = _create_queue_with_dlq(sqs)
    destination_url = sqs.create_queue(QueueName="destination")["QueueUrl"]
    destination_arn = sqs.get_queue_attributes(
        QueueUrl=destination_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    sqs.start_message_move_task(SourceArn=dlq_arn, DestinationArn=destination_arn)

    task = sqs.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]

    assert task["DestinationArn"] == destination_arn


@mock_aws
def test_list_message_move_tasks():
    sqs = boto3.client("sqs", region_name=REGION)
    source_url, _, _, dlq_arn = _create_queue_with_dlq(sqs)
    _send_to_dlq(sqs, source_url, ["first", "second"])

    sqs.start_message_move_task(SourceArn=dlq_arn, MaxNumberOfMessagesPerSecond=10)
    sqs.start_message_move_task(SourceArn=dlq_arn)

    # MaxResults defaults to 1 and returns the most recent task first
    results = sqs.list_message_move_tasks(SourceArn=dlq_arn)["Results"]
    assert len(results) == 1
    assert results[0]["ApproximateNumberOfMessagesMoved"] == 0

    results = sqs.list_message_move_tasks(SourceArn=dlq_arn, MaxResults=10)["Results"]
    assert len(results) == 2
    oldest = results[1]
    assert oldest["Status"] == "COMPLETED"
    assert oldest["SourceArn"] == dlq_arn
    assert oldest["MaxNumberOfMessagesPerSecond"] == 10
    assert oldest["ApproximateNumberOfMessagesMoved"] == 2
    assert oldest["ApproximateNumberOfMessagesToMove"] == 2
    assert isinstance(oldest["StartedTimestamp"], int)
    # The handle is only returned while a task is running
    assert "TaskHandle" not in oldest
    assert "DestinationArn" not in oldest


@mock_aws
def test_cancel_message_move_task_of_a_completed_task():
    sqs = boto3.client("sqs", region_name=REGION)
    _, _, _, dlq_arn = _create_queue_with_dlq(sqs)
    handle = sqs.start_message_move_task(SourceArn=dlq_arn)["TaskHandle"]

    with pytest.raises(ClientError) as exc:
        sqs.cancel_message_move_task(TaskHandle=handle)

    assert (
        exc.value.response["Error"]["Code"]
        == "AWS.SimpleQueueService.UnsupportedOperation"
    )


@mock_aws
def test_cancel_message_move_task_with_unknown_handle():
    sqs = boto3.client("sqs", region_name=REGION)

    with pytest.raises(ClientError) as exc:
        sqs.cancel_message_move_task(TaskHandle="unknown")

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_message_move_task_requires_a_dead_letter_queue():
    sqs = boto3.client("sqs", region_name=REGION)
    queue_url = sqs.create_queue(QueueName="not-a-dlq")["QueueUrl"]
    queue_arn = sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    for call in (sqs.start_message_move_task, sqs.list_message_move_tasks):
        with pytest.raises(ClientError) as exc:
            call(SourceArn=queue_arn)
        assert (
            exc.value.response["Error"]["Code"]
            == "AWS.SimpleQueueService.UnsupportedOperation"
        )


@mock_aws
@pytest.mark.parametrize(
    "arn",
    [
        "arn:aws:sqs:us-east-1:123456789012:does-not-exist",
        "arn:aws:sqs:nowhere-1:123456789012:does-not-exist",
        "not-an-arn",
    ],
)
def test_message_move_task_with_unknown_source_queue(arn):
    sqs = boto3.client("sqs", region_name=REGION)

    for call in (sqs.start_message_move_task, sqs.list_message_move_tasks):
        with pytest.raises(ClientError) as exc:
            call(SourceArn=arn)
        assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_start_message_move_task_with_unknown_destination_queue():
    sqs = boto3.client("sqs", region_name=REGION)
    _, _, _, dlq_arn = _create_queue_with_dlq(sqs)

    with pytest.raises(ClientError) as exc:
        sqs.start_message_move_task(
            SourceArn=dlq_arn,
            DestinationArn="arn:aws:sqs:us-east-1:123456789012:does-not-exist",
        )

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
@pytest.mark.parametrize("rate", [0, 501])
def test_start_message_move_task_with_invalid_rate(rate):
    sqs = boto3.client("sqs", region_name=REGION)
    _, _, _, dlq_arn = _create_queue_with_dlq(sqs)

    with pytest.raises(ClientError) as exc:
        sqs.start_message_move_task(
            SourceArn=dlq_arn, MaxNumberOfMessagesPerSecond=rate
        )

    assert exc.value.response["Error"]["Code"] == "InvalidParameterValue"


@mock_aws
@pytest.mark.parametrize("max_results", [0, 11])
def test_list_message_move_tasks_with_invalid_max_results(max_results):
    sqs = boto3.client("sqs", region_name=REGION)
    _, _, _, dlq_arn = _create_queue_with_dlq(sqs)

    with pytest.raises(ClientError) as exc:
        sqs.list_message_move_tasks(SourceArn=dlq_arn, MaxResults=max_results)

    assert exc.value.response["Error"]["Code"] == "InvalidParameterValue"
