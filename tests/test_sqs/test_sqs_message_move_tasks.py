import base64
import json
from unittest import SkipTest
from uuid import UUID, uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.moto_api import state_manager

REGION = "us-east-1"
MODEL_NAME = "sqs::messagemovetask"


def _queue_arn(client, queue_url):
    return client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]


def _create_queue_with_dlq(client, dlq_arn=None, fifo=False):
    """
    Create a source queue with a DLQ, where every message is moved to the DLQ after one receive.
    Returns (queue_url, dlq_url)
    """
    suffix = ".fifo" if fifo else ""
    attributes = {"FifoQueue": "true", "ContentBasedDeduplication": "true"}
    if dlq_arn is None:
        dlq_url = client.create_queue(
            QueueName=f"dlq-{str(uuid4())[0:6]}{suffix}",
            Attributes=attributes if fifo else {},
        )["QueueUrl"]
        dlq_arn = _queue_arn(client, dlq_url)
    else:
        dlq_url = None
    source_attributes = {
        "RedrivePolicy": json.dumps(
            {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": 1}
        )
    }
    if fifo:
        source_attributes.update(attributes)
    queue_url = client.create_queue(
        QueueName=f"src-{str(uuid4())[0:6]}{suffix}", Attributes=source_attributes
    )["QueueUrl"]
    return queue_url, dlq_url


def _send_to_dlq(client, queue_url, bodies, **send_kwargs):
    for body in bodies:
        client.send_message(QueueUrl=queue_url, MessageBody=body, **send_kwargs)
    # The first receive counts against maxReceiveCount, the next ones move the messages into the DLQ
    for _ in range(len(bodies) + 1):
        client.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=10, VisibilityTimeout=0
        )


def _bodies(client, queue_url):
    messages = client.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=10, VisibilityTimeout=0
    ).get("Messages", [])
    return sorted(m["Body"] for m in messages)


def _set_manual_transition(times=1):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can't set transition directly outside of DecoratorMode")
    state_manager.set_transition(
        model_name=MODEL_NAME, transition={"progression": "manual", "times": times}
    )


@mock_aws
def test_start_message_move_task_to_custom_destination():
    client = boto3.client("sqs", region_name=REGION)
    queue_url, dlq_url = _create_queue_with_dlq(client)
    dlq_arn = _queue_arn(client, dlq_url)
    destination_url = client.create_queue(QueueName=f"dest-{str(uuid4())[0:6]}")[
        "QueueUrl"
    ]
    destination_arn = _queue_arn(client, destination_url)

    _send_to_dlq(client, queue_url, ["message-1", "message-2"])
    assert _bodies(client, dlq_url) == ["message-1", "message-2"]

    resp = client.start_message_move_task(
        SourceArn=dlq_arn, DestinationArn=destination_arn
    )
    task_handle = resp["TaskHandle"]

    decoded = json.loads(base64.b64decode(task_handle))
    assert set(decoded.keys()) == {"taskId", "sourceArn"}
    assert UUID(decoded["taskId"])
    assert decoded["sourceArn"] == dlq_arn

    assert _bodies(client, destination_url) == ["message-1", "message-2"]
    assert _bodies(client, dlq_url) == []
    assert _bodies(client, queue_url) == []

    results = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"]
    assert len(results) == 1
    task = results[0]
    assert task["Status"] == "COMPLETED"
    assert task["SourceArn"] == dlq_arn
    assert task["DestinationArn"] == destination_arn
    assert task["ApproximateNumberOfMessagesMoved"] == 2
    assert task["ApproximateNumberOfMessagesToMove"] == 2
    assert isinstance(task["StartedTimestamp"], int)
    # Only returned for RUNNING tasks
    assert "TaskHandle" not in task
    # Only returned when specified
    assert "MaxNumberOfMessagesPerSecond" not in task
    # Only returned for FAILED tasks
    assert "FailureReason" not in task


