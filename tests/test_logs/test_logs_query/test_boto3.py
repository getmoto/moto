import time
from datetime import timedelta

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core.utils import unix_time, unix_time_millis, utcnow


@mock_aws
def test_start_query__unknown_log_group():
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

    with pytest.raises(ClientError) as exc:
        client.start_query(
            logGroupName="/aws/codebuild/lowercase-dev-invalid",
            startTime=int(time.time()),
            endTime=int(time.time()) + 300,
            queryString="test",
        )

    # then
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The specified log group does not exist."


@mock_aws
def test_get_query_results():
    client = boto3.client("logs", "us-east-1")
    log_group_name = "test"
    log_stream_name = "stream"
    client.create_log_group(logGroupName=log_group_name)
    client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    data = [
        (
            int(unix_time_millis(utcnow() - timedelta(minutes=x))),
            f"event nr {x}",
        )
        for x in range(5)
    ]
    events = [{"timestamp": x, "message": y} for x, y in reversed(data)]

    client.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=events
    )

    query_id = client.start_query(
        logGroupName="test",
        startTime=int(unix_time(utcnow() - timedelta(minutes=10))),
        endTime=int(unix_time(utcnow() + timedelta(minutes=10))),
        queryString="fields @message",
    )["queryId"]

    resp = client.get_query_results(queryId=query_id)
    assert resp["status"] == "Complete"
    assert len(resp["results"]) == 5

    fields = set([row["field"] for field in resp["results"] for row in field])
    assert fields == {"@ptr", "@message"}

    messages = [
        row["value"]
        for field in resp["results"]
        for row in field
        if row["field"] == "@message"
    ]
    assert messages == [
        "event nr 4",
        "event nr 3",
        "event nr 2",
        "event nr 1",
        "event nr 0",
    ]

    # Only find events from last 2 minutes
    query_id = client.start_query(
        logGroupName="test",
        startTime=int(unix_time(utcnow() - timedelta(minutes=2, seconds=1))),
        endTime=int(unix_time(utcnow() - timedelta(seconds=1))),
        queryString="fields @message",
    )["queryId"]

    resp = client.get_query_results(queryId=query_id)
    assert len(resp["results"]) == 2

    messages = [
        row["value"]
        for field in resp["results"]
        for row in field
        if row["field"] == "@message"
    ]
    assert messages == ["event nr 2", "event nr 1"]


@mock_aws
def test_describe_completed_query():
    client = boto3.client("logs", "us-east-1")

    client.create_log_group(logGroupName="test")

    query_id = client.start_query(
        logGroupName="test",
        startTime=int(unix_time(utcnow() + timedelta(minutes=10))),
        endTime=int(unix_time(utcnow() + timedelta(minutes=10))),
        queryString="fields @message",
    )["queryId"]

    queries = client.describe_queries(logGroupName="test")["queries"]

    assert len(queries) == 1
    assert queries[0]["queryId"] == query_id
    assert queries[0]["queryString"] == "fields @message"
    assert queries[0]["status"] == "Complete"
    assert queries[0]["createTime"]
    assert queries[0]["logGroupName"] == "test"

    queries = client.describe_queries(logGroupName="test", status="Complete")["queries"]
    assert len(queries) == 1

    queries = client.describe_queries(logGroupName="test", status="Scheduled")[
        "queries"
    ]
    assert len(queries) == 0


@mock_aws
def test_describe_queries_on_log_group_without_any():
    client = boto3.client("logs", "us-east-1")

    client.create_log_group(logGroupName="test1")
    assert client.describe_queries(logGroupName="test1")["queries"] == []
