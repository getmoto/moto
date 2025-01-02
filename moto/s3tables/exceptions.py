"""Exceptions raised by the s3tables service."""

from moto.core.exceptions import JsonRESTError


class BadRequestException(JsonRESTError):
    def __init__(self, message: str):
        super().__init__("BadRequestException", message)

    ...


class InvalidContinuationToken(BadRequestException): ...
