from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class LogsClientError(JsonRESTError):
    code = 400


class ResourceNotFoundException(LogsClientError):
    def __init__(self):
        self.code = 400
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException",
            "The specified resource does not exist"
        )


class InvalidParameterException(LogsClientError):
    def __init__(self, msg=None):
        self.code = 400
        super(InvalidParameterException, self).__init__(
            "InvalidParameterException",
            msg or "A parameter is specified incorrectly."
        )


class ResourceAlreadyExistsException(LogsClientError):
    def __init__(self):
        self.code = 400
        super(ResourceAlreadyExistsException, self).__init__(
            'ResourceAlreadyExistsException',
            'The specified resource already exists.'
        )
