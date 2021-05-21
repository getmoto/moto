from __future__ import unicode_literals

from moto.core.exceptions import JsonRESTError


class MediaStoreDataClientError(JsonRESTError):
    code = 400


class ContainerNotFoundException(MediaStoreDataClientError):
    def __init__(self, msg=None):
        self.code = 400
        super(ContainerNotFoundException, self).__init__(
            "ContainerNotFoundException",
            msg or "The specified container does not exist",
        )


class ObjectNotFoundException(MediaStoreDataClientError):
    def __init__(self, msg=None):
        self.code = 400
        super(ObjectNotFoundException, self).__init__(
            "ObjectNotFoundException", msg or "The specified object does not exist"
        )


class InternalServerError(MediaStoreDataClientError):
    def __init__(self, msg=None):
        self.code = 500
        super(InternalServerError, self).__init__(
            "InternalServerError",
            msg or "An Internal Error occurred",
        )
# AWS service exceptions are caught with the underlying botocore exception, ClientError
class ClientError(MediaStoreDataClientError):
    def __init__(self, error, message):
        super(ClientError, self).__init__(error, message)
