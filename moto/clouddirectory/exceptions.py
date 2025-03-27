"""Exceptions raised by the clouddirectory service."""

import json

from moto.core.exceptions import JsonRESTError


class ValidationError(JsonRESTError):
    def __init__(self, message: str):
        super().__init__("ValidationException", message)


class InvalidArnException(JsonRESTError):
    def __init__(self, resource_id: str):
        super().__init__("InvalidArnException", "Invalid Arn")
        body = {
            "ResourceId": resource_id,
            "Message": "Invalid Arn",
        }
        self.description = json.dumps(body)
