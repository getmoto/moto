from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class IoTClientError(JsonRESTError):
    code = 400


class ResourceNotFoundException(IoTClientError):
    def __init__(self):
        self.code = 404
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException",
            "The specified resource does not exist"
        )


class InvalidRequestException(IoTClientError):
    def __init__(self, msg=None):
        self.code = 400
        super(InvalidRequestException, self).__init__(
            "InvalidRequestException",
            msg or "The request is not valid."
        )


class VersionConflictException(IoTClientError):
    def __init__(self, name):
        self.code = 409
        super(VersionConflictException, self).__init__(
            'VersionConflictException',
            'The version for thing %s does not match the expected version.' % name
        )
