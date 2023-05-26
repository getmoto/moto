"""Exceptions raised by the identitystore service."""
import json

from moto.core.exceptions import AWSError
from typing import Any


request_id = "178936da-50ad-4d58-8871-22d9979e8658example"


class IdentityStoreError(AWSError):
    def __init__(self, **kwargs: Any):
        super(AWSError, self).__init__(error_type=self.TYPE, message=kwargs['message'])
        self.description: str = json.dumps(
            {
                "__type": self.error_type,
                "RequestId": request_id,
                "Message": self.message,
                "ResourceType": kwargs['resource_type'] if 'resource_type' in kwargs else None,
                "Reason": kwargs['reason'] if 'reason' in kwargs else None
            }
        )


class ResourceNotFoundException(IdentityStoreError):
    TYPE = "ResourceNotFoundException"
    code = 400


class ValidationException(IdentityStoreError):
    TYPE = 'ValidationException'
    code = 400


class ConflictException(IdentityStoreError):
    TYPE = 'ConflictException'
    code = 400
