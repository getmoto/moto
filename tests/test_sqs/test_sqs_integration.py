import json
import time
import uuid
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from tests.markers import requires_docker
from tests.test_awslambda.test_lambda import get_role_name, get_test_zip_file1
from tests.test_awslambda.utilities import get_test_zip_file_print_event


@mock_aws
@requires_docker
def test_invoke_function_from_sqs_queue():
    logs_conn = boto3.client("logs", region_name="us-east-1")
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue_name = str(uuid.uuid4())[0:6]
    queue = sqs.create_queue(QueueName=queue_name)

    fn_name = str(uuid.uuid4())[0:6]
    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=fn_name,
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func["FunctionArn"]
    )

    assert response["EventSourceArn"] == queue.attributes["QueueArn"]
    assert response["State"] == "Enabled"

    entries = [
        {
            "Id": "1",
            "MessageBody": json.dumps({"uuid": str(uuid.uuid4()), "test": "test"}),
        }
    ]

    queue.send_messages(Entries=entries)

    start = time.time()
    while (time.time() - start) < 30:
        result = logs_conn.describe_log_streams(logGroupName=f"/aws/lambda/{fn_name}")
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(0.5)
            continue
        assert len(log_streams) >= 1

        result = logs_conn.get_log_events(
            logGroupName=f"/aws/lambda/{fn_name}",
            logStreamName=log_streams[0]["logStreamName"],
        )
        for event in result.get("events"):
            if "custom log event" in event["message"]:
                return
        time.sleep(0.5)

    assert False, "Test Failed"


@mock_aws(config={"lambda": {"use_docker": False}})
def test_invoke_fake_function_from_sqs_queue():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only set Config in DecoratorMode")
    logs_conn = boto3.client("logs", region_name="us-east-1")
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue_name = str(uuid.uuid4())[0:6]
    queue = sqs.create_queue(QueueName=queue_name)

    fn_name = str(uuid.uuid4())[0:6]
    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=fn_name,
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": b"n/a"},
    )

    conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func["FunctionArn"]
    )

    queue.send_messages(Entries=[{"Id": "1", "MessageBody": "n/a"}])

    # Because the AWSLambda is never invoked, the log group doesn't even exist
    with pytest.raises(ClientError) as exc:
        logs_conn.describe_log_streams(logGroupName=f"/aws/lambda/{fn_name}")
    err = exc.value.response["Error"]
    assert err["Message"] == "The specified log group does not exist."


@mock_aws
@requires_docker
def test_invoke_function_from_sqs_fifo_queue():
    """
    Create a FIFO Queue
    Create a Lambda Function
    Send a message to the queue
    Verify the Lambda has been invoked with the correct message body
       (By checking the resulting log files)
    """
    logs_conn = boto3.client("logs", region_name="us-east-1")
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue_name = str(uuid.uuid4())[0:6] + ".fifo"
    queue = sqs.create_queue(
        QueueName=queue_name,
        Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
    )

    fn_name = str(uuid.uuid4())[0:6]
    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=fn_name,
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file_print_event()},
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func["FunctionArn"]
    )

    assert response["EventSourceArn"] == queue.attributes["QueueArn"]
    assert response["State"] == "Enabled"

    entries = [{"Id": "1", "MessageBody": "some body", "MessageGroupId": "mg1"}]

    queue.send_messages(Entries=entries)

    start = time.time()
    while (time.time() - start) < 30:
        result = logs_conn.describe_log_streams(logGroupName=f"/aws/lambda/{fn_name}")
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(0.5)
            continue
        assert len(log_streams) >= 1

        result = logs_conn.get_log_events(
            logGroupName=f"/aws/lambda/{fn_name}",
            logStreamName=log_streams[0]["logStreamName"],
        )

        for event in result.get("events"):
            try:
                body = json.loads(event.get("message"))
                atts = body["Records"][0]["attributes"]
                assert atts["MessageGroupId"] == "mg1"
                assert "MessageDeduplicationId" in atts
                return
            except:  # noqa: E722 Do not use bare except
                pass

        time.sleep(0.5)

    assert False, "Test Failed"
