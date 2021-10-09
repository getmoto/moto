import json
import os
import time
import sure  # noqa
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_logs, settings
from moto.core.utils import unix_time_millis
from moto.logs.models import MAX_RESOURCE_POLICIES_PER_REGION

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


@pytest.fixture
def json_policy_doc():
    """Returns a policy document in JSON format.

    The ARN is bogus, but that shouldn't matter for the test.
    """
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Route53LogsToCloudWatchLogs",
                    "Effect": "Allow",
                    "Principal": {"Service": ["route53.amazonaws.com"]},
                    "Action": "logs:PutLogEvents",
                    "Resource": "log_arn",
                }
            ],
        }
    )


@mock_logs
def test_describe_metric_filters_happy_prefix():
    conn = boto3.client("logs", "us-west-2")

    response1 = put_metric_filter(conn, count=1)
    assert response1["ResponseMetadata"]["HTTPStatusCode"] == 200
    response2 = put_metric_filter(conn, count=2)
    assert response2["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_metric_filters(filterNamePrefix="filter")

    assert len(response["metricFilters"]) == 2
    assert response["metricFilters"][0]["filterName"] == "filterName1"
    assert response["metricFilters"][1]["filterName"] == "filterName2"


@mock_logs
def test_describe_metric_filters_happy_log_group_name():
    conn = boto3.client("logs", "us-west-2")

    response1 = put_metric_filter(conn, count=1)
    assert response1["ResponseMetadata"]["HTTPStatusCode"] == 200
    response2 = put_metric_filter(conn, count=2)
    assert response2["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_metric_filters(logGroupName="logGroupName2")

    assert len(response["metricFilters"]) == 1
    assert response["metricFilters"][0]["logGroupName"] == "logGroupName2"


@mock_logs
def test_describe_metric_filters_happy_metric_name():
    conn = boto3.client("logs", "us-west-2")

    response1 = put_metric_filter(conn, count=1)
    assert response1["ResponseMetadata"]["HTTPStatusCode"] == 200
    response2 = put_metric_filter(conn, count=2)
    assert response2["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_metric_filters(
        metricName="metricName1", metricNamespace="metricNamespace1",
    )

    assert len(response["metricFilters"]) == 1
    metrics = response["metricFilters"][0]["metricTransformations"]
    assert metrics[0]["metricName"] == "metricName1"
    assert metrics[0]["metricNamespace"] == "metricNamespace1"


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
        build_put_case(name="Invalid filter name", filter_name=invalid_filter_name,),
        build_put_case(
            name="Invalid filter pattern", filter_pattern=invalid_filter_pattern,
        ),
        build_put_case(
            name="Invalid filter metric transformations",
            metric_transformations=invalid_metric_transformations,
        ),
    ]

    for test_case in test_cases:
        with pytest.raises(ClientError) as exc:
            conn.put_metric_filter(**test_case["input"])
        response = exc.value.response
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
        response["Error"]["Code"].should.equal("InvalidParameterException")


@mock_logs
def test_describe_metric_filters_validation():
    conn = boto3.client("logs", "us-west-2")

    length_over_512 = "X" * 513
    length_over_255 = "X" * 256

    test_cases = [
        build_describe_case(
            name="Invalid filter name prefix", filter_name_prefix=length_over_512,
        ),
        build_describe_case(
            name="Invalid log group name", log_group_name=length_over_512,
        ),
        build_describe_case(name="Invalid metric name", metric_name=length_over_255,),
        build_describe_case(
            name="Invalid metric namespace", metric_namespace=length_over_255,
        ),
    ]

    for test_case in test_cases:
        with pytest.raises(ClientError) as exc:
            conn.describe_metric_filters(**test_case["input"])
        response = exc.value.response
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
        response["Error"]["Code"].should.equal("InvalidParameterException")


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


@mock_logs
@pytest.mark.parametrize(
    "filter_name, failing_constraint",
    [
        (
            "X" * 513,
            "Minimum length of 1. Maximum length of 512.",
        ),  # filterName too long
        ("x:x", "Must match pattern"),  # invalid filterName pattern
    ],
)
def test_delete_metric_filter_invalid_filter_name(filter_name, failing_constraint):
    conn = boto3.client("logs", "us-west-2")
    with pytest.raises(ClientError) as exc:
        conn.delete_metric_filter(filterName=filter_name, logGroupName="valid")
    response = exc.value.response
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    response["Error"]["Code"].should.equal("InvalidParameterException")
    response["Error"]["Message"].should.contain(
        f"Value '{filter_name}' at 'filterName' failed to satisfy constraint"
    )
    response["Error"]["Message"].should.contain(failing_constraint)


@mock_logs
@pytest.mark.parametrize(
    "log_group_name, failing_constraint",
    [
        (
            "X" * 513,
            "Minimum length of 1. Maximum length of 512.",
        ),  # logGroupName too long
        ("x!x", "Must match pattern"),  # invalid logGroupName pattern
    ],
)
def test_delete_metric_filter_invalid_log_group_name(
    log_group_name, failing_constraint
):
    conn = boto3.client("logs", "us-west-2")
    with pytest.raises(ClientError) as exc:
        conn.delete_metric_filter(filterName="valid", logGroupName=log_group_name)
    response = exc.value.response
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    response["Error"]["Code"].should.equal("InvalidParameterException")
    response["Error"]["Message"].should.contain(
        f"Value '{log_group_name}' at 'logGroupName' failed to satisfy constraint"
    )
    response["Error"]["Message"].should.contain(failing_constraint)


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


def build_put_case(
    name,
    filter_name="filterName",
    filter_pattern="filterPattern",
    log_group_name="logGroupName",
    metric_transformations=None,
):
    return {
        "name": name,
        "input": build_put_input(
            filter_name, filter_pattern, log_group_name, metric_transformations
        ),
    }


def build_put_input(
    filter_name, filter_pattern, log_group_name, metric_transformations
):
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
        "metricTransformations": metric_transformations,
    }


