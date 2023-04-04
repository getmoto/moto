"""Exceptions raised by the lakeformation service."""
from moto.core.exceptions import JsonRESTError


class EntityNotFound(JsonRESTError):
    def __init__(self) -> None:
        super().__init__("EntityNotFoundException", "Entity not found")
