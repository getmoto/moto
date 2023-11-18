import json
from datetime import timedelta
from uuid import UUID

import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_logs, mock_s3, settings
from moto.core.utils import unix_time_millis, utcnow
from moto.logs.models import MAX_RESOURCE_POLICIES_PER_REGION

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


"""Returns a policy document in JSON format.

The ARN is bogus, but that shouldn't matter for the test.
"""
json_policy_doc = json.dumps(
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

access_policy_doc = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "logs.us-east-1.amazonaws.com"},
                "Action": "logs:PutSubscriptionFilter",
                "Resource": "destination_arn",
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
        metricName="metricName1", metricNamespace="metricNamespace1"
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
        build_put_case(name="Invalid filter name", filter_name=invalid_filter_name),
        build_put_case(
            name="Invalid filter pattern", filter_pattern=invalid_filter_pattern
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
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert response["Error"]["Code"] == "InvalidParameterException"


@mock_logs
def test_describe_metric_filters_validation():
    conn = boto3.client("logs", "us-west-2")

    length_over_512 = "X" * 513
    length_over_255 = "X" * 256

    test_cases = [
        build_describe_case(
            name="Invalid filter name prefix", filter_name_prefix=length_over_512
        ),
        build_describe_case(
            name="Invalid log group name", log_group_name=length_over_512
        ),
        build_describe_case(name="Invalid metric name", metric_name=length_over_255),
        build_describe_case(
            name="Invalid metric namespace", metric_namespace=length_over_255
        ),
    ]

    for test_case in test_cases:
        with pytest.raises(ClientError) as exc:
            conn.describe_metric_filters(**test_case["input"])
        response = exc.value.response
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert response["Error"]["Code"] == "InvalidParameterException"


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
    client = boto3.client("logs", "us-west-2")

    lg_name = "/hello-world/my-cool-endpoint"
    client.create_log_group(logGroupName=lg_name)
    client.put_metric_filter(
        logGroupName=lg_name,
        filterName="my-cool-filter",
        filterPattern="{ $.val = * }",
        metricTransformations=[
            {
                "metricName": "my-metric",
                "metricNamespace": "my-namespace",
                "metricValue": "$.value",
            }
        ],
    )

    response = client.delete_metric_filter(
        filterName="filterName", logGroupName=lg_name
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.describe_metric_filters(
        filterNamePrefix="filter", logGroupName="logGroupName2"
    )
    assert response["metricFilters"] == []


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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert response["Error"]["Code"] == "InvalidParameterException"
    assert (
        f"Value '{filter_name}' at 'filterName' failed to satisfy constraint"
        in response["Error"]["Message"]
    )
    assert failing_constraint in response["Error"]["Message"]


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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert response["Error"]["Code"] == "InvalidParameterException"
    assert (
        f"Value '{log_group_name}' at 'logGroupName' failed to satisfy constraint"
        in response["Error"]["Message"]
    )
    assert failing_constraint in response["Error"]["Message"]


@mock_logs
def test_destinations():
    conn = boto3.client("logs", "us-west-2")
    destination_name = "test-destination"
    role_arn = "arn:aws:iam::123456789012:role/my-subscription-role"
    target_arn = "arn:aws:kinesis:us-east-1:123456789012:stream/my-kinesis-stream"
    role_arn_updated = "arn:aws:iam::123456789012:role/my-subscription-role-updated"
    target_arn_updated = (
        "arn:aws:kinesis:us-east-1:123456789012:stream/my-kinesis-stream-updated"
    )

    response = conn.describe_destinations(DestinationNamePrefix=destination_name)
    assert len(response["destinations"]) == 0

    response = conn.put_destination(
        destinationName=destination_name,
        targetArn=target_arn,
        roleArn=role_arn,
        tags={"Name": destination_name},
    )
    assert response["destination"]["destinationName"] == destination_name
    assert response["destination"]["targetArn"] == target_arn
    assert response["destination"]["roleArn"] == role_arn

    response = conn.describe_destinations(DestinationNamePrefix=destination_name)
    assert len(response["destinations"]) == 1
    assert response["destinations"][0]["destinationName"] == destination_name
    assert response["destinations"][0]["targetArn"] == target_arn
    assert response["destinations"][0]["roleArn"] == role_arn

    response = conn.put_destination(
        destinationName=destination_name,
        targetArn=target_arn_updated,
        roleArn=role_arn_updated,
        tags={"Name": destination_name},
    )
    assert response["destination"]["destinationName"] == destination_name
    assert response["destination"]["targetArn"] == target_arn_updated
    assert response["destination"]["roleArn"] == role_arn_updated

    response = conn.describe_destinations(DestinationNamePrefix=destination_name)
    assert len(response["destinations"]) == 1
    assert response["destinations"][0]["destinationName"] == destination_name
    assert response["destinations"][0]["targetArn"] == target_arn_updated
    assert response["destinations"][0]["roleArn"] == role_arn_updated

    response = conn.put_destination_policy(
        destinationName=destination_name, accessPolicy=access_policy_doc
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_destinations(DestinationNamePrefix=destination_name)
    assert response["destinations"][0]["accessPolicy"] == access_policy_doc

    conn.put_destination(
        destinationName=f"{destination_name}-1",
        targetArn=target_arn,
        roleArn=role_arn,
        tags={"Name": destination_name},
    )
    response = conn.describe_destinations(DestinationNamePrefix=destination_name)
    assert len(response["destinations"]) == 2

    response = conn.describe_destinations(DestinationNamePrefix=f"{destination_name}-1")
    assert len(response["destinations"]) == 1

    response = conn.delete_destination(destinationName=f"{destination_name}-1")
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_destinations(DestinationNamePrefix=destination_name)
    assert len(response["destinations"]) == 1

    response = conn.delete_destination(destinationName=destination_name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


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
    conn.create_log_group(**create_logs_params)
    response = conn.describe_log_groups()

    # Then
    assert len(response["logGroups"]) == 1

    log_group = response["logGroups"][0]
    assert "retentionInDays" not in log_group

    if kms_key_id:
        assert "kmsKeyId" in log_group
        assert log_group["kmsKeyId"] == kms_key_id


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
    assert error["Code"] == "ResourceNotFoundException"
    assert error["Message"] == "The specified log stream does not exist."


@mock_logs
def test_put_logs():
    conn = boto3.client("logs", TEST_REGION)
    log_group_name = "dummy"
    log_stream_name = "stream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    messages = [
        {"timestamp": int(unix_time_millis()), "message": "hello"},
        {"timestamp": int(unix_time_millis()), "message": "world"},
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
    assert len(events) == 2


@mock_logs
def test_put_log_events_in_wrong_order():
    conn = boto3.client("logs", "us-east-1")
    log_group_name = "test"
    log_stream_name = "teststream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    ts_1 = int(unix_time_millis(utcnow() - timedelta(days=2)))
    ts_2 = int(unix_time_millis(utcnow() - timedelta(days=5)))

    messages = [
        {"message": f"Message {idx}", "timestamp": ts}
        for idx, ts in enumerate([ts_1, ts_2])
    ]

    with pytest.raises(ClientError) as exc:
        conn.put_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            logEvents=messages,
            sequenceToken="49599396607703531511419593985621160512859251095480828066",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Log events in a single PutLogEvents request must be in chronological order."
    )


@mock_logs
@pytest.mark.parametrize("days_ago", [15, 400])
def test_put_log_events_in_the_past(days_ago):
    conn = boto3.client("logs", "us-east-1")
    log_group_name = "test"
    log_stream_name = "teststream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    timestamp = int(unix_time_millis(utcnow() - timedelta(days=days_ago)))

    messages = [{"message": "Message number {}", "timestamp": timestamp}]

    resp = conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    assert resp["rejectedLogEventsInfo"] == {"tooOldLogEventEndIndex": 0}


@mock_logs
@pytest.mark.parametrize("minutes", [181, 300, 999999])
def test_put_log_events_in_the_future(minutes):
    conn = boto3.client("logs", "us-east-1")
    log_group_name = "test"
    log_stream_name = "teststream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    timestamp = int(unix_time_millis(utcnow() + timedelta(minutes=minutes)))

    messages = [{"message": "Message number {}", "timestamp": timestamp}]

    resp = conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    assert resp["rejectedLogEventsInfo"] == {"tooNewLogEventStartIndex": 0}


@mock_logs
def test_put_retention_policy():
    conn = boto3.client("logs", TEST_REGION)
    log_group_name = "dummy"
    conn.create_log_group(logGroupName=log_group_name)

    conn.put_retention_policy(logGroupName=log_group_name, retentionInDays=7)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") == 7

    conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_delete_log_stream():
    logs = boto3.client("logs", TEST_REGION)
    logs.create_log_group(logGroupName="logGroup")
    logs.create_log_stream(logGroupName="logGroup", logStreamName="logStream")
    resp = logs.describe_log_streams(logGroupName="logGroup")
    assert resp["logStreams"][0]["logStreamName"] == "logStream"
    logs.delete_log_stream(logGroupName="logGroup", logStreamName="logStream")
    resp = logs.describe_log_streams(logGroupName="logGroup")
    assert resp["logStreams"] == []


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

    # put_resource_policy with same policy name should update the resouce
    created_time = response["resourcePolicy"]["lastUpdatedTime"]
    with freeze_time(timedelta(minutes=1)):
        new_document = '{"Statement":[{"Action":"logs:*","Effect":"Allow","Principal":"*","Resource":"*"}]}'
        policy_info = client.put_resource_policy(
            policyName=policy_name, policyDocument=new_document
        )["resourcePolicy"]
        assert policy_info["policyName"] == policy_name
        assert policy_info["policyDocument"] == new_document
        assert created_time < policy_info["lastUpdatedTime"] <= int(unix_time_millis())


@mock_logs
def test_put_resource_policy_too_many():
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
    assert exc_value.operation_name == "PutResourcePolicy"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "LimitExceededException"
    assert "Resource limit exceeded." in exc_value.response["Error"]["Message"]

    # put_resource_policy on already created policy, shouldnt throw any error
    client.put_resource_policy(
        policyName="test_policy_1", policyDocument=json.dumps(json_policy_doc)
    )


@mock_logs
def test_delete_resource_policy():
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
    assert exc_value.operation_name == "DeleteResourcePolicy"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        "Policy with name [non-existent] does not exist"
        in exc_value.response["Error"]["Message"]
    )


@mock_logs
def test_describe_resource_policies():
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

    data = [
        (int(unix_time_millis(utcnow() + timedelta(milliseconds=x))), str(x))
        for x in range(20)
    ]
    events = [{"timestamp": x, "message": y} for x, y in data]

    client.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=events
    )

    resp = client.get_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, limit=10
    )

    assert len(resp["events"]) == 10
    for idx, (x, y) in enumerate(data[10:]):
        assert resp["events"][idx]["timestamp"] == x
        assert resp["events"][idx]["message"] == y
    assert (
        resp["nextForwardToken"]
        == "f/00000000000000000000000000000000000000000000000000000019"
    )
    assert (
        resp["nextBackwardToken"]
        == "b/00000000000000000000000000000000000000000000000000000010"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextBackwardToken"],
        limit=20,
    )

    assert len(resp["events"]) == 10
    for idx, (x, y) in enumerate(data[0:10]):
        assert resp["events"][idx]["timestamp"] == x
        assert resp["events"][idx]["message"] == y
    assert (
        resp["nextForwardToken"]
        == "f/00000000000000000000000000000000000000000000000000000009"
    )
    assert (
        resp["nextBackwardToken"]
        == "b/00000000000000000000000000000000000000000000000000000000"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextBackwardToken"],
        limit=10,
    )

    assert len(resp["events"]) == 0
    assert (
        resp["nextForwardToken"]
        == "f/00000000000000000000000000000000000000000000000000000000"
    )
    assert (
        resp["nextBackwardToken"]
        == "b/00000000000000000000000000000000000000000000000000000000"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextForwardToken"],
        limit=1,
    )

    assert len(resp["events"]) == 1
    x, y = data[1]
    assert resp["events"][0]["timestamp"] == x
    assert resp["events"][0]["message"] == y
    assert (
        resp["nextForwardToken"]
        == "f/00000000000000000000000000000000000000000000000000000001"
    )
    assert (
        resp["nextBackwardToken"]
        == "b/00000000000000000000000000000000000000000000000000000001"
    )


