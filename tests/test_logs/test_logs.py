import json

import boto3
import os
import sure  # noqa
import six
from botocore.exceptions import ClientError

from moto import mock_logs, settings
from nose.tools import assert_raises
from nose import SkipTest

_logs_region = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


@mock_logs
def test_describe_metric_filters_happy():
    conn = boto3.client("logs", "us-west-2")

    response = put_metric_filter(conn)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_metric_filters(filterNamePrefix="filter")

    assert response["metricFilters"][0]["filterName"] == "filterName1"


@mock_logs
def test_describe_metric_filters_happy_metric_name():
    conn = boto3.client("logs", "us-west-2")

    response = put_metric_filter(conn)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_metric_filters(
        filterNamePrefix="filter",
        metricName="metricName1",
        metricNamespace="metricNamespace1",
    )

    assert response["metricFilters"][0]["filterName"] == "filterName1"


@mock_logs
def test_put_metric_filters_validation():
    conn = boto3.client("logs", "us-west-2")

    invalid_filter_name = "X" * 513
    invalid_filter_pattern = "X" * 1025
    invalid_metric_transformations = [
        {
            "defaultValue": 1,
            "metricName": "metricName",
            "metricNamespace": "metricNamespace",
            "metricValue": "metricValue",
        },
        {
            "defaultValue": 1,
            "metricName": "metricName",
            "metricNamespace": "metricNamespace",
            "metricValue": "metricValue",
        },
    ]

    test_cases = [
        build_put_case(
            name="Invalid filter name",
            expected=AssertionError,
            filter_name=invalid_filter_name,
        ),
        build_put_case(
            name="Invalid filter pattern",
            expected=AssertionError,
            filter_pattern=invalid_filter_pattern,
        ),
        build_put_case(
            name="Invalid filter metric transformations",
            expected=AssertionError,
            metric_transformations=invalid_metric_transformations,
        ),
    ]

    for test_case in test_cases:
        inputs = test_case["input"]
        conn.put_metric_filter.when.called_with(
            filterName=inputs["filterName"],
            filterPattern=inputs["filterPattern"],
            logGroupName=inputs["logGroupName"],
            metricTransformations=inputs["metricTransformations"],
        ).should.throw(test_case["expected"])


@mock_logs
def test_describe_metric_filters_validation():
    conn = boto3.client("logs", "us-west-2")

    length_over_512 = "X" * 513
    length_over_255 = "X" * 256

    test_cases = [
        build_describe_case(
            name="Invalid filter name prefix",
            expected=AssertionError,
            filter_name_prefix=length_over_512,
        ),
        build_describe_case(
            name="Invalid log group name",
            expected=AssertionError,
            log_group_name=length_over_512,
        ),
        build_describe_case(
            name="Invalid metric name",
            expected=AssertionError,
            metric_name=length_over_255,
        ),
        build_describe_case(
            name="Invalid metric namespace",
            expected=AssertionError,
            metric_namespace=length_over_255,
        ),
    ]

    for test_case in test_cases:
        conn.describe_metric_filter.when.called_with(test_case["input"]).should.throw(test_case["expected"])


@mock_logs
def test_describe_metric_filters_validation():
    conn = boto3.client("logs", "us-west-2")
    # conn.enable_key_rotation.when.called_with("not-a-key").should.throw(
    #     NotFoundException
    # )
    # assert response["ResponseMetadata"]["HTTPStatusCode"] != 200

    response = conn.describe_metric_filters(
        filterNamePrefix="filter",
        metricName="metricName1",
        metricNamespace="metricNamespace1",
    )

    # assert response["metricFilters"][0]["filterName"] == "filterName1"


@mock_logs
def test_describe_metric_filters_multiple_happy():
    conn = boto3.client("logs", "us-west-2")

    response = put_metric_filter(conn, 1)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = put_metric_filter(conn, 2)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    response = conn.describe_metric_filters(
        filterNamePrefix="filter", logGroupName="logGroupName1"
    )
    assert response["metricFilters"][0]["filterName"] == "filterName1"

    response = conn.describe_metric_filters(filterNamePrefix="filter")
    assert response["metricFilters"][0]["filterName"] == "filterName1"

    response = conn.describe_metric_filters(logGroupName="logGroupName1")
    assert response["metricFilters"][0]["filterName"] == "filterName1"


@mock_logs
def test_delete_metric_filter():
    conn = boto3.client("logs", "us-west-2")

    response = put_metric_filter(conn, 1)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = put_metric_filter(conn, 2)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.delete_metric_filter(
        filterName="filterName", logGroupName="logGroupName1"
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_metric_filters(
        filterNamePrefix="filter", logGroupName="logGroupName2"
    )
    assert response["metricFilters"][0]["filterName"] == "filterName2"

    response = conn.describe_metric_filters(logGroupName="logGroupName2")
    assert response["metricFilters"][0]["filterName"] == "filterName2"


def put_metric_filter(conn, count=1):
    count = str(count)
    return conn.put_metric_filter(
        filterName="filterName" + count,
        filterPattern="filterPattern" + count,
        logGroupName="logGroupName" + count,
        metricTransformations=[
            {
                "defaultValue": int(count),
                "metricName": "metricName" + count,
                "metricNamespace": "metricNamespace" + count,
                "metricValue": "metricValue" + count,
            },
        ],
    )


def build_put_case(name, expected, filter_name="filterName", filter_pattern="filterPattern",
                   log_group_name="logGroupName", metric_transformations=None):
    return {
        "name": name,
        "input":
            build_put_input(filter_name, filter_pattern, log_group_name, metric_transformations),
        "expected": expected
    }


def build_put_input(filter_name, filter_pattern, log_group_name, metric_transformations):
    if metric_transformations is None:
        metric_transformations = [
            {
                "defaultValue": 1,
                "metricName": "metricName",
                "metricNamespace": "metricNamespace",
                "metricValue": "metricValue",
            },
        ]
    return {
        "filterName": filter_name,
        "filterPattern": filter_pattern,
        "logGroupName": log_group_name,
        "metricTransformations": metric_transformations
    }


def build_describe_input(filter_name_prefix, log_group_name, metric_name, metric_namespace):
    return {
        "filterNamePrefix": filter_name_prefix,
        "logGroupName": log_group_name,
        "metricName": metric_name,
        "metricNamespace": metric_namespace
    }


def build_describe_case(name, expected, filter_name_prefix="filterNamePrefix", log_group_name="logGroupName",
                        metric_name="metricName", metric_namespace="metricNamespace"):
    return {
        "name": name,
        "input":
            build_describe_input(filter_name_prefix, log_group_name, metric_name, metric_namespace),
        "expected": expected
    }


@mock_logs
def test_log_group_create():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    # AWS defaults to Never Expire for log group retention
    assert response["logGroups"][0].get("retentionInDays") == None

    response = conn.delete_log_group(logGroupName=log_group_name)


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
