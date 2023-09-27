from botocore.exceptions import ClientError
import pytest
import boto3

from moto import mock_athena, settings
from moto.athena.models import athena_backends, QueryResults
from moto.core import DEFAULT_ACCOUNT_ID


@mock_athena
def test_create_work_group():
    client = boto3.client("athena", region_name="us-east-1")

    client.create_work_group(
        Name="athena_workgroup",
        Description="Test work group",
        Configuration={
            "ResultConfiguration": {
                "OutputLocation": "s3://bucket-name/prefix/",
                "EncryptionConfiguration": {
                    "EncryptionOption": "SSE_KMS",
                    "KmsKey": "aws:arn:kms:1233456789:us-east-1:key/number-1",
                },
            }
        },
    )

    with pytest.raises(ClientError) as exc:
        # The second time should throw an error
        client.create_work_group(
            Name="athena_workgroup",
            Description="duplicate",
            Configuration={
                "ResultConfiguration": {
                    "OutputLocation": "s3://bucket-name/prefix/",
                    "EncryptionConfiguration": {
                        "EncryptionOption": "SSE_KMS",
                        "KmsKey": "aws:arn:kms:1233456789:us-east-1:key/number-1",
                    },
                }
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "WorkGroup already exists"

    # Then test the work group appears in the work group list
    response = client.list_work_groups()

    work_groups = list(
        filter(lambda wg: wg["Name"] != "primary", response["WorkGroups"])
    )
    assert len(work_groups) == 1
    work_group = work_groups[0]
    assert work_group["Name"] == "athena_workgroup"
    assert work_group["Description"] == "Test work group"
    assert work_group["State"] == "ENABLED"


@mock_athena
def test_get_primary_workgroup():
    client = boto3.client("athena", region_name="us-east-1")
    assert len(client.list_work_groups()["WorkGroups"]) == 1

    primary = client.get_work_group(WorkGroup="primary")["WorkGroup"]
    assert primary["Name"] == "primary"
    assert primary["Configuration"] == {}


@mock_athena
def test_create_and_get_workgroup():
    client = boto3.client("athena", region_name="us-east-1")

    create_basic_workgroup(client=client, name="athena_workgroup")

    work_group = client.get_work_group(WorkGroup="athena_workgroup")["WorkGroup"]
    del work_group["CreationTime"]  # Were not testing creationtime atm
    assert work_group == {
        "Name": "athena_workgroup",
        "State": "ENABLED",
        "Configuration": {
            "ResultConfiguration": {"OutputLocation": "s3://bucket-name/prefix/"}
        },
        "Description": "Test work group",
    }


@mock_athena
def test_start_query_execution():
    client = boto3.client("athena", region_name="us-east-1")

    create_basic_workgroup(client=client, name="athena_workgroup")
    response = client.start_query_execution(
        QueryString="query1",
        QueryExecutionContext={"Database": "string"},
        ResultConfiguration={"OutputLocation": "string"},
        WorkGroup="athena_workgroup",
    )
    assert "QueryExecutionId" in response

    sec_response = client.start_query_execution(
        QueryString="query2",
        QueryExecutionContext={"Database": "string"},
        ResultConfiguration={"OutputLocation": "string"},
    )
    assert "QueryExecutionId" in sec_response
    assert response["QueryExecutionId"] != sec_response["QueryExecutionId"]


@mock_athena
def test_start_query_validate_workgroup():
    client = boto3.client("athena", region_name="us-east-1")

    with pytest.raises(ClientError) as err:
        client.start_query_execution(
            QueryString="query1",
            QueryExecutionContext={"Database": "string"},
            ResultConfiguration={"OutputLocation": "string"},
            WorkGroup="unknown_workgroup",
        )
    assert err.value.response["Error"]["Code"] == "InvalidRequestException"
    assert err.value.response["Error"]["Message"] == "WorkGroup does not exist"


@mock_athena
def test_get_query_execution():
    client = boto3.client("athena", region_name="us-east-1")

    query = "SELECT stuff"
    location = "s3://bucket-name/prefix/"
    database = "database"
    # Start Query
    exex_id = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": location},
    )["QueryExecutionId"]
    #
    details = client.get_query_execution(QueryExecutionId=exex_id)["QueryExecution"]
    #
    assert details["QueryExecutionId"] == exex_id
    assert details["Query"] == query
    assert details["StatementType"] == "DML"
    assert details["ResultConfiguration"]["OutputLocation"] == location
    assert details["QueryExecutionContext"]["Database"] == database
    assert details["Status"]["State"] == "SUCCEEDED"
    assert details["Statistics"] == {
        "EngineExecutionTimeInMillis": 0,
        "DataScannedInBytes": 0,
        "TotalExecutionTimeInMillis": 0,
        "QueryQueueTimeInMillis": 0,
        "QueryPlanningTimeInMillis": 0,
        "ServiceProcessingTimeInMillis": 0,
    }
    assert "WorkGroup" not in details


@mock_athena
def test_stop_query_execution():
    client = boto3.client("athena", region_name="us-east-1")

    query = "SELECT stuff"
    location = "s3://bucket-name/prefix/"
    database = "database"
    # Start Query
    exex_id = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": location},
    )["QueryExecutionId"]
    # Stop Query
    client.stop_query_execution(QueryExecutionId=exex_id)
    # Verify status
    details = client.get_query_execution(QueryExecutionId=exex_id)["QueryExecution"]
    #
    assert details["QueryExecutionId"] == exex_id
    assert details["Status"]["State"] == "CANCELLED"