@mock_logs
def test_get_log_events_with_start_from_head():
    client = boto3.client("logs", TEST_REGION)
    log_group_name = "test"
    log_stream_name = "stream"
    client.create_log_group(logGroupName=log_group_name)
    client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    data = [
        (int(unix_time_millis(utcnow() + timedelta(milliseconds=x))), str(x))
        for x in range(20)
    ]
    events = [{"timestamp": x, "message": y} for x, y in data]

    client.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=events
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        limit=10,
        startFromHead=True,  # this parameter is only relevant without the usage of nextToken
    )

    assert len(resp["events"]) == 10
    for idx, (x, y) in enumerate(data[0:10]):
        assert resp["events"][idx]["timestamp"] == x
        assert resp["events"][idx]["message"] == y
    assert (
        resp["nextForwardToken"]
        == "f/00000000000000000000000000000000000000000000000000000009"
    )
    assert (
        resp["nextBackwardToken"]
        == "b/00000000000000000000000000000000000000000000000000000000"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextForwardToken"],
        limit=20,
    )

    assert len(resp["events"]) == 10
    for idx, (x, y) in enumerate(data[10:]):
        assert resp["events"][idx]["timestamp"] == x
        assert resp["events"][idx]["message"] == y
    assert (
        resp["nextForwardToken"]
        == "f/00000000000000000000000000000000000000000000000000000019"
    )
    assert (
        resp["nextBackwardToken"]
        == "b/00000000000000000000000000000000000000000000000000000010"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextForwardToken"],
        limit=10,
    )

    assert len(resp["events"]) == 0
    assert (
        resp["nextForwardToken"]
        == "f/00000000000000000000000000000000000000000000000000000019"
    )
    assert (
        resp["nextBackwardToken"]
        == "b/00000000000000000000000000000000000000000000000000000019"
    )

    resp = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextBackwardToken"],
        limit=1,
    )

    assert len(resp["events"]) == 1
    x, y = data[18]
    assert resp["events"][0]["timestamp"] == x
    assert resp["events"][0]["message"] == y
    assert (
        resp["nextForwardToken"]
        == "f/00000000000000000000000000000000000000000000000000000018"
    )
    assert (
        resp["nextBackwardToken"]
        == "b/00000000000000000000000000000000000000000000000000000018"
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
    assert exc_value.operation_name == "GetLogEvents"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        "The specified nextToken is invalid." in exc_value.response["Error"]["Message"]
    )

    with pytest.raises(ClientError) as exc:
        client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            nextToken="not-existing-token",
        )
    exc_value = exc.value
    assert exc_value.operation_name == "GetLogEvents"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert exc_value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        "The specified nextToken is invalid." in exc_value.response["Error"]["Message"]
    )


