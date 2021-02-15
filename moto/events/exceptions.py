from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class InvalidEventPatternException(JsonRESTError):
    code = 400

    def __init__(self):
        super(InvalidEventPatternException, self).__init__(
            "InvalidEventPatternException", "Event pattern is not valid."
        )


class ResourceNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException", message
        )


class ResourceAlreadyExistsException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ResourceAlreadyExistsException, self).__init__(
            "ResourceAlreadyExistsException", message
        )


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ValidationException, self).__init__("ValidationException", message)
