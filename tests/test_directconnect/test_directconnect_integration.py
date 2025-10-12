import boto3
import pytest

from moto import mock_aws


@pytest.fixture(name="client")
def fixture_dx_client():
    with mock_aws():
        yield boto3.client("directconnect", region_name="us-east-1")


@mock_aws
def test_tags_from_resourcegroupsapi_connection(client):
    connection_id = client.create_connection(
        location="EqDC2",
        bandwidth="10Gbps",
        connectionName="TestConnection1",
        tags=[{"key": "k1", "value": "v1"}, {"key": "k2", "value": "v2"}],
    )["connectionId"]

    resource_groups_client = boto3.client(
        "resourcegroupstaggingapi", region_name="us-east-1"
    )
    tags = resource_groups_client.get_resources(
        ResourceARNList=[connection_id],
    )["ResourceTagMappingList"]
    assert tags == [
        {
            "ResourceARN": connection_id,
            "Tags": [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
        }
    ]


@mock_aws
def test_tags_from_resourcegroupsapi_lag(client):
    lag_id = client.create_lag(
        numberOfConnections=1,
        location="eqDC2",
        connectionsBandwidth="10Gbps",
        lagName="TestLag0",
        tags=[{"key": "k1", "value": "v1"}, {"key": "k2", "value": "v2"}],
    )["lagId"]

    resource_groups_client = boto3.client(
        "resourcegroupstaggingapi", region_name="us-east-1"
    )
    tags = resource_groups_client.get_resources(
        ResourceARNList=[lag_id],
    )["ResourceTagMappingList"]
    assert tags == [
        {
            "ResourceARN": lag_id,
            "Tags": [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
        }
    ]
