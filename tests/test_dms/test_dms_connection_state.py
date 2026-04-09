from unittest import SkipTest

import boto3
import pytest

from moto import mock_aws, settings
from moto.moto_api import state_manager


@pytest.fixture(scope="function")
def execution_state_transition():
    state_manager.set_transition(
        model_name="dms::connection", transition={"progression": "manual", "times": 3}
    )
    yield
    # Reset to default - we don't want to affect other tests
    state_manager.set_transition(
        model_name="dms::connection", transition={"progression": "manual", "times": 1}
    )


@mock_aws
def test_describe_connection_with_manual_transition(execution_state_transition):
    if not settings.TEST_DECORATOR_MODE:
        # We already test the state transitions in ServerMode in other tests
        raise SkipTest(
            "NO point in verifying state transitions when not using the decorator"
        )

    client = boto3.client("dms", region_name="eu-west-1")
    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_arn = response["ReplicationInstance"]["ReplicationInstanceArn"]
    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_arn = response["Endpoint"]["EndpointArn"]
    response = client.test_connection(
        ReplicationInstanceArn=replication_instance_arn, EndpointArn=endpoint_arn
    )
    connection = response["Connection"]
    assert connection["ReplicationInstanceArn"] == replication_instance_arn
    assert connection["EndpointArn"] == endpoint_arn
    assert connection["Status"] == "testing"
    assert connection["EndpointIdentifier"] == "test-endpoint"
    assert connection["ReplicationInstanceIdentifier"] == "test-instance"

    # first call status should stay testing
    response = client.describe_connections()
    assert len(response["Connections"]) == 1
    connection = response["Connections"][0]
    assert connection["ReplicationInstanceArn"] == replication_instance_arn
    assert connection["EndpointArn"] == endpoint_arn
    assert connection["Status"] == "testing"
    assert connection["EndpointIdentifier"] == "test-endpoint"
    assert connection["ReplicationInstanceIdentifier"] == "test-instance"

    # second call status should stay testing
    response = client.describe_connections()
    assert len(response["Connections"]) == 1
    connection = response["Connections"][0]
    assert connection["ReplicationInstanceArn"] == replication_instance_arn
    assert connection["EndpointArn"] == endpoint_arn
    assert connection["Status"] == "testing"
    assert connection["EndpointIdentifier"] == "test-endpoint"
    assert connection["ReplicationInstanceIdentifier"] == "test-instance"

    # Third call should update the status
    response = client.describe_connections()
    assert len(response["Connections"]) == 1
    connection = response["Connections"][0]
    assert connection["ReplicationInstanceArn"] == replication_instance_arn
    assert connection["EndpointArn"] == endpoint_arn
    assert connection["Status"] == "successful"
    assert connection["EndpointIdentifier"] == "test-endpoint"
    assert connection["ReplicationInstanceIdentifier"] == "test-instance"


@mock_aws
def test_describe_connection_without_transition():
    """
    Default state transition is 'manual', with 1 times  meaning that the first time we call describe_connection status advances
    """

    client = boto3.client("dms", region_name="eu-west-1")
    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_arn = response["ReplicationInstance"]["ReplicationInstanceArn"]
    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_arn = response["Endpoint"]["EndpointArn"]
    response = client.test_connection(
        ReplicationInstanceArn=replication_instance_arn, EndpointArn=endpoint_arn
    )
    connection = response["Connection"]
    assert connection["ReplicationInstanceArn"] == replication_instance_arn
    assert connection["EndpointArn"] == endpoint_arn
    assert connection["Status"] == "testing"
    assert connection["EndpointIdentifier"] == "test-endpoint"
    assert connection["ReplicationInstanceIdentifier"] == "test-instance"

    # first call status should advance the state
    response = client.describe_connections()
    assert len(response["Connections"]) == 1
    connection = response["Connections"][0]
    assert connection["ReplicationInstanceArn"] == replication_instance_arn
    assert connection["EndpointArn"] == endpoint_arn
    assert connection["Status"] == "successful"
    assert connection["EndpointIdentifier"] == "test-endpoint"
    assert connection["ReplicationInstanceIdentifier"] == "test-instance"
