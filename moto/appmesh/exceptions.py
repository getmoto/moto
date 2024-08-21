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


class VirtualRouterNotFoundError(MeshError):
    def __init__(self, mesh_name: str, virtual_router_name: str) -> None:
        super().__init__(
            "VirtualRouterNotFound",
            f"The mesh {mesh_name} does not have a virtaul router named {virtual_router_name}.",
        )
