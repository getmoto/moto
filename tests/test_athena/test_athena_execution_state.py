from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.moto_api import state_manager


@pytest.fixture(scope="function")
def execution_state_transition():
    state_manager.set_transition(
        model_name="athena::execution", transition={"progression": "manual", "times": 2}
    )
    yield
    # Reset to default - we don't want to affect other tests
    state_manager.set_transition(
        model_name="athena::execution", transition={"progression": "immediate"}
    )


@mock_aws
def test_execution_with_manual_transition(execution_state_transition):
    if not settings.TEST_DECORATOR_MODE:
        # We already test the state transitions in ServerMode in other tests
        raise SkipTest(
            "NO point in verifying state transitions when not using the decorator"
        )

    client = boto3.client("athena", region_name="eu-west-1")
    exex_id = client.start_query_execution(
        QueryString="SELECT stuff FROM mytable",
        QueryExecutionContext={"Database": "default", "Catalog": "awsdatacatalog"},
        ResultConfiguration={"OutputLocation": "s3://qwerasdfq3451345254"},
    )["QueryExecutionId"]
    #
    # First state is QUEUED
    assert get_state(client, exex_id) == "QUEUED"

    # Unable to retrieve query results
    with pytest.raises(ClientError) as exc:
        client.get_query_results(QueryExecutionId=exex_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "Query has not yet finished. Current state: QUEUED"

    # Next state is RUNNING
    assert get_state(client, exex_id) == "RUNNING"
    assert get_state(client, exex_id) == "RUNNING"

    # Unable to retrieve query results
    with pytest.raises(ClientError) as exc:
        client.get_query_results(QueryExecutionId=exex_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "Query has not yet finished. Current state: RUNNING"

    # Next state is SUCCEEDED
    assert get_state(client, exex_id) == "SUCCEEDED"

    # Now we can get the results
    assert client.get_query_results(QueryExecutionId=exex_id)["ResultSet"]["Rows"] == []


def get_state(client, exex_id):
    return client.get_query_execution(QueryExecutionId=exex_id)["QueryExecution"][
        "Status"
    ]["State"]


@mock_aws
def test_get_query_results_without_transition():
    """
    Default state transition is 'immediate', meaning that the query results should be ready immediately
    """

    client = boto3.client("athena", region_name="eu-west-1")
    exex_id = client.start_query_execution(
        QueryString="SELECT stuff FROM mytable",
        QueryExecutionContext={"Database": "default", "Catalog": "awsdatacatalog"},
        ResultConfiguration={"OutputLocation": "s3://qwerasdfq3451345254"},
    )["QueryExecutionId"]

    assert client.get_query_results(QueryExecutionId=exex_id)["ResultSet"]["Rows"] == []
