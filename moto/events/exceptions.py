from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class ResourceNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException", message
        )


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ValidationException, self).__init__("ValidationException", message)
