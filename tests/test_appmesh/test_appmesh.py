"""Unit tests for appmesh-supported APIs."""

from collections import defaultdict
from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from .data import (
    grpc_route_spec,
    grpc_virtual_node_spec,
    http2_route_spec,
    http2_virtual_node_spec,
    http_route_spec,
    http_virtual_node_spec,
    modified_http2_virtual_node_spec,
    modified_http_route_spec,
    tcp_route_spec,
    tcp_virtual_node_spec,
)

MESH_NAME = "mock_mesh"


@pytest.fixture(name="client")
def fixture_transfer_client():
    with mock_aws():
        yield boto3.client("appmesh", region_name="us-east-1")


@mock_aws
def test_create_list_update_describe_delete_mesh(client):
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
def test_create_describe_list_update_delete_virtual_router(client):
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

    route = connection["route"]

    spec = route["spec"]
    assert spec["priority"] == 1
    grpc_route = spec["grpcRoute"]

    assert len(grpc_route["action"]["weightedTargets"]) == 1
    weighted_target = grpc_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 8080
    assert weighted_target["virtualNode"] == "my-virtual-node"
    assert weighted_target["weight"] == 50

    assert len(grpc_route["match"]["metadata"]) == 1
    metadata = grpc_route["match"]["metadata"][0]
    assert metadata["invert"] is False
    assert metadata["match"]["exact"] == "example-value"
    assert metadata["name"] == "my-metadata-key"
    assert grpc_route["match"]["methodName"] == "myMethod"
    assert grpc_route["match"]["port"] == 8080
    assert grpc_route["match"]["serviceName"] == "myService"

    assert grpc_route["retryPolicy"]["grpcRetryEvents"] == [
        "unavailable",
        "resource-exhausted",
    ]
    assert grpc_route["retryPolicy"]["httpRetryEvents"] == ["gateway-error"]
    assert grpc_route["retryPolicy"]["maxRetries"] == 3
    assert grpc_route["retryPolicy"]["perRetryTimeout"]["unit"] == "ms"
    assert grpc_route["retryPolicy"]["perRetryTimeout"]["value"] == 200
    assert grpc_route["retryPolicy"]["tcpRetryEvents"] == ["connection-error"]

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

    route = connection["route"]

    spec = route["spec"]
    assert spec["priority"] == 2
    http_route = http_route_spec["httpRoute"]

    assert len(http_route["action"]["weightedTargets"]) == 1
    weighted_target = http_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 80
    assert weighted_target["virtualNode"] == "web-server-node"
    assert weighted_target["weight"] == 100

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

    assert http_route["retryPolicy"]["httpRetryEvents"] == [
        "gateway-error",
        "client-error",
    ]
    assert http_route["retryPolicy"]["maxRetries"] == 0
    assert http_route["retryPolicy"]["perRetryTimeout"]["unit"] == "ms"
    assert http_route["retryPolicy"]["perRetryTimeout"]["value"] == 0
    assert http_route["retryPolicy"]["tcpRetryEvents"] == ["connection-error"]

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

    route = connection["route"]

    spec = route["spec"]
    assert spec["priority"] == 3
    http2_route = spec["http2Route"]

    assert len(http2_route["action"]["weightedTargets"]) == 1
    weighted_target = http2_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 80
    assert weighted_target["virtualNode"] == "web-server-node"
    assert weighted_target["weight"] == 75

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

    assert http2_route["retryPolicy"]["httpRetryEvents"] == ["server-error"]
    assert http2_route["retryPolicy"]["maxRetries"] == 2
    assert http2_route["retryPolicy"]["perRetryTimeout"]["unit"] == "ms"
    assert http2_route["retryPolicy"]["perRetryTimeout"]["value"] == 500
    assert http2_route["retryPolicy"]["tcpRetryEvents"] == ["connection-error"]

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

    route = connection["route"]

    spec = route["spec"]
    assert spec["priority"] == 4
    tcp_route = tcp_route_spec["tcpRoute"]

    assert len(tcp_route["action"]["weightedTargets"]) == 1
    weighted_target = tcp_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 22
    assert weighted_target["virtualNode"] == "ssh-server-node"
    assert weighted_target["weight"] == 100

    assert tcp_route["match"]["port"] == 22

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

    route = connection["route"]
    assert route["metadata"]["version"] == 2

    spec = route["spec"]
    assert spec["priority"] == 5

    modified_http_route = spec["httpRoute"]

    assert len(modified_http_route["action"]["weightedTargets"]) == 1
    weighted_target = modified_http_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 8080
    assert weighted_target["virtualNode"] == "api-server-node"
    assert weighted_target["weight"] == 50

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

    assert modified_http_route["retryPolicy"]["httpRetryEvents"] == ["server-error"]
    assert modified_http_route["retryPolicy"]["maxRetries"] == 3
    assert modified_http_route["retryPolicy"]["perRetryTimeout"]["unit"] == "s"
    assert modified_http_route["retryPolicy"]["perRetryTimeout"]["value"] == 2
    assert modified_http_route["retryPolicy"]["tcpRetryEvents"] == ["connection-reset"]

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

    route = connection["route"]
    assert route["metadata"]["version"] == 2

    spec = route["spec"]
    assert spec["priority"] == 5

    described_http_route = spec["httpRoute"]

    assert len(described_http_route["action"]["weightedTargets"]) == 1
    weighted_target = described_http_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 8080
    assert weighted_target["virtualNode"] == "api-server-node"
    assert weighted_target["weight"] == 50

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

    assert described_http_route["retryPolicy"]["httpRetryEvents"] == ["server-error"]
    assert described_http_route["retryPolicy"]["maxRetries"] == 3
    assert described_http_route["retryPolicy"]["perRetryTimeout"]["unit"] == "s"
    assert described_http_route["retryPolicy"]["perRetryTimeout"]["value"] == 2
    assert described_http_route["retryPolicy"]["tcpRetryEvents"] == ["connection-reset"]

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

    route = connection["route"]
    assert route["status"]["status"] == "DELETED"

    spec = route["spec"]
    assert spec["priority"] == 4
    deleted_route = tcp_route_spec["tcpRoute"]

    assert len(deleted_route["action"]["weightedTargets"]) == 1
    weighted_target = deleted_route["action"]["weightedTargets"][0]
    assert weighted_target["port"] == 22
    assert weighted_target["virtualNode"] == "ssh-server-node"
    assert weighted_target["weight"] == 100

    assert deleted_route["match"]["port"] == 22

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


