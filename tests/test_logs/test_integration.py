import base64
import boto3
import json
import time
import zlib

from botocore.exceptions import ClientError
from io import BytesIO
from moto import mock_logs, mock_lambda, mock_iam
from nose.tools import assert_raises
from zipfile import ZipFile, ZIP_DEFLATED


@mock_lambda
@mock_logs
def test_put_subscription_filter_update():
    # given
    region_name = "us-east-1"
    client_lambda = boto3.client("lambda", region_name)
    client_logs = boto3.client("logs", region_name)
    log_group_name = "/test"
    log_stream_name = "stream"
    client_logs.create_log_group(logGroupName=log_group_name)
    client_logs.create_log_stream(
        logGroupName=log_group_name, logStreamName=log_stream_name
    )
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.8",
        Role=_get_role_name(region_name),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]

    # when
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="",
        destinationArn=function_arn,
    )

    # then
    response = client_logs.describe_subscription_filters(logGroupName=log_group_name)
    response["subscriptionFilters"].should.have.length_of(1)
    filter = response["subscriptionFilters"][0]
    creation_time = filter["creationTime"]
    creation_time.should.be.a(int)
    filter["destinationArn"] = "arn:aws:lambda:us-east-1:123456789012:function:test"
    filter["distribution"] = "ByLogStream"
    filter["logGroupName"] = "/test"
    filter["filterName"] = "test"
    filter["filterPattern"] = ""

    # when
    # to update an existing subscription filter the 'filerName' must be identical
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="[]",
        destinationArn=function_arn,
    )

    # then
    response = client_logs.describe_subscription_filters(logGroupName=log_group_name)
    response["subscriptionFilters"].should.have.length_of(1)
    filter = response["subscriptionFilters"][0]
    filter["creationTime"].should.equal(creation_time)
    filter["destinationArn"] = "arn:aws:lambda:us-east-1:123456789012:function:test"
    filter["distribution"] = "ByLogStream"
    filter["logGroupName"] = "/test"
    filter["filterName"] = "test"
    filter["filterPattern"] = "[]"

    # when
    # only one subscription filter can be associated with a log group
    with assert_raises(ClientError) as e:
        client_logs.put_subscription_filter(
            logGroupName=log_group_name,
            filterName="test-2",
            filterPattern="",
            destinationArn=function_arn,
        )

    # then
    ex = e.exception
    ex.operation_name.should.equal("PutSubscriptionFilter")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("LimitExceededException")
    ex.response["Error"]["Message"].should.equal("Resource limit exceeded.")


@mock_lambda
@mock_logs
def test_put_subscription_filter_with_lambda():
    # given
    region_name = "us-east-1"
    client_lambda = boto3.client("lambda", region_name)
    client_logs = boto3.client("logs", region_name)
    log_group_name = "/test"
    log_stream_name = "stream"
    client_logs.create_log_group(logGroupName=log_group_name)
    client_logs.create_log_stream(
        logGroupName=log_group_name, logStreamName=log_stream_name
    )
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.8",
        Role=_get_role_name(region_name),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]

    # when
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="",
        destinationArn=function_arn,
    )

    # then
    response = client_logs.describe_subscription_filters(logGroupName=log_group_name)
    response["subscriptionFilters"].should.have.length_of(1)
    filter = response["subscriptionFilters"][0]
    filter["creationTime"].should.be.a(int)
    filter["destinationArn"] = "arn:aws:lambda:us-east-1:123456789012:function:test"
    filter["distribution"] = "ByLogStream"
    filter["logGroupName"] = "/test"
    filter["filterName"] = "test"
    filter["filterPattern"] = ""

    # when
    client_logs.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[
            {"timestamp": 0, "message": "test"},
            {"timestamp": 0, "message": "test 2"},
        ],
    )

    # then
    msg_showed_up, received_message = _wait_for_log_msg(
        client_logs, "/aws/lambda/test", "awslogs"
    )
    assert msg_showed_up, "CloudWatch log event was not found. All logs: {}".format(
        received_message
    )

    data = json.loads(received_message)["awslogs"]["data"]
    response = json.loads(
        zlib.decompress(base64.b64decode(data), 16 + zlib.MAX_WBITS).decode("utf-8")
    )
    response["messageType"].should.equal("DATA_MESSAGE")
    response["owner"].should.equal("123456789012")
    response["logGroup"].should.equal("/test")
    response["logStream"].should.equal("stream")
    response["subscriptionFilters"].should.equal(["test"])
    log_events = sorted(response["logEvents"], key=lambda log_event: log_event["id"])
    log_events.should.have.length_of(2)
    log_events[0]["id"].should.be.a(int)
    log_events[0]["message"].should.equal("test")
    log_events[0]["timestamp"].should.equal(0)
    log_events[1]["id"].should.be.a(int)
    log_events[1]["message"].should.equal("test 2")
    log_events[1]["timestamp"].should.equal(0)


