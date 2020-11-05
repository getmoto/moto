from __future__ import unicode_literals

import json


class AWSError(Exception):
    TYPE = None
    STATUS = 400

    def __init__(self, message, type=None, status=None):
        self.message = message
        self.type = type if type is not None else self.TYPE
        self.status = status if status is not None else self.STATUS

    def response(self):
        return (
            json.dumps({"__type": self.type, "message": self.message}),
            dict(status=self.status),
        )


class InvalidInputException(AWSError):
    TYPE = "InvalidInputException"


class ResourceAlreadyExistsException(AWSError):
    TYPE = "ResourceAlreadyExistsException"


class ResourceNotFoundException(AWSError):
    TYPE = "ResourceNotFoundException"


class ResourceInUseException(AWSError):
    TYPE = "ResourceInUseException"


class LimitExceededException(AWSError):
    TYPE = "LimitExceededException"


class ValidationException(AWSError):
    TYPE = "ValidationException"