@mock_aws
def test_create_describe_list_update_delete_virtual_node(client):
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

    GRPC_NODE = "grpc_node"
    HTTP_NODE = "http_node"
    HTTP2_NODE = "http2_node"
    TCP_NODE = "tcp_node"

    connection = client.create_virtual_node(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        spec=grpc_virtual_node_spec,
        tags=[{"key": "type", "value": "grpc"}],
        virtualNodeName=GRPC_NODE,
    )
    virtualNode = connection["virtualNode"]
    spec = virtualNode["spec"]
    backend_defaults = spec["backendDefaults"]
    tls = backend_defaults["clientPolicy"]["tls"]
    assert tls["enforce"] is True
    assert tls["ports"] == [443]
    assert tls["certificate"]["file"]["certificateChain"] == "/path/to/cert_chain.pem"
    assert tls["certificate"]["file"]["privateKey"] == "/path/to/private_key.pem"
    assert tls["validation"]["subjectAlternativeNames"]["match"]["exact"] == [
        "grpc.example.com"
    ]
    assert (
        tls["validation"]["trust"]["file"]["certificateChain"]
        == "/path/to/ca_bundle.pem"
    )

    assert len(spec["backends"]) == 1
    backend = spec["backends"][0]
    assert backend["virtualService"]["clientPolicy"]["tls"]["enforce"] is True
    assert backend["virtualService"]["clientPolicy"]["tls"]["ports"] == [443]
    validation = backend["virtualService"]["clientPolicy"]["tls"]["validation"]
    assert validation["subjectAlternativeNames"]["match"]["exact"] == [
        "validation-alternate-name"
    ]
    assert validation["trust"]["acm"]["certificateAuthorityArns"] == ["example-acm-arn"]
    assert (
        backend["virtualService"]["virtualServiceName"]
        == "my-grpc-service.default.svc.cluster.local"
    )

    assert len(spec["listeners"]) == 1
    listener = spec["listeners"][0]
    assert listener["connectionPool"]["grpc"]["maxRequests"] == 500
    assert listener["healthCheck"]["healthyThreshold"] == 2
    assert listener["healthCheck"]["intervalMillis"] == 5000
    assert listener["healthCheck"]["port"] == 50051
    assert listener["healthCheck"]["protocol"] == "grpc"
    assert listener["healthCheck"]["timeoutMillis"] == 2000
    assert listener["healthCheck"]["unhealthyThreshold"] == 3
    assert listener["portMapping"]["port"] == 50051
    assert listener["portMapping"]["protocol"] == "grpc"
    assert listener["timeout"]["grpc"]["idle"]["unit"] == "s"
    assert listener["timeout"]["grpc"]["idle"]["value"] == 600
    assert listener["timeout"]["grpc"]["perRequest"]["unit"] == "s"
    assert listener["timeout"]["grpc"]["perRequest"]["value"] == 30
    assert (
        listener["tls"]["certificate"]["acm"]["certificateArn"]
        == "arn:aws:acm:us-east-1:123456789012:certificate/abcdefg-1234-5678-90ab-cdef01234567"
    )
    assert listener["tls"]["mode"] == "STRICT"
    assert (
        listener["tls"]["validation"]["trust"]["sds"]["secretName"]
        == "my-ca-bundle-secret"
    )

    access_log = spec["logging"]["accessLog"]
    assert access_log["file"]["path"] == "/var/log/appmesh/new_access.log"
    assert len(access_log["file"]["format"]["json"]) == 2
    assert access_log["file"]["format"]["json"][0] == {
        "key": "end_time",
        "value": "%END_TIME%",
    }
    assert access_log["file"]["format"]["json"][1] == {
        "key": "status_code",
        "value": "%RESPONSE_CODE%",
    }

    service_discovery = spec["serviceDiscovery"]["awsCloudMap"]
    assert len(service_discovery["attributes"]) == 1
    assert service_discovery["attributes"][0] == {"key": "region", "value": "us-east-1"}
    assert service_discovery["ipPreference"] == "IPv6_PREFERRED"
    assert service_discovery["namespaceName"] == "new-namespace"
    assert service_discovery["serviceName"] == "new-service"

    connection = client.create_virtual_node(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        spec=http_virtual_node_spec,
        tags=[{"key": "type", "value": "http"}],
        virtualNodeName=HTTP_NODE,
    )
    virtualNode = connection["virtualNode"]
    spec = virtualNode["spec"]

    backend_defaults = spec["backendDefaults"]
    tls = backend_defaults["clientPolicy"]["tls"]
    assert tls["enforce"] is True
    assert tls["ports"] == [443]
    assert tls["certificate"]["file"]["certificateChain"] == "/path/to/cert_chain.pem"
    assert tls["certificate"]["file"]["privateKey"] == "/path/to/private_key.pem"
    assert tls["validation"]["subjectAlternativeNames"]["match"]["exact"] == [
        "www.example.com",
        "api.example.com",
    ]
    assert (
        tls["validation"]["trust"]["file"]["certificateChain"]
        == "/path/to/ca_bundle.pem"
    )

    assert len(spec["backends"]) == 1
    backend = spec["backends"][0]
    assert backend["virtualService"]["clientPolicy"]["tls"]["enforce"] is False
    validation = backend["virtualService"]["clientPolicy"]["tls"]["validation"]
    assert validation["subjectAlternativeNames"]["match"]["exact"] == [
        "example-alternative-name"
    ]
    assert (
        validation["trust"]["file"]["certificateChain"] == "example-certificate-chain"
    )
    assert (
        backend["virtualService"]["virtualServiceName"]
        == "my-service.default.svc.cluster.local"
    )

    assert len(spec["listeners"]) == 1
    listener = spec["listeners"][0]
    assert listener["connectionPool"]["http"]["maxConnections"] == 1000
    assert listener["connectionPool"]["http"]["maxPendingRequests"] == 5000
    assert listener["healthCheck"]["healthyThreshold"] == 2
    assert listener["healthCheck"]["intervalMillis"] == 5000
    assert listener["healthCheck"]["path"] == "/health"
    assert listener["healthCheck"]["port"] == 80
    assert listener["healthCheck"]["protocol"] == "http"
    assert listener["healthCheck"]["timeoutMillis"] == 2000
    assert listener["healthCheck"]["unhealthyThreshold"] == 3
    assert listener["outlierDetection"]["baseEjectionDuration"]["unit"] == "s"
    assert listener["outlierDetection"]["baseEjectionDuration"]["value"] == 30
    assert listener["outlierDetection"]["interval"]["unit"] == "s"
    assert listener["outlierDetection"]["interval"]["value"] == 10
    assert listener["outlierDetection"]["maxEjectionPercent"] == 10
    assert listener["outlierDetection"]["maxServerErrors"] == 5
    assert listener["portMapping"]["port"] == 80
    assert listener["portMapping"]["protocol"] == "http"
    assert listener["timeout"]["http"]["idle"]["unit"] == "s"
    assert listener["timeout"]["http"]["idle"]["value"] == 60
    assert listener["timeout"]["http"]["perRequest"]["unit"] == "s"
    assert listener["timeout"]["http"]["perRequest"]["value"] == 5
    assert (
        listener["tls"]["certificate"]["acm"]["certificateArn"]
        == "arn:aws:acm:us-east-1:123456789012:certificate/abcdefg-1234-5678-90ab-cdef01234567"
    )
    assert listener["tls"]["mode"] == "STRICT"
    assert (
        listener["tls"]["validation"]["trust"]["sds"]["secretName"]
        == "my-ca-bundle-secret"
    )

    access_log = spec["logging"]["accessLog"]
    assert access_log["file"]["path"] == "/var/log/appmesh/access.log"
    assert len(access_log["file"]["format"]["json"]) == 2
    assert access_log["file"]["format"]["json"][0] == {
        "key": "start_time",
        "value": "%START_TIME%",
    }
    assert access_log["file"]["format"]["json"][1] == {
        "key": "method",
        "value": "%REQ(:METHOD)%",
    }

    service_discovery = spec["serviceDiscovery"]["awsCloudMap"]
    assert len(service_discovery["attributes"]) == 1
    assert service_discovery["attributes"][0] == {"key": "env", "value": "prod"}
    assert service_discovery["ipPreference"] == "IPv4_PREFERRED"
    assert service_discovery["namespaceName"] == "my-namespace"
    assert service_discovery["serviceName"] == "my-service"

    connection = client.create_virtual_node(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        spec=http2_virtual_node_spec,
        tags=[{"key": "type", "value": "http2"}],
        virtualNodeName=HTTP2_NODE,
    )
    virtualNode = connection["virtualNode"]
    spec = virtualNode["spec"]
    backend_defaults = spec["backendDefaults"]
    tls = backend_defaults["clientPolicy"]["tls"]
    assert tls["enforce"] is True
    assert tls["ports"] == [443]
    assert tls["certificate"]["file"]["certificateChain"] == "/path/to/cert_chain.pem"
    assert tls["certificate"]["file"]["privateKey"] == "/path/to/private_key.pem"
    assert tls["validation"]["subjectAlternativeNames"]["match"]["exact"] == [
        "http2.example.com"
    ]
    assert (
        tls["validation"]["trust"]["file"]["certificateChain"]
        == "/path/to/ca_bundle.pem"
    )

    assert len(spec["backends"]) == 1
    backend = spec["backends"][0]
    assert backend["virtualService"]["clientPolicy"]["tls"]["enforce"] is True
    assert backend["virtualService"]["clientPolicy"]["tls"]["ports"] == [443]
    validation = backend["virtualService"]["clientPolicy"]["tls"]["validation"]
    assert validation["subjectAlternativeNames"]["match"]["exact"] == ["match-me"]
    assert validation["trust"]["sds"]["secretName"] == "example-secret-name"
    assert (
        backend["virtualService"]["virtualServiceName"]
        == "my-http2-service.default.svc.cluster.local"
    )

    assert len(spec["listeners"]) == 1
    listener = spec["listeners"][0]
    assert listener["connectionPool"]["http2"]["maxRequests"] == 1000
    assert listener["healthCheck"]["healthyThreshold"] == 2
    assert listener["healthCheck"]["intervalMillis"] == 5000
    assert listener["healthCheck"]["path"] == "/"
    assert listener["healthCheck"]["port"] == 443
    assert listener["healthCheck"]["protocol"] == "http2"
    assert listener["healthCheck"]["timeoutMillis"] == 2000
    assert listener["healthCheck"]["unhealthyThreshold"] == 3
    assert listener["portMapping"]["port"] == 443
    assert listener["portMapping"]["protocol"] == "http2"
    assert listener["timeout"]["http2"]["idle"]["unit"] == "s"
    assert listener["timeout"]["http2"]["idle"]["value"] == 120
    assert listener["timeout"]["http2"]["perRequest"]["unit"] == "s"
    assert listener["timeout"]["http2"]["perRequest"]["value"] == 10
    assert (
        listener["tls"]["certificate"]["acm"]["certificateArn"]
        == "arn:aws:acm:us-east-1:123456789012:certificate/abcdefg-1234-5678-90ab-cdef01234567"
    )
    assert listener["tls"]["mode"] == "STRICT"
    assert (
        listener["tls"]["validation"]["trust"]["sds"]["secretName"]
        == "my-ca-bundle-secret"
    )

    access_log = spec["logging"]["accessLog"]
    assert access_log["file"]["path"] == "/var/log/appmesh/new_access.log"
    assert len(access_log["file"]["format"]["json"]) == 2
    assert access_log["file"]["format"]["json"][0] == {
        "key": "end_time",
        "value": "%END_TIME%",
    }
    assert access_log["file"]["format"]["json"][1] == {
        "key": "status_code",
        "value": "%RESPONSE_CODE%",
    }

    service_discovery = spec["serviceDiscovery"]["awsCloudMap"]
    assert len(service_discovery["attributes"]) == 1
    assert service_discovery["attributes"][0] == {"key": "region", "value": "us-east-1"}
    assert service_discovery["ipPreference"] == "IPv6_PREFERRED"
    assert service_discovery["namespaceName"] == "new-namespace"
    assert service_discovery["serviceName"] == "new-service"

    connection = client.create_virtual_node(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        spec=tcp_virtual_node_spec,
        tags=[{"key": "type", "value": "tcp"}],
        virtualNodeName=TCP_NODE,
    )
    virtualNode = connection["virtualNode"]
    spec = virtualNode["spec"]
    backend_defaults = spec["backendDefaults"]
    tls = backend_defaults["clientPolicy"]["tls"]
    assert tls["enforce"] is True
    assert tls["ports"] == [443]
    assert tls["certificate"]["file"]["certificateChain"] == "/path/to/cert_chain.pem"
    assert tls["certificate"]["file"]["privateKey"] == "/path/to/private_key.pem"
    assert tls["validation"]["subjectAlternativeNames"]["match"]["exact"] == [
        "tcp.example.com"
    ]
    assert (
        tls["validation"]["trust"]["file"]["certificateChain"]
        == "/path/to/ca_bundle.pem"
    )

    assert len(spec["backends"]) == 1
    backend = spec["backends"][0]
    assert backend["virtualService"]["clientPolicy"]["tls"]["enforce"] is False
    validation = backend["virtualService"]["clientPolicy"]["tls"]["validation"]
    assert validation["subjectAlternativeNames"]["match"]["exact"] == [
        "exact-match-example"
    ]
    assert validation["trust"]["file"]["certificateChain"] == "test-certificate-chain"
    assert (
        backend["virtualService"]["virtualServiceName"]
        == "my-tcp-service.default.svc.cluster.local"
    )

    assert len(spec["listeners"]) == 1
    listener = spec["listeners"][0]
    assert listener["connectionPool"]["tcp"]["maxConnections"] == 2000
    assert listener["healthCheck"]["healthyThreshold"] == 2
    assert listener["healthCheck"]["intervalMillis"] == 10000
    assert listener["healthCheck"]["port"] == 8080
    assert listener["healthCheck"]["protocol"] == "tcp"
    assert listener["healthCheck"]["timeoutMillis"] == 5000
    assert listener["healthCheck"]["unhealthyThreshold"] == 3
    assert listener["portMapping"]["port"] == 8080
    assert listener["portMapping"]["protocol"] == "tcp"
    assert listener["timeout"]["tcp"]["idle"]["unit"] == "m"
    assert listener["timeout"]["tcp"]["idle"]["value"] == 30

    access_log = spec["logging"]["accessLog"]
    assert access_log["file"]["path"] == "/var/log/appmesh/new_access.log"
    assert len(access_log["file"]["format"]["json"]) == 2
    assert access_log["file"]["format"]["json"][0] == {
        "key": "end_time",
        "value": "%END_TIME%",
    }
    assert access_log["file"]["format"]["json"][1] == {
        "key": "status_code",
        "value": "%RESPONSE_CODE%",
    }

    service_discovery = spec["serviceDiscovery"]["awsCloudMap"]
    assert len(service_discovery["attributes"]) == 1
    assert service_discovery["attributes"][0] == {"key": "region", "value": "us-east-1"}
    assert service_discovery["ipPreference"] == "IPv6_PREFERRED"
    assert service_discovery["namespaceName"] == "new-namespace"
    assert service_discovery["serviceName"] == "new-service"

    connection = client.list_virtual_nodes(meshName=MESH_NAME, meshOwner=mesh_owner)
    virtual_nodes = connection.get("virtualNodes")
    assert isinstance(virtual_nodes, list)
    assert len(virtual_nodes) == 4
    names_counted = defaultdict(int)
    for node in virtual_nodes:
        node_name = node.get("virtualNodeName")
        if node_name:
            names_counted[node_name] += 1
    assert names_counted[GRPC_NODE] == 1
    assert names_counted[HTTP_NODE] == 1
    assert names_counted[HTTP2_NODE] == 1
    assert names_counted[TCP_NODE] == 1

    connection = client.update_virtual_node(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        spec=modified_http2_virtual_node_spec,
        virtualNodeName=HTTP2_NODE,
    )
    virtualNode = connection["virtualNode"]
    spec = virtualNode["spec"]
    backend_defaults = spec["backendDefaults"]
    tls = backend_defaults["clientPolicy"]["tls"]
    assert tls["enforce"] is False
    assert tls["ports"] == [8443]
    assert (
        tls["certificate"]["file"]["certificateChain"]
        == "/updated/path/to/cert_chain.pem"
    )
    assert (
        tls["certificate"]["file"]["privateKey"] == "/updated/path/to/private_key.pem"
    )
    assert tls["validation"]["subjectAlternativeNames"]["match"]["exact"] == [
        "updated.example.com"
    ]
    assert (
        tls["validation"]["trust"]["file"]["certificateChain"]
        == "/updated/path/to/ca_bundle.pem"
    )

    assert len(spec["backends"]) == 1
    backend = spec["backends"][0]
    assert backend["virtualService"]["clientPolicy"]["tls"]["enforce"] is False
    assert backend["virtualService"]["clientPolicy"]["tls"]["ports"] == [8443]
    assert (
        backend["virtualService"]["virtualServiceName"]
        == "updated-http2-service.default.svc.cluster.local"
    )

    assert len(spec["listeners"]) == 1
    listener = spec["listeners"][0]
    assert listener["connectionPool"]["http2"]["maxRequests"] == 500
    assert listener["healthCheck"]["healthyThreshold"] == 3
    assert listener["healthCheck"]["intervalMillis"] == 5100
    assert listener["healthCheck"]["path"] == "/health"
    assert listener["healthCheck"]["port"] == 8443
    assert listener["healthCheck"]["protocol"] == "http2"
    assert listener["healthCheck"]["timeoutMillis"] == 2200
    assert listener["healthCheck"]["unhealthyThreshold"] == 2
    assert listener["portMapping"]["port"] == 8443
    assert listener["portMapping"]["protocol"] == "http2"
    assert listener["timeout"]["http2"]["idle"]["unit"] == "m"
    assert listener["timeout"]["http2"]["idle"]["value"] == 5
    assert listener["timeout"]["http2"]["perRequest"]["unit"] == "m"
    assert listener["timeout"]["http2"]["perRequest"]["value"] == 1
    assert (
        listener["tls"]["certificate"]["acm"]["certificateArn"]
        == "arn:aws:acm:us-west-2:987654321098:certificate/hgfedcba-4321-8765-ba09-fedc09876543"
    )
    assert listener["tls"]["mode"] == "PERMISSIVE"
    assert (
        listener["tls"]["validation"]["trust"]["sds"]["secretName"]
        == "updated-ca-bundle-secret"
    )

    access_log = spec["logging"]["accessLog"]
    assert access_log["file"]["path"] == "/var/log/appmesh/updated_access.log"
    assert len(access_log["file"]["format"]["json"]) == 2
    assert access_log["file"]["format"]["json"][0] == {
        "key": "start_time",
        "value": "%START_TIME%",
    }
    assert access_log["file"]["format"]["json"][1] == {
        "key": "method",
        "value": "%REQUEST_METHOD%",
    }

    service_discovery = spec["serviceDiscovery"]["awsCloudMap"]
    assert len(service_discovery["attributes"]) == 1
    assert service_discovery["attributes"][0] == {
        "key": "environment",
        "value": "production",
    }
    assert service_discovery["ipPreference"] == "IPv4_PREFERRED"
    assert service_discovery["namespaceName"] == "updated-namespace"
    assert service_discovery["serviceName"] == "updated-service"

    connection = client.describe_virtual_node(
        meshName=MESH_NAME, meshOwner=mesh_owner, virtualNodeName=HTTP2_NODE
    )
    virtualNode = connection["virtualNode"]
    spec = virtualNode["spec"]
    backend_defaults = spec["backendDefaults"]
    tls = backend_defaults["clientPolicy"]["tls"]
    assert tls["enforce"] is False
    assert tls["ports"] == [8443]
    assert (
        tls["certificate"]["file"]["certificateChain"]
        == "/updated/path/to/cert_chain.pem"
    )
    assert (
        tls["certificate"]["file"]["privateKey"] == "/updated/path/to/private_key.pem"
    )
    assert tls["validation"]["subjectAlternativeNames"]["match"]["exact"] == [
        "updated.example.com"
    ]
    assert (
        tls["validation"]["trust"]["file"]["certificateChain"]
        == "/updated/path/to/ca_bundle.pem"
    )

    assert len(spec["backends"]) == 1
    backend = spec["backends"][0]
    assert backend["virtualService"]["clientPolicy"]["tls"]["enforce"] is False
    assert backend["virtualService"]["clientPolicy"]["tls"]["ports"] == [8443]
    validation = backend["virtualService"]["clientPolicy"]["tls"]["validation"]
    assert validation["subjectAlternativeNames"]["match"]["exact"] == [
        "another-exact-match-example"
    ]
    assert (
        validation["trust"]["file"]["certificateChain"]
        == "different-test-certificate-chain"
    )
    assert (
        backend["virtualService"]["virtualServiceName"]
        == "updated-http2-service.default.svc.cluster.local"
    )

    assert len(spec["listeners"]) == 1
    listener = spec["listeners"][0]
    assert listener["connectionPool"]["http2"]["maxRequests"] == 500
    assert listener["healthCheck"]["healthyThreshold"] == 3
    assert listener["healthCheck"]["intervalMillis"] == 5100
    assert listener["healthCheck"]["path"] == "/health"
    assert listener["healthCheck"]["port"] == 8443
    assert listener["healthCheck"]["protocol"] == "http2"
    assert listener["healthCheck"]["timeoutMillis"] == 2200
    assert listener["healthCheck"]["unhealthyThreshold"] == 2
    assert listener["portMapping"]["port"] == 8443
    assert listener["portMapping"]["protocol"] == "http2"
    assert listener["timeout"]["http2"]["idle"]["unit"] == "m"
    assert listener["timeout"]["http2"]["idle"]["value"] == 5
    assert listener["timeout"]["http2"]["perRequest"]["unit"] == "m"
    assert listener["timeout"]["http2"]["perRequest"]["value"] == 1
    assert (
        listener["tls"]["certificate"]["acm"]["certificateArn"]
        == "arn:aws:acm:us-west-2:987654321098:certificate/hgfedcba-4321-8765-ba09-fedc09876543"
    )
    assert listener["tls"]["mode"] == "PERMISSIVE"
    assert (
        listener["tls"]["validation"]["trust"]["sds"]["secretName"]
        == "updated-ca-bundle-secret"
    )

    access_log = spec["logging"]["accessLog"]
    assert access_log["file"]["path"] == "/var/log/appmesh/updated_access.log"
    assert len(access_log["file"]["format"]["json"]) == 2
    assert access_log["file"]["format"]["json"][0] == {
        "key": "start_time",
        "value": "%START_TIME%",
    }
    assert access_log["file"]["format"]["json"][1] == {
        "key": "method",
        "value": "%REQUEST_METHOD%",
    }

    service_discovery = spec["serviceDiscovery"]["awsCloudMap"]
    assert len(service_discovery["attributes"]) == 1
    assert service_discovery["attributes"][0] == {
        "key": "environment",
        "value": "production",
    }
    assert service_discovery["ipPreference"] == "IPv4_PREFERRED"
    assert service_discovery["namespaceName"] == "updated-namespace"
    assert service_discovery["serviceName"] == "updated-service"

    connection = client.delete_virtual_node(
        meshName=MESH_NAME, meshOwner=mesh_owner, virtualNodeName=GRPC_NODE
    )
    virtualNode = connection["virtualNode"]
    spec = virtualNode["spec"]
    backend_defaults = spec["backendDefaults"]
    tls = backend_defaults["clientPolicy"]["tls"]
    assert tls["enforce"] is True
    assert tls["ports"] == [443]
    assert tls["certificate"]["file"]["certificateChain"] == "/path/to/cert_chain.pem"
    assert tls["certificate"]["file"]["privateKey"] == "/path/to/private_key.pem"
    assert tls["validation"]["subjectAlternativeNames"]["match"]["exact"] == [
        "grpc.example.com"
    ]
    assert (
        tls["validation"]["trust"]["file"]["certificateChain"]
        == "/path/to/ca_bundle.pem"
    )

    assert len(spec["backends"]) == 1
    backend = spec["backends"][0]
    assert backend["virtualService"]["clientPolicy"]["tls"]["enforce"] is True
    assert backend["virtualService"]["clientPolicy"]["tls"]["ports"] == [443]
    validation = backend["virtualService"]["clientPolicy"]["tls"]["validation"]
    assert validation["subjectAlternativeNames"]["match"]["exact"] == [
        "validation-alternate-name"
    ]
    assert validation["trust"]["acm"]["certificateAuthorityArns"] == ["example-acm-arn"]
    assert (
        backend["virtualService"]["virtualServiceName"]
        == "my-grpc-service.default.svc.cluster.local"
    )

    assert len(spec["listeners"]) == 1
    listener = spec["listeners"][0]
    assert listener["connectionPool"]["grpc"]["maxRequests"] == 500
    assert listener["healthCheck"]["healthyThreshold"] == 2
    assert listener["healthCheck"]["intervalMillis"] == 5000
    assert listener["healthCheck"]["port"] == 50051
    assert listener["healthCheck"]["protocol"] == "grpc"
    assert listener["healthCheck"]["timeoutMillis"] == 2000
    assert listener["healthCheck"]["unhealthyThreshold"] == 3
    assert listener["portMapping"]["port"] == 50051
    assert listener["portMapping"]["protocol"] == "grpc"
    assert listener["timeout"]["grpc"]["idle"]["unit"] == "s"
    assert listener["timeout"]["grpc"]["idle"]["value"] == 600
    assert listener["timeout"]["grpc"]["perRequest"]["unit"] == "s"
    assert listener["timeout"]["grpc"]["perRequest"]["value"] == 30
    assert (
        listener["tls"]["certificate"]["acm"]["certificateArn"]
        == "arn:aws:acm:us-east-1:123456789012:certificate/abcdefg-1234-5678-90ab-cdef01234567"
    )
    assert listener["tls"]["mode"] == "STRICT"
    assert (
        listener["tls"]["validation"]["trust"]["sds"]["secretName"]
        == "my-ca-bundle-secret"
    )

    access_log = spec["logging"]["accessLog"]
    assert access_log["file"]["path"] == "/var/log/appmesh/new_access.log"
    assert len(access_log["file"]["format"]["json"]) == 2
    assert access_log["file"]["format"]["json"][0] == {
        "key": "end_time",
        "value": "%END_TIME%",
    }
    assert access_log["file"]["format"]["json"][1] == {
        "key": "status_code",
        "value": "%RESPONSE_CODE%",
    }

    service_discovery = spec["serviceDiscovery"]["awsCloudMap"]
    assert len(service_discovery["attributes"]) == 1
    assert service_discovery["attributes"][0] == {"key": "region", "value": "us-east-1"}
    assert service_discovery["ipPreference"] == "IPv6_PREFERRED"
    assert service_discovery["namespaceName"] == "new-namespace"
    assert service_discovery["serviceName"] == "new-service"

    with pytest.raises(ClientError) as e:
        client.describe_virtual_node(
            meshName=MESH_NAME,
            meshOwner=mesh_owner,
            virtualNodeName=GRPC_NODE,
        )
    err = e.value.response["Error"]
    assert err["Code"] == "VirtualNodeNotFound"
    assert (
        err["Message"]
        == f"{GRPC_NODE} is not a virtual node associated with mesh {MESH_NAME}"
    )


