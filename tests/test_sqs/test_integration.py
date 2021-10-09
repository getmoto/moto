# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import json
import time
import uuid
import hashlib

import boto
import boto3
import sure  # noqa
from moto import mock_sqs, mock_lambda, mock_logs

from tests.test_awslambda.test_lambda import get_test_zip_file1, get_role_name


@mock_logs
@mock_lambda
@mock_sqs
def test_invoke_function_from_sqs_exception():
    logs_conn = boto3.client("logs", region_name="us-east-1")
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-sqs-queue1")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
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
        result = logs_conn.describe_log_streams(logGroupName="/aws/lambda/testFunction")
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(1)
            continue
        assert len(log_streams) >= 1

        result = logs_conn.get_log_events(
            logGroupName="/aws/lambda/testFunction",
            logStreamName=log_streams[0]["logStreamName"],
        )
        for event in result.get("events"):
            if "custom log event" in event["message"]:
                return
        time.sleep(1)

    assert False, "Test Failed"