@mock_athena
def test_create_named_query():
    client = boto3.client("athena", region_name="us-east-1")

    # craete named query
    res = client.create_named_query(
        Name="query-name", Database="target_db", QueryString="SELECT * FROM table1"
    )

    assert "NamedQueryId" in res


@mock_athena
def test_get_named_query():
    client = boto3.client("athena", region_name="us-east-1")
    query_name = "query-name"
    database = "target_db"
    query_string = "SELECT * FROM tbl1"
    description = "description of this query"
    # create named query
    res_create = client.create_named_query(
        Name=query_name,
        Database=database,
        QueryString=query_string,
        Description=description,
    )
    query_id = res_create["NamedQueryId"]

    # get named query
    res_get = client.get_named_query(NamedQueryId=query_id)["NamedQuery"]
    assert res_get["Name"] == query_name
    assert res_get["Description"] == description
    assert res_get["Database"] == database
    assert res_get["QueryString"] == query_string
    assert res_get["NamedQueryId"] == query_id


def create_basic_workgroup(client, name):
    client.create_work_group(
        Name=name,
        Description="Test work group",
        Configuration={
            "ResultConfiguration": {"OutputLocation": "s3://bucket-name/prefix/"}
        },
    )


@mock_athena
def test_create_data_catalog():
    client = boto3.client("athena", region_name="us-east-1")
    response = client.create_data_catalog(
        Name="athena_datacatalog",
        Type="GLUE",
        Description="Test data catalog",
        Parameters={"catalog-id": "AWS Test account ID"},
        Tags=[],
    )

    with pytest.raises(ClientError) as exc:
        # The second time should throw an error
        response = client.create_data_catalog(
            Name="athena_datacatalog",
            Type="GLUE",
            Description="Test data catalog",
            Parameters={"catalog-id": "AWS Test account ID"},
            Tags=[],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "DataCatalog already exists"

    # Then test the work group appears in the work group list
    response = client.list_data_catalogs()

    assert len(response["DataCatalogsSummary"]) == 1
    data_catalog = response["DataCatalogsSummary"][0]
    assert data_catalog["CatalogName"] == "athena_datacatalog"
    assert data_catalog["Type"] == "GLUE"


@mock_athena
def test_create_and_get_data_catalog():
    client = boto3.client("athena", region_name="us-east-1")

    client.create_data_catalog(
        Name="athena_datacatalog",
        Type="GLUE",
        Description="Test data catalog",
        Parameters={"catalog-id": "AWS Test account ID"},
        Tags=[],
    )

    data_catalog = client.get_data_catalog(Name="athena_datacatalog")
    assert data_catalog["DataCatalog"] == {
        "Name": "athena_datacatalog",
        "Description": "Test data catalog",
        "Type": "GLUE",
        "Parameters": {"catalog-id": "AWS Test account ID"},
    }


@mock_athena
def test_get_query_results():
    client = boto3.client("athena", region_name="us-east-1")

    result = client.get_query_results(QueryExecutionId="test")

    assert result["ResultSet"]["Rows"] == []
    assert result["ResultSet"]["ResultSetMetadata"]["ColumnInfo"] == []

    if not settings.TEST_SERVER_MODE:
        backend = athena_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        rows = [{"Data": [{"VarCharValue": ".."}]}]
        column_info = [
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
        # This was the documented way to configure query results, before `moto-api/static/athena/query_results` was implemented
        # We should try to keep this for backward compatibility
        results = QueryResults(rows=rows, column_info=column_info)
        backend.query_results["test"] = results

        result = client.get_query_results(QueryExecutionId="test")
        assert result["ResultSet"]["Rows"] == rows
        assert result["ResultSet"]["ResultSetMetadata"]["ColumnInfo"] == column_info


@mock_athena
def test_get_query_results_queue():
    client = boto3.client("athena", region_name="us-east-1")

    result = client.get_query_results(QueryExecutionId="test")

    assert result["ResultSet"]["Rows"] == []
    assert result["ResultSet"]["ResultSetMetadata"]["ColumnInfo"] == []

    if settings.TEST_DECORATOR_MODE:
        backend = athena_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        rows = [{"Data": [{"VarCharValue": ".."}]}]
        column_info = [
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
        results = QueryResults(rows=rows, column_info=column_info)
        backend.query_results_queue.append(results)

        result = client.get_query_results(
            QueryExecutionId="some-id-not-used-when-results-were-added-to-queue"
        )
        assert result["ResultSet"]["Rows"] == rows
        assert result["ResultSet"]["ResultSetMetadata"]["ColumnInfo"] == column_info

        result = client.get_query_results(QueryExecutionId="other-id")
        assert result["ResultSet"]["Rows"] == []
        assert result["ResultSet"]["ResultSetMetadata"]["ColumnInfo"] == []

        result = client.get_query_results(
            QueryExecutionId="some-id-not-used-when-results-were-added-to-queue"
        )
        assert result["ResultSet"]["Rows"] == rows
        assert result["ResultSet"]["ResultSetMetadata"]["ColumnInfo"] == column_info


@mock_athena
def test_list_query_executions():
    client = boto3.client("athena", region_name="us-east-1")

    create_basic_workgroup(client=client, name="athena_workgroup")
    exec_result = client.start_query_execution(
        QueryString="query1",
        QueryExecutionContext={"Database": "string"},
        ResultConfiguration={"OutputLocation": "string"},
        WorkGroup="athena_workgroup",
    )
    exec_id = exec_result["QueryExecutionId"]

    executions = client.list_query_executions()
    assert len(executions["QueryExecutionIds"]) == 1
    assert executions["QueryExecutionIds"][0] == exec_id


@mock_athena
def test_list_named_queries():
    client = boto3.client("athena", region_name="us-east-1")
    create_basic_workgroup(client=client, name="athena_workgroup")
    query_id = client.create_named_query(
        Name="query-name",
        Database="target_db",
        QueryString="SELECT * FROM table1",
        WorkGroup="athena_workgroup",
    )
    list_athena_wg = client.list_named_queries(WorkGroup="athena_workgroup")
    assert list_athena_wg["NamedQueryIds"][0] == query_id["NamedQueryId"]
    list_primary_wg = client.list_named_queries()
    assert len(list_primary_wg["NamedQueryIds"]) == 0


@mock_athena
def test_create_prepared_statement():
    client = boto3.client("athena", region_name="us-east-1")
    create_basic_workgroup(client=client, name="athena_workgroup")
    res = client.create_prepared_statement(
        StatementName="test-statement",
        WorkGroup="athena_workgroup",
        QueryStatement="SELECT * FROM table1",
    )
    metadata = res["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0


@mock_athena
def test_get_prepared_statement():
    client = boto3.client("athena", region_name="us-east-1")
    create_basic_workgroup(client=client, name="athena_workgroup")
    client.create_prepared_statement(
        StatementName="stmt-name",
        WorkGroup="athena_workgroup",
        QueryStatement="SELECT * FROM table1",
    )
    resp = client.get_prepared_statement(
        StatementName="stmt-name", WorkGroup="athena_workgroup"
    )
    assert "PreparedStatement" in resp