@mock_logs
def test_list_tags_log_group():
    conn = boto3.client("logs", TEST_REGION)
    log_group_name = "dummy"
    tags = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}

    conn.create_log_group(logGroupName=log_group_name)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == {}

    conn.delete_log_group(logGroupName=log_group_name)
    conn.create_log_group(logGroupName=log_group_name, tags=tags)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags

    conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_tag_log_group():
    conn = boto3.client("logs", TEST_REGION)
    log_group_name = "dummy"
    tags = {"tag_key_1": "tag_value_1"}
    conn.create_log_group(logGroupName=log_group_name)

    conn.tag_log_group(logGroupName=log_group_name, tags=tags)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags

    tags_with_added_value = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}
    conn.tag_log_group(logGroupName=log_group_name, tags={"tag_key_2": "tag_value_2"})
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags_with_added_value

    tags_with_updated_value = {"tag_key_1": "tag_value_XX", "tag_key_2": "tag_value_2"}
    conn.tag_log_group(logGroupName=log_group_name, tags={"tag_key_1": "tag_value_XX"})
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags_with_updated_value

    conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_untag_log_group():
    conn = boto3.client("logs", TEST_REGION)
    log_group_name = "dummy"
    conn.create_log_group(logGroupName=log_group_name)

    tags = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}
    conn.tag_log_group(logGroupName=log_group_name, tags=tags)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags

    tags_to_remove = ["tag_key_1"]
    remaining_tags = {"tag_key_2": "tag_value_2"}
    conn.untag_log_group(logGroupName=log_group_name, tags=tags_to_remove)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == remaining_tags

    conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_describe_subscription_filters():
    # given
    client = boto3.client("logs", "us-east-1")
    log_group_name = "/test"
    client.create_log_group(logGroupName=log_group_name)

    # when
    response = client.describe_subscription_filters(logGroupName=log_group_name)

    # then
    assert len(response["subscriptionFilters"]) == 0


