import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from moto import mock_redshiftdata
from tests.test_redshiftdata.test_redshiftdata_constants import ErrorAttributes

REGION = "us-east-1"

INVALID_ID_ERROR_MESSAGE = (
    "id must satisfy regex pattern: ^[a-z0-9]{8}(-[a-z0-9]{4}){3}-[a-z0-9]{12}(:\\d+)?$"
)
RESOURCE_NOT_FOUND_ERROR_MESSAGE = "Query does not exist."


@pytest.fixture(autouse=True)
def client():
    yield boto3.client("redshift-data", region_name=REGION)


@mock_redshiftdata
def test_cancel_statement_throws_exception_when_uuid_invalid(client):
    statement_id = "test"

    with pytest.raises(ClientError) as raised_exception:
        client.cancel_statement(Id=statement_id)

    assert_expected_exception(
        raised_exception, "ValidationException", INVALID_ID_ERROR_MESSAGE
    )


@mock_redshiftdata
def test_cancel_statement_throws_exception_when_statement_not_found(client):
    statement_id = "890f1253-595b-4608-a0d1-73f933ccd0a0"

    with pytest.raises(ClientError) as raised_exception:
        client.cancel_statement(Id=statement_id)

    assert_expected_exception(
        raised_exception, "ResourceNotFoundException", RESOURCE_NOT_FOUND_ERROR_MESSAGE
    )


@mock_redshiftdata
def test_describe_statement_throws_exception_when_uuid_invalid(client):
    statement_id = "test"

    with pytest.raises(ClientError) as raised_exception:
        client.describe_statement(Id=statement_id)

    assert_expected_exception(
        raised_exception, "ValidationException", INVALID_ID_ERROR_MESSAGE
    )


@mock_redshiftdata
def test_describe_statement_throws_exception_when_statement_not_found(client):
    statement_id = "890f1253-595b-4608-a0d1-73f933ccd0a0"

    with pytest.raises(ClientError) as raised_exception:
        client.describe_statement(Id=statement_id)

    assert_expected_exception(
        raised_exception, "ResourceNotFoundException", RESOURCE_NOT_FOUND_ERROR_MESSAGE
    )


@mock_redshiftdata
def test_get_statement_result_throws_exception_when_uuid_invalid(client):
    statement_id = "test"

    with pytest.raises(ClientError) as raised_exception:
        client.get_statement_result(Id=statement_id)

    assert_expected_exception(
        raised_exception, "ValidationException", INVALID_ID_ERROR_MESSAGE
    )


@mock_redshiftdata
def test_get_statement_result_throws_exception_when_statement_not_found(client):
    statement_id = "890f1253-595b-4608-a0d1-73f933ccd0a0"

    with pytest.raises(ClientError) as raised_exception:
        client.get_statement_result(Id=statement_id)

    assert_expected_exception(
        raised_exception, "ResourceNotFoundException", RESOURCE_NOT_FOUND_ERROR_MESSAGE
    )


@mock_redshiftdata
def test_execute_statement_and_cancel_statement(client):
    cluster_identifier = "cluster_identifier"
    database = "database"
    db_user = "db_user"
    parameters = [{"name": "name", "value": "value"}]
    secret_arn = "secret_arn"
    sql = "sql"

    # Execute statement
    execute_response = client.execute_statement(
        ClusterIdentifier=cluster_identifier,
        Database=database,
        DbUser=db_user,
        Parameters=parameters,
        SecretArn=secret_arn,
        Sql=sql,
    )

    # Cancel statement
    cancel_response = client.cancel_statement(Id=execute_response["Id"])

    cancel_response["Status"].should.equal(True)


@mock_redshiftdata
def test_execute_statement_and_describe_statement(client):
    cluster_identifier = "cluster_identifier"
    database = "database"
    db_user = "db_user"
    parameters = [{"name": "name", "value": "value"}]
    secret_arn = "secret_arn"
    sql = "sql"

    # Execute statement
    execute_response = client.execute_statement(
        ClusterIdentifier=cluster_identifier,
        Database=database,
        DbUser=db_user,
        Parameters=parameters,
        SecretArn=secret_arn,
        Sql=sql,
    )

    # Describe statement
    describe_response = client.describe_statement(Id=execute_response["Id"])

    describe_response["ClusterIdentifier"].should.equal(cluster_identifier)
    describe_response["Database"].should.equal(database)
    describe_response["DbUser"].should.equal(db_user)
    describe_response["QueryParameters"].should.equal(parameters)
    describe_response["SecretArn"].should.equal(secret_arn)
    describe_response["QueryString"].should.equal(sql)
    describe_response["Status"].should.equal("STARTED")


@mock_redshiftdata
def test_execute_statement_and_get_statement_result(client):
    cluster_identifier = "cluster_identifier"
    database = "database"
    db_user = "db_user"
    parameters = [{"name": "name", "value": "value"}]
    secret_arn = "secret_arn"
    sql = "sql"

    # Execute statement
    execute_response = client.execute_statement(
        ClusterIdentifier=cluster_identifier,
        Database=database,
        DbUser=db_user,
        Parameters=parameters,
        SecretArn=secret_arn,
        Sql=sql,
    )

    # Get statement result
    result_response = client.get_statement_result(Id=execute_response["Id"])

    result_response["ColumnMetadata"][0]["name"].should.equal("Number")
    result_response["ColumnMetadata"][1]["name"].should.equal("Street")
    result_response["ColumnMetadata"][2]["name"].should.equal("City")
    result_response["Records"][0][0]["longValue"].should.equal(10)
    result_response["Records"][1][1]["stringValue"].should.equal("Beta st")
    result_response["Records"][2][2]["stringValue"].should.equal("Seattle")


def assert_expected_exception(raised_exception, expected_exception, expected_message):
    error = raised_exception.value.response[ErrorAttributes.ERROR]
    error[ErrorAttributes.CODE].should.equal(expected_exception)
    error[ErrorAttributes.MESSAGE].should.equal(expected_message)
