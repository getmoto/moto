"""Unit tests for appmesh-supported APIs."""

from collections import defaultdict
from datetime import datetime

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
    # Create first mesh
    connection = client.create_mesh(
        meshName="mesh1",
        spec={
            "egressFilter": {"type": "DROP_ALL"},
            "serviceDiscovery": {"ipPreference": "IPv4_ONLY"},
        },
        tags=[{"key": "owner", "value": "moto"}],
    )
    mesh = connection.get("mesh")
    assert mesh is not None
    assert mesh["meshName"] == "mesh1"
    assert mesh["spec"]["egressFilter"]["type"] == "DROP_ALL"
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv4_ONLY"
    assert mesh["status"]["status"] == "ACTIVE"
    assert mesh["metadata"]["version"] == 1
    assert isinstance(mesh["metadata"]["arn"], str)
    assert isinstance(mesh["metadata"]["meshOwner"], str)
    assert isinstance(mesh["metadata"]["resourceOwner"], str)
    assert isinstance(mesh["metadata"]["createdAt"], datetime)
    assert isinstance(mesh["metadata"]["lastUpdatedAt"], datetime)

    # Create second mesh
    connection = client.create_mesh(
        meshName="mesh2",
        spec={
            "egressFilter": {"type": "ALLOW_ALL"},
            "serviceDiscovery": {"ipPreference": "IPv4_PREFERRED"},
        },
        tags=[{"key": "owner", "value": "moto"}],
    )
    mesh = connection.get("mesh")
    assert mesh is not None
    assert mesh["meshName"] == "mesh2"
    assert mesh["spec"]["egressFilter"]["type"] == "ALLOW_ALL"
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv4_PREFERRED"
    assert mesh["status"]["status"] == "ACTIVE"
    assert mesh["metadata"]["version"] == 1
    assert isinstance(mesh["metadata"]["arn"], str)
    assert isinstance(mesh["metadata"]["meshOwner"], str)
    assert isinstance(mesh["metadata"]["resourceOwner"], str)
    assert isinstance(mesh["metadata"]["createdAt"], datetime)
    assert isinstance(mesh["metadata"]["lastUpdatedAt"], datetime)

    # List all methods, expecting 2
    connection = client.list_meshes()
    meshes = connection.get("meshes")
    assert meshes is not None
    assert isinstance(meshes, list)
    assert len(meshes) == 2
    names_counted = defaultdict(int)
    for mesh in meshes:
        mesh_name = mesh.get("meshName")
        if mesh_name:
            names_counted[mesh_name] += 1
    assert names_counted["mesh1"] == 1
    assert names_counted["mesh2"] == 1

    # Change spec for mesh 1
    connection = client.update_mesh(
        meshName="mesh1",
        spec={
            "egressFilter": {"type": "ALLOW_ALL"},
            "serviceDiscovery": {"ipPreference": "IPv6_PREFERRED"},
        },
    )
    mesh = connection.get("mesh")
    assert mesh is not None
    assert mesh["meshName"] == "mesh1"
    assert mesh["spec"]["egressFilter"]["type"] == "ALLOW_ALL"
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv6_PREFERRED"
    assert mesh["status"]["status"] == "ACTIVE"
    assert mesh["metadata"]["version"] == 2

    # Describe mesh 1, should reflect changes
    connection = client.describe_mesh(meshName="mesh1")
    mesh = connection.get("mesh")
    assert mesh is not None
    assert mesh["meshName"] == "mesh1"
    assert mesh["spec"]["egressFilter"]["type"] == "ALLOW_ALL"
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv6_PREFERRED"
    assert mesh["status"]["status"] == "ACTIVE"
    assert mesh["metadata"]["version"] == 2

    connection = client.delete_mesh(meshName="mesh2")
    mesh = connection.get("mesh")
    assert mesh is not None
    assert mesh["meshName"] == "mesh2"
    assert mesh["spec"]["egressFilter"]["type"] == "ALLOW_ALL"
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv4_PREFERRED"
    assert mesh["status"]["status"] == "DELETED"

    connection = client.list_meshes()
    meshes = connection.get("meshes")
    assert meshes is not None
    assert isinstance(meshes, list)
    assert len(meshes) == 1
    assert meshes[0]["meshName"] == "mesh1"

    with pytest.raises(ClientError) as e:
        client.describe_mesh(meshName="mesh2")
    err = e.value.response["Error"]
    assert err["Code"] == "MeshNotFound"
    assert err["Message"] == "There are no meshes with the name mesh2."


@mock_aws
def test_tag_and_list_tags_for_resource(client):
    connection = client.create_mesh(
        meshName="mesh1",
        spec={
            "egressFilter": {"type": "DROP_ALL"},
            "serviceDiscovery": {"ipPreference": "IPv4_ONLY"},
        },
        tags=[{"key": "owner", "value": "moto"}],
    )
    mesh = connection.get("mesh")
    assert mesh is not None
    arn = mesh["metadata"]["arn"]

    client.tag_resource(
        resourceArn=arn, tags=[{"key": "organization", "value": "moto"}]
    )
    connection = client.list_tags_for_resource(resourceArn=arn)
    tags = connection["tags"]
    assert tags[0] == {"key": "owner", "value": "moto"}
    assert tags[1] == {"key": "organization", "value": "moto"}
