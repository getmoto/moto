import boto3
import requests

from moto import mock_athena, mock_sts, settings


DEFAULT_COLUMN_INFO = [
    {
        "CatalogName": "string",
        "SchemaName": "string",
        "TableName": "string",
        "Name": "string",
        "Label": "string",
        "Type": "string",
        "Precision": 123,
        "Scale": 123,
        "Nullable": "NOT_NULL",
        "CaseSensitive": True,
    }
]


@mock_athena
def test_set_athena_result():
    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )

    athena_result = {
        "results": [
            {
                "rows": [
                    {"Data": [{"VarCharValue": "1"}]},
                ],
                "column_info": DEFAULT_COLUMN_INFO,
            }
        ]
    }
    resp = requests.post(
        f"http://{base_url}/moto-api/static/athena/query-results",
        json=athena_result,
    )
    assert resp.status_code == 201

    client = boto3.client("athena", region_name="us-east-1")
    details = client.get_query_results(QueryExecutionId="anyid")["ResultSet"]
    assert details["Rows"] == athena_result["results"][0]["rows"]
    assert details["ResultSetMetadata"]["ColumnInfo"] == DEFAULT_COLUMN_INFO

    # Operation should be idempotent
    details = client.get_query_results(QueryExecutionId="anyid")["ResultSet"]
    assert details["Rows"] == athena_result["results"][0]["rows"]

    # Different ID should still return different (default) results though
    details = client.get_query_results(QueryExecutionId="otherid")["ResultSet"]
    assert details["Rows"] == []


@mock_athena
def test_set_multiple_athena_result():
    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )

    athena_result = {
        "results": [
            {"rows": [{"Data": [{"VarCharValue": "1"}]}]},
            {"rows": [{"Data": [{"VarCharValue": "2"}]}]},
            {"rows": [{"Data": [{"VarCharValue": "3"}]}]},
        ]
    }
    resp = requests.post(
        f"http://{base_url}/moto-api/static/athena/query-results",
        json=athena_result,
    )
    assert resp.status_code == 201

    client = boto3.client("athena", region_name="us-east-1")
    details = client.get_query_results(QueryExecutionId="first_id")["ResultSet"]
    assert details["Rows"] == [{"Data": [{"VarCharValue": "1"}]}]

    # The same ID should return the same data
    details = client.get_query_results(QueryExecutionId="first_id")["ResultSet"]
    assert details["Rows"] == [{"Data": [{"VarCharValue": "1"}]}]

    # The next ID should return different data
    details = client.get_query_results(QueryExecutionId="second_id")["ResultSet"]
    assert details["Rows"] == [{"Data": [{"VarCharValue": "2"}]}]

    # The last ID should return even different data
    details = client.get_query_results(QueryExecutionId="third_id")["ResultSet"]
    assert details["Rows"] == [{"Data": [{"VarCharValue": "3"}]}]

    # Any other calls should return the default data
    details = client.get_query_results(QueryExecutionId="other_id")["ResultSet"]
    assert details["Rows"] == []


@mock_athena
@mock_sts
def test_set_athena_result_with_custom_region_account():
    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )

    athena_result = {
        "account_id": "222233334444",
        "region": "eu-west-1",
        "results": [
            {
                "rows": [
                    {"Data": [{"VarCharValue": "1"}]},
                ],
                "column_info": DEFAULT_COLUMN_INFO,
            }
        ],
    }
    resp = requests.post(
        f"http://{base_url}/moto-api/static/athena/query-results",
        json=athena_result,
    )
    assert resp.status_code == 201

    sts = boto3.client("sts", "us-east-1")
    cross_account_creds = sts.assume_role(
        RoleArn="arn:aws:iam::222233334444:role/role-in-another-account",
        RoleSessionName="test-session-name",
        ExternalId="test-external-id",
    )["Credentials"]

    athena_in_other_account = boto3.client(
        "athena",
        aws_access_key_id=cross_account_creds["AccessKeyId"],
        aws_secret_access_key=cross_account_creds["SecretAccessKey"],
        aws_session_token=cross_account_creds["SessionToken"],
        region_name="eu-west-1",
    )

    details = athena_in_other_account.get_query_results(QueryExecutionId="anyid")[
        "ResultSet"
    ]
    assert details["Rows"] == athena_result["results"][0]["rows"]
    assert details["ResultSetMetadata"]["ColumnInfo"] == DEFAULT_COLUMN_INFO

    # query results from other regions do not match
    athena_in_diff_region = boto3.client(
        "athena",
        aws_access_key_id=cross_account_creds["AccessKeyId"],
        aws_secret_access_key=cross_account_creds["SecretAccessKey"],
        aws_session_token=cross_account_creds["SessionToken"],
        region_name="eu-west-2",
    )
    details = athena_in_diff_region.get_query_results(QueryExecutionId="anyid")[
        "ResultSet"
    ]
    assert details["Rows"] == []

    # query results from default account does not match
    client = boto3.client("athena", region_name="eu-west-1")
    details = client.get_query_results(QueryExecutionId="anyid")["ResultSet"]
    assert details["Rows"] == []
