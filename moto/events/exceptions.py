from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class IllegalStatusException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(IllegalStatusException, self).__init__("IllegalStatusException", message)


class InvalidEventPatternException(JsonRESTError):
    code = 400

    def __init__(self, reason=None):
        msg = "Event pattern is not valid. "
        if reason:
            msg += f"Reason: {reason}"

        super(InvalidEventPatternException, self).__init__(
            "InvalidEventPatternException", msg
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