def build_describe_input(
    filter_name_prefix, log_group_name, metric_name, metric_namespace
):
    return {
        "filterNamePrefix": filter_name_prefix,
        "logGroupName": log_group_name,
        "metricName": metric_name,
        "metricNamespace": metric_namespace,
    }


def build_describe_case(
    name,
    filter_name_prefix="filterNamePrefix",
    log_group_name="logGroupName",
    metric_name="metricName",
    metric_namespace="metricNamespace",
):
    return {
        "name": name,
        "input": build_describe_input(
            filter_name_prefix, log_group_name, metric_name, metric_namespace
        ),
    }


@mock_logs
@pytest.mark.parametrize(
    "kms_key_id",
    [
        "arn:aws:kms:us-east-1:000000000000:key/51d81fab-b138-4bd2-8a09-07fd6d37224d",
        None,
    ],
)
def test_create_log_group(kms_key_id):
    # Given
    conn = boto3.client("logs", TEST_REGION)

    create_logs_params = dict(logGroupName="dummy")
    if kms_key_id:
        create_logs_params["kmsKeyId"] = kms_key_id

    # When
    response = conn.create_log_group(**create_logs_params)
    response = conn.describe_log_groups()

    # Then
    response["logGroups"].should.have.length_of(1)

    log_group = response["logGroups"][0]
    log_group.should_not.have.key("retentionInDays")

    if kms_key_id:
        log_group.should.have.key("kmsKeyId")
        log_group["kmsKeyId"].should.equal(kms_key_id)


@mock_logs
def test_exceptions():
    conn = boto3.client("logs", TEST_REGION)
    log_group_name = "dummy"
    log_stream_name = "dummp-stream"
    conn.create_log_group(logGroupName=log_group_name)
    with pytest.raises(ClientError):
        conn.create_log_group(logGroupName=log_group_name)

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
    conn = boto3.client("logs", TEST_REGION)
    log_group_name = "dummy"
    log_stream_name = "stream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    messages = [
        {"timestamp": 0, "message": "hello"},
        {"timestamp": 0, "message": "world"},
    ]
    put_results = conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    res = conn.get_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name
    )
    events = res["events"]
    next_sequence_token = put_results["nextSequenceToken"]
    assert isinstance(next_sequence_token, str)
    assert len(next_sequence_token) == 56
    events.should.have.length_of(2)


