import base64
import json
import time
import zlib
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import boto3
import os
import sure  # noqa
import six
from botocore.exceptions import ClientError

from moto import mock_logs, settings, mock_lambda, mock_iam
from nose.tools import assert_raises
from nose import SkipTest

_logs_region = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


@mock_logs
def test_create_log_group():
    conn = boto3.client("logs", "us-west-2")

    response = conn.create_log_group(logGroupName="dummy")
    response = conn.describe_log_groups()

    response["logGroups"].should.have.length_of(1)
    response["logGroups"][0].should_not.have.key("retentionInDays")


@mock_logs
def test_exceptions():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    log_stream_name = "dummp-stream"
    conn.create_log_group(logGroupName=log_group_name)
    with assert_raises(ClientError):
        conn.create_log_group(logGroupName=log_group_name)

    # descrine_log_groups is not implemented yet

    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    with assert_raises(ClientError):
        conn.create_log_stream(
            logGroupName=log_group_name, logStreamName=log_stream_name
        )

    conn.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[{"timestamp": 0, "message": "line"}],
    )

    with assert_raises(ClientError):
        conn.put_log_events(
            logGroupName=log_group_name,
            logStreamName="invalid-stream",
            logEvents=[{"timestamp": 0, "message": "line"}],
        )


@mock_logs
def test_put_logs():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    log_stream_name = "stream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    messages = [
        {"timestamp": 0, "message": "hello"},
        {"timestamp": 0, "message": "world"},
    ]
    putRes = conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    res = conn.get_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name
    )
    events = res["events"]
    nextSequenceToken = putRes["nextSequenceToken"]
    assert isinstance(nextSequenceToken, six.string_types) == True
    assert len(nextSequenceToken) == 56
    events.should.have.length_of(2)


@mock_logs
def test_filter_logs_interleaved():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    log_stream_name = "stream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    messages = [
        {"timestamp": 0, "message": "hello"},
        {"timestamp": 0, "message": "world"},
    ]
    conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    res = conn.filter_log_events(
        logGroupName=log_group_name, logStreamNames=[log_stream_name], interleaved=True
    )
    events = res["events"]
    for original_message, resulting_event in zip(messages, events):
        resulting_event["eventId"].should.equal(str(resulting_event["eventId"]))
        resulting_event["timestamp"].should.equal(original_message["timestamp"])
        resulting_event["message"].should.equal(original_message["message"])


@mock_logs
def test_filter_logs_raises_if_filter_pattern():
    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "true":
        raise SkipTest("Does not work in server mode due to error in Workzeug")
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    log_stream_name = "stream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    messages = [
        {"timestamp": 0, "message": "hello"},
        {"timestamp": 0, "message": "world"},
    ]
    conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    with assert_raises(NotImplementedError):
        conn.filter_log_events(
            logGroupName=log_group_name,
            logStreamNames=[log_stream_name],
            filterPattern='{$.message = "hello"}',
        )


@mock_logs
def test_put_retention_policy():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.put_retention_policy(logGroupName=log_group_name, retentionInDays=7)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") == 7

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_delete_retention_policy():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.put_retention_policy(logGroupName=log_group_name, retentionInDays=7)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") == 7

    response = conn.delete_retention_policy(logGroupName=log_group_name)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") == None

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_get_log_events():
    client = boto3.client("logs", "us-west-2")
    log_group_name = "test"
    log_stream_name = "stream"
    client.create_log_group(logGroupName=log_group_name)
    client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    events = [{"timestamp": x, "message": str(x)} for x in range(20)]

    client.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=events
    )

    resp = client.get_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, limit=10
    )

    resp["events"].should.have.length_of(10)
    for i in range(10):
        resp["events"][i]["timestamp"].should.equal(i + 10)
        resp["events"][i]["message"].should.equal(str(i + 10))
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000019"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000010"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextBackwardToken"],
        limit=20,
    )

    resp["events"].should.have.length_of(10)
    for i in range(10):
        resp["events"][i]["timestamp"].should.equal(i)
        resp["events"][i]["message"].should.equal(str(i))
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000009"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000000"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextBackwardToken"],
        limit=10,
    )

    resp["events"].should.have.length_of(0)
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000000"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000000"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextForwardToken"],
        limit=1,
    )

    resp["events"].should.have.length_of(1)
    resp["events"][0]["timestamp"].should.equal(1)
    resp["events"][0]["message"].should.equal(str(1))
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000001"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000001"
    )


