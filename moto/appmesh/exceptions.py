"""Exceptions raised by the appmesh service."""

from moto.core.exceptions import JsonRESTError


class MeshError(JsonRESTError):
    code = 400


class MeshNotFoundError(MeshError):
    def __init__(self, mesh_name: str) -> None:
        super().__init__(
            "MeshNotFound",
            f"There are no meshes with the name {mesh_name}.",
        )


class ResourceNotFoundError(MeshError):
    def __init__(self, resource_arn: str) -> None:
        super().__init__(
            "ResourceNotFound",
            f"There are no mesh resources with the arn {resource_arn}.",
        )


class MeshOwnerDoesNotMatchError(MeshError):
    def __init__(self, mesh_name: str, mesh_owner: str) -> None:
        super().__init__(
            "MeshOwnerDoesNotMatch",
            f"The owner of the mesh {mesh_name} does not match the owner name provided: {mesh_owner}.",
        )


class VirtualRouterNameAlreadyTakenError(MeshError):
    def __init__(self, mesh_name: str, virtual_router_name: str) -> None:
        super().__init__(
            "VirtualRouterNameAlreadyTaken",
            f"There is already a virtual router named {virtual_router_name} associated with the mesh {mesh_name}.",
        )


class VirtualRouterNotFoundError(MeshError):
    def __init__(self, mesh_name: str, virtual_router_name: str) -> None:
        super().__init__(
            "VirtualRouterNotFound",
            f"The mesh {mesh_name} does not have a virtual router named {virtual_router_name}.",
        )


class RouteNotFoundError(MeshError):
    def __init__(
        self, mesh_name: str, virtual_router_name: str, route_name: str
    ) -> None:
        super().__init__(
            "RouteNotFound",
            f"There is no route named {route_name} associated with router {virtual_router_name} in mesh {mesh_name}.",
        )


class RouteNameAlreadyTakenError(MeshError):
    def __init__(
        self, mesh_name: str, virtual_router_name: str, route_name: str
    ) -> None:
        super().__init__(
            "RouteNameAlreadyTaken",
            f"There is already a route named {route_name} associated with router {virtual_router_name} in mesh {mesh_name}.",
        )


class MissingRequiredFieldError(MeshError):
    def __init__(self, field_name: str) -> None:
        super().__init__(
            "MissingRequiredField",
            f"{field_name} must be defined.",
        )


class VirtualNodeNotFoundError(MeshError):
    def __init__(self, mesh_name: str, virtual_node_name: str) -> None:
        super().__init__(
            "VirtualNodeNotFound",
            f"{virtual_node_name} is not a virtual node associated with mesh {mesh_name}",
        )


class VirtualNodeNameAlreadyTakenError(MeshError):
    def __init__(self, mesh_name: str, virtual_node_name: str) -> None:
        super().__init__(
            "VirtualNodeNameAlreadyTaken",
            f"There is already a virtual node named {virtual_node_name} associated with mesh {mesh_name}",
        )


class VirtualGatewayNotFoundError(MeshError):
    def __init__(self, mesh_name: str, virtual_gateway_name: str) -> None:
        super().__init__(
            "VirtualGatewayNotFound",
            f"{virtual_gateway_name} is not a virtual gateway associated with mesh {mesh_name}",
        )


class VirtualGatewayNameAlreadyTakenError(MeshError):
    def __init__(self, mesh_name: str, virtual_gateway_name: str) -> None:
        super().__init__(
            "VirtualGatewayNameAlreadyTaken",
            f"There is already a virtual gateway named {virtual_gateway_name} associated with mesh {mesh_name}",
        )


class GatewayRouteNotFoundError(MeshError):
    def __init__(
        self, mesh_name: str, virtual_gateway_name: str, gateway_route_name: str
    ) -> None:
        super().__init__(
            "GatewayRouteNotFound",
            f"There is no gateway route named {gateway_route_name} associated with gateway {virtual_gateway_name} in mesh {mesh_name}.",
        )


class GatewayRouteNameAlreadyTakenError(MeshError):
    def __init__(
        self, mesh_name: str, virtual_gateway_name: str, gateway_route_name: str
    ) -> None:
        super().__init__(
            "GatewayRouteNameAlreadyTaken",
            f"There is already a gateway route named {gateway_route_name} associated with gateway {virtual_gateway_name} in mesh {mesh_name}.",
        )
