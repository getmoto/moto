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