@mock_logs
def test_get_log_events_with_start_from_head():
    client = boto3.client("logs", "us-west-2")
    log_group_name = "test"
    log_stream_name = "stream"
    client.create_log_group(logGroupName=log_group_name)
    client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    events = [{"timestamp": x, "message": str(x)} for x in range(20)]

    client.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=events
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        limit=10,
        startFromHead=True,  # this parameter is only relevant without the usage of nextToken
    )

    resp["events"].should.have.length_of(10)
    for i in range(10):
        resp["events"][i]["timestamp"].should.equal(i)
        resp["events"][i]["message"].should.equal(str(i))
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000009"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000000"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextForwardToken"],
        limit=20,
    )

    resp["events"].should.have.length_of(10)
    for i in range(10):
        resp["events"][i]["timestamp"].should.equal(i + 10)
        resp["events"][i]["message"].should.equal(str(i + 10))
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000019"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000010"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextForwardToken"],
        limit=10,
    )

    resp["events"].should.have.length_of(0)
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000019"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000019"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextBackwardToken"],
        limit=1,
    )

    resp["events"].should.have.length_of(1)
    resp["events"][0]["timestamp"].should.equal(18)
    resp["events"][0]["message"].should.equal(str(18))
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000018"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000018"
    )


@mock_logs
def test_get_log_events_errors():
    client = boto3.client("logs", "us-west-2")
    log_group_name = "test"
    log_stream_name = "stream"
    client.create_log_group(logGroupName=log_group_name)
    client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    with assert_raises(ClientError) as e:
        client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            nextToken="n/00000000000000000000000000000000000000000000000000000000",
        )
    ex = e.exception
    ex.operation_name.should.equal("GetLogEvents")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.equal("InvalidParameterException")
    ex.response["Error"]["Message"].should.contain(
        "The specified nextToken is invalid."
    )

    with assert_raises(ClientError) as e:
        client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            nextToken="not-existing-token",
        )
    ex = e.exception
    ex.operation_name.should.equal("GetLogEvents")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.equal("InvalidParameterException")
    ex.response["Error"]["Message"].should.contain(
        "The specified nextToken is invalid."
    )


@mock_logs
def test_list_tags_log_group():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    tags = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}

    response = conn.create_log_group(logGroupName=log_group_name)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == {}

    response = conn.delete_log_group(logGroupName=log_group_name)
    response = conn.create_log_group(logGroupName=log_group_name, tags=tags)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_tag_log_group():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    tags = {"tag_key_1": "tag_value_1"}
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.tag_log_group(logGroupName=log_group_name, tags=tags)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags

    tags_with_added_value = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}
    response = conn.tag_log_group(
        logGroupName=log_group_name, tags={"tag_key_2": "tag_value_2"}
    )
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags_with_added_value

    tags_with_updated_value = {"tag_key_1": "tag_value_XX", "tag_key_2": "tag_value_2"}
    response = conn.tag_log_group(
        logGroupName=log_group_name, tags={"tag_key_1": "tag_value_XX"}
    )
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags_with_updated_value

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_untag_log_group():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    tags = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}
    response = conn.tag_log_group(logGroupName=log_group_name, tags=tags)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags

    tags_to_remove = ["tag_key_1"]
    remaining_tags = {"tag_key_2": "tag_value_2"}
    response = conn.untag_log_group(logGroupName=log_group_name, tags=tags_to_remove)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == remaining_tags

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_describe_subscription_filters():
    # given
    client = boto3.client("logs", "us-east-1")
    log_group_name = "/test"
    client.create_log_group(logGroupName=log_group_name)

    # when
    response = client.describe_subscription_filters(logGroupName=log_group_name)

    # then
    response["subscriptionFilters"].should.have.length_of(0)


@mock_logs
def test_describe_subscription_filters_errors():
    # given
    client = boto3.client("logs", "us-east-1")

    # when
    with assert_raises(ClientError) as e:
        client.describe_subscription_filters(logGroupName="not-existing-log-group",)

    # then
    ex = e.exception
    ex.operation_name.should.equal("DescribeSubscriptionFilters")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "The specified log group does not exist"
    )


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