@mock_aws
def test_start_message_move_task_to_original_source():
    client = boto3.client("sqs", region_name=REGION)
    queue_url, dlq_url = _create_queue_with_dlq(client)
    dlq_arn = _queue_arn(client, dlq_url)

    _send_to_dlq(
        client,
        queue_url,
        ["message-1"],
        MessageAttributes={"attr": {"DataType": "String", "StringValue": "val"}},
    )
    original_id = client.receive_message(
        QueueUrl=dlq_url, MessageAttributeNames=["All"], VisibilityTimeout=0
    )["Messages"][0]["MessageId"]

    client.start_message_move_task(SourceArn=dlq_arn)

    messages = client.receive_message(
        QueueUrl=queue_url,
        MessageAttributeNames=["All"],
        MessageSystemAttributeNames=["ApproximateReceiveCount"],
    )["Messages"]
    assert len(messages) == 1
    assert messages[0]["Body"] == "message-1"
    assert messages[0]["MessageAttributes"] == {
        "attr": {"DataType": "String", "StringValue": "val"}
    }
    # A redriven message is a new message
    assert messages[0]["MessageId"] != original_id
    assert messages[0]["Attributes"]["ApproximateReceiveCount"] == "1"

    task = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]
    assert task["Status"] == "COMPLETED"
    assert task["ApproximateNumberOfMessagesMoved"] == 1
    assert "DestinationArn" not in task


@mock_aws
def test_start_message_move_task_to_multiple_original_sources():
    client = boto3.client("sqs", region_name=REGION)
    queue_url1, dlq_url = _create_queue_with_dlq(client)
    dlq_arn = _queue_arn(client, dlq_url)
    queue_url2, _ = _create_queue_with_dlq(client, dlq_arn=dlq_arn)

    _send_to_dlq(client, queue_url1, ["message-1-1", "message-1-2"])
    _send_to_dlq(client, queue_url2, ["message-2-1", "message-2-2"])

    client.start_message_move_task(SourceArn=dlq_arn)

    assert _bodies(client, queue_url1) == ["message-1-1", "message-1-2"]
    assert _bodies(client, queue_url2) == ["message-2-1", "message-2-2"]
    assert _bodies(client, dlq_url) == []

    task = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]
    assert task["ApproximateNumberOfMessagesMoved"] == 4
    assert task["ApproximateNumberOfMessagesToMove"] == 4


@mock_aws
def test_start_message_move_task_fifo_to_original_source():
    client = boto3.client("sqs", region_name=REGION)
    queue_url, dlq_url = _create_queue_with_dlq(client, fifo=True)
    dlq_arn = _queue_arn(client, dlq_url)

    _send_to_dlq(client, queue_url, ["message-1"], MessageGroupId="group-1")
    assert _bodies(client, queue_url) == []

    client.start_message_move_task(SourceArn=dlq_arn)

    messages = client.receive_message(
        QueueUrl=queue_url, MessageSystemAttributeNames=["MessageGroupId"]
    )["Messages"]
    assert [m["Body"] for m in messages] == ["message-1"]
    assert messages[0]["Attributes"]["MessageGroupId"] == "group-1"


@mock_aws
def test_start_message_move_task_without_known_source_fails():
    client = boto3.client("sqs", region_name=REGION)
    _, dlq_url = _create_queue_with_dlq(client)
    dlq_arn = _queue_arn(client, dlq_url)

    # Sent directly to the DLQ, so there is no original source queue to move it back to
    client.send_message(QueueUrl=dlq_url, MessageBody="direct")

    client.start_message_move_task(SourceArn=dlq_arn)

    task = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]
    assert task["Status"] == "FAILED"
    assert task["FailureReason"] == "CouldNotDetermineMessageSource"
    assert task["ApproximateNumberOfMessagesMoved"] == 0
    assert _bodies(client, dlq_url) == ["direct"]


@mock_aws
def test_start_message_move_task_source_does_not_exist():
    client = boto3.client("sqs", region_name=REGION)
    queue_url = client.create_queue(QueueName=f"q-{str(uuid4())[0:6]}")["QueueUrl"]
    arn = _queue_arn(client, queue_url) + "-unknown"

    with pytest.raises(ClientError) as exc:
        client.start_message_move_task(SourceArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "The resource that you specified for the SourceArn parameter doesn't exist."
    )


