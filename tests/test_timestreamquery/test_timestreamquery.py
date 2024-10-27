"""Unit tests for timestreamquery-supported APIs."""

import boto3
import pytest
import requests
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from tests import DEFAULT_ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_scheduled_query():
    target_config = {
        "TimestreamConfiguration": {
            "DatabaseName": "mydb",
            "TableName": "mytab",
            "TimeColumn": "tc",
            "DimensionMappings": [],
        }
    }

    client = boto3.client("timestream-query", region_name="us-east-2")
    arn = client.create_scheduled_query(
        Name="myquery",
        QueryString="SELECT *",
        ScheduleConfiguration={"ScheduleExpression": "* * * * * 1"},
        NotificationConfiguration={"SnsConfiguration": {"TopicArn": "arn:some:topic"}},
        TargetConfiguration=target_config,
        ScheduledQueryExecutionRoleArn="some role",
        ErrorReportConfiguration=get_error_config(),
        KmsKeyId="arn:kms:key",
    )["Arn"]

    assert (
        arn
        == f"arn:aws:timestream:us-east-2:{DEFAULT_ACCOUNT_ID}:scheduled-query/myquery"
    )

    query = client.describe_scheduled_query(ScheduledQueryArn=arn)["ScheduledQuery"]
    assert query["Arn"] == arn
    assert query["Name"] == "myquery"
    assert query["QueryString"] == "SELECT *"
    assert query["CreationTime"]
    assert query["State"] == "ENABLED"
    assert query["ScheduleConfiguration"] == {"ScheduleExpression": "* * * * * 1"}
    assert query["NotificationConfiguration"] == {
        "SnsConfiguration": {"TopicArn": "arn:some:topic"}
    }
    assert query["TargetConfiguration"] == target_config
    assert query["ScheduledQueryExecutionRoleArn"] == "some role"
    assert query["ErrorReportConfiguration"] == get_error_config()
    assert query["KmsKeyId"] == "arn:kms:key"


@mock_aws
def test_delete_scheduled_query():
    client = boto3.client("timestream-query", region_name="us-east-2")

    arn = client.create_scheduled_query(
        Name="myquery",
        QueryString="SELECT *",
        ScheduleConfiguration={"ScheduleExpression": "* * * * * 1"},
        NotificationConfiguration={"SnsConfiguration": {"TopicArn": "arn:some:topic"}},
        ScheduledQueryExecutionRoleArn="some role",
        ErrorReportConfiguration=get_error_config(),
    )["Arn"]
    client.delete_scheduled_query(ScheduledQueryArn=arn)

    with pytest.raises(ClientError) as exc:
        client.describe_scheduled_query(ScheduledQueryArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"The resource with arn {arn} does not exist."


@mock_aws
def test_update_scheduled_query():
    client = boto3.client("timestream-query", region_name="eu-west-1")
    arn = client.create_scheduled_query(
        Name="myquery",
        QueryString="SELECT *",
        ScheduleConfiguration={"ScheduleExpression": "* * * * * 1"},
        NotificationConfiguration={"SnsConfiguration": {"TopicArn": "arn:some:topic"}},
        ScheduledQueryExecutionRoleArn="some role",
        ErrorReportConfiguration=get_error_config(),
    )["Arn"]

    client.update_scheduled_query(
        ScheduledQueryArn=arn,
        State="DISABLED",
    )

    query = client.describe_scheduled_query(ScheduledQueryArn=arn)["ScheduledQuery"]
    assert query["State"] == "DISABLED"


@mock_aws
def test_query_default_results():
    client = boto3.client("timestream-query", region_name="us-east-1")
    resp = client.query(QueryString="SELECT *")

    assert resp["QueryId"]
    assert resp["Rows"] == []
    assert resp["ColumnInfo"] == []


@mock_aws
def test_query__configured_results():
    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )

    first_result = {
        "QueryId": "some_id",
        "Rows": [{"Data": [{"ScalarValue": "1"}]}],
        "ColumnInfo": [
            {"Name": "c", "Type": {"ScalarType": "VARCHAR"}},
        ],
        "QueryStatus": {
            "ProgressPercentage": 50,
            "CumulativeBytesScanned": 5,
            "CumulativeBytesMetered": 5,
        },
    }
    second_result = {
        "QueryId": "some_id",
        "Rows": [{"Data": [{"ScalarValue": "1"}]}, {"Data": [{"ScalarValue": "2"}]}],
        "ColumnInfo": [
            {"Name": "c", "Type": {"ScalarType": "VARCHAR"}},
            {"Name": "c", "Type": {"ScalarType": "VARCHAR"}},
        ],
        "QueryStatus": {
            "ProgressPercentage": 100,
            "CumulativeBytesScanned": 10,
            "CumulativeBytesMetered": 10,
        },
    }
    third_result = {
        "Rows": [{"Data": [{"ScalarValue": "5"}]}],
        "ColumnInfo": [{"Name": "c", "Type": {"ScalarType": "VARCHAR"}}],
        "QueryStatus": {
            "ProgressPercentage": 100,
            "CumulativeBytesScanned": 10,
            "CumulativeBytesMetered": 10,
        },
    }

    result = {
        "results": {
            "SELECT *": [first_result, second_result],
            None: [third_result],
        }
    }
    requests.post(
        f"http://{base_url}/moto-api/static/timestream/query-results",
        json=result,
    )

    client = boto3.client("timestream-query", region_name="us-east-1")

    # Unknown QUERY returns third result
    resp = client.query(QueryString="SELECT unknown")

    assert resp["Rows"] == third_result["Rows"]
    assert resp["ColumnInfo"] == third_result["ColumnInfo"]

    # Known QUERY returns first result
    resp = client.query(QueryString="SELECT *")

    assert resp["QueryId"] == "some_id"
    assert resp["Rows"] == first_result["Rows"]
    assert resp["ColumnInfo"] == first_result["ColumnInfo"]

    # Querying the same thing returns the second result
    resp = client.query(QueryString="SELECT *")

    assert resp["QueryId"] == "some_id"
    assert resp["Rows"] == second_result["Rows"]
    assert resp["ColumnInfo"] == second_result["ColumnInfo"]

    # Unknown QUERY returns third result again
    resp = client.query(QueryString="SELECT unknown")

    assert resp["Rows"] == third_result["Rows"]
    assert resp["ColumnInfo"] == third_result["ColumnInfo"]

    # Known QUERY returns nothing - we've already returned all possible results
    resp = client.query(QueryString="SELECT *")

    assert resp["QueryId"]
    assert resp["Rows"] == []
    assert resp["ColumnInfo"] == []


def get_error_config():
    return {"S3Configuration": {"BucketName": "mybucket", "ObjectKeyPrefix": "prefix"}}