@mock_lambda
@mock_logs
def test_delete_subscription_filter_errors():
    # given
    region_name = "us-east-1"
    client_lambda = boto3.client("lambda", region_name)
    client_logs = boto3.client("logs", region_name)
    log_group_name = "/test"
    client_logs.create_log_group(logGroupName=log_group_name)
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.8",
        Role=_get_role_name(region_name),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="",
        destinationArn=function_arn,
    )

    # when
    client_logs.delete_subscription_filter(
        logGroupName="/test", filterName="test",
    )

    # then
    response = client_logs.describe_subscription_filters(logGroupName=log_group_name)
    response["subscriptionFilters"].should.have.length_of(0)


@mock_lambda
@mock_logs
def test_delete_subscription_filter_errors():
    # given
    region_name = "us-east-1"
    client_lambda = boto3.client("lambda", region_name)
    client_logs = boto3.client("logs", region_name)
    log_group_name = "/test"
    client_logs.create_log_group(logGroupName=log_group_name)
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.8",
        Role=_get_role_name(region_name),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="",
        destinationArn=function_arn,
    )

    # when
    with assert_raises(ClientError) as e:
        client_logs.delete_subscription_filter(
            logGroupName="not-existing-log-group", filterName="test",
        )

    # then
    ex = e.exception
    ex.operation_name.should.equal("DeleteSubscriptionFilter")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "The specified log group does not exist"
    )

    # when
    with assert_raises(ClientError) as e:
        client_logs.delete_subscription_filter(
            logGroupName="/test", filterName="wrong-filter-name",
        )

    # then
    ex = e.exception
    ex.operation_name.should.equal("DeleteSubscriptionFilter")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "The specified subscription filter does not exist."
    )


@mock_logs
def test_put_subscription_filter_errors():
    # given
    client = boto3.client("logs", "us-east-1")
    log_group_name = "/test"
    client.create_log_group(logGroupName=log_group_name)

    # when
    with assert_raises(ClientError) as e:
        client.put_subscription_filter(
            logGroupName="not-existing-log-group",
            filterName="test",
            filterPattern="",
            destinationArn="arn:aws:lambda:us-east-1:123456789012:function:test",
        )

    # then
    ex = e.exception
    ex.operation_name.should.equal("PutSubscriptionFilter")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "The specified log group does not exist"
    )

    # when
    with assert_raises(ClientError) as e:
        client.put_subscription_filter(
            logGroupName="/test",
            filterName="test",
            filterPattern="",
            destinationArn="arn:aws:lambda:us-east-1:123456789012:function:not-existing",
        )

    # then
    ex = e.exception
    ex.operation_name.should.equal("PutSubscriptionFilter")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterException")
    ex.response["Error"]["Message"].should.equal(
        "Could not execute the lambda function. "
        "Make sure you have given CloudWatch Logs permission to execute your function."
    )

    # when
    with assert_raises(ClientError) as e:
        client.put_subscription_filter(
            logGroupName="/test",
            filterName="test",
            filterPattern="",
            destinationArn="arn:aws:lambda:us-east-1:123456789012:function:not-existing",
        )

    # then
    ex = e.exception
    ex.operation_name.should.equal("PutSubscriptionFilter")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterException")
    ex.response["Error"]["Message"].should.equal(
        "Could not execute the lambda function. "
        "Make sure you have given CloudWatch Logs permission to execute your function."
    )


def _get_role_name(region_name):
    with mock_iam():
        iam = boto3.client("iam", region_name=region_name)
        try:
            return iam.get_role(RoleName="test-role")["Role"]["Arn"]
        except ClientError:
            return iam.create_role(
                RoleName="test-role", AssumeRolePolicyDocument="test policy", Path="/",
            )["Role"]["Arn"]


def _get_test_zip_file():
    func_str = """
def lambda_handler(event, context):
    return event
"""

    zip_output = BytesIO()
    zip_file = ZipFile(zip_output, "w", ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", func_str)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def _wait_for_log_msg(client, log_group_name, expected_msg_part):
    received_messages = []
    start = time.time()
    while (time.time() - start) < 10:
        result = client.describe_log_streams(logGroupName=log_group_name)
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(1)
            continue

        for log_stream in log_streams:
            result = client.get_log_events(
                logGroupName=log_group_name, logStreamName=log_stream["logStreamName"],
            )
            received_messages.extend(
                [event["message"] for event in result.get("events")]
            )
        for message in received_messages:
            if expected_msg_part in message:
                return True, message
        time.sleep(1)
    return False, received_messages