@mock_logs
def test_describe_subscription_filters_errors():
    # given
    client = boto3.client("logs", "us-east-1")

    # when
    with pytest.raises(ClientError) as exc:
        client.describe_subscription_filters(logGroupName="not-existing-log-group")

    # then
    exc_value = exc.value
    assert exc_value.operation_name == "DescribeSubscriptionFilters"
    assert exc_value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "ResourceNotFoundException" in exc_value.response["Error"]["Code"]
    assert (
        exc_value.response["Error"]["Message"]
        == "The specified log group does not exist"
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
    assert len(resp["logGroups"]) == 4
    assert "nextToken" not in resp

    resp = client.describe_log_groups(limit=2)
    assert len(resp["logGroups"]) == 2
    assert "nextToken" in resp

    resp = client.describe_log_groups(nextToken=resp["nextToken"], limit=1)
    assert len(resp["logGroups"]) == 1
    assert "nextToken" in resp

    resp = client.describe_log_groups(nextToken=resp["nextToken"])
    assert len(resp["logGroups"]) == 1
    assert resp["logGroups"][0]["logGroupName"] == "/aws/lambda/lowercase-dev"
    assert "nextToken" not in resp

    resp = client.describe_log_groups(nextToken="invalid-token")
    assert len(resp["logGroups"]) == 0
    assert "nextToken" not in resp


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
    assert len(resp["logStreams"]) == 10
    assert "nextToken" not in resp

    # Get stream 1-4
    resp = client.describe_log_streams(logGroupName=group_name, limit=4)
    assert len(resp["logStreams"]) == 4
    assert [stream["logStreamName"] for stream in resp["logStreams"]] == [
        "stream0",
        "stream1",
        "stream2",
        "stream3",
    ]
    assert "nextToken" in resp

    # Get stream 4-8
    resp = client.describe_log_streams(
        logGroupName=group_name, limit=4, nextToken=str(resp["nextToken"])
    )
    assert len(resp["logStreams"]) == 4
    assert [stream["logStreamName"] for stream in resp["logStreams"]] == [
        "stream4",
        "stream5",
        "stream6",
        "stream7",
    ]
    assert "nextToken" in resp

    # Get stream 8-10
    resp = client.describe_log_streams(
        logGroupName=group_name, limit=4, nextToken=str(resp["nextToken"])
    )
    assert len(resp["logStreams"]) == 2
    assert [stream["logStreamName"] for stream in resp["logStreams"]] == [
        "stream8",
        "stream9",
    ]
    assert "nextToken" not in resp


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
    assert len(resp["logStreams"]) == 4
    assert log_group_name in resp["logStreams"][0]["arn"]
    assert "nextToken" not in resp

    resp = client.describe_log_streams(logGroupName=log_group_name, limit=2)
    assert len(resp["logStreams"]) == 2
    assert log_group_name in resp["logStreams"][0]["arn"]
    assert (
        resp["nextToken"]
        == f"{log_group_name}@{resp['logStreams'][1]['logStreamName']}"
    )

    resp = client.describe_log_streams(
        logGroupName=log_group_name, nextToken=resp["nextToken"], limit=1
    )
    assert len(resp["logStreams"]) == 1
    assert log_group_name in resp["logStreams"][0]["arn"]
    assert (
        resp["nextToken"]
        == f"{log_group_name}@{resp['logStreams'][0]['logStreamName']}"
    )

    resp = client.describe_log_streams(
        logGroupName=log_group_name, nextToken=resp["nextToken"]
    )
    assert len(resp["logStreams"]) == 1
    assert log_group_name in resp["logStreams"][0]["arn"]
    assert "nextToken" not in resp

    resp = client.describe_log_streams(
        logGroupName=log_group_name, nextToken="invalid-token"
    )
    assert len(resp["logStreams"]) == 0
    assert "nextToken" not in resp

    resp = client.describe_log_streams(
        logGroupName=log_group_name, nextToken="invalid@token"
    )
    assert len(resp["logStreams"]) == 0
    assert "nextToken" not in resp


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
    assert err["Code"] == "InvalidParameterException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{nr_of_events}' at 'limit' failed to satisfy constraint"
        in err["Message"]
    )
    assert "Member must have value less than or equal to 10000" in err["Message"]


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
    assert err["Code"] == "InvalidParameterException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{nr_of_events}' at 'limit' failed to satisfy constraint"
        in err["Message"]
    )
    assert "Member must have value less than or equal to 10000" in err["Message"]


