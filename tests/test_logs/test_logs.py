import os
import time
from unittest import SkipTest
import boto3
import six
from botocore.exceptions import ClientError
import pytest
import sure  # noqa

from moto import mock_logs, settings

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
    with pytest.raises(ClientError):
        conn.create_log_group(logGroupName=log_group_name)

    # descrine_log_groups is not implemented yet

    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    with pytest.raises(ClientError):
        conn.create_log_stream(
            logGroupName=log_group_name, logStreamName=log_stream_name
        )

    conn.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[{"timestamp": 0, "message": "line"}],
    )

    with pytest.raises(ClientError) as ex:
        conn.put_log_events(
            logGroupName=log_group_name,
            logStreamName="invalid-stream",
            logEvents=[{"timestamp": 0, "message": "line"}],
        )
    error = ex.value.response["Error"]
    error["Code"].should.equal("ResourceNotFoundException")
    error["Message"].should.equal("The specified log stream does not exist.")


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
    with pytest.raises(NotImplementedError):
        conn.filter_log_events(
            logGroupName=log_group_name,
            logStreamNames=[log_stream_name],
            filterPattern='{$.message = "hello"}',
        )


@mock_logs
def test_filter_logs_paging():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "/aws/dummy"
    log_stream_name = "stream/stage"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    timestamp = int(time.time())
    messages = []
    for i in range(25):
        messages.append(
            {"message": "Message number {}".format(i), "timestamp": timestamp}
        )
        timestamp += 100

    conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    res = conn.filter_log_events(
        logGroupName=log_group_name, logStreamNames=[log_stream_name], limit=20
    )
    events = res["events"]
    events.should.have.length_of(20)
    res["nextToken"].should.equal("/aws/dummy@stream/stage@" + events[-1]["eventId"])

    res = conn.filter_log_events(
        logGroupName=log_group_name,
        logStreamNames=[log_stream_name],
        limit=20,
        nextToken=res["nextToken"],
    )
    events += res["events"]
    events.should.have.length_of(25)
    res.should_not.have.key("nextToken")

    for original_message, resulting_event in zip(messages, events):
        resulting_event["eventId"].should.equal(str(resulting_event["eventId"]))
        resulting_event["timestamp"].should.equal(original_message["timestamp"])
        resulting_event["message"].should.equal(original_message["message"])

    res = conn.filter_log_events(
        logGroupName=log_group_name,
        logStreamNames=[log_stream_name],
        limit=20,
        nextToken="invalid-token",
    )
    res["events"].should.have.length_of(0)
    res.should_not.have.key("nextToken")

    res = conn.filter_log_events(
        logGroupName=log_group_name,
        logStreamNames=[log_stream_name],
        limit=20,
        nextToken="wrong-group@stream@999",
    )
    res["events"].should.have.length_of(0)
    res.should_not.have.key("nextToken")


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

    with pytest.raises(ClientError) as e:
        client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            nextToken="n/00000000000000000000000000000000000000000000000000000000",
        )
    ex = e.value
    ex.operation_name.should.equal("GetLogEvents")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.equal("InvalidParameterException")
    ex.response["Error"]["Message"].should.contain(
        "The specified nextToken is invalid."
    )

    with pytest.raises(ClientError) as e:
        client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            nextToken="not-existing-token",
        )
    ex = e.value
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
    with pytest.raises(ClientError) as e:
        client.describe_subscription_filters(logGroupName="not-existing-log-group",)

    # then
    ex = e.value
    ex.operation_name.should.equal("DescribeSubscriptionFilters")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "The specified log group does not exist"
    )