@mock_logs
def test_filter_logs_interleaved():
    conn = boto3.client("logs", TEST_REGION)
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
    conn = boto3.client("logs", TEST_REGION)
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
    conn = boto3.client("logs", TEST_REGION)
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
    conn = boto3.client("logs", TEST_REGION)
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.put_retention_policy(logGroupName=log_group_name, retentionInDays=7)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") == 7

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_delete_retention_policy():
    conn = boto3.client("logs", TEST_REGION)
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.put_retention_policy(logGroupName=log_group_name, retentionInDays=7)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") == 7

    response = conn.delete_retention_policy(logGroupName=log_group_name)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") is None

    conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_put_resource_policy():
    client = boto3.client("logs", TEST_REGION)

    # For this test a policy document with a valid ARN will be used.
    log_group_name = "test_log_group"
    client.create_log_group(logGroupName=log_group_name)
    log_group_info = client.describe_log_groups(logGroupNamePrefix=log_group_name)

    policy_name = "test_policy"
    policy_doc = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Route53LogsToCloudWatchLogs",
                    "Effect": "Allow",
                    "Principal": {"Service": ["route53.amazonaws.com"]},
                    "Action": "logs:PutLogEvents",
                    "Resource": log_group_info["logGroups"][0]["arn"],
                }
            ],
        }
    )
    response = client.put_resource_policy(
        policyName=policy_name, policyDocument=policy_doc
    )

    assert response["resourcePolicy"]["policyName"] == policy_name
    assert response["resourcePolicy"]["policyDocument"] == policy_doc
    assert response["resourcePolicy"]["lastUpdatedTime"] <= int(unix_time_millis())

    client.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_put_resource_policy_too_many(json_policy_doc):
    client = boto3.client("logs", TEST_REGION)

    # Create the maximum number of resource policies.
    for idx in range(MAX_RESOURCE_POLICIES_PER_REGION):
        policy_name = f"test_policy_{idx}"
        client.put_resource_policy(
            policyName=policy_name, policyDocument=json.dumps(json_policy_doc)
        )

    # Now create one more policy, which should generate an error.
    with pytest.raises(ClientError) as exc:
        client.put_resource_policy(
            policyName="too_many", policyDocument=json.dumps(json_policy_doc)
        )
    exc_value = exc.value
    exc_value.operation_name.should.equal("PutResourcePolicy")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("LimitExceededException")
    exc_value.response["Error"]["Message"].should.contain("Resource limit exceeded.")


@mock_logs
def test_delete_resource_policy(json_policy_doc):
    client = boto3.client("logs", TEST_REGION)

    # Create a bunch of resource policies so we can give delete a workout.
    base_policy_name = "test_policy"
    for idx in range(MAX_RESOURCE_POLICIES_PER_REGION):
        client.put_resource_policy(
            policyName=f"{base_policy_name}_{idx}", policyDocument=json_policy_doc
        )

    # Verify that all those resource policies can be deleted.
    for idx in range(MAX_RESOURCE_POLICIES_PER_REGION):
        client.delete_resource_policy(policyName=f"{base_policy_name}_{idx}")

    # Verify there are no resource policies.
    response = client.describe_resource_policies()
    policies = response["resourcePolicies"]
    assert not policies

    # Try deleting a non-existent resource policy.
    with pytest.raises(ClientError) as exc:
        client.delete_resource_policy(policyName="non-existent")
    exc_value = exc.value
    exc_value.operation_name.should.equal("DeleteResourcePolicy")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    exc_value.response["Error"]["Message"].should.contain(
        "Policy with name [non-existent] does not exist"
    )


@mock_logs
def test_describe_resource_policies(json_policy_doc):
    client = boto3.client("logs", TEST_REGION)

    # Create the maximum number of resource policies so there's something
    # to retrieve.
    for idx in range(MAX_RESOURCE_POLICIES_PER_REGION):
        policy_name = f"test_policy_{idx}"
        client.put_resource_policy(
            policyName=policy_name, policyDocument=json_policy_doc
        )

    # Retrieve all of the resource policies that were just created.
    response = client.describe_resource_policies(limit=50)
    assert "resourcePolicies" in response
    policies = response["resourcePolicies"]
    assert len(policies) == MAX_RESOURCE_POLICIES_PER_REGION

    # Verify the retrieved list is valid.
    now_millis = int(unix_time_millis())
    for idx, policy in enumerate(policies):
        assert policy["policyName"] == f"test_policy_{idx}"
        assert policy["policyDocument"] == json_policy_doc
        assert policy["lastUpdatedTime"] <= now_millis


