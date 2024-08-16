"""Unit tests for appmesh-supported APIs."""

import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@pytest.fixture(name="client")
def fixture_transfer_client():
    with mock_aws():
        yield boto3.client("appmesh", region_name="us-east-1")


@mock_aws
def test_create_list_update_describe_delete_mesh(client):
    connection = client.create_mesh(
        meshName="mesh1",
        spec={
            "egressFilter": {
                "type": "DROP_ALL"
            },
            "serviceDiscovery": {
                "ipPreference": "IPv4_ONLY"
            }
        },
        tags=[
            {
                "key": "owner",
                "value": "moto"
            }
        ]
    )
    assert "mesh" in connection
    mesh = connection["mesh"]
    assert mesh["meshName"] == "mesh1"
    assert mesh["spec"]["egressFilter"]["type"] == "DROP_ALL" 
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv4_ONLY"
    assert mesh["status"]["status"] == "ACTIVE"
    # TODO 
    # assert mesh["metadata"]["meshOwner"] == ??

    connection = client.create_mesh(
        meshName="mesh2",
        spec={
            "egressFilter": {
                "type": "ALLOW_ALL"
            },
            "serviceDiscovery": {
                "ipPreference": "IPv4_PREFERRED"
            }
        },
        tags=[
            {
                "key": "owner",
                "value": "moto"
            }
        ]
    )
    assert "mesh" in connection
    mesh = connection["mesh"]
    assert mesh["meshName"] == "mesh2"
    assert mesh["spec"]["egressFilter"]["type"] == "ALLOW_ALL" 
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv4_PREFERRED"
    assert mesh["status"]["status"] == "ACTIVE"
    # TODO 
    # assert mesh["metadata"]["meshOwner"] == ??

    connection = client.list_meshes()
    connection = client.update_mesh()
    connection = client.describe_mesh(meshName="mesh1")
    connection = client.delete_mesh(meshName="mesh2")
    with pytest.raises(ClientError) as e:
        client.describe_mesh(meshName="mesh2")
    err = e.value.response["Error"]
    assert err["Code"] == "MeshNotFound"
    assert err["Message"] == f"There are no meshes with the name mesh2."



@mock_aws
def test_tag_and_list_tags_for_resource(client):
    connection = client.list_tags_for_resource()
    connection = client.tag_resource()
