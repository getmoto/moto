"""Test different server responses."""
import json
from uuid import UUID

import pytest

import moto.server as server
from tests.test_redshiftdata.test_redshiftdata_constants import (
    DEFAULT_ENCODING,
    HttpHeaders,
)

CLIENT_ENDPOINT = "/"


def headers(action):
    return {
        "X-Amz-Target": f"RedshiftData.{action}",
        "Content-Type": "application/x-amz-json-1.1",
    }


@pytest.fixture(autouse=True, name="client")
def fixture_client():
    backend = server.create_backend_app("redshift-data")
    yield backend.test_client()


def test_redshiftdata_cancel_statement_unknown_statement(client):
    statement_id = "890f1253-595b-4608-a0d1-73f933ccd0a0"
    response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": statement_id}),
        headers=headers("CancelStatement"),
    )
    assert response.status_code == 400
    should_return_expected_exception(
        response, "ResourceNotFoundException", "Query does not exist."
    )


def test_redshiftdata_describe_statement_unknown_statement(client):
    statement_id = "890f1253-595b-4608-a0d1-73f933ccd0a0"
    response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": statement_id}),
        headers=headers("DescribeStatement"),
    )
    assert response.status_code == 400
    should_return_expected_exception(
        response, "ResourceNotFoundException", "Query does not exist."
    )


def test_redshiftdata_get_statement_result_unknown_statement(client):
    statement_id = "890f1253-595b-4608-a0d1-73f933ccd0a0"
    response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": statement_id}),
        headers=headers("GetStatementResult"),
    )
    assert response.status_code == 400
    should_return_expected_exception(
        response, "ResourceNotFoundException", "Query does not exist."
    )


def test_redshiftdata_execute_statement_with_minimal_values(client):
    database = "database"
    sql = "sql"
    response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Database": database, "Sql": sql}),
        headers=headers("ExecuteStatement"),
    )
    assert response.status_code == 200
    payload = get_payload(response)

    assert payload["ClusterIdentifier"] is None
    assert payload["Database"] == database
    assert payload["DbUser"] is None
    assert payload["SecretArn"] is None

    uuid_obj = UUID(payload["Id"], version=4)
    assert str(uuid_obj) == payload["Id"]


def test_redshiftdata_execute_statement_with_all_values(client):
    cluster = "cluster"
    database = "database"
    dbUser = "dbUser"
    sql = "sql"
    secretArn = "secretArn"

    response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps(
            {
                "ClusterIdentifier": cluster,
                "Database": database,
                "DbUser": dbUser,
                "Sql": sql,
                "SecretArn": secretArn,
            }
        ),
        headers=headers("ExecuteStatement"),
    )
    assert response.status_code == 200
    payload = get_payload(response)

    assert payload["ClusterIdentifier"] == cluster
    assert payload["Database"] == database
    assert payload["DbUser"] == dbUser
    assert payload["SecretArn"] == secretArn


def test_redshiftdata_execute_statement_and_describe_statement(client):
    cluster = "cluster"
    database = "database"
    dbUser = "dbUser"
    sql = "sql"
    secretArn = "secretArn"

    # ExecuteStatement
    execute_response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps(
            {
                "ClusterIdentifier": cluster,
                "Database": database,
                "DbUser": dbUser,
                "Sql": sql,
                "SecretArn": secretArn,
            }
        ),
        headers=headers("ExecuteStatement"),
    )
    assert execute_response.status_code == 200
    execute_payload = get_payload(execute_response)

    # DescribeStatement
    describe_response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": execute_payload["Id"]}),
        headers=headers("DescribeStatement"),
    )
    assert describe_response.status_code == 200
    describe_payload = get_payload(execute_response)

    assert describe_payload["ClusterIdentifier"] == cluster
    assert describe_payload["Database"] == database
    assert describe_payload["DbUser"] == dbUser
    assert describe_payload["SecretArn"] == secretArn


def test_redshiftdata_execute_statement_and_get_statement_result(client):
    database = "database"
    sql = "sql"

    # ExecuteStatement
    execute_response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Database": database, "Sql": sql}),
        headers=headers("ExecuteStatement"),
    )
    assert execute_response.status_code == 200
    execute_payload = get_payload(execute_response)

    # GetStatementResult
    statement_result_response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": execute_payload["Id"]}),
        headers=headers("GetStatementResult"),
    )
    assert statement_result_response.status_code == 200
    statement_result_payload = get_payload(statement_result_response)
    assert statement_result_payload["TotalNumberRows"] == 3

    # columns
    assert len(statement_result_payload["ColumnMetadata"]) == 3
    assert statement_result_payload["ColumnMetadata"][0]["name"] == "Number"
    assert statement_result_payload["ColumnMetadata"][1]["name"] == "Street"
    assert statement_result_payload["ColumnMetadata"][2]["name"] == "City"

    # records
    assert len(statement_result_payload["Records"]) == 3
    assert statement_result_payload["Records"][0][0]["longValue"] == 10
    assert statement_result_payload["Records"][1][1]["stringValue"] == "Beta st"
    assert statement_result_payload["Records"][2][2]["stringValue"] == "Seattle"


def test_redshiftdata_execute_statement_and_cancel_statement(client):
    database = "database"
    sql = "sql"

    # ExecuteStatement
    execute_response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Database": database, "Sql": sql}),
        headers=headers("ExecuteStatement"),
    )
    assert execute_response.status_code == 200
    execute_payload = get_payload(execute_response)

    # CancelStatement 1
    cancel_response1 = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": execute_payload["Id"]}),
        headers=headers("CancelStatement"),
    )
    assert cancel_response1.status_code == 200
    cancel_payload1 = get_payload(cancel_response1)
    assert cancel_payload1["Status"] is True

    # CancelStatement 2
    cancel_response2 = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": execute_payload["Id"]}),
        headers=headers("CancelStatement"),
    )
    assert cancel_response2.status_code == 400
    should_return_expected_exception(
        cancel_response2,
        "ValidationException",
        (
            "Could not cancel a query that is already in ABORTED state "
            f"with ID: {execute_payload['Id']}"
        ),
    )


def get_payload(response):
    return json.loads(response.data.decode(DEFAULT_ENCODING))


def should_return_expected_exception(response, expected_exception, message):
    result_data = get_payload(response)
    assert response.headers.get(HttpHeaders.ErrorType) == expected_exception
    assert result_data["message"] == message