@mock_aws
def test_start_message_move_task_source_is_not_a_dlq():
    client = boto3.client("sqs", region_name=REGION)
    queue_url, dlq_url = _create_queue_with_dlq(client)
    destination_arn = _queue_arn(client, dlq_url)

    with pytest.raises(ClientError) as exc:
        client.start_message_move_task(
            SourceArn=_queue_arn(client, queue_url), DestinationArn=destination_arn
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Source queue must be configured as a Dead Letter Queue."


@mock_aws
def test_start_message_move_task_destination_does_not_exist():
    client = boto3.client("sqs", region_name=REGION)
    _, dlq_url = _create_queue_with_dlq(client)
    dlq_arn = _queue_arn(client, dlq_url)

    with pytest.raises(ClientError) as exc:
        client.start_message_move_task(
            SourceArn=dlq_arn, DestinationArn=dlq_arn + "doesntexist"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "The resource that you specified for the DestinationArn parameter doesn't exist."
    )


@mock_aws
@pytest.mark.parametrize("rate", [0, 501])
def test_start_message_move_task_invalid_rate(rate):
    client = boto3.client("sqs", region_name=REGION)
    _, dlq_url = _create_queue_with_dlq(client)
    dlq_arn = _queue_arn(client, dlq_url)

    with pytest.raises(ClientError) as exc:
        client.start_message_move_task(
            SourceArn=dlq_arn, MaxNumberOfMessagesPerSecond=rate
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == f"Value {rate} for parameter MaxNumberOfMessagesPerSecond is invalid. Reason: Must be between 1 and 500."
    )


@mock_aws
def test_list_message_move_tasks():
    client = boto3.client("sqs", region_name=REGION)
    queue_url, dlq_url = _create_queue_with_dlq(client)
    dlq_arn = _queue_arn(client, dlq_url)

    assert client.list_message_move_tasks(SourceArn=dlq_arn)["Results"] == []

    for rate in [1, 2, 3]:
        _send_to_dlq(client, queue_url, [f"message-{rate}"])
        client.start_message_move_task(
            SourceArn=dlq_arn, MaxNumberOfMessagesPerSecond=rate
        )

    # The most recent task is returned by default
    results = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"]
    assert [r["MaxNumberOfMessagesPerSecond"] for r in results] == [3]

    results = client.list_message_move_tasks(SourceArn=dlq_arn, MaxResults=10)[
        "Results"
    ]
    assert [r["MaxNumberOfMessagesPerSecond"] for r in results] == [3, 2, 1]
    assert all(r["Status"] == "COMPLETED" for r in results)


@mock_aws
def test_list_message_move_tasks_source_does_not_exist():
    client = boto3.client("sqs", region_name=REGION)
    queue_url = client.create_queue(QueueName=f"q-{str(uuid4())[0:6]}")["QueueUrl"]

    with pytest.raises(ClientError) as exc:
        client.list_message_move_tasks(SourceArn=_queue_arn(client, queue_url) + "x")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "The resource that you specified for the SourceArn parameter doesn't exist."
    )


@mock_aws
@pytest.mark.parametrize("max_results", [0, 11])
def test_list_message_move_tasks_invalid_max_results(max_results):
    client = boto3.client("sqs", region_name=REGION)
    _, dlq_url = _create_queue_with_dlq(client)

    with pytest.raises(ClientError) as exc:
        client.list_message_move_tasks(
            SourceArn=_queue_arn(client, dlq_url), MaxResults=max_results
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == f"Value {max_results} for parameter MaxResults is invalid. Reason: Must be between 1 and 10."
    )


@mock_aws
def test_cancel_message_move_task_with_invalid_task_handle():
    client = boto3.client("sqs", region_name=REGION)

    with pytest.raises(ClientError) as exc:
        client.cancel_message_move_task(TaskHandle="foobared")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Value for parameter TaskHandle is invalid."


@mock_aws
def test_cancel_message_move_task_with_unknown_source_arn():
    client = boto3.client("sqs", region_name=REGION)
    source_arn = f"arn:aws:sqs:{REGION}:123456789012:unknown-queue"
    task_handle = base64.b64encode(
        json.dumps({"taskId": str(uuid4()), "sourceArn": source_arn}).encode()
    ).decode()

    with pytest.raises(ClientError) as exc:
        client.cancel_message_move_task(TaskHandle=task_handle)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "The resource that you specified for the SourceArn parameter doesn't exist."
    )


@mock_aws
def test_cancel_message_move_task_with_unknown_task_id():
    client = boto3.client("sqs", region_name=REGION)
    queue_url = client.create_queue(QueueName=f"q-{str(uuid4())[0:6]}")["QueueUrl"]
    task_handle = base64.b64encode(
        json.dumps(
            {"taskId": str(uuid4()), "sourceArn": _queue_arn(client, queue_url)}
        ).encode()
    ).decode()

    with pytest.raises(ClientError) as exc:
        client.cancel_message_move_task(TaskHandle=task_handle)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Task does not exist."


@mock_aws
def test_cancel_message_move_task_that_is_not_running():
    client = boto3.client("sqs", region_name=REGION)
    _, dlq_url = _create_queue_with_dlq(client)
    dlq_arn = _queue_arn(client, dlq_url)

    # Transitions immediately by default, so this task has already completed
    task_handle = client.start_message_move_task(SourceArn=dlq_arn)["TaskHandle"]

    with pytest.raises(ClientError) as exc:
        client.cancel_message_move_task(TaskHandle=task_handle)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Task does not exist."