@pytest.mark.parametrize("nr_of_groups", [51, 100])
@mock_logs
def test_describe_too_many_log_groups(nr_of_groups):
    client = boto3.client("logs", "us-east-1")
    with pytest.raises(ClientError) as ex:
        client.describe_log_groups(limit=nr_of_groups)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{nr_of_groups}' at 'limit' failed to satisfy constraint"
        in err["Message"]
    )
    assert "Member must have value less than or equal to 50" in err["Message"]


@pytest.mark.parametrize("nr_of_streams", [51, 100])
@mock_logs
def test_describe_too_many_log_streams(nr_of_streams):
    client = boto3.client("logs", "us-east-1")
    log_group_name = "dummy"
    client.create_log_group(logGroupName=log_group_name)
    with pytest.raises(ClientError) as ex:
        client.describe_log_streams(logGroupName=log_group_name, limit=nr_of_streams)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{nr_of_streams}' at 'limit' failed to satisfy constraint"
        in err["Message"]
    )
    assert "Member must have value less than or equal to 50" in err["Message"]


@pytest.mark.parametrize("length", [513, 1000])
@mock_logs
def test_create_log_group_invalid_name_length(length):
    log_group_name = "a" * length
    client = boto3.client("logs", "us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_log_group(logGroupName=log_group_name)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{log_group_name}' at 'logGroupName' failed to satisfy constraint"
        in err["Message"]
    )
    assert "Member must have length less than or equal to 512" in err["Message"]


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
    assert err["Code"] == "InvalidParameterException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{invalid_orderby}' at 'orderBy' failed to satisfy constraint"
        in err["Message"]
    )
    assert (
        "Member must satisfy enum value set: [LogStreamName, LastEventTime]"
        in err["Message"]
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
    assert err["Code"] == "InvalidParameterException"
    assert err["Message"] == "Cannot order by LastEventTime with a logStreamNamePrefix."


@mock_s3
@mock_logs
def test_create_export_task_happy_path():
    log_group_name = "/aws/codebuild/blah1"
    destination = "mybucket"
    fromTime = 1611316574
    to = 1642852574
    logs = boto3.client("logs", region_name="ap-southeast-1")
    s3 = boto3.client("s3", "us-east-1")
    logs.create_log_group(logGroupName=log_group_name)
    s3.create_bucket(Bucket=destination)
    resp = logs.create_export_task(
        logGroupName=log_group_name, fromTime=fromTime, to=to, destination=destination
    )
    # taskId resembles a valid UUID (i.e. a string of 32 hexadecimal digits)
    assert UUID(resp["taskId"])
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_logs
def test_create_export_task_raises_ClientError_when_bucket_not_found():
    log_group_name = "/aws/codebuild/blah1"
    destination = "368a7022dea3dd621"
    fromTime = 1611316574
    to = 1642852574
    logs = boto3.client("logs", region_name="ap-southeast-1")
    logs.create_log_group(logGroupName=log_group_name)
    with pytest.raises(ClientError):
        logs.create_export_task(
            logGroupName=log_group_name,
            fromTime=fromTime,
            to=to,
            destination=destination,
        )


@mock_s3
@mock_logs
def test_create_export_raises_ResourceNotFoundException_log_group_not_found():
    log_group_name = "/aws/codebuild/blah1"
    destination = "mybucket"
    fromTime = 1611316574
    to = 1642852574
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=destination)
    logs = boto3.client("logs", region_name="ap-southeast-1")
    with pytest.raises(logs.exceptions.ResourceNotFoundException):
        logs.create_export_task(
            logGroupName=log_group_name,
            fromTime=fromTime,
            to=to,
            destination=destination,
        )
