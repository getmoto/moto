from __future__ import unicode_literals

from moto.core.exceptions import JsonRESTError


class MediaPackageClientError(JsonRESTError):
    code = 400


# AWS service exceptions are caught with the underlying botocore exception, ClientError
class ClientError(MediaPackageClientError):
    def __init__(self, error, message):
        super(ClientError, self).__init__(error, message)