@mock_aws
def test_tag_and_list_tags_for_resource(client):
    # create resources
    connection = client.create_mesh(
        meshName=MESH_NAME,
        spec={
            "egressFilter": {"type": "DROP_ALL"},
            "serviceDiscovery": {"ipPreference": "IPv4_ONLY"},
        },
        tags=[{"key": "owner", "value": "moto"}],
    )
    mesh = connection["mesh"]
    mesh_owner = mesh["metadata"]["meshOwner"]
    mesh_arn = mesh["metadata"]["arn"]

    ROUTER_NAME = "mock_router"

    connection = client.create_virtual_router(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        virtualRouterName=ROUTER_NAME,
        spec={"listeners": [{"portMapping": {"port": 80, "protocol": "http"}}]},
        tags=[{"key": "router_traffic", "value": "http"}],
    )

    virtual_router = connection.get("virtualRouter")
    virtual_router_arn = virtual_router["metadata"]["arn"]

    connection = client.create_route(
        meshOwner=mesh_owner,
        meshName=MESH_NAME,
        virtualRouterName=ROUTER_NAME,
        routeName="mock_http_route",
        tags=[{"key": "license", "value": "mit"}],
        spec=http_route_spec,
    )

    route = connection["route"]
    route_arn = route["metadata"]["arn"]

    connection = client.create_virtual_node(
        meshName=MESH_NAME,
        meshOwner=mesh_owner,
        spec=http_virtual_node_spec,
        tags=[{"key": "type", "value": "http"}],
        virtualNodeName="mock_http_node",
    )
    virtual_node = connection["virtualNode"]
    virtual_node_arn = virtual_node["metadata"]["arn"]

    # add tags and validate
    client.tag_resource(
        resourceArn=mesh_arn, tags=[{"key": "organization", "value": "moto"}]
    )
    connection = client.list_tags_for_resource(resourceArn=mesh_arn)
    tags = connection["tags"]
    assert tags[0] == {"key": "owner", "value": "moto"}
    assert tags[1] == {"key": "organization", "value": "moto"}

    client.tag_resource(
        resourceArn=virtual_router_arn,
        tags=[{"key": "organization", "value": "2moto2furious"}],
    )
    connection = client.list_tags_for_resource(resourceArn=virtual_router_arn)
    tags = connection["tags"]
    assert tags[0] == {"key": "router_traffic", "value": "http"}
    assert tags[1] == {"key": "organization", "value": "2moto2furious"}

    client.tag_resource(
        resourceArn=route_arn, tags=[{"key": "organization", "value": "motyo_drift"}]
    )
    connection = client.list_tags_for_resource(resourceArn=route_arn)
    tags = connection["tags"]
    assert tags[0] == {"key": "license", "value": "mit"}
    assert tags[1] == {"key": "organization", "value": "motyo_drift"}

    client.tag_resource(
        resourceArn=virtual_node_arn,
        tags=[{"key": "organization", "value": "how_moto_got_its_mojo_back"}],
    )
    connection = client.list_tags_for_resource(resourceArn=virtual_node_arn)
    tags = connection["tags"]
    assert tags[0] == {"key": "type", "value": "http"}
    assert tags[1] == {"key": "organization", "value": "how_moto_got_its_mojo_back"}
