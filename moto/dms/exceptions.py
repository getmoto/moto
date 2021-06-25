from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class DmsClientError(JsonRESTError):
    code = 400


class ResourceNotFoundFault(DmsClientError):
    def __init__(self, message):
        super(ResourceNotFoundFault, self).__init__("ResourceNotFoundFault", message)


class InvalidResourceStateFault(DmsClientError):
    def __init__(self, message):
        super(InvalidResourceStateFault, self).__init__(
            "InvalidResourceStateFault", message
        )


class ResourceAlreadyExistsFault(DmsClientError):
    def __init__(self, message):
        super(ResourceAlreadyExistsFault, self).__init__(
            "ResourceAlreadyExistsFault", message
        )