@mock_logs
def test_get_log_events():
    client = boto3.client("logs", TEST_REGION)
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
    client = boto3.client("logs", TEST_REGION)
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
    client = boto3.client("logs", TEST_REGION)
    log_group_name = "test"
    log_stream_name = "stream"
    client.create_log_group(logGroupName=log_group_name)
    client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    with pytest.raises(ClientError) as exc:
        client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            nextToken="n/00000000000000000000000000000000000000000000000000000000",
        )
    exc_value = exc.value
    exc_value.operation_name.should.equal("GetLogEvents")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterException")
    exc_value.response["Error"]["Message"].should.contain(
        "The specified nextToken is invalid."
    )

    with pytest.raises(ClientError) as exc:
        client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            nextToken="not-existing-token",
        )
    exc_value = exc.value
    exc_value.operation_name.should.equal("GetLogEvents")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.equal("InvalidParameterException")
    exc_value.response["Error"]["Message"].should.contain(
        "The specified nextToken is invalid."
    )


@mock_logs
def test_list_tags_log_group():
    conn = boto3.client("logs", TEST_REGION)
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
    conn = boto3.client("logs", TEST_REGION)
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
    conn = boto3.client("logs", TEST_REGION)
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
    with pytest.raises(ClientError) as exc:
        client.describe_subscription_filters(logGroupName="not-existing-log-group",)

    # then
    exc_value = exc.value
    exc_value.operation_name.should.equal("DescribeSubscriptionFilters")
    exc_value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    exc_value.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    exc_value.response["Error"]["Message"].should.equal(
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
    resp.should.have.key("nextToken")

    resp = client.describe_log_groups(nextToken=resp["nextToken"], limit=1)
    resp["logGroups"].should.have.length_of(1)
    resp.should.have.key("nextToken")

    resp = client.describe_log_groups(nextToken=resp["nextToken"])
    resp["logGroups"].should.have.length_of(1)
    resp["logGroups"][0]["logGroupName"].should.equal("/aws/lambda/lowercase-dev")
    resp.should_not.have.key("nextToken")

    resp = client.describe_log_groups(nextToken="invalid-token")
    resp["logGroups"].should.have.length_of(0)
    resp.should_not.have.key("nextToken")


@mock_logs
def test_describe_log_streams_simple_paging():
    client = boto3.client("logs", "us-east-1")

    group_name = "/aws/lambda/lowercase-dev"

    client.create_log_group(logGroupName=group_name)
    stream_names = ["stream" + str(i) for i in range(0, 10)]
    for name in stream_names:
        client.create_log_stream(logGroupName=group_name, logStreamName=name)

    # Get stream 1-10
    resp = client.describe_log_streams(logGroupName=group_name)
    resp["logStreams"].should.have.length_of(10)
    resp.should_not.have.key("nextToken")

    # Get stream 1-4
    resp = client.describe_log_streams(logGroupName=group_name, limit=4)
    resp["logStreams"].should.have.length_of(4)
    [l["logStreamName"] for l in resp["logStreams"]].should.equal(
        ["stream0", "stream1", "stream2", "stream3"]
    )
    resp.should.have.key("nextToken")

    # Get stream 4-8
    resp = client.describe_log_streams(
        logGroupName=group_name, limit=4, nextToken=str(resp["nextToken"])
    )
    resp["logStreams"].should.have.length_of(4)
    [l["logStreamName"] for l in resp["logStreams"]].should.equal(
        ["stream4", "stream5", "stream6", "stream7"]
    )
    resp.should.have.key("nextToken")

    # Get stream 8-10
    resp = client.describe_log_streams(
        logGroupName=group_name, limit=4, nextToken=str(resp["nextToken"])
    )
    resp["logStreams"].should.have.length_of(2)
    [l["logStreamName"] for l in resp["logStreams"]].should.equal(
        ["stream8", "stream9"]
    )
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
        "{}@{}".format(log_group_name, resp["logStreams"][1]["logStreamName"])
    )

    resp = client.describe_log_streams(
        logGroupName=log_group_name, nextToken=resp["nextToken"], limit=1
    )
    resp["logStreams"].should.have.length_of(1)
    resp["logStreams"][0]["arn"].should.contain(log_group_name)
    resp["nextToken"].should.equal(
        "{}@{}".format(log_group_name, resp["logStreams"][0]["logStreamName"])
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

    with pytest.raises(ClientError) as exc:
        client.start_query(
            logGroupName="/aws/codebuild/lowercase-dev-invalid",
            startTime=int(time.time()),
            endTime=int(time.time()) + 300,
            queryString="test",
        )

    # then
    exc_value = exc.value
    exc_value.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    exc_value.response["Error"]["Message"].should.equal(
        "The specified log group does not exist"
    )


@pytest.mark.parametrize("nr_of_events", [10001, 1000000])
@mock_logs
def test_get_too_many_log_events(nr_of_events):
    client = boto3.client("logs", "us-east-1")
    log_group_name = "dummy"
    log_stream_name = "stream"
    client.create_log_group(logGroupName=log_group_name)
    client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    with pytest.raises(ClientError) as ex:
        client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            limit=nr_of_events,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterException")
    err["Message"].should.contain("1 validation error detected")
    err["Message"].should.contain(
        "Value '{}' at 'limit' failed to satisfy constraint".format(nr_of_events)
    )
    err["Message"].should.contain("Member must have value less than or equal to 10000")


@pytest.mark.parametrize("nr_of_events", [10001, 1000000])
@mock_logs
def test_filter_too_many_log_events(nr_of_events):
    client = boto3.client("logs", "us-east-1")
    log_group_name = "dummy"
    log_stream_name = "stream"
    client.create_log_group(logGroupName=log_group_name)
    client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    with pytest.raises(ClientError) as ex:
        client.filter_log_events(
            logGroupName=log_group_name,
            logStreamNames=[log_stream_name],
            limit=nr_of_events,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterException")
    err["Message"].should.contain("1 validation error detected")
    err["Message"].should.contain(
        "Value '{}' at 'limit' failed to satisfy constraint".format(nr_of_events)
    )
    err["Message"].should.contain("Member must have value less than or equal to 10000")


@pytest.mark.parametrize("nr_of_groups", [51, 100])
@mock_logs
def test_describe_too_many_log_groups(nr_of_groups):
    client = boto3.client("logs", "us-east-1")
    with pytest.raises(ClientError) as ex:
        client.describe_log_groups(limit=nr_of_groups)
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterException")
    err["Message"].should.contain("1 validation error detected")
    err["Message"].should.contain(
        "Value '{}' at 'limit' failed to satisfy constraint".format(nr_of_groups)
    )
    err["Message"].should.contain("Member must have value less than or equal to 50")


@pytest.mark.parametrize("nr_of_streams", [51, 100])
@mock_logs
def test_describe_too_many_log_streams(nr_of_streams):
    client = boto3.client("logs", "us-east-1")
    log_group_name = "dummy"
    client.create_log_group(logGroupName=log_group_name)
    with pytest.raises(ClientError) as ex:
        client.describe_log_streams(logGroupName=log_group_name, limit=nr_of_streams)
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterException")
    err["Message"].should.contain("1 validation error detected")
    err["Message"].should.contain(
        "Value '{}' at 'limit' failed to satisfy constraint".format(nr_of_streams)
    )
    err["Message"].should.contain("Member must have value less than or equal to 50")


@pytest.mark.parametrize("length", [513, 1000])
@mock_logs
def test_create_log_group_invalid_name_length(length):
    log_group_name = "a" * length
    client = boto3.client("logs", "us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_log_group(logGroupName=log_group_name)
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterException")
    err["Message"].should.contain("1 validation error detected")
    err["Message"].should.contain(
        "Value '{}' at 'logGroupName' failed to satisfy constraint".format(
            log_group_name
        )
    )
    err["Message"].should.contain("Member must have length less than or equal to 512")


@pytest.mark.parametrize("invalid_orderby", ["", "sth", "LogStreamname"])
@mock_logs
def test_describe_log_streams_invalid_order_by(invalid_orderby):
    client = boto3.client("logs", "us-east-1")
    log_group_name = "dummy"
    client.create_log_group(logGroupName=log_group_name)
    with pytest.raises(ClientError) as ex:
        client.describe_log_streams(
            logGroupName=log_group_name, orderBy=invalid_orderby
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterException")
    err["Message"].should.contain("1 validation error detected")
    err["Message"].should.contain(
        "Value '{}' at 'orderBy' failed to satisfy constraint".format(invalid_orderby)
    )
    err["Message"].should.contain(
        "Member must satisfy enum value set: [LogStreamName, LastEventTime]"
    )


@mock_logs
def test_describe_log_streams_no_prefix():
    """
    From the docs: If orderBy is LastEventTime , you cannot specify [logStreamNamePrefix]
    """
    client = boto3.client("logs", "us-east-1")
    log_group_name = "dummy"
    client.create_log_group(logGroupName=log_group_name)
    with pytest.raises(ClientError) as ex:
        client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy="LastEventTime",
            logStreamNamePrefix="sth",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterException")
    err["Message"].should.equal(
        "Cannot order by LastEventTime with a logStreamNamePrefix."
    )
