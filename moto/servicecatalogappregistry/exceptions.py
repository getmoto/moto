"""Exceptions raised by the servicecatalogappregistry service."""

from moto.core.exceptions import JsonRESTError


class ResourceNotFoundException(JsonRESTError):
    def __init__(self) -> None:
        super().__init__(
            "ResourceNotFoundException", "The specified resource does not exist."
        )


class ValidationException(JsonRESTError):
    def __init__(self) -> None:
        super().__init__(
            "ValidationException", "The request has invalid or missing parameters."
        )
