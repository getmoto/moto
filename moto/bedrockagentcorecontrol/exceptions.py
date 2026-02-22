"""BedrockAgentCoreControl exceptions."""

from moto.core.exceptions import JsonRESTError


class BedrockAgentCoreControlClientError(JsonRESTError):
    code = 400


class ResourceNotFoundException(BedrockAgentCoreControlClientError):
    code = 404

    def __init__(self, message: str) -> None:
        super().__init__("ResourceNotFoundException", message)


class ConflictException(BedrockAgentCoreControlClientError):
    code = 409

    def __init__(self, message: str) -> None:
        super().__init__("ConflictException", message)


class ValidationException(BedrockAgentCoreControlClientError):
    def __init__(self, message: str) -> None:
        super().__init__("ValidationException", message)
