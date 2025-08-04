import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@pytest.fixture(name="client")
@mock_aws
def get_client():
    return boto3.client("athena", region_name="us-east-1")


@mock_aws
def test_create_capacity_reservation(client):
    capacity_reservation = client.create_capacity_reservation(
        TargetDpus=123,
        Name="athena_workgroup",
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )
    metadata = capacity_reservation["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0


@mock_aws
def test_get_capacity_reservation_not_found(client):
    with pytest.raises(ClientError) as ex:
        client.get_capacity_reservation(Name="test")

    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "Capacity reservation does not exist"


@mock_aws
def test_get_capacity_reservation(client):
    client.create_capacity_reservation(
        TargetDpus=123,
        Name="athena_workgroup",
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )

    capacity_reservation = client.get_capacity_reservation(Name="athena_workgroup")
    result = capacity_reservation["CapacityReservation"]
    assert result["Name"] == "athena_workgroup"
    assert result["TargetDpus"] == 123
