from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class LogsClientError(JsonRESTError):
    code = 400


class ResourceNotFoundException(LogsClientError):
    def __init__(self, msg=None):
        self.code = 400
        super().__init__(
            "ResourceNotFoundException", msg or "The specified log group does not exist"
        )


class InvalidParameterException(LogsClientError):
    def __init__(self, msg=None, constraint=None, parameter=None, value=None):
        self.code = 400
        if constraint:
            msg = "1 validation error detected: Value '{}' at '{}' failed to satisfy constraint: {}".format(
                value, parameter, constraint
            )
        super().__init__(
            "InvalidParameterException", msg or "A parameter is specified incorrectly."
        )


class ResourceAlreadyExistsException(LogsClientError):
    def __init__(self):
        self.code = 400
        super().__init__(
            "ResourceAlreadyExistsException", "The specified log group already exists"
        )


class LimitExceededException(LogsClientError):
    def __init__(self):
        self.code = 400
        super().__init__("LimitExceededException", "Resource limit exceeded.")