@mock_aws
def test_message_move_task_completes_when_status_advances():
    _set_manual_transition(times=2)
    try:
        client = boto3.client("sqs", region_name=REGION)
        queue_url, dlq_url = _create_queue_with_dlq(client)
        dlq_arn = _queue_arn(client, dlq_url)
        _send_to_dlq(client, queue_url, ["message-1", "message-2"])

        task_handle = client.start_message_move_task(
            SourceArn=dlq_arn, MaxNumberOfMessagesPerSecond=10
        )["TaskHandle"]

        # Nothing has moved yet
        assert _bodies(client, queue_url) == []

        task = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]
        assert task["Status"] == "RUNNING"
        assert task["TaskHandle"] == task_handle
        assert task["ApproximateNumberOfMessagesMoved"] == 0
        assert task["ApproximateNumberOfMessagesToMove"] == 2
        assert task["MaxNumberOfMessagesPerSecond"] == 10

        # Only one active task per source queue
        with pytest.raises(ClientError) as exc:
            client.start_message_move_task(SourceArn=dlq_arn)
        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParameterValue"
        assert (
            err["Message"]
            == "There is already a task running. Only one active task is allowed for a source queue arn at a given time."
        )

        task = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]
        assert task["Status"] == "COMPLETED"
        assert task["ApproximateNumberOfMessagesMoved"] == 2
        assert "TaskHandle" not in task
        assert _bodies(client, queue_url) == ["message-1", "message-2"]
        assert _bodies(client, dlq_url) == []

        # A new task can be started once the previous one is no longer active
        client.start_message_move_task(SourceArn=dlq_arn)
        results = client.list_message_move_tasks(SourceArn=dlq_arn, MaxResults=10)[
            "Results"
        ]
        assert [r["Status"] for r in results] == ["RUNNING", "COMPLETED"]
    finally:
        state_manager.unset_transition(MODEL_NAME)


@mock_aws
def test_cancel_message_move_task():
    _set_manual_transition(times=2)
    try:
        client = boto3.client("sqs", region_name=REGION)
        queue_url, dlq_url = _create_queue_with_dlq(client)
        dlq_arn = _queue_arn(client, dlq_url)
        _send_to_dlq(client, queue_url, ["message-1", "message-2"])

        task_handle = client.start_message_move_task(SourceArn=dlq_arn)["TaskHandle"]

        resp = client.cancel_message_move_task(TaskHandle=task_handle)
        assert resp["ApproximateNumberOfMessagesMoved"] == 0

        task = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]
        assert task["Status"] == "CANCELLING"
        assert "TaskHandle" not in task

        # A task that is cancelling is still active
        with pytest.raises(ClientError) as exc:
            client.start_message_move_task(SourceArn=dlq_arn)
        assert exc.value.response["Error"]["Code"] == "InvalidParameterValue"

        # Only a RUNNING task can be cancelled
        with pytest.raises(ClientError) as exc:
            client.cancel_message_move_task(TaskHandle=task_handle)
        assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

        task = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]
        assert task["Status"] == "CANCELLED"
        assert task["ApproximateNumberOfMessagesMoved"] == 0

        # Messages that were not moved stay in the DLQ
        assert _bodies(client, dlq_url) == ["message-1", "message-2"]
        assert _bodies(client, queue_url) == []
    finally:
        state_manager.unset_transition(MODEL_NAME)


@mock_aws
def test_message_move_task_fails_when_destination_is_deleted():
    _set_manual_transition()
    try:
        client = boto3.client("sqs", region_name=REGION)
        queue_url, dlq_url = _create_queue_with_dlq(client)
        dlq_arn = _queue_arn(client, dlq_url)
        destination_url = client.create_queue(QueueName=f"dest-{str(uuid4())[0:6]}")[
            "QueueUrl"
        ]
        _send_to_dlq(client, queue_url, ["message-1"])

        client.start_message_move_task(
            SourceArn=dlq_arn, DestinationArn=_queue_arn(client, destination_url)
        )
        client.delete_queue(QueueUrl=destination_url)

        task = client.list_message_move_tasks(SourceArn=dlq_arn)["Results"][0]
        assert task["Status"] == "FAILED"
        assert task["FailureReason"] == "AWS.SimpleQueueService.NonExistentQueue"
        assert task["ApproximateNumberOfMessagesMoved"] == 0
        assert _bodies(client, dlq_url) == ["message-1"]
    finally:
        state_manager.unset_transition(MODEL_NAME)
