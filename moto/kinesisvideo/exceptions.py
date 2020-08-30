from __future__ import unicode_literals

from moto.core.exceptions import RESTError


class KinesisvideoClientError(RESTError):
    code = 400


class ResourceNotFoundException(KinesisvideoClientError):
    def __init__(self):
        self.code = 404
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException",
            "The requested stream is not found or not active.",
        )


class ResourceInUseException(KinesisvideoClientError):
    def __init__(self, message):
        self.code = 400
        super(ResourceInUseException, self).__init__(
            "ResourceInUseException", message,
        )