@mock_logs
def test_describe_log_groups_paging():
    client = boto3.client("logs", "us-east-1")

    group_names = [
        "/aws/lambda/lowercase-dev",
        "/aws/lambda/FileMonitoring",
        "/aws/events/GetMetricData",
        "/aws/lambda/fileAvailable",
    ]

    for name in group_names:
        client.create_log_group(logGroupName=name)

    resp = client.describe_log_groups()
    resp["logGroups"].should.have.length_of(4)
    resp.should_not.have.key("nextToken")

    resp = client.describe_log_groups(limit=2)
    resp["logGroups"].should.have.length_of(2)
    resp["nextToken"].should.equal("/aws/lambda/FileMonitoring")

    resp = client.describe_log_groups(nextToken=resp["nextToken"], limit=1)
    resp["logGroups"].should.have.length_of(1)
    resp["nextToken"].should.equal("/aws/lambda/fileAvailable")

    resp = client.describe_log_groups(nextToken=resp["nextToken"])
    resp["logGroups"].should.have.length_of(1)
    resp["logGroups"][0]["logGroupName"].should.equal("/aws/lambda/lowercase-dev")
    resp.should_not.have.key("nextToken")

    resp = client.describe_log_groups(nextToken="invalid-token")
    resp["logGroups"].should.have.length_of(0)
    resp.should_not.have.key("nextToken")


@mock_logs
def test_describe_log_streams_paging():
    client = boto3.client("logs", "us-east-1")

    log_group_name = "/aws/codebuild/lowercase-dev"
    stream_names = [
        "job/214/stage/unit_tests/foo",
        "job/215/stage/unit_tests/spam",
        "job/215/stage/e2e_tests/eggs",
        "job/216/stage/unit_tests/eggs",
    ]

    client.create_log_group(logGroupName=log_group_name)
    for name in stream_names:
        client.create_log_stream(logGroupName=log_group_name, logStreamName=name)

    resp = client.describe_log_streams(logGroupName=log_group_name)
    resp["logStreams"].should.have.length_of(4)
    resp["logStreams"][0]["arn"].should.contain(log_group_name)
    resp.should_not.have.key("nextToken")

    resp = client.describe_log_streams(logGroupName=log_group_name, limit=2)
    resp["logStreams"].should.have.length_of(2)
    resp["logStreams"][0]["arn"].should.contain(log_group_name)
    resp["nextToken"].should.equal(
        u"{}@{}".format(log_group_name, resp["logStreams"][1]["logStreamName"])
    )

    resp = client.describe_log_streams(
        logGroupName=log_group_name, nextToken=resp["nextToken"], limit=1
    )
    resp["logStreams"].should.have.length_of(1)
    resp["logStreams"][0]["arn"].should.contain(log_group_name)
    resp["nextToken"].should.equal(
        u"{}@{}".format(log_group_name, resp["logStreams"][0]["logStreamName"])
    )

    resp = client.describe_log_streams(
        logGroupName=log_group_name, nextToken=resp["nextToken"]
    )
    resp["logStreams"].should.have.length_of(1)
    resp["logStreams"][0]["arn"].should.contain(log_group_name)
    resp.should_not.have.key("nextToken")

    resp = client.describe_log_streams(
        logGroupName=log_group_name, nextToken="invalid-token"
    )
    resp["logStreams"].should.have.length_of(0)
    resp.should_not.have.key("nextToken")

    resp = client.describe_log_streams(
        logGroupName=log_group_name, nextToken="invalid@token"
    )
    resp["logStreams"].should.have.length_of(0)
    resp.should_not.have.key("nextToken")


@mock_logs
def test_start_query():
    client = boto3.client("logs", "us-east-1")

    log_group_name = "/aws/codebuild/lowercase-dev"
    client.create_log_group(logGroupName=log_group_name)

    response = client.start_query(
        logGroupName=log_group_name,
        startTime=int(time.time()),
        endTime=int(time.time()) + 300,
        queryString="test",
    )

    assert "queryId" in response

    with pytest.raises(ClientError) as e:
        client.start_query(
            logGroupName="/aws/codebuild/lowercase-dev-invalid",
            startTime=int(time.time()),
            endTime=int(time.time()) + 300,
            queryString="test",
        )

    # then
    ex = e.value
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "The specified log group does not exist"
    )
