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


@mock_aws
def test_create_describe_list_update_delete_virtual_router(client):
    MESH_NAME = "mock_mesh"
    connection = client.create_mesh(
        meshName=MESH_NAME,
        spec={
            "egressFilter": {"type": "DROP_ALL"},
            "serviceDiscovery": {"ipPreference": "IPv4_ONLY"},
        },
        tags=[{"key": "owner", "value": "moto"}],
    )
    assert "mesh" in connection
    mesh = connection["mesh"]
    assert "metadata" in mesh
    mesh_owner = mesh["metadata"]["meshOwner"]

    ROUTER_1 = "router1"
    ROUTER_2 = "router2"

    connection = client.create_virtual_router(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        virtualRouterName=ROUTER_1,
        spec={"listeners": [{"portMapping": {"port": 80, "protocol": "http"}}]},
        tags=[{"key": "router_traffic", "value": "http"}],
    )
    router1 = connection.get("virtualRouter")
    assert router1 is not None
    assert router1["meshName"] == MESH_NAME
    assert router1["metadata"]["meshOwner"] == mesh_owner
    assert router1["metadata"]["version"] == 1
    assert router1["spec"]["listeners"][0]["portMapping"]["port"] == 80
    assert router1["spec"]["listeners"][0]["portMapping"]["protocol"] == "http"
    assert router1["status"]["status"] == "ACTIVE"

    connection = client.create_virtual_router(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        virtualRouterName=ROUTER_2,
        spec={"listeners": [{"portMapping": {"port": 443, "protocol": "http2"}}]},
        tags=[{"key": "router_traffic", "value": "https"}],
    )
    router2 = connection.get("virtualRouter")
    assert router2 is not None
    assert router2["meshName"] == MESH_NAME
    assert router2["metadata"]["meshOwner"] == mesh_owner
    assert router2["metadata"]["version"] == 1
    assert router2["spec"]["listeners"][0]["portMapping"]["port"] == 443
    assert router2["spec"]["listeners"][0]["portMapping"]["protocol"] == "http2"
    assert router2["status"]["status"] == "ACTIVE"
    connection = client.list_virtual_routers(meshName=MESH_NAME, meshOwner=mesh_owner)
    virtual_routers = connection.get("virtualRouters")
    assert virtual_routers is not None
    assert isinstance(virtual_routers, list)
    assert len(virtual_routers) == 2
    names_counted = defaultdict(int)
    for virtual_router in virtual_routers:
        router_name = virtual_router.get("virtualRouterName")
        if router_name:
            names_counted[router_name] += 1
    assert names_counted[ROUTER_1] == 1
    assert names_counted[ROUTER_2] == 1

    connection = client.update_virtual_router(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        virtualRouterName=ROUTER_2,
        spec={"listeners": [{"portMapping": {"port": 80, "protocol": "tcp"}}]},
    )
    updated_router2 = connection.get("virtualRouter")
    assert updated_router2 is not None
    assert updated_router2["virtualRouterName"] == ROUTER_2
    assert updated_router2["meshName"] == MESH_NAME
    assert updated_router2["metadata"]["meshOwner"] == mesh_owner
    assert updated_router2["metadata"]["version"] == 2
    assert updated_router2["spec"]["listeners"][0]["portMapping"]["port"] == 80
    assert updated_router2["spec"]["listeners"][0]["portMapping"]["protocol"] == "tcp"
    assert updated_router2["status"]["status"] == "ACTIVE"

    connection = client.describe_virtual_router(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        virtualRouterName=ROUTER_2,
    )
    described_router2 = connection.get("virtualRouter")
    assert described_router2 is not None
    assert described_router2["virtualRouterName"] == ROUTER_2
    assert described_router2["meshName"] == MESH_NAME
    assert described_router2["metadata"]["meshOwner"] == mesh_owner
    assert described_router2["metadata"]["version"] == 2
    assert described_router2["spec"]["listeners"][0]["portMapping"]["port"] == 80
    assert described_router2["spec"]["listeners"][0]["portMapping"]["protocol"] == "tcp"
    assert described_router2["status"]["status"] == "ACTIVE"

    connection = client.delete_virtual_router(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        virtualRouterName=ROUTER_1,
    )
    deleted_router1 = connection.get("virtualRouter")
    assert deleted_router1 is not None
    assert deleted_router1["virtualRouterName"] == ROUTER_1
    assert deleted_router1["meshName"] == MESH_NAME
    assert deleted_router1["metadata"]["meshOwner"] == mesh_owner
    assert deleted_router1["metadata"]["version"] == 1
    assert deleted_router1["spec"]["listeners"][0]["portMapping"]["port"] == 80
    assert deleted_router1["spec"]["listeners"][0]["portMapping"]["protocol"] == "http"
    assert deleted_router1["status"]["status"] == "DELETED"
    with pytest.raises(ClientError) as e:
        client.describe_virtual_router(
            meshName=MESH_NAME,
            meshOwner=mesh_owner,
            virtualRouterName=ROUTER_1,
        )
    err = e.value.response["Error"]
    assert err["Code"] == "VirtualRouterNotFound"
    assert (
        err["Message"]
        == f"The mesh {MESH_NAME} does not have a virtual router named {ROUTER_1}."
    )

@mock_aws
def test_create_describe_list_update_delete_route(client):
    MESH_NAME = "mock_mesh"
    ROUTER_NAME = "mock_virtual_router"

    connection = client.create_mesh(
        meshName=MESH_NAME,
        spec={
            "egressFilter": {"type": "DROP_ALL"},
            "serviceDiscovery": {"ipPreference": "IPv4_ONLY"},
        },
        tags=[{"key": "owner", "value": "moto"}],
    )
    assert "mesh" in connection
    mesh = connection["mesh"]
    assert "metadata" in mesh
    mesh_owner = mesh["metadata"]["meshOwner"]

    connection = client.create_virtual_router(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        virtualRouterName=ROUTER_NAME,
        spec={"listeners": [{"portMapping": {"port": 80, "protocol": "http"}}]},
        tags=[{"key": "router_traffic", "value": "http"}],
    )
    router = connection.get("virtualRouter")
    assert router is not None
    assert router["meshName"] == MESH_NAME
    assert router["metadata"]["meshOwner"] == mesh_owner
    assert router["virtualRouterName"] == ROUTER_NAME

    ROUTE_1 = "route1"
    ROUTE_2 = "route2"
    connection = client.create_route(
        meshOwner=mesh_owner,
        meshName=MESH_NAME,
        virtualRouterName=ROUTER_NAME,
        routeName=ROUTE_1,
        tags=[{"key": "license", "value": "apache" }],
        spec=route_spec(ROUTE_1)
    )
    connection = client.create_route(
        meshOwner=mesh_owner,
        meshName=MESH_NAME,
        virtualRouterName=ROUTER_NAME,
        routeName=ROUTE_2,
        tags=[{"key": "license", "value": "mit" }],
        spec=route_spec(ROUTE_2)
    )
    connection = client.list_routes()
    connection = client.update_route()
    connection = client.describe_route()
    connection = client.delete_route()
    with pytest.raises(ClientError) as e:
        client.describe_route()
    err = e.value.response["Error"]
    assert err["Code"] == "RouteNotFound"
    assert (
        err["Message"]
        == f"There is no route named {ROUTE_1} associated with router {ROUTER_NAME} in mesh {MESH_NAME}."
    )