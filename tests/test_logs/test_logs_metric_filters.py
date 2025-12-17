import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
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


@mock_aws
def test_describe_metric_filters_happy_log_group_name():
    conn = boto3.client("logs", "us-west-2")

    response1 = put_metric_filter(conn, count=1)
    assert response1["ResponseMetadata"]["HTTPStatusCode"] == 200
    response2 = put_metric_filter(conn, count=2)
    assert response2["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_metric_filters(logGroupName="logGroupName2")

    assert len(response["metricFilters"]) == 1
    assert response["metricFilters"][0]["logGroupName"] == "logGroupName2"


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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

    response = conn.describe_metric_filters(
        metricName="metricName1", metricNamespace="metricNamespace1"
    )
    assert response["metricFilters"][0]["filterName"] == "filterName1"


@mock_aws
def test_put_and_describe_metric_filter_with_non_alphanumerics_in_namespace():
    """
    Should allow namespaces as described here:
    https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#Namespace
    """
    conn = boto3.client("logs", "us-west-2")
    namespace = "A.B-c_d/1#2:metricNamespace"
    response = conn.put_metric_filter(
        filterName="filterName",
        filterPattern="filterPattern",
        logGroupName="logGroupName",
        metricTransformations=[
            {
                "metricName": "metricName",
                "metricNamespace": namespace,
                "metricValue": "metricValue",
            },
        ],
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = conn.describe_metric_filters(
        metricName="metricName", metricNamespace=namespace
    )
    assert response["metricFilters"][0]["filterName"] == "filterName"


@mock_aws
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


@mock_aws
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


@mock_aws
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
