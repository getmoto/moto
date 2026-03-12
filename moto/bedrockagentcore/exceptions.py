"""Exceptions raised by the bedrock-agentcore service."""

from moto.core.exceptions import JsonRESTError


class BedrockAgentCoreClientError(JsonRESTError):
    code = 400


class ValidationException(BedrockAgentCoreClientError):
    def __init__(self, msg: str):
        super().__init__(
            "ValidationException",
            "Input validation failed. Check your request parameters and retry the request.",
            f"{msg}",
        )


class ResourceNotFoundException(BedrockAgentCoreClientError):
    def __init__(self, msg: str):
        super().__init__("ResourceNotFoundException", f"{msg}")
