"""Unit tests for appmesh-supported APIs."""

from collections import defaultdict
from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from .data import (
    grpc_route_spec,
    http2_route_spec,
    http_route_spec,
    modified_http_route_spec,
    tcp_route_spec,
)

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
    assert mesh["meshName"] == "mesh1"
    assert mesh["spec"]["egressFilter"]["type"] == "ALLOW_ALL"
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv6_PREFERRED"
    assert mesh["status"]["status"] == "ACTIVE"
    assert mesh["metadata"]["version"] == 2

    # Describe mesh 1, should reflect changes
    connection = client.describe_mesh(meshName="mesh1")
    mesh = connection.get("mesh")
    assert mesh["meshName"] == "mesh1"
    assert mesh["spec"]["egressFilter"]["type"] == "ALLOW_ALL"
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv6_PREFERRED"
    assert mesh["status"]["status"] == "ACTIVE"
    assert mesh["metadata"]["version"] == 2

    connection = client.delete_mesh(meshName="mesh2")
    mesh = connection.get("mesh")
    assert mesh["meshName"] == "mesh2"
    assert mesh["spec"]["egressFilter"]["type"] == "ALLOW_ALL"
    assert mesh["spec"]["serviceDiscovery"]["ipPreference"] == "IPv4_PREFERRED"
    assert mesh["status"]["status"] == "DELETED"

    connection = client.list_meshes()
    meshes = connection.get("meshes")
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
    assert router2["meshName"] == MESH_NAME
    assert router2["metadata"]["meshOwner"] == mesh_owner
    assert router2["metadata"]["version"] == 1
    assert router2["spec"]["listeners"][0]["portMapping"]["port"] == 443
    assert router2["spec"]["listeners"][0]["portMapping"]["protocol"] == "http2"
    assert router2["status"]["status"] == "ACTIVE"
    connection = client.list_virtual_routers(meshName=MESH_NAME, meshOwner=mesh_owner)
    virtual_routers = connection.get("virtualRouters")
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
    assert router["meshName"] == MESH_NAME
    assert router["metadata"]["meshOwner"] == mesh_owner
    assert router["virtualRouterName"] == ROUTER_NAME

    ROUTE_1 = "route1"
    ROUTE_2 = "route2"
    ROUTE_3 = "route3"
    ROUTE_4 = "route4"

    connection = client.create_route(
        meshOwner=mesh_owner,
        meshName=MESH_NAME,
        virtualRouterName=ROUTER_NAME,
        routeName=ROUTE_1,
        tags=[{"key": "license", "value": "apache"}],
        spec=grpc_route_spec,
    )

    assert "route" in connection
    route = connection["route"]
    assert "spec" in route
    spec = route["spec"]
    assert spec["priority"] == 1
    grpc_route = spec["grpcRoute"]

    # action assertions
    assert len(grpc_route["action"]["weightedTargets"]) == 1
    weighted_target = grpc_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 8080
    assert weighted_target["virtualNode"] == "my-virtual-node"
    assert weighted_target["weight"] == 50

    # match assertions
    assert len(grpc_route["match"]["metadata"]) == 1
    metadata = grpc_route["match"]["metadata"][0]
    assert metadata["invert"] is False
    assert metadata["match"]["exact"] == "example-value"
    assert metadata["name"] == "my-metadata-key"
    assert grpc_route["match"]["methodName"] == "myMethod"
    assert grpc_route["match"]["port"] == 8080
    assert grpc_route["match"]["serviceName"] == "myService"

    # retryPolicy assertions
    assert grpc_route["retryPolicy"]["grpcRetryEvents"] == [
        "unavailable",
        "resource-exhausted",
    ]
    assert grpc_route["retryPolicy"]["httpRetryEvents"] == ["gateway-error"]
    assert grpc_route["retryPolicy"]["maxRetries"] == 3
    assert grpc_route["retryPolicy"]["perRetryTimeout"]["unit"] == "ms"
    assert grpc_route["retryPolicy"]["perRetryTimeout"]["value"] == 200
    assert grpc_route["retryPolicy"]["tcpRetryEvents"] == ["connection-error"]

    # timeout assertions
    assert grpc_route["timeout"]["idle"]["unit"] == "s"
    assert grpc_route["timeout"]["idle"]["value"] == 60
    assert grpc_route["timeout"]["perRequest"]["unit"] == "s"
    assert grpc_route["timeout"]["perRequest"]["value"] == 5

    connection = client.create_route(
        meshOwner=mesh_owner,
        meshName=MESH_NAME,
        virtualRouterName=ROUTER_NAME,
        routeName=ROUTE_2,
        tags=[{"key": "license", "value": "mit"}],
        spec=http_route_spec,
    )
    assert "route" in connection
    route = connection["route"]
    assert "spec" in route
    spec = route["spec"]
    assert spec["priority"] == 2
    http_route = http_route_spec["httpRoute"]

    # action assertions
    assert len(http_route["action"]["weightedTargets"]) == 1
    weighted_target = http_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 80
    assert weighted_target["virtualNode"] == "web-server-node"
    assert weighted_target["weight"] == 100

    # match assertions
    assert len(http_route["match"]["headers"]) == 1
    header = http_route["match"]["headers"][0]
    assert header["invert"] is True
    assert header["match"]["prefix"] == "Bearer "
    assert header["name"] == "Authorization"
    assert http_route["match"]["method"] == "POST"
    assert http_route["match"]["path"]["exact"] == "/login"
    assert http_route["match"]["port"] == 80
    assert (
        http_route["match"]["queryParameters"][0]["match"]["exact"] == "example-match"
    )
    assert http_route["match"]["queryParameters"][0]["name"] == "http-query-param"
    assert http_route["match"]["scheme"] == "http"

    # retryPolicy assertions
    assert http_route["retryPolicy"]["httpRetryEvents"] == [
        "gateway-error",
        "client-error",
    ]
    assert http_route["retryPolicy"]["maxRetries"] == 0
    assert http_route["retryPolicy"]["perRetryTimeout"]["unit"] == "ms"
    assert http_route["retryPolicy"]["perRetryTimeout"]["value"] == 0
    assert http_route["retryPolicy"]["tcpRetryEvents"] == ["connection-error"]

    # timeout assertions
    assert http_route["timeout"]["idle"]["unit"] == "s"
    assert http_route["timeout"]["idle"]["value"] == 15
    assert http_route["timeout"]["perRequest"]["unit"] == "s"
    assert http_route["timeout"]["perRequest"]["value"] == 1

    connection = client.create_route(
        meshOwner=mesh_owner,
        meshName=MESH_NAME,
        virtualRouterName=ROUTER_NAME,
        routeName=ROUTE_3,
        tags=[{"key": "license", "value": "mpl"}],
        spec=http2_route_spec,
    )
    assert "route" in connection
    route = connection["route"]
    assert "spec" in route
    spec = route["spec"]
    assert spec["priority"] == 3
    http2_route = spec["http2Route"]

    # action assertions
    assert len(http2_route["action"]["weightedTargets"]) == 1
    weighted_target = http2_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 80
    assert weighted_target["virtualNode"] == "web-server-node"
    assert weighted_target["weight"] == 75

    # match assertions
    assert len(http2_route["match"]["headers"]) == 1
    header = http2_route["match"]["headers"][0]
    assert header["invert"] is False
    assert header["match"]["exact"] == "application/json"
    assert header["name"] == "Content-Type"
    assert http2_route["match"]["method"] == "GET"
    assert http2_route["match"]["path"]["exact"] == "/api/products"
    assert http2_route["match"]["port"] == 80
    assert http2_route["match"]["prefix"] == "/api"
    assert len(http2_route["match"]["queryParameters"]) == 1
    query_param = http2_route["match"]["queryParameters"][0]
    assert query_param["match"]["exact"] == "electronics"
    assert query_param["name"] == "category"
    assert http2_route["match"]["scheme"] == "https"

    # retryPolicy assertions
    assert http2_route["retryPolicy"]["httpRetryEvents"] == ["server-error"]
    assert http2_route["retryPolicy"]["maxRetries"] == 2
    assert http2_route["retryPolicy"]["perRetryTimeout"]["unit"] == "ms"
    assert http2_route["retryPolicy"]["perRetryTimeout"]["value"] == 500
    assert http2_route["retryPolicy"]["tcpRetryEvents"] == ["connection-error"]

    # timeout assertions
    assert http2_route["timeout"]["idle"]["unit"] == "s"
    assert http2_route["timeout"]["idle"]["value"] == 30
    assert http2_route["timeout"]["perRequest"]["unit"] == "s"
    assert http2_route["timeout"]["perRequest"]["value"] == 2

    connection = client.create_route(
        meshOwner=mesh_owner,
        meshName=MESH_NAME,
        virtualRouterName=ROUTER_NAME,
        routeName=ROUTE_4,
        tags=[{"key": "license", "value": "bsd"}],
        spec=tcp_route_spec,
    )
    assert "route" in connection
    route = connection["route"]
    assert "spec" in route
    spec = route["spec"]
    assert spec["priority"] == 4
    tcp_route = tcp_route_spec["tcpRoute"]

    # action assertions
    assert len(tcp_route["action"]["weightedTargets"]) == 1
    weighted_target = tcp_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 22
    assert weighted_target["virtualNode"] == "ssh-server-node"
    assert weighted_target["weight"] == 100

    # match assertions
    assert tcp_route["match"]["port"] == 22

    # timeout assertions
    assert tcp_route["timeout"]["idle"]["unit"] == "s"
    assert tcp_route["timeout"]["idle"]["value"] == 600

    connection = client.list_routes(meshName=MESH_NAME, virtualRouterName=ROUTER_NAME)
    routes = connection.get("routes")
    assert isinstance(routes, list)
    assert len(routes) == 4
    names_counted = defaultdict(int)
    for route in routes:
        route_name = route.get("routeName")
        if route_name:
            names_counted[route_name] += 1
    assert names_counted[ROUTE_1] == 1
    assert names_counted[ROUTE_2] == 1
    assert names_counted[ROUTE_3] == 1
    assert names_counted[ROUTE_4] == 1

    connection = client.update_route(
        meshName=MESH_NAME,
        routeName=ROUTE_2,
        virtualRouterName=ROUTER_NAME,
        spec=modified_http_route_spec,
    )
    assert "route" in connection
    route = connection["route"]
    assert route["metadata"]["version"] == 2
    assert "spec" in route
    spec = route["spec"]
    assert spec["priority"] == 5

    modified_http_route = spec["httpRoute"]

    # action assertions
    assert len(modified_http_route["action"]["weightedTargets"]) == 1
    weighted_target = modified_http_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 8080
    assert weighted_target["virtualNode"] == "api-server-node"
    assert weighted_target["weight"] == 50

    # match assertions
    assert len(modified_http_route["match"]["headers"]) == 1
    header = modified_http_route["match"]["headers"][0]
    assert header["invert"] is False
    assert header["match"]["prefix"] == "Token "
    assert header["name"] == "X-Auth-Token"
    assert modified_http_route["match"]["method"] == "GET"
    assert modified_http_route["match"]["path"]["exact"] == "/profile"
    assert modified_http_route["match"]["port"] == 443
    assert len(modified_http_route["match"]["queryParameters"]) == 1
    query_param = modified_http_route["match"]["queryParameters"][0]
    assert query_param["match"]["exact"] == "modified-match"
    assert query_param["name"] == "filter-param"
    assert modified_http_route["match"]["scheme"] == "https"

    # retryPolicy assertions
    assert modified_http_route["retryPolicy"]["httpRetryEvents"] == ["server-error"]
    assert modified_http_route["retryPolicy"]["maxRetries"] == 3
    assert modified_http_route["retryPolicy"]["perRetryTimeout"]["unit"] == "s"
    assert modified_http_route["retryPolicy"]["perRetryTimeout"]["value"] == 2
    assert modified_http_route["retryPolicy"]["tcpRetryEvents"] == ["connection-reset"]

    # timeout assertions
    assert modified_http_route["timeout"]["idle"]["unit"] == "m"
    assert modified_http_route["timeout"]["idle"]["value"] == 5
    assert modified_http_route["timeout"]["perRequest"]["unit"] == "ms"
    assert modified_http_route["timeout"]["perRequest"]["value"] == 500
    connection = client.describe_route(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        routeName=ROUTE_2,
        virtualRouterName=ROUTER_NAME,
    )
    assert "route" in connection
    route = connection["route"]
    assert route["metadata"]["version"] == 2
    assert "spec" in route
    spec = route["spec"]
    assert spec["priority"] == 5

    described_http_route = spec["httpRoute"]

    # action assertions
    assert len(described_http_route["action"]["weightedTargets"]) == 1
    weighted_target = described_http_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 8080
    assert weighted_target["virtualNode"] == "api-server-node"
    assert weighted_target["weight"] == 50

    # match assertions
    assert len(described_http_route["match"]["headers"]) == 1
    header = described_http_route["match"]["headers"][0]
    assert header["invert"] is False
    assert header["match"]["prefix"] == "Token "
    assert header["name"] == "X-Auth-Token"
    assert described_http_route["match"]["method"] == "GET"
    assert described_http_route["match"]["path"]["exact"] == "/profile"
    assert described_http_route["match"]["port"] == 443
    assert len(described_http_route["match"]["queryParameters"]) == 1
    query_param = described_http_route["match"]["queryParameters"][0]
    assert query_param["match"]["exact"] == "modified-match"
    assert query_param["name"] == "filter-param"
    assert described_http_route["match"]["scheme"] == "https"

    # retryPolicy assertions
    assert described_http_route["retryPolicy"]["httpRetryEvents"] == ["server-error"]
    assert described_http_route["retryPolicy"]["maxRetries"] == 3
    assert described_http_route["retryPolicy"]["perRetryTimeout"]["unit"] == "s"
    assert described_http_route["retryPolicy"]["perRetryTimeout"]["value"] == 2
    assert described_http_route["retryPolicy"]["tcpRetryEvents"] == ["connection-reset"]

    # timeout assertions
    assert described_http_route["timeout"]["idle"]["unit"] == "m"
    assert described_http_route["timeout"]["idle"]["value"] == 5
    assert described_http_route["timeout"]["perRequest"]["unit"] == "ms"
    assert described_http_route["timeout"]["perRequest"]["value"] == 500
    connection = client.delete_route(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        routeName=ROUTE_4,
        virtualRouterName=ROUTER_NAME,
    )
    assert "route" in connection
    route = connection["route"]
    assert route["status"]["status"] == "DELETED"
    assert "spec" in route
    spec = route["spec"]
    assert spec["priority"] == 4
    deleted_route = tcp_route_spec["tcpRoute"]

    # action assertions
    assert len(deleted_route["action"]["weightedTargets"]) == 1
    weighted_target = deleted_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 22
    assert weighted_target["virtualNode"] == "ssh-server-node"
    assert weighted_target["weight"] == 100

    # match assertions
    assert deleted_route["match"]["port"] == 22

    # timeout assertions
    assert deleted_route["timeout"]["idle"]["unit"] == "s"
    assert deleted_route["timeout"]["idle"]["value"] == 600

    with pytest.raises(ClientError) as e:
        client.describe_route(
            meshName=MESH_NAME,
            meshOwner=mesh_owner,
            routeName=ROUTE_4,
            virtualRouterName=ROUTER_NAME,
        )
    err = e.value.response["Error"]
    assert err["Code"] == "RouteNotFound"
    assert (
        err["Message"]
        == f"There is no route named {ROUTE_4} associated with router {ROUTER_NAME} in mesh {MESH_NAME}."
    )
