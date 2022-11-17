"""Test different server responses."""
import json
import pytest
import sure  # noqa # pylint: disable=unused-import
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
    response.status_code.should.equal(400)
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
    response.status_code.should.equal(400)
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
    response.status_code.should.equal(400)
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
    response.status_code.should.equal(200)
    payload = get_payload(response)

    payload["ClusterIdentifier"].should.equal(None)
    payload["Database"].should.equal(database)
    payload["DbUser"].should.equal(None)
    payload["SecretArn"].should.equal(None)
    payload["Id"].should.match_uuid4()


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
    response.status_code.should.equal(200)
    payload = get_payload(response)

    payload["ClusterIdentifier"].should.equal(cluster)
    payload["Database"].should.equal(database)
    payload["DbUser"].should.equal(dbUser)
    payload["SecretArn"].should.equal(secretArn)


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
    execute_response.status_code.should.equal(200)
    execute_payload = get_payload(execute_response)

    # DescribeStatement
    describe_response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": execute_payload["Id"]}),
        headers=headers("DescribeStatement"),
    )
    describe_response.status_code.should.equal(200)
    describe_payload = get_payload(execute_response)

    describe_payload["ClusterIdentifier"].should.equal(cluster)
    describe_payload["Database"].should.equal(database)
    describe_payload["DbUser"].should.equal(dbUser)
    describe_payload["SecretArn"].should.equal(secretArn)


def test_redshiftdata_execute_statement_and_get_statement_result(client):
    database = "database"
    sql = "sql"

    # ExecuteStatement
    execute_response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Database": database, "Sql": sql}),
        headers=headers("ExecuteStatement"),
    )
    execute_response.status_code.should.equal(200)
    execute_payload = get_payload(execute_response)

    # GetStatementResult
    statement_result_response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": execute_payload["Id"]}),
        headers=headers("GetStatementResult"),
    )
    statement_result_response.status_code.should.equal(200)
    statement_result_payload = get_payload(statement_result_response)
    statement_result_payload["TotalNumberRows"].should.equal(3)

    # columns
    len(statement_result_payload["ColumnMetadata"]).should.equal(3)
    statement_result_payload["ColumnMetadata"][0]["name"].should.equal("Number")
    statement_result_payload["ColumnMetadata"][1]["name"].should.equal("Street")
    statement_result_payload["ColumnMetadata"][2]["name"].should.equal("City")

    # records
    len(statement_result_payload["Records"]).should.equal(3)
    statement_result_payload["Records"][0][0]["longValue"].should.equal(10)
    statement_result_payload["Records"][1][1]["stringValue"].should.equal("Beta st")
    statement_result_payload["Records"][2][2]["stringValue"].should.equal("Seattle")


def test_redshiftdata_execute_statement_and_cancel_statement(client):
    database = "database"
    sql = "sql"

    # ExecuteStatement
    execute_response = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Database": database, "Sql": sql}),
        headers=headers("ExecuteStatement"),
    )
    execute_response.status_code.should.equal(200)
    execute_payload = get_payload(execute_response)

    # CancelStatement 1
    cancel_response1 = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": execute_payload["Id"]}),
        headers=headers("CancelStatement"),
    )
    cancel_response1.status_code.should.equal(200)
    cancel_payload1 = get_payload(cancel_response1)
    cancel_payload1["Status"].should.equal(True)

    # CancelStatement 2
    cancel_response2 = client.post(
        CLIENT_ENDPOINT,
        data=json.dumps({"Id": execute_payload["Id"]}),
        headers=headers("CancelStatement"),
    )
    cancel_response2.status_code.should.equal(400)
    should_return_expected_exception(
        cancel_response2,
        "ValidationException",
        f"Could not cancel a query that is already in ABORTED state with ID: {execute_payload['Id']}",
    )


def get_payload(response):
    return json.loads(response.data.decode(DEFAULT_ENCODING))


def should_return_expected_exception(response, expected_exception, message):
    result_data = get_payload(response)
    response.headers.get(HttpHeaders.ErrorType).should.equal(expected_exception)
    result_data["message"].should.equal(message)
