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
    def __init__(self):
        self.code = 400
        super(InvalidRequestException, self).__init__(
            "InvalidRequestException",
            "The request is not valid."
        )
