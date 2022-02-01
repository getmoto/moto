import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from moto import mock_redshiftdata
from tests.test_redshiftdata.test_redshiftdata_constants import ErrorAttributes

REGION = "us-east-1"

INVALID_ID_ERROR_MESSAGE = "id must satisfy regex pattern: ^[a-z0-9]{8}(-[a-z0-9]{4}){3}-[a-z0-9]{12}(:\\d+)?$"
RESOURCE_NOT_FOUND_ERROR_MESSAGE = "Query does not exist."


@pytest.fixture(autouse=True)
def client():
    yield boto3.client("redshift-data", region_name=REGION)


@mock_redshiftdata
def test_cancel_statement_throws_exception_when_uuid_invalid(client):
    statement_id = "test"

    with pytest.raises(ClientError) as raised_exception:
        client.cancel_statement(Id=statement_id)

    assert_expected_exception(raised_exception, "ValidationException", INVALID_ID_ERROR_MESSAGE)


@mock_redshiftdata
def test_cancel_statement_throws_exception_when_statement_not_found(client):
    statement_id = "890f1253-595b-4608-a0d1-73f933ccd0a0"

    with pytest.raises(ClientError) as raised_exception:
        client.cancel_statement(Id=statement_id)

    assert_expected_exception(raised_exception, "ResourceNotFoundException", RESOURCE_NOT_FOUND_ERROR_MESSAGE)


@mock_redshiftdata
def test_describe_statement_throws_exception_when_uuid_invalid(client):
    statement_id = "test"

    with pytest.raises(ClientError) as raised_exception:
        client.describe_statement(Id=statement_id)

    assert_expected_exception(raised_exception, "ValidationException", INVALID_ID_ERROR_MESSAGE)


@mock_redshiftdata
def test_describe_statement_throws_exception_when_statement_not_found(client):
    statement_id = "890f1253-595b-4608-a0d1-73f933ccd0a0"

    with pytest.raises(ClientError) as raised_exception:
        client.describe_statement(Id=statement_id)

    assert_expected_exception(raised_exception, "ResourceNotFoundException", RESOURCE_NOT_FOUND_ERROR_MESSAGE)


@mock_redshiftdata
def test_get_statement_result_throws_exception_when_uuid_invalid(client):
    statement_id = "test"

    with pytest.raises(ClientError) as raised_exception:
        client.get_statement_result(Id=statement_id)

    assert_expected_exception(raised_exception, "ValidationException", INVALID_ID_ERROR_MESSAGE)


@mock_redshiftdata
def test_get_statement_result_throws_exception_when_statement_not_found(client):
    statement_id = "890f1253-595b-4608-a0d1-73f933ccd0a0"

    with pytest.raises(ClientError) as raised_exception:
        client.get_statement_result(Id=statement_id)

    assert_expected_exception(raised_exception, "ResourceNotFoundException", RESOURCE_NOT_FOUND_ERROR_MESSAGE)


def assert_expected_exception(raised_exception, expected_exception, expected_message):
    error = raised_exception.value.response[ErrorAttributes.ERROR]
    error[ErrorAttributes.CODE].should.equal(expected_exception)
    error[ErrorAttributes.MESSAGE].should.equal(expected_message)
